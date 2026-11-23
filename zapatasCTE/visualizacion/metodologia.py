"""Formulaciones documentales y memoria numérica en vistas separadas.

La metodología no presenta resultados; la memoria se visualiza en la ficha B x L.
No modifica ninguna magnitud del motor de cálculo.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from calculos.memoria_calculo import elaborar_memoria
from modelos.datos import DatosAsientos, DatosHundimiento
from modelos.geometrias import ResultadoGeometria


def _fila(nombre: str, valor: float | None, unidad: str = "", fuente: str = "Calculado") -> dict:
    return {
        "Magnitud": nombre,
        "Valor": "No válido" if valor is None else f"{valor:.4f}",
        "Unidad": unidad,
        "Procedencia": fuente,
    }


def mostrar_compendio() -> None:
    """Muestra exclusivamente formulaciones, hipótesis y referencias."""
    st.subheader("Metodología y formulaciones de cálculo")
    st.caption(
        "Ecuaciones del motor de ZapatasCTE, condiciones de aplicación "
        "y limitaciones. Los resultados numéricos se consultan en las "
        "pestañas «Zapatas B × L» y «Zapatas corridas»."
    )
    t_h, t_a, t_s, t_c = st.tabs([
        "Hundimiento", "Asientos (Steinbrenner)",
        "Servicio y balasto", "Controles y advertencias",
    ])
    with t_h:
        st.markdown("**1. Resistencia característica y presión de hundimiento de cálculo**")
        st.latex(
            r"q_{h,k}=c_kN_cd_cs_ct_c+q_{0k}N_qd_qs_qt_q"
            r"+\frac{1}{2}B\gamma_kN_\gamma d_\gamma s_\gamma t_\gamma"
            r"+\Delta q_{\mathrm{talud,ud}}"
        )
        st.latex(r"q_{h,d}^{bruta}=\frac{q_{h,k}}{\gamma_R}")
        st.caption(
            "CTE DB-SE-C §4.3.2.1, expresión 4.8, para carga vertical centrada. "
            "En esta aplicación i_c=i_q=i_γ=1; el motor divide la suma completa "
            "entre γR (3 en situación persistente/transitoria, 2 en extraordinaria). "
            "El término corrector adicional se aplica solo en el caso sin drenaje y con talud."
        )
        with st.expander("Factores de capacidad de carga N y caso sin drenaje"):
            st.latex(r"N_q=\tan^2(45^\circ+\varphi'/2)\,e^{\pi\tan\varphi'}")
            st.latex(r"N_c=\frac{N_q-1}{\tan\varphi'}")
            st.latex(r"N_\gamma=1.5(N_q-1)\tan\varphi'")
            st.caption(
                "CTE Anejo F, F.13-F.15 en condiciones drenadas. "
                "En la opción sin drenaje el motor impone φ=0, N_c=5,14, N_q=1, N_γ=0. "
                "Revisar la pertinencia de estos parámetros en el proyecto."
            )
        with st.expander("Factores de forma, profundidad y talud"):
            st.latex(r"s_c=1+0.2\frac{B}{L},\qquad s_q=1+1.5\tan\varphi'\frac{B}{L}")
            st.latex(r"s_\gamma=1-0.3\frac{B}{L},\qquad d_\gamma=1")
            st.latex(r"d_c=1+0.34\arctan(D/B)")
            st.latex(
                r"d_q=1+2\frac{N_q}{N_c}(1-\sin\varphi')^2"
                r"\arctan\left(\frac{\min(D,2B)}{B}\right)"
            )
            st.caption(
                "Los factores d solo se activan expresamente; el programa exige D≥2 m "
                "y ausencia de talud para aplicarlos. Si no se activan, d_c=d_q=1. "
                "En φ=0 toma d_q=1."
            )
            st.latex(r"t_c=e^{-2\beta\tan\varphi'},\qquad t_q=t_\gamma=1-\sin(2\beta)")
            st.latex(r"\Delta q_{\mathrm{talud,ud}}=-2\beta c_u\quad(\beta\ \mathrm{en\ rad})")
            st.caption(
                "Los t corresponden al caso drenado de la implementación. "
                "En el caso sin drenaje el programa aplica t=1 y la corrección "
                "aditiva por talud anterior; sin talud, Δq=0."
            )
        with st.expander("Nivel freático, sobrecarga y pesos específicos"):
            st.latex(r"\gamma'=\gamma_{\mathrm{sat}}-\gamma_w,\qquad\gamma_w=9.81\ \mathrm{kN/m^3}")
            st.latex(
                r"\gamma_k=\gamma'+\operatorname{clip}\left("
                r"\frac{NF-D}{B},0,1\right)(\gamma_{\mathrm{ap}}-\gamma')"
            )
            st.latex(r"\gamma_k=\gamma'-i_v\gamma_w\quad\text{(flujo ascendente)}")
            st.latex(r"q_{0k}=\gamma_{\mathrm{sob}}\;h_{\mathrm{sob}}")
            st.caption(
                "NF y D se miden bajo rasante. La interpolación en el intervalo "
                "D < NF < D+B corresponde al tratamiento F.16; para flujo ascendente "
                "se usa F.17. q0 es una sobrecarga de contorno, distinta de la "
                "tensión retirada por excavación."
            )

    with t_a:
        st.markdown("**2. Asiento elástico mediante Steinbrenner**")
        st.latex(
            r"u(z)=\frac{q\,b}{2E}\left[(1-\nu^2)F_1-"
            r"(1-\nu-2\nu^2)F_2\right]"
        )
        st.caption(
            "u(z) es el desplazamiento asociado a una esquina de un rectángulo "
            "uniformemente cargado b × l. Si q y E están en MPa, b y z en metros, "
            "el desplazamiento se obtiene en metros."
        )
        with st.expander("Desarrollo de los factores F1 y F2"):
            st.latex(r"m=z/b,\quad n=l/b,\quad\tau=\sqrt{1+n^2+m^2}")
            st.latex(
                r"F_1=\frac{1}{\pi}\left[\ln\frac{\tau+n}{\tau-n}"
                r"+n\ln\frac{\tau+1}{\tau-1}\right]"
            )
            st.latex(r"F_2=\frac{m}{\pi}\arctan\left(\frac{n}{\tau m}\right)")
            st.caption(
                "El motor evalúa formas numéricamente estables de estos factores "
                "y toma F2=0 para z=0. No son expresiones del Anejo F de hundimiento."
            )
        st.markdown("**Contribución por estrato y asiento bajo el centro**")
        st.latex(r"\Delta s_i=u_i(z_{\mathrm{sup},i})-u_i(z_{\mathrm{inf},i})")
        st.latex(
            r"s_{\mathrm{centro}}=4\sum_i\Delta s_i"
            r"\quad\text{con}\quad b=B/2,\ l=L/2"
        )
        st.caption(
            "ZapatasCTE calcula el asiento central exclusivamente mediante "
            "superposición de cuatro cuadrantes (B/2 × L/2)."
        )
        st.markdown("**Presión neta limitada por asiento**")
        st.latex(r"s=q_{\mathrm{neta}}f(B,L,E_i,\nu_i)")
        st.latex(r"q_{as,\mathrm{neta}}=\frac{s_{\mathrm{adm}}}{f}")
        st.caption(
            "f se calcula aplicando 1 MPa de presión neta. Las contribuciones "
            "por capas aproximan un perfil estratificado; no constituyen una "
            "solución multicapa rigurosa ni incluyen consolidación."
        )

    with t_s:
        st.markdown("**3. Conversión bruta/neta y estado límite gobernante**")
        st.latex(r"q_{h,d}^{neta}=q_{h,d}^{bruta}-\sigma_{v0,exc}")
        st.latex(r"q_{as}^{bruta}=q_{as}^{neta}+\sigma_{v0,exc}")
        st.latex(r"q_{serv}^{neta}=\min(q_{h,d}^{neta},q_{as}^{neta})")
        st.latex(r"q_{serv}^{bruta}=q_{serv}^{neta}+\sigma_{v0,exc}")
        st.caption(
            "σv0,exc es la tensión TOTAL preexistente retirada por excavación "
            "(estimación con D, NF y pesos específicos o dato manual). "
            "No es el q0 de la ecuación de hundimiento. "
            "Si q_h,d neta ≤ 0, el programa no declara presión de servicio válida."
        )
        st.markdown("**4. Coeficientes de balasto**")
        st.latex(r"k_{s,BL}=\frac{q_{as}^{neta}}{s_{\mathrm{adm}}}")
        st.latex(
            r"k_{s,B}=\frac{k_{s,BL}}{1+B/(2L)}\quad(B<L)"
        )
        st.latex(
            r"K_{sp30}=k_{s,B}\frac{B}{0.30}\quad\text{(cohesivo)}"
        )
        st.latex(
            r"K_{sp30}=k_{s,B}\left(\frac{2B}{B+0.30}\right)^2"
            r"\quad\text{(granular)}"
        )
        st.caption(
            "Para B=L el código utiliza k_s,B=k_s,BL sin factor rectangular. "
            "La transición a B<L y su interpretación respecto a E.6-E.8 "
            "están pendientes de revisión técnica. k_s se expresa en MN/m³ "
            "y el asiento en metros al aplicar la primera expresión."
        )

    with t_c:
        st.markdown("**5. Bulbo Boussinesq como comprobación independiente**")
        st.latex(r"\Delta\sigma_z=q_{\mathrm{neta}}I(B,L,z)")
        st.latex(
            r"\Delta\sigma_z\leq\min"
            r"\left(0.10q_{\mathrm{neta}},\,0.05\sigma'_{v0}(z)\right)"
        )
        st.caption(
            "Se estima el cruce sobre el eje central y se contrasta con "
            "la profundidad inferior del perfil introducido. El bulbo no "
            "calcula asientos ni garantiza que los estratos fuera del perfil "
            "sean rígidos. El 2D representa incrementos de tensión total."
        )
        st.markdown("**Hipótesis y limitaciones**")
        st.caption(
            "Herramienta de predimensionamiento: carga vertical centrada y "
            "base horizontal. No verifica cargas excéntricas o inclinadas, "
            "consolidación, interacción entre zapatas ni seguridad global. "
            "Steinbrenner por estratos y el control de profundidad son "
            "aproximaciones que requieren comprobación geotécnica."
        )
    st.markdown(
        "**Referencias técnicas:** "
        "[CTE DB-SE-C, §4.3.2.1 y Anejo F (hundimiento), Anejo E (balasto)]"
        "(https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf); "
        "método de Steinbrenner descrito en "
        "METODOLOGIA_ASIENTOS.md del repositorio."
    )

def mostrar_memoria_numerica(
    h: DatosHundimiento,
    s: DatosAsientos,
    seleccion: ResultadoGeometria,
    *,
    origen_gamma: str | None = None,
    gamma_sat_kn_m3: float | None = None,
    desactualizado: bool = False,
) -> None:
    """Presenta los factores y términos numéricos de la zapata B x L elegida."""
    if desactualizado:
        st.warning(
            "Resultados pendientes de actualizar: pulse «Calcular» "
            "para incorporar las entradas modificadas."
        )

    st.subheader("Memoria numérica de la zapata B × L seleccionada")
    st.caption(
        f"Datos del último cálculo: B={seleccion.b_m:.2f} m, "
        f"L={seleccion.l_m:.2f} m. La selección sigue la ficha del mapa B × L; "
        "esta memoria usa una única geometría B × L en ambos cálculos."
    )
    memo = elaborar_memoria(h, s, seleccion)
    st.markdown("**Parámetros y factores efectivos del cálculo de hundimiento**")
    if origen_gamma == "Calcular γ' a partir de γsat" and gamma_sat_kn_m3 is not None:
        st.caption(
            f"Origen de γ': calculado con γsat={gamma_sat_kn_m3:.2f} kN/m³ "
            "y γagua=9,81 kN/m³."
        )
    else:
        st.caption("Origen de γ': valor introducido directamente por el usuario.")
    if h.flujo_ascendente:
        caso_gamma = "F.17: flujo ascendente (gradiente medio en 1,5 B)"
    else:
        distancia_nf = h.nivel_freatico_m - h.profundidad_base_m
        caso_gamma = (
            "NF en o sobre base: γ'" if distancia_nf <= 0 else
            "NF a ≥B bajo base: γaparente" if distancia_nf >= seleccion.b_m else
            "F.16: interpolación por profundidad de NF"
        )
    st.caption(f"Peso específico γk: {memo.gamma_k_kn_m3:.2f} kN/m³. {caso_gamma}.")
    st.dataframe(pd.DataFrame([
        _fila("Cohesión representativa", memo.cohesion_kpa, "kPa"),
        _fila("γk de hundimiento", memo.gamma_k_kn_m3, "kN/m³"),
        _fila("q0 contorno", memo.q0_kpa, "kPa", "Entrada/derivado"),
        _fila("Nc", memo.nc), _fila("Nq", memo.nq), _fila("Nγ", memo.ngamma),
        _fila("sc", memo.sc), _fila("sq", memo.sq), _fila("sγ", memo.sgamma),
        _fila("dc", memo.dc), _fila("dq", memo.dq), _fila("dγ", memo.dgamma),
        _fila("tc", memo.tc), _fila("tq", memo.tq), _fila("tγ", memo.tgamma),
        _fila("γR", memo.gamma_r),
    ]), hide_index=True, use_container_width=True)

    st.markdown("**Desglose de términos y resultados calculados**")
    st.dataframe(pd.DataFrame([
        _fila("Término de cohesión", memo.termino_cohesion_kpa, "kPa"),
        _fila("Término de sobrecarga", memo.termino_sobrecarga_kpa, "kPa"),
        _fila("Término de peso específico", memo.termino_gamma_kpa, "kPa"),
        _fila("Corrección aditiva talud sin drenaje", memo.correccion_talud_kpa, "kPa"),
        _fila("Resistencia característica qh,k", memo.q_h_caracteristica_kpa, "kPa"),
        _fila("Hundimiento de cálculo bruto", memo.q_h_d_bruta_mpa, "MPa"),
        _fila("Tensión retirada por excavación", memo.sigma_pre_base_kpa, "kPa"),
        _fila("Hundimiento de cálculo neto", memo.q_h_d_neta_mpa, "MPa"),
        _fila("Flexibilidad de asiento unitario (1 MPa)", memo.flexibilidad_cm_mpa, "cm/MPa"),
        _fila("Asiento admisible", memo.asiento_admisible_cm, "cm", "Entrada"),
        _fila("Presión por asientos neta", memo.q_asiento_neta_mpa, "MPa"),
        _fila("Presión de servicio neta", memo.q_servicio_neta_mpa, "MPa"),
        _fila("Presión de servicio bruta", memo.q_servicio_bruta_mpa, "MPa"),
        _fila("Balasto ks,BL", memo.ks_bl_mn_m3, "MN/m³"),
        _fila("Balasto Ksp30", memo.ksp30_mn_m3, "MN/m³"),
    ]), hide_index=True, use_container_width=True)
    st.write(
        f"**Gobierna:** {memo.limitacion}. "
        f"**Método de asientos:** {memo.metodo_asientos}. "
        f"**Material para balasto:** {memo.tipo_balasto}."
    )
