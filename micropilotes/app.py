"""Geo_App Micropilotes · interfaz parametrica v0.5.0."""
from math import cos, radians
from dataclasses import asdict
import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from calculos.axial import calcular
from calculos.barrido import DIAMETROS_GUIA, barrido
from calculos.avanzado import longitud_necesaria
from calculos.estructural import PERFILES, UNIONES, EJECUCION, axial_estructural
from modelos.aceros_catalogo import CALIDADES, FY_GUIA, fy_referencia
from modelos.tuberias_catalogo import CATALOGO, POR_ETIQUETA, propiedades, personalizada
from modelos.tablas_guia import CORROSION, VIDAS, RECUBRIMIENTO, COACCION, perdida, recubrimiento, cr_libre
from calculos.limites_acero import limite_acero, longitud_cruce, envolvente
from modelos.espesores import intervalos_desde_espesores, espesores_desde_cotas
from modelos.adherencias import FR_DURACION, necesita_iu, preparar_estratos, resumen_aplicado
from visualizacion.graficas import perfil_adherencias, contribucion, seccion_transversal, comparacion_parcial
from visualizacion.vista_geotecnica import tabla_calculada

VERSION='0.5.0'
st.set_page_config(page_title='Geo_App | Micropilotes',layout='wide')
# Proyecto versionado: las entradas cargadas se usan como valores iniciales; no se confía en resultados externos.
from servicios.proyecto import cargar as cargar_proyecto, serializar as serializar_proyecto
from servicios.informes import excel, word, pdf
import hashlib
if 'mp_generacion' not in st.session_state: st.session_state.mp_generacion=0
if 'mp_proyecto' not in st.session_state: st.session_state.mp_proyecto={}
cargado=st.session_state.mp_proyecto
registrados={}
def ui(fn,kind,label,*args,**kwargs):
    logical=kwargs.pop('key',label)
    k=f"mp_{st.session_state.mp_generacion}_{logical}"
    args=list(args)
    if logical in cargado.get('widgets',{}):
        v=cargado['widgets'][logical]
        # Inyectar defaults en vez de sobreescribir un widget ya creado.
        if kind in ('selectbox','multiselect'):
            options=list(args[0] if args else kwargs['options'])
            if kind=='selectbox':
                if v not in options: st.error('Opción de proyecto no válida: '+label);st.stop()
                idx=options.index(v)
                if len(args)>1: args[1]=idx
                else: kwargs['index']=idx
            else:
                if not isinstance(v,list) or any(x not in options for x in v):st.error('Selección de proyecto no válida: '+label);st.stop()
                if len(args)>1:args[1]=v
                else:kwargs['default']=v
        else:
            pos=2 if kind=='number_input' else 0
            if kind=='number_input':
                lo=args[0] if len(args)>0 else kwargs.get('min_value')
                hi=args[1] if len(args)>1 else kwargs.get('max_value')
                if v is not None and (type(v) not in (float,int) or (lo is not None and v<lo) or (hi is not None and v>hi)):
                    st.error('Número de proyecto no válido: '+label);st.stop()
                if v is not None: v=float(v) if isinstance(lo,float) else v
            elif kind=='checkbox' and type(v) is not bool:st.error('Casilla de proyecto no válida: '+label);st.stop()
            elif kind=='text_input' and not isinstance(v,str):st.error('Texto de proyecto no válido: '+label);st.stop()
            if len(args)>pos:args[pos]=v
            else:kwargs['value']=v
    v=fn(label,*args,key=k,**kwargs)
    registrados[logical]=v
    return v

st.title('Geo_App · Micropilotes')
st.caption('Diseño paramétrico axial | v'+VERSION+' | Guía DGC 2005')
st.caption('Prototipo técnico · capacidades parciales de cálculo, no conformidad global. Datos iniciales sintéticos.')
proy,geot,geom,comp,tract,est,compare,export=st.tabs([
    '01 Proyecto','02 Geotecnia','03 Geometría','04 Compresión',
    '05 Tracción','06 Estructural','07 Comparativas','08 Informes'])
with proy:
    st.subheader('Identificación del proyecto')
    with st.expander('Abrir o iniciar proyecto'):
        archivo_proyecto=st.file_uploader('Proyecto JSON (esquema 1)',type=['json'],key='mp_archivo_proyecto')
        c1,c2=st.columns(2)
        if c1.button('Abrir proyecto',disabled=archivo_proyecto is None):
            try:
                st.session_state.mp_proyecto=cargar_proyecto(archivo_proyecto.getvalue())
                st.session_state.mp_generacion+=1
                st.session_state.pop('mp_informes',None)
                st.rerun()
            except (ValueError,TypeError,UnicodeError) as exc: st.error(str(exc))
        if c2.button('Nuevo proyecto'):
            st.session_state.mp_proyecto={}
            st.session_state.mp_generacion+=1
            st.session_state.pop('mp_informes',None)
            st.rerun()
        if cargado: st.caption('Proyecto recuperado. Los resultados se recalculan con el motor actual.')
    proyecto=ui(st.text_input,'text_input','Proyecto / referencia','EJEMPLO-SINTETICO')
    autor=ui(st.text_input,'text_input','Autor (opcional)')
    revision=ui(st.text_input,'text_input','Revisión (opcional)','00')
    st.markdown('[Guía DGC 2005 — documento de referencia](https://cdn.transportes.gob.es/portal-web-transportes/carreteras/normativa_tecnica/08.1_guias_tecnicas/0710200.pdf)')
    st.info('Flujo: configurar longitudes y definir el perfil en Geotecnia, seleccionar geometría y consultar resultados en las pestañas 04–08.')
