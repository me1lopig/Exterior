"""Interfaz Streamlit de GeoCorr."""

from __future__ import annotations

import json
from datetime import date

import pandas as pd
import streamlit as st

from calculos.spt import DENSIDADES_CTE, K30_CTE, PERMEABILIDAD_CTE, POISSON_CTE, PROPIEDADES_BASICAS_CTE
from modelos.dominio import GrupoParametro, MetodoInterpolacion, TipoEnsayo, TipoN
from servicios.calculo_tabular import (
    calcular_dmt,
    calcular_molinete,
    calcular_placa,
    calcular_pmt,
    calcular_sismica,
    calcular_spt,
)
from servicios.adopcion import validar_adopciones
from servicios.catalogo import CORRELACIONES, FUENTES, correlaciones_por_grupo
from servicios.estado import ESQUEMAS, inicializar_estado, normalizar_ids
from servicios.informes_docx import generar_informe
from servicios.version import APP_VERSION
from visualizacion.graficos import perfil_resultados
from visualizacion.tema import CSS


st.set_page_config(
    page_title="GeoCorr | Correlaciones geotecnicas",
    page_icon="G",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)
inicializar_estado(st.session_state)


ETIQUETAS_COLUMNAS = {
    "registro_id": "ID",
    "grupo": "Grupo",
    "punto": "Punto / sondeo",
    "profundidad_m": "Profundidad (m)",
    "unidad_geotecnica": "Unidad geotecnica",
    "tipo_suelo": "Tipo de suelo",
    "tipo_n": "Tipo de N",
    "n": "N corregido",
    "porcentaje_mayor_20mm": ">20 mm (%)",
    "diametro_m": "Diametro veleta (m)",
    "altura_m": "Altura veleta (m)",
    "torque_pico_kNm": "Par pico (kN m)",
    "torque_rem_kNm": "Par remoldeado (kN m)",
    "Vs_m_s": "Vs (m/s)",
    "Vp_m_s": "Vp (m/s)",
    "gamma_kN_m3": "gamma (kN/m3)",
    "p0_kPa": "p0 (kPa)",
    "p1_kPa": "p1 (kPa)",
    "u0_kPa": "u0 (kPa)",
    "sigma_v_eff_kPa": "sigma'v (kPa)",
    "EM_MPa": "EM (MPa)",
    "plM_MPa": "plM (MPa)",
    "pf_MPa": "pf (MPa)",
    "alpha": "Factor reologico alpha",
    "p0h_MPa": "Presion horizontal p0 (MPa)",
    "Ev1_MPa": "Ev1 (MPa)",
    "Ev2_MPa": "Ev2 (MPa)",
    "K30_MN_m3": "K30 (MN/m3)",
    "tipo_ensayo": "Tipo de ensayo",
    "k_m_s": "k (m/s)",
    "observaciones": "Observaciones",
}


def grupos_ids() -> list[str]:
    return [g["id"] for g in st.session_state.grupos]


def etiqueta_grupo(grupo_id: str) -> str:
    for grupo in st.session_state.grupos:
        if grupo["id"] == grupo_id:
            return f"{grupo['id']} · {grupo['nombre']}"
    return grupo_id


