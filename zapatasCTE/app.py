"""Cimentaciones superficiales: malla BxL, hundimiento y asiento elástico.

Prototipo técnico; no sustituye la verificación del proyecto conforme al CTE.
"""
from __future__ import annotations

from math import isfinite
from dataclasses import replace
import hashlib
import json

import pandas as pd
import streamlit as st

from calculos.agua import GAMMA_AGUA_KN_M3, gamma_sumergido_desde_saturado
from calculos.capacidad_portante import _peso_especifico_representativo
from calculos.analisis_corridas import (
    convergencia_corrida, convergencia_porcentaje_final,
    comparativa_corridas, sensibilidad_nivel_freatico,
)
from calculos.diagnostico_asientos import (
    calcular_perfil_bulbo, contribuciones_steinbrenner, profundidad_porcentaje_asiento,
    descarga_preexistente_kpa,
)
from visualizacion.graficos_asientos import (
    figura_bulbo, figura_asiento_acumulado, figura_contribuciones,
)
from calculos.malla import (
    LONGITUD_CORRIDA_INTERNA_M,
    LONGITUD_CORRIDA_HUNDIMIENTO_M,
    avisos_globales,
    calcular_corridas,
    calcular_malla,
)
from modelos.datos import CapaSuelo, DatosAsientos, DatosHundimiento, DatosProyecto
from modelos.geometrias import RangoGeometrico, generar_geometrias, serie_rango
from utiles.tablas_malla import CAMPOS_MAPA, tabla_malla
from visualizacion.graficos_malla import curvas_seccion, grafico_geom, mapa_calor, grafico_presiones_corridas
from visualizacion.graficos_bulbo_2d import figura_seccion_bulbo
from visualizacion.metodologia import mostrar_compendio
from visualizacion.graficos_corridas import (
    mapa_calor_corridas, grafico_balasto, grafico_convergencia,
    grafico_comparativa, grafico_sensibilidad,
)

st.set_page_config(page_title="Cimentaciones superficiales · B × L", page_icon="▦", layout="wide")
st.markdown("""
<style>
:root{--blue:#142d48;--red:#c94f59;--line:#dce5ed;--muted:#66768c}
.block-container{max-width:1540px;padding-top:2rem}
h1,h2,h3{color:var(--blue)!important}
h1{font-size:2.05rem!important}
.small-intro{color:var(--muted);margin-top:-.4rem;margin-bottom:1rem}
.stButton>button[kind="primary"]{background:var(--red);border-color:var(--red)}
[data-testid="stMetric"]{border-left:3px solid var(--red);padding-left:.8rem}
[data-testid="stDataFrame"]{border:1px solid var(--line)}
.tabla-presiones{width:100%;border-collapse:collapse;margin:.55rem 0 1rem}
.tabla-presiones th,.tabla-presiones td{padding:.55rem .65rem;border-bottom:1px solid var(--line)}
.tabla-presiones th{font-size:.87rem;font-weight:600;text-align:right}
.tabla-presiones th:first-child,.tabla-presiones td:first-child{text-align:left}
.tabla-presiones td{font-size:1.05rem}
.tabla-presiones td:not(:first-child){text-align:right;font-weight:600;font-variant-numeric:tabular-nums}
.tabla-presiones .fila-servicio{background:rgba(65,122,173,.10);font-weight:700}
</style>
""", unsafe_allow_html=True)


def capas_desde_tabla(tabla: pd.DataFrame) -> tuple[CapaSuelo, ...]:
    capas = []
    for i, (_, fila) in enumerate(tabla.iterrows(), 1):
        if any(pd.isna(fila.get(c)) for c in ("z sup. (m)","z inf. (m)","E (MPa)","nu")):
            raise ValueError(f"Estrato {i}: faltan valores obligatorios.")
        capas.append(CapaSuelo(
            nombre=str(fila.get("Unidad") or f"Nivel {i}"),
            z_superior_m=float(fila["z sup. (m)"]),
            z_inferior_m=float(fila["z inf. (m)"]),
            modulo_mpa=float(fila["E (MPa)"]),
            poisson=float(fila["nu"]),
        ))
    return tuple(capas)


def formatear(valor: float | None, decimales: int=3) -> str:
    return "No válido" if valor is None or not isfinite(valor) else f"{valor:.{decimales}f}"


def mostrar_tabla_presiones(resultado) -> None:
    """INC-02: presenta las presiones ya calculadas sin alterar el motor."""
    filas = (
        ("Hundimiento", resultado.q_hund_neta_mpa, resultado.q_hund_bruta_mpa),
        ("Asientos", resultado.q_asiento_neta_mpa, resultado.q_asiento_bruta_mpa),
        ("Servicio", resultado.q_serv_neta_mpa, resultado.q_serv_bruta_mpa),
    )
    cuerpo = "".join(
        f'<tr class="{"fila-servicio" if etiqueta == "Servicio" else ""}">'
        f"<td>{etiqueta}</td><td>{formatear(neta)}</td>"
        f"<td>{formatear(bruta)}</td></tr>"
        for etiqueta, neta, bruta in filas
    )
    st.markdown(
        '<table class="tabla-presiones" aria-label="Presiones admisibles netas y brutas">'
        '<thead><tr><th>Comprobación</th><th>Neta (MPa)</th>'
        '<th>Bruta (MPa)</th></tr></thead><tbody>'
        + cuerpo + '</tbody></table>',
        unsafe_allow_html=True,
    )


st.caption("GEO APP / GEOTECNIA / PROTOTIPO TÉCNICO")
st.title("Presiones admisibles · Zapatas B × L")
st.markdown('<p class="small-intro">Hundimiento (CTE DB-SE-C), asientos elásticos por estratos y balasto. Malla rectangular con B ≤ L.</p>',unsafe_allow_html=True)

