"""GeoCorrelaciones v0.7: consulta de correlaciones, no seleccion de valores de proyecto."""
from __future__ import annotations

import math
import pandas as pd
import streamlit as st

from calculos.correlaciones import K30_TABLA, calcular_e_arcillas, calcular_e_cte, calcular_k30, obtener_poisson
from calculos.cu_validado import DatosCu, CONSOLIDACION, TIPOS_SUELO, calcular_cu
from calculos.cte_orientativos import cu_por_consistencia, cu_por_nspt_cte, phi_por_tipo_cte, CONSISTENCIA_CU, PHI_D27, eu_desde_gmax
from calculos.spt import DatosSPT, SalidaSPT, normalizar_spt
from calculos.granulares import calcular_phi_verificado, calcular_e_arenas_verificado
from calculos.dappolonia import calcular_m_dappolonia, ESTADOS as ESTADOS_DAPPOLONIA
from calculos.webb_stroud import calcular_webb, calcular_stroud_butler, WEBB_MATERIALES, STROUD_MATERIALES
from visualizacion.componentes import cabecera_pestana, mostrar_resultados

st.set_page_config(page_title='GeoCorrelaciones v0.7',layout='wide')
st.markdown('''<style>
:root{--navy:#123149;--red:#d95d56;--line:#e0e6eb;--soft:#f4f7f9}
.stApp{background:#fff;color:var(--navy)}
h1,h2,h3{color:var(--navy)}.stTabs [data-baseweb="tab-list"]{overflow-x:auto;gap:0;border-bottom:1px solid var(--line)}
.stTabs [data-baseweb="tab"]{white-space:nowrap}
.stTabs [aria-selected="true"]{color:var(--red)!important;border-bottom:2px solid var(--red)}
</style>''',unsafe_allow_html=True)


def ejecutar(fn,*args,**kwargs):
    try:return fn(*args,**kwargs)
    except ValueError as e:
        st.error(str(e));return None


def input_spt(clave: str, *, tension: bool = True) -> SalidaSPT | None:
    """Se especifica la convencion de golpeo; nunca reinterpretar N como N60 silenciosamente."""
    with st.expander('Datos de SPT y correcciones (N, N60, (N1)60)',expanded=True):
        modo=st.radio('Origen del SPT', ['Partir de N de campo','Introducir N60 conocido'],horizontal=True,key=f'{clave}_modo')
        c1,c2,c3=st.columns(3)
        if modo=='Partir de N de campo':
            n=c1.number_input('N de campo [golpes]',0.0,500.0,20.0,1.0,key=f'{clave}_nraw')
            energia=c2.number_input('Relación de energía ER [%]',1.0,200.0,60.0,1.0,key=f'{clave}_er')
            with st.expander('Factores del ensayo (si se conocen)',expanded=False):
                st.caption('CB diámetro de perforación, CR longitud de varillaje, CS muestreador. Por defecto 1,0 significa que el usuario acepta no introducir correcciones adicionales.')
                a,b,c=st.columns(3)
                cb=a.number_input('CB [-]',0.01,2.0,1.0,0.05,key=f'{clave}_cb')
                cr=b.number_input('CR [-]',0.01,2.0,1.0,0.05,key=f'{clave}_cr')
                cs=c.number_input('CS [-]',0.01,2.0,1.0,0.05,key=f'{clave}_cs')
            n60=ejecutar(normalizar_spt,DatosSPT(n,energia,cb,cr,cs))
            if n60 is None:return None
            n60v=n60.n60
        else:
            n60v=c1.number_input('N60 ya corregido [golpes]',0.0,500.0,20.0,1.0,key=f'{clave}_n60manual')
            n=float('nan')  # no se conoce el N bruto, Begemann exige otro dato
        if not tension:
            st.caption(f'N60 aplicado = {n60v:.3f} golpes. El N de campo se solicita por separado cuando un metodo historico lo necesita.')
            if modo=='Partir de N de campo':
                return SalidaSPT(n_campo=n,n60=n60v,n1_60=None,cn=None)
            # Ncampo inexistente: se usa n60 solo a efectos de los metodos basados en N60.
            return SalidaSPT(n_campo=n60v,n60=n60v,n1_60=None,cn=None)
        sigma=c3.number_input("Tensión vertical efectiva σ'v0 [kPa]",1.0,10000.0,100.0,5.0,key=f'{clave}_sig')
        cn_op=st.selectbox('Factor de confinamiento CN',['CN limitado a 1,7','CN sin limitar (Liao-Whitman)','Introducir (N1)60 independiente'],key=f'{clave}_cnmodo')
        if cn_op=='Introducir (N1)60 independiente':
            n1=st.number_input('(N1)60 conocido [golpes]',0.0,500.0,20.0,1.0,key=f'{clave}_n1manual')
            st.caption('El valor (N1)60 declarado se considera independiente; comprobar que es compatible con N60 y la tensión efectiva.')
            salida=SalidaSPT(n_campo=n if math.isfinite(n) else n60v,n60=n60v,n1_60=n1,cn=None)
        else:
            maximo=1.7 if cn_op=='CN limitado a 1,7' else None
            s=ejecutar(normalizar_spt,DatosSPT(n_campo=n60v,energia_pct=60.,sigma_v_ef_kpa=sigma,cn_max=maximo))
            if s is None:return None
            salida=SalidaSPT(n_campo=n if math.isfinite(n) else n60v,n60=n60v,n1_60=s.n1_60,cn=s.cn)
        st.caption(f'N60 = {salida.n60:.3f} · (N1)60 = {salida.n1_60:.3f}'+(f' · CN = {salida.cn:.3f}' if salida.cn is not None else ' (introducido)'))
        return salida