def editor_datos(tipo: str, grupo_id: str, clave: str) -> pd.DataFrame:
    """Edita las observaciones de un grupo y sincroniza el almacen comun."""
    almacen = st.session_state[f"datos_{tipo}"].copy()
    actual = almacen[almacen["grupo"] == grupo_id].copy() if not almacen.empty else almacen.copy()
    columnas = [c for c in ESQUEMAS[tipo] if c != "grupo"]
    actual = actual.reindex(columns=columnas)
    config: dict[str, object] = {
        "registro_id": st.column_config.TextColumn("ID", disabled=True, width="small"),
        "profundidad_m": st.column_config.NumberColumn("Profundidad (m)", min_value=0.0, step=0.5),
        "tipo_n": st.column_config.SelectboxColumn("Tipo de N", options=[item.value for item in TipoN]),
        "tipo_suelo": st.column_config.SelectboxColumn(
            "Tipo de suelo",
            options=[
                "Grava limpia", "Arena limpia", "Arena con finos", "Limo no cohesivo",
                "Limo cohesivo", "Arcilla", "Relleno", "Roca", "Otro",
            ],
        ),
        "cementado": st.column_config.CheckboxColumn("Suelo cementado"),
        "n": st.column_config.NumberColumn("N corregido", min_value=0.0, step=1.0),
        "porcentaje_mayor_20mm": st.column_config.NumberColumn(">20 mm (%)", min_value=0.0, max_value=100.0),
    }
    for columna in columnas:
        if columna not in config:
            config[columna] = st.column_config.TextColumn(ETIQUETAS_COLUMNAS.get(columna, columna))
    numericas = {
        "diametro_m", "altura_m", "torque_pico_kNm", "torque_rem_kNm", "Vs_m_s", "Vp_m_s",
        "gamma_kN_m3", "p0_kPa", "p1_kPa", "u0_kPa", "sigma_v_eff_kPa", "EM_MPa",
        "plM_MPa", "pf_MPa", "alpha", "p0h_MPa", "Ev1_MPa", "Ev2_MPa", "K30_MN_m3", "k_m_s",
    }
    for columna in numericas.intersection(columnas):
        config[columna] = st.column_config.NumberColumn(ETIQUETAS_COLUMNAS[columna], min_value=0.0, format="%.4g")
    editado = st.data_editor(
        actual,
        key=clave,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config=config,
    )
    editado = normalizar_ids(editado)
    editado.insert(1, "grupo", grupo_id)
    resto = almacen[almacen["grupo"] != grupo_id] if not almacen.empty else almacen
    combinado = pd.concat([resto, editado], ignore_index=True).reindex(columns=ESQUEMAS[tipo])
    st.session_state[f"datos_{tipo}"] = combinado
    return editado


def mostrar_entradas(tipo: str, grupo_id: str) -> None:
    """Muestra la fuente unica de datos sin crear editores concurrentes."""
    almacen = st.session_state[f"datos_{tipo}"]
    vista = almacen[almacen["grupo"] == grupo_id] if not almacen.empty else almacen
    columnas = [c for c in ESQUEMAS[tipo] if c != "grupo"]
    if vista.empty:
        st.info("No hay datos. Introduzcalos en la pestaña Datos.")
    else:
        st.dataframe(vista.reindex(columns=columnas), use_container_width=True, hide_index=True)
    st.caption("Fuente unica de entrada: la edicion se realiza en la pestaña Datos.")


def datos_activos(tipo: str, grupos_activos: list[str]) -> pd.DataFrame:
    df = st.session_state[f"datos_{tipo}"]
    return df[df["grupo"].isin(grupos_activos)].copy() if not df.empty else df.copy()


def guardar_resultados(nuevos: pd.DataFrame) -> None:
    if nuevos.empty:
        return
    existentes = st.session_state.resultados.copy()
    if not existentes.empty:
        for grupo, metodo in nuevos[["grupo", "metodo"]].drop_duplicates().itertuples(index=False):
            existentes = existentes[~((existentes["grupo"] == grupo) & (existentes["metodo"] == metodo))]
    if "adoptado" not in nuevos:
        nuevos["adoptado"] = False
        nuevos["valor_adoptado"] = pd.NA
        nuevos["justificacion"] = ""
    st.session_state.resultados = pd.concat([existentes, nuevos], ignore_index=True)


def mostrar_resultados(df: pd.DataFrame, titulo: str) -> None:
    if df.empty:
        st.info("Todavia no hay resultados para esta seleccion.")
        return
    validos = int((df["estado"] == "Valido").sum())
    condicionados = int((df["estado"] == "Condicionado").sum())
    st.markdown(f'<div class="geo-status">{validos} validos · {condicionados} condicionados · {len(df)} evaluaciones.</div>', unsafe_allow_html=True)
    columnas = [
        "grupo", "punto", "profundidad_m", "unidad_geotecnica", "correlacion_id",
        "parametro", "metodo",
        "valor", "minimo", "maximo", "unidad", "estado", "categoria", "interpolado", "advertencias",
    ]
    st.dataframe(df[columnas], use_container_width=True, hide_index=True)
    st.plotly_chart(perfil_resultados(df[df["estado"] == "Valido"], titulo), use_container_width=True)


