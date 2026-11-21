from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
import streamlit as st

from calculos.asientos import calcular_caso, modulo_confinado_kpa
from calculos.steinbrenner import calcular_steinbrenner
from modelos.datos import COLUMNAS_ESTRATOS, Cimentacion, estratos_ejemplo, validar_estratos
from servicios.exportacion_docx import crear_informe_docx
from servicios.exportacion_excel import crear_excel
from utiles.estilos import CSS_APP
from visualizacion.graficos import (
    figura_aporte_estratos,
    figura_aporte_steinbrenner,
    figura_asientos,
    figura_asientos_steinbrenner,
    figura_bulbo,
    figura_deformacion,
    figura_tensiones,
)


st.set_page_config(
    page_title="Asientos de zapata flexible",
    page_icon="▤",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS_APP, unsafe_allow_html=True)


def firma_caso(payload: dict, estratos: pd.DataFrame) -> str:
    contenido = json.dumps(payload, sort_keys=True, ensure_ascii=True) + estratos.to_json()
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


if "estratos" not in st.session_state:
    st.session_state.estratos = estratos_ejemplo()

st.markdown('<div class="geo-kicker">Geo Settlement · Elasticidad multicapa</div>', unsafe_allow_html=True)
st.title("Asientos de zapata rectangular flexible")
st.markdown(
    '<div class="geo-subtitle">Distribución de tensiones de Boussinesq y compresión vertical elástica en terreno estratificado.</div>',
    unsafe_allow_html=True,
)

tabs = st.tabs(
    [
        "Proyecto y geometría",
        "Terreno",
        "Resultados",
        "Bulbo de influencia",
        "Informe y datos",
        "Formulación",
    ]
)

with tabs[0]:
    st.subheader("Datos del caso")
    st.caption("Defina la referencia del proyecto y la geometría de la cimentación. La carga introducida debe ser neta.")
    c1, c2 = st.columns([1.35, 1.0])
    with c1:
        proyecto_nombre = st.text_input("Proyecto", "Zapata flexible - Caso 01")
        localizacion = st.text_input("Localización", "")
        autor = st.text_input("Autor / revisión", "")
        observaciones = st.text_area("Observaciones", "", height=90)
    with c2:
        g1, g2 = st.columns(2)
        b_m = g1.number_input("Ancho B (m)", min_value=0.10, value=2.00, step=0.10, format="%.2f")
        l_m = g2.number_input("Longitud L (m)", min_value=0.10, value=3.00, step=0.10, format="%.2f")
        q_kpa = g1.number_input("Presión neta q (kN/m²)", min_value=0.10, value=150.0, step=5.0, format="%.1f")
        df_m = g2.number_input("Profundidad de apoyo Df (m)", min_value=0.0, value=1.00, step=0.10, format="%.2f")
        if b_m > l_m:
            st.error("La geometría no es válida: debe cumplirse B ≤ L.")
        else:
            st.success(f"Geometría comprobada · L/B = {l_m / b_m:.2f}")
        st.info("q se interpreta como presión neta uniforme en la base; la excavación no se descuenta de nuevo.")

    st.divider()
    st.subheader("Dominio y discretización")
    st.caption("El programa propone el paso a partir de B; el calculista puede adoptar un nivel predefinido o introducir un valor propio.")
    d1, d2, d3, d4 = st.columns([1.0, 1.15, 1.0, 1.0])
    z_max_m = d1.number_input(
        "Profundidad bajo la base (m)", min_value=0.50,
        value=max(8.0, 4.0 * b_m), step=0.50, format="%.2f",
    )
    nivel_paso = d2.selectbox(
        "Nivel de discretización",
        ["Normal · B/20", "Preliminar · B/10", "Refinado · B/40", "Personalizado"],
    )
    pasos_predefinidos = {
        "Preliminar · B/10": b_m / 10.0,
        "Normal · B/20": b_m / 20.0,
        "Refinado · B/40": b_m / 40.0,
    }
    paso_recomendado_m = b_m / 20.0
    if nivel_paso == "Personalizado":
        valor_personalizado = min(max(round(paso_recomendado_m, 3), 0.001), z_max_m * 0.50)
        if "paso_personalizado_m" not in st.session_state:
            st.session_state.paso_personalizado_m = valor_personalizado
        elif st.session_state.paso_personalizado_m >= z_max_m * 0.99:
            st.session_state.paso_personalizado_m = valor_personalizado
        paso_m = d3.number_input(
            "Paso vertical adoptado Δz (m)", min_value=0.001,
            max_value=float(z_max_m * 0.99), step=0.01, format="%.3f",
            key="paso_personalizado_m",
        )
    else:
        paso_m = pasos_predefinidos[nivel_paso]
        d3.metric("Paso vertical adoptado", f"{paso_m:.3f} m")
    intervalos_estimados = int(np.ceil(z_max_m / paso_m))
    d4.metric("Intervalos estimados", f"{intervalos_estimados}")
    st.caption(
        f"Paso normal recomendado B/20 = {paso_recomendado_m:.3f} m · "
        "las interfaces de los estratos se insertarán exactamente y pueden aumentar el número final de intervalos."
    )
    if paso_m > b_m / 10.0:
        st.warning("El paso adoptado es mayor que B/10. Se recomienda comprobar el caso con Δz ≤ B/20.")
    st.markdown("**Puntos de control**")
    st.write("Centro, centros de los bordes B y L, esquina y dos puntos exteriores situados a una distancia B o L del centro.")
    st.warning("La distribución de tensiones corresponde a un semiespacio homogéneo; la estratificación se aplica al módulo de deformación.")

