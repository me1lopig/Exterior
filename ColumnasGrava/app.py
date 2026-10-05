import streamlit as st
import numpy as np
import plotly.graph_objects as go
from funciones_grava import calcular_mejora_excel
from informes import generar_excel_memoria, generar_word_memoria


st.set_page_config(page_title="Diseño de Columnas de Grava", layout="wide")


def plot_comparativa_parametros(df, col_final, col_inicial, title, y_label, color_final):
    """
    Genera un gráfico Plotly comparando el parámetro del terreno natural (inicial)
    frente al terreno homogeneizado mejorado (final).
    """
    fig = go.Figure()
    
    # 1. Traza del terreno inicial (Línea base punteada)
    fig.add_trace(go.Scatter(
        x=df['Diámetro Columa de grava (m)'], 
        y=df[col_inicial], 
        mode='lines', 
        name=f'Terreno Natural ({col_inicial})',
        line=dict(color='gray', width=2, dash='dash')
    ))
    
    # 2. Traza del terreno mejorado (Línea continua con marcadores)
    fig.add_trace(go.Scatter(
        x=df['Diámetro Columa de grava (m)'], 
        y=df[col_final], 
        mode='lines+markers', 
        name=f'Terreno Mejorado ({col_final})',
        line=dict(color=color_final, width=2.5),
        marker=dict(size=8, symbol='circle')
    ))
    
    # Configuración de layout profesional
    fig.update_layout(
        title=dict(text=title, font=dict(size=18)),
        xaxis_title="Diámetro Columna de grava (m)",
        yaxis_title=y_label,
        template="plotly_white",
        hovermode="x unified",
        legend=dict(
            orientation="h", 
            yanchor="bottom", y=1.02, 
            xanchor="right", x=1
        ), # Leyenda horizontal superior para no tapar datos
        margin=dict(l=40, r=40, t=60, b=40)
    )
    return fig

st.title("🏗️ Cálculo de mejora del terreno con Columnas de Grava")
st.markdown("Esta aplicación permite evaluar la mejora del terreno mediante columnas de grava ")
st.markdown("Según el Método de Priebe (1995).")
st.markdown( "Se calculan los parámetros equivalentes del terreno homogeneizado y se generan informes en Excel y Word.")

st.markdown("Según directiva ITQ404")

with st.sidebar:
    st.header("Parámetros de las Gravas")
    phi_c = st.number_input("Ángulo de rozamiento, $\phi_c$ (º)", value=40.0, step=1.0)
    E_c = st.number_input("Módulo elástico, $E_c$ (kPa)", value=50000.0, step=100.0)
    
    st.header("Geometría de la Malla")
    separacion = st.number_input("Espaciamiento, $s$ (m)", value=2.5, step=0.1)
    tipo_malla_str = st.selectbox("Tipo de Malla", ["1 Cuadrícula", "2 Tresbolillo"], index=1)
    tipo_malla = int(tipo_malla_str.split()[0]) # Extrae el 1 o el 2
    
    st.header("Parámetros Suelo a Mejorar")
    c_s = st.number_input("Cohesión, $c$ (kPa)", value=15.0, step=1.0)
    phi_s = st.number_input("Ángulo de rozamiento, $\phi$ (º)", value=27.0, step=1.0)
    E_s = st.number_input("Módulo elástico del terreno, $E$ (kPa)", value=3000.0, step=100.0)
    nu_s = st.number_input("Coeficiente de poisson, $\\nu$", value=0.33, step=0.01)

# Generación del array de diámetros idéntico a la hoja (0.6 a 1.5 en pasos de 0.1)
diametros_array = np.round(np.arange(0.6, 1.6, 0.1), 1)

# Llamada al core matemático
df_geo, df_int1, df_int2, df_params = calcular_mejora_excel(
    diametros_array, separacion, tipo_malla, 
    phi_c, E_c, c_s, phi_s, E_s, nu_s
)