with geot:
    st.subheader('1 · Configuración del cálculo')
    c1,c2,c3=st.columns(3)
    lmin=ui(c1.number_input,'number_input','Longitud mínima (m)',min_value=.1,value=3.,step=.5,format='%.2f')
    lmax=ui(c2.number_input,'number_input','Longitud máxima (m)',min_value=.1,value=15.,step=.5,format='%.2f')
    paso=ui(c3.number_input,'number_input','Incremento (m)',min_value=.01,value=.5,step=.25,format='%.2f')
    c1,c2=st.columns(2)
    a=ui(c1.number_input,'number_input','Inclinación desde la vertical (°)',0.,89.,0.,1.)
    alterna=ui(c2.selectbox,'selectbox','Régimen de tracción',['Tracción exclusiva','Alternancia compresión/tracción'],index=1)=='Alternancia compresión/tracción'
    if lmin>lmax:
        st.error('La longitud mínima no puede superar la máxima.')
    else:
        from math import ceil
        c1,c2=st.columns(2)
        c1.metric('Profundidad vertical máxima',f'{lmax*cos(radians(a)):.2f} m')
        c2.metric('Longitudes regulares (extremos incluidos)',ceil((lmax-lmin)/paso-1e-12)+1,help='El motor incorpora además cambios de estrato y la profundidad vertical de 5 m.')
    punta_teorica=ui(st.checkbox,'checkbox','Mostrar hipótesis máxima de punta: +15 % del fuste (solo compresión)')
    if punta_teorica:
        st.warning('Hipótesis máxima no verificada. Guía 3.3.1.1 y 3.3.3.1: requiere N>30 o qu>100 kPa según suelo, empotramiento ≥6D y comprobación de zona 6D/3D. No se utiliza para verificar cargas ni en la envolvente parcial.')
    with st.expander('Acciones de cálculo (opcionales)'):
        nc=ui(st.number_input,'number_input','Compresión de cálculo (kN)',min_value=0.,value=None,placeholder='Sin acción introducida')
        nt=ui(st.number_input,'number_input','Tracción de cálculo (kN)',min_value=0.,value=None,placeholder='Sin acción introducida')
        st.caption('Sin acciones se muestran capacidades, no aprovechamientos. El fuste no incluye peso propio ni rozamiento negativo; si procede, téngalos en cuenta externamente.')
    if a>30: st.warning('Revise efectos transversales y ejecución para inclinaciones elevadas.')
with geom:
    st.subheader('Geometría de cálculo')
    nom=ui(st.selectbox,'selectbox','Diámetro nominal (mm) · tabla 4.1',['Personalizado']+list(DIAMETROS_GUIA),index=4,
                     format_func=lambda v: v if isinstance(v,str) else f'{v:.1f} mm')
    dmm=ui(st.number_input,'number_input','D nominal personalizado (mm)',min_value=10.,max_value=299.,value=200.) if nom=='Personalizado' else float(nom)
    dpmm=ui(st.number_input,'number_input','Diámetro de perforación (mm)',min_value=10.,max_value=350.,
                         value=round(dmm*1.10,2),step=1.,key=f'perforacion_{dmm:g}',format='%.2f')
    st.caption('Valor inicial D +10 % (preferencia editable, no requisito de la guía). D nominal gobierna el cálculo por fuste; tabla 4.1 de revestimiento provisional.')
    if dmm in DIAMETROS_GUIA: st.caption(f'Perforación habitual de referencia según tabla 4.1: {DIAMETROS_GUIA[dmm]:g} mm.')
    extras=ui(st.multiselect,'multiselect','Otros diámetros nominales para comparar (mm)',[v for v in DIAMETROS_GUIA if v!=dmm])
    geometria={dmm:dpmm}
    for v in extras:
        geometria[v]=ui(st.number_input,'number_input',f'Perforación para D={v:g} mm',min_value=10.,max_value=350.,value=round(v*1.10,2),step=1.,key=f'perforacion_extra_{v:g}')
    d,dp=dmm/1000,dpmm/1000
