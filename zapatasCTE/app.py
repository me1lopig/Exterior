from __future__ import annotations

import pandas as pd
import streamlit as st

from calculations.analysis import (
    admissible_capacity_grid,
    evaluate_cases,
)
from calculations.layers import vertical_overburden_from_layers
from models.inputs import (
    ActionCase,
    DesignSituation,
    DrainageCondition,
    Foundation,
    FoundationType,
    SoilLayer,
    SoilProfile,
)
from services.exporting import capacity_grid_to_excel
from services.reporting import generate_capacity_report
from visualization.plots import optimization_figure, terms_figure


st.set_page_config(page_title="Carga admisible CTE DB SE-C", layout="wide")
st.markdown(
    """
    <style>
    :root { --ink:#0b2239; --muted:#64748b; --coral:#e55353; --line:#d9e0e7; }
    .stApp { background:#ffffff; color:var(--ink); }
    [data-testid="stSidebar"] { background:#fbfcfd; border-right:1px solid var(--line); }
    h1, h2, h3 { color:var(--ink); letter-spacing:0 !important; }
    h1 { font-size:2rem !important; margin-bottom:.2rem !important; }
    .block-container { max-width:1480px; padding-top:2rem; }
    .stButton > button[kind="primary"] { background:var(--coral); border-color:var(--coral); }
    .stButton > button { border-radius:4px; min-height:2.65rem; }
    div[data-baseweb="tab-list"] { gap:1.15rem; border-bottom:1px solid var(--line); }
    button[data-baseweb="tab"] { padding-left:0; padding-right:0; }
    [data-testid="stMetric"] { border-left:3px solid var(--coral); padding-left:.8rem; }
    .status-ok { color:#087443; font-weight:700; }
    .status-bad { color:#a9232f; font-weight:700; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _default_layers() -> pd.DataFrame:
    return pd.DataFrame(
        [{
            "Capa": "Terreno 1", "Espesor m": 20.0,
            "c' kPa": 0.0, "phi' grados": 30.0,
            "gamma kN/m3": 18.0, "gamma sat kN/m3": 20.0,
            "E_s MPa": 25.0, "Poisson": 0.30,
        }]
    )


def _default_cu_profile() -> pd.DataFrame:
    return pd.DataFrame([
        {"Profundidad z m": 0.0, "cu kPa": 50.0},
        {"Profundidad z m": 20.0, "cu kPa": 100.0},
    ])


def _default_actions() -> pd.DataFrame:
    return pd.DataFrame([{
        "Combinacion": "Persistente 1", "Situacion": "persistente",
        "V estructura": 1000.0, "H_B": 0.0, "H_L": 0.0,
        "M_B": 0.0, "M_L": 0.0,
    }])


for key, default in (
    ("layers_df", _default_layers()),
    ("cu_df", _default_cu_profile()),
    ("actions_df", _default_actions()),
):
    if key not in st.session_state:
        st.session_state[key] = default
if "analysis" not in st.session_state:
    st.session_state.analysis = None


def _required_float(row: pd.Series, column: str, layer_name: str) -> float:
    value = row.get(column)
    if pd.isna(value):
        raise ValueError(f"Falta '{column}' en la capa {layer_name}")
    return float(value)


def _normalize_layers_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Migrate previous top/bottom tables to the thickness-only interface."""
    normalized = frame.copy()
    if "Espesor m" not in normalized.columns:
        if {"Techo m", "Muro m"}.issubset(normalized.columns):
            normalized["Espesor m"] = normalized["Muro m"] - normalized["Techo m"]
        else:
            normalized["Espesor m"] = pd.NA
    return normalized.drop(columns=["Techo m", "Muro m"], errors="ignore")


def _build_layers(frame: pd.DataFrame) -> list[SoilLayer]:
    clean = frame.dropna(how="all")
    if clean.empty:
        raise ValueError("Debe definir al menos una capa de terreno")
    layers: list[SoilLayer] = []
    names: set[str] = set()
    top_depth = 0.0
    for index, row in clean.iterrows():
        name = str(row.get("Capa", "")).strip()
        if not name or name.lower() == "nan":
            raise ValueError(f"Falta el nombre de la capa en la fila {index + 1}")
        if name in names:
            raise ValueError(f"El nombre de capa '{name}' esta repetido")
        names.add(name)
        thickness = _required_float(row, "Espesor m", name)
        if thickness <= 0:
            raise ValueError(f"El espesor de la capa '{name}' debe ser positivo")
        bottom_depth = top_depth + thickness
        layers.append(SoilLayer(
            name=name,
            top_depth_m=top_depth,
            bottom_depth_m=bottom_depth,
            deformation_modulus_mpa=_required_float(row, "E_s MPa", name),
            phi_effective_deg=_required_float(row, "phi' grados", name),
            c_effective_kpa=_required_float(row, "c' kPa", name),
            gamma_apparent_kn_m3=_required_float(row, "gamma kN/m3", name),
            gamma_saturated_kn_m3=_required_float(row, "gamma sat kN/m3", name),
            poisson_ratio=_required_float(row, "Poisson", name),
        ))
        top_depth = bottom_depth
    return layers


def _build_cu_profile(frame: pd.DataFrame) -> tuple[tuple[float, float], ...]:
    clean = frame.dropna(how="all")
    if len(clean) < 2:
        raise ValueError("El perfil cu(z) requiere al menos dos puntos")
    points = [
        (float(row["Profundidad z m"]), float(row["cu kPa"]))
        for _, row in clean.iterrows()
        if not pd.isna(row.get("Profundidad z m")) and not pd.isna(row.get("cu kPa"))
    ]
    if len(points) != len(clean):
        raise ValueError("Hay filas incompletas en el perfil cu(z)")
    return tuple(sorted(points))


def _build_actions(frame: pd.DataFrame, added_vertical_kn: float) -> list[ActionCase]:
    clean = frame.dropna(how="all")
    if clean.empty:
        raise ValueError("Debe definir al menos una combinacion de acciones")
    return [ActionCase(
        name=str(row["Combinacion"]),
        situation=DesignSituation(str(row["Situacion"])),
        vertical_kn=float(row["V estructura"]) + added_vertical_kn,
        horizontal_b_kn=float(row["H_B"]),
        horizontal_l_kn=float(row["H_L"]),
        moment_b_knm=float(row["M_B"]),
        moment_l_knm=float(row["M_L"]),
    ) for _, row in clean.iterrows()]


st.caption("CTE DB SE-C · CARGA ADMISIBLE DE CIMENTACIONES DIRECTAS")
st.title("Capacidad geotecnica B-L")
st.write("Hundimiento y asiento elastico estratificado, con comprobacion opcional de acciones.")

tabs = st.tabs([
    "Proyecto y geometria", "Terrenos", "Calculo B-L", "Acciones opcionales",
    "Resultados", "Formulaciones CTE",
])

with tabs[0]:
    st.subheader("Datos del caso")
    p1, p2 = st.columns(2)
    project_name = p1.text_input("Proyecto", "Carga admisible - Caso 01")
    project_location = p2.text_input("Localizacion", "")
    project_author = p1.text_input("Autor o revision", "")
    project_notes = p2.text_input("Observaciones", "")
    st.subheader("Cimentacion y entorno")
    g1, g2, g3, g4 = st.columns(4)
    kind_label = g1.selectbox("Tipologia", ["Rectangular", "Circular", "Corrida"])
    kind = {"Rectangular": FoundationType.RECTANGULAR,
            "Circular": FoundationType.CIRCULAR,
            "Corrida": FoundationType.STRIP}[kind_label]
    embedment = g2.number_input("Cota de apoyo D (m)", min_value=0.0, value=1.0, step=0.10)
    slope = g3.number_input("Pendiente beta (grados)", min_value=0.0, max_value=44.0, value=0.0)
    surcharge = g4.number_input("Sobrecarga exterior (kPa)", min_value=0.0, value=0.0)
    g5, g6 = st.columns(2)
    near_slope = g5.checkbox("Cimentacion proxima a talud", value=False)
    depth_factors = g6.checkbox("Considerar factores de profundidad", value=True)
    st.subheader("Peso propio a descontar de la carga admisible estructural")
    w1, w2, w3 = st.columns(3)
    include_weight = w1.checkbox("Descontar zapata y tierras", value=True)
    footing_thickness = w2.number_input("Canto de zapata (m)", min_value=0.10, value=0.50)
    gamma_concrete = w3.number_input("Peso especifico del hormigon (kN/m3)", min_value=20.0, value=25.0)

with tabs[1]:
    st.subheader("Estratigrafia")
    t1, t2, t3, t4 = st.columns(4)
    drainage_label = t1.segmented_control(
        "Regimen de calculo", ["Drenado", "No drenado"], default="Drenado"
    )
    drainage = (
        DrainageCondition.DRAINED
        if drainage_label == "Drenado"
        else DrainageCondition.UNDRAINED
    )
    water_table = t2.number_input(
        "Nivel freatico desde superficie (m)", min_value=0.0, value=5.0
    )
    upward_gradient = t3.number_input(
        "Gradiente hidraulico ascendente i", min_value=0.0, value=0.0, step=0.05
    )
    st.session_state.layers_df = _normalize_layers_frame(st.session_state.layers_df)
    if drainage is DrainageCondition.UNDRAINED:
        st.session_state.layers_df.loc[:, "phi' grados"] = 0.0
    st.caption(
        "Las capas se introducen consecutivamente mediante su espesor. "
        "E_s y Poisson se emplean en Steinbrenner."
    )
    st.session_state.layers_df = st.data_editor(
        st.session_state.layers_df, num_rows="dynamic", use_container_width=True,
        column_config={
            "Espesor m": st.column_config.NumberColumn(min_value=0.01),
            "phi' grados": st.column_config.NumberColumn(min_value=0.0, max_value=59.9),
            "Poisson": st.column_config.NumberColumn(min_value=0.0, max_value=0.49, step=0.01),
            "E_s MPa": st.column_config.NumberColumn(min_value=0.01),
        },
        disabled=["phi' grados"] if drainage is DrainageCondition.UNDRAINED else False,
        key="layers_editor_v4",
    )
    layer_names = [str(v) for v in st.session_state.layers_df.get("Capa", pd.Series(dtype=str)).dropna() if str(v).strip()]
    bearing_layer_name = t4.selectbox(
        "Estrato representativo para hundimiento", layer_names or ["Sin capas"]
    )
    use_cu_profile = False
    cu_constant = 50.0
    if drainage is DrainageCondition.UNDRAINED:
        st.subheader("Resistencia no drenada")
        use_cu_profile = st.checkbox(
            "Considerar variacion de cu con la profundidad", value=True
        )
        if use_cu_profile:
            st.caption(
                "z es la profundidad absoluta desde la superficie; "
                "cu se interpola entre puntos sin extrapolar."
            )
            st.session_state.cu_df = st.data_editor(
                st.session_state.cu_df, num_rows="dynamic", use_container_width=True,
                column_config={
                    "Profundidad z m": st.column_config.NumberColumn(min_value=0.0),
                    "cu kPa": st.column_config.NumberColumn(min_value=0.0),
                }, key="cu_editor_v4")
        else:
            cu_constant = st.number_input(
                "Resistencia no drenada constante cu (kPa)",
                min_value=0.01,
                value=50.0,
            )

with tabs[2]:
    st.subheader("Malla de dimensiones y criterio de asiento")
    c1, c2, c3, c4, c5 = st.columns(5)
    b_min = c1.number_input("B minima (m)", min_value=0.10, value=1.0, step=0.10)
    b_max = c2.number_input("B maxima (m)", min_value=b_min, value=3.0, step=0.10)
    if kind is FoundationType.RECTANGULAR:
        l_min = c3.number_input(
            "L minima (m)", min_value=b_min, value=max(1.0, b_min), step=0.10
        )
        l_max = c4.number_input("L maxima (m)", min_value=l_min, value=4.0, step=0.10)
    else:
        l_min = l_max = 1.0
        c3.metric("Relacion geometrica", "L=B" if kind is FoundationType.CIRCULAR else "L=1 m")
        c4.metric("Unidad", "por zapata" if kind is FoundationType.CIRCULAR else "por metro")
    grid_step = c5.number_input("Paso B-L (m)", min_value=0.05, value=0.25, step=0.05)
    s1, s2 = st.columns(2)
    allowable_settlement = s1.number_input("Asiento admisible (mm)", min_value=1.0, value=25.0, step=1.0)
    influence_depth = s2.number_input("Profundidad de influencia ZI bajo la base (m)", min_value=0.10, value=max(2.0 * b_max, 0.10), step=0.10)
    st.info("La carga admisible se calcula para carga vertical centrada; gobierna el menor limite entre ELU y asiento.")

with tabs[3]:
    st.subheader("Comprobacion de una geometria con acciones")
    check_actions = st.checkbox("Activar comprobacion con acciones", value=False)
    a1, a2 = st.columns(2)
    check_width = a1.number_input("B de comprobacion (m)", min_value=0.10, value=2.0)
    if kind is FoundationType.RECTANGULAR:
        check_length = a2.number_input("L de comprobacion (m)", min_value=check_width, value=max(3.0, check_width))
    elif kind is FoundationType.CIRCULAR:
        check_length = check_width
        a2.metric("Diametro", f"{check_width:.2f} m")
    else:
        check_length = 1.0
        a2.metric("Franja", "1.00 m")
    if check_actions:
        st.caption("Se comprueban hundimiento, excentricidad y contacto. No se comprueba deslizamiento.")
        st.session_state.actions_df = st.data_editor(
            st.session_state.actions_df, num_rows="dynamic", use_container_width=True,
            column_config={"Situacion": st.column_config.SelectboxColumn(
                options=[item.value for item in DesignSituation], required=True)},
            key="actions_editor_v3")

with st.sidebar:
    st.header("Navegacion")
    st.write("Defina el terreno y la malla B-L antes de ejecutar el calculo.")
    st.divider()
    calculate = st.button("Calcular capacidad B-L", type="primary", use_container_width=True)
    st.divider()
    st.header("Estado")
    if st.session_state.analysis is None:
        st.write("Pendiente de calculo")
    else:
        valid = bool(st.session_state.analysis["grid"]["perfil_cubre_bulbos"].all())
        css = "status-ok" if valid else "status-bad"
        label = "Perfil suficiente" if valid else "Existen bulbos sin caracterizar"
        st.markdown(f'<p class="{css}">{label}</p>', unsafe_allow_html=True)


if calculate:
    try:
        layers = _build_layers(st.session_state.layers_df)
        selected_layer = next(layer for layer in layers if layer.name == bearing_layer_name)
        cu_profile = (
            _build_cu_profile(st.session_state.cu_df)
            if drainage is DrainageCondition.UNDRAINED and use_cu_profile
            else ()
        )
        overburden = vertical_overburden_from_layers(
            layers,
            embedment,
            water_table,
            drainage is DrainageCondition.DRAINED,
        )
        soil = SoilProfile(
            drainage=drainage,
            c_effective_kpa=selected_layer.c_effective_kpa,
            phi_effective_deg=(
                0.0
                if drainage is DrainageCondition.UNDRAINED
                else selected_layer.phi_effective_deg or 0.0
            ),
            cu0_kpa=(
                cu_profile[0][1]
                if cu_profile
                else cu_constant if drainage is DrainageCondition.UNDRAINED else 0.0
            ),
            cu_profile=cu_profile,
            gamma_apparent_kn_m3=selected_layer.gamma_apparent_kn_m3,
            gamma_saturated_kn_m3=selected_layer.gamma_saturated_kn_m3,
            water_table_depth_m=water_table,
            upward_gradient=upward_gradient,
            overburden_soil_kpa=overburden,
        )
        template_length = b_min if kind is FoundationType.CIRCULAR else (1.0 if kind is FoundationType.STRIP else max(l_min, b_min))
        template = Foundation(
            kind=kind, width_m=b_min, length_m=template_length,
            embedment_m=embedment, ground_slope_deg=slope,
            surcharge_kpa=surcharge, include_depth_factors=depth_factors,
            near_slope=near_slope,
        )
        cover = max(embedment - footing_thickness, 0.0)
        additional_vertical_kpa = (
            footing_thickness * gamma_concrete + cover * selected_layer.gamma_apparent_kn_m3
            if include_weight else 0.0
        )
        grid, grid_details = admissible_capacity_grid(
            soil, template, layers, b_min, b_max, l_min, l_max, grid_step,
            allowable_settlement, influence_depth, additional_vertical_kpa)
        if grid.empty:
            raise ValueError("La malla B-L no contiene geometrías calculables")

        action_summary = action_details = None
        check_foundation = Foundation(
            kind=kind, width_m=check_width, length_m=check_length,
            embedment_m=embedment, ground_slope_deg=slope,
            surcharge_kpa=surcharge, include_depth_factors=depth_factors,
            near_slope=near_slope,
        )
        if check_actions:
            actions = _build_actions(
                st.session_state.actions_df,
                check_foundation.plan_area_m2 * additional_vertical_kpa,
            )
            action_summary, action_details = evaluate_cases(soil, check_foundation, actions)

        project = {"name": project_name, "location": project_location,
                   "author": project_author, "notes": project_notes}
        report = generate_capacity_report(
            project=project, soil=soil, bearing_layer_name=bearing_layer_name,
            layers=layers, cu_profile=cu_profile, foundation_template=template,
            allowable_settlement_mm=allowable_settlement,
            influence_depth_m=influence_depth, capacity_grid=grid,
            action_summary=action_summary, action_details=action_details,
        )
        excel = capacity_grid_to_excel(
            grid, st.session_state.layers_df,
            st.session_state.cu_df if cu_profile else None,
        )
        st.session_state.analysis = {
            "soil": soil, "layers": layers, "cu_profile": cu_profile,
            "grid": grid, "grid_details": grid_details,
            "action_summary": action_summary,
            "action_details": action_details, "report": report, "excel": excel,
        }
        st.success("Malla B-L calculada e informe actualizado.")
        st.rerun()
    except Exception as exc:
        st.error(f"No se ha podido completar el calculo: {exc}")


with tabs[4]:
    analysis = st.session_state.analysis
    if analysis is None:
        st.info("Ejecute el calculo para mostrar las capacidades admisibles.")
    else:
        grid = analysis["grid"]
        r1, r2 = st.columns(2)
        r1.metric("Geometrias calculadas", str(len(grid)))
        r2.metric("Geometrias con perfil completo", str(int(grid["perfil_cubre_bulbos"].sum())))
        st.plotly_chart(optimization_figure(grid), use_container_width=True)
        display_grid = grid[[
            "B_m", "L_m", "q_d_kpa", "q_adm_asiento_bruta_kpa",
            "q_limite_bruta_kpa", "Q_limite_estructura_kn",
            "criterio_gobernante", "perfil_cubre_bulbos",
        ]].rename(columns={
            "B_m": "B (m)", "L_m": "L (m)",
            "q_d_kpa": "qd ELU (kPa)",
            "q_adm_asiento_bruta_kpa": "qd ELS (kPa)",
            "q_limite_bruta_kpa": "qadm (kPa)",
            "Q_limite_estructura_kn": "Nadm (kN)",
            "criterio_gobernante": "Criterio gobernante",
            "perfil_cubre_bulbos": "Perfil completo",
        }).round(2)
        display_grid["Perfil completo"] = display_grid["Perfil completo"].map(
            {True: "SI", False: "NO"}
        )
        st.dataframe(display_grid, use_container_width=True, hide_index=True)
        options = [f"B={row.B_m:.2f} m · L={row.L_m:.2f} m" for row in grid.itertuples()]
        selected_index = options.index(st.selectbox("Desglose de geometria", options))
        selected_detail = analysis["grid_details"][selected_index]
        b1, b2 = st.columns(2)
        with b1:
            st.plotly_chart(terms_figure(selected_detail["bearing"].terms_kpa), use_container_width=True)
        with b2:
            settlement = selected_detail["settlement"]
            if settlement is None:
                st.warning("No hay asiento admisible: perfil insuficiente o tipologia no compatible.")
            else:
                st.write("Aportacion por estrato para una presion neta unitaria")
                st.dataframe(pd.DataFrame(settlement["unit_pressure_result"]["components"]), use_container_width=True, hide_index=True)
        if analysis["action_summary"] is not None:
            st.subheader("Comprobacion opcional con acciones")
            st.dataframe(analysis["action_summary"], use_container_width=True, hide_index=True)
        d1, d2 = st.columns(2)
        d1.download_button("Descargar memoria DOCX", data=analysis["report"],
                           file_name="memoria_carga_admisible.docx",
                           mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                           use_container_width=True)
        d2.download_button("Descargar tablas XLSX", data=analysis["excel"],
                           file_name="carga_admisible_B_L.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)

with tabs[5]:
    st.subheader("Formulaciones implementadas")
    st.caption("Referencia: CTE DB SE-C, apartados 2.4, 4.3 y Anejo F.1.")
    st.markdown("**Geometria efectiva con excentricidad**")
    st.latex(r"B^*=B-2|e_B| \qquad L^*=L-2|e_L|")
    st.latex(r"e_B=\frac{M_B}{V} \qquad e_L=\frac{M_L}{V}")
    st.markdown("**Presion de hundimiento caracteristica**")
    st.latex(r"q_h=c_kN_cs_cd_ci_ct_c+q_{0k}N_qs_qd_qi_qt_q+\frac{1}{2}\gamma_kB^*N_\gamma s_\gamma d_\gamma i_\gamma t_\gamma")
    st.markdown("**Factores de capacidad de carga**")
    st.latex(r"N_q=\frac{1+\sin\phi'}{1-\sin\phi'}e^{\pi\tan\phi'}")
    st.latex(r"N_c=\frac{N_q-1}{\tan\phi'} \qquad N_\gamma=1.5(N_q-1)\tan\phi'")
    st.markdown("**Resistencia de calculo**")
    st.latex(r"q_d=\frac{q_h}{\gamma_R}")
    st.write("Para hundimiento: gamma_R=3,0 en situación persistente o transitoria y 2,0 en extraordinaria.")
    st.markdown("**Asiento elastico estratificado**")
    st.write("Se emplea Steinbrenner por superposicion de capas. Es un método analitico, no una expresion normativa del CTE.")
    st.latex(r"s=\sum_i\left[w_i(z_{i,\mathrm{sup}})-w_i(z_{i,\mathrm{inf}})\right]")
    st.latex(r"q_{\mathrm{adm,s}}=\frac{s_{\mathrm{adm}}}{s(1\ \mathrm{kPa})}")
    st.markdown("**Presion y carga limite**")
    st.latex(r"q_{\mathrm{lim}}=\min(q_d,q_{\mathrm{adm,s,bruta}}) \qquad Q_{\mathrm{lim}}=q_{\mathrm{lim}}A")
    st.warning("La selección de parámetros característicos representativos corresponde al técnico responsable.")
