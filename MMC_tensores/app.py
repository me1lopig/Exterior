import streamlit as st
import numpy as np
import pandas as pd
import tensor_operations as to

st.set_page_config(page_title="Tensor Math - Ing. Estructural", layout="wide")

st.title("⚙️ Análisis Tensorial de Esfuerzos / Deformaciones")
st.markdown("Herramienta matricial para la evaluación de estados tensionales en medios continuos.")

# --- SECCIÓN DE ENTRADA DE DATOS ---
st.subheader("1. Entrada del Tensor")
st.write("Introduce los componentes del tensor (Ej: Tensor de tensiones de Cauchy en MPa o kPa).")

# Matriz por defecto (estado plano de tensiones con corte puro de ejemplo)
default_matrix = pd.DataFrame(
    [[10.0, 5.0, 0.0],
     [5.0, -10.0, 0.0],
     [0.0, 0.0, 0.0]],
    columns=['x', 'y', 'z'],
    index=['x', 'y', 'z']
)

# Editor de datos interactivo
col1, col2 = st.columns([1, 2])
with col1:
    df_tensor = st.data_editor(default_matrix, use_container_width=True)
    T = df_tensor.values

# Verificación rápida de simetría para advertir al usuario
is_sym = np.allclose(T, T.T, atol=1e-5)
if not is_sym:
    st.warning("⚠️ El tensor introducido no es simétrico. Verifica los componentes fuera de la diagonal si representa un tensor de tensiones clásico.")

st.divider()

# --- SECCIÓN DE CÁLCULO Y RESULTADOS ---
st.subheader("2. Resultados del Análisis")

try:
    # Ejecución del core matemático
    I1, I2, I3 = to.get_invariants(T)
    eigvals, eigvecs = to.get_principal(T)
    T_sph, T_dev, p = to.get_decomposition(T)
    J2, J3, von_mises, tresca = to.get_deviatoric_invariants(T_dev, eigvals)
    
    col_res1, col_res2, col_res3 = st.columns(3)
    
    with col_res1:
        st.markdown("**Valores Principales**")
        st.metric(label="σ1 (Máxima)", value=f"{eigvals[0]:.2f}")
        st.metric(label="σ2 (Intermedia)", value=f"{eigvals[1]:.2f}")
        st.metric(label="σ3 (Mínima)", value=f"{eigvals[2]:.2f}")

    with col_res2:
        st.markdown("**Invariantes del Tensor**")
        st.write(f"- **I1:** {I1:.2f}")
        st.write(f"- **I2:** {I2:.2f}")
        st.write(f"- **I3:** {I3:.2f}")
        st.markdown("**Invariantes del Desviador**")
        st.write(f"- **J2:** {J2:.2f}")
        st.write(f"- **J3:** {J3:.2f}")

    with col_res3:
        st.markdown("**Criterios de Plastificación / Rotura**")
        st.metric(label="Tensión Eq. Von Mises", value=f"{von_mises:.2f}")
        st.metric(label="Cortante Máximo Tresca", value=f"{tresca:.2f}")
        st.metric(label="Presión Hidrostática (p)", value=f"{p:.2f}")

    # Despliegue de matrices adicionales
    with st.expander("Ver Descomposición Tensorial y Vectores Principales"):
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write("Tensor Esférico (Volumétrico):")
            st.dataframe(pd.DataFrame(T_sph).round(3))
        with c2:
            st.write("Tensor Desviador (Distorsión):")
            st.dataframe(pd.DataFrame(T_dev).round(3))
        with c3:
            st.write("Matriz de Cos. Directores (Direcciones Principales):")
            st.dataframe(pd.DataFrame(eigvecs).round(3))
            
    # --- SECCIÓN: COMPONENTES INTRÍNSECAS ---
    st.subheader("3. Componentes en un Plano Específico")
    col_n1, col_n2, col_n3, col_n4 = st.columns(4)
    nx = col_n1.number_input("Normal X", value=1.0)
    ny = col_n2.number_input("Normal Y", value=0.0)
    nz = col_n3.number_input("Normal Z", value=0.0)
    
    n_vec = [nx, ny, nz]
    
    if np.linalg.norm(n_vec) > 1e-12:
        t_vec, sigma_n, tau_vec, tau = to.get_plane_components(T, n_vec)
        col_n4.markdown("**Resultados en el plano:**")
        col_n4.write(f"**σn:** {sigma_n:.2f}")
        col_n4.write(f"**τ:** {tau:.2f}")
    else:
        st.error("El vector normal no puede ser [0,0,0]")

except Exception as e:
    st.error(f"Error en el cálculo numérico: {e}")