with st.sidebar:
    st.subheader("Análisis de cimentaciones")
    st.caption("Complete las entradas en las primeras tres pestañas y pulse «Calcular» en Resultados.")
    st.divider()
    st.info("Presiones de comparación: **netas**. También se proporcionan las equivalentes **brutas**.")
    st.caption("Hipótesis: carga vertical centrada, base horizontal, dimensiones B y L ya equivalentes si existen excentricidades.")
    st.divider()
    st.caption("Comparativa corrida: longitudes internas originales fijas, L de asientos = 100 m y L de hundimiento = 1000 m.")
    st.caption("Herramienta de predimensionamiento pendiente de validación profesional completa.")

tab_ini,tab_hund,tab_as,tab_res = st.tabs(["Datos iniciales","Hundimiento","Asientos","Resultados"])

with tab_ini:
    st.header("Datos iniciales")
    uno,dos=st.columns([1.0,1.2],gap="large")
    with uno:
        st.subheader("Identificación del proyecto")
        peticionario=st.text_input("Peticionario",value="")
        trabajo=st.text_input("Trabajo",value="")
        expediente=st.text_input("Expediente",value="")
    with dos:
        st.subheader("Barrido dimensional")
        st.caption("Introduzca rangos en metros. Se evalúan automáticamente todas las parejas 0 < B ≤ L.")
        ba,bb,bc=st.columns(3)
        with ba: bmin=st.number_input("Bmin (m)",min_value=0.05,value=1.5,step=0.25,format="%.2f")
        with bb: bmax=st.number_input("Bmax (m)",min_value=0.05,value=3.0,step=0.25,format="%.2f")
        with bc: incr_b=st.number_input("incrB (m)",min_value=0.01,value=0.5,step=0.05,format="%.2f")
        la,lb,lc=st.columns(3)
        with la: lmin=st.number_input("Lmin (m)",min_value=0.05,value=1.5,step=0.25,format="%.2f")
        with lb: lmax=st.number_input("Lmax (m)",min_value=0.05,value=5.0,step=0.25,format="%.2f")
        with lc: incr_l=st.number_input("incrL (m)",min_value=0.01,value=0.5,step=0.05,format="%.2f")
        st.caption("Si el máximo no coincide exactamente con un incremento, no se añade un último tramo irregular.")
    st.info("B y L se consideran **dimensiones equivalentes** B* y L*. No se calculan excentricidades ni giros de carga.")

