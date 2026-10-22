"""Interfaz Streamlit para cimentaciones superficiales en suelos."""

from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from calculos.servicio import calcular_resultados
from modelos.datos import CapaSuelo, DatosAsientos, DatosHundimiento, DatosProyecto
from utiles.tablas import tabla_resultados
from visualizacion.graficos import grafico_presiones


st.set_page_config(
    page_title="Cimentaciones superficiales",
    page_icon="▦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --navy:#10243a; --coral:#e65358; --line:#dfe5eb; --muted:#66758a; }
    .stApp { color: var(--navy); }
    .block-container { max-width: 1500px; padding-top: 2.25rem; padding-bottom: 3rem; }
    [data-testid="stSidebar"] { border-right: 1px solid var(--line); background: #fff; }
    [data-testid="stSidebar"] .block-container { padding-top: 3.2rem; }
    h1, h2, h3 { color: var(--navy); letter-spacing: 0 !important; }
    h1 { font-size: 2rem !important; margin-bottom: .35rem !important; }
    h2 { font-size: 1.35rem !important; margin-top: 1.2rem !important; }
    h3 { font-size: 1.05rem !important; }
    .eyebrow { color: #c9a1a3; font-size: .72rem; letter-spacing: .08rem; text-transform: uppercase; }
    .subtitle { color: var(--muted); margin-bottom: 1rem; }
    .section-note { color: var(--muted); font-size: .88rem; margin-top: -.45rem; margin-bottom: 1rem; }
    .status-ok { background:#e5f6eb; color:#08783f; padding:.85rem 1rem; border-radius:6px; }
    .status-error { background:#fff0f0; color:#a9272c; padding:.85rem 1rem; border-radius:6px; }
    .stButton > button[kind="primary"] { background:var(--coral); border-color:var(--coral); }
    .stButton > button { border-radius:5px; min-height:2.55rem; }
    [data-baseweb="tab-list"] { gap: 1.2rem; border-bottom: 1px solid var(--line); }
    [data-baseweb="tab"] { padding-left:0; padding-right:0; }
    [data-baseweb="tab-highlight"] { background-color:var(--coral); }
    [data-testid="stMetric"] { border-left: 3px solid var(--coral); padding-left: 1rem; }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 4px; }
    div[data-baseweb="input"] { border-radius: 5px; }
    @keyframes gentle-in { from { opacity:0; transform:translateY(5px); } to { opacity:1; transform:none; } }
    .main .block-container { animation: gentle-in .28s ease-out; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _valor_estado(clave: str, valor):
    return st.session_state.get(clave, valor)


def _capas_desde_tabla(tabla: pd.DataFrame) -> tuple[CapaSuelo, ...]:
    capas: list[CapaSuelo] = []
    for indice, fila in tabla.iterrows():
        if pd.isna(fila.get("E (MPa)")) or pd.isna(fila.get("z inf. (m)")):
            continue
        capas.append(
            CapaSuelo(
                nombre=str(fila.get("Unidad", f"Nivel {indice + 1}")),
                z_superior_m=float(fila["z sup. (m)"]),
                z_inferior_m=float(fila["z inf. (m)"]),
                modulo_mpa=float(fila["E (MPa)"]),
                poisson=float(fila["nu"]),
            )
        )
    return tuple(capas)


def _anchos_desde_tabla(tabla: pd.DataFrame) -> tuple[float, ...]:
    return tuple(float(x) for x in tabla["B* (m)"].dropna().tolist())


st.markdown('<div class="eyebrow">Geo App · Cimentaciones superficiales</div>', unsafe_allow_html=True)
st.title("Presión admisible en suelos")
st.markdown(
    '<div class="subtitle">Réplica trazable de la pestaña SUELOS: hundimiento, asiento elástico y presión de servicio.</div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.subheader("Navegación")
    st.caption("Introduzca los datos en las pestañas y revise el estado límite que gobierna en Resultados.")
    st.divider()
    st.subheader("Acciones")
    calcular = st.button("▦  Calcular caso", type="primary", use_container_width=True)
    st.divider()
    st.subheader("Estado")
    estado = st.empty()
    st.divider()
    st.subheader("Datos")
    descarga = st.empty()
    st.divider()
    st.subheader("Alcance")
    st.caption(
        "Reproduce las expresiones del Excel. Los resultados requieren revisión geotécnica y no sustituyen la comprobación normativa del proyecto."
    )


tab_proyecto, tab_hundimiento, tab_asientos, tab_resultados = st.tabs(
    ["Proyecto", "Hundimiento", "Asientos", "Resultados"]
)

with tab_proyecto:
    st.header("Datos del caso")
    st.markdown('<div class="section-note">Identificación y geometrías que se evaluarán.</div>', unsafe_allow_html=True)
    col_izq, col_der = st.columns([1.35, 1], gap="large")
    with col_izq:
        peticionario = st.text_input(
            "Peticionario",
            value="CONSEJERÍA DE EDUCACIÓN - JUNTA DE EXTREMADURA",
            key="peticionario",
        )
        trabajo = st.text_input(
            "Trabajo",
            value="GIMNASIO EN COLEGIO PÚBLICO PRINCIPE DE ASTURIAS - MONTIJO",
            key="trabajo",
        )
        expediente = st.text_input("Expediente", value="6/C555/005", key="expediente")
    with col_der:
        st.markdown("#### Anchos equivalentes")
        st.caption("La hoja original evalúa cinco valores de B*.")
        anchos_df = st.data_editor(
            pd.DataFrame({"B* (m)": [1.5, 1.8, 2.0, 2.5, 3.0]}),
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            column_config={
                "B* (m)": st.column_config.NumberColumn(min_value=0.05, step=0.1, format="%.2f")
            },
            key="tabla_anchos",
        )

with tab_hundimiento:
    st.header("Presión vertical de hundimiento")
    st.markdown(
        '<div class="section-note">Parámetros característicos y factores de influencia trasladados de la hoja SUELOS.</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        st.markdown("#### Situación y geometría")
        situacion_drenaje = st.selectbox(
            "Situación de dimensionado",
            ["Persistente a largo plazo", "Transitoria a corto plazo (sin drenaje)"],
        )
        forma = st.selectbox("Forma de la cimentación", ["Rectangular", "Circular"])
        profundidad_base = st.number_input(
            "Profundidad de la base D (m)", min_value=0.0, value=0.5, step=0.1
        )
        situacion_seguridad = st.selectbox(
            "Situación para gamma_R",
            ["Situación persistente", "Situación transitoria", "Situación extraordinaria"],
            index=1,
        )
        longitud_hundimiento = st.number_input(
            "Longitud equivalente corrida L* (m)", min_value=1.0, value=1000.0, step=10.0
        )
    with c2:
        st.markdown("#### Resistencia del terreno")
        phi = st.number_input("Ángulo de rozamiento phi' (°)", 0.0, 89.0, 30.0, 0.5)
        cohesion = st.number_input("Cohesión c' / cu (kPa)", min_value=0.0, value=0.0, step=5.0)
        cu_aumenta = st.toggle("cu aumenta linealmente con la profundidad", value=False)
        cu_col1, cu_col2 = st.columns(2)
        with cu_col1:
            cu_z0 = st.number_input("z inicial (m)", value=0.0, step=0.5, disabled=not cu_aumenta)
            cu_0 = st.number_input("cu inicial (kPa)", value=50.0, step=5.0, disabled=not cu_aumenta)
        with cu_col2:
            cu_z1 = st.number_input("z final (m)", value=10.0, step=0.5, disabled=not cu_aumenta)
            cu_1 = st.number_input("cu final (kPa)", value=150.0, step=5.0, disabled=not cu_aumenta)
        considerar_superior = st.toggle(
            "Considerar resistencia del terreno sobre la base", value=False
        )
    with c3:
        st.markdown("#### Agua, sobrecarga y talud")
        nivel_freatico = st.number_input("Nivel freático bajo rasante (m)", min_value=0.0, value=6.6, step=0.1)
        gamma_efectivo = st.number_input("Peso específico efectivo gamma' (kN/m³)", min_value=0.1, value=18.0, step=0.5)
        gamma_aparente = st.number_input("Peso específico aparente (kN/m³)", min_value=0.1, value=18.0, step=0.5)
        flujo = st.toggle("Existe flujo ascendente", value=False)
        gradiente = st.number_input("Gradiente vertical medio", value=0.4, step=0.05, disabled=not flujo)
        considerar_sobrecarga = st.toggle("Considerar sobrecarga al nivel de la base", value=True)
        sobre1, sobre2 = st.columns(2)
        with sobre1:
            gamma_sobrecarga = st.number_input("gamma sobrecarga (kN/m³)", min_value=0.1, value=18.0, step=0.5, disabled=not considerar_sobrecarga)
        with sobre2:
            altura_sobrecarga = st.number_input("Altura H (m)", min_value=0.0, value=0.5, step=0.1, disabled=not considerar_sobrecarga)
        beta = st.number_input("Inclinación del terreno beta (°)", 0.0, 89.0, 0.0, 0.5)
        talud_transitorio = st.toggle("Talud transitorio y sin drenaje", value=False)

with tab_asientos:
    st.header("Cálculo elástico de asientos")
    st.markdown(
        '<div class="section-note">Método de Steinbrenner por estratos. E y q se expresan en MPa; los asientos, en cm.</div>',
        unsafe_allow_html=True,
    )
    a1, a2 = st.columns([1, 2], gap="large")
    with a1:
        asiento_admisible = st.number_input(
            "Asiento admisible (cm)", min_value=0.01, value=5.0, step=0.5
        )
        tipo_material_balasto = st.selectbox(
            "Material para el coeficiente de balasto",
            ["Cohesivo", "Granular"],
            help="Selecciona la relación de escala de placa del CTE DB SE-C: E.6 para cohesivos y E.7 para granulares.",
        )
        longitud_asientos = st.number_input(
            "Longitud equivalente corrida (m)", min_value=1.0, value=100.0, step=10.0
        )
        metodo_etiqueta = st.radio(
            "Cálculo bajo el centro",
            ["Convención del Excel", "Superposición B/2 × L/2"],
            help="La primera opción reproduce la macro. La segunda suma cuatro cuadrantes respecto al centro.",
        )
        if metodo_etiqueta == "Convención del Excel":
            st.info("Modo réplica: s_centro = 2 · s_esquina(B, L).")
        else:
            st.warning("Modo revisado: s_centro = 4 · s_esquina(B/2, L/2).")
    with a2:
        st.markdown("#### Perfil deformacional")
        capas_df = st.data_editor(
            pd.DataFrame(
                {
                    "Unidad": ["NIVEL 1", "NIVEL 2"],
                    "z sup. (m)": [0.0, 2.5],
                    "z inf. (m)": [2.5, 10.0],
                    "E (MPa)": [15.0, 1200.0],
                    "nu": [0.30, 0.20],
                }
            ),
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            column_config={
                "Unidad": st.column_config.TextColumn(required=True),
                "z sup. (m)": st.column_config.NumberColumn(min_value=0.0, step=0.5, format="%.2f"),
                "z inf. (m)": st.column_config.NumberColumn(min_value=0.01, step=0.5, format="%.2f"),
                "E (MPa)": st.column_config.NumberColumn(min_value=0.01, step=1.0, format="%.2f"),
                "nu": st.column_config.NumberColumn(min_value=0.0, max_value=0.499, step=0.01, format="%.3f"),
            },
            key="tabla_capas",
        )


proyecto = DatosProyecto(peticionario=peticionario, trabajo=trabajo, expediente=expediente)
try:
    anchos = _anchos_desde_tabla(anchos_df)
    capas = _capas_desde_tabla(capas_df)
    datos_hundimiento = DatosHundimiento(
        situacion_drenaje=situacion_drenaje,
        forma=forma,
        anchos_m=anchos,
        profundidad_base_m=profundidad_base,
        nivel_freatico_m=nivel_freatico,
        flujo_ascendente=flujo,
        gradiente_vertical=gradiente,
        inclinacion_talud_deg=beta,
        talud_transitorio_sin_drenaje=talud_transitorio,
        phi_deg=phi,
        cohesion_kpa=cohesion,
        cu_aumenta_con_profundidad=cu_aumenta,
        cu_z_inicial_m=cu_z0,
        cu_inicial_kpa=cu_0,
        cu_z_final_m=cu_z1,
        cu_final_kpa=cu_1,
        gamma_efectivo_kn_m3=gamma_efectivo,
        gamma_aparente_kn_m3=gamma_aparente,
        considerar_sobrecarga=considerar_sobrecarga,
        gamma_sobrecarga_kn_m3=gamma_sobrecarga,
        altura_sobrecarga_m=altura_sobrecarga,
        considerar_terreno_sobre_base=considerar_superior,
        situacion_seguridad=situacion_seguridad,
        longitud_corrida_m=longitud_hundimiento,
    )
    datos_asientos = DatosAsientos(
        asiento_admisible_cm=asiento_admisible,
        longitud_corrida_m=longitud_asientos,
        capas=capas,
        metodo_centro="excel" if metodo_etiqueta == "Convención del Excel" else "superposicion",
        tipo_material_balasto=tipo_material_balasto,
    )
    resultados, resumen = calcular_resultados(datos_hundimiento, datos_asientos)
    errores: list[str] = []
except (ValueError, TypeError, KeyError) as exc:
    resultados = []
    resumen = {}
    errores = [str(exc)]

if calcular:
    st.session_state["ultima_accion"] = "Cálculo actualizado"

if errores:
    estado.markdown('<div class="status-error">Revise las entradas</div>', unsafe_allow_html=True)
    descarga.empty()
else:
    estado.markdown('<div class="status-ok">Entradas comprobadas</div>', unsafe_allow_html=True)
    tabla_c = tabla_resultados(resultados, "Cuadrada")
    tabla_l = tabla_resultados(resultados, "Corrida")
    combinado = pd.concat(
        [tabla_c.assign(Geometría="Cuadrada"), tabla_l.assign(Geometría="Corrida")],
        ignore_index=True,
    )
    descarga.download_button(
        "↓  Descargar resultados CSV",
        data=combinado.to_csv(index=False).encode("utf-8-sig"),
        file_name="resultados_cimentaciones.csv",
        mime="text/csv",
        use_container_width=True,
    )

with tab_resultados:
    st.header("Presión admisible de servicio")
    st.markdown(
        '<div class="section-note">El valor de servicio es el mínimo entre hundimiento y asientos para cada ancho.</div>',
        unsafe_allow_html=True,
    )
    if errores:
        for error in errores:
            st.error(error)
    else:
        gobernantes = [
            r.limitacion_cuadrada for r in resultados
        ] + [r.limitacion_corrida for r in resultados]
        k1, k2, k3 = st.columns(3)
        k1.metric(
            f"Ksp30 medio · cuadrada · {tipo_material_balasto.lower()}",
            f"{resumen['ksp30_cuadrada_media_mn_m3']:.1f} MN/m³",
        )
        k2.metric(
            f"Ksp30 medio · corrida · {tipo_material_balasto.lower()}",
            f"{resumen['ksp30_corrida_media_mn_m3']:.1f} MN/m³",
        )
        k3.metric("Estado límite dominante", max(set(gobernantes), key=gobernantes.count))
        st.divider()
        vista_c, vista_l = st.tabs(["Zapata cuadrada", "Zapata corrida"])
        with vista_c:
            izquierda, derecha = st.columns([1.1, 1], gap="large")
            with izquierda:
                st.dataframe(
                    tabla_resultados(resultados, "Cuadrada").style.format(
                        {
                            "B* (m)": "{:.2f}",
                            "Hundimiento (MPa)": "{:.3f}",
                            "Asientos (MPa)": "{:.3f}",
                            "Servicio (MPa)": "{:.3f}",
                            "Ksp30 (MN/m³)": "{:.1f}",
                        }
                    ),
                    hide_index=True,
                    use_container_width=True,
                    height=245,
                )
            with derecha:
                st.plotly_chart(grafico_presiones(resultados, "Cuadrada"), use_container_width=True)
        with vista_l:
            izquierda, derecha = st.columns([1.1, 1], gap="large")
            with izquierda:
                st.dataframe(
                    tabla_resultados(resultados, "Corrida").style.format(
                        {
                            "B* (m)": "{:.2f}",
                            "Hundimiento (MPa)": "{:.3f}",
                            "Asientos (MPa)": "{:.3f}",
                            "Servicio (MPa)": "{:.3f}",
                            "Ksp30 (MN/m³)": "{:.1f}",
                        }
                    ),
                    hide_index=True,
                    use_container_width=True,
                    height=245,
                )
            with derecha:
                st.plotly_chart(grafico_presiones(resultados, "Corrida"), use_container_width=True)
        st.caption(
            f"Caso: {proyecto.trabajo or 'Sin denominación'} · Expediente: {proyecto.expediente or 'Sin expediente'}"
        )