def tabla_intervalos(items, clave):
    df=pd.DataFrame([x.fila() for x in items])
    st.dataframe(df,hide_index=True,use_container_width=True)
    st.download_button('Descargar intervalos CSV',df.to_csv(index=False,sep=';').encode('utf-8-sig'),
                       file_name=f'{clave}.csv',mime='text/csv',key=f'csv_{clave}')

with st.sidebar:
    st.markdown('### GeoCorrelaciones')
    st.caption('v0.7 · Referencias y calculo orientativo')
    st.divider()
    proyecto=st.text_input('Proyecto',value='Caso de estudio')
    localizacion=st.text_input('Localización')
    revision=st.text_input('Autor / revisión')
    st.divider()
    st.caption('Herramienta de consulta. Solo se muestran ecuaciones con soporte documental identificado. Ver condiciones y fuentes dentro de cada método.')

st.caption('GEOCORRELACIONES · EDICIÓN 0.7')
st.title('Correlaciones geotécnicas')
st.write('Comparación por parámetro con corrección de SPT, controles de aplicabilidad y formulación accesible.')

tabs=st.tabs(['Cu','φ · Rozamiento','E · Arenas','E · Arcillas','E · CTE','Coef. Poisson','K30'])
with tabs[0]:
    cabecera_pestana('Resistencia al corte sin drenaje, cᵤ','Cuatro correlaciones bibliográficas con restricciones. Dos métodos de referencia CTE por intervalos.')
    st.markdown('#### Correlaciones bibliográficas')
    a,b,c=st.columns(3)
    sigma=a.number_input("σ'v0 efectiva [kPa]",min_value=0.0,value=150.,step=5.,key='cu_sv')
    ip=b.number_input('IP [%]',min_value=0.0,value=55.,step=1.,key='cu_ip')
    ll=c.number_input('LL [%]',min_value=0.0,value=75.,step=1.,key='cu_ll')
    a,b=st.columns(2)
    nc=a.selectbox('Consolidación',CONSOLIDACION,key='cu_nc')
    suelo=b.selectbox('Tipo de suelo',TIPOS_SUELO,key='cu_tipo')
    pre=st.checkbox("Dispongo de σ'p medido/interpretado",key='cu_pre')
    sp=st.number_input("σ'p preconsolidación [kPa]",min_value=0.,value=150.,step=5.,key='cu_sp',disabled=not pre)
    r=ejecutar(calcular_cu,DatosCu(sigma,ip,ll,nc,suelo,sp if pre else None))
    if r is not None:mostrar_resultados(r,'cu_v05',mostrar_grafico=False)
    st.divider()
    st.markdown('#### Valores orientativos del CTE (intervalos, no valores puntuales)')
    modo=st.radio('Consulta CTE', ['Consistencia de arcilla (D.3)','NSPT y qu (D.23)'],horizontal=True,key='cu_cte_modo')
    if modo=='Consistencia de arcilla (D.3)':
        cl=st.selectbox('Consistencia',list(CONSISTENCIA_CU),key='cu_cte_cl')
        item=cu_por_consistencia(cl)
    else:
        n=st.number_input('N SPT de referencia [golpes]',0.0,500.0,20.0,1.0,key='cu_cte_n')
        item=cu_por_nspt_cte(n)
    tabla_intervalos([item],'cu_cte')
    st.caption('El CTE tabula resistencia a compresión simple qu. El intervalo cu=qu/2 se deduce únicamente cuando la hipótesis no drenada de arcilla saturada es compatible.')

