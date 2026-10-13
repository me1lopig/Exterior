"""Interfaz Streamlit para estabilidad de taludes temporales."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from math import radians, tan

import pandas as pd
import streamlit as st

from slope_stability_app.calculations import run_sensitivity, search_critical_surfaces
from slope_stability_app.models import AnalysisConfig, ProjectData, SlopeGeometry, Soil, SoilProfile, SweepConfig
from slope_stability_app.services import audit_case_inputs, audit_sweep_inputs, build_report
from slope_stability_app.utils.tables import slices_dataframe
from slope_stability_app.visualization import section_figure, sensitivity_figure


@st.cache_data(show_spinner=False)
def _cached_analysis(geometry: SlopeGeometry, profile: SoilProfile, config: AnalysisConfig):
    return search_critical_surfaces(geometry, profile, config)


@st.cache_data(show_spinner=False)
def _cached_sensitivity(
    geometry: SlopeGeometry,
    profile: SoilProfile,
    config: AnalysisConfig,
    sweep: SweepConfig,
) -> pd.DataFrame:
    return run_sensitivity(geometry, profile, config, sweep)


def _page_style() -> None:
    st.markdown(
        """
        <style>
        :root { --ink:#1D2D44; --muted:#6B778C; --line:#DCE2EA; --accent:#E05252; --soft:#F7F9FC; }
        .stApp { background:#FFFFFF; color:var(--ink); }
        [data-testid="stHeader"] { background:rgba(255,255,255,.94); }
        [data-testid="stSidebar"] { background:#FFFFFF; border-right:1px solid var(--line); }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.55rem; }
        [data-testid="stSidebar"] h2 { font-size:1.05rem; letter-spacing:0; margin-bottom:.2rem; }
        [data-testid="stSidebar"] hr { margin:.75rem 0; }
        .block-container { max-width:1520px; padding-top:1.15rem; padding-bottom:3rem; }
        h1, h2, h3 { color:var(--ink); letter-spacing:0 !important; }
        h1 { font-size:2rem !important; font-weight:750 !important; margin-bottom:.05rem !important; }
        h2 { font-size:1.3rem !important; margin-top:.35rem !important; }
        h3 { font-size:.98rem !important; }
        .app-kicker { color:var(--accent); font-size:.72rem; font-weight:750; text-transform:uppercase; letter-spacing:.08em; }
        .app-subtitle { color:var(--muted); margin-top:-.15rem; margin-bottom:.75rem; max-width:980px; }
        .section-rule { border-top:1px solid var(--line); margin:1rem 0; }
        [data-testid="stMetric"] { background:transparent; border-bottom:2px solid var(--line); padding:.15rem .1rem .55rem; }
        [data-testid="stMetricValue"] { font-size:1.55rem; color:var(--ink); }
        .stButton>button, .stDownloadButton>button { border-radius:4px; font-weight:650; min-height:2.45rem; }
        .stButton>button[kind="primary"] { background:var(--accent); border-color:var(--accent); }
        div[data-baseweb="tab-list"] { gap:.15rem; border-bottom:1px solid var(--line); }
        button[data-baseweb="tab"] { padding:.65rem .85rem; color:var(--muted); }
        button[data-baseweb="tab"][aria-selected="true"] { color:var(--ink); border-bottom-color:var(--accent); }
        div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:3px; }
        div[data-testid="stExpander"] { border-color:var(--line); border-radius:3px; }
        div[data-testid="stAlert"] { border-radius:3px; }
        .workspace-title { font-size:1.35rem; font-weight:730; color:var(--ink); margin:.85rem 0 .1rem; }
        .workspace-copy { color:var(--muted); font-size:.86rem; margin-bottom:.8rem; }
        .sidebar-label { color:var(--muted); font-size:.76rem; text-transform:uppercase; font-weight:700; letter-spacing:.06em; }
        .technical-note { color:var(--muted); font-size:.83rem; line-height:1.45; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _soil_inputs(prefix: str, title: str, defaults: tuple[float, float, float, float]) -> Soil:
    st.markdown(f"#### {title}")
    name = st.text_input("Nombre", value=title, key=f"{prefix}_name")
    c1, c2 = st.columns(2)
    gamma_dry = c1.number_input("Peso unitario seco (kN/m3)", 10.0, 30.0, defaults[0], 0.1, key=f"{prefix}_gd")
    gamma_sat = c2.number_input("Peso unitario saturado (kN/m3)", 10.0, 30.0, defaults[1], 0.1, key=f"{prefix}_gs")
    c3, c4 = st.columns(2)
    cohesion = c3.number_input("Cohesion efectiva c' (kPa)", 0.0, 200.0, defaults[2], 0.5, key=f"{prefix}_c")
    friction = c4.number_input("Rozamiento efectivo phi' (deg)", 0.0, 49.0, defaults[3], 0.5, key=f"{prefix}_phi")
    return Soil(name, gamma_dry, gamma_sat, cohesion, friction)


def _status(fs: float, target: float) -> tuple[str, str]:
    if fs >= target:
        return "Sobre el objetivo", "normal"
    if fs >= 1.0:
        return "Bajo el objetivo", "off"
    return "FS inferior a 1,00", "inverse"


def main() -> None:
    st.set_page_config(page_title="GeoSlope | Taludes temporales", page_icon="📐", layout="wide")
    _page_style()
    st.markdown('<div class="app-kicker">GeoSlope · Equilibrio limite 2D</div>', unsafe_allow_html=True)
    st.title("Estabilidad de taludes temporales")
    st.markdown(
        '<div class="app-subtitle">Fellenius y Bishop simplificado para geometria altura-pendiente, uno o dos suelos y nivel freatico horizontal.</div>',
        unsafe_allow_html=True,
    )

    tabs = st.tabs(
        [
            "Proyecto y geometria",
            "Suelos",
            "Calculo",
            "Sensibilidad",
            "Resultados",
            "Visualizacion",
            "Dovelas",
        ]
    )

    with tabs[0]:
        st.markdown('<div class="workspace-title">Datos del caso</div>', unsafe_allow_html=True)
        st.markdown('<div class="workspace-copy">Defina la referencia del proyecto y la geometria basica del talud.</div>', unsafe_allow_html=True)
        left, right = st.columns([0.9, 1.1], gap="large")
        with left:
            project_name = st.text_input("Proyecto", "Talud temporal - Caso 01")
            location = st.text_input("Localizacion", "")
            author = st.text_input("Autor / revision", "")
            notes = st.text_area("Observaciones", "", height=82)
        with right:
            c1, c2 = st.columns(2)
            height = c1.number_input("Altura H (m)", 1.0, 50.0, 8.0, 0.25)
            angle = c2.number_input(
                "Pendiente (deg)",
                10.0,
                85.0,
                45.0,
                1.0,
                help="Angulo de la cara respecto a la horizontal.",
            )
            c3, c4 = st.columns(2)
            water = c3.number_input(
                "Cota del nivel freatico (m)",
                0.0,
                float(height),
                min(3.0, float(height)),
                0.25,
            )
            target_factor = c4.number_input(
                "FS objetivo",
                0.50,
                3.00,
                1.30,
                0.05,
                help="Criterio definido por el usuario; no se asigna automaticamente a una norma.",
            )
            st.caption(f"Desarrollo horizontal de la cara: {height / max(tan(radians(angle)), 1e-9):.2f} m")

    with tabs[1]:
        st.markdown('<div class="workspace-title">Modelo estratigrafico</div>', unsafe_allow_html=True)
        st.markdown('<div class="workspace-copy">Introduzca parametros efectivos de Mohr-Coulomb y espesores verticales medidos desde coronacion.</div>', unsafe_allow_html=True)
        two_soils = st.toggle("Activar segundo suelo", value=False)
        s1, s2 = st.columns(2, gap="large")
        with s1:
            upper_soil = _soil_inputs("upper", "Suelo superior", (18.0, 20.0, 5.0, 28.0))
        with s2:
            if two_soils:
                lower_soil = _soil_inputs("lower", "Suelo inferior", (19.0, 21.0, 12.0, 32.0))
                default_upper_thickness = min(3.0, float(height) / 2)
                tc1, tc2 = st.columns(2)
                upper_thickness = tc1.number_input(
                    "Espesor superior desde coronacion (m)",
                    value=default_upper_thickness,
                    step=0.1,
                    help="Espesor vertical medido hacia abajo desde z=H.",
                    key="upper_thickness",
                )
                lower_thickness = tc2.number_input(
                    "Espesor inferior dentro de H (m)",
                    value=float(height) - default_upper_thickness,
                    step=0.1,
                    help="Espesor entre el contacto y el pie; el estrato continua bajo z=0.",
                    key="lower_thickness",
                )
                interface = float(height) - float(upper_thickness)
                total_thickness = float(upper_thickness) + float(lower_thickness)
                thickness_difference = float(height) - total_thickness
                if upper_thickness <= 0 or lower_thickness <= 0:
                    st.error("Los espesores de ambos suelos deben ser mayores que cero.")
                elif abs(thickness_difference) > max(1e-6 * float(height), 1e-6):
                    if thickness_difference > 0:
                        st.error(f"La estratigrafia no cubre H: faltan {thickness_difference:.2f} m.")
                    else:
                        st.error(f"La estratigrafia supera H: existe un exceso de {-thickness_difference:.2f} m.")
                else:
                    st.success(f"Espesores comprobados: {total_thickness:.2f} m = H.")
                st.caption(f"Contacto horizontal en z={interface:.2f} m. El suelo inferior continua bajo el pie.")
            else:
                st.markdown("#### Perfil homogeneo")
                st.markdown(
                    f'<p class="technical-note">El suelo ocupa toda la altura ({float(height):.2f} m) y continua bajo el pie.</p>',
                    unsafe_allow_html=True,
                )
                lower_soil = None
                interface = 0.0
                upper_thickness = float(height)
                lower_thickness = 0.0

    with tabs[2]:
        st.markdown('<div class="workspace-title">Control del analisis</div>', unsafe_allow_html=True)
        st.markdown('<div class="workspace-copy">Ajuste la discretizacion y la densidad de busqueda de superficies circulares.</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        slices = c1.number_input("Numero de dovelas", 10, 100, 30, 5)
        search_level = c2.selectbox("Densidad de busqueda", ["Rapida", "Equilibrada", "Detallada"], index=1)
        gamma_water = c3.number_input("Peso unitario del agua (kN/m3)", 9.0, 10.5, 9.81, 0.01)
        with st.expander("Control numerico y dominio de busqueda"):
            e1, e2, e3 = st.columns(3)
            tolerance = e1.number_input("Tolerancia Bishop", 1e-7, 1e-2, 1e-5, format="%.1e")
            iterations = e2.number_input("Iteraciones maximas", 20, 300, 100, 10)
            min_depth_ratio = e3.number_input("Profundidad minima / H", 0.02, 0.40, 0.08, 0.01)
        st.info("La busqueda es discreta. Conviene contrastar el minimo con mayor densidad y numero de dovelas.")

    with tabs[3]:
        st.markdown('<div class="workspace-title">Barrido parametrico</div>', unsafe_allow_html=True)
        st.markdown('<div class="workspace-copy">Varie la pendiente, la posicion del nivel freatico o ambas variables.</div>', unsafe_allow_html=True)
        v1, v2 = st.columns(2, gap="large")
        with v1:
            vary_angle = st.checkbox("Variar pendiente", value=True)
            ac1, ac2, ac3 = st.columns(3)
            angle_min = ac1.number_input("Min. (deg)", 10.0, 85.0, max(10.0, float(angle) - 10), 1.0, disabled=not vary_angle)
            angle_max = ac2.number_input("Max. (deg)", 10.0, 85.0, min(85.0, float(angle) + 10), 1.0, disabled=not vary_angle)
            angle_steps = ac3.number_input("Pasos", 2, 15, 5, 1, disabled=not vary_angle, key="angle_steps")
        with v2:
            vary_water = st.checkbox("Variar nivel freatico", value=True)
            wc1, wc2, wc3 = st.columns(3)
            water_min = wc1.number_input("Min. (m)", 0.0, float(height), 0.0, 0.25, disabled=not vary_water)
            water_max = wc2.number_input("Max. (m)", 0.0, float(height), float(height), 0.25, disabled=not vary_water)
            water_steps = wc3.number_input("Pasos", 2, 15, 5, 1, disabled=not vary_water, key="water_steps")
        sensitivity_level = st.selectbox("Densidad de busqueda del barrido", ["Rapida", "Equilibrada", "Detallada"], index=0)
        cases = (int(angle_steps) if vary_angle else 1) * (int(water_steps) if vary_water else 1)
        st.caption(f"Combinaciones previstas: {cases}. Cada combinacion busca su propia superficie critica.")

    project = ProjectData(project_name, location, author, notes)
    geometry = SlopeGeometry(float(height), float(angle), float(water))
    profile = SoilProfile(upper_soil, lower_soil, float(interface))
    config = AnalysisConfig(
        slices=int(slices),
        search_level=search_level,
        gamma_water=float(gamma_water),
        bishop_tolerance=float(tolerance),
        bishop_max_iterations=int(iterations),
        min_depth_ratio=float(min_depth_ratio),
        target_factor=float(target_factor),
    )
    sweep = SweepConfig(
        vary_angle,
        float(angle_min),
        float(angle_max),
        int(angle_steps),
        vary_water,
        float(water_min),
        float(water_max),
        int(water_steps),
    )
    case_issues = audit_case_inputs(
        project,
        geometry,
        profile,
        config,
        float(upper_thickness),
        float(lower_thickness),
    )
    sweep_issues = audit_sweep_inputs(sweep, geometry.height)
    case_errors = [issue for issue in case_issues if issue.level == "error"]
    sweep_errors = [issue for issue in sweep_issues if issue.level == "error"]
    all_issues = case_issues + sweep_issues

    with st.sidebar:
        st.markdown("## Navegacion")
        st.caption("Use las pestañas superiores para introducir datos, revisar resultados y consultar la seccion critica.")
        st.divider()
        st.markdown("## Acciones")
        run_base = st.button(
            "Calcular caso base",
            type="primary",
            use_container_width=True,
            icon=":material/calculate:",
            disabled=bool(case_errors),
        )
        run_sweep = st.button(
            "Ejecutar sensibilidad",
            use_container_width=True,
            icon=":material/grid_view:",
            disabled=bool(case_errors or sweep_errors),
        )

    if run_base:
        try:
            with st.spinner("Buscando superficies criticas..."):
                st.session_state.analysis = _cached_analysis(geometry, profile, config)
                st.session_state.analysis_inputs = (project, geometry, profile, config)
                st.session_state.pop("sensitivity", None)
                st.session_state.pop("sensitivity_inputs", None)
        except (ArithmeticError, ValueError, RuntimeError) as exc:
            st.error(str(exc))
    if run_sweep:
        try:
            with st.spinner(f"Resolviendo {cases} combinaciones..."):
                sweep_config = replace(config, search_level=sensitivity_level)
                st.session_state.sensitivity = _cached_sensitivity(geometry, profile, sweep_config, sweep)
                st.session_state.sensitivity_inputs = (geometry, profile, sweep_config, sweep)
                st.session_state.analysis = _cached_analysis(geometry, profile, config)
                st.session_state.analysis_inputs = (project, geometry, profile, config)
        except (ArithmeticError, ValueError, RuntimeError) as exc:
            st.error(str(exc))

    result = st.session_state.get("analysis")
    sensitivity = st.session_state.get("sensitivity")
    stored_inputs = st.session_state.get("analysis_inputs")
    inputs_changed = stored_inputs is not None and stored_inputs[1:] != (geometry, profile, config)

    with st.sidebar:
        st.divider()
        st.markdown("## Estado")
        if case_errors:
            st.error("Corrija los errores del caso para calcular.")
        elif sweep_errors:
            st.warning("Caso base valido; revise el barrido de sensibilidad.")
        elif inputs_changed:
            st.warning("Las entradas han cambiado desde el ultimo calculo.")
        else:
            st.success("Entradas comprobadas")
        if all_issues:
            with st.expander(
                f"Revision: {len(case_errors) + len(sweep_errors)} errores · "
                f"{sum(issue.level == 'warning' for issue in all_issues)} avisos"
            ):
                for issue in all_issues:
                    if issue.level == "error":
                        st.error(issue.message)
                    else:
                        st.warning(issue.message)
        st.caption(f"H={geometry.height:.2f} m · beta={geometry.angle_deg:.1f} deg · NF={geometry.water_elevation:.2f} m")
        st.divider()
        st.markdown("## Informe y datos")
        if result is not None and stored_inputs is not None:
            report_project, report_geometry, report_profile, report_config = stored_inputs
            report_bytes = build_report(report_project, report_geometry, report_profile, report_config, result, sensitivity)
            safe_name = "".join(char if char.isalnum() or char in "-_" else "_" for char in report_project.name).strip("_") or "talud"
            st.download_button(
                "Descargar informe DOCX",
                data=report_bytes,
                file_name=f"informe_{safe_name}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                icon=":material/description:",
            )
            if sensitivity is not None:
                st.download_button(
                    "Descargar sensibilidad CSV",
                    data=sensitivity.to_csv(index=False, float_format="%.6f").encode("utf-8-sig"),
                    file_name=f"sensibilidad_{safe_name}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    icon=":material/download:",
                )
        else:
            st.caption("Calcule el caso base para habilitar el informe.")
        st.divider()
        st.markdown("## Alcance")
        st.caption("Equilibrio limite 2D · superficies circulares · Mohr-Coulomb · presion hidrostatica. No incluye sismo, sobrecargas, anclajes ni etapas constructivas.")

    with tabs[0]:
        st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
        st.markdown("### Vista previa")
        st.plotly_chart(section_figure(geometry, profile), use_container_width=True, config={"displaylogo": False})

    with tabs[1]:
        st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
        profile_rows = [
            {
                "Suelo": profile.upper.name,
                "Espesor en H (m)": profile.upper_thickness(geometry.height),
                "gamma seco (kN/m3)": profile.upper.gamma_dry,
                "gamma sat. (kN/m3)": profile.upper.gamma_sat,
                "c' (kPa)": profile.upper.cohesion,
                "phi' (deg)": profile.upper.friction_deg,
            }
        ]
        if profile.lower is not None:
            profile_rows.append(
                {
                    "Suelo": profile.lower.name,
                    "Espesor en H (m)": profile.lower_thickness_within_slope(geometry.height),
                    "gamma seco (kN/m3)": profile.lower.gamma_dry,
                    "gamma sat. (kN/m3)": profile.lower.gamma_sat,
                    "c' (kPa)": profile.lower.cohesion,
                    "phi' (deg)": profile.lower.friction_deg,
                }
            )
        st.dataframe(pd.DataFrame(profile_rows).style.format(precision=2), use_container_width=True, hide_index=True)

    with tabs[2]:
        st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
        if all_issues:
            st.markdown("### Revision de entradas")
            for issue in all_issues:
                if issue.level == "error":
                    st.error(issue.message)
                else:
                    st.warning(issue.message)
        else:
            st.success("Datos del caso y del barrido comprobados sin inconsistencias.")
        with st.expander("Hipotesis del modelo"):
            st.markdown(
                """
                - Analisis bidimensional por metro de ancho y superficies circulares.
                - Resistencia efectiva Mohr-Coulomb y presion intersticial hidrostatica.
                - Fellenius omite fuerzas entre dovelas; Bishop simplificado itera equilibrio de momentos.
                - El minimo obtenido depende de la familia discreta de circulos explorada.
                """
            )

    with tabs[3]:
        st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
        st.markdown("### Resultados del barrido")
        if sensitivity is None:
            st.info("Configure el barrido y pulse 'Ejecutar sensibilidad' en el panel lateral.")
        else:
            st.plotly_chart(sensitivity_figure(sensitivity), use_container_width=True, config={"displaylogo": False})
            min_row = sensitivity.loc[sensitivity["FS Bishop"].idxmin()]
            max_row = sensitivity.loc[sensitivity["FS Bishop"].idxmax()]
            s1, s2, s3 = st.columns(3)
            s1.metric("FS Bishop minimo", f"{min_row['FS Bishop']:.3f}")
            s2.metric("FS Bishop maximo", f"{max_row['FS Bishop']:.3f}")
            s3.metric("Amplitud", f"{max_row['FS Bishop'] - min_row['FS Bishop']:.3f}")
            st.dataframe(
                sensitivity.style.format(
                    {
                        "Pendiente (deg)": "{:.2f}",
                        "Nivel freatico (m)": "{:.2f}",
                        "FS Fellenius": "{:.3f}",
                        "FS Bishop": "{:.3f}",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    with tabs[4]:
        st.markdown('<div class="workspace-title">Resumen del caso base</div>', unsafe_allow_html=True)
        st.markdown('<div class="workspace-copy">Factores de seguridad minimos dentro de la familia de circulos analizada.</div>', unsafe_allow_html=True)
        if result is None:
            st.info("Pulse 'Calcular caso base' en el panel lateral para obtener resultados.")
        else:
            result_config = stored_inputs[3] if stored_inputs is not None else config
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("FS Fellenius", f"{result.fellenius.factor_of_safety:.3f}", delta=f"{result.fellenius.factor_of_safety - result_config.target_factor:+.3f} vs objetivo")
            m2.metric("FS Bishop", f"{result.bishop.factor_of_safety:.3f}", delta=f"{result.bishop.factor_of_safety - result_config.target_factor:+.3f} vs objetivo")
            governing = min(result.fellenius.factor_of_safety, result.bishop.factor_of_safety)
            m3.metric("FS gobernante", f"{governing:.3f}")
            m4.metric("Superficies validas", f"{result.valid_surfaces}", delta=f"de {result.evaluated_surfaces}", delta_color="off")
            status, icon = _status(governing, result_config.target_factor)
            if icon == "normal":
                st.success(f"{status}: el minimo supera el FS objetivo ({result_config.target_factor:.2f}).")
            elif icon == "off":
                st.warning(f"{status}: el minimo es mayor que 1,00, pero no alcanza el objetivo ({result_config.target_factor:.2f}).")
            else:
                st.error("El factor de seguridad calculado es inferior a 1,00.")
            summary_rows = []
            for item in (result.fellenius, result.bishop):
                circle = item.evaluation.circle
                summary_rows.append(
                    {
                        "Metodo": item.method,
                        "FS": item.factor_of_safety,
                        "xc (m)": circle.center_x,
                        "zc (m)": circle.center_y,
                        "R (m)": circle.radius,
                        "Peso (kN/m)": item.evaluation.total_weight,
                        "u max (kPa)": item.evaluation.max_pore_pressure,
                    }
                )
            st.dataframe(pd.DataFrame(summary_rows).style.format(precision=3), use_container_width=True, hide_index=True)
            st.caption("La comprobacion frente al objetivo es informativa; el criterio exigible corresponde al proyectista.")

    with tabs[5]:
        st.markdown('<div class="workspace-title">Seccion del talud</div>', unsafe_allow_html=True)
        st.markdown('<div class="workspace-copy">Estratigrafia, nivel freatico y superficie critica a escala geometrica 1:1.</div>', unsafe_allow_html=True)
        if result is None or stored_inputs is None:
            st.plotly_chart(section_figure(geometry, profile), use_container_width=True, config={"displaylogo": False})
            st.info("La superficie critica y las dovelas apareceran despues de calcular el caso base.")
        else:
            method = st.segmented_control(
                "Superficie mostrada",
                ["Bishop simplificado", "Fellenius"],
                default="Bishop simplificado",
                key="surface_method",
            )
            selected = result.bishop if method == "Bishop simplificado" else result.fellenius
            st.plotly_chart(
                section_figure(stored_inputs[1], stored_inputs[2], selected),
                use_container_width=True,
                config={"displaylogo": False, "scrollZoom": True},
            )
            circle = selected.evaluation.circle
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Entrada x", f"{circle.entry_x:.2f} m")
            c2.metric("Salida x", f"{circle.exit_x:.2f} m")
            c3.metric("Radio", f"{circle.radius:.2f} m")
            c4.metric("Iteraciones", f"{selected.evaluation.bishop.iterations}" if selected.method.startswith("Bishop") else "1")

    with tabs[6]:
        st.markdown('<div class="workspace-title">Dovelas y trazabilidad</div>', unsafe_allow_html=True)
        st.markdown('<div class="workspace-copy">Desglose numerico de la superficie critica seleccionada.</div>', unsafe_allow_html=True)
        if result is None:
            st.info("Calcule el caso base para consultar el desglose de dovelas.")
        else:
            trace_method = st.radio("Desglose", ["Bishop simplificado", "Fellenius"], horizontal=True)
            trace = result.bishop if trace_method == "Bishop simplificado" else result.fellenius
            table = slices_dataframe(trace)
            st.dataframe(table.style.format(precision=3), use_container_width=True, hide_index=True)
            csv_buffer = BytesIO()
            table.to_csv(csv_buffer, index=False)
            st.download_button(
                "Descargar dovelas CSV",
                csv_buffer.getvalue(),
                "dovelas_superficie_critica.csv",
                "text/csv",
                icon=":material/download:",
            )


if __name__ == "__main__":
    main()
