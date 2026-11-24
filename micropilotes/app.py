"""Geo_App Micropilotes · interfaz parametrica v0.4.1."""
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
from modelos.aceros_catalogo import CALIDADES
from modelos.espesores import intervalos_desde_espesores, espesores_desde_cotas
from modelos.adherencias import FR_DURACION, necesita_iu, preparar_estratos, resumen_aplicado
from visualizacion.graficas import perfil_adherencias, contribucion, seccion_transversal, comparacion_parcial
from visualizacion.vista_geotecnica import tabla_calculada

VERSION='0.4.1'
st.set_page_config(page_title='Geo_App | Micropilotes',layout='wide')
st.title('Geo_App · Micropilotes')
st.caption('Diseño paramétrico axial | v'+VERSION+' | Guía DGC 2005')
st.caption('Prototipo técnico · capacidades parciales de cálculo, no conformidad global. Datos iniciales sintéticos.')
proy,geot,geom,comp,tract,est,compare,export=st.tabs([
    '01 Proyecto','02 Geotecnia','03 Geometría','04 Compresión',
    '05 Tracción','06 Estructural','07 Comparativas','08 Informes'])
with proy:
    st.subheader('Identificación del proyecto')
    proyecto=st.text_input('Proyecto / referencia','EJEMPLO-SINTETICO')
    autor=st.text_input('Autor (opcional)')
    revision=st.text_input('Revisión (opcional)','00')
    st.markdown('[Guía DGC 2005 — documento de referencia](https://cdn.transportes.gob.es/portal-web-transportes/carreteras/normativa_tecnica/08.1_guias_tecnicas/0710200.pdf)')
    st.info('Flujo: configurar longitudes y definir el perfil en Geotecnia, seleccionar geometría y consultar resultados en las pestañas 04–08.')
with geot:
    st.subheader('1 · Configuración del cálculo')
    c1,c2,c3=st.columns(3)
    lmin=c1.number_input('Longitud mínima (m)',min_value=.1,value=3.,step=.5,format='%.2f')
    lmax=c2.number_input('Longitud máxima (m)',min_value=.1,value=15.,step=.5,format='%.2f')
    paso=c3.number_input('Incremento (m)',min_value=.01,value=.5,step=.25,format='%.2f')
    c1,c2=st.columns(2)
    a=c1.number_input('Inclinación desde la vertical (°)',0.,89.,0.,1.)
    alterna=c2.selectbox('Régimen de tracción',['Tracción exclusiva','Alternancia compresión/tracción'],index=1)=='Alternancia compresión/tracción'
    if lmin>lmax:
        st.error('La longitud mínima no puede superar la máxima.')
    else:
        from math import ceil
        c1,c2=st.columns(2)
        c1.metric('Profundidad vertical máxima',f'{lmax*cos(radians(a)):.2f} m')
        c2.metric('Longitudes regulares (extremos incluidos)',ceil((lmax-lmin)/paso-1e-12)+1,help='El motor incorpora además cambios de estrato y la profundidad vertical de 5 m.')
    punta_teorica=st.checkbox('Mostrar hipótesis máxima de punta: +15 % del fuste (solo compresión)')
    if punta_teorica:
        st.warning('Hipótesis máxima no verificada. Guía 3.3.1.1 y 3.3.3.1: requiere N>30 o qu>100 kPa según suelo, empotramiento ≥6D y comprobación de zona 6D/3D. No se utiliza para verificar cargas ni en la envolvente parcial.')
    with st.expander('Acciones de cálculo (opcionales)'):
        nc=st.number_input('Compresión de cálculo (kN)',min_value=0.,value=None,placeholder='Sin acción introducida')
        nt=st.number_input('Tracción de cálculo (kN)',min_value=0.,value=None,placeholder='Sin acción introducida')
        st.caption('Sin acciones se muestran capacidades, no aprovechamientos. El fuste no incluye peso propio ni rozamiento negativo; si procede, téngalos en cuenta externamente.')
    if a>30: st.warning('Revise efectos transversales y ejecución para inclinaciones elevadas.')
with geom:
    st.subheader('Geometría de cálculo')
    nom=st.selectbox('Diámetro nominal (mm) · tabla 4.1',['Personalizado']+list(DIAMETROS_GUIA),index=4,
                     format_func=lambda v: v if isinstance(v,str) else f'{v:.1f} mm')
    dmm=st.number_input('D nominal personalizado (mm)',min_value=10.,max_value=299.,value=200.) if nom=='Personalizado' else float(nom)
    dpmm=st.number_input('Diámetro de perforación (mm)',min_value=10.,max_value=350.,
                         value=round(dmm*1.10,2),step=1.,key=f'perforacion_{dmm:g}',format='%.2f')
    st.caption('Valor inicial D +10 % (preferencia editable, no requisito de la guía). D nominal gobierna el cálculo por fuste; tabla 4.1 de revestimiento provisional.')
    if dmm in DIAMETROS_GUIA: st.caption(f'Perforación habitual de referencia según tabla 4.1: {DIAMETROS_GUIA[dmm]:g} mm.')
    extras=st.multiselect('Otros diámetros nominales para comparar (mm)',[v for v in DIAMETROS_GUIA if v!=dmm])
    geometria={dmm:dpmm}
    for v in extras:
        geometria[v]=st.number_input(f'Perforación para D={v:g} mm',min_value=10.,max_value=350.,value=round(v*1.10,2),step=1.,key=f'perforacion_extra_{v:g}')
    d,dp=dmm/1000,dpmm/1000
with geom:
    st.subheader('Armadura tubular · comprobación opcional')
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
        st.caption('Módulo preliminar: verifique corrosión, coacción lateral y uniones. No contempla barras adicionales.')
