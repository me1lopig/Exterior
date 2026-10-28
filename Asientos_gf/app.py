"""Interfaz Streamlit del calculador de asientos."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from calculos.asientos import calculate_settlement, validate_case
from modelos.datos import AnalysisOptions, Foundation, Layer
from servicios.exportacion import detailed_csv_bytes, export_bundle_bytes, result_manifest
from visualizacion.graficos import (
    contact_pressure_figure,
    settlement_components_figure,
    stress_profile_figure,
    time_figure,
)


st.set_page_config(
    page_title="Asientos de cimentaciones",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --navy:#0b263e; --red:#e45455; --soft:#f0f3f7; --line:#d9dee6; }
    .stApp { color:var(--navy); background:#fff; }
    [data-testid="stSidebar"] { border-right:1px solid var(--line); background:#fff; }
    [data-testid="stSidebar"] > div { padding-top:2rem; }
    h1,h2,h3 { color:var(--navy); letter-spacing:0; }
    h1 { font-size:2rem !important; }
    h2 { font-size:1.35rem !important; margin-top:1.5rem !important; }
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div,
    [data-testid="stNumberInput"] input, [data-testid="stTextInput"] input {
        background:var(--soft) !important; border-color:transparent !important; border-radius:6px !important;
    }
    .stButton > button[kind="primary"] { background:var(--red); border-color:var(--red); border-radius:4px; }
    .stButton > button, .stDownloadButton > button { border-radius:4px; min-height:2.7rem; }
    [data-baseweb="tab-list"] { gap:1.2rem; border-bottom:1px solid var(--line); }
    [data-baseweb="tab"] { padding-left:0; padding-right:0; }
    [aria-selected="true"] { color:var(--red) !important; }
    .metric-strip { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:1px; background:var(--line); border:1px solid var(--line); }
    .metric-cell { background:white; padding:1rem; min-height:86px; }
    .metric-label { color:#697586; font-size:.78rem; }
    .metric-value { color:var(--navy); font-size:1.35rem; font-weight:700; margin-top:.35rem; }
    .status-ok { padding:.85rem 1rem; background:#e8f6ee; color:#187a49; border-left:4px solid #238b57; }
    .status-no { padding:.85rem 1rem; background:#fdecec; color:#a83232; border-left:4px solid var(--red); }
    @media (max-width:800px) { .metric-strip { grid-template-columns:1fr 1fr; } h1 { font-size:1.55rem !important; } }
    </style>
    """,
    unsafe_allow_html=True,
)


DEFAULT_LAYERS = pd.DataFrame([
    {"Nombre": "Arena densa", "Tipo": "granular", "H (m)": 4.0, "gamma (kN/m3)": 18.0,
     "gamma sat (kN/m3)": 20.0, "E (MPa)": 35.0, "nu": 0.30, "Cc": 0.0, "Cr": 0.0,
     "e0": 0.70, "sigma pc (kPa)": 500.0, "cv (m2/ano)": 1.0, "C alfa": 0.0, "Drenaje": "doble"},
    {"Nombre": "Arcilla", "Tipo": "cohesivo", "H (m)": 6.0, "gamma (kN/m3)": 17.5,
     "gamma sat (kN/m3)": 19.5, "E (MPa)": 12.0, "nu": 0.35, "Cc": 0.22, "Cr": 0.04,
     "e0": 0.85, "sigma pc (kPa)": 300.0, "cv (m2/ano)": 0.8, "C alfa": 0.006, "Drenaje": "doble"},
    {"Nombre": "Grava", "Tipo": "granular", "H (m)": 12.0, "gamma (kN/m3)": 20.0,
     "gamma sat (kN/m3)": 22.0, "E (MPa)": 70.0, "nu": 0.25, "Cc": 0.0, "Cr": 0.0,
     "e0": 0.60, "sigma pc (kPa)": 800.0, "cv (m2/ano)": 1.0, "C alfa": 0.0, "Drenaje": "doble"},
])


def layers_from_frame(frame: pd.DataFrame) -> list[Layer]:
    layers: list[Layer] = []
    for _, row in frame.iterrows():
        layers.append(Layer(
            name=str(row["Nombre"]), soil_type=str(row["Tipo"]), thickness_m=float(row["H (m)"]),
            gamma_unsat_kn_m3=float(row["gamma (kN/m3)"]), gamma_sat_kn_m3=float(row["gamma sat (kN/m3)"]),
            e_mpa=float(row["E (MPa)"]), nu=float(row["nu"]), cc=float(row["Cc"]), cr=float(row["Cr"]),
            e0=float(row["e0"]), sigma_pc_kpa=float(row["sigma pc (kPa)"]), cv_m2_year=float(row["cv (m2/ano)"]),
            c_alpha=float(row["C alfa"]), drainage=str(row["Drenaje"]),
        ))
    return layers