with tabs[1]:
    cabecera_pestana("Ángulo de rozamiento φ'",'Métodos FHWA, Wolff/Peck y dos variantes Shioi-Fukui, más tabla D.27 del CTE.')
    categoria=st.selectbox('Tipo de material para correlaciones SPT',('Arena limpia fina/media','Arena limpia gruesa','Arena con finos','Grava/arena gravosa'),key='phi_material')
    spt=input_spt('phi',tension=True)
    if spt is not None:
        sv=st.session_state['phi_sig']
        mostrar_resultados(ejecutar(calcular_phi_verificado,spt,sv,categoria) or [],'phi_v06')
        st.caption(f'Shioi-Fukui: N70 = {spt.n60*60/70:.3f} (desde N60, sin corrección por confinamiento). Wolff/Peck: utiliza (N1)60.')
    st.markdown('#### Rangos orientativos de φ por tipo de terreno (CTE D.27)')
    tipo=st.selectbox('Suelo (CTE)',list(PHI_D27),key='phi_cte_suelo')
    tabla_intervalos([phi_por_tipo_cte(tipo)],'phi_cte_d27')
    st.caption('Peck/Wolff se calcula con (N1)60. Shioi-Fukui se calcula con N70 (energía 70%): carreteras/puentes y ferrocarriles, contrastadas mediante fuente técnica secundaria. El resto de variantes sin ecuación inequívoca permanece excluido.')