with geom:
    st.divider()
    st.subheader('Armaduras tubulares · catálogo CS550 / CSTM80')
    estruct=ui(st.checkbox,'checkbox','Considerar el límite resistente de las armaduras',value=True)
    tubos=[]; arm_error=None
    if estruct:
        material=ui(st.selectbox,'selectbox','Material de inyección · tabla 2.3',list(RECUBRIMIENTO))
        uso=ui(st.selectbox,'selectbox','Recubrimiento para',['Compresión y tracción','Solo compresión','Solo tracción'])
        modo_rec='Compresion' if uso=='Solo compresión' else 'Traccion'
        minimo_rec=RECUBRIMIENTO[material][modo_rec]
        st.caption(f'Recubrimiento mínimo del cuerpo: {minimo_rec:g} mm. Comprobar también empalmes.')
        compatibles=[t.etiqueta for t in CATALOGO if any(t.de_mm<D and (P-t.de_mm)/2>=minimo_rec for D,P in geometria.items())]
        todas=[t.etiqueta for t in CATALOGO]
        opciones=todas  # orden estable al modificar diámetros
        default=[min(compatibles,key=lambda s:abs(POR_ETIQUETA[s].de_mm-114.3)+abs(POR_ETIQUETA[s].t_mm-9))] if compatibles else []
        seleccion=ui(st.multiselect,'multiselect','Secciones comerciales (74 referencias)',opciones,default=default,
                                 format_func=lambda x:x if x in compatibles else x+' · incompatible con geometrías actuales',
                                 help='Seleccione una o varias. Se conservan las 74 referencias; solo se calculan las combinaciones compatibles.')
        tubos=[POR_ETIQUETA[x] for x in seleccion]
        if ui(st.checkbox,'checkbox','Añadir sección personalizada'):
            c1,c2=st.columns(2)
            de_p=ui(c1.number_input,'number_input','Diámetro exterior personalizado (mm)',1.,value=139.7)
            t_p=ui(c2.number_input,'number_input','Espesor personalizado (mm)',.1,value=7.)
            try: tubos.append(personalizada(de_p,t_p))
            except ValueError as exc: arm_error=str(exc); st.error(arm_error)
        calidad=ui(st.selectbox,'selectbox','Calidad de acero (común a las secciones)',list(CALIDADES),index=list(CALIDADES).index('S550'))
        acero=CALIDADES[calidad]
        fy=fy_referencia(calidad)
        c1,c2,c3=st.columns(3)
        c1.metric('Límite elástico de referencia',f'{acero.limite_elastico_mpa} MPa')
        c2.metric('Resistencia a tracción fu',f'{acero.resistencia_traccion_mpa} MPa' if acero.resistencia_traccion_mpa else 'No tabulada')
        c3.metric('Alargamiento mínimo',f'{acero.alargamiento_min_pct} %' if acero.alargamiento_min_pct is not None else 'No tabulado')
        if calidad not in FY_GUIA: st.caption('Calidad no incluida en tabla 2.1; comprobar especificación y certificado aplicables.')
        with st.expander('Material certificado y catálogo completo'):
            fy_cert=ui(st.number_input,'number_input','fy certificado para estas secciones (MPa; opcional)',min_value=1.,value=None)
            if fy_cert is not None: fy=fy_cert
            st.dataframe(pd.DataFrame([propiedades(t) for t in CATALOGO]),hide_index=True,use_container_width=True)
            st.caption('Valores de catálogo sin corregir. Carga comercial conjunta CS550/CSTM80, no Rd ni dependiente del selector de calidad. 273 × 6: carga no publicada.')
        if tubos: st.dataframe(pd.DataFrame([propiedades(t) for t in tubos])[['referencia','A_cm2','peso_kg_m','carga_catalogo_kN']],hide_index=True,use_container_width=True,column_config={'referencia':'Tubería','A_cm2':'Área (cm²)','peso_kg_m':'Peso (kg/m)','carga_catalogo_kN':'Carga catálogo (kN)'})
        st.markdown('**Durabilidad y ejecución**')
        c1,c2=st.columns(2)
        terreno=ui(c1.selectbox,'selectbox','Categoría de corrosión más desfavorable · tabla 2.4',list(CORROSION))
        vida=ui(c2.selectbox,'selectbox','Vida útil de referencia (años)',VIDAS,index=2)
        re=perdida(terreno,vida)
        st.caption(f'Pérdida radial exterior tabulada: {re:.2f} mm. No se aplica reducción por compactación ni extrapolación.')
        union=ui(st.selectbox,'selectbox','Tipo de unión · tablas 3.4 / 3.7',list(UNIONES),index=4)
        ejec=ui(st.selectbox,'selectbox','Tipo de ejecución · tabla 3.5',list(EJECUCION))
        coaccion=ui(st.selectbox,'selectbox','Coacción lateral · tabla 3.6',['No definida']+list(COACCION))
        cr=None; H=None; Dr=None
        if coaccion=='Zona libre o terreno inestable':
            H=ui(st.number_input,'number_input','Longitud axial libre máxima H (m)',min_value=.001,value=None)
            Dr=ui(st.number_input,'number_input','Diámetro de camisa perdida DR (mm; vacío = diámetro de armadura)',min_value=1.,value=None)
        elif coaccion!='No definida':
            lo,hi=COACCION[coaccion]
            cr=hi if lo==hi else ui(st.number_input,'number_input','CR dentro del intervalo tabulado',min_value=lo,max_value=hi,value=hi)
        st.caption(f'Fu,c={UNIONES[union][0]:g}; Fu,t={UNIONES[union][1]:g}; Fe={EJECUCION[ejec]:g}. CR usa el extremo conservador por defecto.')
        with st.expander('Empalmes y cálculo estructural completo (opcional)'):
            # Un único dato de empalme solo cuando aplica a todas las secciones.
            emp=ui(st.number_input,'number_input','Diámetro exterior máximo de empalme común (mm; opcional)',min_value=1.,value=None)
            uc=ui(st.number_input,'number_input','Capacidad certificada común de unión a compresión (kN)',min_value=.001,value=None)
            ut=ui(st.number_input,'number_input','Capacidad certificada común de unión a tracción (kN)',min_value=.001,value=None)
            completo=ui(st.checkbox,'checkbox','Calcular también sección compuesta acero + lechada/mortero')
            fck=ui(st.number_input,'number_input','fck a 28 días (MPa)',min_value=1.,value=25.) if completo else None
            relleno=ui(st.checkbox,'checkbox','Relleno interior acreditado') if completo else False
            sr=ui(st.text_input,'text_input','Justificación de parámetros estructurales (opcional)')
        st.caption('Predimensionamiento: acero solo, sin sumar lechada, con corrosión y factores de unión/ejecución/pandeo. Sin coacción definida no se traza límite de compresión; la tracción se calcula independientemente.')
        if arm_error: st.warning('Revise la sección personalizada. No se publican límites mientras exista un error.')