with geot:
    st.divider()
    st.subheader('2 · Modelo geotécnico · Datos de entrada')
    st.caption('Espesores verticales, desde la superficie. Introduzca adherencias límite sin minorar. Datos iniciales sintéticos.')
    cols=['nombre','espesor_m','inyeccion','adlim_kPa','fr','activo']
    ejemplo=pd.DataFrame([['UG-01',5.,'IU',80.,1.65,True],['UG-02',10.,'IRS',150.,1.65,True]],columns=cols)
    with st.expander('Importación de datos · CSV'):
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
                iu_extra[i]=st.number_input(f"Adherencia límite IU (kPa) · fila {i+1}: {f['nombre']}",
                    min_value=0.,value=dato_legado(i,f,'iu_kPa'),key=f'iu_{i}_{f["nombre"]}_{f["inyeccion"]}_{f["inicio_m"]}_{f["fin_m"]}')
        with st.expander('Control avanzado de aplicabilidad: presiones (opcional)'):
            st.caption('No intervienen en la ecuación por fuste. Son condiciones de aplicación de la figura 3.3 (apartado 4.4.2). Sin datos, la verificación numérica queda pendiente ; no se considera verificada.')
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

error=None; filas=[]; casos={}; se=None; err_s=None; tabla_df=None
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
    if estruct:
        try:
            se=axial_estructural(dmm,de,t,re,fy,fck,union,ejec,cr,sr,relleno,uc or None,ut or None)
        except (ValueError,TypeError,KeyError,OverflowError) as exc:
            err_s=str(exc)
except (ValueError,TypeError,KeyError,OverflowError) as exc:
    error=str(exc)

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
        elegido=st.selectbox('Longitud axial para detalle (m)',sorted(tabla_df.L_m.unique()),index=len(tabla_df.L_m.unique())-1,key='detalle_'+modo)
        detalle=calcular(d,elegido,a,estratos,meses,alterna)
        st.plotly_chart(contribucion(detalle),use_container_width=True,config=cfg,key='tramos_'+modo)
        detalle_df=pd.DataFrame(detalle['tramos'])
        st.dataframe(detalle_df,hide_index=True,column_config={k:st.column_config.NumberColumn(k,format='%.2f') for k in detalle_df.select_dtypes(include='number').columns})
with est:
    st.subheader('Resistencia estructural axial · D principal')
    if not estruct: st.info('Seleccione la armadura en Geometría para activar este módulo.')
    elif error or err_s: st.warning(error or err_s)
    elif se is not None:
        c1,c2=st.columns(2)
        c1.metric('Compresión de sección (kN)',f"{se['nc_kN']:.2f}")
        c2.metric('Tracción de sección (kN)',f"{se['nt_kN']:.2f}")
        st.plotly_chart(seccion_transversal(dmm,dpmm,de,t,re,relleno),use_container_width=True,config=cfg,key='sec_04')
        st.caption('Sección centrada; no acredita recubrimiento, manguitos ni tolerancias.')
        se_df=pd.DataFrame([se])
        st.dataframe(se_df,hide_index=True,column_config={k:st.column_config.NumberColumn(k,format='%.2f') for k in se_df.select_dtypes(include='number').columns})
        if not se['uniones_acreditadas']: st.warning('Faltan capacidades certificadas de uniones.')
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
        if se is not None:
            st.plotly_chart(comparacion_parcial(casos[dmm],se,(nc or 0.,nt or 0.)),use_container_width=True,config=cfg,key='comp_04')
            st.warning('Envolvente parcial del diámetro principal; sección fija supuesta para todas las longitudes, sin recalcular pandeo ni uniones. Excluye punta hipotética.')
with export:
    st.subheader('Exportaciones de cálculo')
    if error: st.info(error)
    else:
        entrada=dict(proyecto=proyecto,autor=autor,revision=revision,geometria_mm=geometria,L_min_m=lmin,L_max_m=lmax,paso_m=paso,angulo_grados=a,alternancia=alterna,Fr=fr,Nc_Ed_kN=nc,Nt_Ed_kN=nt,punta_hipotetica=punta_teorica,control_presiones=presiones is not None,estratos=json.loads(pd.DataFrame(filas_calculo).to_json(orient='records')))
        if estruct:
            entrada['seccion']=dict(de_mm=de,t_mm=t,corrosion_mm=re,fy_MPa=fy,fck_MPa=fck,calidad=calidad,propiedades_catalogo=None if calidad=='Sin seleccionar' else asdict(CALIDADES[calidad]),union=union,ejecucion=ejec,CR=cr,relleno=relleno,limite_union_c_kN=uc,limite_union_t_kN=ut,referencia=sr)
        salida=dict(version=VERSION,entrada=entrada,barrido=json.loads(tabla_df.to_json(orient='records')),detalle_Lmax={str(k):v for k,v in casos.items()},estructura=se,error_estructural=err_s,estado='prototipo; punta máxima hipotética no verificada; capacidades parciales')
        st.download_button('Proyecto y resultados JSON',json.dumps(salida,ensure_ascii=False,indent=2,allow_nan=False),'micropilotes_resultado.json','application/json')
        st.download_button('Barrido de capacidades CSV',tabla_df.to_csv(index=False).encode('utf-8-sig'),'curvas_fuste.csv','text/csv')
        detalle_csv=pd.DataFrame(casos[dmm]['tramos'])
        st.download_button('Detalle por tramos a L máxima CSV',detalle_csv.to_csv(index=False).encode('utf-8-sig'),'tramos.csv','text/csv')
        st.caption('SVG: botón de descarga en cada gráfica. Excel, Word, PDF y recarga JSON pendientes.')
