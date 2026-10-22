"""Cimentaciones superficiales: malla BxL, hundimiento y asiento elástico.

Prototipo técnico; no sustituye la verificación del proyecto conforme al CTE.
"""
from __future__ import annotations

from math import isfinite
import hashlib
import json

import pandas as pd
import streamlit as st

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
from visualizacion.graficos_malla import curvas_seccion, grafico_geom, mapa_calor

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
        gamma_ef=st.number_input("Peso específico sumergido γ' (kN/m³)",min_value=0.1,value=18.0,step=0.5)
        gamma_ap=st.number_input("Peso específico aparente (kN/m³)",min_value=0.1,value=18.0,step=0.5)
        flujo=st.toggle("Flujo ascendente",value=False)
        gradiente=st.number_input("Gradiente vertical",value=0.4,step=0.05,disabled=not flujo)
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
    with der:
        st.subheader("Perfil de deformabilidad")
        capas_df=st.data_editor(
            pd.DataFrame({"Unidad":["NIVEL 1","NIVEL 2"],"z sup. (m)":[0.0,2.5],
                "z inf. (m)":[2.5,10.0],"E (MPa)":[15.0,1200.0],"nu":[0.30,0.20]}),
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
        cu_z1, cu_1, nf, gamma_ef, gamma_ap, flujo, gradiente,
        considerar_sobrecarga, gamma_sob, altura_sob, beta],
    "asientos": [asiento_adm, tipo_balasto, metodo_id],
    "capas": capas_df.to_dict(orient="records"),
}
firma_actual = hashlib.sha256(json.dumps(entrada_actual,sort_keys=True,default=str,
    ensure_ascii=False).encode("utf-8")).hexdigest()