tab1, tab2, tab3, tab4 = st.tabs(["📋 Tablas de datos", "📈 Gráficas", "📥 Descargas","🧮 Formulaciones usadas"])

# --- Renderizado de la Pestaña de Tablas ---
with tab1:
    st.subheader("DATOS GEOMÉTRICOS")
    
    # Función de formato condicional para validar el rango de Priebe (Ac/A)
    def highlight_r_bounds(val):
        if isinstance(val, (int, float)):
            if val < 0.1 or val > 0.5:
                return 'color: red; font-weight: bold;'
        return ''
    
    # Aplicamos el estilo a las dos nuevas columnas de relaciones Ac/A, al final salen con dos decimales y resaltando en rojo los valores fuera del rango 0.1 a 0.5
    styled_df_geo = df_geo.style.map(
        highlight_r_bounds, 
        subset=['Ac/A (Cuadricula)', 'Ac/A (Tresbolillo)']
    ).format({
        'Ac (m2)': '{:.3f}', 
        'Ac/A (Cuadricula)': '{:.3f}', 
        'Ac/A (Tresbolillo)': '{:.3f}'
    })
    
    #st.dataframe(styled_df_geo, use_container_width=True, hide_index=True)
    st.dataframe(styled_df_geo.format(precision=2), use_container_width=True, hide_index=True)

    
    st.subheader("CÁLCULOS INTERMEDIOS")
    # El cálculo intermedio muestra solo el 'r' seleccionado (ya sin el formato rojo)
    st.dataframe(df_int1.style.format(precision=2), use_container_width=True, hide_index=True)

    st.subheader("CÁLCULOS INTERMEDIOS")
    st.dataframe(df_int2.style.format(precision=2), use_container_width=True, hide_index=True)
    
    st.subheader("CÁLCULOS DE PARÁMETROS")
    st.dataframe(df_params.style.format(precision=2), use_container_width=True, hide_index=True)

with tab2:
    st.plotly_chart(
        plot_comparativa_parametros(
            df_params, 
            col_final='f final (º)', 
            col_inicial='f inicial (º)', 
            title='Evolución Ángulo de Rozamiento Equivalente', 
            y_label='Ángulo de rozamiento (º)',
            color_final='#1f77b4'
        ), 
        use_container_width=True
    )
    
    st.plotly_chart(
        plot_comparativa_parametros(
            df_params, 
            col_final='c final (kPa)', 
            col_inicial='c inicial (kPa)', 
            title='Evolución Cohesión Equivalente', 
            y_label='Cohesión (kPa)',
            color_final='#ff7f0e'
        ), 
        use_container_width=True
    )
    
    st.plotly_chart(
        plot_comparativa_parametros(
            df_params, 
            col_final='E final (kPa)', 
            col_inicial='E inicial (kPa)', 
            title='Evolución Módulo de Elasticidad Equivalente', 
            y_label='Módulo Elástico (kPa)',
            color_final='#2ca02c'
        ), 
        use_container_width=True
    )