with geot:
    st.divider()
    st.subheader('2 · Modelo geotécnico · Datos de entrada')
    st.caption('Espesores verticales, desde la superficie. Introduzca adherencias límite sin minorar. Datos iniciales sintéticos.')
    cols=['nombre','espesor_m','inyeccion','adlim_kPa','fr','activo']
    ejemplo=pd.DataFrame([['UG-01',5.,'IU',80.,1.65,True],['UG-02',10.,'IRS',150.,1.65,True]],columns=cols)
    with st.expander('Importación de datos · CSV'):
        archivo=st.file_uploader('Importar estratos CSV (opcional)',type=['csv'],key=f'csv_{st.session_state.mp_generacion}')
        legado=[]
        if archivo:
            try:
                df=pd.read_csv(archivo)
                if 'inyeccion' not in df.columns:
                    tipo_ant=ui(st.selectbox,'selectbox','Inyección del CSV antiguo (revise cada fila)',['IU','IR','IRS'])
                    df['inyeccion']=tipo_ant
                if 'espesor_m' not in df.columns and {'inicio_m','fin_m'}.issubset(df.columns):
                    df=pd.DataFrame(espesores_desde_cotas(df.to_dict('records')))
                if 'adlim_kPa' not in df.columns and {'iu_kPa','seleccion_kPa'}.issubset(df.columns):
                    df['adlim_kPa']=df['seleccion_kPa'].where(df['inyeccion']!='IU',df['iu_kPa'])
                if 'fr' not in df.columns:
                    fr_ant=ui(st.selectbox,'selectbox','Fr para CSV antiguo (tabla 3.2)',[1.65,1.45])
                    df['fr']=fr_ant
                if not set(cols).issubset(df.columns): raise ValueError('Columnas requeridas: '+', '.join(cols))
                if not df.activo.isin([True,False,0,1]).all(): raise ValueError('activo debe ser true/false.')
                df.activo=df.activo.astype(bool)
                legado=df.to_dict('records')
                df=df[cols].copy()
            except Exception as e:
                st.error(str(e)); st.stop()
        else:
            df=pd.DataFrame(cargado['estratos'],columns=cols) if cargado else ejemplo
        st.download_button('Descargar plantilla CSV',ejemplo.to_csv(index=False).encode(),'estratos_ejemplo.csv','text/csv')
    tabla=st.data_editor(df,num_rows='dynamic',hide_index=True,key=f'estratos_reducidos_{st.session_state.mp_generacion}',column_config={
        'nombre':st.column_config.TextColumn('Unidad',required=True),
        'espesor_m':st.column_config.NumberColumn('Espesor (m)',min_value=0.000001,required=True,format='%.2f'),
        'inyeccion':st.column_config.SelectboxColumn('Tipo inyección',options=['IU','IR','IRS'],required=True,default='IU'),
        'adlim_kPa':st.column_config.NumberColumn('Adherencia límite (kPa)',min_value=0.,format='%.2f'),
        'fr':st.column_config.SelectboxColumn('Coeficiente Fr',options=[1.45,1.65],required=True,default=1.65,
            help='Tabla 3.2: 1,45 hasta 6 meses; 1,65 para más de 6 meses. Igual para todos los tramos.'),
        'activo':st.column_config.CheckboxColumn('Fuste activo',default=True),
    })
    st.caption('Fr: 1,45 (hasta 6 meses inclusive) o 1,65 (más de 6 meses). Adherencia admisible = adherencia límite / Fr. Fuste inactivo: resistencia nula.')
    # Controles auxiliares se construyen despues de conocer el intervalo de calculo.

    prof_activa=lmax*cos(radians(a))
    iu_extra={}
    presiones=None
    modelo_error=None
    filas_calculo=[]
    fr=None
    try:
        filas_prev=intervalos_desde_espesores(tabla.to_dict('records'))
        zrecon=filas_prev[-1]['fin_m']
        c1,c2=st.columns(2)
        c1.metric('Profundidad total reconocida',f'{zrecon:.2f} m')
        c2.metric('Profundidad máxima de cálculo',f'{prof_activa:.2f} m')
        if prof_activa>zrecon+1e-8:
            raise ValueError(f'La profundidad máxima de cálculo ({prof_activa:.2f} m) supera el perfil reconocido ({zrecon:.2f} m). No se extrapola.')
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
                iu_extra[i]=ui(st.number_input,'number_input',f"Adherencia límite IU (kPa) · fila {i+1}: {f['nombre']}",
                    min_value=0.,value=dato_legado(i,f,'iu_kPa'),key=f'iu_{i}_{f["nombre"]}_{f["inyeccion"]}_{f["inicio_m"]}_{f["fin_m"]}')
        with st.expander('Control avanzado de aplicabilidad: presiones (opcional)'):
            st.caption('No intervienen en la ecuación por fuste. Son condiciones de aplicación de la figura 3.3 (apartado 4.4.2). Sin datos, la verificación numérica queda pendiente ; no se considera verificada.')
            verificar=ui(st.checkbox,'checkbox','Comprobar presiones numéricamente',value=any('pi_kPa' in x and 'plim_kPa' in x for x in legado))
            if verificar:
                presiones={}
                for i,f in enumerate(filas_prev):
                    if f['activo'] and f['inicio_m']<prof_activa:
                        c1,c2=st.columns(2)
                        pi=ui(c1.number_input,'number_input',f"p_i (kPa) · fila {i+1}",min_value=0.,value=dato_legado(i,f,'pi_kPa'),key=f'pi_{i}_{f["nombre"]}_{f["inyeccion"]}')
                        pl=ui(c2.number_input,'number_input',f"P_lím (kPa) · fila {i+1}",min_value=0.,value=dato_legado(i,f,'plim_kPa'),key=f'pl_{i}_{f["nombre"]}_{f["inyeccion"]}')
                        presiones[i]=(pi,pl)
        estratos,filas_calculo,fr=preparar_estratos(tabla.to_dict('records'),prof_activa,iu_extra,presiones)
        meses=FR_DURACION[fr]
        st.divider()
        st.subheader('3 · Modelo geotécnico · Valores calculados')
        st.caption('Solo tramos atravesados a la longitud axial máxima. Tabla de solo lectura.')
        vista=pd.DataFrame(tabla_calculada(filas_calculo,resumen_aplicado(filas_calculo,prof_activa),a))
        st.dataframe(vista,hide_index=True,use_container_width=True,column_config={
            'nombre':'Unidad','inicio_m':st.column_config.NumberColumn('Inicio vertical (m)',format='%.2f'),
            'fin_efectivo_m':st.column_config.NumberColumn('Fin vertical efectivo (m)',format='%.2f'),
            'longitud_axial_m':st.column_config.NumberColumn('Longitud axial (m)',format='%.2f'),
            'admisible_kPa':st.column_config.NumberColumn('Adherencia admisible (kPa)',format='%.2f'),
            'criterio':'Observación'})
        st.caption(f"Longitud axial total atravesada: {vista.longitud_axial_m.sum():.2f} m.")
    except (ValueError,TypeError,KeyError,OverflowError) as exc:
        modelo_error=str(exc)
        st.info('Revise el modelo geotécnico: '+modelo_error)

