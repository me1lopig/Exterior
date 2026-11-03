"""Pantallas y control de estado de GeoPerfil 2D."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from perfil_geologico.calculos.contactos import (
    actualizar_vertices,
    actualizar_vinculos_observados,
    interfaces_observadas,
    vinculos_observados_desactualizados,
    vertices_a_dataframe,
)
from perfil_geologico.calculos.proyeccion import proyectar_puntos, longitud_eje
from perfil_geologico.calculos.terreno import terreno_de_campana, incidencias_cota_inicio
from perfil_geologico.calculos.dpsh import distribucion_curvas
from perfil_geologico.servicios.importar_campana import importar_campana
from perfil_geologico.calculos.presentacion import limites_perfil
from perfil_geologico.calculos.zonas import (
    TRAMAS,
    asignar_estilos_zonas,
    construir_zonas,
    validar_contactos_dominio,
)
from perfil_geologico.componentes.minicad import minicad_geologico, modelo_minicad
from perfil_geologico.modelos.dominio import Contacto, Proyecto, VerticeContacto
from perfil_geologico.servicios.datos_demo import crear_datos_vacios
from perfil_geologico.servicios.exportacion import (
    contactos_a_csv,
    contactos_a_dxf,
    figura_perfil_pdf, figura_perfil_imagen,
)
from perfil_geologico.servicios.importar_excel import (
    datos_a_excel,
)
from perfil_geologico.servicios.persistencia import proyecto_a_json, proyecto_desde_json
from perfil_geologico.utiles.validacion import validar_datos
from perfil_geologico.visualizacion.perfil_plotly import crear_figura_perfil


TABLAS = ("Sondeos", "Intervalos", "Unidades", "Ensayos_DPSH", "Lecturas_DPSH", "Eje")


def inicializar_estado() -> None:
    if "proyecto" not in st.session_state:
        st.session_state.proyecto = Proyecto(nombre="Perfil geologico")
    if "datos" not in st.session_state:
        st.session_state.datos = crear_datos_vacios()
    if "contactos" not in st.session_state:
        st.session_state.contactos = []
    if "zonas" not in st.session_state:
        st.session_state.zonas = list(st.session_state.proyecto.zonas)
    if "ultimo_evento_cad" not in st.session_state:
        st.session_state.ultimo_evento_cad = None
    if "revision_datos" not in st.session_state:
        st.session_state.revision_datos = 0
    if "hipotesis_referencia" not in st.session_state:
        st.session_state.hipotesis_referencia = ""
    if "avisos_importacion" not in st.session_state:
        st.session_state.avisos_importacion = []


def _datos_geometricos() -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    datos = st.session_state.datos
    if datos["Eje"].empty:
        return pd.DataFrame(), pd.DataFrame(), [], []
    errores, avisos = validar_datos(
        datos["Sondeos"], datos["Intervalos"], datos["Unidades"],
        datos["Ensayos_DPSH"], datos["Lecturas_DPSH"],
    )
    if errores:
        return pd.DataFrame(), pd.DataFrame(), errores, avisos
    try:
        sondeos = proyectar_puntos(datos["Sondeos"], datos["Eje"])
        dpsh = proyectar_puntos(datos["Ensayos_DPSH"], datos["Eje"])
    except ValueError as exc:
        errores.append(str(exc))
        return pd.DataFrame(), pd.DataFrame(), errores, avisos
    corredor = float(st.session_state.proyecto.corredor_m)
    fuera = pd.concat(
        [
            sondeos.loc[sondeos["distancia_eje_m"].abs() > corredor, "sondeo_id"].astype(str),
            dpsh.loc[dpsh["distancia_eje_m"].abs() > corredor, "ensayo_id"].astype(str),
        ]
    ).tolist()
    if fuera:
        avisos.append(f"Fuera del corredor de {corredor:g} m: {', '.join(fuera)}.")
    # Solo en la importacion multifichero, donde PERFIL1 aporta tambien cada cota de boca.
    estaciones = datos.get('Estaciones')
    if estaciones is not None and not estaciones.empty:
        try:
            terreno = terreno_de_campana(datos, sondeos)
            errores.extend(incidencias_cota_inicio(terreno, sondeos, dpsh))
        except ValueError as exc:
            errores.append(str(exc))
    return sondeos, dpsh, errores, avisos


CAPAS_PERFIL = (
    ("terreno", "Terreno"),
    ("sondeos", "Sondeos"),
    ("contactos", "Contactos y lentejones"),
    ("rellenos", "Rellenos geológicos"),
    ("penetracion", "Penetración dinámica"),
    ("spt", "SPT · secuencia de golpes"),
    ("muestras", "Muestras"),
    ("laboratorio", "Laboratorio (resumen)"),
    ("guitarra", "Guitarra"),
)


def _estado_sidebar(pagina: str) -> None:
    """Panel lateral contextual: configuracion grafica, sin duplicar el menu de proyecto."""
    proyecto: Proyecto = st.session_state.proyecto
    with st.sidebar:
        st.markdown('<div class="sidebar-heading">CAPAS Y VISUALIZACIÓN</div>', unsafe_allow_html=True)
        if pagina in ("Perfil", "Interpretación"):
            st.caption("Active solo las capas que necesite para interpretar o presentar el perfil.")
            grupos = (
                (("terreno", "Terreno"), ("sondeos", "Sondeos"),
                 ("contactos", "Contactos y lentejones"), ("rellenos", "Rellenos geológicos")),
                (("penetracion", "Penetración dinámica"), ("spt", "SPT · golpeos"),
                 ("muestras", "Muestras"), ("laboratorio", "Laboratorio")),
                (("guitarra", "Guitarra"),),
            )
            for i, grupo in enumerate(grupos):
                st.markdown(("**Geología**", "**Ensayos y muestras**", "**Presentación**")[i])
                for clave, etiqueta in grupo:
                    proyecto.capas[clave] = st.checkbox(
                        etiqueta, value=bool(proyecto.capas.get(clave, False)),
                        key=f"capa-{clave}",
                    )
            st.divider()
            st.markdown("**Tamaño de letra**")
            proyecto.texto_general_pt = st.slider(
                "Texto general (pt)", 6, 18, int(proyecto.texto_general_pt), key="texto-general")
            proyecto.texto_ensayos_pt = st.slider(
                "Ensayos (pt)", 6, 18, int(proyecto.texto_ensayos_pt), key="texto-ensayos")
            proyecto.texto_guitarra_pt = st.slider(
                "Guitarra (pt)", 6, 18, int(proyecto.texto_guitarra_pt), key="texto-guitarra")
            if pagina == "Interpretación":
                st.caption("En MiniCAD se muestran terreno, sondeos, contactos, rellenos y penetración. "
                           "Los SPT, las muestras y la guitarra aparecen en Perfil y en las exportaciones.")
        else:
            st.caption("Las capas y tamaños de letra se configuran en Perfil o Interpretación.")
        st.divider()
        st.markdown("**Campaña actual**")
        if st.session_state.datos["Eje"].empty:
            st.info("Importe varios Excel en la pestaña Datos.")
        else:
            sondeos, dpsh, errores, avisos = _datos_geometricos()
            st.caption(f"{len(sondeos)} sondeos · {len(dpsh)} penetraciones · "
                       f"{len(st.session_state.contactos)} contactos · {len(st.session_state.zonas)} zonas")
            if errores:
                st.error(f"{len(errores)} errores de validación")
            elif avisos:
                st.warning(f"{len(avisos)} avisos")
            else:
                st.success("Datos comprobados")


def _limpiar_preferencias_widgets() -> None:
    """Evita que controles de la campana anterior sobrescriban el JSON cargado."""
    claves = [f"capa-{nombre}" for nombre, _ in CAPAS_PERFIL]
    claves += ["texto-general", "texto-ensayos", "texto-guitarra", "escala_h", "escala_v"]
    for clave in claves:
        st.session_state.pop(clave, None)


def _acciones_proyecto() -> None:
    """Acciones reales de proyecto en cabecera con confirmacion para operaciones destructivas."""
    proyecto: Proyecto = st.session_state.proyecto
    proyecto.contactos = st.session_state.contactos
    proyecto.zonas = st.session_state.zonas
    con_datos = not st.session_state.datos["Eje"].empty
    nombre_archivo = "geoperfil_proyecto.json"
    a, b, c, d = st.columns([1, 1, 1, 6], gap="small")
    with a:
        with st.popover("＋ Nuevo", use_container_width=True):
            st.caption("Vacía la campaña y la interpretación actuales.")
            confirmado = st.checkbox("Confirmo el descarte de los cambios actuales", key="nuevo-confirmado")
            if st.button("Crear proyecto vacío", disabled=con_datos and not confirmado,
                         use_container_width=True, key="nuevo-aplicar"):
                st.session_state.proyecto = Proyecto(nombre="Perfil geológico")
                st.session_state.datos = crear_datos_vacios()
                st.session_state.contactos = []
                st.session_state.zonas = []
                st.session_state.avisos_importacion = []
                st.session_state.hipotesis_referencia = ""
                st.session_state.revision_datos += 1
                _limpiar_preferencias_widgets()
                for clave in ("campana_pendiente", "campana_huella_pendiente",
                              "campana_avisos_pendientes", "pagina_principal"):
                    st.session_state.pop(clave, None)
                st.rerun()
    with b:
        with st.popover("▣ Abrir", use_container_width=True):
            carga = st.file_uploader("Proyecto GeoPerfil (JSON)", type=["json"], key="abrir-json")
            confirmado = st.checkbox("Confirmo sustituir el proyecto actual", key="abrir-confirmado")
            if st.button("Abrir proyecto", use_container_width=True,
                         disabled=carga is None or (con_datos and not confirmado), key="abrir-aplicar"):
                try:
                    nuevo, datos = proyecto_desde_json(carga.getvalue())
                    st.session_state.proyecto = nuevo
                    st.session_state.contactos = nuevo.contactos
                    st.session_state.zonas = nuevo.zonas
                    st.session_state.datos = datos
                    st.session_state.hipotesis_referencia = ""
                    st.session_state.revision_datos += 1
                    st.session_state.avisos_importacion = []
                    _limpiar_preferencias_widgets()
                    st.rerun()
                except (ValueError, KeyError, TypeError) as exc:
                    st.error(f"Proyecto no válido: {exc}")
    with c:
        archivo = proyecto_a_json(proyecto, st.session_state.datos)
        st.download_button("▣ Guardar", data=archivo, file_name=nombre_archivo,
                           mime="application/json", use_container_width=True, disabled=not con_datos)
    with d:
        st.markdown('<div class="project-actions-hint">Proyecto JSON · se descarga una copia local; '
                    'la interpretación MiniCAD se guarda al finalizar cada geometría.</div>',
                    unsafe_allow_html=True)


def _cabecera() -> None:
    st.markdown("""<div class="gp-brand">
      <div class="gp-logo">◈</div>
      <div class="gp-brand-name">GeoPerfil <span>2D</span></div>
      <div class="gp-brand-subtitle">Interpretación geológica y geotécnica</div>
      <div class="gp-brand-version">v0.8.5 · Unidades, guitarra y correcciones</div>
    </div>""", unsafe_allow_html=True)
    _acciones_proyecto()


def vista_proyecto() -> None:
    proyecto: Proyecto = st.session_state.proyecto
    st.header("Datos del proyecto")
    st.markdown('<p class="section-note">Defina la referencia documental y las escalas de trabajo.</p>', unsafe_allow_html=True)
    izquierda, derecha = st.columns([1.4, 1.0])
    with izquierda:
        proyecto.nombre = st.text_input("Proyecto", proyecto.nombre)
        proyecto.localizacion = st.text_input("Localizacion", proyecto.localizacion)
        proyecto.autor = st.text_input("Autor / revision", proyecto.autor)
        proyecto.sistema_referencia = st.text_input("Sistema de referencia", proyecto.sistema_referencia)
    with derecha:
        col_h, col_v = st.columns(2)
        escala_h = col_h.selectbox("Escala H", [100, 200, 500, 1000, 2000, 5000], index=3, key="escala_h")
        opciones_v = [50, 100, 200, 500, 1000, 2000, 5000]
        escala_v = col_v.selectbox("Escala V", opciones_v, index=opciones_v.index(
            min(opciones_v, key=lambda valor: abs(valor - escala_h / max(proyecto.exageracion_vertical, 0.1)))
        ), key="escala_v")
        proyecto.exageracion_vertical = escala_h / escala_v
        st.caption(f"Exageracion vertical: {proyecto.exageracion_vertical:g}x (H 1:{escala_h} / V 1:{escala_v}). "
                   "Las coordenadas no cambian. Los formatos de impresion precisan escala fisica propia.")
    st.session_state.proyecto = proyecto


def vista_datos() -> None:
    st.header("Datos de campaña")
    st.markdown('<p class="section-note">Importe los libros originales y conserve la referencia de sus observaciones.</p>', unsafe_allow_html=True)
    with st.expander("Datos generales del proyecto y escalas", expanded=False):
        vista_proyecto()
    with st.expander("Importar campana desde varios archivos Excel", expanded=True):
        st.caption("PERFIL1.xlsx (obligatorio): PK acumulado y cota del terreno. BKFL, DPRG, ISPT y ListadoLab son opcionales. STA es un punto topografico del terreno, no una prospeccion.")
        libros = st.file_uploader("Seleccionar archivos de campana", type=["xlsx"], accept_multiple_files=True, key="libros-campana")
        if libros:
            st.write("Archivos seleccionados:", ", ".join(f.name for f in libros))
        # La previsualizacion solo vale para el conjunto exacto de archivos validado.
        from hashlib import sha256
        huella = tuple(sorted((f.name,sha256(f.getvalue()).hexdigest()) for f in libros)) if libros else ()
        if st.session_state.get("campana_huella_pendiente") != huella:
            st.session_state.pop("campana_pendiente", None)
            st.session_state.pop("campana_avisos_pendientes", None)
        if st.button("Validar archivos", disabled=not libros):
            try:
                nombres = [f.name for f in libros]
                if len(nombres) != len(set(nombres)):
                    raise ValueError("Existen archivos con el mismo nombre; cambie los nombres antes de cargar.")
                nuevos, avisos = importar_campana({f.name:f.getvalue() for f in libros})
                st.session_state.campana_pendiente = nuevos
                st.session_state.campana_huella_pendiente = huella
                st.session_state.campana_avisos_pendientes = avisos
                st.success(f"Validacion correcta: {len(nuevos['Sondeos'])} sondeos, {len(nuevos['Ensayos_DPSH'])} penetraciones, {len(nuevos['SPT'])} SPT y {len(nuevos['Muestras'])} muestras.")
            except (ValueError,KeyError,TypeError) as exc:
                st.session_state.pop("campana_pendiente", None)
                st.session_state.pop("campana_huella_pendiente", None)
                st.error(str(exc))
        if "campana_pendiente" in st.session_state:
            pendiente = st.session_state.campana_pendiente
            st.dataframe(pendiente["Estaciones"].rename(columns={"reconocimiento": "punto_id"}), use_container_width=True, hide_index=True)
            for aviso in st.session_state.get("campana_avisos_pendientes", []): st.warning(aviso)
            confirmar_campana=st.checkbox("Confirmo la sustitucion de datos y el descarte de la interpretacion actual", key="confirmar-campana")
            if st.button("Aplicar campana validada", type="primary", disabled=not confirmar_campana):
                st.session_state.datos = pendiente
                st.session_state.revision_datos += 1
                st.session_state.contactos = []
                st.session_state.zonas = []
                st.session_state.proyecto.contactos = []
                st.session_state.proyecto.zonas = []
                st.session_state.proyecto.extension_modo = "eje_completo"
                st.session_state.proyecto.pk_inicio_m = 0.0
                st.session_state.proyecto.pk_fin_m = float(pendiente["Eje"]["x_m"].max())
                posiciones=sorted(set(pendiente['Estaciones'].loc[
                    pendiente['Estaciones']['tipo_punto'].eq('reconocimiento'),'pk_m'].astype(float)))
                if len(posiciones)>1 and not pendiente['Lecturas_DPSH'].empty:
                    separacion=min(y-x for x,y in zip(posiciones,posiciones[1:]) if y>x)
                    max_golpes=max(float(pendiente['Lecturas_DPSH']['n20'].max()),1.0)
                    st.session_state.proyecto.escala_penetracion_m_golpe=round(
                        max(.005,min(.12,.72*separacion/max_golpes)),3)
                if st.session_state.proyecto.pk_fin_m<=25:
                    st.session_state.proyecto.guitarra_paso_m=5.0
                st.session_state.avisos_importacion = list(st.session_state.get("campana_avisos_pendientes", []))
                st.session_state.pop("campana_pendiente", None)
                st.session_state.pop("campana_huella_pendiente", None)
                st.rerun()
    if "Estaciones" in st.session_state.datos:
        with st.expander("Datos complementarios importados y fuentes"):
            for nombre in ("Estaciones","SPT","Muestras","Laboratorio","Fuentes"):
                tabla_extra=st.session_state.datos.get(nombre)
                if tabla_extra is not None:
                    st.markdown(f"**{nombre} — {len(tabla_extra)} registros**")
                    if nombre == "Estaciones":
                        tabla_extra = tabla_extra.rename(columns={"reconocimiento": "punto_id"})
                    st.dataframe(tabla_extra, use_container_width=True, hide_index=True)
            st.caption("Los datos de campana originales son de solo lectura. Para corregirlos modifique el Excel de origen y vuelva a importar.")
        for aviso in st.session_state.get("avisos_importacion",[]): st.warning(aviso)
    if st.session_state.datos["Eje"].empty:
        st.info("No hay campana cargada. Seleccione PERFIL1.xlsx y los libros complementarios para comenzar.")
        return
    with st.expander("Tablas internas de consulta (solo lectura)"):
        for nombre in TABLAS:
            tabla = st.session_state.datos[nombre]
            st.markdown(f"**{nombre} — {len(tabla)} registros**")
            st.dataframe(tabla, use_container_width=True, hide_index=True)
    _, _, errores, avisos = _datos_geometricos()
    for error in errores:
        st.error(error)
    for aviso in avisos:
        st.warning(aviso)
    if not errores and not avisos:
        st.success("Datos de campana validados.")


def vista_trazado() -> None:
    st.header("Eje y proyeccion")
    proyecto = st.session_state.proyecto
    proyecto.corredor_m = st.number_input(
        "Distancia maxima al eje del perfil (m)", 0.0, 5000.0, float(proyecto.corredor_m), 5.0,
        help="Semiancho del corredor: permite identificar reconocimientos alejados del eje. No modifica las coordenadas ni excluye silenciosamente los datos."
    )
    st.markdown('<p class="section-note">Perfil definido por PK acumulado y cotas de PERFIL1; STA aporta un punto de terreno, no un trabajo de campo.</p>', unsafe_allow_html=True)
    st.caption("Eje calculado automaticamente desde los PK de PERFIL1. Para corregirlo, modifique ese archivo y vuelva a importar.")
    st.dataframe(st.session_state.datos['Eje'], use_container_width=True, hide_index=True)
    sondeos, dpsh, errores, avisos = _datos_geometricos()
    if errores:
        for error in errores:
            st.error(error)
        return
    if "Estaciones" in st.session_state.datos:
        st.info("Campana por PK: las coordenadas X del eje son PK acumulados; Y=0. Las cotas se toman de PERFIL1.")
    st.subheader("Extension del perfil")
    longitud = longitud_eje(st.session_state.datos["Eje"])
    opciones = {"Eje completo": "eje_completo", "Reconocimientos extremos": "reconocimientos", "Intervalo manual": "manual"}
    modo_actual = proyecto.extension_modo if proyecto.extension_modo in opciones.values() else "eje_completo"
    etiqueta = st.selectbox("Limites de visualizacion", list(opciones), index=list(opciones.values()).index(modo_actual))
    proyecto.extension_modo = opciones[etiqueta]
    if proyecto.extension_modo == "reconocimientos":
        proyecto.margen_pk_m = st.number_input("Margen adicional en cada extremo (m)", min_value=0.0,
                                               max_value=max(longitud, 1.0), value=min(float(proyecto.margen_pk_m), longitud))
    elif proyecto.extension_modo == "manual":
        a, b = st.columns(2)
        proyecto.pk_inicio_m = a.number_input("PK inicial (m)", min_value=0.0, max_value=max(longitud, 0.001),
                                             value=min(max(0.0, float(proyecto.pk_inicio_m)), longitud))
        proyecto.pk_fin_m = b.number_input("PK final (m)", min_value=0.0, max_value=max(longitud, 0.001),
                                          value=min(max(0.0, float(proyecto.pk_fin_m)), longitud))
    opciones_paso = [2.0,5.0,10.0,25.0,50.0,100.0,200.0]
    proyecto.guitarra_paso_m = st.selectbox("Intervalo de la guitarra / PK (m)", opciones_paso,
                                            index=opciones_paso.index(float(proyecto.guitarra_paso_m))
                                            if float(proyecto.guitarra_paso_m) in opciones_paso else 4)
    try:
        rango = limites_perfil(proyecto, st.session_state.datos["Eje"], sondeos, dpsh)
        st.caption(f"Longitud del eje: {longitud:.2f} m. Representacion: PK {rango[0]:.2f} - {rango[1]:.2f} m. "
                   "El terreno se interpola entre puntos de PERFIL1, incluido STA; no se extrapola fuera.")
    except ValueError as exc:
        st.error(str(exc))
    fig = go.Figure()
    eje_actual = st.session_state.datos["Eje"].sort_values("orden")
    fig.add_trace(go.Scatter(x=eje_actual["x_m"], y=eje_actual["y_m"], mode="lines", name="Eje",
                             line={"color": "#0A2239", "width": 3}))
    fig.add_trace(go.Scatter(x=sondeos["x_m"], y=sondeos["y_m"], mode="markers+text", text=sondeos["sondeo_id"],
                             textposition="top center", name="Sondeos", marker={"color": "#5C748C", "size": 9}))
    fig.add_trace(go.Scatter(x=dpsh["x_m"], y=dpsh["y_m"], mode="markers+text", text=dpsh["ensayo_id"],
                             textposition="bottom center", name="Penetraciones", marker={"color": "#E45658", "size": 9, "symbol": "diamond"}))
    fig.update_layout(template="plotly_white", height=480, margin={"l": 30, "r": 20, "t": 20, "b": 40},
                      xaxis_title="X (m)", yaxis_title="Y (m)", yaxis={"scaleanchor": "x", "scaleratio": 1})
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "scrollZoom": True})
    tabla = pd.concat(
        [
            sondeos[["sondeo_id", "s_m", "distancia_eje_m"]].rename(columns={"sondeo_id": "reconocimiento"}),
            dpsh[["ensayo_id", "s_m", "distancia_eje_m"]].rename(columns={"ensayo_id": "reconocimiento"}),
        ], ignore_index=True,
    )
    st.dataframe(tabla.style.format({"s_m": "{:.2f}", "distancia_eje_m": "{:+.2f}"}), use_container_width=True, hide_index=True)
    for aviso in avisos:
        st.warning(aviso)


def vista_unidades() -> None:
    """Edicion de nombres y colores de las unidades interpretadas; el codigo BKFL no cambia."""
    st.header("Unidades geológicas")
    st.caption("Personalice nombres y colores. Se conserva el código de estrato original "
               "para que los intervalos y contactos sigan vinculados a la misma unidad.")
    tabla = st.session_state.datos["Unidades"]
    if tabla.empty:
        st.info("Cargue un libro BKFL para definir las unidades geológicas.")
        return
    from perfil_geologico.calculos.estilos_unidades import aplicar_edicion_unidades

    revision = int(st.session_state.revision_datos)
    cambios = {}
    with st.form("personalizar-unidades", border=True):
        for fila in tabla.sort_values("orden").itertuples(index=False):
            unidad_id = str(fila.unidad_id)
            izquierda, centro, derecha = st.columns([1.2, 4.5, 2.3], vertical_alignment="bottom")
            with izquierda:
                st.text_input("Código", value=unidad_id, disabled=True,
                              key=f"unidad-id-{revision}-{unidad_id}")
            with centro:
                nombre = st.text_input("Nombre", value=str(fila.nombre),
                                      key=f"unidad-nombre-{revision}-{unidad_id}")
            with derecha:
                color = st.color_picker("Color seleccionado", value=str(fila.color),
                                        key=f"unidad-color-{revision}-{unidad_id}")
                st.caption(f"{color.upper()}")
            cambios[unidad_id] = {"nombre": nombre, "color": color}
            st.divider()
        confirmar = st.form_submit_button("Guardar nombres y colores", type="primary", use_container_width=True)
    if confirmar:
        try:
            nuevas_unidades, nuevas_zonas = aplicar_edicion_unidades(
                tabla, st.session_state.zonas, cambios)
        except ValueError as exc:
            st.error(f"No se pudieron actualizar las unidades: {exc}")
        else:
            st.session_state.datos["Unidades"] = nuevas_unidades
            st.session_state.zonas = nuevas_zonas
            st.session_state.proyecto.zonas = nuevas_zonas
            st.session_state.revision_datos += 1
            st.success("Nombres y colores actualizados en el perfil, MiniCAD y exportaciones.")
            st.rerun()
    st.caption("La litología original permanece en BKFL/Intervalos y Fuentes. "
               "Las tramas de las zonas se asignan desde Interpretación.")


def _contactos_desde_cad(datos: list[dict]) -> list[Contacto]:
    """Valida y reconstruye los contactos enviados por el lienzo."""
    resultado: list[Contacto] = []
    identificadores: set[str] = set()
    for bruto in datos:
        identificador = str(bruto.get("contacto_id", "")).strip()
        if not identificador or identificador in identificadores:
            raise ValueError("Cada contacto debe tener un identificador unico.")
        identificadores.add(identificador)
        vertices = [
            VerticeContacto(
                s_m=float(punto["s_m"]), z_m=float(punto["z_m"]),
                origen=str(punto.get("origen", "interpretado")),
                referencia=str(punto.get("referencia", "")),
                interfaz_id=str(punto.get("interfaz_id", "")),
            )
            for punto in bruto.get("vertices", [])
        ]
        contacto = Contacto(
            contacto_id=identificador,
            nombre=str(bruto.get("nombre", identificador)),
            unidad_superior=str(bruto.get("unidad_superior", "")),
            unidad_inferior=str(bruto.get("unidad_inferior", "")),
            color=str(bruto.get("color", "#334155")),
            vertices=vertices,
            visible=bool(bruto.get("visible", True)),
            bloqueado=bool(bruto.get("bloqueado", False)),
            evidencia=str(bruto.get("evidencia", "interpretado")),
            incertidumbre_m=max(0.0, float(bruto.get("incertidumbre_m", 0.0))),
        )
        contacto.ordenar()
        resultado.append(contacto)
    return resultado


def vista_interpretacion() -> None:
    st.header("MiniCAD de interpretacion")
    st.markdown(
        '<p class="section-note">Dibuje contactos o lentes, ajuste vertices a interfaces observadas y asigne unidad y trama a cada zona cerrada.</p>',
        unsafe_allow_html=True,
    )
    sondeos, dpsh, errores, _ = _datos_geometricos()
    if sondeos.empty:
        st.info('No hay columnas litologicas BKFL; el MiniCAD requiere al menos un sondeo.')
        return
    if errores:
        st.error("Corrija los datos y el eje antes de interpretar contactos.")
        return

    interfaces = interfaces_observadas(sondeos, st.session_state.datos["Intervalos"])
    vinculos_desactualizados = vinculos_observados_desactualizados(
        st.session_state.contactos, interfaces
    )
    if vinculos_desactualizados:
        aviso, accion = st.columns([4, 1])
        aviso.warning(
            f"Hay {len(vinculos_desactualizados)} vertices vinculados a sondeos cuya posicion "
            "ha cambiado o cuya interfaz ya no existe. Los contactos bloqueados no se actualizaran."
        )
        if accion.button("Actualizar vinculos", use_container_width=True):
            actualizar_vinculos_observados(st.session_state.contactos, interfaces)
            try:
                st.session_state.zonas, avisos = construir_zonas(
                    sondeos, st.session_state.contactos, st.session_state.zonas,
                    terreno_puntos=terreno_de_campana(st.session_state.datos, sondeos),
                    dpsh=dpsh,
                )
                st.session_state.avisos_topologia = avisos
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))

    st.caption(
        "Dibuje contactos y lentejones manualmente. Al finalizar una geometria, "
        "se recalcularan las zonas para poder rellenarlas. Alt desactiva temporalmente el ajuste."
    )

    with st.expander("Hipotesis y comparacion"):
        st.caption("Guarde primero los cambios del miniCAD antes de crear una hipotesis.")
        columnas = st.columns([2, 1, 2, 1, 1])
        nombre_hipotesis = columnas[0].text_input(
            "Nombre", placeholder="Ej. Hipotesis A", label_visibility="collapsed",
            key="nombre-nueva-hipotesis",
        ).strip()
        if columnas[1].button("Guardar", use_container_width=True, disabled=not nombre_hipotesis):
            nueva = {
                "nombre": nombre_hipotesis,
                "creada": datetime.now().astimezone().isoformat(timespec="seconds"),
                "contactos": [asdict(contacto) for contacto in st.session_state.contactos],
                "zonas": list(st.session_state.zonas),
            }
            existentes = st.session_state.proyecto.hipotesis
            st.session_state.proyecto.hipotesis = [
                hipotesis for hipotesis in existentes if hipotesis.get("nombre") != nombre_hipotesis
            ] + [nueva]
            st.rerun()
        nombres_hipotesis = [
            str(hipotesis.get("nombre", "")) for hipotesis in st.session_state.proyecto.hipotesis
            if hipotesis.get("nombre")
        ]
        seleccion_hipotesis = columnas[2].selectbox(
            "Hipotesis", [""] + nombres_hipotesis,
            format_func=lambda valor: valor or "Seleccionar hipotesis",
            label_visibility="collapsed", key="selector-hipotesis",
        )
        if columnas[3].button("Cargar", use_container_width=True, disabled=not seleccion_hipotesis):
            hipotesis = next(
                item for item in st.session_state.proyecto.hipotesis
                if item.get("nombre") == seleccion_hipotesis
            )
            st.session_state.contactos = _contactos_desde_cad(hipotesis.get("contactos", []))
            st.session_state.zonas = list(hipotesis.get("zonas", []))
            st.session_state.hipotesis_referencia = ""
            st.rerun()
        if columnas[4].button("Borrar", use_container_width=True, disabled=not seleccion_hipotesis):
            st.session_state.proyecto.hipotesis = [
                item for item in st.session_state.proyecto.hipotesis
                if item.get("nombre") != seleccion_hipotesis
            ]
            if st.session_state.hipotesis_referencia == seleccion_hipotesis:
                st.session_state.hipotesis_referencia = ""
            st.rerun()
        st.selectbox(
            "Superponer como referencia", [""] + nombres_hipotesis,
            format_func=lambda valor: valor or "Ninguna",
            key="hipotesis_referencia",
        )

    contactos_referencia: list[Contacto] = []
    if st.session_state.hipotesis_referencia:
        referencia = next(
            (item for item in st.session_state.proyecto.hipotesis
             if item.get("nombre") == st.session_state.hipotesis_referencia),
            None,
        )
        if referencia:
            contactos_referencia = _contactos_desde_cad(referencia.get("contactos", []))

    modelo = modelo_minicad(
        sondeos, st.session_state.datos["Intervalos"], st.session_state.datos["Unidades"],
        st.session_state.contactos, st.session_state.zonas, dpsh,
        st.session_state.datos["Lecturas_DPSH"],
        escala_dpsh=float(st.session_state.proyecto.escala_penetracion_m_golpe),
        contactos_referencia=contactos_referencia,
        exageracion_vertical=st.session_state.proyecto.exageracion_vertical,
        terreno_puntos=terreno_de_campana(st.session_state.datos, sondeos),
        capas=st.session_state.proyecto.capas,
        texto_general_pt=st.session_state.proyecto.texto_general_pt,
        texto_ensayos_pt=st.session_state.proyecto.texto_ensayos_pt,
    )
    respuesta = minicad_geologico(modelo, key="minicad-principal")
    if isinstance(respuesta, str):
        try:
            respuesta = json.loads(respuesta)
        except json.JSONDecodeError:
            respuesta = None
    if respuesta and respuesta.get("action") == "save":
        evento = respuesta.get("event_id")
        if evento != st.session_state.ultimo_evento_cad:
            try:
                contactos = _contactos_desde_cad(respuesta.get("contactos", []))
                for contacto in contactos:
                    for punto in contacto.vertices:
                        if punto.origen == "observado" and punto.interfaz_id:
                            referencia = interfaces.get(punto.interfaz_id)
                            if referencia is None or any(abs(a-b) > 1e-7 for a,b in zip(referencia,(punto.s_m,punto.z_m))):
                                raise ValueError(f"Interfaz observada desactualizada: {punto.interfaz_id}.")
                validar_contactos_dominio(sondeos, contactos,
                    terreno_puntos=terreno_de_campana(st.session_state.datos, sondeos), dpsh=dpsh)
                if respuesta.get("limpiar_interpretacion") and not contactos:
                    zonas, avisos = [], []
                else:
                    zonas, avisos = construir_zonas(
                        sondeos, contactos, list(respuesta.get("zonas", [])),
                        terreno_puntos=terreno_de_campana(st.session_state.datos, sondeos),
                        dpsh=dpsh,
                    )
                st.session_state.contactos = contactos
                st.session_state.zonas = zonas
                st.session_state.avisos_topologia = avisos
                st.session_state.ultimo_evento_cad = evento
                st.session_state.proyecto.contactos = contactos
                st.session_state.proyecto.zonas = zonas
                st.rerun()
            except (ValueError, RuntimeError, KeyError, TypeError) as exc:
                st.error(f"No se pudo guardar la interpretacion: {exc}")

    for aviso in st.session_state.get("avisos_topologia", []):
        st.warning(aviso)
    if st.session_state.zonas:
        sin_asignar = sum(not zona.get("unidad_id") for zona in st.session_state.zonas)
        if sin_asignar:
            st.info(f"Asigne unidad y trama a {sin_asignar} zonas con Rellenar o desde la tabla avanzada.")
        else:
            st.success("Todas las zonas tienen unidad asignada.")

    with st.expander("Edicion numerica y tabla de zonas"):
        if st.session_state.contactos:
            nombres = {c.contacto_id: c.nombre for c in st.session_state.contactos}
            seleccionado = st.selectbox("Contacto", list(nombres), format_func=nombres.get)
            contacto = next(c for c in st.session_state.contactos if c.contacto_id == seleccionado)
            editada = st.data_editor(
                vertices_a_dataframe(contacto), num_rows="dynamic", use_container_width=True, hide_index=True,
                column_config={
                    "origen": st.column_config.SelectboxColumn(
                        "origen", options=["observado", "proyectado", "interpretado", "inferido_acunamiento"], required=True
                    ),
                    "s_m": st.column_config.NumberColumn("s (m)", format="%.3f"),
                    "z_m": st.column_config.NumberColumn("cota (m)", format="%.3f"),
                    "interfaz_id": st.column_config.TextColumn("interfaz vinculada", disabled=True),
                }, key=f"vertices-avanzado-{seleccionado}",
            )
            if st.button("Aplicar coordenadas exactas"):
                try:
                    actualizar_vertices(contacto, editada)
                    validar_contactos_dominio(sondeos, st.session_state.contactos,
                        terreno_puntos=terreno_de_campana(st.session_state.datos, sondeos), dpsh=dpsh)
                    st.session_state.zonas, _ = construir_zonas(
                        sondeos, st.session_state.contactos, st.session_state.zonas,
                        terreno_puntos=terreno_de_campana(st.session_state.datos, sondeos),
                        dpsh=dpsh,
                    )
                    st.rerun()
                except (ValueError, RuntimeError) as exc:
                    st.error(str(exc))
        if st.session_state.zonas:
            tabla_zonas = pd.DataFrame(st.session_state.zonas)[
                ["zona_id", "etiqueta", "unidad_id", "trama", "area_m2"]
            ]
            unidades = st.session_state.datos["Unidades"]["unidad_id"].astype(str).tolist()
            tabla_editada = st.data_editor(
                tabla_zonas, use_container_width=True, hide_index=True, disabled=["zona_id", "etiqueta", "area_m2"],
                column_config={
                    "unidad_id": st.column_config.SelectboxColumn("unidad", options=unidades),
                    "trama": st.column_config.SelectboxColumn("trama", options=list(TRAMAS)),
                    "area_m2": st.column_config.NumberColumn("area grafica (m2)", format="%.2f"),
                }, key="tabla-zonas",
            )
            if st.button("Aplicar unidades y tramas"):
                st.session_state.zonas = asignar_estilos_zonas(
                    st.session_state.zonas, tabla_editada, st.session_state.datos["Unidades"]
                )
                st.rerun()


def vista_perfil() -> None:
    st.header("Perfil integrado")
    sondeos, dpsh, errores, avisos = _datos_geometricos()
    if errores:
        st.error("No es posible representar el perfil mientras existan errores bloqueantes.")
        return
    if sondeos.empty:
        st.warning('No se han importado sondeos BKFL. Consulte penetraciones y resultados en Datos; el perfil geologico requiere al menos un sondeo.')
        return
    proyecto=st.session_state.proyecto
    st.caption("Capas visibles y tamaños de letra: panel lateral izquierdo. "
               "Las preferencias se conservan en el proyecto y las exportaciones.")
    proyecto.escala_penetracion_m_golpe=st.number_input(
        'Escala penetracion (m/golpe)', 0.005, 1.0,
        float(proyecto.escala_penetracion_m_golpe), 0.005)
    escala=proyecto.escala_penetracion_m_golpe
    st.caption("Los golpes DPRG se representan como registrados cada 20 cm; subtipo y rechazo requieren confirmacion documental.")
    if not dpsh.empty:
        limite_grafico=terreno_de_campana(st.session_state.datos,sondeos)
        lim_b=(float(limite_grafico['s_m'].min()),float(limite_grafico['s_m'].max()))
        efectiva, sentidos = distribucion_curvas(dpsh,st.session_state.datos['Lecturas_DPSH'],escala,sondeos,lim_b)
        if efectiva < escala - 1e-8:
            st.caption(f"Escala grafica aplicada: {efectiva:.4f} m/golpe (reducida automaticamente para no invadir otros trabajos ni los limites del perfil).")
        if any(v==-1 for v in sentidos.values()):
            st.caption("Las curvas en el extremo derecho se dibujan hacia el interior; sus PK, cotas y N20 no cambian.")
    rellenos=proyecto.capas['rellenos']
    mostrar_dpsh=proyecto.capas['penetracion']
    extras={
        'terreno_puntos':terreno_de_campana(st.session_state.datos,sondeos),
        'spt':st.session_state.datos.get('SPT'),
        'muestras':st.session_state.datos.get('Muestras'),
        'laboratorio':st.session_state.datos.get('Laboratorio'),
    }
    try:
        rango = limites_perfil(st.session_state.proyecto, st.session_state.datos["Eje"], sondeos, dpsh)
    except ValueError as exc:
        st.error(str(exc))
        return
    figura = crear_figura_perfil(
        st.session_state.proyecto, sondeos, st.session_state.datos["Intervalos"],
        st.session_state.datos["Unidades"], st.session_state.contactos, dpsh,
        st.session_state.datos["Lecturas_DPSH"], zonas=st.session_state.zonas,
        escala_dpsh=escala, mostrar_rellenos=rellenos, mostrar_dpsh=mostrar_dpsh,
        rango_pk=rango, paso_guitarra=st.session_state.proyecto.guitarra_paso_m,
        **extras,
    )
    st.plotly_chart(figura, use_container_width=True, config={"displaylogo": False, "scrollZoom": True})
    sin_asignar = sum(not zona.get("unidad_id") for zona in st.session_state.zonas)
    if sin_asignar:
        st.warning(f"Hay {sin_asignar} zonas sin unidad asignada.")
    elif st.session_state.zonas:
        st.success("Zonas topologicas calculadas y asignadas.")
    for aviso in avisos:
        st.warning(aviso)


def vista_exportacion() -> None:
    st.header("Exportacion y trazabilidad")
    st.markdown('<p class="section-note">Todos los formatos se generan desde las coordenadas almacenadas.</p>', unsafe_allow_html=True)
    sondeos, dpsh, errores, _ = _datos_geometricos()
    if errores:
        st.error("Corrija los errores antes de exportar.")
        return
    if sondeos.empty:
        st.warning('Sin sondeos BKFL no se generan perfiles graficos. Descargue el proyecto y sus datos desde la barra lateral o Datos.')
        return
    proyecto: Proyecto = st.session_state.proyecto
    proyecto.contactos = st.session_state.contactos
    proyecto.zonas = st.session_state.zonas
    datos = st.session_state.datos
    proyecto.escala_penetracion_m_golpe=st.number_input(
        'Escala penetracion para exportacion (m/golpe)', 0.005, 1.0,
        float(proyecto.escala_penetracion_m_golpe), 0.005)
    escala=proyecto.escala_penetracion_m_golpe
    try:
        rango = limites_perfil(proyecto, datos["Eje"], sondeos, dpsh)
    except ValueError as exc:
        st.error(str(exc))
        return
    extras={
        'terreno_puntos':terreno_de_campana(datos,sondeos),
        'spt':datos.get('SPT'),
        'muestras':datos.get('Muestras'),
        'laboratorio':datos.get('Laboratorio'),
    }
    st.caption("Las exportaciones utilizan las capas y tamanos de texto guardados desde la pestana Perfil.")
    figura = crear_figura_perfil(
        proyecto, sondeos, datos["Intervalos"], datos["Unidades"],
        st.session_state.contactos, dpsh, datos["Lecturas_DPSH"],
        zonas=st.session_state.zonas, escala_dpsh=escala, rango_pk=rango,
        paso_guitarra=proyecto.guitarra_paso_m, **extras,
    )
    col1, col2, col3 = st.columns(3)
    col1.download_button("Proyecto JSON", proyecto_a_json(proyecto, datos), "perfil_geologico.json", "application/json", use_container_width=True)
    col2.download_button("Exportar datos procesados (Excel)", datos_a_excel(datos), "datos_perfil.xlsx",
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    col3.download_button("Perfil HTML", figura.to_html(include_plotlyjs="cdn").encode("utf-8"),
                         "perfil_interactivo.html", "text/html", use_container_width=True)
    col4, col5, col6 = st.columns(3)
    col4.download_button("Contactos CSV", contactos_a_csv(st.session_state.contactos), "contactos.csv", "text/csv", use_container_width=True)
    col5.download_button(
        "Perfil DXF con guitarra y tramas", contactos_a_dxf(
            st.session_state.contactos, st.session_state.zonas, proyecto=proyecto,
            sondeos=sondeos, dpsh=dpsh, lecturas_dpsh=datos["Lecturas_DPSH"],
            intervalos=datos["Intervalos"], unidades=datos["Unidades"],
            rango_pk=rango, escala_dpsh=escala, **extras,
        ),
        "perfil_geologico.dxf", "application/dxf", use_container_width=True,
    )
    try:
        pdf = figura_perfil_pdf(
            proyecto, sondeos, datos["Intervalos"], datos["Unidades"],
            st.session_state.contactos, dpsh, datos["Lecturas_DPSH"], escala,
            zonas=st.session_state.zonas, rango_pk=rango, **extras,
        )
        col6.download_button("Plano PDF", pdf, "perfil_geologico.pdf", "application/pdf", use_container_width=True)
    except ImportError:
        col6.warning("Instale matplotlib para exportar PDF.")
    try:
        png = figura_perfil_imagen(
            proyecto, sondeos, datos["Intervalos"], datos["Unidades"],
            st.session_state.contactos, dpsh, datos["Lecturas_DPSH"], escala,
            zonas=st.session_state.zonas, rango_pk=rango, formato="png", **extras,
        )
        svg = figura_perfil_imagen(
            proyecto, sondeos, datos["Intervalos"], datos["Unidades"],
            st.session_state.contactos, dpsh, datos["Lecturas_DPSH"], escala,
            zonas=st.session_state.zonas, rango_pk=rango, formato="svg", **extras,
        )
        a, b = st.columns(2)
        a.download_button("Imagen PNG con guitarra", png, "perfil_geologico.png", "image/png", use_container_width=True)
        b.download_button("Imagen SVG con guitarra", svg, "perfil_geologico.svg", "image/svg+xml", use_container_width=True)
    except ImportError:
        st.warning("Se necesita Matplotlib para generar las imagenes.")
    st.caption("DXF en coordenadas locales del perfil: X = PK (m); Y = cota (m). "
               "La guitarra DXF se coloca bajo el perfil, fuera del dominio de cotas geologicas.")


def ejecutar_aplicacion() -> None:
    inicializar_estado()
    _cabecera()
    paginas = ["Datos", "Trazado", "Perfil", "Unidades", "Interpretación", "Exportar"]
    pagina = st.radio("Navegación principal", paginas, horizontal=True,
                      label_visibility="collapsed", key="pagina_principal")
    _estado_sidebar(pagina)
    vistas = {
        "Datos": vista_datos,
        "Trazado": vista_trazado,
        "Perfil": vista_perfil,
        "Unidades": vista_unidades,
        "Interpretación": vista_interpretacion,
        "Exportar": vista_exportacion,
    }
    if pagina != "Datos" and st.session_state.datos["Eje"].empty:
        st.info("Importe una campaña mediante varios archivos Excel en la pestaña Datos.")
        return
    vistas[pagina]()