with tab_res:
    if st.button("Calcular", type="primary", use_container_width=True, key="calcular_malla"):
        try:
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
                capas=capas,metodo_centro=metodo_id,tipo_material_balasto=tipo_balasto)
            resultados = calcular_malla(geometrias,h,s)
            tabla = tabla_malla(resultados)
            corridas = calcular_corridas(tuple(sorted(set(tabla["B (m)"]))),h,s)
            st.session_state["ultimo_calculo"] = {
                "firma": firma_actual, "resultados": resultados, "tabla": tabla,
                "corridas": corridas, "h": h, "s": s,
                "proyecto": DatosProyecto(peticionario,trabajo,expediente),
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
    an_tab,co_tab,met_tab=st.tabs(["Mapa B × L y ficha","Tabla general y curvas","Método y advertencias"])
    with an_tab:
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
            fa,fb=st.columns(2)
            fa.metric("Hundimiento neto",f"{seleccionado.q_hund_neta_mpa:.3f} MPa")
            fb.metric("Asientos neto",f"{seleccionado.q_asiento_neta_mpa:.3f} MPa")
            st.metric("Presión de servicio neta",formatear(seleccionado.q_serv_neta_mpa)+" MPa")
            st.write(f"**Gobierna:** {seleccionado.limitacion}")
            with st.expander("Detalle de presiones, balasto y factores"):
                st.write(f"q0 = {seleccionado.q0_kpa/1000:.3f} MPa")
                st.write(f"Hundimiento bruto = {seleccionado.q_hund_bruta_mpa:.3f} MPa")
                st.write(f"Servicio bruto = {formatear(seleccionado.q_serv_bruta_mpa)} MPa")
                st.write(f"k_s,BL = {seleccionado.ks_bl_mn_m3:.2f} MN/m³")
                st.write(f"Ksp30 ({s_cal.tipo_material_balasto.lower()}) = {seleccionado.ksp30_mn_m3:.2f} MN/m³")
                st.write(f"Factores de forma: sc={seleccionado.sc:.3f}, sq={seleccionado.sq:.3f}, sγ={seleccionado.sgamma:.3f}")
            if seleccionado.avisos:
                for aviso in seleccionado.avisos:
                    st.warning(aviso)
    with co_tab:
        st.subheader("Tabla completa B × L")
        st.dataframe(tabla,hide_index=True,use_container_width=True,height=410,
                     column_config={
                         "q servicio neta (MPa)":st.column_config.NumberColumn(format="%.4f"),
                         "q servicio bruta (MPa)":st.column_config.NumberColumn(format="%.4f"),
                         "Ksp30 (MN/m³)":st.column_config.NumberColumn(format="%.2f"),
                     })
        ancho_curva=st.selectbox("Ancho B para comparación de longitudes L",sorted(set(tabla["B (m)"])))
        st.plotly_chart(curvas_seccion(tabla,ancho_curva),use_container_width=True)
        st.download_button("Descargar resultados B × L (CSV)",data=tabla.to_csv(index=False).encode("utf-8-sig"),
            file_name="resultados_zapatas_rectangulares.csv",mime="text/csv",
            disabled=desactualizado,help="Recalcule para descargar datos correspondientes a las entradas actuales." if desactualizado else None)
        st.divider()
        st.subheader("Comparativa de zapatas corridas")
        st.caption(f"Aproximación histórica con longitudes INTERNAS no editables: L(asientos)={LONGITUD_CORRIDA_INTERNA_M:.0f} m; L(hundimiento)={LONGITUD_CORRIDA_HUNDIMIENTO_M:.0f} m. No corresponde a una única zapata B×L física.")
        try:
            tc=tabla_malla(corridas)
            if len(tc):
                tc.insert(2,"L hundimiento (m)",LONGITUD_CORRIDA_HUNDIMIENTO_M)
                tc=tc.rename(columns={"L (m)":"L asientos (m)"})
                st.dataframe(tc,hide_index=True,use_container_width=True)
                st.download_button("Descargar comparativa corrida (CSV)",data=tc.to_csv(index=False).encode("utf-8-sig"),
                    file_name="resultados_zapatas_corridas.csv",mime="text/csv",disabled=desactualizado)
            else:
                st.warning("B es mayor que la longitud equivalente interna; no se calcula la comparación corrida.")
        except (ValueError,OverflowError) as exc:
            st.warning(f"No ha podido completarse la comparación corrida: {exc}")
    with met_tab:
        st.subheader("Criterio de comparación")
        st.latex(r"q_{h,d}^{bruta}=\frac{q_h}{\gamma_R}; \quad q_{h,d}^{neta}=q_{h,d}^{bruta}-q_0")
        st.latex(r"q_{asientos}^{neta}=\frac{s_{adm}}{s(q_{neta}=1)}; \quad q_{serv}^{neta}=\min(q_{h,d}^{neta},q_{asientos}^{neta})")
        st.latex(r"q_{serv}^{bruta}=q_{serv}^{neta}+q_0")
        st.caption("No se mezcla presión neta de asientos con bruta de hundimiento. k_s,BL se calcula con la flexibilidad elástica lineal.")
        st.subheader("Advertencias generales del modelo")
        for w in avisos_globales(h_cal,s_cal,True):
            st.warning(w)
        st.subheader("Advertencias de geometrías")
        n_alertas=sum(bool(r.avisos) for r in resultados)
        st.write(f"{n_alertas} combinaciones presentan al menos un aviso específico.")
        if n_alertas:
            st.dataframe(tabla.loc[tabla["Avisos"].str.len()>0,["B (m)","L (m)","Avisos"]],
                hide_index=True,use_container_width=True)
        st.markdown("**Referencias:** CTE DB-SE-C, §4.3.2.1 y Anejo F (hundimiento); Anejo E.5 (balasto). "
                    "[Documento oficial](https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf).")
    st.caption(f"Trabajo: {proyecto_cal.trabajo or 'Sin especificar'} · Expediente: {proyecto_cal.expediente or 'Sin especificar'}")