# Calculo sobre entradas actuales en cada rerun; no se conserva un resultado obsoleto.
cfg={'displaylogo':False,'toImageButtonOptions':{'format':'svg','filename':'micropilotes'}}
colores=['#2563eb','#0d9488','#b45309','#7c3aed','#475569','#be185d','#0891b2']
def fig_capacidad(df, modo, carga):
    campo='Rc_fuste_kN' if modo=='c' else 'Rt_fuste_kN'
    fig=go.Figure()
    for i,(diam,g) in enumerate(df.groupby('D_mm',sort=True)):
        c=colores[i%len(colores)]
        fig.add_scatter(x=g.L_m,y=g[campo],mode='lines+markers',name=f'Ø {diam:g} mm · fuste',
                        line=dict(color=c,width=2.5),marker=dict(size=4),
                        hovertemplate='L=%{x:.2f} m · R=%{y:.2f} kN<extra>%{fullData.name}</extra>')
        if modo=='c' and punta_teorica:
            fig.add_scatter(x=g.L_m,y=g.Rc_max_hipotetica_kN,mode='lines',name=f'Ø {diam:g} mm · máximo hipotético',
                            line=dict(color=c,dash='dot',width=2))
    l5=5/cos(radians(a))
    if lmin<=l5<=lmax:
        fig.add_vline(x=l5,line_dash='dash',line_color='#b45309',annotation_text='5 m verticales')
    if carga is not None: fig.add_hline(y=carga,line_dash='dash',line_color='#dc2626',annotation_text='Acción de cálculo')
    fig.update_layout(template='plotly_white',height=500,margin=dict(l=55,r=25,t=45,b=75),
                      title='Resistencia por fuste frente a longitud axial',xaxis_title='Longitud axial (m)',
                      yaxis_title='Resistencia de cálculo (kN)',legend=dict(orientation='h',y=-.22))
    return fig

