"""Interfaz Streamlit para consulta y calculo de correlaciones geotecnicas."""

import pandas as pd
import streamlit as st

from calculations.correlations import (
    CTE_D23,
    CTE_K30,
    CTE_POISSON,
    bjerrum_simons_su,
    calip,
    cte_d23_linear,
    cte_eu,
    cte_subgrade_modulus,
    mesri_su,
    navfac_sand_modulus,
    phi_hatanaka_uchida,
    phi_jra,
    phi_mayne,
    phi_residual_from_calip,
    phi_wolff,
    skempton_su,
    stroud_drained_vertical_modulus,
)
from calculations.spt import SPTCorrection
from models.catalog import FORMULATIONS, REFERENCES
from models.domain import CalculationResult


st.set_page_config(page_title="Correlaciones geotecnicas", page_icon="G", layout="wide")
st.markdown(
    """
    <style>
    .stApp { background: #f5f7f8; }
    .block-container { max-width: 1320px; padding-top: 1.5rem; }
    .hero { background:#17384d; color:white; padding:22px 26px; border-radius:6px; margin-bottom:16px; }
    .hero h1 { font-size:1.7rem; margin:0 0 7px; letter-spacing:0; }
    .hero p { color:#dbe8ee; margin:0; max-width:900px; }
    [data-testid="stMetric"] { background:white; border:1px solid #d9e1e5; padding:10px; border-radius:6px; }
    [data-testid="stExpander"] { background:white; border:1px solid #d9e1e5; border-radius:6px; }
    </style>
    """,
    unsafe_allow_html=True,
)
st.markdown(
    """<div class="hero"><h1>Correlaciones geotecnicas</h1>
    <p>Estimaciones preliminares con base de entrada explicita, control de dominio y trazabilidad bibliografica.</p></div>""",
    unsafe_allow_html=True,
)


def result_frame(results: list[CalculationResult]) -> pd.DataFrame:
    rows = []
    for result in results:
        rows.append(
            {
                "Metodo": result.method,
                "Valor": round(result.value, 3) if isinstance(result.value, float) else result.value,
                "Unidad": result.unit,
                "Base de entrada": result.input_basis,
                "Aplicabilidad": result.applicability,
                "Aviso": result.warning or "Dentro del dominio declarado",
                "Ref.": result.reference_id,
            }
        )
    return pd.DataFrame(rows)


def show_frame(frame: pd.DataFrame) -> None:
    st.dataframe(frame, hide_index=True, use_container_width=True)


tab_calc, tab_refs = st.tabs(["Calculo", "Referencias y formulaciones"])