with tab_hund:
    st.header("Hundimiento · Resistencia del terreno")
    st.caption("Expresión 4.8 del CTE DB-SE-C y factores de forma F.3–F.5 para zapatas rectangulares.")
    c1,c2,c3=st.columns(3,gap="large")
    with c1:
        st.subheader("Situación de cálculo")
        drenaje=st.selectbox("Condición",["Persistente a largo plazo","Transitoria a corto plazo (sin drenaje)"])
        sin_drenaje=drenaje=="Transitoria a corto plazo (sin drenaje)"
        profundidad_base=st.number_input("Profundidad D (m)",min_value=0.0,value=0.5,step=0.1)
        seguridad=st.selectbox("Situación para γR",["Situación persistente","Situación transitoria","Situación extraordinaria"],index=1)
        considerar_superior=st.toggle("Aplicar factores de profundidad d",value=False,
            help="CTE Anejo F: sólo si D >= 2 m, sin taludes próximos y con permanencia garantizada del terreno superior.")
    with c2:
        st.subheader("Parámetros resistentes")
        if sin_drenaje:
            st.caption("Condición sin drenaje: φ = 0° impuesto por el modelo.")
        phi=st.number_input("Ángulo de rozamiento φ' (°)",min_value=0.0,max_value=89.0,
                            value=0.0 if sin_drenaje else 30.0,step=0.5,disabled=sin_drenaje,
                            key="phi_ud" if sin_drenaje else "phi_drenado")
        cohesion=st.number_input("c' / cu (kPa)",min_value=0.0,value=0.0 if not sin_drenaje else 50.0,step=5.0,
                                 key="cohesion_ud" if sin_drenaje else "cohesion_drenado")
        cu_aumenta=st.toggle("Perfil lineal cu(z)",value=False,disabled=not sin_drenaje)
        ua,ub=st.columns(2)
        with ua:
            cu_z0=st.number_input("z0 cu (m)",value=0.0,step=0.5,disabled=not cu_aumenta)
            cu_0=st.number_input("cu0 (kPa)",min_value=0.1,value=50.0,step=5.0,disabled=not cu_aumenta)
        with ub:
            cu_z1=st.number_input("z1 cu (m)",value=10.0,step=0.5,disabled=not cu_aumenta)
            cu_1=st.number_input("cu1 (kPa)",min_value=0.1,value=150.0,step=5.0,disabled=not cu_aumenta)
    with c3:
        st.subheader("Agua, sobrecarga y talud")
        nf=st.number_input("Nivel freático bajo rasante (m)",min_value=0.0,value=6.6,step=0.1)
        modo_gamma=st.selectbox("Origen del peso específico sumergido γ'",[
            "Introducir γ' directamente","Calcular γ' a partir de γsat"])
        gamma_sat=None
        if modo_gamma=="Introducir γ' directamente":
            gamma_ef=st.number_input("Peso específico sumergido γ' (kN/m³)",
                                    min_value=0.1,value=18.0,step=0.5)
        else:
            gamma_sat=st.number_input("Peso específico saturado γsat (kN/m³)",
                                      min_value=0.01,value=20.0,step=0.5)
            gamma_ef=gamma_sat-GAMMA_AGUA_KN_M3
            if gamma_ef > 0:
                st.metric("Peso específico sumergido calculado γ'",f"{gamma_ef:.2f} kN/m³")
            else:
                st.error("γsat debe superar al peso específico del agua (9,81 kN/m³).")
        st.caption("γ' = γsat - γagua. Se utiliza γagua = 9,81 kN/m³; verifique los parámetros geotécnicos.")
        gamma_ap=st.number_input("Peso específico aparente (kN/m³)",min_value=0.1,value=18.0,step=0.5)
        flujo=st.toggle("Flujo ascendente",value=False)
        gradiente=st.number_input("Gradiente vertical ascendente iᵥ (medio en 1,5 B)",
                                  min_value=0.0,value=0.4,step=0.05,disabled=not flujo)
        st.markdown("**Vista previa de γk (sin ejecutar la malla)**")
        b_vista=st.number_input("Anchura B para γk (m)",min_value=0.05,
                                value=float(bmin),step=0.25,key="b_vista_gamma")
        if gamma_ef > 0:
            h_vista=replace(DatosHundimiento(),profundidad_base_m=profundidad_base,
                nivel_freatico_m=nf,gamma_efectivo_kn_m3=gamma_ef,
                gamma_aparente_kn_m3=gamma_ap,flujo_ascendente=flujo,
                gradiente_vertical=gradiente)
            gamma_vista=_peso_especifico_representativo(h_vista,b_vista)
            st.metric("γk para B seleccionada",f"{gamma_vista:.2f} kN/m³")
            st.caption("Se actualiza al cambiar NF, D, B, γ' / γsat, γaparente o gradiente. "
                       "Los resultados de hundimiento se actualizan al pulsar «Calcular».")
        else:
            st.warning("γk no calculable: compruebe γsat y γ'.")
        considerar_sobrecarga=st.toggle("Incluir q0 alrededor de la base",value=True)
        sc1,sc2=st.columns(2)
        with sc1: gamma_sob=st.number_input("γ sobrecarga (kN/m³)",min_value=0.1,value=18.0,step=0.5,disabled=not considerar_sobrecarga)
        with sc2: altura_sob=st.number_input("Altura sobrecarga (m)",min_value=0.0,value=0.5,step=0.1,disabled=not considerar_sobrecarga)
        q0_vista = gamma_sob * altura_sob if considerar_sobrecarga else 0.0
        st.metric("Sobrecarga calculada q₀", f"{q0_vista:.2f} kN/m²", help="q₀ = γ sobrecarga × altura; cambia al editar los valores, sin pulsar Calcular. Si la sobrecarga no está incluida, q₀ = 0.")
        beta=st.number_input("Pendiente β (°)",min_value=0.0,max_value=89.0,value=0.0,step=0.5)
    st.caption("q₀ = γ × h se toma como presión representativa en el contorno de la base; en cálculo drenado debe representar la presión EFECTIVA y en no drenado la TOTAL. Verifique agua y permanencia de la sobrecarga. No se consideran cargas inclinadas ni excéntricas.")
    st.caption("Sin cargas horizontales, momentos ni factores de inclinación i; se exige comprobación externa para cargas no centradas o inclinadas.")

with tab_as:
    st.header("Asientos · Terreno deformable")
    st.caption("Steinbrenner por capas elásticas. Profundidades z medidas desde la base de la zapata (z=0).")
    izq,der=st.columns([0.9,2.1],gap="large")
    with izq:
        asiento_adm=st.number_input("Asiento admisible (cm)",min_value=0.01,value=5.0,step=0.5)
        tipo_balasto=st.selectbox("Tipo de terreno para Ksp30",["Cohesivo","Granular"],
            help="Relación de escala E.6 (cohesivo), E.7 (granular) y factor rectangular E.8.")
        metodo=st.radio("Asiento bajo el centro",[
            "Superposición 4 × (B/2 × L/2) — Recomendado",
            "Aproximación 2 × (B × L)",
        ],help="La superposición de cuatro cuadrantes es el modo recomendado; la aproximación permite compararse con el Excel original.")
        if metodo.startswith("Superposición"):
            st.success("s_centro = 4 × s_esquina(B/2,L/2)")
            metodo_id="superposicion"
        else:
            st.warning("s_centro = 2 × s_esquina(B,L): aproximación histórica, no recomendada para estratificados.")
            metodo_id="excel"
        st.caption("El balasto se obtiene de la flexibilidad elástica calculada y se transforma a placa de 30 cm según el material elegido.")
        st.divider()
        st.subheader("Presion inicial en la base")
        descarga_manual = st.toggle("Introducir tension de tierras excavadas manualmente", value=False,
            help="Si se desactiva, se estima con D, nivel freatico y pesos especificos. No es q0 de hundimiento.")
        sigma_descarga = (st.number_input("Tension retirada (kPa)",min_value=0.0,value=9.0,step=1.0)
                          if descarga_manual else None)
        st.caption("Se distingue la descarga previa por excavacion del q0 de contorno empleado en hundimiento.")
        st.divider()
        st.subheader("Diagnostico de tensiones")
        modo_profundidad = st.selectbox("Profundidad del grafico", ["Automatica","Manual"])
        z_manual = (st.number_input("Profundidad maxima (m)",min_value=0.5,value=20.0,step=0.5)
                    if modo_profundidad == "Manual" else None)
        paso_tensiones = st.number_input("Paso deseado del bulbo (m)",min_value=0.02,max_value=2.0,value=0.10,step=0.05)
        st.caption("Criterio de influencia: min(10% de q neta, 5% de sigma'v0); calculado con Boussinesq bajo el centro.")
    with der:
        st.subheader("Perfil de deformabilidad")
        capas_df=st.data_editor(
            pd.DataFrame({"Unidad":["NIVEL 1","NIVEL 2"],"z sup. (m)":[0.0,2.5],
                "z inf. (m)":[2.5,10.0],"E (MPa)":[15.0,30.0],"nu":[0.30,0.20]}),
            num_rows="dynamic",hide_index=True,use_container_width=True,key="perfil_capas",
            column_config={
                "Unidad":st.column_config.TextColumn(required=True),
                "z sup. (m)":st.column_config.NumberColumn(min_value=0.0,step=0.5,format="%.2f"),
                "z inf. (m)":st.column_config.NumberColumn(min_value=0.0,step=0.5,format="%.2f"),
                "E (MPa)":st.column_config.NumberColumn(min_value=0.01,step=1.0,format="%.2f"),
                "nu":st.column_config.NumberColumn(min_value=0.0,max_value=0.499,step=0.01,format="%.3f"),
            },
        )
        st.caption("Estratos contiguos sin solapes ni huecos. E > 0 y 0 ≤ ν < 0,5.")

