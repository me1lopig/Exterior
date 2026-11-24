"""Geo_App - Micropilotes. Prototipo de calculo axial v0.3.3."""
from math import cos, radians, sin
from dataclasses import asdict
import json
import pandas as pd
import streamlit as st
from calculos.axial import Estrato, calcular
from calculos.avanzado import estrato_con_inyeccion, validar_punta, longitud_necesaria
from calculos.estructural import PERFILES, UNIONES, EJECUCION, axial_estructural
from modelos.aceros_catalogo import CALIDADES
from modelos.espesores import intervalos_desde_espesores, espesores_desde_cotas
from modelos.adherencias import FR_DURACION, necesita_iu, preparar_estratos, resumen_aplicado
from visualizacion.graficas import (perfil_adherencias, curvas_fuste, contribucion,
                                    seccion_transversal, comparacion_parcial, puntos_fuste)

VERSION='0.3.3'
st.set_page_config(page_title='Geo_App | Micropilotes',layout='wide')
st.title('Micropilotes | Geo_App')
st.caption('v'+VERSION+' · Guia DGC 2005 · kN, m, kPa (seccion: mm y MPa)')
st.warning('Prototipo. No sustituye la revision profesional ni las pruebas de carga. No verifica el conjunto de estados limite ni la aplicabilidad contractual de la guia.')
with st.sidebar:
    proyecto=st.text_input('Identificador del caso', 'EJEMPLO-SINTETICO')
    d=st.number_input('Diametro nominal D (m)',.01,.299,.20,.01,format='%.3f')
    dp=st.number_input('Diametro perforacion (m)',.01,.299,.22,.01,format='%.3f')
    l=st.number_input('Longitud axial (m)',.1,1000.,10.,.5)
    a=st.number_input('Inclinacion desde vertical (°)',0.,89.,0.,1.)
    nc=st.number_input('Compresion de calculo (kN)',0.,value=100.)
    nt=st.number_input('Traccion de calculo (kN)',0.,value=50.)
    alterna=st.checkbox('Alternancia de compresion y traccion',value=True)
    peso=st.number_input('Peso axial favorable justificado (kN)',0.,value=0.)
    neg=st.number_input('Accion adicional de rozamiento negativo (kN)',0.,value=0.,help='Valor de calculo externo, solo si no incluido en Nc; no se calcula automaticamente.')
    peso_ref=st.text_input('Justificacion peso axial (si > 0)') if peso>0 else ''
    neg_ref=st.text_input('Justificacion rozamiento negativo y tramo sin resistencia favorable (si > 0)') if neg>0 else ''
    if a>30: st.warning('Inclinacion superior a 30°: revise efectos transversales y ejecucion.')
st.subheader('1 · Modelo geotécnico')
st.caption('Espesores verticales, desde la superficie. Introduzca adherencias límite sin minorar. Datos iniciales sintéticos.')
cols=['nombre','espesor_m','inyeccion','adlim_kPa','fr','activo']
ejemplo=pd.DataFrame([['UG-01',5.,'IU',80.,1.65,True],['UG-02',10.,'IRS',150.,1.65,True]],columns=cols)
archivo=st.file_uploader('Importar estratos CSV (opcional)',type=['csv'])
legado=[]
if archivo:
    try:
        df=pd.read_csv(archivo)
        if 'inyeccion' not in df.columns:
            tipo_ant=st.selectbox('Inyección del CSV antiguo (revise cada fila)',['IU','IR','IRS'])
            df['inyeccion']=tipo_ant
        if 'espesor_m' not in df.columns and {'inicio_m','fin_m'}.issubset(df.columns):
            df=pd.DataFrame(espesores_desde_cotas(df.to_dict('records')))
        if 'adlim_kPa' not in df.columns and {'iu_kPa','seleccion_kPa'}.issubset(df.columns):
            df['adlim_kPa']=df['seleccion_kPa'].where(df['inyeccion']!='IU',df['iu_kPa'])
        if 'fr' not in df.columns:
            fr_ant=st.selectbox('Fr para CSV antiguo (tabla 3.2)',[1.65,1.45])
            df['fr']=fr_ant
        if not set(cols).issubset(df.columns): raise ValueError('Columnas requeridas: '+', '.join(cols))
        if not df.activo.isin([True,False,0,1]).all(): raise ValueError('activo debe ser true/false.')
        df.activo=df.activo.astype(bool)
        legado=df.to_dict('records')
        df=df[cols].copy()
    except Exception as e:
        st.error(str(e)); st.stop()