with tab_calc:
    st.subheader("Normalizacion del SPT")
    st.caption("Introduzca los factores del parte de campo o del certificado de energia. No se presupone N60 = 0.60 N.")
    spt_cols = st.columns(4)
    n_field = spt_cols[0].number_input("N de campo [golpes/0.30 m]", 0.0, 200.0, 20.0, 1.0)
    er = spt_cols[1].number_input("Relacion de energia ER [%]", 1.0, 150.0, 60.0, 1.0)
    sigma_eff = spt_cols[2].number_input("Tension vertical efectiva sigma'v0 [kPa]", 1.0, 5000.0, 100.0, 5.0)
    cn_cap = spt_cols[3].number_input("Limite superior CN", 1.0, 3.0, 1.7, 0.1)
    with st.expander("Factores de equipo SPT"):
        factor_cols = st.columns(3)
        cb = factor_cols[0].number_input("CB, diametro de sondeo", 0.1, 2.0, 1.0, 0.05)
        cr = factor_cols[1].number_input("CR, longitud de varillaje", 0.1, 2.0, 1.0, 0.05)
        cs = factor_cols[2].number_input("CS, tomamuestras", 0.1, 2.0, 1.0, 0.05)
    spt = SPTCorrection(n_field, er, cb, cr, cs, sigma_eff, cn_cap=cn_cap)
    m1, m2, m3 = st.columns(3)
    m1.metric("N60", f"{spt.n60:.2f}")
    m2.metric("CN", f"{spt.cn:.3f}")
    m3.metric("(N1)60", f"{spt.n1_60:.2f}")
    resistant, deformation, cte_tables = st.tabs(["Resistencia", "Deformabilidad", "Tablas CTE"])

    with resistant:
        with st.expander("Resistencia al corte no drenada su", expanded=True):
            col1, col2, col3 = st.columns(3)
            pi = col1.number_input("Indice de plasticidad IP [%]", 0.0, 100.0, 25.0, 1.0, key="su_pi")
            sig_v = col2.number_input("sigma'v0 efectiva [kPa]", 0.1, 5000.0, 100.0, 5.0, key="su_sig")
            sig_p = col3.number_input("sigma'p efectiva [kPa]", 0.1, 10000.0, 150.0, 5.0)
            su_results = [skempton_su(pi, sig_v), bjerrum_simons_su(pi, sig_v), mesri_su(sig_p)]
            su_frame = result_frame(su_results)
            show_frame(su_frame)
            st.info("Skempton y Bjerrum-Simons estiman resistencia de veleta para arcillas NC. Mesri usa resistencia movilizada y sigma'p; no son valores intercambiables.")

        with st.expander("Angulo de rozamiento efectivo de arenas", expanded=True):
            phi_results = [
                phi_wolff(spt.n1_60),
                phi_hatanaka_uchida(spt.n1_60),
                phi_mayne(spt.n1_60),
                phi_jra(spt.n1_60),
            ]
            phi_frame = result_frame(phi_results)
            show_frame(phi_frame)
            st.warning("Las tres expresiones requieren (N1)60. El resultado representa una correlacion empirica de angulo de pico, no un valor caracteristico automatico.")

        with st.expander("Parametro CALIP y rozamiento residual"):
            c1, c2, c3, c4 = st.columns(4)
            p40 = c1.number_input("Pasa tamiz ASTM No. 40 (0.425 mm) [%]", 0.1, 100.0, 80.0, 1.0)
            clay = c2.number_input("Contenido de arcilla CA [% del suelo total]", 0.0, 100.0, 40.0, 1.0)
            ll = c3.number_input("Limite liquido LL [%]", 0.1, 500.0, 50.0, 1.0)
            pl = c4.number_input("Limite plastico LP [%]", 0.0, 499.0, 20.0, 1.0)
            try:
                cf, pi_calip, calip_value = calip(p40, clay, ll, pl)
                phi_residual = phi_residual_from_calip(calip_value)
                calip_frame = pd.DataFrame(
                    [(cf, pi_calip, calip_value, phi_residual.value)],
                    columns=["CF [% de P40]", "IP = LL-LP [%]", "CALIP", "phi_R residual secante [grados]"],
                ).round(4)
                show_frame(calip_frame)
                st.info("El valor de phi_R se obtiene con la ecuacion B4 de Tzampoglou et al. (2026), ajuste no lineal de la curva de corte anular de Collotta et al. (1989), con R2 > 0.99. Es un angulo residual secante y no sustituye el ensayo residual de proyecto.")
                st.caption(phi_residual.applicability)
                if phi_residual.warning:
                    st.warning(phi_residual.warning)
            except ValueError as error:
                st.error(str(error))

    with deformation:
        with st.expander("Modulo vertical drenado de arcillas segun Stroud-Butler", expanded=True):
            stroud_cols = st.columns(2)
            n_stroud = stroud_cols[0].number_input(
                "N SPT compatible con la base historica de Stroud",
                min_value=0.0,
                max_value=100.0,
                value=min(float(n_field), 100.0),
                step=1.0,
            )
            pi_stroud = stroud_cols[1].number_input(
                "IP para Stroud [%]",
                min_value=0.0,
                max_value=60.0,
                value=25.0,
                step=1.0,
            )
            stroud_frame = result_frame(list(stroud_drained_vertical_modulus(n_stroud, pi_stroud)))
            show_frame(stroud_frame)
            st.warning("Los limites son polinomios de digitalizacion de la Figura 6, no ecuaciones publicadas por Stroud. Estiman E'v drenado para materiales sobreconsolidados y conservan la base SPT historica del estudio.")

        with st.expander("Modulo de arenas segun NAVFAC DM 7.1", expanded=True):
            soil_options = ["Limos y arenas limosas", "Arenas limpias finas-medias", "Arenas gruesas con poca grava", "Gravas arenosas y gravas"]
            soil_type = st.selectbox("Tipo de suelo", soil_options)
            e_navfac = navfac_sand_modulus(n_field, soil_type)
            navfac_frame = result_frame([e_navfac])
            show_frame(navfac_frame)
            st.warning("La expresion pertenece al procedimiento historico NAVFAC y usa su base N original. No mezcle automaticamente este N con N60 o (N1)60.")

        with st.expander("Modulo no drenado Eu segun CTE DB-SE-C, tabla F.2", expanded=True):
            c1, c2, c3 = st.columns(3)
            cu = c1.number_input("cu [kPa]", 0.1, 5000.0, 75.0, 5.0)
            pi_e = c2.number_input("IP [%]", 0.0, 100.0, 25.0, 1.0, key="eu_pi")
            ocr = c3.number_input("OCR [-]", 0.1, 50.0, 2.0, 0.1)
            try:
                eu_frame = result_frame([cte_eu(cu, pi_e, ocr)])
                show_frame(eu_frame)
            except ValueError as error:
                st.error(str(error))

        with st.expander("Modulo de balasto segun CTE DB-SE-C"):
            c1, c2, c3, c4 = st.columns(4)
            k30 = c1.number_input("ksp30 [MN/m3]", 0.1, 10000.0, 50.0, 5.0)
            width = c2.number_input("B, lado menor [m]", 0.01, 100.0, 2.0, 0.1)
            length = c3.number_input("L, lado mayor [m]", 0.01, 500.0, 3.0, 0.1)
            soil = c4.selectbox("Comportamiento", ["Cohesivo", "Granular"])
            try:
                ks_frame = result_frame([cte_subgrade_modulus(k30, width, length, soil)])
                show_frame(ks_frame)
                st.caption("El modulo de balasto depende de dimensiones y modelo estructural; no es una propiedad intrinseca del terreno.")
            except ValueError as error:
                st.error(str(error))

    with cte_tables:
        st.subheader("CTE DB-SE-C, tabla D.23")
        st.caption("Intervalos orientativos. La herramienta permite adoptar una interpolacion lineal por tramos entre sus extremos.")
        d23_frame = pd.DataFrame(CTE_D23, columns=["Compacidad/consistencia", "N SPT", "qu [kPa]", "E [MPa]"])
        show_frame(d23_frame)
        st.markdown("#### Interpolacion lineal adoptada")
        d23_cols = st.columns(2)
        n_refusal = d23_cols[0].number_input(
            "N equivalente al rechazo [golpes/0.30 m]",
            min_value=51.0,
            max_value=500.0,
            value=100.0,
            step=1.0,
        )
        n_d23 = d23_cols[1].number_input(
            "N SPT para tabla D.23 [golpes/0.30 m]",
            min_value=0.0,
            max_value=float(n_refusal),
            value=min(30.0, float(n_refusal)),
            step=1.0,
        )
        d23_results = result_frame(list(cte_d23_linear(n_d23, n_refusal)))
        show_frame(d23_results)
        st.warning("La interpolacion es una hipotesis de la herramienta. El CTE aporta intervalos y no fija un N numerico para el rechazo; el valor adoptado debe justificarse para cada campana y procedimiento de ensayo.")
        st.subheader("CTE DB-SE-C, tabla D.29")
        k30_frame = pd.DataFrame(CTE_K30, columns=["Tipo de suelo", "ksp30 minimo [MN/m3]", "ksp30 maximo [MN/m3]"])
        k30_frame = k30_frame.replace(float("inf"), "sin limite tabulado")
        show_frame(k30_frame)
        st.subheader("CTE DB-SE-C, tabla D.24")
        poisson_frame = pd.DataFrame(CTE_POISSON, columns=["Tipo de suelo", "nu"])
        show_frame(poisson_frame)