error=None; filas=[]; casos={}; tabla_df=None; alternativas=[]; curvas_arm=[]
try:
    if modelo_error: raise ValueError(modelo_error)
    if any(not 0<v<=p<300 for v,p in geometria.items()):
        raise ValueError('Ámbito actual: 0 < D nominal ≤ perforación < 300 mm.')
    if nc is not None and nt is not None and nc>0 and nt>0 and not alterna:
        raise ValueError('Para cargas alternas de compresión y tracción seleccione alternancia.')
    for diam in geometria:
        filas.extend(barrido(diam/1000,lmin,lmax,paso,a,estratos,meses,alterna,punta_teorica))
        casos[diam]=calcular(diam/1000,lmax,a,estratos,meses,alterna)
    tabla_df=pd.DataFrame(filas)
    if estruct and not arm_error:
        for D,P in geometria.items():
            # Avoid binary representation mismatch on mm-m round trip.
            g=tabla_df[(tabla_df.D_mm-D).abs()<1e-7]
            for i,tubo in enumerate(tubos):
                etiqueta=f'{D:g} mm | {tubo.etiqueta} | {i+1}'
                r_c=recubrimiento(P,tubo.de_mm,material,'Compresion',emp)
                r_t=recubrimiento(P,tubo.de_mm,material,'Traccion',emp)
                base=dict(alternativa=etiqueta,D_mm=D,Dp_mm=P,**propiedades(tubo),
                          calidad=calidad,fy_MPa=fy,corrosion_mm=re,
                          holgura_mm=r_c['holgura_mm'],r_min_c_mm=r_c['r_min_mm'],r_min_t_mm=r_t['r_min_mm'],
                          empalme_mm=emp,holgura_empalme_mm=r_c['holgura_union_mm'])
                c_ok=uso!='Solo tracción' and tubo.de_mm<D and r_c['cuerpo_compatible'] and r_c['union_compatible'] is not False
                t_ok=uso!='Solo compresión' and tubo.de_mm<D and r_t['cuerpo_compatible'] and r_t['union_compatible'] is not False
                if not(c_ok or t_ok):
                    alternativas.append({**base,'estado':'Geometría incompatible para los modos seleccionados'})
                    continue
                try:
                    cr_i=cr
                    if coaccion=='Zona libre o terreno inestable':
                        if H is None: raise ValueError('Indique longitud libre H.')
                        cr_i=cr_libre(H,Dr if Dr is not None else tubo.de_mm)
                    s=limite_acero(tubo,fy,re,union,ejec,cr_i,uc,ut)
                    compuesto=None
                    if completo and cr_i is not None and s['nc_kN'] is not None:
                        compuesto=axial_estructural(D,tubo.de_mm,tubo.t_mm,re,fy,fck,union,ejec,cr_i,sr or 'Hipótesis de predimensionamiento',relleno,uc,ut)
                    L=g.L_m.tolist()
                    C=g.Rc_fuste_kN.tolist(); T=g.Rt_fuste_kN.tolist()
                    nc_lim=s['nc_kN'] if c_ok else None
                    nt_lim=s['nt_kN'] if t_ok else None
                    # If full-section capacity is lower, do not overstate the displayed partial envelope.
                    if compuesto is not None:
                        if nc_lim is not None: nc_lim=min(nc_lim,compuesto['nc_kN'])
                        if nt_lim is not None: nt_lim=min(nt_lim,compuesto['nt_kN'])
                    estado='Predimensionamiento parcial; certificado/empalmes/coacción a verificar' if s['nc_kN'] is not None else 'Compresión no evaluada: coacción/pandeo pendiente; tracción parcial'
                    fila={**base,**s,'CR':cr_i,'limite_c_kN':nc_lim,'limite_t_kN':nt_lim,
                          'Rc_compuesto_kN':compuesto['nc_kN'] if compuesto else None,
                          'Rt_compuesto_kN':compuesto['nt_kN'] if compuesto else None,
                          'L_cruce_c_m':longitud_cruce(L,C,nc_lim) if nc_lim is not None else None,
                          'L_cruce_t_m':longitud_cruce(L,T,nt_lim) if nt_lim is not None else None,
                          'Rc_parcial_Lmax_kN':min(C[-1],nc_lim) if nc_lim is not None else None,
                          'Rt_parcial_Lmax_kN':min(T[-1],nt_lim) if nt_lim is not None else None,
                          'estado':estado}
                    alternativas.append(fila)
                    curvas_arm.append((fila,tubo,L,C,T))
                except (ValueError,TypeError,KeyError,OverflowError) as exc:
                    alternativas.append({**base,'estado':str(exc)})
except (ValueError,TypeError,KeyError,OverflowError) as exc:
    error=str(exc)

def fig_armadura(fila,L,capacidades,modo):
    campo='limite_c_kN' if modo=='c' else 'limite_t_kN'
    limite=fila[campo]
    x,y=envolvente(L,capacidades,limite)
    fig=go.Figure()
    fig.add_scatter(x=L,y=capacidades,name='Fuste',line=dict(color='#2563eb',width=2.5))
    fig.add_scatter(x=x,y=y,name='Envolvente parcial',line=dict(color='#0d9488',width=3.5))
    fig.add_hline(y=limite,line_color='#b45309',line_dash='dash',annotation_text='Límite de cálculo adoptado')
    if modo=='c' and fila.get('carga_catalogo_kN') is not None:
        fig.add_hline(y=fila['carga_catalogo_kN'],line_color='#64748b',line_dash='dot',annotation_text='Carga comercial (referencia)')
    cr=longitud_cruce(L,capacidades,limite)
    if cr is not None: fig.add_vline(x=cr,line_dash='dot',annotation_text=f'Cruce: {cr:.2f} m')
    fig.update_layout(template='plotly_white',height=440,title=fila['alternativa'],
                      xaxis_title='Longitud axial (m)',yaxis_title='Capacidad (kN)',
                      legend=dict(orientation='h',y=-.2))
    return fig

