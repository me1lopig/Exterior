"""Interfaz Streamlit para estabilidad de taludes temporales."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
from math import radians, tan

import pandas as pd
import streamlit as st

from slope_stability_app.calculations import run_sensitivity, search_critical_surfaces
from slope_stability_app.models import AnalysisConfig, ProjectData, SlopeGeometry, Soil, SoilProfile, SweepConfig
from slope_stability_app.services import build_report
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
        :root { --ink:#17202A; --muted:#667085; --line:#E4E7EC; --accent:#D97706; }
        .stApp { background:#FBFCFD; color:var(--ink); }
        [data-testid="stHeader"] { background:rgba(251,252,253,.92); }
        [data-testid="stSidebar"] { background:#F1F3F5; border-right:1px solid #D8DDE3; }
        [data-testid="stSidebar"] h2 { font-size:1.05rem; letter-spacing:0; }
        .block-container { max-width:1480px; padding-top:1.35rem; padding-bottom:3rem; }
        h1, h2, h3 { color:var(--ink); letter-spacing:0 !important; }
        h1 { font-size:1.72rem !important; font-weight:720 !important; margin-bottom:.15rem !important; }
        h2 { font-size:1.12rem !important; margin-top:.4rem !important; }
        h3 { font-size:.98rem !important; }
        .app-kicker { color:var(--accent); font-size:.76rem; font-weight:750; text-transform:uppercase; letter-spacing:.08em; }
        .app-subtitle { color:var(--muted); margin-top:-.25rem; margin-bottom:1.2rem; max-width:880px; }
        .section-rule { border-top:1px solid var(--line); margin:.8rem 0 1rem; }
        [data-testid="stMetric"] { background:transparent; border-left:3px solid #D8DDE3; padding-left:.85rem; }
        [data-testid="stMetricValue"] { font-size:1.65rem; }
        .stButton>button, .stDownloadButton>button { border-radius:6px; font-weight:650; min-height:2.5rem; }
        .stButton>button[kind="primary"] { background:var(--accent); border-color:var(--accent); }
        div[data-baseweb="tab-list"] { gap:1.2rem; border-bottom:1px solid var(--line); }
        button[data-baseweb="tab"] { padding-left:0; padding-right:0; }
        div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:5px; }
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
    st.markdown('<div class="app-kicker">GeoSlope / Equilibrio limite</div>', unsafe_allow_html=True)
    st.title("Estabilidad de taludes temporales")
    st.markdown(
        '<div class="app-subtitle">Superficies circulares, uno o dos suelos y nivel freatico horizontal. Compare Fellenius y Bishop simplificado y explore la sensibilidad geometrica e hidraulica.</div>',
        unsafe_allow_html=True,
    )

    input_tabs = st.tabs(["Proyecto y geometria", "Suelos", "Calculo", "Sensibilidad"])
    with input_tabs[0]:
        left, right = st.columns([1, 1], gap="large")
        with left:
            project_name = st.text_input("Proyecto", "Talud temporal - Caso 01")
            location = st.text_input("Localizacion", "")
            author = st.text_input("Autor / revision", "")
            notes = st.text_area("Observaciones", "", height=95)
        with right:
            c1, c2 = st.columns(2)
            height = c1.number_input("Altura H (m)", 1.0, 50.0, 8.0, 0.25)
            angle = c2.number_input("Pendiente (deg)", 10.0, 85.0, 45.0, 1.0, help="Angulo de la cara respecto a la horizontal.")
            c3, c4 = st.columns(2)
            water = c3.number_input("Cota del nivel freatico (m)", 0.0, float(height), min(3.0, float(height)), 0.25)
            target_factor = c4.number_input("FS objetivo", 0.50, 3.00, 1.30, 0.05, help="Criterio introducido por el usuario; no se asigna automaticamente a una norma.")
            st.caption(f"Desarrollo horizontal de la cara: {height / max(tan(radians(angle)), 1e-9):.2f} m")

    with input_tabs[1]:
        two_soils = st.toggle("Activar segundo suelo", value=False)
        s1, s2 = st.columns(2, gap="large")
        with s1:
            upper_soil = _soil_inputs("upper", "Suelo superior", (18.0, 20.0, 5.0, 28.0))
        with s2:
            if two_soils:
                lower_soil = _soil_inputs("lower", "Suelo inferior", (19.0, 21.0, 12.0, 32.0))
                upper_thickness = st.number_input(
                    "Espesor del suelo superior desde coronacion (m)",
                    0.01,
                    max(float(height) - 0.01, 0.01),
                    min(3.0, float(height) / 2),
                    0.1,
                    help="Espesor vertical medido hacia abajo desde la cota de coronacion z=H.",
                )
                interface = float(height) - float(upper_thickness)
                st.metric("Espesor inferior dentro de H", f"{interface:.2f} m")
                st.caption(
                    f"Contacto horizontal en z = {interface:.2f} m sobre el pie. "
                    "El suelo inferior continua bajo z=0 para superficies de rotura profundas."
                )
            else:
                st.markdown("#### Perfil homogeneo")
                st.markdown(
                    f'<p class="technical-note">El suelo superior ocupa toda la altura del talud ({float(height):.2f} m) y continua bajo el pie.</p>',
                    unsafe_allow_html=True,
                )
                lower_soil = None
                interface = 0.0

    with input_tabs[2]:
        c1, c2, c3 = st.columns(3)
        slices = c1.number_input("Numero de dovelas", 10, 100, 30, 5)
        search_level = c2.selectbox("Densidad de busqueda", ["Rapida", "Equilibrada", "Detallada"], index=1)
        gamma_water = c3.number_input("Peso unitario del agua (kN/m3)", 9.0, 10.5, 9.81, 0.01)
        with st.expander("Control numerico y dominio de busqueda"):
            e1, e2, e3 = st.columns(3)
            tolerance = e1.number_input("Tolerancia Bishop", 1e-7, 1e-2, 1e-5, format="%.1e")
            iterations = e2.number_input("Iteraciones maximas", 20, 300, 100, 10)
            min_depth_ratio = e3.number_input("Profundidad minima / H", 0.02, 0.40, 0.08, 0.01)
        st.info("El buscador explora una familia discreta de circulos con entrada en coronacion y salida en la cara o al pie. Aumentar la densidad mejora la resolucion, pero no garantiza el minimo global.")

    with input_tabs[3]:
        st.markdown("#### Variables del barrido")
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
        sensitivity_level = st.selectbox("Densidad de busqueda en el barrido", ["Rapida", "Equilibrada", "Detallada"], index=0)
        cases = (int(angle_steps) if vary_angle else 1) * (int(water_steps) if vary_water else 1)
        st.caption(f"Combinaciones previstas: {cases}. Cada combinacion realiza una busqueda independiente de superficie critica.")

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

    with st.sidebar:
        st.markdown("## Acciones")
        run_base = st.button("Calcular caso base", type="primary", use_container_width=True, icon=":material/calculate:")
        run_sweep = st.button("Ejecutar sensibilidad", use_container_width=True, icon=":material/grid_view:")
        st.divider()
        st.markdown("## Informe y datos")

    if run_base:
        try:
            with st.spinner("Buscando superficies criticas..."):
                st.session_state.analysis = _cached_analysis(geometry, profile, config)
                st.session_state.analysis_inputs = (project, geometry, profile, config)
                st.session_state.pop("sensitivity", None)
                st.session_state.pop("sensitivity_inputs", None)
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))
    if run_sweep:
        try:
            with st.spinner(f"Resolviendo {cases} combinaciones..."):
                sweep_config = replace(config, search_level=sensitivity_level)
                st.session_state.sensitivity = _cached_sensitivity(geometry, profile, sweep_config, sweep)
                st.session_state.sensitivity_inputs = (geometry, profile, sweep_config, sweep)
                st.session_state.analysis = _cached_analysis(geometry, profile, config)
                st.session_state.analysis_inputs = (project, geometry, profile, config)
        except (ValueError, RuntimeError) as exc:
            st.error(str(exc))

    result = st.session_state.get("analysis")
    sensitivity = st.session_state.get("sensitivity")
    stored_inputs = st.session_state.get("analysis_inputs")
    if stored_inputs is not None and stored_inputs[1:] != (geometry, profile, config):
        st.warning("Hay entradas modificadas desde el ultimo calculo. Pulse 'Calcular caso base' para actualizar los resultados.")

    with st.sidebar:
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

    st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
    if result is None:
        preview_left, preview_right = st.columns([1.45, 0.55], gap="large")
        with preview_left:
            st.plotly_chart(section_figure(geometry, profile), use_container_width=True, config={"displaylogo": False})
        with preview_right:
            st.markdown("### Modelo preparado")
            st.metric("Altura", f"{height:.2f} m")
            st.metric("Pendiente", f"{angle:.1f} deg")
            st.metric("Nivel freatico", f"z = {water:.2f} m")
            st.caption("Revise las cuatro pestañas de entrada y ejecute el caso base desde el panel lateral.")
        return

    result_tabs = st.tabs(["Resumen", "Seccion critica", "Sensibilidad", "Dovelas y trazabilidad"])
    with result_tabs[0]:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("FS Fellenius", f"{result.fellenius.factor_of_safety:.3f}", delta=f"{result.fellenius.factor_of_safety - config.target_factor:+.3f} vs objetivo")
        m2.metric("FS Bishop", f"{result.bishop.factor_of_safety:.3f}", delta=f"{result.bishop.factor_of_safety - config.target_factor:+.3f} vs objetivo")
        governing = min(result.fellenius.factor_of_safety, result.bishop.factor_of_safety)
        m3.metric("FS gobernante", f"{governing:.3f}")
        m4.metric("Superficies validas", f"{result.valid_surfaces}", delta=f"de {result.evaluated_surfaces} evaluadas", delta_color="off")
        status, icon = _status(governing, config.target_factor)
        if icon == "normal":
            st.success(f"{status}: el minimo calculado supera el FS objetivo introducido ({config.target_factor:.2f}).")
        elif icon == "off":
            st.warning(f"{status}: el minimo es mayor que 1,00 pero no alcanza el FS objetivo ({config.target_factor:.2f}).")
        else:
            st.error("El factor de seguridad calculado es inferior a 1,00 para alguna de las superficies exploradas.")
        summary_rows = []
        for item in (result.fellenius, result.bishop):
            circle = item.evaluation.circle
            summary_rows.append({"Metodo": item.method, "FS": item.factor_of_safety, "xc (m)": circle.center_x, "zc (m)": circle.center_y, "R (m)": circle.radius, "Peso (kN/m)": item.evaluation.total_weight, "u max (kPa)": item.evaluation.max_pore_pressure})
        st.dataframe(pd.DataFrame(summary_rows).style.format(precision=3), use_container_width=True, hide_index=True)
        st.caption("La comprobacion respecto al objetivo es informativa. La seleccion del FS exigible corresponde al proyectista y al marco normativo aplicable.")

    with result_tabs[1]:
        method = st.segmented_control("Superficie mostrada", ["Bishop simplificado", "Fellenius"], default="Bishop simplificado")
        selected = result.bishop if method == "Bishop simplificado" else result.fellenius
        st.plotly_chart(section_figure(stored_inputs[1], stored_inputs[2], selected), use_container_width=True, config={"displaylogo": False, "scrollZoom": True})
        circle = selected.evaluation.circle
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Entrada x", f"{circle.entry_x:.2f} m")
        c2.metric("Salida x", f"{circle.exit_x:.2f} m")
        c3.metric("Radio", f"{circle.radius:.2f} m")
        c4.metric("Iteraciones", f"{selected.evaluation.bishop.iterations}" if selected.method.startswith("Bishop") else "1")

    with result_tabs[2]:
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
            st.dataframe(sensitivity.style.format({"Pendiente (deg)": "{:.2f}", "Nivel freatico (m)": "{:.2f}", "FS Fellenius": "{:.3f}", "FS Bishop": "{:.3f}"}), use_container_width=True, hide_index=True)

    with result_tabs[3]:
        trace_method = st.radio("Desglose", ["Bishop simplificado", "Fellenius"], horizontal=True)
        trace = result.bishop if trace_method == "Bishop simplificado" else result.fellenius
        table = slices_dataframe(trace)
        st.dataframe(table.style.format(precision=3), use_container_width=True, hide_index=True)
        csv_buffer = BytesIO()
        table.to_csv(csv_buffer, index=False)
        st.download_button("Descargar dovelas CSV", csv_buffer.getvalue(), "dovelas_superficie_critica.csv", "text/csv", icon=":material/download:")
        with st.expander("Hipotesis y formulacion aplicada"):
            st.markdown(
                """
                - Analisis bidimensional por metro de ancho y superficies de rotura circulares.
                - Resistencia efectiva Mohr-Coulomb. El suelo de la base se asigna por la cota del punto medio de cada dovela.
                - Peso integrado separando estrato y condicion seca/saturada.
                - Presion intersticial hidrostatica bajo un nivel horizontal recortado contra el terreno.
                - Fellenius desprecia fuerzas entre dovelas. Bishop simplificado itera el equilibrio de momentos y no satisface el equilibrio horizontal completo.
                - El minimo es relativo a la familia discreta explorada; debe comprobarse la sensibilidad a densidad de busqueda y numero de dovelas.
                """
            )


if __name__ == "__main__":
    main()