with tabs[2]:
    cabecera_pestana('Módulo de elasticidad E · Arenas','Relaciones N60 de Kulhawy y Mayne (FHWA) y ramas Begemann documentadas por una fuente técnica secundaria.')
    familia=st.selectbox('Material y consolidación',('Arena con finos','Arena limpia NC','Arena limpia OC','Grava/arena gravosa'),key='arena_familia')
    spt=input_spt('egran',tension=False)
    if spt is not None:
        if st.session_state['egran_modo']=='Partir de N de campo':
            n_be=spt.n_campo
        else:
            st.caption('Para Begemann se introduce N según la convención histórica de la fuente, sin sustituirlo automáticamente por N60.')
            n_be=st.number_input('N declarado para Begemann [golpes]',min_value=0.,max_value=500.,value=20.,key='egran_nbeg')
        mostrar_resultados(ejecutar(calcular_e_arenas_verificado,spt,familia,n_begemann=n_be) or [],'e_arenas_v05')
    with st.expander('Webb (1969/1970): módulo de deformación estimado con N SPT bruto', expanded=False):
        st.caption('Fórmulas recuperadas mediante Wagh y Bambole (2024). Reflejan módulos inferidos de ensayos con placa de tornillo para estimar asientos. Utilizar N bruto sin corregir; nunca sustituirlo por N60 ni (N1)60.')
        hay_n_webb=st.checkbox('Dispongo de N SPT bruto para Webb',key='webb_hay_n')
        colw1,colw2=st.columns(2)
        n_webb=colw1.number_input('N de campo para Webb [golpes]', min_value=0., max_value=500.,value=20.,step=1.,key='webb_n',disabled=not hay_n_webb)
        material_webb=colw2.selectbox('Tipo de material (Webb)', WEBB_MATERIALES,key='webb_mat')
        if hay_n_webb:
            rr=ejecutar(calcular_webb,n_webb,material_webb)
            if rr is not None:mostrar_resultados(rr,'webb_v07',mostrar_grafico=False)
        else:
            st.caption('Introduzca N bruto para obtener el módulo empírico de la variante de Webb seleccionada.')
    with st.expander('D’Appolonia (1970): módulo de compresibilidad M, distinto de E', expanded=False):
        st.caption('Relación propia del método de asientos: M se obtiene con el N medio bruto, sin corrección, desde la base de la zapata hasta B metros por debajo. No reutilizar N60 ni (N1)60.')
        tengo_n_promedio=st.checkbox('Dispongo del N SPT medio bruto en el espesor B bajo la zapata',key='dap_tengo_n')
        col1,col2,col3=st.columns(3)
        b_dap=col1.number_input('Ancho B de cimentación [m]',min_value=0.01,value=2.0,step=0.1,key='dap_b')
        n_dap=col2.number_input('N medio bruto en espesor B [golpes]',min_value=0.0,max_value=500.0,value=20.0,step=1.0,key='dap_n',disabled=not tengo_n_promedio)
        estado_dap=col3.selectbox('Historia tensional para D’Appolonia',ESTADOS_DAPPOLONIA,index=0,key='dap_estado')
        if tengo_n_promedio and estado_dap!='No definido':
            rr=ejecutar(calcular_m_dappolonia,n_dap,b_dap,estado_dap,familia)
            if rr is not None:mostrar_resultados(rr,'m_dappolonia_v06',mostrar_grafico=False)
        else:
            st.caption('Para calcular M se necesitan el N bruto medio del intervalo B y su historia tensional. Las relaciones E basadas en N60 siguen arriba.')
    st.caption('Pendientes: Denver, Bowles, Meigh-Nixon, Wrench-Nowatzki y otras variantes con atribución o unidades no resueltas. Webb se ofrece con respaldo secundario y alcance diferenciado.')