def mostrar_armadura(modo,clave):
    campo='limite_c_kN' if modo=='c' else 'limite_t_kN'
    candidatas=[v for v in curvas_arm if v[0][campo] is not None]
    if not candidatas: return
    st.markdown('**Límite resistente de armadura y fuste**')
    i=st.selectbox('Alternativa para visualizar',range(len(candidatas)),format_func=lambda j:candidatas[j][0]['alternativa'],key=clave)
    fila,tubo,L,C,T=candidatas[i]
    valores=C if modo=='c' else T
    st.plotly_chart(fig_armadura(fila,L,valores,modo),use_container_width=True,config=cfg,key=clave+'_graf')
    st.caption('Envolvente parcial de fuste y acero; hipótesis de sección y pandeo constantes. Sin punta hipotética ni conformidad global.')
    df_arm=pd.DataFrame({'L_m':L,'R_fuste_kN':valores,'limite_kN':fila[campo],
                        'R_parcial_kN':[min(v,fila[campo]) for v in valores]})
    st.dataframe(df_arm.style.format(precision=2),hide_index=True,use_container_width=True)

with geot:
    if error: st.warning(error)
    else:
        st.divider()
        st.subheader('4 · Representación gráfica')
        st.plotly_chart(perfil_adherencias(filas_calculo,casos[dmm],lmax,a),use_container_width=True,config=cfg,key='perfil_041')
        st.caption('Perfil completo reconocido; zona gris por debajo de la punta. Grosor del micropilote simbólico; adherencias efectivas solo hasta la longitud máxima.')
        if presiones is None: st.caption('Control numérico de presiones no realizado (condiciones de aplicación: guía 4.4.2).')

for tab,modo,carga in [(comp,'c',nc),(tract,'t',nt)]:
    with tab:
        st.subheader('Capacidad geotécnica a '+('compresión' if modo=='c' else 'tracción'))
        if error:
            st.info('Revise las entradas: '+error)
            continue
        campo='Rc_fuste_kN' if modo=='c' else 'Rt_fuste_kN'
        st.metric('Resistencia por fuste a L máxima · D principal',f"{casos[dmm]['fuste_compresion' if modo=='c' else 'fuste_traccion']:.2f} kN")
        st.plotly_chart(fig_capacidad(tabla_df,modo,carga),use_container_width=True,config=cfg,key='cap_'+modo)
        columnas=['D_mm','L_m','z_m',campo]
        if modo=='c' and punta_teorica:
            columnas+=['punta_max_hipotetica_kN','Rc_max_hipotetica_kN']
            st.warning('La curva punteada y las columnas de punta representan únicamente el máximo hipotético. No son resistencia verificada.')
        tabla_resultado=tabla_df[columnas].copy()
        if carga is not None:
            tabla_resultado['Ed_kN']=carga
            tabla_resultado['Ed_menor_igual_R_fuste']=tabla_resultado[campo]>=carga
        st.dataframe(tabla_resultado,hide_index=True,use_container_width=True,column_config={k:st.column_config.NumberColumn(k,format='%.2f') for k in tabla_resultado.select_dtypes(include='number').columns})
        if carga is not None:
            st.caption('Comparación solo por fuste; no conformidad global ni inclusión de punta hipotética.')
        mostrar_armadura(modo,'arm_'+modo)
        elegido=st.selectbox('Longitud axial para detalle (m)',sorted(tabla_df.L_m.unique()),index=len(tabla_df.L_m.unique())-1,key='detalle_'+modo)
        detalle=calcular(d,elegido,a,estratos,meses,alterna)
        st.plotly_chart(contribucion(detalle),use_container_width=True,config=cfg,key='tramos_'+modo)
        detalle_df=pd.DataFrame(detalle['tramos'])
        st.dataframe(detalle_df,hide_index=True,column_config={k:st.column_config.NumberColumn(k,format='%.2f') for k in detalle_df.select_dtypes(include='number').columns})
with est:
    st.subheader('Armaduras · capacidades de sección')
    if error: st.info(error)
    elif not estruct: st.info('Active armaduras en Geometría.')
    elif not alternativas: st.info('Seleccione secciones y revise los datos.')
    else:
        st.dataframe(pd.DataFrame(alternativas).style.format(precision=2,na_rep='—'),hide_index=True,use_container_width=True)
        if curvas_arm:
            j=st.selectbox('Sección transversal',range(len(curvas_arm)),format_func=lambda i:curvas_arm[i][0]['alternativa'])
            fila,tubo,_,_,_=curvas_arm[j]
            st.plotly_chart(seccion_transversal(fila['D_mm'],fila['Dp_mm'],tubo.de_mm,tubo.t_mm,re,relleno),use_container_width=True,config=cfg,key='sec_042')
        st.warning('Capacidades parciales. La carga comercial no se utiliza como Rd. Geometría nominal; verificar uniones, tolerancias, corrosión y coacción real por longitud.')
