"""PilotesCTE v3.0 · interfaz Streamlit (el motor reside en src/pilotes_cte/core.py)."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict
from pathlib import Path
import sys

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE / "src"))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pilotes_cte.core import (
    CLASES_RN, Configuracion, ErrorDatos, Estrato, Geometria,
    comprobar_estratos, comprobar_nf, crear_seccion, matriz_calculo,
    perfil_tensiones, seleccionar_gamma, tensiones,
)
from pilotes_cte.report import generar_informe

VERSION="3.0.0"


def df_ejemplo()->pd.DataFrame:
    """Estratigrafía ficticia solo para explorar la interfaz; no es un sondeo real."""
    return pd.DataFrame({
        "Estrato":["UG-01","UG-02","UG-03","UG-04"],
        "Espesor (m)":[2.,5.,8.,10.],
        "Gamma Seco (kN/m3)":[18.,19.,18.5,20.],
        "Gamma Sat. (kN/m3)":[20.,20.,20.5,21.],
        "Tipo suelo":["Fino","Fino","Granular","Granular"],
        "Condición":["Corto Plazo","Corto Plazo","Largo Plazo","Largo Plazo"],
        "cu (kPa)":[30.,150.,0.,0.],
        "phi (grados)":[0.,0.,30.,35.],
        "Clase RN":["No definida"]*4,
    })


def desde_tabla(df:pd.DataFrame)->list[Estrato]:
    r=[]
    for i,fila in df.iterrows():
        try:
            if any(pd.isna(fila[k]) for k in ("Estrato","Espesor (m)","Gamma Seco (kN/m3)",
                  "Gamma Sat. (kN/m3)","Tipo suelo","Condición","cu (kPa)","phi (grados)","Clase RN")):
                raise ErrorDatos(f"Fila {i+1}: no se admiten celdas vacías o NaN.")
            r.append(Estrato(
                nombre=str(fila["Estrato"]).strip(),
                espesor=float(fila["Espesor (m)"]),
                gamma_seco=float(fila["Gamma Seco (kN/m3)"]),
                gamma_sat=float(fila["Gamma Sat. (kN/m3)"]),
                tipo=str(fila["Tipo suelo"]),
                condicion=str(fila["Condición"]),
                cu=float(fila["cu (kPa)"]),
                phi=float(fila["phi (grados)"]),
                clase_rn=str(fila["Clase RN"]),
            ))
        except (KeyError,TypeError,ValueError) as exc:
            raise ErrorDatos(f"Datos incompletos o no numéricos en estratigrafía: {exc}") from exc
    return r


def _rango(a:float,b:float,step:float)->list[float]:
    if not all(math.isfinite(v) for v in (a,b,step)) or step<=0 or b<a:
        raise ErrorDatos("Matriz: máximo ≥ mínimo, con paso positivo y valores finitos.")
    count=math.floor((b-a)/step+1e-9)+1
    if count>40:
        raise ErrorDatos("La matriz no debe superar 40 valores en cada dirección.")
    return [round(a+i*step,6) for i in range(count)]


def _firma(valores:dict)->str:
    return hashlib.sha256(json.dumps(valores,sort_keys=True,default=str).encode("utf-8")).hexdigest()


def _tabla_pivot(resultados,diametros,longitudes,campo):
    lookup={(round(r.longitud,6),round(r.diametro,6)):r for r in resultados}
    data=[]
    for l in longitudes:
        fila=[]
        for d in diametros:
            r=lookup.get((round(l,6),round(d,6)))
            fila.append(float(getattr(r,campo)) if r is not None else float("nan"))
        data.append(fila)
    return pd.DataFrame(data,index=[f"L={x:.2f} m" for x in longitudes],
                        columns=[f"D eq={x:.3f} m" for x in diametros])


def _estres_plot(estratos,cfg):
    zs,sv,u,se=perfil_tensiones(estratos,cfg.nivel_freatico)
    fig=go.Figure()
    for x,n,color in ((sv,"Tensión vertical total σv","black"),
                      (u,"Presión intersticial u","#3975ad"),
                      (se,"Tensión efectiva σ'v","#be4545")):
        fig.add_trace(go.Scatter(x=x,y=zs,name=n,line=dict(color=color,width=2)))
    top=0.
    colors=["#eaf4fb","#f4f0fa","#f5eee5","#e8f3ee"]
    for i,e in enumerate(estratos):
        fig.add_hrect(y0=top,y1=top+e.espesor,fillcolor=colors[i%4],opacity=.35,
                      annotation_text=e.nombre,annotation_position="top left",line_width=0)
        top+=e.espesor
    if cfg.nivel_freatico is not None:
        fig.add_hline(y=cfg.nivel_freatico,line_color="#3975ad",line_dash="dot",annotation_text="N.F.")
    fig.add_hline(y=top,line_color="gray",line_dash="dash",annotation_text="Fin del sondeo")
    fig.update_yaxes(autorange="reversed",title="Profundidad (m)")
    fig.update_xaxes(title="Presión (kPa)",side="top")
    fig.update_layout(height=520,margin=dict(t=35,b=25,l=15,r=15),legend=dict(orientation="h",y=-.14))
    return fig


def _bulbo_plot(estratos,cfg,r):
    D=r.diametro;L=r.longitud
    fig=go.Figure()
    top=0
    colores=["#eaf4fb","#f4f0fa","#f5eee5","#e8f3ee"]
    for i,e in enumerate(estratos):
        fig.add_hrect(y0=top,y1=top+e.espesor,fillcolor=colores[i%4],opacity=.7,
                      annotation_text=e.nombre,annotation_position="top left")
        top+=e.espesor
    fig.add_shape(type="rect",x0=-D/2,x1=D/2,y0=0,y1=L,
                  fillcolor="#b6bcc3",line=dict(color="black",width=2))
    fig.add_shape(type="rect",x0=-1.4*D,x1=1.4*D,y0=max(0,L-6*D),y1=L+3*D,
                  line=dict(color="#ba3434",dash="dash",width=2),fillcolor="rgba(202,66,66,0.13)")
    fig.add_hline(y=L,line_color="black",annotation_text="Punta")
    fig.add_hline(y=top,line_dash="dash",annotation_text="Fin del sondeo")
    if cfg.nivel_freatico is not None:
        fig.add_hline(y=cfg.nivel_freatico,line_color="blue",line_dash="dot",annotation_text="N.F.")
    if cfg.rozamiento_negativo:
        a=cfg.rn_desde;b=min(cfg.rn_hasta,L)
        if a<b:
            fig.add_shape(type="rect",x0=-D/1.8,x1=D/1.8,y0=a,y1=b,
                          fillcolor="rgba(249,163,44,.25)",line=dict(color="orange",width=2))
    fig.update_yaxes(range=[top+1,-max(.5,D)],title="Profundidad (m)")
    fig.update_xaxes(range=[-3.0*D,3.0*D],showticklabels=False,title="Sección equivalente (solo esquema)")
    fig.update_layout(height=540,showlegend=False,margin=dict(l=15,r=15,t=20,b=20))
    return fig


def main():
    st.set_page_config(page_title="PilotesCTE · v3",page_icon="🏗️",layout="wide")
    st.title("🏗️ PilotesCTE · versión 3.0")
    st.caption("CTE DB-SE-C · Resistencia axial analítica · Prototipo sujeto a revisión geotécnica")
    st.warning("No calcula todos los estados límite ni determina automáticamente los dos escenarios de corto/largo plazo de los suelos finos. "
               "El tope axial estructural es simplificado. No apto como única justificación de un proyecto.")

    if "tabla_inicial" not in st.session_state:
        st.session_state.tabla_inicial=df_ejemplo()
    if "firma_calculo" not in st.session_state:
        st.session_state.firma_calculo=None
    if "word_buffer_v3" not in st.session_state:
        st.session_state.word_buffer_v3=None

    st.sidebar.header("1 · Pilote y ejecución")
    ejecucion=st.sidebar.selectbox("Ejecución",["Perforados","Hincados"])
    if ejecucion=="Perforados":
        procedimiento=st.sidebar.selectbox("Procedimiento",["Entubados","Lodos","En seco",
                             "Barrenados con control de parámetros","Barrenados sin control de parámetros"])
        material="Hormigón armado"
        tope_base={"Entubados":5.,"Lodos":4.,"En seco":4.,
                   "Barrenados con control de parámetros":4.,
                   "Barrenados sin control de parámetros":3.5}[procedimiento]
        control_integridad=st.sidebar.checkbox("Control de integridad (+25 % tope)",value=False)
        sigma_tope=tope_base*(1.25 if control_integridad else 1)
        tipo_geom="Circular macizo"
        st.sidebar.caption("Apoyo en roca no implementado; únicamente suelo.")
    else:
        material=st.sidebar.selectbox("Material",["Hormigón armado","Hormigón pretensado", "Metálicos","Madera"])
        if material=="Hormigón armado":
            fck=st.sidebar.number_input("fck (MPa)",min_value=1.,value=30.,step=5.)
            sigma_tope=.30*fck
        elif material=="Hormigón pretensado":
            fck=st.sidebar.number_input("fck (MPa)",min_value=1.,value=40.,step=5.)
            fp_tension=st.sidebar.number_input("fp (MPa)",value=10.,min_value=0.,step=1.)
            sigma_tope=.30*(fck-.9*fp_tension)
        elif material=="Metálicos":
            fyk=st.sidebar.number_input("fyk (MPa)",min_value=1.,value=275.,step=5.)
            sigma_tope=.30*fyk
        else:
            sigma_tope=5.0
        tipo_geom=st.sidebar.selectbox("Geometría",["Circular macizo","Tubular acero","Perfil H acero"]
                                       if material=="Metálicos" else ["Circular macizo"])

    st.sidebar.metric("Tope axial simplificado",f"{sigma_tope:.2f} MPa")
    st.sidebar.header("2 · Nivel freático y fuste")
    existe_nf=st.sidebar.checkbox("Existe nivel freático en sondeo",value=True)
    zw=st.sidebar.number_input("Profundidad N.F. (m)",min_value=0.,value=3.,step=.5) if existe_nf else None
    if not existe_nf:
        st.sidebar.caption("Sin nivel freático: γ seco y u=0 hasta fondo del reconocimiento.")
    z_nulo=st.sidebar.number_input("Fuste nulo (m)",min_value=0.,value=1.5,step=.5)
    rn_act=st.sidebar.checkbox("Activar rozamiento negativo (CTE 5.2.2)",value=False)
    rn_desde=rn_hasta=0.; factor_rn=1.
    if rn_act:
        st.sidebar.info("Debe justificarse el intervalo por asientos relativos. Indique la clase β de cada unidad afectada en la tabla.")
        rn_desde=st.sidebar.number_input("RN desde z (m)",min_value=0.,value=0.,step=.5)
        rn_hasta=st.sidebar.number_input("RN hasta z (m)",min_value=0.,value=5.,step=.5)
        factor_rn=st.sidebar.number_input("Factor de acción Fneg,d / Fneg,k",min_value=.1,value=1.,step=.1,
                                          help="Valor supuesto; justificarlo mediante combinación de acciones del proyecto.")
        st.sidebar.warning("La capacidad neta de cabeza es indicativa; no equivale a una verificación ELU.")

    st.sidebar.header("3 · Geometría matricial")
    esp_tubo=.02;b=h=tf=tw=0.
    if tipo_geom=="Perfil H acero":
        st.sidebar.caption("Perfil H de dimensiones fijas; se evalúa una sola columna de D equivalente.")
        b=st.sidebar.number_input("Ancho del ala b (m)",value=.30,min_value=.001,step=.01)
        h=st.sidebar.number_input("Canto h (m)",value=.32,min_value=.001,step=.01)
        tf=st.sidebar.number_input("Espesor ala tf (m)",value=.018,min_value=.001,step=.001,format="%.3f")
        tw=st.sidebar.number_input("Espesor alma tw (m)",value=.012,min_value=.001,step=.001,format="%.3f")
        d_values=[]
        geos=[Geometria(tipo=tipo_geom,ancho_ala=b,canto=h,espesor_ala=tf,espesor_alma=tw)]
        try:d_values=[crear_seccion(geos[0]).d_equivalente]
        except ErrorDatos:pass
    else:
        c1,c2=st.sidebar.columns(2)
        dmin=c1.number_input("D mínimo (m)",min_value=.10,value=.40,step=.1)
        dmax=c2.number_input("D máximo (m)",min_value=.10,value=1.00,step=.1)
        dpaso=st.sidebar.number_input("Paso D (m)",min_value=.01,value=.20,step=.05)
        if tipo_geom=="Tubular acero":
            esp_tubo=st.sidebar.number_input("Espesor pared tubular (m)",value=.02,min_value=.001,step=.005,format="%.3f")
        geos=[];d_values=[]
    c3,c4=st.sidebar.columns(2)
    lmin=c3.number_input("L mínimo (m)",min_value=.5,value=10.,step=1.)
    lmax=c4.number_input("L máximo (m)",min_value=.5,value=20.,step=1.)
    lpaso=st.sidebar.number_input("Paso L (m)",min_value=.1,value=2.5,step=.5)

    st.sidebar.header("4 · Coeficiente parcial γR")
    situacion=st.sidebar.selectbox("Situación de dimensionado",["Persistente/transitoria","Extraordinaria"])
    modo_gamma=st.sidebar.radio("γR",["Normativo automático","Manual justificado"],horizontal=False)
    gamma_manual=None;justificacion=""
    if modo_gamma=="Manual justificado":
        gamma_manual=st.sidebar.number_input("γR manual",min_value=1.,value=3.,step=.1)
        justificacion=st.sidebar.text_area("Justificación obligatoria",placeholder="Razón técnica y referencia")

    st.sidebar.header("5 · Identificación para memoria")
    proyecto=st.sidebar.text_input("Proyecto",value="Estudio preliminar")
    sondeo=st.sidebar.text_input("Sondeo / perfil",value="Perfil de ejemplo")

    tabs=st.tabs(["📋 Estratigrafía","🌊 Tensiones","🔻 Punta","🟫 Fuste",
                  "🌍 Resistencia total","🛑 Capacidad de cabeza","🔍 Auditoría","📖 Formulación e informe"])
    with tabs[0]:
        st.subheader("Unidades geotécnicas")
        st.info("Los datos iniciales son **ficticios**, no representan un reconocimiento real. "
                "'Tipo suelo' controla los límites de fuste y la regla 5.11; 'Condición' mantiene el escenario escogido por unidad (NO se calculan ambos automáticamente).")
        df=st.data_editor(st.session_state.tabla_inicial,num_rows="dynamic",use_container_width=True,
                          key="editor_v3",
                          column_config={
                              "Tipo suelo":st.column_config.SelectboxColumn("Tipo suelo",options=["Fino","Granular"],required=True),
                              "Condición":st.column_config.SelectboxColumn("Condición",options=["Corto Plazo","Largo Plazo"],required=True),
                              "Clase RN":st.column_config.SelectboxColumn("Clase RN",options=["No definida",*CLASES_RN],required=True),
                          })
        st.caption("β (solo si activa RN): arcilla/limo blando=0,25; arena floja=0,10; arena densa=0,80 (CTE 5.2.2). "
                   "No se asigna β por defecto sin identificar el material.")

    errores=[];estratos=[];cfg=None;motivo_gamma="";l_values=[]
    try:
        estratos=desde_tabla(df.reset_index(drop=True))
        ztotal=comprobar_estratos(estratos)
        comprobar_nf(zw,ztotal)
        if sigma_tope<=0:raise ErrorDatos("El tope axial calculado no es positivo; revise fck y fp.")
        gamma,motivo_gamma=seleccionar_gamma(estratos,situacion,gamma_manual,justificacion)
        if tipo_geom!="Perfil H acero":
            d_values=_rango(dmin,dmax,dpaso)
            geos=[Geometria(tipo=tipo_geom,diametro=d,espesor_pared=esp_tubo) for d in d_values]
            d_values=[crear_seccion(g).d_equivalente for g in geos]
        elif not d_values:
            raise ErrorDatos("Dimensiones del perfil H no válidas.")
        l_values=_rango(lmin,lmax,lpaso)
        if len(geos)*len(l_values)>800:
            raise ErrorDatos("Matriz demasiado grande; máximo 800 combinaciones.")
        for g in geos:crear_seccion(g)
        cfg=Configuracion(ejecucion=ejecucion,material=material,gamma_r=gamma,
                          sigma_tope_mpa=sigma_tope,nivel_freatico=zw,fuste_nulo=z_nulo,
                          rozamiento_negativo=rn_act,rn_desde=rn_desde,rn_hasta=rn_hasta,factor_rn=factor_rn)
        # Validación global de rangos. Unas combinaciones podrán ser N/D por RN o bulbo.
        if rn_act and not (0<=rn_desde<rn_hasta<=ztotal):
            raise ErrorDatos(f"Zona RN fuera del sondeo (0–{ztotal:.2f} m).")
        if z_nulo>ztotal:
            raise ErrorDatos("El fuste nulo supera la estratigrafía definida.")
    except ErrorDatos as exc:
        errores.append(str(exc))
    if errores:
        with tabs[0]:
            for err in errores:st.error(f"⛔ {err}")
        st.sidebar.error("Corrija los datos de entrada para calcular.")
    else:
        with tabs[0]:
            st.success(f"Reconocimiento definido hasta {ztotal:.2f} m · γR={cfg.gamma_r:.2f} · {motivo_gamma}")
            if lmax+3*max(d_values)>ztotal+1e-9:
                st.warning(f"Algunas geometrías exceden el terreno reconocido: para el máximo se requieren "
                           f"{lmax+3*max(d_values):.2f} m (=L+3D), frente a {ztotal:.2f} m. Se marcarán N/D.")
            if any(e.tipo=="Fino" for e in estratos):
                st.caption("En suelo fino los dos escenarios, corto y largo plazo, deben contrastarse posteriormente.")

    # La firma incluye datos, parámetros y contexto de informe; no persistir informes obsoletos.
    firma=None
    if not errores:
        firma=_firma({"estratos":[asdict(e) for e in estratos],
                      "config":asdict(cfg),"geometrias":[asdict(g) for g in geos],
                      "longitudes":l_values,"situacion":situacion,"motivo_gamma":motivo_gamma,
                      "proyecto":proyecto,"sondeo":sondeo})
    if firma!=st.session_state.firma_calculo:
        st.session_state.word_buffer_v3=None
    run=st.sidebar.button("⚙️ Calcular matriz",type="primary",use_container_width=True,disabled=bool(errores))
    if run and not errores:
        rs,errs=matriz_calculo(estratos,cfg,geos,l_values)
        st.session_state.datos_resultados_v3=(rs,errs)
        st.session_state.firma_calculo=firma
        st.session_state.word_buffer_v3=None

    if errores or firma!=st.session_state.firma_calculo or not st.session_state.get("datos_resultados_v3"):
        with tabs[1]:st.info("Introduzca datos válidos y pulse **Calcular matriz**.")
        with tabs[7]:st.info("La memoria se habilita tras calcular con los datos actuales.")
        return

    resultados,errs=st.session_state.datos_resultados_v3
    if not resultados:
        with tabs[0]:st.error("Ninguna combinación calculable. Revise la profundidad del sondeo, bulbos y rango de RN.")
        if errs:
            with tabs[6]:st.dataframe(pd.DataFrame(errs),use_container_width=True)
        return
    st.sidebar.success(f"{len(resultados)} combinaciones calculadas; {len(errs)} N/D")

    with tabs[1]:
        st.plotly_chart(_estres_plot(estratos,cfg),use_container_width=True)
        zconsulta=st.number_input("Consulta puntual z (m)",min_value=0.,max_value=float(ztotal),
                                  value=float(min(ztotal,zw if zw is not None else 0.)),step=.1)
        v=tensiones(zconsulta,estratos,zw)
        cols=st.columns(3)
        for c,n,x in zip(cols,["σv total","u intersticial","σ'v efectiva"],v):
            c.metric(n,f"{x:.2f} kPa")

    for tab,title,campo,color in ((tabs[2],"Resistencia característica por punta, Rpk","r_pk","Reds"),
                                   (tabs[3],"Resistencia característica por fuste positivo, Rfk","r_fk","Oranges"),
                                   (tabs[4],"Resistencia geotécnica de cálculo, Rcd = Rck/γR","r_cd","Greens"),
                                   (tabs[5],"Capacidad de cabeza ORIENTATIVA, tras RN si procede","r_cabeza_orientativa","Blues")):
        with tab:
            st.subheader(title+" (kN)")
            pivot=_tabla_pivot(resultados,d_values,l_values,campo)
            st.dataframe(pivot.style.background_gradient(cmap=color,axis=None).format("{:.0f}",na_rep="N/D"),
                         use_container_width=True)
            if campo=="r_cabeza_orientativa":
                st.warning("No constituye verificación ELU Ed≤Rd; el tope estructural es una simplificación. "
                           "El rozamiento negativo debe considerarse como acción y justificarse con los asientos relativos.")
                data=pd.DataFrame([{"D eq":f"{r.diametro:.3f} m","L (m)":r.longitud,
                                    "R cabeza orientativa (kN)":r.r_cabeza_orientativa} for r in resultados])
                st.plotly_chart(px.line(data,x="L (m)",y="R cabeza orientativa (kN)",color="D eq",markers=True),
                                use_container_width=True)
                if rn_act:
                    neg=_tabla_pivot(resultados,d_values,l_values,"rn_d")
                    st.subheader("Acción por rozamiento negativo Fneg,d (kN)")
                    st.dataframe(neg.style.format("{:.0f}",na_rep="N/D"),use_container_width=True)
            st.download_button(f"Descargar matriz CSV · {campo}",pivot.to_csv(sep=";",decimal=",").encode("utf-8-sig"),
                               file_name=f"PilotesCTE_v3_{campo}.csv",mime="text/csv",key=f"desc_{campo}")

    with tabs[6]:
        st.subheader("Auditoría de una combinación")
        valores=sorted(resultados,key=lambda r:(r.diametro,r.longitud))
        ids=[f"L={r.longitud:.2f} m · D eq={r.diametro:.3f} m" for r in valores]
        sel=st.selectbox("Combinación",options=range(len(ids)),format_func=lambda i:ids[i])
        r=valores[sel]
        st.session_state.resultado_aud_v3=r
        kpis=st.columns(4)
        for col,texto,n in zip(kpis,["Rpk","Rfk","Rcd","Fneg,d"],[r.r_pk,r.r_fk,r.r_cd,r.rn_d]):
            col.metric(texto,f"{n:.1f} kN")
        st.write(f"**Sección:** {r.seccion.descripcion} · Ap={r.seccion.area_punta:.4f} m² · "
                 f"A estructural={r.seccion.area_estructural:.4f} m² · perímetro={r.seccion.perimetro_fuste:.4f} m")
        st.write(f"**Punta qp:** {r.q_p:.1f} kPa (antes de 5.11: {r.q_p_sin_limite:.1f} kPa; "
                 f"límite 5.11: {r.q_limite_511:.1f} kPa)" if r.q_limite_511 is not None
                 else f"**Punta qp:** {r.q_p:.1f} kPa (sin límite 5.11 aplicable en el perfil)")
        st.write(f"**Carga de cabeza orientativa:** {r.r_cabeza_orientativa:,.1f} kN · "
                 f"**Tope axial simplificado:** {r.r_estructural:,.1f} kN · Gobierno: {r.control}")
        for mensaje in r.observaciones:st.warning(mensaje)
        st.plotly_chart(_bulbo_plot(estratos,cfg,r),use_container_width=True)
        for title,rows in (("Parámetros de punta",r.detalles_punta),
                           ("Fuste positivo",r.detalles_fuste),
                           ("Rozamiento negativo",r.detalles_rn)):
            st.markdown(f"**{title}**")
            if rows:st.dataframe(pd.DataFrame(rows),use_container_width=True)
            else:st.caption("Sin tramos.")
        if errs:
            st.subheader("Combinaciones N/D y causas")
            st.dataframe(pd.DataFrame(errs),use_container_width=True)

    with tabs[7]:
        st.subheader("Formulación y fuentes")
        st.markdown("""**CTE DB-SE-C (PDF oficial de 20-12-2019)**:

