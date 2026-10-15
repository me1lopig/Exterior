from __future__ import annotations

import pandas as pd
import streamlit as st

from calculations.analysis import evaluate_cases, optimize_geometry, sensitivity_analysis
from calculations.layers import (
    assess_foundation_bulbs,
    assess_relevant_layers,
    check_layer_coverage,
)
from calculations.serviceability import (
    elastic_settlement,
    layered_settlement_2to1,
    spt_allowable_pressure_cte,
    spt_settlement_burland_burbidge,
)
from models.inputs import (
    ActionCase,
    DesignSituation,
    DrainageCondition,
    Foundation,
    FoundationType,
    SoilLayer,
    SoilProfile,
)
from services.field_data import mean_spt_in_cte_zone, normalize_field_data
from services.reporting import generate_docx_report
from visualization.plots import optimization_figure, sensitivity_figure, terms_figure


st.set_page_config(page_title="Zapatas CTE Geotecnia", layout="wide")

st.markdown(
    """
    <style>
    :root { --ink:#0b2239; --muted:#64748b; --coral:#e55353; --line:#d9e0e7; }
    .stApp { background:#ffffff; color:var(--ink); }
    [data-testid="stSidebar"] { background:#fbfcfd; border-right:1px solid var(--line); }
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color:var(--ink); }
    h1, h2, h3 { color:var(--ink); letter-spacing:0 !important; }
    h1 { font-size:2rem !important; margin-bottom:.2rem !important; }
    .block-container { max-width:1440px; padding-top:2rem; }
    .stButton > button[kind="primary"] { background:var(--coral); border-color:var(--coral); }
    .stButton > button { border-radius:4px; min-height:2.65rem; }
    div[data-baseweb="tab-list"] { gap:1.25rem; border-bottom:1px solid var(--line); }
    button[data-baseweb="tab"] { padding-left:0; padding-right:0; }
    [data-testid="stMetric"] { border-left:3px solid var(--coral); padding-left:.8rem; }
    .status-ok { color:#087443; font-weight:700; }
    .status-bad { color:#a9232f; font-weight:700; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _default_actions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Combinacion": "Persistente 1",
                "Situacion": "persistente",
                "V estructura": 1000.0,
                "H_B": 0.0,
                "H_L": 0.0,
                "M_B": 0.0,
                "M_L": 0.0,
            }
        ]
    )


def _default_layers() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Capa": "Estrato 1",
                "Techo m": 0.0,
                "Muro m": 10.0,
                "E oed MPa": 25.0,
                "phi grados": 30.0,
                "cu kPa": None,
                "N SPT": 20.0,
            }
        ]
    )


if "actions_df" not in st.session_state:
    st.session_state.actions_df = _default_actions()
if "layers_df" not in st.session_state:
    st.session_state.layers_df = _default_layers()
if "analysis" not in st.session_state:
    st.session_state.analysis = None


st.caption("ZAPATAS CTE · ANALISIS GEOTECNICO")
st.title("Cimentaciones directas")
st.write(
    "Hundimiento, deslizamiento, servicio y sensibilidad con trazabilidad de hipotesis."
)

tabs = st.tabs(
    [
        "Proyecto y geometria",
        "Terreno",
        "Acciones",
        "Datos de campo",
        "Calculo",
        "Sensibilidad",
        "Resultados",
    ]
)

with tabs[0]:
    st.subheader("Datos del caso")
    p1, p2 = st.columns([2, 1])
    project_name = p1.text_input("Proyecto", "Cimentacion directa - Caso 01")
    project_location = p2.text_input("Localizacion", "")
    project_author = p1.text_input("Autor o revision", "")
    project_notes = p2.text_input("Observaciones", "")

    st.subheader("Geometria")
    g1, g2, g3, g4 = st.columns(4)
    kind_label = g1.selectbox("Tipologia", ["Rectangular", "Corrida", "Circular"])
    kind_map = {
        "Rectangular": FoundationType.RECTANGULAR,
        "Corrida": FoundationType.STRIP,
        "Circular": FoundationType.CIRCULAR,
    }
    kind = kind_map[kind_label]
    width = g2.number_input("B o diametro (m)", min_value=0.10, value=2.00, step=0.10)
    if kind is FoundationType.RECTANGULAR:
        length = g3.number_input("L (m)", min_value=width, value=max(3.0, width), step=0.10)
    elif kind is FoundationType.CIRCULAR:
        length = width
        g3.metric("L equivalente", f"{length:.2f} m")
    else:
        length = 1.0
        g3.metric("Franja de calculo", "1.00 m")
    embedment = g4.number_input("D (m)", min_value=0.0, value=1.0, step=0.10)

    g5, g6, g7, g8 = st.columns(4)
    slope = g5.number_input("Pendiente beta (grados)", min_value=0.0, max_value=44.0, value=0.0)
    surcharge = g6.number_input("Sobrecarga exterior (kPa)", min_value=0.0, value=0.0)
    near_slope = g7.checkbox("Proxima a talud", value=False)
    depth_factors = g8.checkbox("Considerar factores de profundidad", value=True)

    st.subheader("Peso propio geotecnico")
    w1, w2, w3 = st.columns(3)
    include_weight = w1.checkbox("Sumar zapata y tierras a V", value=True)
    footing_thickness = w2.number_input("Canto de zapata (m)", min_value=0.10, value=0.50)
    gamma_concrete = w3.number_input("Peso especifico del hormigon (kN/m3)", min_value=20.0, value=25.0)

with tabs[1]:
    st.subheader("Modelo geotecnico")
    drainage_label = st.segmented_control(
        "Regimen de calculo", ["Drenado", "No drenado"], default="Drenado"
    )
    drainage = (
        DrainageCondition.DRAINED
        if drainage_label == "Drenado"
        else DrainageCondition.UNDRAINED
    )
    s1, s2, s3, s4 = st.columns(4)
    c_eff = s1.number_input("c' (kPa)", min_value=0.0, value=0.0, disabled=drainage is DrainageCondition.UNDRAINED)
    phi = s2.number_input("phi' (grados)", min_value=0.0, max_value=55.0, value=30.0, disabled=drainage is DrainageCondition.UNDRAINED)
    cu0 = s3.number_input("cu0 (kPa)", min_value=0.0, value=50.0, disabled=drainage is DrainageCondition.DRAINED)
    cu_grad = s4.number_input("Gradiente cu (kPa/m)", min_value=0.0, value=0.0, disabled=drainage is DrainageCondition.DRAINED)

    s5, s6, s7, s8 = st.columns(4)
    gamma_ap = s5.number_input("gamma aparente (kN/m3)", min_value=1.0, value=18.0)
    gamma_sat = s6.number_input("gamma saturado (kN/m3)", min_value=9.82, value=20.0)
    water = s7.number_input("Profundidad del nivel freatico (m)", min_value=0.0, value=5.0)
    upward = s8.number_input("Gradiente ascendente iv", min_value=0.0, value=0.0, step=0.05)

    s9, s10, s11, s12 = st.columns(4)
    base_adhesion = s9.number_input("Adhesion garantizada en base (kPa)", min_value=0.0, value=0.0)
    fines = s10.number_input("Finos (% peso)", min_value=0.0, max_value=100.0, value=10.0)
    coarse = s11.number_input("Particulas >20 mm (%)", min_value=0.0, max_value=100.0, value=0.0)
    modulus = s12.number_input("Modulo de deformacion (MPa)", min_value=0.1, value=25.0)
    poisson = st.slider("Coeficiente de Poisson", 0.0, 0.49, 0.30, 0.01)

with tabs[2]:
    st.subheader("Combinaciones de acciones en la base")
    unit_note = "por metro lineal" if kind is FoundationType.STRIP else "totales por zapata"
    st.caption(
        f"Acciones {unit_note}. V estructura no incluye el peso propio calculado en la pestana anterior."
    )
    st.session_state.actions_df = st.data_editor(
        st.session_state.actions_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Situacion": st.column_config.SelectboxColumn(
                options=[item.value for item in DesignSituation], required=True
            ),
            "V estructura": st.column_config.NumberColumn(min_value=0.01),
        },
        key="actions_editor",
    )

with tabs[3]:
    st.subheader("Ensayos SPT o CPT")
    st.caption("CSV admitido: depth_m,N_spt o depth_m,qc_MPa.")
    f1, f2 = st.columns([2, 1])
    field_upload = f1.file_uploader("Perfil de campo", type=["csv"])
    qc_ratio = f2.number_input("Relacion qc/N (MPa)", min_value=0.05, value=0.40, step=0.05)
    terzaghi_correction = f2.checkbox("Correccion de Terzaghi bajo nivel freatico", value=False)

    st.subheader("Estratigrafia para control y asientos")
    st.session_state.layers_df = st.data_editor(
        st.session_state.layers_df,
        num_rows="dynamic",
        use_container_width=True,
        key="layers_editor",
    )

with tabs[4]:
    st.subheader("Barrido y criterios de servicio")
    o1, o2, o3, o4, o5 = st.columns(5)
    b_min = o1.number_input("B minima (m)", min_value=0.10, value=max(0.5, width - 0.5))
    b_max = o2.number_input("B maxima (m)", min_value=b_min, value=max(width + 1.0, b_min))
    l_min = o3.number_input("L minima (m)", min_value=0.10, value=max(width, length - 0.5), disabled=kind is not FoundationType.RECTANGULAR)
    l_max = o4.number_input("L maxima (m)", min_value=l_min, value=max(length + 1.0, l_min), disabled=kind is not FoundationType.RECTANGULAR)
    grid_step = o5.number_input("Paso (m)", min_value=0.05, value=0.25, step=0.05)

    c1, c2, c3, c4 = st.columns(4)
    allowable_settlement = c1.number_input("Asiento admisible (mm)", min_value=1.0, max_value=25.0, value=25.0)
    n_spt_manual = c2.number_input("N SPT medio manual", min_value=1.0, value=20.0)
    influence_depth = c3.number_input("Profundidad ZI bajo base (m)", min_value=0.1, value=max(2.0 * width, 0.1))
    influence_factor = c4.number_input("Factor elastico de influencia", min_value=0.1, value=1.0)

with tabs[5]:
    st.subheader("Analisis de sensibilidad")
    sensitivity_percent = st.slider("Variacion de parametros (%)", 5, 40, 20, 5)
    if st.session_state.analysis is not None:
        sensitivity_data = st.session_state.analysis["sensitivity"]
        st.plotly_chart(sensitivity_figure(sensitivity_data), use_container_width=True)
        st.dataframe(sensitivity_data, use_container_width=True, hide_index=True)
    else:
        st.info("Ejecute el calculo para generar la sensibilidad.")

with st.sidebar:
    st.header("Navegacion")
    st.write("Complete las pestanas y ejecute la envolvente geotecnica.")
    st.divider()
    st.header("Acciones")
    calculate = st.button("Calcular caso y barrido", type="primary", use_container_width=True)
    st.divider()
    st.header("Estado")
    if st.session_state.analysis is None:
        st.write("Pendiente de calculo")
    else:
        status = bool(
            st.session_state.analysis["summary"]["cumple_geotecnia"].all()
            and st.session_state.analysis["bulb_coverage"]["all_covered"]
        )
        css = "status-ok" if status else "status-bad"
        label = "Comprobaciones favorables" if status else "Existe una comprobacion no favorable"
        st.markdown(f'<p class="{css}">{label}</p>', unsafe_allow_html=True)


def _build_layers(frame: pd.DataFrame) -> list[SoilLayer]:
    layers: list[SoilLayer] = []
    for _, row in frame.dropna(subset=["Capa", "Techo m", "Muro m", "E oed MPa"]).iterrows():
        layers.append(
            SoilLayer(
                name=str(row["Capa"]),
                top_depth_m=float(row["Techo m"]),
                bottom_depth_m=float(row["Muro m"]),
                deformation_modulus_mpa=float(row["E oed MPa"]),
                phi_effective_deg=None if pd.isna(row.get("phi grados")) else float(row["phi grados"]),
                cu_kpa=None if pd.isna(row.get("cu kPa")) else float(row["cu kPa"]),
                spt_n=None if pd.isna(row.get("N SPT")) else float(row["N SPT"]),
            )
        )
    return layers


if calculate:
    try:
        soil = SoilProfile(
            drainage=drainage,
            c_effective_kpa=c_eff,
            phi_effective_deg=phi,
            cu0_kpa=cu0,
            cu_gradient_kpa_m=cu_grad,
            gamma_apparent_kn_m3=gamma_ap,
            gamma_saturated_kn_m3=gamma_sat,
            water_table_depth_m=water,
            upward_gradient=upward,
            fines_percent=fines,
            coarse_over_20mm_percent=coarse,
            spt_n_mean=n_spt_manual,
            deformation_modulus_mpa=modulus,
            poisson_ratio=poisson,
        )
        foundation = Foundation(
            kind=kind,
            width_m=width,
            length_m=length,
            embedment_m=embedment,
            ground_slope_deg=slope,
            surcharge_kpa=surcharge,
            base_adhesion_kpa=base_adhesion,
            include_depth_factors=depth_factors,
            near_slope=near_slope,
        )
        cover = max(embedment - footing_thickness, 0.0)
        additional_vertical_kpa = 0.0
        if include_weight:
            additional_vertical_kpa = (
                footing_thickness * gamma_concrete + cover * gamma_ap
            )
        structural_actions: list[ActionCase] = []
        for _, row in st.session_state.actions_df.iterrows():
            structural_actions.append(
                ActionCase(
                    name=str(row["Combinacion"]),
                    situation=DesignSituation(str(row["Situacion"])),
                    vertical_kn=float(row["V estructura"]),
                    horizontal_b_kn=float(row["H_B"]),
                    horizontal_l_kn=float(row["H_L"]),
                    moment_b_knm=float(row["M_B"]),
                    moment_l_knm=float(row["M_L"]),
                )
            )
        action_cases = [
            ActionCase(
                name=action.name,
                situation=action.situation,
                vertical_kn=(
                    action.vertical_kn
                    + foundation.plan_area_m2 * additional_vertical_kpa
                ),
                horizontal_b_kn=action.horizontal_b_kn,
                horizontal_l_kn=action.horizontal_l_kn,
                moment_b_knm=action.moment_b_knm,
                moment_l_knm=action.moment_l_knm,
            )
            for action in structural_actions
        ]
        summary, details = evaluate_cases(soil, foundation, action_cases)
        layers = _build_layers(st.session_state.layers_df)
        layer_assessment = assess_relevant_layers(layers, embedment, width)
        bulb_coverage = assess_foundation_bulbs(
            layers,
            embedment,
            width,
            influence_depth,
        )
        optimization = optimize_geometry(
            soil,
            foundation,
            structural_actions,
            b_min,
            b_max,
            l_min if kind is FoundationType.RECTANGULAR else 1.0,
            l_max if kind is FoundationType.RECTANGULAR else 1.0,
            grid_step,
            additional_vertical_kpa,
        )
        if not optimization.empty:
            optimization["cumple_resistencia"] = optimization["cumple"]
            optimization["perfil_cubre_bulbo"] = [
                bool(
                    check_layer_coverage(
                        layers,
                        embedment,
                        embedment + 1.5 * float(candidate_width),
                        f"Geometria B={float(candidate_width):.2f} m",
                    )["covered"]
                )
                for candidate_width in optimization["B_m"]
            ]
            optimization["cumple"] = (
                optimization["cumple_resistencia"]
                & optimization["perfil_cubre_bulbo"]
            )
        sensitivity = sensitivity_analysis(
            soil,
            foundation,
            action_cases[0],
            sensitivity_percent / 100.0,
        )
        n_spt = n_spt_manual
        field_result = None
        if field_upload is not None:
            normalized = normalize_field_data(pd.read_csv(field_upload), qc_ratio)
            field_result = mean_spt_in_cte_zone(
                normalized,
                embedment,
                details[0]["bearing"].geometry.width_m,
                terzaghi_correction,
                water,
            )
            n_spt = float(field_result["mean_n"])

        first = details[0]["bearing"]
        serviceability: dict[str, object] = {}
        spt_applicable = (
            fines < 35
            and coarse <= 30
            and slope < 5.71
            and action_cases[0].horizontal_kn < 0.10 * action_cases[0].vertical_kn
            and width <= 5.0
            and upward == 0
        )
        if spt_applicable:
            serviceability["q_adm_servicio_SPT_kPa"] = round(
                spt_allowable_pressure_cte(
                    n_spt,
                    first.geometry.width_m,
                    embedment,
                    allowable_settlement,
                ),
                2,
            )
        else:
            serviceability["SPT_CTE"] = "No aplicable por condiciones de 4.3.3"

        pore_pressure = max(embedment - water, 0.0) * soil.gamma_water_kn_m3
        q_effective = max(first.pressure_gross_kpa - pore_pressure, 0.0)
        if fines < 35 and coarse <= 30 and n_spt >= 7:
            bb = spt_settlement_burland_burbidge(
                q_effective,
                first.geometry.width_m,
                first.geometry.length_m,
                n_spt,
                influence_depth,
            )
            serviceability["asiento_Burland_Burbidge_mm"] = round(bb["settlement_mm"], 2)
        serviceability["asiento_elastico_mm"] = round(
            elastic_settlement(
                max(first.pressure_net_kpa, 0.0),
                first.geometry.width_m,
                modulus,
                poisson,
                influence_factor,
            ),
            2,
        )
        settlement_coverage = bulb_coverage["checks"][1]
        if layers and settlement_coverage["covered"]:
            layered = layered_settlement_2to1(
                max(first.pressure_net_kpa, 0.0),
                first.geometry.width_m,
                first.geometry.length_m,
                embedment,
                layers,
                influence_depth,
            )
            serviceability["asiento_estratificado_2a1_mm"] = round(
                layered["settlement_mm"], 2
            )
        else:
            serviceability["asiento_estratificado_2a1"] = (
                "No calculado: la estratigrafia no cubre completamente D a D+ZI"
            )

        project = {
            "name": project_name,
            "location": project_location,
            "author": project_author,
            "notes": project_notes,
        }
        report = generate_docx_report(
            project,
            soil,
            foundation,
            summary,
            details,
            serviceability,
            layer_assessment["warnings"] + bulb_coverage["warnings"],
            bulb_coverage,
        )
        st.session_state.analysis = {
            "soil": soil,
            "foundation": foundation,
            "actions": action_cases,
            "summary": summary,
            "details": details,
            "optimization": optimization,
            "sensitivity": sensitivity,
            "serviceability": serviceability,
            "layers": layers,
            "layer_assessment": layer_assessment,
            "bulb_coverage": bulb_coverage,
            "field_result": field_result,
            "report": report,
        }
        st.success("Calculo completado y memoria actualizada.")
        st.rerun()
    except Exception as exc:
        st.error(f"No se ha podido completar el calculo: {exc}")

with tabs[6]:
    analysis = st.session_state.analysis
    if analysis is None:
        st.info("Ejecute el calculo para mostrar la envolvente de resultados.")
    else:
        summary = analysis["summary"]
        worst_bearing = float(summary["util_hundimiento"].max())
        worst_sliding = float(summary["util_deslizamiento"].max())
        best = analysis["optimization"]
        feasible = best.loc[best["cumple"]] if not best.empty else best
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Maximo hundimiento", f"{worst_bearing:.3f}")
        r2.metric("Maximo deslizamiento", f"{worst_sliding:.3f}")
        r3.metric("Asiento elastico", f"{analysis['serviceability']['asiento_elastico_mm']:.2f} mm")
        r4.metric(
            "Geometria minima",
            "Sin solucion" if feasible.empty else f"{feasible.iloc[0]['B_m']:.2f} x {feasible.iloc[0]['L_m']:.2f} m",
        )
        st.subheader("Envolvente de combinaciones")
        st.dataframe(summary, use_container_width=True, hide_index=True)
        st.plotly_chart(optimization_figure(best), use_container_width=True)
        st.dataframe(best, use_container_width=True, hide_index=True)

        coverage_frame = pd.DataFrame(
            [
                {
                    "Control": check["label"],
                    "Desde (m)": check["required_top_m"],
                    "Hasta (m)": check["required_bottom_m"],
                    "Cobertura": "COMPLETA" if check["covered"] else "INSUFICIENTE",
                }
                for check in analysis["bulb_coverage"]["checks"]
            ]
        )
        st.subheader("Cobertura de los bulbos de presiones")
        st.dataframe(coverage_frame, use_container_width=True, hide_index=True)

        selected_name = st.selectbox("Desglose de combinacion", summary["combinacion"].tolist())
        selected = next(
            item for item in analysis["details"] if item["bearing"].action_name == selected_name
        )
        st.plotly_chart(terms_figure(selected["bearing"].terms_kpa), use_container_width=True)
        f1, f2 = st.columns(2)
        with f1:
            st.write("Factores")
            st.dataframe(
                pd.DataFrame([selected["bearing"].factors]).T.rename(columns={0: "valor"}),
                use_container_width=True,
            )
        with f2:
            st.write("Servicio")
            st.dataframe(
                pd.DataFrame(
                    list(analysis["serviceability"].items()), columns=["resultado", "valor"]
                ),
                use_container_width=True,
                hide_index=True,
            )
        warnings = (
            list(selected["bearing"].warnings)
            + list(analysis["layer_assessment"]["warnings"])
            + list(analysis["bulb_coverage"]["warnings"])
        )
        for warning in warnings:
            st.warning(warning)

        st.download_button(
            "Descargar memoria DOCX",
            data=analysis["report"],
            file_name="memoria_geotecnica_zapata.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