with compare:
    st.subheader('Comparación de soluciones')
    if error: st.info(error)
    else:
        st.dataframe(tabla_df.pivot(index='L_m',columns='D_mm',values=['Rc_fuste_kN','Rt_fuste_kN']).style.format(precision=2),use_container_width=True)
        if nc is not None or nt is not None:
            soluciones=[]
            for diam in geometria:
                for modo,carga in [('Compresión',nc),('Tracción',nt)]:
                    if carga is None: continue
                    minimo=longitud_necesaria(diam/1000,lmax,a,estratos,meses,alterna,carga if modo=='Compresión' else 0.,carga if modo=='Tracción' else 0.,min_l=lmin)
                    soluciones.append(dict(D_mm=diam,modo=modo,Ed_kN=carga,L_min_fuste_m=minimo,estado='Alcanzada por fuste' if minimo is not None else 'No alcanzada'))
            st.dataframe(pd.DataFrame(soluciones).style.format(precision=2,na_rep='—'),hide_index=True)
        if alternativas:
            st.markdown('**Alternativas terreno–armadura · resultados a L máxima**')
            cols=['alternativa','calidad','carga_catalogo_kN','limite_c_kN','limite_t_kN','L_cruce_c_m','L_cruce_t_m','Rc_parcial_Lmax_kN','Rt_parcial_Lmax_kN','estado']
            st.dataframe(pd.DataFrame(alternativas).reindex(columns=cols).style.format(precision=2,na_rep='—'),hide_index=True)
            mostrar_armadura('c','comparar_c')
            mostrar_armadura('t','comparar_t')
with proy:
    try:
        st.download_button('Guardar proyecto JSON',serializar_proyecto(registrados,json.loads(tabla.to_json(orient='records')),VERSION),'micropilotes_proyecto.json','application/json')
    except (ValueError,TypeError) as exc: st.warning(str(exc))
with export:
    st.subheader('Exportaciones de cálculo')
    if error: st.info(error)
    else:
        entrada=dict(proyecto=proyecto,autor=autor,revision=revision,geometria_mm=geometria,L_min_m=lmin,L_max_m=lmax,paso_m=paso,angulo_grados=a,alternancia=alterna,Fr=fr,Nc_Ed_kN=nc,Nt_Ed_kN=nt,punta_hipotetica=punta_teorica,control_presiones=presiones is not None,estratos=json.loads(pd.DataFrame(filas_calculo).to_json(orient='records')))
        if estruct:
            entrada['armaduras']=dict(tubos=[propiedades(t) for t in tubos],calidad=calidad,fy_MPa=fy,material=material,uso=uso,terreno=terreno,vida=vida,corrosion_mm=re,union=union,ejecucion=ejec,coaccion=coaccion,CR=cr,H_m=H,Dr_mm=Dr,empalme_mm=emp,uc_kN=uc,ut_kN=ut,compuesto=completo,fck_MPa=fck,relleno=relleno,referencia=sr,error_entrada=arm_error)
        salida=dict(version=VERSION,entrada=entrada,barrido=json.loads(tabla_df.to_json(orient='records')),detalle_Lmax={str(k):v for k,v in casos.items()},armaduras=json.loads(pd.DataFrame(alternativas).to_json(orient='records')),estado='prototipo; punta máxima hipotética no verificada; capacidades parciales')
        if alternativas:
            st.download_button('Comparación de armaduras CSV',pd.DataFrame(alternativas).to_csv(index=False).encode('utf-8-sig'),'armaduras.csv','text/csv')
        st.download_button('Proyecto y resultados JSON',json.dumps(salida,ensure_ascii=False,indent=2,allow_nan=False),'micropilotes_resultado.json','application/json')
        st.download_button('Barrido de capacidades CSV',tabla_df.to_csv(index=False).encode('utf-8-sig'),'curvas_fuste.csv','text/csv')
        detalle_csv=pd.DataFrame(casos[dmm]['tramos'])
        st.download_button('Detalle por tramos a L máxima CSV',detalle_csv.to_csv(index=False).encode('utf-8-sig'),'tramos.csv','text/csv')
        st.caption('SVG: botón de descarga en cada gráfica.')
        firma=hashlib.sha256(json.dumps(salida,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        previo=st.session_state.get('mp_informes',{})
        if previo.get('firma')!=firma:
            previo={};st.session_state.pop('mp_informes',None)
        st.markdown('**Documentación técnica**')
        st.caption('Excel: barrido íntegro, entradas, capacidades y gráficas. Word/PDF: resumen a longitud máxima, perfil, curvas y limitaciones.')
        formato=st.selectbox('Formato a generar',['Excel (.xlsx)','Word (.docx)','PDF (.pdf)'])
        if st.button('Preparar documento'):
            try:
                fn,nombre,mime={'Excel (.xlsx)':(excel,'Micropilotes_Resultados.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                               'Word (.docx)':(word,'Micropilotes_Memoria.docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
                               'PDF (.pdf)':(pdf,'Micropilotes_Memoria.pdf','application/pdf')}[formato]
                previo={'firma':firma,'datos':fn(salida),'nombre':nombre,'mime':mime,'formato':formato}
                st.session_state.mp_informes=previo
            except Exception as exc: st.error('No se ha generado el documento: '+str(exc))
        if previo.get('formato')==formato:
            st.download_button('Descargar '+previo['nombre'],previo['datos'],previo['nombre'],previo['mime'])