with tabs[3]:
    cabecera_pestana('Módulo de elasticidad sin drenaje Eᵤ · Arcillas','CTE DB SE-C: tabla F.2 (Eu/cu) y tabla F.1 (Eu=fP·Gmax).')
    a,b,c=st.columns(3)
    ip=a.number_input('IP [%]',0.0,150.0,23.0,1.,key='arc_ip')
    cu=b.number_input('cᵤ obtenido de ensayo [kPa]',0.0,10000.0,200.0,5.,key='arc_cu')
    ocr=c.number_input('OCR [-]',min_value=1.0,value=2.,step=.1,key='arc_ocr')
    aplica=st.checkbox('Confirmo arcilla sobreconsolidada y condiciones compatibles del CTE',value=False,key='arc_ap')
    if aplica:
        mostrar_resultados(ejecutar(calcular_e_arcillas,ip,0,cu,ocr) or [],'arc_f2',mostrar_grafico=False)
    else:
        st.info('Seleccione la condición geotécnica para calcular Eu mediante la tabla F.2.')
    with st.expander('Alternativa: Eᵤ a partir de Gmax medido (CTE tabla F.1)',expanded=False):
        gmax=st.number_input('Gmax de cross-hole/down-hole [MPa]',min_value=0.01,value=50.0,step=1.,key='arc_gmax')
        if aplica:
            item=ejecutar(eu_desde_gmax,ip,gmax)
            if item is not None:mostrar_resultados([item],'arc_f1',mostrar_grafico=False)
        else:st.caption('Disponible cuando se confirma arcilla sobreconsolidada.')
    with st.expander('Stroud y Butler (1975): módulo edométrico M y compresibilidad mv',expanded=False):
        st.caption('Método original para materiales glaciares: mv = 1/(f2·N) y M = f2·N. N es el golpeo bruto del ensayo histórico, sin aplicar automáticamente N60; estudio con martillo de 63,5 kg y caída de 760 mm. f2 depende del IP y del depósito y debe estar documentado.')
        sa,sb,sc=st.columns(3)
        mat_sb=sa.selectbox('Material (Stroud-Butler)',STROUD_MATERIALES,key='sb_mat')
        ip_sb=sb.number_input('IP del material [%]',min_value=0.,max_value=150.,value=25.,step=1.,key='sb_ip')
        n_sb=sc.number_input('N SPT bruto del material [golpes]',min_value=0.,max_value=500.,value=20.,step=1.,key='sb_n')
        f2_sb=st.number_input('Coeficiente f2 documentado [kPa = kN/m²]',min_value=0.01,max_value=10000.,value=450.,step=10.,key='sb_f2')
        st.caption('Fuente primaria: Stroud y Butler (1975), figura 5. Por ejemplo, se observan f2 de alrededor de 440–600 kPa en numerosos casos; la figura no permite asignar una constante universal. m_v original corresponde aproximadamente a incremento de carga edométrica de 100 kPa sobre la tensión efectiva inicial.')
        con_f2=st.checkbox('He comprobado la procedencia de f2 y la compatibilidad del material y del ensayo',key='sb_confirmado')
        if con_f2:
            rr=ejecutar(calcular_stroud_butler,n_sb,ip_sb,f2_sb,mat_sb,f2_confirmado=con_f2)
            if rr is not None:mostrar_resultados(rr,'stroud_butler_v07',mostrar_grafico=False)
        else:
            st.caption('El resultado permanece deshabilitado hasta confirmar f2. M y mv no deben confundirse con E o Eu.')
    st.caption('Las cuatro expresiones Stroud/Butler del Excel no se han conservado como módulo de Young. El método recuperado usa la formulación original de compresibilidad.')

with tabs[4]:
    cabecera_pestana('E y qu orientativos por NSPT (CTE)',
        'Tabla D.23 e interpolaciones lineales propias del Excel, diferenciadas de la referencia normativa.')
    n=st.number_input('NSPT [golpes]',0.,500.,35.,1.,key='e_cte_n')
    mostrar_resultados(ejecutar(calcular_e_cte,n) or [],'e_cte_v05',mostrar_grafico=False)
    st.caption('Interpolación solo 10 a 50 golpes; para N>50 se mantienen los intervalos tabulados sin extrapolar.')

with tabs[5]:
    cabecera_pestana('Coeficiente de Poisson ν','CTE DB SE-C tabla D.24; valores orientativos de consulta.')
    mostrar_resultados(obtener_poisson(),'poisson_v05',mostrar_grafico=False)

with tabs[6]:
    cabecera_pestana('Módulo de balasto k₃₀','CTE tabla D.29 y ecuaciones E.6–E.8.')
    df=pd.DataFrame(K30_TABLA,columns=['Tipo de suelo','k30 mínimo [MN/m³]','k30 máximo [MN/m³]'])
    df['k30 máximo [MN/m³]']=df['k30 máximo [MN/m³]'].map(lambda x: '> 5000' if math.isinf(x) else f'{x:g}')
    st.dataframe(df,hide_index=True,use_container_width=True)
    a,b,c=st.columns(3)
    ancho=a.number_input('Ancho menor B [m]',min_value=.01,value=2.,step=.1,key='k_b')
    largo=b.number_input('Longitud mayor L [m]',min_value=.01,value=3.,step=.1,key='k_l')
    k30=c.number_input('k30 [MN/m³]',min_value=0.,value=25.,step=5.,key='k_30')
    mostrar_resultados(ejecutar(calcular_k30,ancho,largo,k30) or [],'k30_v05')

st.divider()
st.caption(f'Proyecto: {proyecto or "-"} · Localización: {localizacion or "-"} · Revisión: {revision or "-"} · Cc, Cs, K0 y OCR excluidos de esta edición.')