with tabs[1]:
    st.subheader("Perfil estratigráfico")
    st.caption("Las cotas de las capas y del nivel freático se miden hacia abajo desde la superficie del terreno.")
    t1, t2 = st.columns([1.0, 2.0])
    nivel_freatico_m = t1.number_input("Nivel freático (m)", min_value=0.0, value=2.50, step=0.10, format="%.2f")
    t2.info("Introduzca E y ν para cada estrato. M se calcula automáticamente. γap se usa sobre el nivel freático y γsat por debajo.")
    columnas = {
        "Estrato": st.column_config.TextColumn("Estrato", required=True, width="medium"),
        "z_sup_m": st.column_config.NumberColumn("z sup (m)", min_value=0.0, format="%.2f", required=True),
        "z_inf_m": st.column_config.NumberColumn("z inf (m)", min_value=0.0, format="%.2f", required=True),
        "gamma_ap_kN_m3": st.column_config.NumberColumn("γap (kN/m³)", min_value=0.1, format="%.2f", required=True),
        "gamma_sat_kN_m3": st.column_config.NumberColumn("γsat (kN/m³)", min_value=0.1, format="%.2f", required=True),
        "E_MPa": st.column_config.NumberColumn("E (MPa)", min_value=0.001, format="%.2f", required=True),
        "nu": st.column_config.NumberColumn("ν (-)", min_value=0.101, max_value=0.498, format="%.3f", required=True),
    }
    tabla_entrada = st.session_state.estratos.reindex(columns=COLUMNAS_ESTRATOS)
    estratos_editados = st.data_editor(
        tabla_entrada,
        column_config=columnas,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="editor_estratos",
    )
    st.session_state.estratos = estratos_editados
    nu_editado = pd.to_numeric(estratos_editados.get("nu"), errors="coerce")
    e_editado = pd.to_numeric(estratos_editados.get("E_MPa"), errors="coerce")
    if (nu_editado >= 0.45).any():
        st.warning(
            "Se han introducido valores de ν próximos a 0.5. M crece con rapidez y el método "
            "de integración vertical pierde representatividad para respuesta casi incompresible."
        )
    denominador = (1.0 + nu_editado) * (1.0 - 2.0 * nu_editado)
    m_derivado = e_editado * (1.0 - nu_editado) / denominador
    tabla_modulos = pd.DataFrame(
        {
            "Estrato": estratos_editados["Estrato"],
            "E (MPa)": e_editado,
            "ν (-)": nu_editado,
            "M derivado (MPa)": m_derivado,
        }
    )
    with st.expander("Módulos derivados", expanded=False):
        st.dataframe(tabla_modulos, use_container_width=True, hide_index=True)
    espesores_utiles = []
    for _, capa in estratos_editados.iterrows():
        try:
            espesor = max(
                0.0,
                min(float(capa["z_inf_m"]), df_m + z_max_m)
                - max(float(capa["z_sup_m"]), df_m),
            )
            if espesor > 0.0:
                espesores_utiles.append(espesor)
        except (TypeError, ValueError):
            pass
    if espesores_utiles and paso_m > min(espesores_utiles) / 3.0:
        st.warning(
            f"El estrato más delgado dentro del dominio tiene {min(espesores_utiles):.3f} m. "
            "El paso adoptado genera menos de tres intervalos en ese espesor."
        )

