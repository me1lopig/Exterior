"""ZapatasCTE 4.2 completa autonoma (reconstruida). Interfaz Streamlit.

Herramienta de predimensionamiento NO equivalente a verificaciones ELU/ELS integrales.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import asdict
import math
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from src.engine import (VERSION, Parametros, Estrato, MAPA, dimensiones,
                        ejecutar_malla, tabla_resultados, contribuciones_asiento,
                        bulbo_tensiones, calcular_corrida_historica)
from src.balasto_cte import comparar_criterios

st.set_page_config(page_title='ZapatasCTE · v4.2', page_icon='▦',layout='wide')
st.markdown('''<style>.block-container{max-width:1520px;padding-top:1.4rem}
h1,h2,h3{color:#203a55!important}.stButton>button[kind="primary"]{background:#b84e57}
</style>''',unsafe_allow_html=True)


def checksum(obj):
    texto=json.dumps(obj,sort_keys=True,ensure_ascii=False,default=str)
    return hashlib.sha256(texto.encode('utf-8')).hexdigest()


def valor(v,dec=3):
    if v is None or (isinstance(v,(int,float)) and not math.isfinite(v)):
        return 'No válido'
    return f'{v:.{dec}f}'


def figura_mapa(rows,etiqueta):
    campo=MAPA[etiqueta]
    bs=sorted({r['B_m'] for r in rows});ls=sorted({r['L_m'] for r in rows})
    dd={(r['B_m'],r['L_m']):r for r in rows}
    cats={'Hundimiento':0.,'No valido':0.5,'Asientos':1.}
    z=[];textos=[];anotaciones=[]
    for b in bs:
        fila=[];hov=[]
        for l in ls:
            r=dd.get((b,l))
            if r is None:
                fila.append(None);hov.append('Fuera de la malla B ≤ L');continue
            vv=r[campo]
            fila.append(cats.get(vv,.5) if campo=='limitacion' else vv)
            lines=[f'B={b:.2f} m · L={l:.2f} m']
            for item,field in [('Hundimiento neto','q_hund_neta_mpa'),('Hundimiento bruto','q_hund_bruta_mpa'),
                  ('Asientos neto','q_asiento_neta_mpa'),('Asientos bruto','q_asiento_bruta_mpa'),
                  ('Servicio neto','q_serv_neta_mpa'),('Servicio bruto','q_serv_bruta_mpa')]:
                lines.append(f'{item}: {valor(r[field])} MPa')
            lines.append(f"ks,BL: {valor(r['ks_bl_mn_m3'],2)} MN/m³")
            lines.append(f"Ksp30: {valor(r['ksp30_mn_m3'],2)} MN/m³")
            lines.append(f"Gobierna: {r['limitacion']}")
            hov.append('<br>'.join(lines))
            if len(bs)*len(ls)<=150:
                t = {'Hundimiento':'H','Asientos':'A','No valido':'!'}.get(vv,'?') if campo=='limitacion' else valor(vv,2)
                anotaciones.append(dict(x=l,y=b,text=t,showarrow=False,font=dict(size=9,color='#142d48')))
        z.append(fila);textos.append(hov)
    categorico=campo=='limitacion'
    fig=go.Figure(go.Heatmap(x=ls,y=bs,z=z,text=textos,hoverongaps=False,
       hovertemplate='%{text}<extra></extra>',xgap=2,ygap=2,
       colorscale=([[0,'#4c79b8'],[.499,'#4c79b8'],[.50,'#a6a6a6'],[.51,'#e6a565'],[1,'#e6a565']]
           if categorico else [[0,'#d7e6f1'],[0.5,'#8daed4'],[1,'#344b9d']]),
       showscale=not categorico,colorbar=dict(title='MN/m³' if 'balasto' in etiqueta.lower() or 'Ksp30' in etiqueta else 'MPa')))
    fig.update_layout(title=etiqueta,template='plotly_white',xaxis_title='L (m)',yaxis_title='B (m)',
                      height=min(850,max(430, 300+len(bs)*28)),margin=dict(l=30,r=30,t=65,b=30),
                      annotations=anotaciones)
    return fig


def figura_zapata(b,l):
    fig=go.Figure()
    fig.add_shape(type='rect',x0=-l/2,x1=l/2,y0=-b/2,y1=b/2,fillcolor='#c9dcf0',line=dict(color='#335f9a',width=3))
    fig.update_layout(template='plotly_white',height=190,margin=dict(t=10,b=10,l=10,r=10),
                      xaxis=dict(title='L (m)',scaleanchor='y'),yaxis=dict(title='B (m)'))
    return fig


def figura_bulbo(df,prof_capa,prof_act):
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=df['Delta sigma vertical (kPa)'],y=df['z bajo base (m)'],name='Δσz (Boussinesq)',mode='lines'))
    fig.add_trace(go.Scatter(x=df['umbral CTE (kPa)'],y=df['z bajo base (m)'],name='Umbral de influencia',line=dict(dash='dash')))
    fig.add_hline(y=prof_capa,line_dash='dot',annotation_text='Fin perfil elástico')
    if prof_act is not None: fig.add_hline(y=prof_act,line_dash='dot',line_color='#36987a',annotation_text='Profundidad activa')
    fig.update_layout(template='plotly_white',title='Bulbo de tensiones verticales',height=440,
                      xaxis_title='Tensión (kPa)',yaxis_title='Profundidad bajo base (m)')
    fig.update_yaxes(autorange='reversed')
    return fig


st.caption('GEOTECNIA / CTE DB-SE-C / HERRAMIENTA DE PREDIMENSIONAMIENTO')
st.title('ZapatasCTE v4.2 · Presiones admisibles B × L')
st.info('Versión completa autónoma reconstruida a partir de la funcionalidad pública v4. No es una copia exacta de GitHub ni acredita aprobación normativa. Solo carga vertical centrada y asiento elástico inmediato.')
t_ini,t_h,t_as,t_res=st.tabs(['Datos iniciales','Hundimiento','Asientos','Resultados'])

with t_ini:
    st.subheader('Identificación y barrido geométrico')
    c1,c2=st.columns([1,2],gap='large')
    with c1:
        pet=st.text_input('Peticionario',value='')
        obra=st.text_input('Trabajo',value='')
        exp=st.text_input('Expediente',value='')
    with c2:
        x1,x2,x3=st.columns(3)
        with x1: bmin=st.number_input('Bmin (m)',value=1.5,min_value=.05,step=.25)
        with x2: bmax=st.number_input('Bmax (m)',value=3.,min_value=.05,step=.25)
        with x3: db=st.number_input('Incremento B (m)',value=.5,min_value=.01,step=.05)
        x1,x2,x3=st.columns(3)
        with x1: lmin=st.number_input('Lmin (m)',value=1.5,min_value=.05,step=.25)
        with x2: lmax=st.number_input('Lmax (m)',value=5.,min_value=.05,step=.25)
        with x3: dl=st.number_input('Incremento L (m)',value=.5,min_value=.01,step=.05)
    st.caption('Se calculan exclusivamente B>0, L>=B. B y L deben ser dimensiones eficaces si existe excentricidad; esta aplicación no las calcula.')

with t_h:
    st.subheader('Hundimiento · CTE DB-SE-C')
    c1,c2,c3=st.columns(3,gap='large')
    with c1:
        drenaje=st.selectbox('Condición',('Drenada','No drenada'))
        sin_drenaje=drenaje=='No drenada'
        D=st.number_input('Profundidad de apoyo D (m)',min_value=0.,value=.5,step=.1)
        gammaR=st.selectbox('Coeficiente de resistencia γR',[3.,2.],help='Defecto 3; verifique situación de proyecto y factor aplicable.')
        factor_prof=st.checkbox('Factores de profundidad d (D>=2 m, sin talud)',value=False)
    with c2:
        phi=st.number_input('Rozamiento φ (°)',min_value=0.,max_value=89.,value=0. if sin_drenaje else 30.,step=.5,disabled=sin_drenaje)
        cohesion=st.number_input('c′ / cu (kPa)',min_value=0.,value=50. if sin_drenaje else 0.,step=5.)
        perfil_cu=st.checkbox('cu aumenta linealmente con z',disabled=not sin_drenaje)
        cu_z0=st.number_input('z0 cu (m)',value=0.,disabled=not perfil_cu)
        cu0=st.number_input('cu0 (kPa)',min_value=.1,value=50.,disabled=not perfil_cu)
        cu_z1=st.number_input('z1 cu (m)',min_value=.1,value=10.,disabled=not perfil_cu)
        cu1=st.number_input('cu1 (kPa)',min_value=.1,value=150.,disabled=not perfil_cu)
    with c3:
        nf=st.number_input('Nivel freático bajo rasante (m)',min_value=0.,value=6.6,step=.1)
        gam_ap=st.number_input('Peso aparente γ (kN/m³)',min_value=.1,value=18.,step=.5)
        gam_sub=st.number_input('Peso sumergido γ′ (kN/m³)',min_value=.1,value=9.,step=.5,
                                help='Peso sumergido, no saturado. γsat = γ′ + 9.81 kN/m³.')
        flujo=st.checkbox('Flujo ascendente',value=False)
        grad=st.number_input('Gradiente hidráulico',min_value=0.,value=.4,step=.05,disabled=not flujo)
        q0_on=st.checkbox('Sobrecarga q0 en contorno',value=True)
        gam_q0=st.number_input('γ sobrecarga (kN/m³)',min_value=.1,value=18.,disabled=not q0_on)
        alt_q0=st.number_input('Altura sobrecarga (m)',min_value=0.,value=.5,disabled=not q0_on)
        beta=st.number_input('Inclinación de talud β (°)',min_value=0.,max_value=89.,value=0.,step=.5)
        st.metric('q0 de contorno',f'{gam_q0*alt_q0 if q0_on else 0:.2f} kPa')
    st.caption('No se calculan carga horizontal, momento, excentricidad, deslizamiento ni vuelco. q0 y descarga previa a excavación son magnitudes distintas.')

with t_as:
    st.subheader('Asientos inmediatos y coeficiente de balasto')
    c1,c2=st.columns([0.9,2.1],gap='large')
    with c1:
        asiento_adm=st.number_input('Asiento admisible (cm)',min_value=.01,value=5.,step=.5)
        tipo=st.selectbox('Tipo de terreno para Ksp30',('Cohesivo','Granular'))
        criterio_txt=st.selectbox('Conversión geométrica del balasto',(
            'Literal CTE (E.6/E.7 + E.8 según geometría)',
            'Continua (adaptación técnica NO literal)'),help='El método continuo normaliza E.8 por su factor 1.5 en B=L, no es regla literal.')
        criterio='continuo' if criterio_txt.startswith('Continua') else 'literal_cte'
        st.caption('E.6: cohesivo · E.7: granular · E.8: rectangular. Solo dos tipos de suelo.')
        metodo=st.radio('Asiento bajo centro',('Superposición de cuatro cuadrantes','Aproximación histórica 2 × esquina'))
        metodo_id='superposicion' if metodo.startswith('Superposición') else 'excel'
        descarga_on=st.checkbox('Introducir tensión retirada por excavación',value=False)
        sigma_man=st.number_input('Tensión retirada (kPa)',min_value=0.,value=9.,disabled=not descarga_on)
        paso=st.number_input('Paso del bulbo (m)',min_value=.02,max_value=2.,value=.1,step=.05)
        z_man_on=st.checkbox('Profundidad del bulbo manual',value=False)
        z_man=st.number_input('Profundidad gráfica (m)',min_value=.5,value=20.,step=.5,disabled=not z_man_on)
        if criterio=='literal_cte':
            st.warning('La combinación literal de fórmulas cuadrada/rectangular tiene salto en B=L.')
        else:
            st.warning('Criterio continuo propuesto: no es E.8 literal; exige justificación del proyectista.')
    with c2:
        st.caption('Las profundidades se miden desde la base. El perfil debe comenzar en z=0 y sus capas ser contiguas.')
        capas_df=st.data_editor(pd.DataFrame({
           'Unidad':['NIVEL 1','NIVEL 2'],'z sup. (m)':[0.,2.5],
           'z inf. (m)':[2.5,10.], 'E (MPa)':[15.,1200.], 'nu':[.30,.20]}),
           num_rows='dynamic',use_container_width=True,hide_index=True,key='tabla_estratos')

p=Parametros(D_m=D,nf_m=nf,gamma_ap_kn_m3=gam_ap,gamma_sub_kn_m3=gam_sub,
    drenaje=drenaje,phi_deg=phi if not sin_drenaje else 0.,cohesion_kpa=cohesion,
    gamma_R=gammaR,incluir_q0=q0_on,gamma_q0_kn_m3=gam_q0,altura_q0_m=alt_q0,
    factor_profundidad=factor_prof,beta_deg=beta,flujo_ascendente=flujo,gradiente=grad,
    cu_gradiente=perfil_cu,cu_z0_m=cu_z0,cu0_kpa=cu0,cu_z1_m=cu_z1,cu1_kpa=cu1,
    asiento_adm_cm=asiento_adm,metodo_asiento=metodo_id,tipo_balasto=tipo,
    criterio_balasto=criterio,descarga_manual_kpa=sigma_man if descarga_on else None)
entrada=dict(proyecto=[pet,obra,exp],malla=[bmin,bmax,db,lmin,lmax,dl],parametros=asdict(p),
             capas=capas_df.to_dict(orient='records'),paso=paso,zmax=z_man if z_man_on else None)
firma=checksum(entrada)

with t_res:
    if st.button('Calcular',type='primary',use_container_width=True):
        try:
            capas=tuple(Estrato(str(x['Unidad']),float(x['z sup. (m)']),float(x['z inf. (m)']),
                                 float(x['E (MPa)']),float(x['nu'])) for x in entrada['capas'])
            geom=dimensiones(bmin,bmax,db,lmin,lmax,dl)
            rows=ejecutar_malla(geom,p,capas)
            st.session_state['ultimo_calculo']=dict(firma=firma,rows=rows,p=p,capas=capas,
                proyecto=[pet,obra,exp],paso=paso,zmax=z_man if z_man_on else None)
            st.success(f'Calculadas {len(rows)} combinaciones B × L.')
        except (ValueError,TypeError,ArithmeticError,OverflowError,KeyError) as e:
            st.error(f'Cálculo cancelado. Revise los parámetros: {e}')
    actual=st.session_state.get('ultimo_calculo')
    if actual is None:
        st.info('Introduzca datos y pulse Calcular para visualizar los resultados.')
        st.stop()
    rows=actual['rows'];pp=actual['p'];capas=actual['capas']
    desactualizado=firma!=actual['firma']
    if desactualizado:
        st.warning('Resultados obsoletos: se muestran los datos del cálculo anterior. Pulse Calcular para actualizar; descargas deshabilitadas.')
    tabla=tabla_resultados(rows)
    tb_mapa,tb_tabla,tb_met=st.tabs(['Mapa B × L y ficha','Tabla general y curvas','Método y advertencias'])
    with tb_mapa:
        iz,dr=st.columns([1.35,1.0],gap='large')
        with iz:
            metrica=st.selectbox('Variable representada',list(MAPA),key='metrica_mapa')
            if '(bruta)' in metrica:
                st.caption('Bruta = neta + tensión preexistente retirada en la base; no confundir con q0 de contorno.')
            chart=figura_mapa(rows,metrica)
            event=st.plotly_chart(chart,use_container_width=True,key='graf_mapa',on_select='rerun',selection_mode='points')
        with dr:
            st.subheader('Ficha de la zapata')
            opciones=[f'B={r["B_m"]:.2f} m · L={r["L_m"]:.2f} m' for r in rows]
            idx=st.selectbox('Geometría',range(len(opciones)),format_func=lambda i:opciones[i])
            seleccionado=rows[idx]
            try:
                pts=event.selection.points
                if pts:
                    b_s=float(pts[0]['y']);l_s=float(pts[0]['x'])
                    seleccionado=next((r for r in rows if abs(r['B_m']-b_s)<1e-7 and abs(r['L_m']-l_s)<1e-7),seleccionado)
            except (AttributeError,TypeError,KeyError,IndexError,ValueError):
                pass
            c1,c2,c3=st.columns(3)
            c1.metric('B',f"{seleccionado['B_m']:.2f} m")
            c2.metric('L',f"{seleccionado['L_m']:.2f} m")
            c3.metric('Área',f"{seleccionado['area_m2']:.2f} m²")
            st.plotly_chart(figura_zapata(seleccionado['B_m'],seleccionado['L_m']),use_container_width=True)
            st.metric('Presión de servicio neta',valor(seleccionado['q_serv_neta_mpa'])+' MPa')
            st.write('**Gobierna:**',seleccionado['limitacion'])
            st.markdown('**Comparación simultánea de presiones (MPa)**')
            comp=pd.DataFrame([{'Criterio':nombre,'Neta (MPa)':seleccionado[neta], 'Bruta (MPa)':seleccionado[bruta]}
                for nombre,neta,bruta in [('Hundimiento','q_hund_neta_mpa','q_hund_bruta_mpa'),
                ('Asientos','q_asiento_neta_mpa','q_asiento_bruta_mpa'),
                ('Servicio','q_serv_neta_mpa','q_serv_bruta_mpa')]])
            st.dataframe(comp,hide_index=True,use_container_width=True)
            with st.expander('Detalle de presiones, balasto y factores',expanded=True):
                st.write(f"q0 contorno = {seleccionado['q0_kpa']:.2f} kPa; tensión preexistente = {seleccionado['sigma_pre_base_kpa']:.2f} kPa")
                st.write(f"ks,BL = {seleccionado['ks_bl_mn_m3']:.2f} MN/m³")
                st.write(f"ks,B equivalente = {seleccionado['ks_b_equiv_mn_m3']:.2f} MN/m³")
                st.write(f"Ksp30 = {seleccionado['ksp30_mn_m3']:.2f} MN/m³ ({seleccionado['tipo_balasto']})")
                st.write(f"Criterio = {seleccionado['criterio_balasto']}; {seleccionado['referencia_balasto']}")
                st.write(f"Factor geométrico = {seleccionado['factor_forma_balasto']:.6f}; factor escala = {seleccionado['factor_escala_balasto']:.6f}")
                st.write(f"sc={seleccionado['sc']:.3f}; sq={seleccionado['sq']:.3f}; sγ={seleccionado['sgamma']:.3f}")
                contraste=comparar_criterios(seleccionado['ks_bl_mn_m3'],seleccionado['B_m'],seleccionado['L_m'],pp.tipo_balasto)
                st.caption(f"Contraste Ksp30: literal = {contraste['ksp30_literal_mn_m3']:.2f}; continuo = {contraste['ksp30_continuo_mn_m3']:.2f} MN/m³")
            if seleccionado['avisos']:
                for a in seleccionado['avisos']:
                    st.warning(a)
            ficha=dict(version=VERSION,fecha_normativa='CTE DB-SE-C Anejo E.5 y F.1',
                       proyecto=actual['proyecto'],parametros=asdict(pp),resultado=seleccionado)
            st.download_button('Descargar ficha JSON',data=json.dumps(ficha,indent=2,ensure_ascii=False,default=str),
                        file_name=f"ficha_B{seleccionado['B_m']:g}_L{seleccionado['L_m']:g}.json",
                        mime='application/json',disabled=desactualizado)
        st.divider()
        st.subheader('Diagnóstico de asientos elásticos')
        referencia=st.radio('Presión de referencia',('Servicio neto','Límite neto por asientos'),horizontal=True)
        q_ref=seleccionado['q_serv_neta_mpa'] if referencia=='Servicio neto' else seleccionado['q_asiento_neta_mpa']
        if q_ref is None or q_ref<=0:
            st.warning('Presión no positiva para el diagnóstico. Seleccione límite por asientos.')
        else:
            desglose=pd.DataFrame(contribuciones_asiento(seleccionado['B_m'],seleccionado['L_m'],capas,pp.metodo_asiento,q_ref))
            perf,prof_act=bulbo_tensiones(seleccionado['B_m'],seleccionado['L_m'],pp,capas,q_ref,actual['paso'],actual['zmax'])
            c1,c2=st.columns(2)
            with c1:
                st.metric('Asiento elástico',f"{desglose['Asiento (mm)'].sum():.2f} mm")
                st.plotly_chart(figura_bulbo(perf,capas[-1].z1,prof_act),use_container_width=True)
            with c2:
                st.metric('Profundidad activa por tensiones',f'{prof_act:.2f} m' if prof_act is not None else 'No alcanzada')
                f=go.Figure(go.Scatter(x=desglose['Asiento acumulado (mm)'],y=desglose['z inf. (m)'],mode='lines+markers'))
                f.update_layout(template='plotly_white',height=440,title='Asiento acumulado (mm)',xaxis_title='mm',yaxis_title='z bajo base (m)')
                f.update_yaxes(autorange='reversed')
                st.plotly_chart(f,use_container_width=True)
            if prof_act is None or prof_act>capas[-1].z1:
                st.warning('No queda demostrada la cobertura de la profundidad de influencia con el perfil disponible.')
            st.dataframe(desglose,hide_index=True,use_container_width=True)
            b1,b2=st.columns(2)
            with b1:
                st.download_button('Descargar asientos por estrato CSV',data=desglose.to_csv(index=False).encode('utf-8-sig'),
                                   file_name='asientos_por_estratos.csv',disabled=desactualizado)
            with b2:
                st.download_button('Descargar perfil de tensiones CSV',data=perf.to_csv(index=False).encode('utf-8-sig'),
                                   file_name='bulbo_de_tensiones.csv',disabled=desactualizado)
    with tb_tabla:
        st.subheader('Tabla general B × L')
        st.dataframe(tabla,hide_index=True,use_container_width=True,height=450)
        st.download_button('Descargar tabla completa CSV',tabla.to_csv(index=False).encode('utf-8-sig'),
                           file_name='ZapatasCTE_v42_resultados.csv',disabled=desactualizado,mime='text/csv')
        b_c=st.selectbox('Ancho B para curvas comparativas',sorted({r['B_m'] for r in rows}))
        df_b=pd.DataFrame([r for r in rows if r['B_m']==b_c])
        graf=go.Figure()
        for titulo,col in [('Hundimiento neto','q_hund_neta_mpa'),('Asientos neto','q_asiento_neta_mpa'),('Servicio neto','q_serv_neta_mpa'),
                           ('Hundimiento bruto','q_hund_bruta_mpa'),('Asientos bruto','q_asiento_bruta_mpa'),('Servicio bruto','q_serv_bruta_mpa')]:
            graf.add_trace(go.Scatter(x=df_b['L_m'],y=df_b[col],name=titulo,mode='lines+markers'))
        graf.update_layout(template='plotly_white',height=450,xaxis_title='L (m)',yaxis_title='Presión (MPa)',title=f'B = {b_c:g} m')
        st.plotly_chart(graf,use_container_width=True)
        st.subheader('Comparativa corrida histórica')
        st.caption('Referencia exclusivamente orientativa: L=100 m en asiento y L=1.000 m en hundimiento, conforme a la convención histórica descrita en v4.')
        try:
            corridas=[calcular_corrida_historica(float(b),pp,capas) for b in sorted({r['B_m'] for r in rows}) if b<=100]
            df_corrida=tabla_resultados(corridas)
            st.dataframe(df_corrida,hide_index=True,use_container_width=True)
            st.download_button('Descargar comparativa corrida CSV',df_corrida.to_csv(index=False).encode('utf-8-sig'),
                               file_name='ZapatasCTE_corrida_historica.csv',disabled=desactualizado,mime='text/csv')
        except ValueError as error:
            st.warning(f'No se pudo obtener la comparativa corrida: {error}')
    with tb_met:
        st.subheader('Método, convenciones y advertencias')
        st.markdown('''
        - **Hundimiento:** expresión resistente clásica de CTE DB-SE-C para carga centrada y vertical, con coeficiente γR elegido.
        - **Asientos:** Steinbrenner por capas y superposición de cuatro cuadrantes; aproximación histórica opcional.
        - **Presiones:** q_hund bruta se convierte en neta descontando la tensión retirada antes de ejecutar la cimentación; asientos se calculan con presión neta.
        - **Balasto:** ks,BL = q_neta/s_elástico (E.5). Ksp30 es equivalencia inversa de E.6 o E.7, con E.8 literal o adaptación continua explícitamente no literal.
        - **Limitaciones:** no modela consolidación, plastificación, interacción entre zapatas, excentricidades, cargas horizontales, deslizamiento, vuelco ni cálculo estructural del hormigón.
        - **Calidad:** modelo computacional sujeto a revisión; no constituye un certificado de cumplimiento normativo.
        ''')
        st.code(f'Versión: {VERSION} · SHA-256 entradas: {actual["firma"]}',language='text')
