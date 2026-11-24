"""Interfaz para comprobacion geotecnica axial de micropilotes."""
import pandas as pd
import streamlit as st
from calculos.axial import Estrato, calcular

st.set_page_config(page_title='Micropilotes | Comprobacion axial', layout='wide')
st.title('Micropilotes')
st.caption('Comprobacion geotecnica axial | correlaciones empiricas de la Guia de carreteras')
st.warning('Los rozamientos limite se introducen mediante lectura justificada de la figura 3.3. Esta version no digitaliza las curvas ni comprueba la resistencia estructural.')

with st.sidebar:
    st.header('Geometria y acciones')
    d = st.number_input('Diametro nominal de calculo D (m)', min_value=0.01, value=0.20, step=0.01, format='%.3f')
    perforacion = st.number_input('Diametro de perforacion (m)', min_value=0.01, value=0.20, step=0.01, format='%.3f')
    longitud = st.number_input('Longitud axial (m)', min_value=0.1, value=10.0, step=0.5)
    angulo = st.number_input('Inclinacion respecto a la vertical (°)', min_value=0.0, max_value=89.0, value=0.0, step=1.0)
    meses = st.number_input('Duracion de la funcion estructural (meses)', min_value=0.1, value=12.0, step=1.0)
    modo = st.radio('Historia de carga', ['Solo traccion', 'Alternancia compresion y traccion'])
    nc = st.number_input('Compresion axial de calculo (kN)', min_value=0.0, value=100.0)
    nt = st.number_input('Traccion axial de calculo (kN)', min_value=0.0, value=50.0)
    peso = st.number_input('Componente axial favorable del peso propio (kN)', min_value=0.0, value=0.0, help='Valor sin minorar. Se divide por 1,2; justificar su valor.')

st.subheader('Estratigrafia y rozamiento limite')
st.write('Profundidades verticales desde la superficie. Introduzca r límite en kPa, segun la figura 3.3 y el procedimiento de inyeccion aplicable.')
tipo = st.selectbox('Procedimiento de inyeccion', ['IU', 'IR', 'IRS'])
st.info('En z < 5 m se emplea IU. Para IR o IRS debe verificarse que se cumplen las presiones minimas y demas condiciones de aplicacion de la guia.')
tabla = st.data_editor(pd.DataFrame([{'Desde (m)': 0.0, 'Hasta (m)': 12.0, 'r limite IU (kPa)': 100.0, 'r limite seleccionado (kPa)': 100.0, 'Fuste activo': True}]), num_rows='dynamic', hide_index=True, key='estratos')
fuente = st.text_input('Referencia y justificacion de las lecturas y ensayos', placeholder='Indique estratos, ensayos y procedencia de los valores')
st.caption('Desactive el fuste en cavidades y tramos de camisa permanente sin justificacion aplicable. Valores iniciales ilustrativos, no validos como datos de proyecto.')

st.subheader('Resistencia por punta en compresion')
usar_punta = st.checkbox('Considerar resistencia por punta en suelo')
punta = 0.0
justificada = False
if usar_punta:
    st.warning('Debe justificar las condiciones de la guia: zona de influencia de 6D sobre y 3D bajo punta, parametro representativo, condiciones de suelo y empotramiento minimo 6D. El 15 % es un limite, no una resistencia automatica. El empotramiento en roca queda fuera del alcance.')
    punta = st.number_input('Resistencia por punta de calculo justificada (kN)', min_value=0.0, value=0.0)
    justificada = st.checkbox('He comprobado y documentado las condiciones de aplicacion del apartado 3.3.1.1 y el valor de punta.')

if st.button('Calcular', type='primary'):
    try:
        if d > perforacion:
            raise ValueError('El diametro nominal no puede superar el diametro de perforacion.')
        if not fuente.strip():
            raise ValueError('Indique la procedencia y justificacion de los valores de rozamiento.')
        if usar_punta and not justificada:
            raise ValueError('La resistencia por punta requiere la comprobacion y justificacion expresas.')
        estratos = []
        for _, row in tabla.iterrows():
            iu = float(row['r limite IU (kPa)'])
            elegido = iu if tipo == 'IU' else float(row['r limite seleccionado (kPa)'])
            estratos.append(Estrato(float(row['Desde (m)']), float(row['Hasta (m)']), iu, elegido, bool(row['Fuste activo'])))
        r = calcular(d, longitud, angulo, estratos, meses, modo.startswith('Alternancia'), peso, punta, justificada)
        a, b = st.columns(2)
        with a:
            st.metric('Resistencia a compresion (kN)', f"{r['compresion']:.2f}")
            st.write(f"Fuste: {r['fuste_compresion']:.2f} kN | Punta: {r['punta']:.2f} kN")
            st.write('Cumple resistencia geotecnica axial' if r['compresion'] >= nc else 'No cumple resistencia geotecnica axial')
        with b:
            st.metric('Resistencia a traccion (kN)', f"{r['traccion']:.2f}")
            st.write(f"Fuste: {r['fuste_traccion']:.2f} kN | Peso minorado: {r['peso_reducido']:.2f} kN")
            st.write('Cumple resistencia geotecnica axial' if r['traccion'] >= nt else 'No cumple resistencia geotecnica axial')
        st.caption(f"Profundidad vertical de punta: {r['profundidad']:.2f} m | Fr = {r['fr']:.2f} | eta = {r['eta']:.2f}")
        st.subheader('Detalle por tramo')
        st.dataframe(pd.DataFrame(r['tramos']).rename(columns={'z_inicio':'Inicio vertical (m)', 'z_fin':'Fin vertical (m)', 'longitud_axial':'Longitud axial (m)', 'r_lim':'r limite (kPa)', 'r_calculo':'r calculo (kPa)', 'compresion':'Fuste compresion (kN)', 'traccion':'Fuste traccion (kN)'}), hide_index=True)
        st.warning('Resultado limitado a resistencia geotecnica axial. No incluye estructura, empalmes, corrosion, acciones laterales, asientos, efecto grupo ni estabilidad global. Compruebe la aplicabilidad de la guia y la validez de las lecturas.')
    except (ValueError, TypeError, KeyError) as exc:
        st.error(f'Datos no validos: {exc}')