cimentacion = Cimentacion(b_m=b_m, l_m=l_m, q_neta_kpa=q_kpa, df_m=df_m)
proyecto = {"proyecto": proyecto_nombre, "localizacion": localizacion, "autor": autor, "observaciones": observaciones}
payload = {
    "b": b_m, "l": l_m, "q": q_kpa, "df": df_m, "nf": nivel_freatico_m,
    "zmax": z_max_m, "paso": paso_m, "nivel_paso": nivel_paso,
    "proyecto": proyecto,
}
firma_actual = firma_caso(payload, estratos_editados)

with st.sidebar:
    st.subheader("Navegación")
    st.caption("Introduzca los datos en las pestañas superiores, calcule y revise los indicadores de control.")
    st.divider()
    st.subheader("Acciones")
    calcular = st.button("Calcular caso", type="primary", use_container_width=True)
    limpiar = st.button("Restablecer estratos", use_container_width=True)
    if limpiar:
        st.session_state.estratos = estratos_ejemplo()
        st.session_state.pop("resultado", None)
        st.session_state.pop("resultado_steinbrenner", None)
        st.rerun()

    if calcular:
        errores = cimentacion.validar()
        capas, errores_capas = validar_estratos(
            estratos_editados, df_m + z_max_m
        )
        errores.extend(errores_capas)
        if paso_m >= z_max_m:
            errores.append("El paso vertical debe ser menor que la profundidad analizada.")
        if int(np.ceil(z_max_m / paso_m)) > 20_000:
            errores.append("El paso vertical genera más de 20 000 intervalos.")
        if errores:
            st.session_state.errores = errores
            st.session_state.pop("resultado", None)
            st.session_state.pop("resultado_steinbrenner", None)
        else:
            with st.spinner("Integrando tensiones y deformaciones..."):
                st.session_state.resultado = calcular_caso(
                    cimentacion, capas, nivel_freatico_m, z_max_m, paso_m
                )
                st.session_state.resultado_steinbrenner = calcular_steinbrenner(
                    cimentacion, capas, z_max_m
                )
                st.session_state.capas_calculadas = capas
                st.session_state.firma_resultado = firma_actual
                st.session_state.errores = []
                capas_exportacion = capas.copy()
                capas_exportacion["M_calculo_MPa"] = modulo_confinado_kpa(capas) / 1000.0
                st.session_state.docx_resultado = crear_informe_docx(
                    proyecto, cimentacion, capas_exportacion,
                    nivel_freatico_m, z_max_m, st.session_state.resultado,
                    st.session_state.resultado_steinbrenner,
                )
                st.session_state.xlsx_resultado = crear_excel(
                    cimentacion, capas_exportacion,
                    nivel_freatico_m, z_max_m, st.session_state.resultado,
                    st.session_state.resultado_steinbrenner,
                )

    st.divider()
    st.subheader("Estado")
    if st.session_state.get("errores"):
        st.error("Revise las entradas")
        for error in st.session_state.errores:
            st.caption(f"• {error}")
    elif "resultado" in st.session_state:
        if st.session_state.get("firma_resultado") != firma_actual:
            st.warning("Entradas modificadas · recalcule")
        else:
            st.success("Resultados actualizados")
            resultado_sidebar = st.session_state.resultado
            s_centro = resultado_sidebar.resumen_puntos.loc[
                resultado_sidebar.resumen_puntos["Punto"] == "Centro", "asiento_base_mm"
            ].iloc[0]
            st.metric("Asiento central", f"{s_centro:.2f} mm")
            s_stein = st.session_state.resultado_steinbrenner.resumen_puntos.loc[
                st.session_state.resultado_steinbrenner.resumen_puntos["Punto"] == "Centro",
                "asiento_base_mm",
            ].iloc[0]
            st.metric("Steinbrenner central", f"{s_stein:.2f} mm")
    else:
        st.info("Caso pendiente de cálculo")

resultado = st.session_state.get("resultado")
resultado_steinbrenner = st.session_state.get("resultado_steinbrenner")
resultado_vigente = (
    resultado is not None
    and resultado_steinbrenner is not None
    and st.session_state.get("firma_resultado") == firma_actual
)