if "layers" not in st.session_state:
    st.session_state.layers = DEFAULT_LAYERS
if "result" not in st.session_state:
    st.session_state.result = None
if "case_inputs" not in st.session_state:
    st.session_state.case_inputs = None
if "pore_profile" not in st.session_state:
    st.session_state.pore_profile = pd.DataFrame({"z (m)": [0.0, 2.0, 10.0], "u (kPa)": [0.0, 0.0, 78.48]})


with st.sidebar:
    st.subheader("Navegacion")
    st.caption("Defina la cimentacion, el terreno y las opciones. El calculo solo se ejecuta tras validar todas las entradas.")
    st.divider()
    st.subheader("Acciones")
    calculate_clicked = st.button("Calcular caso", type="primary", use_container_width=True)
    st.divider()
    st.subheader("Estado")
    status_placeholder = st.empty()
    st.divider()
    st.subheader("Informe y datos")
    download_placeholder = st.container()


st.caption("GEOTECNIA · DEFORMACIONES VERTICALES")
st.title("Asientos de cimentaciones")
st.caption("Tensiones de Boussinesq sobre el area real, contacto sin traccion y consolidacion por unidad drenante.")

tab_project, tab_soil, tab_options, tab_results, tab_method = st.tabs([
    "Proyecto y carga", "Suelos", "Calculo", "Resultados", "Metodologia"
])

with tab_project:
    st.header("Datos de la cimentacion")
    left, right = st.columns([1.05, 1])
    with left:
        project_name = st.text_input("Proyecto", value="Cimentacion - Caso 01")
        type_label = st.selectbox("Tipo estructural", ["Zapata", "Losa", "Pozo / caisson"])
        foundation_type = {"Zapata": "zapata", "Losa": "losa", "Pozo / caisson": "pozo"}[type_label]
        shape_label = st.selectbox("Geometria", ["Rectangular", "Circular", "Banda indefinida"])
        shape = {"Rectangular": "rectangular", "Circular": "circular", "Banda indefinida": "banda"}[shape_label]
        d_col, w_col, l_col = st.columns(3)
        embedment = d_col.number_input("Empotramiento D (m)", min_value=0.0, value=1.0, step=0.1)
        if shape == "circular":
            diameter = w_col.number_input("Diametro (m)", min_value=0.1, value=2.0, step=0.1)
            width, length = diameter, diameter
        else:
            width = w_col.number_input("Ancho B (m)", min_value=0.1, value=2.0, step=0.1)
            length = l_col.number_input("Largo L (m)", min_value=0.1, value=3.0 if shape == "rectangular" else 1.0, step=0.1)
            diameter = width
    with right:
        load_mode_label = st.radio("Entrada de la accion vertical", ["Presion", "Fuerza"], horizontal=True)
        load_mode = "presion" if load_mode_label == "Presion" else "fuerza"
        basis_label = st.radio("Referencia de la accion", ["Neta", "Bruta"], horizontal=True)
        basis = "neta" if basis_label == "Neta" else "bruta"
        if load_mode == "presion":
            pressure = st.number_input("Presion vertical (kPa)", value=100.0, step=5.0)
            vertical_load = 0.0
        else:
            vertical_load = st.number_input("Carga vertical N (kN)", value=600.0, step=25.0)
            pressure = 0.0
        moment_cols = st.columns(2)
        mx = moment_cols[0].number_input("Momento Mx (kN m)", value=0.0, step=10.0, disabled=shape == "banda")
        my = moment_cols[1].number_input("Momento My (kN m)", value=0.0, step=10.0, disabled=shape == "banda")
        rigidity_label = st.radio("Comportamiento de la base", ["Flexible", "Rigida"], horizontal=True)
        rigidity = "flexible" if rigidity_label == "Flexible" else "rigida"