def selector_correlaciones(grupo: GrupoParametro, clave: str) -> list[str]:
    disponibles = [
        correlacion
        for correlacion in correlaciones_por_grupo(grupo)
        if correlacion.ensayo == TipoEnsayo.SPT
    ]
    opciones = [c.id for c in disponibles]
    return st.multiselect(
        "Correlaciones",
        opciones,
        default=opciones,
        format_func=lambda cid: f"{CORRELACIONES[cid].nombre} · {cid}",
        key=clave,
    )


with st.sidebar:
    st.markdown('<div class="geo-kicker">GeoCorr</div>', unsafe_allow_html=True)
    st.header("Proyecto")
    st.session_state.proyecto_nombre = st.text_input("Nombre", st.session_state.proyecto_nombre)
    st.session_state.proyecto_localizacion = st.text_input("Localizacion", st.session_state.proyecto_localizacion)
    st.divider()
    st.subheader("Grupos")
    grupo_edicion = st.selectbox("Grupo en edicion", grupos_ids(), format_func=etiqueta_grupo)
    activos = st.multiselect("Grupos en calculo", grupos_ids(), default=grupos_ids(), format_func=etiqueta_grupo)
    with st.expander("Nuevo grupo"):
        nuevo_nombre = st.text_input("Nombre del grupo", key="nuevo_grupo_nombre")
        nuevo_ensayo = st.selectbox("Ensayo principal", [e.value for e in TipoEnsayo], key="nuevo_grupo_ensayo")
        if st.button("Añadir grupo", use_container_width=True):
            if nuevo_nombre.strip():
                numero = max([int(g["id"][1:]) for g in st.session_state.grupos] + [0]) + 1
                st.session_state.grupos.append({"id": f"G{numero:02d}", "nombre": nuevo_nombre.strip(), "ensayo": nuevo_ensayo})
                st.rerun()
            else:
                st.warning("Indique un nombre.")
    if len(st.session_state.grupos) > 1 and st.button("Eliminar grupo en edicion", use_container_width=True):
        st.session_state.grupos = [g for g in st.session_state.grupos if g["id"] != grupo_edicion]
        for tipo in ESQUEMAS:
            df = st.session_state[f"datos_{tipo}"]
            st.session_state[f"datos_{tipo}"] = df[df["grupo"] != grupo_edicion]
        st.rerun()
    st.divider()
    st.subheader("Estado")
    total_registros = sum(len(st.session_state[f"datos_{t}"]) for t in ESQUEMAS)
    st.caption(f"{len(st.session_state.grupos)} grupos · {total_registros} registros")
    st.caption(f"GeoCorr {APP_VERSION} · Entrada manual · Sin CPT/CPTu")


st.markdown('<div class="geo-kicker">Caracterizacion geotecnica</div>', unsafe_allow_html=True)
st.title("Correlaciones de parametros del terreno")
st.markdown(
    '<p class="geo-lead">Calculo trazable desde SPT y ensayos de campo, con control de dominio, unidades e interpolacion.</p>',
    unsafe_allow_html=True,
)

tab_datos, tab_res, tab_def, tab_est, tab_hid, tab_int, tab_comp, tab_bib = st.tabs([
    "Datos", "Resistencia", "Deformabilidad", "Estado", "Hidraulica",
    "Interaccion", "Comparacion", "Bibliografia",
])


with tab_datos:
    st.header("Datos del proyecto")
    st.caption("Los grupos permiten separar sondeos, zonas o campañas sin mezclar automaticamente sus resultados.")
    st.dataframe(pd.DataFrame(st.session_state.grupos), use_container_width=True, hide_index=True)
    tipo_datos = st.selectbox("Tabla de campo", list(ESQUEMAS), format_func=lambda x: {
        "spt": "SPT", "molinete": "Molinete", "sismica": "Sismica", "dmt": "DMT",
        "pmt": "Presiometro", "placa": "Placa de carga", "permeabilidad": "Permeabilidad",
    }[x])
    editor_datos(tipo_datos, grupo_edicion, f"editor_datos_{tipo_datos}_{grupo_edicion}")