with tab_refs:
    st.subheader("Formulaciones implementadas")
    formula_frame = pd.DataFrame(FORMULATIONS, columns=["Magnitud", "Formulacion", "Entradas/unidades", "Ref.", "Observacion"])
    show_frame(formula_frame)
    st.subheader("Criterio de depuracion")
    st.markdown(
        """
        - Se corrigio Skempton a una dependencia lineal con IP; se elimino `log10(IP)`.
        - CALIP usa `IP = LL - LP`, no el limite plastico, y el tamiz ASTM No. 40 es 0.425 mm.
        - `phi_R` se calcula mediante la ecuacion B4 de Tzampoglou et al. (2026), ajuste de corte anular a la grafica de Collotta et al.
        - La banda de Stroud-Butler estima el modulo vertical drenado E'v; sus polinomios son una digitalizacion posterior de la Figura 6 y no ecuaciones originales.
        - Las expresiones de rozamiento implementadas reciben `(N1)60`; no reciben N bruto.
        - La tabla D.23 se conserva y se complementa con una interpolacion lineal por tramos adoptada por la herramienta; el N equivalente al rechazo es una hipotesis editable.
        - Se eliminaron los polinomios de quinto grado sin fuente del prototipo y se sustituyeron por una regresion publicada y trazable.
        """
    )
    st.subheader("Bibliografia")
    for reference in REFERENCES:
        st.markdown(f"**[{reference.ref_id}] {reference.citation}**  ")
        st.caption(f"{reference.source_type}. {reference.scope}")
        st.link_button("Abrir fuente", reference.url)

st.caption("Uso preliminar. El criterio geotecnico y la validacion con ensayos prevalecen sobre cualquier correlacion.")