else:
    df=ejemplo
st.download_button('Descargar plantilla CSV',ejemplo.to_csv(index=False).encode(),'estratos_ejemplo.csv','text/csv')
tabla=st.data_editor(df,num_rows='dynamic',hide_index=True,key='estratos_reducidos_v1',column_config={
    'nombre':st.column_config.TextColumn('Unidad',required=True),
    'espesor_m':st.column_config.NumberColumn('Espesor (m)',min_value=0.000001,required=True,format='%.3f'),
    'inyeccion':st.column_config.SelectboxColumn('Tipo inyección',options=['IU','IR','IRS'],required=True,default='IU'),
    'adlim_kPa':st.column_config.NumberColumn('Adherencia límite (kPa)',min_value=0.,format='%.2f'),
    'fr':st.column_config.SelectboxColumn('Coeficiente Fr',options=[1.45,1.65],required=True,default=1.65,
        help='Tabla 3.2: 1,45 hasta 6 meses; 1,65 para más de 6 meses. Igual para todos los tramos.'),
    'activo':st.column_config.CheckboxColumn('Fuste activo',default=True),
})
st.caption('Fr: 1,45 (hasta 6 meses inclusive) o 1,65 (más de 6 meses). Adherencia admisible = adherencia límite / Fr. Fuste inactivo: resistencia nula.')
# Controles auxiliares se construyen despues de conocer el intervalo de calculo.
confirma=st.checkbox('He verificado la aplicabilidad de las adherencias introducidas y las condiciones de ejecución de la guía (incluidas las presiones de inyección).')
st.subheader('2 · Resistencia por punta')
usar=st.checkbox('Incluir punta en suelo (solo compresion)')
p=0.; punta_ref=''; datos_punta=None
if usar:
    tip=st.selectbox('Suelo de punta',['Granular','Cohesivo'])
    un='N corregido' if tip=='Granular' else 'qu (kPa)'
    sup=st.number_input('Estimacion prudente zona 6D superior: '+un,0.,value=0.)
    inf=st.number_input('Estimacion prudente zona 3D inferior: '+un,0.,value=0.)
    emp=st.number_input('Empotramiento axial en terreno apto (m)',0.,value=0.)
    p=st.number_input('Resistencia de calculo por punta justificada (kN)',0.,value=0.)
    punta_ref=st.text_input('Justificacion de punta y continuidad del terreno')
    datos_punta={'tipo':tip,'superior':sup,'inferior':inf,'empotramiento_m':emp,'referencia':punta_ref}
st.subheader('3 · Seccion estructural axial (opcional)')
estruct=st.checkbox('Calcular resistencia de seccion tubular')
if estruct:
    opciones=['Personalizada']+[f'{de:g} × {t:g} mm' for de,t in PERFILES]
    perfil=st.selectbox('Tuberia (seleccion parcial de catalogo)',opciones)
    if perfil=='Personalizada':
        de=st.number_input('Diametro exterior (mm)',1.,value=139.7)
        t=st.number_input('Espesor nominal (mm)',.1,value=7.)
    else: de,t=PERFILES[opciones.index(perfil)-1]
    calidad=st.selectbox('Calidad de acero de referencia', ['Sin seleccionar']+list(CALIDADES))
    if calidad != 'Sin seleccionar':
        acero=CALIDADES[calidad]
        st.caption(f'Catalogo p. 03 | {acero.norma_tabla}: limite elastico {acero.limite_elastico_mpa} MPa; resistencia a traccion {acero.resistencia_traccion_mpa} MPa; alargamiento minimo {acero.alargamiento_min_pct} %.')
        st.caption('Valores orientativos del catalogo. Confirme disponibilidad por dimension y propiedades en el certificado; no se aplican automaticamente al calculo.')
    re=st.number_input('Perdida radial exterior por corrosion (mm)',0.,value=0.)
    fy=st.number_input('Limite elastico certificado fy (MPa)',1.,value=550.)
    fck=st.number_input('Resistencia caracteristica lechada a 28 dias (MPa)',1.,value=25.)
    union=st.selectbox('Union justificada segun tablas 3.4 y 3.7',list(UNIONES),index=4)
    ejec=st.selectbox('Tipo de perforacion (tabla 3.5)',list(EJECUCION))
    cr=st.number_input('Coeficiente CR de pandeo (tabla 3.6; 0 solo si no procede)',0.,value=0.)
    relleno=st.checkbox('Relleno interior de lechada acreditado')
    uc=st.number_input('Limite certificado union en compresion (kN; 0=no aportado)',0.,value=0.)
    ut=st.number_input('Limite certificado union en traccion (kN; 0=no aportado)',0.,value=0.)
    sr=st.text_input('Justificacion estructural: certificado, vida util, corrosion, union y CR')
    ok_s=st.checkbox('He revisado materiales, reduccion por corrosion (tabla 2.4), coaccion lateral y geometria; no hay barras adicionales.')