with tab_res:
    st.header("Resistencia")
    metodo_res = st.selectbox("Ensayo de origen", ["SPT", "Molinete", "DMT", "Presiometro"], key="metodo_res")
    if metodo_res == "SPT":
        seleccion = selector_correlaciones(GrupoParametro.RESISTENCIA, "corr_res")
        modo = MetodoInterpolacion(st.radio("Tratamiento de tablas", [m.value for m in MetodoInterpolacion], horizontal=True, key="interp_res"))
        mostrar_entradas("spt", grupo_edicion)
        if modo == MetodoInterpolacion.LINEAL:
            st.caption("D.23 se interpola por criterio adoptado de GeoCorr; el CTE publica rangos y no prescribe esta interpolacion.")
        if st.button("Calcular resistencia", type="primary"):
            guardar_resultados(calcular_spt(datos_activos("spt", activos), seleccion, modo))
        resultados = st.session_state.resultados
        mostrar_resultados(resultados[resultados["parametro"].isin(["phi_eff", "qu"])] if not resultados.empty else resultados, "Resistencia desde SPT")
    else:
        mapa = {"Molinete": ("molinete", calcular_molinete), "DMT": ("dmt", calcular_dmt), "Presiometro": ("pmt", calcular_pmt)}
        tipo, funcion = mapa[metodo_res]
        mostrar_entradas(tipo, grupo_edicion)
        if st.button("Calcular resistencia", type="primary", key=f"calc_res_{tipo}"):
            guardar_resultados(funcion(datos_activos(tipo, activos)))
        resultados = st.session_state.resultados
        parametros = ["su_pico", "su_rem", "su", "qu", "plM", "pf"]
        mostrar_resultados(resultados[resultados["parametro"].isin(parametros)] if not resultados.empty else resultados, f"Resistencia · {metodo_res}")


with tab_def:
    st.header("Deformabilidad")
    metodo_def = st.selectbox("Ensayo de origen", ["SPT", "Sismica", "DMT", "Presiometro", "Placa de carga"], key="metodo_def")
    if metodo_def == "SPT":
        seleccion = selector_correlaciones(GrupoParametro.DEFORMABILIDAD, "corr_def")
        modo = MetodoInterpolacion(st.radio("Tratamiento de tablas", [m.value for m in MetodoInterpolacion], horizontal=True, key="interp_def"))
        mostrar_entradas("spt", grupo_edicion)
        if modo == MetodoInterpolacion.LINEAL:
            st.caption("D.23 se interpola por criterio adoptado de GeoCorr; el CTE publica rangos y no prescribe esta interpolacion.")
        if st.button("Calcular deformabilidad", type="primary"):
            guardar_resultados(calcular_spt(datos_activos("spt", activos), seleccion, modo))
    else:
        mapa = {
            "Sismica": ("sismica", calcular_sismica), "DMT": ("dmt", calcular_dmt),
            "Presiometro": ("pmt", calcular_pmt), "Placa de carga": ("placa", calcular_placa),
        }
        tipo, funcion = mapa[metodo_def]
        mostrar_entradas(tipo, grupo_edicion)
        if st.button("Calcular deformabilidad", type="primary", key=f"calc_def_{tipo}"):
            guardar_resultados(funcion(datos_activos(tipo, activos)))
    resultados = st.session_state.resultados
    parametros = ["E", "Es", "Ic", "G0", "E0", "ED", "EM", "E_equiv", "Ev1", "Ev2"]
    mostrar_resultados(resultados[resultados["parametro"].isin(parametros)] if not resultados.empty else resultados, f"Deformabilidad · {metodo_def}")