with tabs[2]:
    st.subheader("Resultados del cálculo")
    if not resultado_vigente:
        st.info("Calcule el caso o actualice los resultados después de modificar las entradas.")
    else:
        tab_integracion, tab_steinbrenner = st.tabs(
            ["Integración vertical Δσz/M", "Steinbrenner E–ν"]
        )
        with tab_integracion:
            resumen = resultado.resumen_puntos
            asiento_centro = float(resumen.loc[resumen["Punto"] == "Centro", "asiento_base_mm"].iloc[0])
            asiento_esquina = float(resumen.loc[resumen["Punto"] == "Esquina", "asiento_base_mm"].iloc[0])
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Asiento bajo el centro", f"{asiento_centro:.2f} mm")
            m2.metric("Asiento bajo la esquina", f"{asiento_esquina:.2f} mm")
            m3.metric("Error de discretización", f"{resultado.error_discretizacion_pct:.3f} %")
            m4.metric("Aporte del último 10 %", f"{resultado.contribucion_tramo_final_pct:.2f} %")
            st.caption(
                f"Δz adoptado = {resultado.paso_adoptado_m:.3f} m ({resultado.intervalos_adoptados} intervalos) · "
                f"control con Δz/2 = {resultado.paso_control_m:.3f} m ({resultado.intervalos_control} intervalos)."
            )
            if resultado.contribucion_tramo_final_pct > 2.0:
                st.warning("El tramo final mantiene una contribución apreciable. Amplíe la profundidad y compruebe la estabilización del asiento.")
            c1, c2 = st.columns(2)
            c1.plotly_chart(figura_tensiones(resultado), use_container_width=True)
            c2.plotly_chart(figura_asientos(resultado), use_container_width=True)
            c3, c4 = st.columns(2)
            c3.plotly_chart(figura_deformacion(resultado), use_container_width=True)
            c4.plotly_chart(figura_aporte_estratos(resultado), use_container_width=True)
            st.markdown("**Asientos en puntos de control**")
            st.dataframe(resumen, use_container_width=True, hide_index=True)
            st.markdown("**Contribución por estrato bajo el centro**")
            st.dataframe(resultado.resumen_estratos, use_container_width=True, hide_index=True)

        with tab_steinbrenner:
            stein = st.session_state.resultado_steinbrenner
            resumen_stein = stein.resumen_puntos
            centro_stein = float(resumen_stein.loc[resumen_stein["Punto"] == "Centro", "asiento_base_mm"].iloc[0])
            esquina_stein = float(resumen_stein.loc[resumen_stein["Punto"] == "Esquina", "asiento_base_mm"].iloc[0])
            s1, s2, s3 = st.columns(3)
            s1.metric("Asiento bajo el centro", f"{centro_stein:.2f} mm")
            s2.metric("Asiento bajo la esquina", f"{esquina_stein:.2f} mm")
            s3.metric("Estratos calculados", f"{len(stein.resumen_estratos)}")
            st.caption("Cálculo independiente mediante E y ν; no utiliza M ni el paso vertical Δz.")
            sc1, sc2 = st.columns(2)
            sc1.plotly_chart(figura_asientos_steinbrenner(stein), use_container_width=True)
            sc2.plotly_chart(figura_aporte_steinbrenner(stein), use_container_width=True)
            st.markdown("**Asientos en puntos de control**")
            st.dataframe(resumen_stein, use_container_width=True, hide_index=True)
            st.markdown("**Contribución por estrato bajo el centro**")
            st.dataframe(stein.resumen_estratos, use_container_width=True, hide_index=True)

with tabs[3]:
    st.subheader("Entorno del bulbo de influencia")
    if not resultado_vigente:
        st.info("Los mapas estarán disponibles después de calcular el caso.")
    else:
        eje = st.segmented_control("Sección vertical", ["Dirección B", "Dirección L"], default="Dirección B")
        malla = resultado.malla_corta if eje == "Dirección B" else resultado.malla_larga
        st.plotly_chart(figura_bulbo(malla, cimentacion, st.session_state.capas_calculadas), use_container_width=True)
        st.caption("Las isolíneas representan Δσz/q. Las líneas horizontales discontinuas indican interfaces estratigráficas bajo la base.")