st.subheader('4 · Predimensionamiento')
dimensionar=st.checkbox('Estimar longitud necesaria por fuste')
if dimensionar:
    max_l=st.number_input('Longitud axial maxima a explorar (m)',.1,1000.,12.,.5)
    st.caption('Sin punta ni peso favorable. Acciones constantes, incluye la accion adicional de rozamiento negativo indicada. No dimensiona por asientos, estructura o estabilidad global.')
prof_activa=max(l,max_l if dimensionar else l)*cos(radians(a))
iu_extra={}
presiones=None
modelo_error=None
filas_calculo=[]
fr=None
try:
    filas_prev=intervalos_desde_espesores(tabla.to_dict('records'))
    def dato_legado(i,f,k):
        if i>=len(legado): return None
        old=legado[i]
        if any(old.get(c)!=f.get(c) for c in ('nombre','espesor_m','inyeccion','adlim_kPa')):
            return None
        v=old.get(k)
        return float(v) if v is not None and not pd.isna(v) else None
    especiales=[(i,f) for i,f in enumerate(filas_prev) if necesita_iu(f,prof_activa)]
    if especiales:
        st.info('En los primeros 5 m verticales se aplica IU incluso si el tipo ejecutado es IR o IRS. Introduzca solo los valores IU adicionales necesarios.')
        for i,f in especiales:
            iu_extra[i]=st.number_input(f"Adherencia límite IU (kPa) · fila {i+1}: {f['nombre']}",
                min_value=0.,value=dato_legado(i,f,'iu_kPa'),key=f'iu_{i}_{f["nombre"]}_{f["inyeccion"]}_{f["inicio_m"]}_{f["fin_m"]}')
    with st.expander('Control avanzado de aplicabilidad: presiones (opcional)'):
        st.caption('No intervienen en la ecuación por fuste. Son condiciones de aplicación de la figura 3.3 (apartado 4.4.2). Sin datos, la verificación numérica queda pendiente y se requiere confirmación del técnico.')
        verificar=st.checkbox('Comprobar presiones numéricamente',value=any('pi_kPa' in x and 'plim_kPa' in x for x in legado))
        if verificar:
            presiones={}
            for i,f in enumerate(filas_prev):
                if f['activo'] and f['inicio_m']<prof_activa:
                    c1,c2=st.columns(2)
                    pi=c1.number_input(f"p_i (kPa) · fila {i+1}",min_value=0.,value=dato_legado(i,f,'pi_kPa'),key=f'pi_{i}_{f["nombre"]}_{f["inyeccion"]}')
                    pl=c2.number_input(f"P_lím (kPa) · fila {i+1}",min_value=0.,value=dato_legado(i,f,'plim_kPa'),key=f'pl_{i}_{f["nombre"]}_{f["inyeccion"]}')
                    presiones[i]=(pi,pl)
    estratos,filas_calculo,fr=preparar_estratos(tabla.to_dict('records'),prof_activa,iu_extra,presiones)
    meses=FR_DURACION[fr]
    st.markdown('**Adherencias admisibles aplicadas · cálculo automático**')
    vista=pd.DataFrame(resumen_aplicado(filas_calculo,prof_activa))
    st.dataframe(vista,hide_index=True,column_config={
        'nombre':'Unidad','espesor_m':st.column_config.NumberColumn('Espesor (m)',format='%.3f'),
        'inyeccion':'Tipo aplicado','adlim_kPa':st.column_config.NumberColumn('Adherencia límite (kPa)',format='%.2f'),
        'fr':st.column_config.NumberColumn('Fr',format='%.2f'),
        'admisible_kPa':st.column_config.NumberColumn('Adherencia admisible (kPa)',format='%.2f'),
        'activo':'Fuste activo'})
except (ValueError,TypeError,KeyError,OverflowError) as exc:
    modelo_error=str(exc)
    st.info('Revise el modelo geotécnico: '+modelo_error)