with tab_est:
    st.header("Estado del terreno")
    origen_estado = st.selectbox("Fuente", ["SPT - CTE D.23", "DMT", "Molinete", "CTE D.24", "CTE D.26", "CTE D.27"])
    if origen_estado == "SPT - CTE D.23":
        mostrar_entradas("spt", grupo_edicion)
        if st.button("Clasificar estado desde SPT", type="primary"):
            guardar_resultados(calcular_spt(
                datos_activos("spt", activos), ["DEF-E-SPT-CTE2019-D23"], MetodoInterpolacion.LITERAL
            ))
        resultados = st.session_state.resultados
        mostrar_resultados(
            resultados[resultados["correlacion_id"] == "DEF-E-SPT-CTE2019-D23"] if not resultados.empty else resultados,
            "Estado orientativo CTE D.23",
        )
    elif origen_estado == "DMT":
        mostrar_entradas("dmt", grupo_edicion)
        if st.button("Calcular indices DMT", type="primary"):
            guardar_resultados(calcular_dmt(datos_activos("dmt", activos)))
        resultados = st.session_state.resultados
        mostrar_resultados(resultados[resultados["parametro"].isin(["ID", "KD", "OCR"])] if not resultados.empty else resultados, "Indices de estado DMT")
    elif origen_estado == "Molinete":
        mostrar_entradas("molinete", grupo_edicion)
        if st.button("Calcular sensibilidad", type="primary"):
            guardar_resultados(calcular_molinete(datos_activos("molinete", activos)))
        resultados = st.session_state.resultados
        mostrar_resultados(resultados[resultados["parametro"] == "St"] if not resultados.empty else resultados, "Sensibilidad")
    elif origen_estado == "CTE D.24":
        clase = st.selectbox("Clase de suelo", list(POISSON_CTE))
        st.metric("Coeficiente de Poisson orientativo", f"{POISSON_CTE[clase]:.2f}")
        st.caption("Valor categorial de referencia; no es un resultado medido.")
    elif origen_estado == "CTE D.26":
        clase = st.selectbox("Clase de suelo", list(DENSIDADES_CTE))
        valores = DENSIDADES_CTE[clase]
        st.table(pd.DataFrame([{"Parametro": "gamma_sat", "Minimo": valores["gamma_sat"][0], "Maximo": valores["gamma_sat"][1], "Unidad": "kN/m3"}, {"Parametro": "gamma_d", "Minimo": valores["gamma_d"][0], "Maximo": valores["gamma_d"][1], "Unidad": "kN/m3"}]))
    else:
        clase = st.selectbox("Clase de suelo", list(PROPIEDADES_BASICAS_CTE))
        valores = PROPIEDADES_BASICAS_CTE[clase]
        st.table(pd.DataFrame([{"Parametro": "gamma", "Minimo": valores["gamma"][0], "Maximo": valores["gamma"][1], "Unidad": "kN/m3"}, {"Parametro": "phi", "Minimo": valores["phi"][0], "Maximo": valores["phi"][1], "Unidad": "grados"}]))


with tab_hid:
    st.header("Hidraulica")
    origen_hid = st.radio("Fuente", ["Ensayo in situ", "CTE D.28"], horizontal=True)
    if origen_hid == "Ensayo in situ":
        datos = st.session_state.datos_permeabilidad
        datos = datos[datos["grupo"] == grupo_edicion] if not datos.empty else datos
        mostrar_entradas("permeabilidad", grupo_edicion)
        st.caption("El valor se conserva como resultado del ensayo de campo; no se transforma mediante una correlacion adicional.")
        if not datos.empty:
            st.dataframe(datos[["punto", "profundidad_m", "tipo_ensayo", "k_m_s"]], use_container_width=True, hide_index=True)
    else:
        clase = st.selectbox("Tipo de suelo", list(PERMEABILIDAD_CTE))
        minimo, maximo = PERMEABILIDAD_CTE[clase]
        st.table(pd.DataFrame([{"Tipo": clase, "k minimo (m/s)": minimo, "k maximo (m/s)": maximo}]))
        st.caption("Intervalo categorial: no se interpola.")


