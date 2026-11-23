from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
import streamlit as st

from calculos.asientos import calcular_caso, modulo_confinado_kpa
from calculos.rigidez import AjusteRigidez, tabla_aportes_con_porcentaje
from calculos.steinbrenner import calcular_steinbrenner
from modelos.datos import COLUMNAS_ESTRATOS, Cimentacion, estratos_ejemplo, validar_estratos
from servicios.exportacion_docx import crear_informe_docx
from servicios.exportacion_excel import crear_excel
from utiles.estilos import CSS_APP
from visualizacion.esquema import figura_esquema_cimentacion
from visualizacion.graficos import (
    figura_asientos,
    figura_asientos_steinbrenner,
    figura_bulbo,
    figura_deformacion,
    figura_tensiones,
)


st.set_page_config(
    page_title="Asientos de zapata rectangular",
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
st.title("Asientos de zapata rectangular")
st.markdown(
    '<div class="geo-subtitle">Distribución de tensiones y asiento elástico multicapa con corrección opcional de rigidez.</div>',
    unsafe_allow_html=True,
)

tabs = st.tabs(
    [
        "01 · Geometría",
        "02 · Terreno",
        "03 · Resultados",
        "04 · Bulbo",
        "05 · Informes",
        "06 · Formulación",
    ]
)

with tabs[0]:
    st.subheader("Datos del caso")
    st.caption("Defina la referencia del proyecto y la geometría de la cimentación. La carga introducida debe ser neta.")
    c1, c2 = st.columns([1.35, 1.0])
    with c1:
        proyecto_nombre = st.text_input("Proyecto", "Zapata rectangular - Caso 01")
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

        considerar_rigida = st.checkbox(
            "Considerar zapata rígida mediante factor simplificado",
            value=False,
            help="Corrige el asiento flexible central sin recalcular la distribución de presiones.",
        )
        if considerar_rigida:
            factor_rigidez = st.number_input(
                "Factor de rigidez Cr",
                min_value=0.01,
                max_value=1.00,
                value=0.80,
                step=0.01,
                format="%.2f",
            )
            st.caption("Asiento adoptado: sr = Cr · sf,centro. Valor inicial Cr = 0,80.")
        else:
            factor_rigidez = 0.80
            st.caption("Modelo flexible activo. La presión neta se considera uniforme.")

    st.divider()
    st.subheader("Esquema de la cimentación")
    st.caption("Vista en planta proporcional a B y L; la sección estratigráfica se muestra en la pestaña Terreno.")
    st.plotly_chart(figura_esquema_cimentacion(b_m, l_m), use_container_width=True)
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
        "nu": st.column_config.NumberColumn("ν (-)", min_value=0.0, max_value=0.498, format="%.3f", required=True),
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
    with st.expander("Vista esquemática del perfil geotécnico", expanded=True):
        from visualizacion.esquema import figura_perfil_estratos
        st.plotly_chart(
            figura_perfil_estratos(estratos_editados, df_m, nivel_freatico_m),
            use_container_width=True,
        )
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
ajuste_rigidez = AjusteRigidez(considerar_rigida=considerar_rigida, factor=factor_rigidez)
proyecto = {"proyecto": proyecto_nombre, "localizacion": localizacion, "autor": autor, "observaciones": observaciones}
payload = {
    "b": b_m, "l": l_m, "q": q_kpa, "df": df_m, "nf": nivel_freatico_m,
    "zmax": z_max_m, "paso": paso_m, "nivel_paso": nivel_paso,
    "considerar_rigida": considerar_rigida, "factor_rigidez": factor_rigidez,
    "proyecto": proyecto,
}
firma_actual = firma_caso(payload, estratos_editados)

with st.sidebar:
    st.subheader("Flujo de trabajo")
    st.caption("01 Datos → 02 Terreno → 03 Resultados → 04 Bulbo → 05 Informes")
    st.caption("Los informes se generan únicamente a petición del usuario.")
    st.divider()
    st.subheader("Acciones")
    calcular = st.button("Calcular caso", type="primary", use_container_width=True)
    limpiar = st.button("Restablecer estratos", use_container_width=True)
    if limpiar:
        st.session_state.estratos = estratos_ejemplo()
        st.session_state.pop("resultado", None)
        st.session_state.pop("resultado_steinbrenner", None)
        st.session_state.pop("docx_resultado", None)
        st.session_state.pop("xlsx_resultado", None)
        st.rerun()

    if calcular:
        errores = cimentacion.validar()
        errores.extend(ajuste_rigidez.validar())
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
            st.session_state.pop("docx_resultado", None)
            st.session_state.pop("xlsx_resultado", None)
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
                st.session_state.pop("docx_resultado", None)
                st.session_state.pop("xlsx_resultado", None)

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
            st.metric(
                f"Integración · {ajuste_rigidez.tipo}",
                f"{ajuste_rigidez.asiento_adoptado_mm(float(s_centro)):.2f} mm",
            )
            s_stein = st.session_state.resultado_steinbrenner.resumen_puntos.loc[
                st.session_state.resultado_steinbrenner.resumen_puntos["Punto"] == "Centro",
                "asiento_base_mm",
            ].iloc[0]
            st.metric(
                f"Steinbrenner · {ajuste_rigidez.tipo}",
                f"{ajuste_rigidez.asiento_adoptado_mm(float(s_stein)):.2f} mm",
            )
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
        puntos_disponibles = resultado.resumen_puntos["Punto"].tolist()
        puntos_visibles = st.multiselect(
            "Puntos visibles en los perfiles",
            puntos_disponibles,
            default=["Centro", "Borde B", "Borde L", "Esquina"],
            help="Los puntos exteriores permanecen disponibles para revisión específica.",
        )
        if not puntos_visibles:
            puntos_visibles = ["Centro"]
        st.markdown("#### Resumen de asientos bajo el centro")
        centro_b = float(resultado.resumen_puntos.loc[
            resultado.resumen_puntos["Punto"] == "Centro", "asiento_base_mm"].iloc[0])
        centro_s = float(resultado_steinbrenner.resumen_puntos.loc[
            resultado_steinbrenner.resumen_puntos["Punto"] == "Centro", "asiento_base_mm"].iloc[0])
        k1, k2 = st.columns(2)
        k1.metric("Boussinesq + M · asiento adoptado", f"{ajuste_rigidez.asiento_adoptado_mm(centro_b):.2f} mm")
        k2.metric("Steinbrenner · asiento adoptado", f"{ajuste_rigidez.asiento_adoptado_mm(centro_s):.2f} mm")
        st.caption("Cada resultado se obtiene de forma independiente. Los perfiles detallados se presentan por método.")
        tab_integracion, tab_steinbrenner = st.tabs(
            ["Integración vertical Δσz/M", "Steinbrenner E–ν"]
        )
        with tab_integracion:
            resumen = resultado.resumen_puntos
            asiento_centro = float(resumen.loc[resumen["Punto"] == "Centro", "asiento_base_mm"].iloc[0])
            asiento_esquina = float(resumen.loc[resumen["Punto"] == "Esquina", "asiento_base_mm"].iloc[0])
            asiento_adoptado = ajuste_rigidez.asiento_adoptado_mm(asiento_centro)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(f"Asiento de zapata {ajuste_rigidez.tipo.lower()}", f"{asiento_adoptado:.2f} mm")
            m2.metric(
                "Flexible central de partida" if considerar_rigida else "Asiento bajo la esquina",
                f"{asiento_centro if considerar_rigida else asiento_esquina:.2f} mm",
            )
            m3.metric("Error de discretización", f"{resultado.error_discretizacion_pct:.3f} %")
            m4.metric("Aporte del último 10 %", f"{resultado.contribucion_tramo_final_pct:.2f} %")
            if considerar_rigida:
                st.caption(
                    f"Corrección simplificada Cr = {factor_rigidez:.2f}. "
                    "Los perfiles y tensiones mostrados corresponden al cálculo flexible de presión uniforme."
                )
            else:
                st.caption(f"Asiento flexible bajo la esquina = {asiento_esquina:.2f} mm.")
            st.caption(
                f"Δz adoptado = {resultado.paso_adoptado_m:.3f} m ({resultado.intervalos_adoptados} intervalos) · "
                f"control con Δz/2 = {resultado.paso_control_m:.3f} m ({resultado.intervalos_control} intervalos)."
            )
            if resultado.contribucion_tramo_final_pct > 2.0:
                st.warning("El tramo final mantiene una contribución apreciable. Amplíe la profundidad y compruebe la estabilización del asiento.")
            c1, c2 = st.columns(2)
            c1.plotly_chart(
                figura_tensiones(resultado, st.session_state.capas_calculadas, cimentacion),
                use_container_width=True,
            )
            c2.plotly_chart(
                figura_asientos(
                    resultado, puntos_visibles, st.session_state.capas_calculadas, cimentacion
                ),
                use_container_width=True,
            )
            with st.expander("Resultados avanzados", expanded=False):
                st.plotly_chart(
                    figura_deformacion(resultado, st.session_state.capas_calculadas, cimentacion),
                    use_container_width=True,
                )
            st.markdown("**Asientos en puntos de control**")
            st.dataframe(resumen, use_container_width=True, hide_index=True)
            st.markdown("**Contribución por estrato bajo el centro**")
            st.dataframe(
                tabla_aportes_con_porcentaje(resultado.resumen_estratos),
                use_container_width=True,
                hide_index=True,
            )

        with tab_steinbrenner:
            stein = st.session_state.resultado_steinbrenner
            resumen_stein = stein.resumen_puntos
            centro_stein = float(resumen_stein.loc[resumen_stein["Punto"] == "Centro", "asiento_base_mm"].iloc[0])
            esquina_stein = float(resumen_stein.loc[resumen_stein["Punto"] == "Esquina", "asiento_base_mm"].iloc[0])
            adoptado_stein = ajuste_rigidez.asiento_adoptado_mm(centro_stein)
            s1, s2, s3 = st.columns(3)
            s1.metric(f"Asiento de zapata {ajuste_rigidez.tipo.lower()}", f"{adoptado_stein:.2f} mm")
            s2.metric(
                "Flexible central de partida" if considerar_rigida else "Asiento bajo la esquina",
                f"{centro_stein if considerar_rigida else esquina_stein:.2f} mm",
            )
            s3.metric("Estratos calculados", f"{len(stein.resumen_estratos)}")
            detalle_rigidez = (
                f" Corrección simplificada Cr = {factor_rigidez:.2f}." if considerar_rigida else ""
            )
            st.caption(
                "Cálculo independiente mediante E y ν; no utiliza M ni el paso vertical Δz."
                + detalle_rigidez
            )
            st.plotly_chart(
                figura_asientos_steinbrenner(
                    stein, puntos_visibles, st.session_state.capas_calculadas, cimentacion
                ),
                use_container_width=True,
            )
            st.markdown("**Asientos en puntos de control**")
            st.dataframe(resumen_stein, use_container_width=True, hide_index=True)
            st.markdown("**Contribución por estrato bajo el centro**")
            st.dataframe(
                tabla_aportes_con_porcentaje(stein.resumen_estratos),
                use_container_width=True,
                hide_index=True,
            )

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
    st.subheader("Informes y exportaciones")
    st.caption("Generación manual e independiente. Los documentos se conservan hasta que cambie el caso calculado.")
    if not resultado_vigente:
        st.info("Calcule el caso o recalcule después de modificar las entradas para habilitar la exportación.")
    else:
        col_docx, col_excel = st.columns(2)
        with col_docx:
            st.markdown("#### Informe técnico · DOCX")
            st.caption("Memoria de cálculo, resultados, tablas y figuras.")
            if st.button("Generar informe DOCX", key="generar_docx", use_container_width=True):
                with st.spinner("Preparando el informe DOCX..."):
                    capas_exportacion = st.session_state.capas_calculadas.copy()
                    capas_exportacion["M_calculo_MPa"] = modulo_confinado_kpa(capas_exportacion) / 1000.0
                    st.session_state.docx_resultado = crear_informe_docx(
                        proyecto, cimentacion, capas_exportacion, nivel_freatico_m, z_max_m,
                        resultado, resultado_steinbrenner, ajuste_rigidez,
                    )
            if st.session_state.get("docx_resultado") is not None:
                st.success("Informe preparado")
                st.download_button(
                    "Descargar DOCX", data=st.session_state.docx_resultado,
                    file_name="informe_asiento_zapata_rectangular.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )
        with col_excel:
            st.markdown("#### Datos y resultados · XLSX")
            st.caption("Perfiles numéricos, tensiones, estratos y resultados.")
            if st.button("Generar Excel", key="generar_xlsx", use_container_width=True):
                with st.spinner("Preparando el libro Excel..."):
                    capas_exportacion = st.session_state.capas_calculadas.copy()
                    capas_exportacion["M_calculo_MPa"] = modulo_confinado_kpa(capas_exportacion) / 1000.0
                    st.session_state.xlsx_resultado = crear_excel(
                        cimentacion, capas_exportacion, nivel_freatico_m, z_max_m,
                        resultado, resultado_steinbrenner, ajuste_rigidez,
                    )
            if st.session_state.get("xlsx_resultado") is not None:
                st.success("Excel preparado")
                st.download_button(
                    "Descargar XLSX", data=st.session_state.xlsx_resultado,
                    file_name="datos_asiento_zapata_rectangular.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )

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
    st.markdown("**Corrección simplificada de rigidez**")
    st.latex(r"s_r=C_r\,s_{f,c},\qquad C_r=0{,}80\ \text{por defecto}")
    st.write(
        "La corrección se aplica únicamente al asiento flexible central. No modifica las tensiones, "
        "los perfiles flexibles ni calcula la redistribución de presiones de contacto de una base rígida."
    )
    st.markdown("**Alcance**")
    st.write(
        "Cimentación flexible con corrección opcional de rigidez, presión neta uniforme, elasticidad lineal y compresión vertical confinada. "
        "No se consideran consolidación, deformación secundaria, plasticidad, anisotropía ni interacción rígida suelo estructura. "
        "La solución de tensiones no corrige la redistribución causada por contrastes de rigidez entre capas. "
        "Steinbrenner se aplica sobre el plano de apoyo con q neta, sin un factor adicional de empotramiento."
    )

