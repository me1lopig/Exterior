"""Geo_App - Micropilotes. Prototipo de calculo axial v0.3.0."""
from math import cos, radians, sin
from dataclasses import asdict
import json
import pandas as pd
import streamlit as st
from calculos.axial import Estrato, calcular
from calculos.avanzado import validar_inyeccion, validar_punta, longitud_necesaria
from calculos.estructural import PERFILES, UNIONES, EJECUCION, axial_estructural

VERSION='0.3.0'
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
    meses=st.number_input('Duracion funcion estructural (meses)',.1,value=12.)
    tipo=st.selectbox('Inyeccion',['IU','IR','IRS'])
    nc=st.number_input('Compresion de calculo (kN)',0.,value=100.)
    nt=st.number_input('Traccion de calculo (kN)',0.,value=50.)
    alterna=st.checkbox('Alternancia de compresion y traccion',value=True)
    peso=st.number_input('Peso axial favorable justificado (kN)',0.,value=0.)
    neg=st.number_input('Accion adicional de rozamiento negativo (kN)',0.,value=0.,help='Valor de calculo externo, solo si no incluido en Nc; no se calcula automaticamente.')
    peso_ref=st.text_input('Justificacion peso axial (si > 0)') if peso>0 else ''
    neg_ref=st.text_input('Justificacion rozamiento negativo y tramo sin resistencia favorable (si > 0)') if neg>0 else ''
    if a>30: st.warning('Inclinacion superior a 30°: revise efectos transversales y ejecucion.')
st.subheader('1 · Modelo geotecnico')
st.caption('Profundidades verticales. Valores de ejemplo sinteticos, no datos de obra. Puede importar CSV de adherencias externas adaptado a las columnas indicadas.')
cols=['inicio_m','fin_m','iu_kPa','seleccion_kPa','pi_kPa','plim_kPa','activo','nombre']
ejemplo=pd.DataFrame([[0.,5.,80.,80.,600.,800.,True,'Estrato A'],[5.,15.,150.,150.,600.,800.,True,'Estrato B']],columns=cols)
archivo=st.file_uploader('Importar estratos CSV (opcional)',type=['csv'])
if archivo:
    try:
        df=pd.read_csv(archivo)
        if not set(cols).issubset(df.columns): raise ValueError('Columnas requeridas: '+', '.join(cols))
        if not df.activo.isin([True,False,0,1]).all(): raise ValueError('activo debe ser true/false.')
        df=df[cols].copy()
        df.activo=df.activo.astype(bool)
    except Exception as e:
        st.error(str(e)); st.stop()
else:
    df=ejemplo
st.download_button('Descargar plantilla CSV',ejemplo.to_csv(index=False).encode(), 'estratos_ejemplo.csv','text/csv')
tabla=st.data_editor(df,num_rows='dynamic',hide_index=True,key='estratos')
fuente=st.text_input('Origen y justificacion de adherencias y presiones',placeholder='Informe, ensayo o aplicacion externa y version')
st.caption('activo=false: fuste nulo (cavidades/camisa perdida). IU en z < 5 m. pi: minimo durante IU, final de ultima fase IR o minimo de reinyeccion IRS. Filtro conservador de 4.4.2; las excepciones requieren otro metodo.')
confirma=st.checkbox('He comprobado que las correlaciones son aplicables, las presiones y su medicion son representativas y la estratigrafia cubre el intervalo.')
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
if st.button('Calcular',type='primary'):
    try:
        if not 0<d<=dp<.3: raise ValueError('D nominal <= D perforacion < 300 mm.')
        if not fuente.strip() or not confirma: raise ValueError('Aporte origen de valores y confirme aplicabilidad.')
        if nc+neg>0 and nt>0 and not alterna: raise ValueError('Si hay compresion y traccion en el mismo caso, active alternancia.')
        if peso>0 and not peso_ref.strip(): raise ValueError('Justifique el peso favorable, incluida la flotabilidad cuando proceda.')
        if neg>0 and not neg_ref.strip(): raise ValueError('Justifique la accion adicional y evite doble contabilizacion de resistencia.')
        estratos=[]
        for row in tabla.to_dict('records'):
            if pd.isna(row['activo']) or row['activo'] not in (True,False): raise ValueError('Fuste activo debe ser booleano.')
            e=Estrato(float(row['inicio_m']),float(row['fin_m']),float(row['iu_kPa']),
                      float(row['iu_kPa'] if tipo=='IU' else row['seleccion_kPa']),bool(row['activo']))
            if e.activo and e.inicio < max(l,max_l if dimensionar else l)*cos(radians(a)):
                validar_inyeccion(tipo,float(row['pi_kPa']),float(row['plim_kPa']))
            estratos.append(e)
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
        st.subheader('Resistencias por tramo')
        st.dataframe(tr,hide_index=True)
        st.line_chart(pd.concat([pd.DataFrame({'L_acumulada_m':[0.],'Rc_fuste_acumulado_kN':[0.],'Rt_fuste_acumulado_kN':[0.]}),tr],ignore_index=True),x='L_acumulada_m',y=['Rc_fuste_acumulado_kN','Rt_fuste_acumulado_kN'])
        st.bar_chart(tr,x='z_inicio',y=['compresion','traccion'])
        st.caption('Graficos: resistencia acumulada por longitud y contribucion por tramo (sin punta ni peso).')
        minimo=None
        if dimensionar:
            minimo=longitud_necesaria(d,max_l,a,estratos,meses,alterna,*acciones)
            st.metric('Longitud axial minima por fuste', 'No alcanzada' if minimo is None else f'{minimo:.3f} m')
        if se:
            st.subheader('Seccion tubular: propiedades y resistencia')
            st.json(se,expanded=False)
            if not se['uniones_acreditadas']: st.warning('Uniones: faltan limites certificados; comprobacion de seccion provisional.')
        st.warning('No es conformidad global. Pendientes: estabilidad global/cono de arranque, asientos, efecto grupo, conexiones, acciones laterales, flexion y cortante, y revision independiente.')
        entrada={'proyecto':proyecto,'D_m':d,'perforacion_m':dp,'longitud_m':l,'angulo_grados':a,'meses':meses,'inyeccion':tipo,'Nc_kN':nc,'Nt_kN':nt,'alternancia':alterna,'peso_axial_kN':peso,'rozamiento_negativo_kN':neg,'referencia_peso':peso_ref,'referencia_rozamiento_negativo':neg_ref,'estratos':json.loads(tabla.to_json(orient='records')),'origen':fuente,'punta_kN':p,'datos_punta':datos_punta}
        if estruct:
            entrada['seccion']={'de_mm':de,'t_mm':t,'re_mm':re,'fy_MPa':fy,'fck_MPa':fck,'union':union,'ejecucion':ejec,'CR':cr,'relleno':relleno,'limite_union_c_kN':uc,'limite_union_t_kN':ut,'referencia':sr}
        salida={'version':VERSION,'entrada':entrada,'geotecnia':r,'estructura':se,'comprobaciones':resumen,'longitud_minima_fuste_m':minimo,'longitud_maxima_m':max_l if dimensionar else None,'estado':'prototipo; comprobaciones parciales'}
        st.download_button('Exportar datos y resultados JSON',json.dumps(salida,ensure_ascii=False,indent=2,allow_nan=False),'micropilotes_resultado.json','application/json')
        st.download_button('Exportar tramos CSV',tr.to_csv(index=False).encode(),'tramos.csv','text/csv')
    except (ValueError,TypeError,KeyError,IndexError,OverflowError) as e:
        st.error('Revise los datos: '+str(e))