d_actual=round(d*1000,6)
opciones_graf=sorted(set([d_actual]+[v for v in (100,125,150,180,200,220,250,280) if v<=dp*1000]))
comparar_d=st.multiselect('Diametros nominales adicionales para comparar fuste (mm)',opciones_graf,
                          default=[d_actual],help='Misma estratigrafia, inyecciones, inclinacion y perforacion maxima. Comparacion solo geotecnica; no acredita compatibilidad con la armadura.')
if st.button('Calcular',type='primary'):
    try:
        if not 0<d<=dp<.3: raise ValueError('D nominal <= D perforacion < 300 mm.')
        if modelo_error: raise ValueError(modelo_error)
        if not confirma: raise ValueError('Confirme la aplicabilidad de las correlaciones y los datos introducidos.')
        if nc+neg>0 and nt>0 and not alterna: raise ValueError('Si hay compresion y traccion en el mismo caso, active alternancia.')
        if peso>0 and not peso_ref.strip(): raise ValueError('Justifique el peso favorable, incluida la flotabilidad cuando proceda.')
        if neg>0 and not neg_ref.strip(): raise ValueError('Justifique la accion adicional y evite doble contabilizacion de resistencia.')
        if presiones is None:
            st.warning('Presiones de inyección: comprobación numérica no realizada; aplicabilidad declarada por el técnico.')
        r=calcular(d,l,a,estratos,meses,alterna,peso)
        if usar:
            rep=validar_punta(d,l,a,estratos[-1].fin,tip,sup,inf,emp,punta_ref)
            datos_punta['parametro_representativo']=rep
            r=calcular(d,l,a,estratos,meses,alterna,peso,p,True)
        acciones=(nc+neg,nt)
        checks=[('Compresion geotecnica',acciones[0],r['compresion']),('Traccion geotecnica',nt,r['traccion'])]
        se=None
        if estruct:
            if not ok_s: raise ValueError('Falta confirmar condiciones estructurales.')
            se=axial_estructural(d*1000,de,t,re,fy,fck,union,ejec,cr,sr,relleno,uc or None,ut or None)
            checks += [('Compresion seccion',acciones[0],se['nc_kN']),('Traccion seccion',nt,se['nt_kN'])]
        st.header('Resultados del caso')
        c1,c2=st.columns(2)
        c1.metric('Resistencia geotecnica compresion',f"{r['compresion']:.2f} kN")
        c2.metric('Resistencia geotecnica traccion',f"{r['traccion']:.2f} kN")
        st.caption(f"Fr={r['fr']:.2f}; eta={r['eta']:.2f}; profundidad vertical={r['profundidad']:.3f} m; punta={r['punta']:.2f} kN; peso favorable minorado={r['peso_reducido']:.2f} kN.")
        resumen=[]
        for nombre,n,rd in checks:
            u=100*n/rd if rd>0 else None
            estado='Satisface comprobacion parcial' if n<=rd else 'No satisface'
            resumen.append({'comprobacion':nombre,'Ed_kN':n,'Rd_kN':rd,'aprovechamiento_pct':u,'estado':estado})
        st.dataframe(pd.DataFrame(resumen),hide_index=True)
        tr=pd.DataFrame(r['tramos'])
        tr['L_acumulada_m']=tr.longitud_axial.cumsum()
        tr['Rc_fuste_acumulado_kN']=tr.compresion.cumsum()
        tr['Rt_fuste_acumulado_kN']=tr.traccion.cumsum()
        st.subheader('Resultados graficos')
        long_graf=max(l,max_l if dimensionar else l)
        casos_graf=[]
        for diam in sorted(set([d_actual]+comparar_d)):
            if not 0<diam/1000<=dp+1e-10: raise ValueError('Diametro grafico fuera de la perforacion.')
            casos_graf.append((f'D nominal {diam:g} mm',calcular(diam/1000,long_graf,a,estratos,meses,alterna)))
        cfg={'displaylogo':False,'toImageButtonOptions':{'format':'svg','filename':'micropilotes'}}
        tabs=st.tabs(['Perfil y adherencias','Curvas de fuste','Tramos','Seccion transversal','Comparacion parcial'])
        with tabs[0]:
            st.plotly_chart(perfil_adherencias(filas_calculo,r,l,a),use_container_width=True,config=cfg,key='perfil_graf')
            st.caption('Ejes independientes; grosor del micropilote simbolico. Se representan solo las adherencias efectivamente aplicadas hasta la punta.')
        with tabs[1]:
            st.plotly_chart(curvas_fuste(casos_graf,a),use_container_width=True,config=cfg,key='fuste_graf')
            st.caption('Nodos exactos por cambio de tramo, incluido el limite de 5 m verticales. Solo fuste; sin punta ni peso favorable.')
            nodos=[]
            for nombre,rr in casos_graf:
                LL,CC,TT=puntos_fuste(rr)
                nodos.extend(dict(alternativa=nombre,L_axial_m=x,Rc_fuste_kN=c,Rt_fuste_kN=t0) for x,c,t0 in zip(LL,CC,TT))
            nodos_df=pd.DataFrame(nodos)
            st.dataframe(nodos_df,hide_index=True)
            st.download_button('Descargar nodos de curvas CSV',nodos_df.to_csv(index=False).encode(),'curvas_fuste.csv','text/csv')
        with tabs[2]:
            st.plotly_chart(contribucion(r),use_container_width=True,config=cfg,key='tramos_graf')
            st.dataframe(tr,hide_index=True)
        with tabs[3]:
            if se is not None:
                st.plotly_chart(seccion_transversal(d*1000,dp*1000,de,t,re,relleno),use_container_width=True,config=cfg,key='seccion_graf')
                st.caption('Seccion centrada nominal, sin manguitos ni tolerancias. No verifica el recubrimiento.')
            else:
                st.info('Active el calculo estructural para visualizar la seccion.')
        with tabs[4]:
            if se is not None:
                st.plotly_chart(comparacion_parcial(r,se,acciones),use_container_width=True,config=cfg,key='comparacion_graf')
                st.warning('Solo fuste frente a capacidad de seccion fija del caso introducido. No se recalcula el pandeo ni las uniones para cada longitud; no es una envolvente global de proyecto.')
            else:
                st.info('Active el calculo estructural para comparar capacidades.')
        minimo=None
        if dimensionar:
            minimo=longitud_necesaria(d,max_l,a,estratos,meses,alterna,*acciones)
            st.metric('Longitud axial minima por fuste', 'No alcanzada' if minimo is None else f'{minimo:.3f} m')
        if se:
            st.subheader('Seccion tubular: propiedades y resistencia')
            st.json(se,expanded=False)
            if not se['uniones_acreditadas']: st.warning('Uniones: faltan limites certificados; comprobacion de seccion provisional.')
        st.warning('No es conformidad global. Pendientes: estabilidad global/cono de arranque, asientos, efecto grupo, conexiones, acciones laterales, flexion y cortante, y revision independiente.')
        entrada={'proyecto':proyecto,'D_m':d,'perforacion_m':dp,'longitud_m':l,'angulo_grados':a,'Fr':fr,'duracion_funcion_estructural':'hasta 6 meses' if fr==1.45 else 'superior a 6 meses','presiones_control_numerico':presiones is not None,'aplicabilidad_declarada':confirma,'Nc_kN':nc,'Nt_kN':nt,'alternancia':alterna,'peso_axial_kN':peso,'rozamiento_negativo_kN':neg,'referencia_peso':peso_ref,'referencia_rozamiento_negativo':neg_ref,'estratos':json.loads(pd.DataFrame(filas_calculo).to_json(orient='records')),'punta_kN':p,'datos_punta':datos_punta}
        if estruct:
            entrada['seccion']={'de_mm':de,'t_mm':t,'re_mm':re,'calidad_catalogo':None if calidad=='Sin seleccionar' else calidad,'propiedades_catalogo':None if calidad=='Sin seleccionar' else asdict(CALIDADES[calidad]),'fy_MPa':fy,'fck_MPa':fck,'union':union,'ejecucion':ejec,'CR':cr,'relleno':relleno,'limite_union_c_kN':uc,'limite_union_t_kN':ut,'referencia':sr}
        salida={'version':VERSION,'entrada':entrada,'geotecnia':r,'estructura':se,'comprobaciones':resumen,'curvas_fuste_nodos':nodos,'longitud_minima_fuste_m':minimo,'longitud_maxima_m':max_l if dimensionar else None,'estado':'prototipo; comprobaciones parciales'}
        st.download_button('Exportar datos y resultados JSON',json.dumps(salida,ensure_ascii=False,indent=2,allow_nan=False),'micropilotes_resultado.json','application/json')
        st.download_button('Exportar tramos CSV',tr.to_csv(index=False).encode(),'tramos.csv','text/csv')
    except (ValueError,TypeError,KeyError,IndexError,OverflowError) as e:
        st.error('Revise los datos: '+str(e))