with tab_soil:
    st.header("Perfil geotecnico")
    st.caption("La ultima capa se prolonga solo si el bulbo supera la profundidad definida; el programa lo advertira.")
    hydraulic_mode = st.radio(
        "Modelo hidraulico", ["Nivel freatico horizontal", "Perfil piezometrico u(z)", "Sin agua"], horizontal=True
    )
    pore_pressure_points = None
    if hydraulic_mode == "Nivel freatico horizontal":
        water_table = st.number_input(
            "Profundidad del nivel freatico zw (m)", min_value=0.0, value=2.0, step=0.1,
            help="Introduzca 0,00 m para nivel freatico en superficie."
        )
    elif hydraulic_mode == "Perfil piezometrico u(z)":
        water_table = None
        st.session_state.pore_profile = st.data_editor(
            st.session_state.pore_profile, num_rows="dynamic", hide_index=True, use_container_width=True,
            key="pore_profile_editor",
        )
        try:
            pore_pressure_points = tuple(
                (float(row["z (m)"]), float(row["u (kPa)"]))
                for _, row in st.session_state.pore_profile.sort_values("z (m)").iterrows()
            )
        except (TypeError, ValueError, KeyError):
            pore_pressure_points = ()
    else:
        water_table = None
    st.session_state.layers = st.data_editor(
        st.session_state.layers,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Tipo": st.column_config.SelectboxColumn(options=["granular", "cohesivo"], required=True),
            "Drenaje": st.column_config.SelectboxColumn(options=["simple", "doble"], required=True),
        },
        key="soil_editor",
    )
    st.info("Cc, Cr, e0, sigma'pc, cv y C alfa solo se emplean en estratos cohesivos saturados.")

with tab_options:
    st.header("Opciones de calculo")
    c1, c2, c3 = st.columns(3)
    immediate_label = c1.selectbox("Modelo de asiento inmediato", ["Elastico 3D", "Deformacion 1D"])
    immediate_model = "elastico_3d" if immediate_label == "Elastico 3D" else "edometrico_1d"
    dz = c1.number_input("Espesor maximo de subcapa (m)", min_value=0.01, max_value=2.0, value=0.20, step=0.05)
    influence = c2.number_input("Criterio Delta sigma / sigma'v0", min_value=0.01, max_value=0.50, value=0.10, step=0.01)
    max_factor = c2.number_input("Profundidad maxima (veces B)", min_value=5.0, max_value=200.0, value=50.0, step=5.0)
    service_years = c3.number_input("Vida de servicio (anos)", min_value=0.1, value=50.0, step=1.0)
    limit_mm = c3.number_input("Limite definido por el usuario (mm)", min_value=1.0, value=50.0, step=5.0)
    include_primary = st.checkbox("Incluir consolidacion primaria", value=True)
    include_secondary = st.checkbox("Incluir consolidacion secundaria", value=True, disabled=not include_primary)


foundation = Foundation(
    shape=shape, foundation_type=foundation_type, width_m=width, length_m=length, diameter_m=diameter, embedment_m=embedment,
    load_mode=load_mode, pressure_basis=basis, rigidity=rigidity, vertical_load_kn=vertical_load,
    pressure_kpa=pressure, mx_knm=mx, my_knm=my,
)
options = AnalysisOptions(
    dz_m=dz, influence_ratio=influence, max_depth_factor=max_factor, immediate_model=immediate_model,
    include_primary=include_primary, include_secondary=include_secondary and include_primary,
    service_years=service_years, settlement_limit_mm=limit_mm,
)

try:
    layers = layers_from_frame(st.session_state.layers)
except (TypeError, ValueError, KeyError) as exc:
    layers = []
    conversion_error = str(exc)
else:
    conversion_error = ""

issues = validate_case(foundation, layers, options, water_table, pore_pressure_points)
if conversion_error:
    issues.append(type("Issue", (), {"severity": "error", "field": "estratos", "message": conversion_error})())
errors = [item for item in issues if item.severity == "error"]
warnings = [item for item in issues if item.severity == "warning"]

if errors:
    status_placeholder.markdown('<div class="status-no">Entradas pendientes de corregir</div>', unsafe_allow_html=True)
else:
    status_placeholder.markdown('<div class="status-ok">Entradas comprobadas</div>', unsafe_allow_html=True)

if calculate_clicked:
    if errors:
        st.session_state.result = None
        st.error("No se ha ejecutado el calculo:\n\n" + "\n".join(f"- {item.field}: {item.message}" for item in errors))
    else:
        try:
            with st.spinner("Resolviendo tensiones, contacto y consolidacion..."):
                st.session_state.result = calculate_settlement(
                    foundation, layers, options, water_table, pore_pressure_points
                )
                st.session_state.case_inputs = (
                    foundation, layers, options, water_table, pore_pressure_points, project_name
                )
        except ValueError as exc:
            st.session_state.result = None
            st.error(str(exc))