# Los controles de entrada no ejecutan cálculos pesados en cada edición.
# El identificador también incorpora el perfil completo para detectar resultados obsoletos.
entrada_actual = {
    "proyecto": [peticionario, trabajo, expediente],
    "rango": [bmin, bmax, incr_b, lmin, lmax, incr_l],
    "hundimiento": [drenaje, profundidad_base, seguridad, considerar_superior,
        phi if not sin_drenaje else 0.0, cohesion, cu_aumenta, cu_z0, cu_0,
        cu_z1, cu_1, nf, modo_gamma, gamma_sat, gamma_ef, gamma_ap, flujo, gradiente,
        considerar_sobrecarga, gamma_sob, altura_sob, beta],
    "asientos": [asiento_adm, tipo_balasto, metodo_id, descarga_manual, sigma_descarga, modo_profundidad, z_manual, paso_tensiones],
    "capas": capas_df.to_dict(orient="records"),
}
firma_actual = hashlib.sha256(json.dumps(entrada_actual,sort_keys=True,default=str,
    ensure_ascii=False).encode("utf-8")).hexdigest()

with tab_res:
    if st.button("Calcular", type="primary", use_container_width=True, key="calcular_malla"):
        try:
            if modo_gamma!="Introducir γ' directamente":
                gamma_sumergido_desde_saturado(gamma_sat)
            rango = RangoGeometrico(bmin,bmax,incr_b,lmin,lmax,incr_l)
            geometrias = generar_geometrias(rango)
            capas = capas_desde_tabla(capas_df)
            bs = tuple(sorted({b for b,l in geometrias}))
            h = DatosHundimiento(
                situacion_drenaje=drenaje,forma="Rectangular",anchos_m=bs,
                profundidad_base_m=profundidad_base,nivel_freatico_m=nf,
                flujo_ascendente=flujo,gradiente_vertical=gradiente,inclinacion_talud_deg=beta,
                talud_transitorio_sin_drenaje=sin_drenaje,phi_deg=0.0 if sin_drenaje else phi,
                cohesion_kpa=cohesion,cu_aumenta_con_profundidad=cu_aumenta,
                cu_z_inicial_m=cu_z0,cu_inicial_kpa=cu_0,cu_z_final_m=cu_z1,cu_final_kpa=cu_1,
                gamma_efectivo_kn_m3=gamma_ef,gamma_aparente_kn_m3=gamma_ap,
                considerar_sobrecarga=considerar_sobrecarga,gamma_sobrecarga_kn_m3=gamma_sob,
                altura_sobrecarga_m=altura_sob,considerar_terreno_sobre_base=considerar_superior,
                situacion_seguridad=seguridad,longitud_corrida_m=LONGITUD_CORRIDA_INTERNA_M,
            )
            s = DatosAsientos(asiento_admisible_cm=asiento_adm,
                longitud_corrida_m=LONGITUD_CORRIDA_INTERNA_M,
                capas=capas,metodo_centro=metodo_id,tipo_material_balasto=tipo_balasto,
                descarga_excavacion_kpa=sigma_descarga)
            resultados = calcular_malla(geometrias,h,s)
            tabla = tabla_malla(resultados)
            corridas = calcular_corridas(tuple(sorted(set(tabla["B (m)"]))),h,s)
            st.session_state["ultimo_calculo"] = {
                "firma": firma_actual, "resultados": resultados, "tabla": tabla,
                "corridas": corridas, "h": h, "s": s,
                "proyecto": DatosProyecto(peticionario,trabajo,expediente),
                "paso_bulbo": paso_tensiones, "z_bulbo": z_manual,
                "origen_gamma": modo_gamma, "gamma_sat_kn_m3": gamma_sat,
            }
            st.success(f"Cálculo completado: {len(resultados)} geometrías B × L.")
        except (ValueError,TypeError,OverflowError,ZeroDivisionError,ArithmeticError) as exc:
            st.error(f"No se han actualizado los resultados. Revise los datos: {exc}")
    guardado = st.session_state.get("ultimo_calculo")
    if guardado is None:
        st.info("No hay cálculos realizados. Complete los datos de entrada y pulse «Calcular».")
        st.stop()
    resultados=guardado["resultados"]
    tabla=guardado["tabla"]
    corridas=guardado["corridas"]
    h_cal=guardado["h"]
    s_cal=guardado["s"]
    proyecto_cal=guardado["proyecto"]
    desactualizado=firma_actual != guardado["firma"]
    if desactualizado:
        st.warning("Resultados pendientes de actualizar: se muestran los resultados del último cálculo. Pulse «Calcular» para aplicar los datos modificados.")
    # Sin bloque de KPIs ni título general, como se acordó.
    with st.sidebar:
        st.divider()
        st.caption(f"Último cálculo: {len(resultados)} geometrías")
        if desactualizado:
            st.warning("Resultados pendientes de actualizar")
        st.download_button("Descargar tabla CSV",data=tabla.to_csv(index=False).encode("utf-8-sig"),
            file_name="cimentaciones_BxL_resultados.csv",mime="text/csv",
            use_container_width=True,disabled=desactualizado)
    an_tab,co_tab,met_tab=st.tabs(["Zapatas B × L","Zapatas corridas · aproximación","Metodología y formulaciones"])
    with an_tab:
        st.subheader("Zapatas cuadradas y rectangulares B × L")
        mapa_col,ficha_col=st.columns([1.4,1.0],gap="large")
        with mapa_col:
            metrica=st.selectbox("Variable representada",list(CAMPOS_MAPA),key="metrica_mapa")
            st.caption("Cada casilla corresponde a una combinación B ≤ L. Pulse una casilla o seleccione una geometría en la ficha.")
            event=st.plotly_chart(mapa_calor(tabla,metrica),use_container_width=True,
                on_select="rerun",selection_mode="points",key="mapa_puntos")
            if any(r.q_serv_neta_mpa is None for r in resultados):
                st.warning("Algunas geometrías carecen de margen neto positivo. Consulte la tabla y las advertencias.")
        with ficha_col:
            st.subheader("Ficha de la zapata")
            opciones=[f"B={r.b_m:.2f} m · L={r.l_m:.2f} m" for r in resultados]
            idx=st.selectbox("Geometría",range(len(opciones)),format_func=lambda i:opciones[i],key="geometria_ficha")
            try:
                pts=event.selection.points
                if pts:
                    xb=float(pts[0]["y"]); xl=float(pts[0]["x"])
                    seleccionado=next((r for r in resultados if abs(r.b_m-xb)<1e-8 and abs(r.l_m-xl)<1e-8),resultados[idx])
                else:
                    seleccionado=resultados[idx]
            except (AttributeError,KeyError,IndexError,TypeError,ValueError):
                seleccionado=resultados[idx]
            f1,f2,f3=st.columns(3)
            f1.metric("B",f"{seleccionado.b_m:.2f} m")
            f2.metric("L",f"{seleccionado.l_m:.2f} m")
            f3.metric("Área",f"{seleccionado.area_m2:.2f} m²")
            st.plotly_chart(grafico_geom(seleccionado.b_m,seleccionado.l_m),use_container_width=True)
            mostrar_tabla_presiones(seleccionado)
            st.write(f"**Gobierna:** {seleccionado.limitacion}")
            with st.expander("Detalle de presiones, balasto y factores"):
                st.write(f"q0 del contorno (hundimiento) = {seleccionado.q0_kpa/1000:.3f} MPa")
                st.write(f"Tension preexistente en la base = {seleccionado.sigma_pre_base_kpa/1000:.3f} MPa")
                st.write(f"k_s,BL = {seleccionado.ks_bl_mn_m3:.2f} MN/m³")
                st.write(f"Ksp30 ({s_cal.tipo_material_balasto.lower()}) = {seleccionado.ksp30_mn_m3:.2f} MN/m³")
                gamma_k=_peso_especifico_representativo(h_cal,seleccionado.b_m)
                if h_cal.flujo_ascendente:
                    caso_gamma="F.17: flujo ascendente (gradiente medio en 1,5 B)"
                else:
                    z_nf=h_cal.nivel_freatico_m-h_cal.profundidad_base_m
                    caso_gamma=("NF en o sobre base: γ'" if z_nf<=0 else
                                "NF a ≥B bajo base: γaparente" if z_nf>=seleccionado.b_m else
                                "F.16: interpolación por profundidad de NF")
                st.write(f"Peso específico de hundimiento γk = {gamma_k:.2f} kN/m³ · {caso_gamma}")
                st.write(f"Factores de forma: sc={seleccionado.sc:.3f}, sq={seleccionado.sq:.3f}, sγ={seleccionado.sgamma:.3f}")
            if seleccionado.avisos:
                for aviso in seleccionado.avisos:
                    st.warning(aviso)
        st.divider()
        st.subheader("Diagnóstico de asientos elásticos de la zapata seleccionada")
        st.caption("Detalle de Steinbrenner: desglose por estratos, suma acumulada y control INDEPENDIENTE de tensiones verticales por Boussinesq.")
        opcion_presion = st.radio("Presión de referencia", ["Servicio neto", "Límite neto por asientos"],
                                 horizontal=True, key="presion_diagnostico")
        q_ref = (seleccionado.q_serv_neta_mpa if opcion_presion=="Servicio neto"
                 else seleccionado.q_asiento_neta_mpa)
        if q_ref is None or q_ref <= 0:
            st.warning("No existe presion de referencia positiva; seleccione el limite por asientos.")
        else:
            try:
                filas = contribuciones_steinbrenner(seleccionado.b_m, seleccionado.l_m, s_cal, q_ref)
                tabla_capas = pd.DataFrame(filas)
                perfil = calcular_perfil_bulbo(seleccionado.b_m, seleccionado.l_m, q_ref,
                    h_cal, s_cal, paso_m=guardado["paso_bulbo"],
                    profundidad_manual_m=guardado["z_bulbo"])
                total_mm = filas[-1]["Asiento acumulado (mm)"]
                s1, s2, s3 = st.columns(3)
                s1.metric("Asiento elástico", f"{total_mm:.2f} mm")
                s2.metric("Profundidad activa (CTE)",
                          f"{perfil.profundidad_influencia_m:.2f} m" if perfil.profundidad_influencia_m is not None else "No alcanzada")
                s3.metric("Profundidad 90% del asiento (por capas)",
                    f"{profundidad_porcentaje_asiento(filas,90):.2f} m" if profundidad_porcentaje_asiento(filas,90) is not None else "N/D")
                # INC-03A/D: referencias comparables, siempre medidas bajo la base.
                c_cte,c_2b,c_perfil=st.columns(3)
                c_cte.metric("Z_CTE bajo la base",
                    f"{perfil.profundidad_influencia_m:.2f} m"
                    if perfil.profundidad_influencia_m is not None else "No determinada")
                c_2b.metric("2B · orientativo",f"{2*seleccionado.b_m:.2f} m")
                c_perfil.metric("Fin del perfil E, ν",f"{perfil.profundidad_modelo_m:.2f} m")
                if perfil.suficiente:
                    st.success("El perfil E, ν alcanza Z_CTE bajo el eje central (comprobación tensional).")
                elif perfil.profundidad_influencia_m is None:
                    st.warning("No se ha determinado Z_CTE en el intervalo de búsqueda; "
                               "no se puede demostrar la suficiencia del perfil.")
                else:
                    faltante=perfil.profundidad_influencia_m-perfil.profundidad_modelo_m
                    st.warning(f"Perfil insuficiente: faltan al menos {faltante:.2f} m "
                               "de caracterización bajo la base para alcanzar Z_CTE. "
                               "La presión admisible por asientos sigue calculada con el perfil disponible; "
                               "no debe considerarse verificada hasta ampliar o justificar el reconocimiento.")
                st.caption("Z_CTE: cruce en el eje central entre Δσz de Boussinesq "
                           "y min(10 % de q neta, 5 % de σ'v0). "
                           "2B es orientativo; ninguno de estos límites recorta el motor de Steinbrenner.")
                seccion_tab, existente_tab = st.tabs(["Sección y bulbo 2D", "Tensiones 1D y asientos"])
                with seccion_tab:
                    q_2d=float(q_ref*1000)
                    st.caption(f"Presión neta de referencia: {q_2d:.2f} kPa.")
                    # Se amplía la vista si es necesario para incluir las tres referencias.
                    z_visible=max(
                        6*seleccionado.b_m,2*seleccionado.l_m,
                        1.1*perfil.profundidad_modelo_m,
                        1.1*(perfil.profundidad_influencia_m or 0.0),
                        2.2*seleccionado.b_m,
                        guardado["z_bulbo"] or 0.0,
                    )
                    figura_2d=figura_seccion_bulbo(
                        seleccionado.b_m,seleccionado.l_m,
                        h_cal.profundidad_base_m,h_cal.nivel_freatico_m,s_cal.capas,
                        q_2d,corrida=False,zmax_m=z_visible,
                        zcte_m=perfil.profundidad_influencia_m,
                        profundidad_perfil_m=perfil.profundidad_modelo_m,
                        mostrar_2b=True)
                    st.plotly_chart(figura_2d,use_container_width=True)
                    st.caption("Isobaras: Δσz/q neta de Boussinesq (incremento de tensión vertical total). "
                               "No equivale automáticamente a Δσ' en situación no drenada. "
                               "Estratos y NF son referencias visuales; no modifican las isobaras homogéneas.")
                    st.caption("Líneas horizontales: Z_CTE (cruce tensional bajo el eje), "
                               "2B (referencia) y profundidad final del perfil. "
                               "La vista se amplía automáticamente para mostrarlas.")
                with existente_tab:
                    c_bulbo, c_acum = st.columns(2,gap="large")
                    with c_bulbo: st.plotly_chart(
                        figura_bulbo(perfil,b_m=seleccionado.b_m),use_container_width=True)
                    with c_acum: st.plotly_chart(figura_asiento_acumulado(tabla_capas),use_container_width=True)
                    st.plotly_chart(figura_contribuciones(tabla_capas),use_container_width=True)
                    st.dataframe(tabla_capas,hide_index=True,use_container_width=True,
                        column_config={"Asiento (mm)":st.column_config.NumberColumn(format="%.3f"),
                                       "Contribucion (%)":st.column_config.NumberColumn(format="%.2f")})
                    c_ex1, c_ex2 = st.columns(2)
                    with c_ex1:
                        st.download_button("Descargar contribuciones por estrato (CSV)",
                        data=tabla_capas.to_csv(index=False).encode("utf-8-sig"),
                        file_name=f"asientos_B{seleccionado.b_m:g}_L{seleccionado.l_m:g}.csv",
                        mime="text/csv",disabled=desactualizado)
                    with c_ex2:
                        tabla_tensiones = pd.DataFrame({"z bajo base (m)":perfil.z_m,
                            "Delta sigma vertical (kPa)":perfil.delta_sigma_kpa,
                            "sigma efectiva inicial (kPa)":perfil.sigma_efectiva_inicial_kpa,
                            "umbral CTE (kPa)":perfil.umbral_cte_kpa})
                        st.download_button("Descargar bulbo de tensiones (CSV)",
                            data=tabla_tensiones.to_csv(index=False).encode("utf-8-sig"),
                            file_name=f"bulbo_B{seleccionado.b_m:g}_L{seleccionado.l_m:g}.csv",
                            mime="text/csv",disabled=desactualizado)
                    for mensaje in perfil.avisos: st.info(mensaje)
                    st.caption("Las cuatro curvas permiten auditar el cruce Z_CTE; las tensiones iniciales "
                               "se estiman con los pesos específicos introducidos, no con una estratigrafía "
                               "geostática individualizada. Boussinesq: bulbo en semiespacio homogéneo. "
                               "El asiento por estratos es aproximado; "
                               "la profundidad 90% se informa solo en los limites de capa conocidos. "
                               "No se calculan consolidacion primaria/secundaria ni asiento diferencial.")
            except (ValueError,ZeroDivisionError,OverflowError) as exc:
                st.error(f"No se pudo generar el diagnostico elastico: {exc}")
        st.divider()
        st.subheader("Tabla completa y curvas B × L")
        st.dataframe(tabla,hide_index=True,use_container_width=True,height=410,
                     column_config={
                         "q servicio neta (MPa)":st.column_config.NumberColumn(format="%.4f"),
                         "q servicio bruta (MPa)":st.column_config.NumberColumn(format="%.4f"),
                         "Ksp30 (MN/m³)":st.column_config.NumberColumn(format="%.2f"),
                     })
        ancho_curva=st.selectbox("Ancho B para comparar longitudes L",
                                sorted(set(tabla["B (m)"])),key="b_curvas_bxl")
        st.plotly_chart(curvas_seccion(tabla,ancho_curva),use_container_width=True)
        st.plotly_chart(grafico_balasto(tabla,b=ancho_curva),use_container_width=True)
        st.download_button("Descargar resultados B × L (CSV)",
            data=tabla.to_csv(index=False).encode("utf-8-sig"),
            file_name="resultados_zapatas_rectangulares.csv",mime="text/csv",
            disabled=desactualizado)

        st.divider()
        st.subheader("Sensibilidad al nivel freático — zapata B × L seleccionada")
        st.caption("Análisis paramétrico exploratorio: se modifica NF manteniendo fijos los demás "
                   "parámetros resistentes; no se reestima E, ν, asientos ni la interacción con el agua.")
        nf1,nf2=st.columns(2)
        with nf1:
            nf_min=st.number_input("NF mínimo bajo rasante (m)",min_value=0.0,
                value=max(0.,h_cal.profundidad_base_m-1.),step=0.5,key="nf_sens_min")
        with nf2:
            nf_max=st.number_input("NF máximo bajo rasante (m)",min_value=0.0,
                value=max(h_cal.nivel_freatico_m,h_cal.profundidad_base_m+2*seleccionado.b_m,
                          nf_min+0.5),step=0.5,key="nf_sens_max")
        if nf_max>nf_min:
            datos_nf=sensibilidad_nivel_freatico(seleccionado.b_m,seleccionado.l_m,
                h_cal,s_cal,nf_min,nf_max)
            st.plotly_chart(grafico_sensibilidad(datos_nf),use_container_width=True)
            with st.expander("Tabla de sensibilidad NF"):
                st.dataframe(datos_nf,hide_index=True,use_container_width=True)
                st.download_button("Descargar sensibilidad NF (CSV)",
                    data=datos_nf.to_csv(index=False).encode("utf-8-sig"),
                    file_name="sensibilidad_nivel_freatico.csv",mime="text/csv",
                    disabled=desactualizado)
            if h_cal.flujo_ascendente:
                st.info("Con flujo ascendente γk depende de γ' e iᵥ y no varía con NF "
                        "en el modelo actual; la descarga de excavación sí puede variar.")
            elif abs(h_cal.gamma_aparente_kn_m3-h_cal.gamma_efectivo_kn_m3)<1e-10:
                st.info("γaparente = γ': γk resulta constante al desplazar el NF.")
        else:
            st.warning("El NF máximo debe superar al NF mínimo.")
    with co_tab:
        st.subheader("Zapatas corridas · comparativa histórica")
        st.caption(f"**Aproximación numérica, no B × ∞ estricto**: "
                   f"L_asientos={LONGITUD_CORRIDA_INTERNA_M:.0f} m; "
                   f"L_hundimiento={LONGITUD_CORRIDA_HUNDIMIENTO_M:.0f} m.")
        tc=tabla_malla(corridas)
        if not tc.empty:
            tc.insert(2,"L hundimiento (m)",LONGITUD_CORRIDA_HUNDIMIENTO_M)
            tc=tc.rename(columns={"L (m)":"L asientos (m)"})
            c_mapa,c_ficha=st.columns([1.25,1.0],gap="large")
            with c_mapa:
                metrica_corrida=st.selectbox("Variable del mapa de corridas",
                    list(CAMPOS_MAPA),key="variable_mapa_corridas")
                event_corrida=st.plotly_chart(
                    mapa_calor_corridas(tc,metrica_corrida),
                    use_container_width=True,on_select="rerun",
                    selection_mode="points",key="mapa_corridas")
            with c_ficha:
                st.subheader("Ficha de zapata corrida")
                bs_corridas=[r.b_m for r in corridas]
                idx_corrida=st.selectbox("Anchura B (m)",range(len(bs_corridas)),
                    format_func=lambda i:f"B = {bs_corridas[i]:.2f} m",
                    key="ancho_ficha_corrida")
                corrida_sel=corridas[idx_corrida]
                try:
                    if event_corrida.selection.points:
                        elegido=float(event_corrida.selection.points[0]["y"])
                        corrida_sel=next((r for r in corridas if abs(r.b_m-elegido)<1e-8),
                                         corrida_sel)
                except (AttributeError,KeyError,TypeError,IndexError,ValueError):
                    pass
                st.metric("Anchura B",f"{corrida_sel.b_m:.2f} m")
                mostrar_tabla_presiones(corrida_sel)
                st.write(f"**Gobierna:** {corrida_sel.limitacion}")
                with st.expander("Datos y factores de la corrida seleccionada"):
                    st.write(f"Longitud usada en hundimiento: {LONGITUD_CORRIDA_HUNDIMIENTO_M:.0f} m")
                    st.write(f"Longitud usada en asientos: {LONGITUD_CORRIDA_INTERNA_M:.0f} m")
                    st.write(f"γk = {_peso_especifico_representativo(h_cal,corrida_sel.b_m):.2f} kN/m³")
                    st.write(f"sc = {corrida_sel.sc:.4f}; sq = {corrida_sel.sq:.4f}; "
                             f"sγ = {corrida_sel.sgamma:.4f}")
                    st.write(f"σv0,exc = {corrida_sel.sigma_pre_base_kpa:.2f} kPa")
                    st.write(f"ks,BL = {corrida_sel.ks_bl_mn_m3:.3f} MN/m³")
                    st.write(f"Ksp30 = {corrida_sel.ksp30_mn_m3:.3f} MN/m³")
                for aviso in corrida_sel.avisos:
                    st.caption(aviso)
            st.divider()
            st.subheader("Curvas y tabla de zapatas corridas")
            tipo_presion_corrida=st.radio("Presiones a representar (corridas)",
                ["Netas","Brutas"],horizontal=True,key="presiones_corridas")
            st.plotly_chart(grafico_presiones_corridas(tc,tipo_presion_corrida),
                use_container_width=True)
            st.plotly_chart(grafico_balasto(tc,corrida=True),use_container_width=True)
            st.dataframe(tc,hide_index=True,use_container_width=True)
            st.download_button("Descargar comparativa corrida (CSV)",
                data=tc.to_csv(index=False).encode("utf-8-sig"),
                file_name="resultados_zapatas_corridas.csv",mime="text/csv",
                disabled=desactualizado)
            st.divider()
            st.subheader("Bulbo de tensiones 2D — banda infinita ideal")
            q_corrida=st.number_input("Presión neta del bulbo ideal (kPa)",
                min_value=0.1,
                value=float(1000*(corrida_sel.q_serv_neta_mpa
                      if corrida_sel.q_serv_neta_mpa is not None
                      and corrida_sel.q_serv_neta_mpa>0 else corrida_sel.q_asiento_neta_mpa)),
                step=10.0,key="q_bulbo_corrida")
            st.plotly_chart(figura_seccion_bulbo(
                corrida_sel.b_m,None,h_cal.profundidad_base_m,
                h_cal.nivel_freatico_m,s_cal.capas,q_corrida,
                corrida=True,zmax_m=guardado["z_bulbo"]),
                use_container_width=True)
            st.caption("Banda infinita matemática de Boussinesq. El bulbo no utiliza L=100 ni "
                       "L=1000 m ni se emplea directamente para obtener el asiento o la presión admisible.")
            st.divider()
            st.subheader("Auditoría exploratoria de la aproximación a corrida")
            st.caption("Los gráficos siguientes comparan longitudes FINITAS y el límite algebraico "
                       "de hundimiento al tender B/L a cero. No se declara convergencia de asientos "
                       "en un semiespacio infinito ni un nuevo valor admisible de diseño.")
            try:
                conv=convergencia_corrida(corrida_sel.b_m,h_cal,s_cal)
                variacion=convergencia_porcentaje_final(conv)
                st.metric("Variación entre las dos mayores L/B (asientos)",
                          f"{variacion:.3f} %")
                st.plotly_chart(grafico_convergencia(conv),use_container_width=True)
                st.dataframe(conv,hide_index=True,use_container_width=True)
                st.download_button("Descargar convergencia (CSV)",
                    data=conv.to_csv(index=False).encode("utf-8-sig"),
                    file_name="convergencia_corrida.csv",mime="text/csv",
                    disabled=desactualizado)
                if variacion>1.0:
                    st.warning("La variación final de la presión por asientos supera el 1 % "
                               "entre las dos mayores relaciones L/B ensayadas.")
                else:
                    st.info("La variación entre las dos longitudes finitas mayores es ≤1 %. "
                            "Esto no demuestra por sí solo validez de L infinito.")
                comp=comparativa_corridas(corrida_sel.b_m,h_cal,s_cal)
                st.subheader("Comparación de hipótesis de cálculo")
                st.plotly_chart(grafico_comparativa(comp),use_container_width=True)
                st.dataframe(comp,hide_index=True,use_container_width=True)
                st.download_button("Descargar comparación de hipótesis (CSV)",
                    data=comp.to_csv(index=False).encode("utf-8-sig"),
                    file_name="comparacion_metodos_corridas.csv",mime="text/csv",
                    disabled=desactualizado)
                st.warning("El límite B/L=0 mostrado solo proporciona hundimiento: "
                           "no existe aquí un valor validado de asiento ni de presión de servicio "
                           "para L infinito. No usar como dimensionamiento independiente.")
            except (ValueError,ZeroDivisionError,OverflowError) as exc:
                st.warning(f"No se pudo completar el estudio exploratorio de corridas: {exc}")
        else:
            st.warning("Ningún ancho B es compatible con la aproximación de longitud interna.")
    with met_tab:
        mostrar_compendio(
            h_cal, s_cal, seleccionado, resultados, tabla,
            origen_gamma=guardado.get("origen_gamma"),
            gamma_sat_kn_m3=guardado.get("gamma_sat_kn_m3"),
            desactualizado=desactualizado,
        )
    st.caption(f"Trabajo: {proyecto_cal.trabajo or 'Sin especificar'} · Expediente: {proyecto_cal.expediente or 'Sin especificar'}")