with tab3:
    st.subheader("Descargas y Documentación de Proyecto")
    st.markdown("Generación automática de informe de resultados.")
    
    # 1. Preparar diccionario de inputs para los reportes
    inputs_actuales = {
        "Separación (m)": separacion,
        "Tipo de Malla": "Cuadrícula" if tipo_malla == 1 else "Tresbolillo",
        "Grava - Fricción (º)": phi_c,
        "Grava - Módulo E (kPa)": E_c,
        "Suelo - Cohesión (kPa)": c_s,
        "Suelo - Fricción (º)": phi_s,
        "Suelo - Módulo E (kPa)": E_s,
        "Suelo - Poisson": nu_s
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("📊 **Matriz de Cálculo (Excel)**\nContiene los resultados de los cálculos.")
        excel_data = generar_excel_memoria(df_geo, df_int1, df_int2, df_params, inputs_actuales)
        st.download_button(
            label="📥 Descargar tablas de datos (.xlsx)",
            data=excel_data,
            file_name="matriz_columnas_grava.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    with col2:
        st.info("📄 **Memoria Justificativa (Word)**\nGenera informe")
        # Generar de nuevo las figuras silenciosamente para inyectarlas al Word
        fig_phi = plot_comparativa_parametros(df_params, 'f final (º)', 'f inicial (º)', 'Ángulo de Rozamiento', 'º', '#1f77b4')
        fig_c = plot_comparativa_parametros(df_params, 'c final (kPa)', 'c inicial (kPa)', 'Cohesión', 'kPa', '#ff7f0e')
        fig_e = plot_comparativa_parametros(df_params, 'E final (kPa)', 'E inicial (kPa)', 'Módulo Elástico', 'kPa', '#2ca02c')
        
        try:
            word_data = generar_word_memoria(df_params, [fig_phi, fig_c, fig_e], inputs_actuales)
            st.download_button(
                label="📥 Descargar Anexo de Cálculo (.docx)",
                data=word_data,
                file_name="memoria_columnas_grava.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.warning("Para generar el Word con gráficos es necesario tener instalado 'kaleido'. Ejecuta: pip install kaleido")


with tab4:
    st.header("Formulación del Método de Priebe (1995)")
    st.markdown("A continuación se detallan las ecuaciones usadas en el motor de cálculo para la homogeneización paramétrica del suelo tratado.")
    
    st.subheader("1. Relaciones Espaciales y Geometría")
    st.markdown("Área transversal de la columna ($A_c$) y el área tributaria de la celda unidad ($A$):")
    st.latex(r"A_c = \frac{\pi \cdot D^2}{4}")
    
    col_eq1, col_eq2 = st.columns(2)
    with col_eq1:
        st.markdown("**Malla en Cuadrícula:**")
        st.latex(r"A = s^2")
    with col_eq2:
        st.markdown("**Malla al Tresbolillo:**")
        st.latex(r"A = \frac{\sqrt{3}}{2} \cdot s^2 \approx 0.8667 \cdot s^2")
        
    st.markdown("Tasa de sustitución ($a_s$ o $r$):")
    st.latex(r"a_s = \frac{A_c}{A}")
    
    st.divider()
    
    st.subheader("2. Factor Básico de Mejora ($n_0$)")
    st.markdown("Coeficiente de empuje activo de la grava ($K_{ac}$) asumiendo un estado plástico interno:")
    st.latex(r"K_{ac} = \tan^2\left(45^\circ - \frac{\phi_c}{2}\right)")
    
    st.markdown("Coeficientes intermedios de compresibilidad radial de la celda ($C_n$, $C_d$, $C$), dependientes del coeficiente de Poisson del suelo ($\nu$):")
    st.latex(r"f_2 = \frac{1 - a_s}{\nu + a_s}")
    st.latex(r"C_n = 0.5 + \frac{2}{3}f_2 \quad ; \quad C_d = K_{ac} \left(\frac{2}{3}f_2\right)")
    st.latex(r"n_0 = 1 + a_s \cdot \left(\frac{C_n}{C_d}\right)")
    
    st.divider()
    
    st.subheader("3. Parámetros Homogeneizados del Terreno")
    st.markdown("Coeficiente de reparto de cargas ($m$):")
    st.latex(r"m = \frac{n_0 - 1}{n_0}")
    
    st.markdown("Parámetros equivalentes del terreno:")
    st.latex(r"\phi_{eq} = \arctan\Big[ m \cdot \tan(\phi_c) + (1 - m) \cdot \tan(\phi_0) \Big]")
    st.latex(r"c_{eq} = c_0 \cdot (1 - m)")
    st.latex(r"E_{eq} = E_0 \cdot (1 - m) + E_c \cdot m")