with tab_int:
    st.header("Interaccion suelo-estructura")
    origen_int = st.radio("Fuente", ["Placa de carga", "CTE D.29"], horizontal=True)
    if origen_int == "Placa de carga":
        mostrar_entradas("placa", grupo_edicion)
        if st.button("Calcular parametros de placa", type="primary"):
            guardar_resultados(calcular_placa(datos_activos("placa", activos)))
        resultados = st.session_state.resultados
        mostrar_resultados(resultados[resultados["parametro"].isin(["K30", "Ev2/Ev1"])] if not resultados.empty else resultados, "Placa de carga")
    else:
        clase = st.selectbox("Tipo y estado del suelo", list(K30_CTE))
        minimo, maximo = K30_CTE[clase]
        st.table(pd.DataFrame([{"Tipo": clase, "K30 minimo (MN/m3)": minimo, "K30 maximo (MN/m3)": maximo}]))
        st.caption("K30 corresponde a la placa de referencia; no equivale directamente al balasto de una cimentacion real.")


with tab_comp:
    st.header("Comparacion y seleccion")
    resultados = st.session_state.resultados.copy()
    if resultados.empty:
        st.info("Ejecute al menos un calculo para comparar resultados.")
    else:
        filtro_parametro = st.multiselect("Parametros", sorted(resultados["parametro"].dropna().unique()), default=sorted(resultados["parametro"].dropna().unique()))
        vista = resultados[resultados["parametro"].isin(filtro_parametro)].copy()
        editado = st.data_editor(
            vista,
            use_container_width=True,
            hide_index=True,
            disabled=[c for c in vista.columns if c not in {"adoptado", "valor_adoptado", "justificacion"}],
            column_config={
                "adoptado": st.column_config.CheckboxColumn("Adoptar"),
                "valor_adoptado": st.column_config.NumberColumn("Valor adoptado"),
                "justificacion": st.column_config.TextColumn("Justificacion tecnica", width="large"),
            },
            key="editor_resultados",
        )
        candidato = st.session_state.resultados.copy()
        candidato.loc[editado.index, ["adoptado", "valor_adoptado", "justificacion"]] = editado[["adoptado", "valor_adoptado", "justificacion"]]
        errores_adopcion = validar_adopciones(candidato)
        if errores_adopcion:
            for error in errores_adopcion:
                st.error(error)
        else:
            st.session_state.resultados = candidato
        st.plotly_chart(perfil_resultados(vista[vista["estado"] == "Valido"], "Comparacion de resultados"), use_container_width=True)
        entradas_informe = {tipo: st.session_state[f"datos_{tipo}"] for tipo in ESQUEMAS}
        informe = generar_informe(
            st.session_state.proyecto_nombre,
            st.session_state.proyecto_localizacion,
            st.session_state.grupos,
            st.session_state.resultados,
            entradas=entradas_informe,
        )
        st.download_button("Descargar informe DOCX", informe, file_name=f"informe_correlaciones_{date.today().isoformat()}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        proyecto_json = json.dumps({
            "version": APP_VERSION,
            "proyecto": st.session_state.proyecto_nombre,
            "localizacion": st.session_state.proyecto_localizacion,
            "grupos": st.session_state.grupos,
            "entradas": {tipo: json.loads(df.to_json(orient="records")) for tipo, df in entradas_informe.items()},
            "resultados": json.loads(st.session_state.resultados.to_json(orient="records")),
        }, ensure_ascii=True, indent=2)
        st.download_button("Descargar ficha del proyecto JSON", proyecto_json, file_name="proyecto_geocorr.json", mime="application/json")


with tab_bib:
    st.header("Bibliografia y trazabilidad")
    st.caption("Cada resultado conserva el identificador de la correlacion y la fuente empleada.")
    for correlacion in CORRELACIONES.values():
        fuente = FUENTES[correlacion.fuente_id]
        with st.expander(f"{correlacion.nombre} · {correlacion.id}"):
            st.markdown(
                f"**Parametro:** `{correlacion.parametro}`  \\n"
                f"**Ensayo:** {correlacion.ensayo.value}  \\n"
                f"**Formula:** {correlacion.formula}  \\n"
                f"**Dominio:** {correlacion.dominio}  \\n"
                f"**Fuente:** [{fuente.referencia}]({fuente.url})"
            )
            st.caption(f"Version: {correlacion.version_metodo} · Nivel: {correlacion.nivel_confianza} · Salida: {correlacion.unidades_salida}")