with tabs[4]:
    st.subheader("Informe y datos")
    st.caption("Los archivos reproducen exactamente el caso calculado y mantienen unidades explícitas.")
    if not resultado_vigente:
        st.info("Calcule el caso para habilitar las exportaciones.")
    else:
        d1, d2 = st.columns(2)
        d1.download_button(
            "Descargar informe DOCX", data=st.session_state.docx_resultado,
            file_name="informe_asiento_zapata_flexible.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
        d2.download_button(
            "Descargar datos XLSX", data=st.session_state.xlsx_resultado,
            file_name="datos_asiento_zapata_flexible.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.caption("El informe incluye las principales figuras y tablas. El Excel contiene perfiles completos y mallas de tensión en las direcciones B y L.")

with tabs[5]:
    st.subheader("Formulación utilizada")
    st.caption("Convención: compresión positiva; z se mide desde la base de la cimentación.")
    st.markdown("**Incremento de tensión bajo la esquina de un rectángulo**")
    st.latex(r"\Delta\sigma_z=q\,I_z(m,n),\qquad m=\frac{B}{z},\quad n=\frac{L}{z}")
    st.latex(r"I_z=\frac{1}{2\pi}\left[\tan^{-1}\left(\frac{mn}{\sqrt{1+m^2+n^2}}\right)+\frac{mn}{\sqrt{1+m^2+n^2}}\left(\frac{1}{1+m^2}+\frac{1}{1+n^2}\right)\right]")
    st.write("Para puntos arbitrarios se aplica superposición con signo de las cuatro esquinas del área cargada.")
    st.markdown("**Módulo confinado y deformación vertical**")
    st.latex(r"M=\frac{E(1-\nu)}{(1+\nu)(1-2\nu)},\qquad \varepsilon_z(z)=\frac{\Delta\sigma_z(z)}{M(z)}")
    st.latex(r"s(x,y)=\int_0^{z_{\max}}\frac{\Delta\sigma_z(x,y,z)}{M(z)}\,dz")
    st.latex(r"s(x,y)\approx\sum_i \frac{\Delta\sigma_z(x,y,z_{m,i})}{M_i}\,\Delta z_i")
    st.write("La suma se evalúa en el punto medio de cada intervalo. Las interfaces de estrato se incorporan como nodos exactos y el control se repite con Δz/2.")
    st.markdown("**Tensiones geostáticas**")
    st.latex(r"\sigma_{v0}(z)=\int_0^z\gamma(\zeta)\,d\zeta,\qquad u(z)=\gamma_w\max(z-z_w,0),\qquad \sigma'_{v0}=\sigma_{v0}-u")
    st.markdown("**Steinbrenner**")
    st.latex(r"s=\frac{qB'(1-\nu^2)}{E}\left[I_1+\frac{1-2\nu}{1-\nu}I_2\right]")
    st.latex(r"m_r=\frac{L'}{B'},\qquad n_r=\frac{H}{B'}")
    st.latex(r"\begin{aligned} I_1=\frac{1}{\pi}\Bigg[&m_r\ln\left(\frac{(1+\sqrt{m_r^2+1})\sqrt{m_r^2+n_r^2}}{m_r(1+\sqrt{m_r^2+n_r^2+1})}\right)\\ &+\ln\left(\frac{(m_r+\sqrt{m_r^2+1})\sqrt{1+n_r^2}}{m_r+\sqrt{m_r^2+n_r^2+1}}\right)\Bigg] \end{aligned}")
    st.latex(r"I_2=\frac{n_r}{2\pi}\tan^{-1}\left(\frac{m_r}{n_r\sqrt{m_r^2+n_r^2+1}}\right)")
    st.write("Cada capa se obtiene por diferencia entre la compresión acumulada en sus límites. Bajo puntos arbitrarios se aplica superposición de rectángulos. El cálculo se ejecuta de forma independiente y no emplea M ni Δz.")
    st.markdown("**Alcance**")
    st.write(
        "Cimentación flexible, presión neta uniforme, elasticidad lineal y compresión vertical confinada. "
        "No se consideran consolidación, deformación secundaria, plasticidad, anisotropía ni interacción rígida suelo estructura. "
        "La solución de tensiones no corrige la redistribución causada por contrastes de rigidez entre capas. "
        "Steinbrenner se aplica sobre el plano de apoyo con q neta, sin un factor adicional de empotramiento."
    )