result = st.session_state.result
current_case = (foundation, layers, options, water_table, pore_pressure_points, project_name)
case_changed = st.session_state.case_inputs is not None and current_case != st.session_state.case_inputs
with tab_results:
    st.header("Resultados")
    if result is None:
        st.info("Ejecute el caso desde el panel lateral para mostrar resultados.")
    else:
        if case_changed:
            st.warning("Las entradas han cambiado desde el ultimo calculo. Los resultados mostrados pertenecen al caso guardado; vuelva a calcular.")
        center = result.points[0]
        saved_options_for_result = st.session_state.case_inputs[2]
        compliance = center.total_service_mm <= saved_options_for_result.settlement_limit_mm
        status_class = "status-ok" if compliance else "status-no"
        status_text = "Cumple el limite introducido por el usuario" if compliance else "No cumple el limite introducido por el usuario"
        st.markdown(f'<div class="{status_class}">{status_text}</div>', unsafe_allow_html=True)
        st.markdown(
            f"""<div class="metric-strip">
            <div class="metric-cell"><div class="metric-label">Asiento total · centro</div><div class="metric-value">{center.total_service_mm:.2f} mm</div></div>
            <div class="metric-cell"><div class="metric-label">Resultante neta</div><div class="metric-value">{result.net_resultant_kn:.1f} kN</div></div>
            <div class="metric-cell"><div class="metric-label">Profundidad analizada</div><div class="metric-value">{result.analysis_depth_m:.2f} m</div></div>
            <div class="metric-cell"><div class="metric-label">Contacto bruto qmin / qmax</div><div class="metric-value">{result.pressure_field.gross_pressure_kpa.min():.1f} / {result.pressure_field.gross_pressure_kpa.max():.1f} kPa</div></div>
            </div>""",
            unsafe_allow_html=True,
        )
        st.caption("Esta indicacion no constituye por si sola una comprobacion normativa CTE o Eurocodigo 7.")
        plot_left, plot_right = st.columns(2)
        plot_left.plotly_chart(stress_profile_figure(result), use_container_width=True)
        plot_right.plotly_chart(settlement_components_figure(result), use_container_width=True)
        plot_left.plotly_chart(time_figure(result), use_container_width=True)
        plot_right.plotly_chart(contact_pressure_figure(result), use_container_width=True)
        st.subheader("Resumen por punto")
        st.dataframe(pd.DataFrame([point.__dict__ for point in result.points]), hide_index=True, use_container_width=True)
        st.subheader("Detalle por subcapa")
        st.dataframe(pd.DataFrame(result.slices), hide_index=True, use_container_width=True, height=360)
        if result.warnings:
            st.warning("\n".join(f"- {message}" for message in result.warnings))

with tab_method:
    st.header("Metodologia, alcance y limitaciones")
    st.markdown(
        """
        **Tensiones.** La presion se integra sobre la geometria cargada real mediante el nucleo de Boussinesq. Los rectangulos se subdividen en celdas con integracion cerrada; los circulos emplean cuadratura polar. Las cargas excentricas se equilibran con N, Mx y My y se elimina cualquier traccion de contacto.

        **Base rigida.** Se resuelve una matriz de influencia del semiespacio elastico imponiendo un plano de desplazamientos y equilibrio. No se aplica ningun factor constante de reduccion. En suelos estratificados se usa un modulo armonico equivalente para la redistribucion inicial.

        **Asiento inmediato.** El modo elastico 3D integra la deformacion vertical derivada de la solucion de Boussinesq e incluye el efecto de Poisson. El modo 1D usa Delta sigma z / E y se identifica expresamente como aproximacion edometrica.

        **Consolidacion.** La formulacion logaritmica se aplica exclusivamente a subcapas cohesivas saturadas. Cada estrato conserva su cv, camino de drenaje y t95; la curva temporal suma la respuesta individual. La compresion secundaria comienza en el t95 de cada unidad.

        **Limitaciones.** Se supone estratificacion horizontal, nivel freatico hidrostatico y comportamiento elastico lineal para transmitir tensiones. Para contrastes acusados de rigidez, geometria tridimensional compleja o acoplamiento suelo-estructura dependiente del tiempo debe emplearse un modelo multicapa avanzado o FEM calibrado.
        """
    )
    if result is not None:
        st.subheader("Hipotesis del caso calculado")
        for assumption in result.assumptions:
            st.write("- " + assumption)

if result is not None and st.session_state.case_inputs is not None:
    saved_foundation, saved_layers, saved_options, saved_water, saved_pore_points, saved_project = st.session_state.case_inputs
    manifest = result_manifest(
        result, saved_foundation, saved_layers, saved_options, saved_water, saved_pore_points, saved_project
    )
    with download_placeholder:
        st.download_button(
            "Descargar resultados CSV", detailed_csv_bytes(result), "resultados_asientos.csv", "text/csv", use_container_width=True
        )
        st.download_button(
            "Descargar paquete trazable", export_bundle_bytes(result, manifest), "calculo_asientos_trazable.zip",
            "application/zip", use_container_width=True
        )
elif warnings:
    with download_placeholder:
        st.caption("Revise las advertencias antes de exportar.")
