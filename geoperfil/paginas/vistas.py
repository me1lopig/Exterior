"""Pantallas y control de estado de GeoPerfil 2D."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from io import BytesIO
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from perfil_geologico.calculos.contactos import (
    actualizar_vertices,
    actualizar_vinculos_observados,
    contactos_observados,
    interfaces_observadas,
    vinculos_observados_desactualizados,
    vertices_a_dataframe,
)
from perfil_geologico.calculos.proyeccion import proyectar_puntos
from perfil_geologico.calculos.zonas import TRAMAS, asignar_estilos_zonas, construir_zonas
from perfil_geologico.componentes.minicad import minicad_geologico, modelo_minicad
from perfil_geologico.modelos.dominio import Contacto, Proyecto, VerticeContacto
from perfil_geologico.servicios.datos_demo import crear_datos_demo
from perfil_geologico.servicios.exportacion import (
    contactos_a_csv,
    contactos_a_dxf,
    figura_perfil_pdf,
)
from perfil_geologico.servicios.importar_excel import (
    crear_plantilla_excel,
    datos_a_excel,
    leer_excel,
)
from perfil_geologico.servicios.persistencia import proyecto_a_json, proyecto_desde_json
from perfil_geologico.utiles.validacion import validar_datos
from perfil_geologico.visualizacion.perfil_plotly import crear_figura_perfil


TABLAS = ("Sondeos", "Intervalos", "Unidades", "Ensayos_DPSH", "Lecturas_DPSH", "Eje")


def inicializar_estado() -> None:
    if "proyecto" not in st.session_state:
        st.session_state.proyecto = Proyecto()
    if "datos" not in st.session_state:
        st.session_state.datos = crear_datos_demo()
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


def _datos_geometricos() -> tuple[pd.DataFrame, pd.DataFrame, list[str], list[str]]:
    datos = st.session_state.datos
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
    return sondeos, dpsh, errores, avisos


def _estado_sidebar() -> None:
    proyecto: Proyecto = st.session_state.proyecto
    proyecto.contactos = st.session_state.contactos
    proyecto.zonas = st.session_state.zonas
    sondeos, dpsh, errores, avisos = _datos_geometricos()
    st.sidebar.markdown("## Navegacion")
    st.sidebar.caption("Introduzca datos, defina el eje y revise la interpretacion antes de exportar.")
    st.sidebar.divider()
    st.sidebar.markdown("### Acciones")
    if st.sidebar.button("Restablecer caso demostrativo", use_container_width=True):
        st.session_state.proyecto = Proyecto()
        st.session_state.datos = crear_datos_demo()
        st.session_state.contactos = []
        st.session_state.zonas = []
        st.session_state.hipotesis_referencia = ""
        st.rerun()
    if st.sidebar.button("Crear borrador automatico", type="primary", use_container_width=True):
        if not errores:
            st.session_state.contactos = contactos_observados(
                sondeos, st.session_state.datos["Intervalos"], st.session_state.datos["Unidades"]
            )
            try:
                st.session_state.zonas, _ = construir_zonas(sondeos, st.session_state.contactos, [])
                st.rerun()
            except RuntimeError as exc:
                st.sidebar.error(str(exc))
    st.sidebar.divider()
    st.sidebar.markdown("### Estado")
    if errores:
        st.sidebar.markdown(f'<div class="status-error">{len(errores)} errores bloqueantes</div>', unsafe_allow_html=True)
    else:
        st.sidebar.markdown('<div class="status-ok">Entradas comprobadas</div>', unsafe_allow_html=True)
    st.sidebar.markdown(
        f'<p class="metric-line">{len(sondeos)} sondeos · {len(dpsh)} DPSH · '
        f'{len(st.session_state.contactos)} contactos · {len(st.session_state.zonas)} zonas · {len(avisos)} avisos</p>',
        unsafe_allow_html=True,
    )
    st.sidebar.divider()
    st.sidebar.markdown("### Proyecto")
    archivo = proyecto_a_json(proyecto, st.session_state.datos)
    st.sidebar.download_button(
        "Descargar proyecto", archivo, file_name="perfil_geologico.json",
        mime="application/json", use_container_width=True,
    )
    carga = st.sidebar.file_uploader("Abrir proyecto", type=["json"], label_visibility="collapsed")
    if carga is not None and st.sidebar.button("Cargar archivo", use_container_width=True):
        try:
            proyecto_nuevo, datos_nuevos = proyecto_desde_json(carga.getvalue())
            st.session_state.proyecto = proyecto_nuevo
            st.session_state.contactos = proyecto_nuevo.contactos
            st.session_state.zonas = proyecto_nuevo.zonas
            st.session_state.datos = datos_nuevos
            st.session_state.hipotesis_referencia = ""
            st.rerun()
        except (ValueError, KeyError, TypeError) as exc:
            st.sidebar.error(f"Proyecto no valido: {exc}")


def _cabecera() -> None:
    st.markdown('<div class="app-kicker">GEOPERFIL · INTERPRETACION GEOLOGICA 2D</div>', unsafe_allow_html=True)
    st.title("Perfil geologico desde reconocimientos")
    st.markdown(
        '<p class="app-subtitle">Correlacion trazable de sondeos y representacion grafica de ensayos DPSH.</p>',
        unsafe_allow_html=True,
    )


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
        proyecto.corredor_m = st.number_input("Semiancho del corredor (m)", 0.0, 5000.0, proyecto.corredor_m, 5.0)
        proyecto.exageracion_vertical = st.number_input(
            "Exageracion vertical", 0.1, 20.0, proyecto.exageracion_vertical, 0.1
        )
        st.info("La exageracion afecta al plano exportado. Las coordenadas almacenadas permanecen invariables.")
    st.session_state.proyecto = proyecto


def vista_datos() -> None:
    st.header("Datos de reconocimiento")
    st.markdown('<p class="section-note">Importe la plantilla Excel o revise las tablas directamente.</p>', unsafe_allow_html=True)
    col1, col2 = st.columns([1, 1])
    with col1:
        st.download_button(
            "Descargar plantilla con ejemplo", crear_plantilla_excel(True),
            file_name="plantilla_geoperfil.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col2:
        excel = st.file_uploader("Importar Excel", type=["xlsx"], label_visibility="collapsed")
        if excel is not None and st.button("Aplicar datos importados", type="primary", use_container_width=True):
            try:
                st.session_state.datos = leer_excel(BytesIO(excel.getvalue()))
                st.session_state.contactos = []
                st.session_state.zonas = []
                st.rerun()
            except (ValueError, KeyError) as exc:
                st.error(str(exc))
    tabla_nombre = st.selectbox("Tabla editable", TABLAS)
    tabla = st.session_state.datos[tabla_nombre]
    editada = st.data_editor(tabla, num_rows="dynamic", use_container_width=True, hide_index=True, key=f"tabla-{tabla_nombre}")
    if st.button("Guardar cambios de tabla"):
        st.session_state.datos[tabla_nombre] = editada
        if tabla_nombre in {"Sondeos", "Intervalos", "Unidades", "Eje"}:
            st.session_state.contactos = []
            st.session_state.zonas = []
        st.success("Tabla actualizada. Las validaciones se han recalculado.")
    _, _, errores, avisos = _datos_geometricos()
    if errores:
        for error in errores:
            st.error(error)
    elif not avisos:
        st.success("Estructura, referencias y rangos basicos correctos.")
    for aviso in avisos:
        st.warning(aviso)


def vista_trazado() -> None:
    st.header("Eje y proyeccion")
    st.markdown('<p class="section-note">Los reconocimientos se proyectan por minima distancia sobre la polilinea.</p>', unsafe_allow_html=True)
    eje = st.data_editor(
        st.session_state.datos["Eje"], num_rows="dynamic", use_container_width=True,
        hide_index=True, key="editor-eje",
    )
    if st.button("Aplicar eje", type="primary"):
        st.session_state.datos["Eje"] = eje.sort_values("orden").reset_index(drop=True)
        st.session_state.contactos = []
        st.session_state.zonas = []
        st.rerun()
    sondeos, dpsh, errores, avisos = _datos_geometricos()
    if errores:
        for error in errores:
            st.error(error)
        return
    fig = go.Figure()
    eje_actual = st.session_state.datos["Eje"].sort_values("orden")
    fig.add_trace(go.Scatter(x=eje_actual["x_m"], y=eje_actual["y_m"], mode="lines+markers", name="Eje",
                             line={"color": "#0A2239", "width": 3}))
    fig.add_trace(go.Scatter(x=sondeos["x_m"], y=sondeos["y_m"], mode="markers+text", text=sondeos["sondeo_id"],
                             textposition="top center", name="Sondeos", marker={"color": "#5C748C", "size": 9}))
    fig.add_trace(go.Scatter(x=dpsh["x_m"], y=dpsh["y_m"], mode="markers+text", text=dpsh["ensayo_id"],
                             textposition="bottom center", name="DPSH", marker={"color": "#E45658", "size": 9, "symbol": "diamond"}))
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
                    sondeos, st.session_state.contactos, st.session_state.zonas
                )
                st.session_state.avisos_topologia = avisos
                st.rerun()
            except RuntimeError as exc:
                st.error(str(exc))

    acciones = st.columns([1, 1, 2])
    if acciones[0].button("Generar borrador automatico", use_container_width=True):
        st.session_state.contactos = contactos_observados(
            sondeos, st.session_state.datos["Intervalos"], st.session_state.datos["Unidades"]
        )
        try:
            st.session_state.zonas, avisos = construir_zonas(sondeos, st.session_state.contactos, [])
            st.session_state.avisos_topologia = avisos
        except RuntimeError as exc:
            st.error(str(exc))
        st.rerun()
    if acciones[1].button("Recalcular zonas", use_container_width=True):
        try:
            st.session_state.zonas, avisos = construir_zonas(
                sondeos, st.session_state.contactos, st.session_state.zonas
            )
            st.session_state.avisos_topologia = avisos
            st.rerun()
        except RuntimeError as exc:
            st.error(str(exc))
    acciones[2].caption(
        "Ajuste activo: los vertices cercanos se vinculan a interfaces observadas; Alt lo omite. "
        "Use Mayusculas + arrastre para desplazar el lienzo y Supr para borrar la seleccion."
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
        contactos_referencia=contactos_referencia,
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
                if respuesta.get("limpiar_interpretacion") and not contactos:
                    zonas, avisos = [], []
                else:
                    zonas, avisos = construir_zonas(
                        sondeos, contactos, list(respuesta.get("zonas", []))
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
            st.info(f"Asigne unidad y trama a {sin_asignar} zonas desde el modo Pintar zona o desde la tabla avanzada.")
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
                    st.session_state.zonas, _ = construir_zonas(
                        sondeos, st.session_state.contactos, st.session_state.zonas
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
    controles = st.columns([1, 1, 1, 2])
    rellenos = controles[0].toggle("Relleno de unidades", True)
    mostrar_dpsh = controles[1].toggle("Ensayos DPSH", True)
    escala = controles[2].number_input("Escala DPSH (m/golpe)", 0.01, 1.0, 0.12, 0.01)
    controles[3].caption("DPSH: lecturas N20 unidas por segmentos rectos; sin correlacion ni interpretacion automatica.")
    figura = crear_figura_perfil(
        st.session_state.proyecto, sondeos, st.session_state.datos["Intervalos"],
        st.session_state.datos["Unidades"], st.session_state.contactos, dpsh,
        st.session_state.datos["Lecturas_DPSH"], zonas=st.session_state.zonas,
        escala_dpsh=escala, mostrar_rellenos=rellenos, mostrar_dpsh=mostrar_dpsh,
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
    proyecto: Proyecto = st.session_state.proyecto
    proyecto.contactos = st.session_state.contactos
    proyecto.zonas = st.session_state.zonas
    datos = st.session_state.datos
    escala = st.number_input("Escala DPSH para PDF (m/golpe)", 0.01, 1.0, 0.12, 0.01)
    figura = crear_figura_perfil(
        proyecto, sondeos, datos["Intervalos"], datos["Unidades"],
        st.session_state.contactos, dpsh, datos["Lecturas_DPSH"],
        zonas=st.session_state.zonas, escala_dpsh=escala,
    )
    col1, col2, col3 = st.columns(3)
    col1.download_button("Proyecto JSON", proyecto_a_json(proyecto, datos), "perfil_geologico.json", "application/json", use_container_width=True)
    col2.download_button("Datos Excel", datos_a_excel(datos), "datos_perfil.xlsx",
                         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    col3.download_button("Perfil HTML", figura.to_html(include_plotlyjs="cdn").encode("utf-8"),
                         "perfil_interactivo.html", "text/html", use_container_width=True)
    col4, col5, col6 = st.columns(3)
    col4.download_button("Contactos CSV", contactos_a_csv(st.session_state.contactos), "contactos.csv", "text/csv", use_container_width=True)
    col5.download_button(
        "Geometria DXF", contactos_a_dxf(st.session_state.contactos, st.session_state.zonas),
        "perfil_geologico.dxf", "application/dxf", use_container_width=True,
    )
    try:
        pdf = figura_perfil_pdf(
            proyecto, sondeos, datos["Intervalos"], datos["Unidades"],
            st.session_state.contactos, dpsh, datos["Lecturas_DPSH"], escala,
            zonas=st.session_state.zonas,
        )
        col6.download_button("Plano PDF", pdf, "perfil_geologico.pdf", "application/pdf", use_container_width=True)
    except ImportError:
        col6.warning("Instale matplotlib para exportar PDF.")
    st.caption("El DXF usa coordenadas locales del perfil: X = abscisa s; Y = cota z.")


def ejecutar_aplicacion() -> None:
    inicializar_estado()
    _estado_sidebar()
    _cabecera()
    paginas = ["Proyecto", "Datos", "Trazado", "Interpretacion", "Perfil", "Exportacion"]
    pagina = st.radio("Navegacion principal", paginas, horizontal=True, label_visibility="collapsed")
    vistas = {
        "Proyecto": vista_proyecto,
        "Datos": vista_datos,
        "Trazado": vista_trazado,
        "Interpretacion": vista_interpretacion,
        "Perfil": vista_perfil,
        "Exportacion": vista_exportacion,
    }
    vistas[pagina]()