- **Punta granular:** F.30, $q_p=f_p\\sigma'_{vp}N_q\\leq 20000\\,\\mathrm{kPa}$.
- **Punta fina sin drenaje:** F.32, $q_p=9c_u$, con $c_u$ en entorno 2D/2D.
- **Estratigrafía heterogénea:** 5.3.4.1.2, entorno 6D/3D, homogeneización de parámetros.
- **Arcilla blanda inferior:** 5.11, $q_p\\leq 6(1+H/D)^2c_u$.
- **Fuste drenado:** F.31, $\\tau_f=\\sigma'_vK_ff\\tan\\phi$, tope 120 kPa granular / 100 kPa fino.
- **Fuste fino sin drenaje:** F.33, $\\tau_f=100c_u/(100+c_u)$.
- **Rozamiento negativo:** 5.2.2, $\\tau_{neg}=\\beta\\sigma'_v$, integrado en la zona indicada.
- **Coeficiente parcial:** tabla 2.1, 3,0 largo plazo; 2,0 corto plazo analítico permitido; 2,0 extraordinaria.

[Consultar CTE DB-SE-C oficial](https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf).
""")
        st.caption("Los perfiles mixtos (suelo fino no drenado con granular/drenado en entorno de punta) utilizan una cota conservadora explícita. "
                   "No es un método de homogeneización mixto prescrito literalmente por el CTE.")
        st.markdown("**Memoria Word**: hipótesis, estratigrafía, tensiones, formulación, matrices, "
                    "auditoría por tramo, RN y limitaciones.")
        if st.button("📄 Generar memoria Word",type="primary"):
            with st.spinner("Preparando memoria..."):
                try:
                    seleccion=st.session_state.get("resultado_aud_v3",resultados[0])
                    geo_desc=seleccion.seccion.descripcion
                    doc=generar_informe(estratos,cfg,situacion,motivo_gamma,geo_desc,resultados,
                                        seleccion,errs,{"proyecto":proyecto,"sondeo":sondeo})
                    st.session_state.word_buffer_v3=doc
                except Exception as exc:
                    st.error(f"No se pudo generar la memoria: {exc}")
        if st.session_state.word_buffer_v3 is not None:
            st.download_button("⬇️ Descargar memoria (.docx)",data=st.session_state.word_buffer_v3,
                               file_name="PilotesCTE_v3_Memoria.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        st.markdown("**Límites:** Sin apoyo en roca; sin comprobación completa Ed≤Rd; sin escenarios automáticos, "
                    "sin asientos, grupos, arrancamiento ni acciones horizontales. "
                    "RN requiere verificar deformaciones relativas y plano neutro.")


if __name__=="__main__":
    main()
