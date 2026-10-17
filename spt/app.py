import streamlit as st
import pandas as pd
import numpy as np

# Configuración de la página
st.set_page_config(
    page_title="Calculadora SPT (N1)60",
    page_icon="🏗️",
    layout="centered"
)

# --- TÍTULO Y DESCRIPCIÓN ---
st.title("🏗️ Corrección de Ensayos SPT")
st.markdown("""
Esta herramienta calcula el valor corregido **$(N_1)_{60}$** basándose en las recomendaciones de 
*Skempton (1986)* y *Youd et al. (2001)*.
""")
st.markdown("---")

# --- BARRA LATERAL: CONFIGURACIÓN DEL EQUIPO ---
st.sidebar.header("⚙️ Configuración del Equipo")
st.sidebar.info("Defina aquí las características de la perforadora.")

# 1. Eficiencia del Martillo (Ce)
hammer_type = st.sidebar.selectbox(
    "Tipo de Martillo",
    options=["Martillo Automático (Estándar moderno)", "Martillo de Seguridad (Safety)", "Martillo Donut (Antiguo)"],
    index=0
)

if "Automático" in hammer_type:
    er_default = 80
elif "Seguridad" in hammer_type:
    er_default = 60
else:
    er_default = 45

efficiency = st.sidebar.slider(
    "Eficiencia de energía medida (%)", 
    min_value=30, max_value=100, value=er_default, step=5,
    help="Porcentaje de energía teórica que realmente llega al varillaje."
)
Ce = efficiency / 60.0

# 2. Diámetro del Sondeo (Cb)
borehole_diam = st.sidebar.selectbox(
    "Diámetro del Sondeo (mm)",
    options=["65 - 115 mm", "150 mm", "200 mm"],
    index=0
)

if "65 - 115" in borehole_diam:
    Cb = 1.0
elif "150" in borehole_diam:
    Cb = 1.05
else:
    Cb = 1.15

# 3. Tipo de Muestreador (Cs)
sampler_type = st.sidebar.radio(
    "Tipo de Muestreador",
    options=["Estándar (sin liners)", "Con liners (camisas)"],
    help="El muestreador con liners aumenta la fricción, por lo que se corrige."
)
Cs = 1.0 if "Estándar" in sampler_type else 1.2

# --- PANEL PRINCIPAL: DATOS DEL ENSAYO ---
st.subheader("📝 Datos del Ensayo en Profundidad")

col1, col2 = st.columns(2)

with col1:
    depth = st.number_input("Profundidad del ensayo (m)", min_value=0.5, value=3.0, step=0.5)
    n_raw = st.number_input("Valor N de campo (golpes)", min_value=1, value=15, step=1)

with col2:
    gamma_soil = st.number_input("Peso específico del suelo (kN/m³)", min_value=10.0, value=18.0, step=0.5, help="Valor típico arenas: 17-20 kN/m³")
    water_table = st.number_input("Profundidad Nivel Freático (m)", min_value=0.0, value=10.0, step=0.5, help="Si no hay agua, pon un valor mayor a la profundidad del ensayo.")

# --- CÁLCULOS (BACKEND) ---

# 1. Cálculo de Tensión Efectiva (Sigma_v')
# Asumimos peso del agua = 9.81 kN/m3
gamma_w = 9.81

if depth <= water_table:
    # Suelo seco/húmedo todo el camino
    sigma_v_eff = depth * gamma_soil
else:
    # Parte seca + Parte sumergida
    sigma_v_total = (water_table * gamma_soil) + ((depth - water_table) * gamma_soil)
    u = (depth - water_table) * gamma_w # Presión de poros
    sigma_v_eff = sigma_v_total - u

# Evitar división por cero
if sigma_v_eff < 1:
    sigma_v_eff = 1.0

# 2. Factor de corrección por sobrecarga (Cn)
# Fórmula de Liao & Whitman: sqrt(Pa / sigma_v')
# Pa ≈ 100 kPa (1 atm)
Cn = (100.0 / sigma_v_eff) ** 0.5
# Cap (límite máximo) usualmente es 1.7
if Cn > 1.7:
    Cn = 1.7

# 3. Corrección por longitud de varillaje (Cr)
if depth < 3:
    Cr = 0.75
elif depth < 4:
    Cr = 0.80
elif depth < 6:
    Cr = 0.85
elif depth < 10:
    Cr = 0.95
else:
    Cr = 1.0

# 4. Cálculo Final
N60 = n_raw * Ce * Cb * Cs * Cr
N1_60 = N60 * Cn

# --- RESULTADOS ---
st.markdown("---")
st.header("📊 Resultados")

# Mostrar resultado principal grande
res_col1, res_col2 = st.columns([1, 2])

with res_col1:
    st.metric(label="Valor N (Campo)", value=f"{n_raw}")
    st.metric(label="Tensión Efectiva (σ'v)", value=f"{sigma_v_eff:.1f} kPa")

with res_col2:
    st.success(f"### (N1)60 = {N1_60:.1f}")
    st.caption("Valor corregido por energía y sobrecarga (normalizado a 1 atm).")

# Tabla de detalles de factores
st.subheader("Detalle de Factores de Corrección")
factores_data = {
    "Factor": ["Energía (Ce)", "Sobrecarga (Cn)", "Diámetro (Cb)", "Varillaje (Cr)", "Muestreador (Cs)"],
    "Valor": [f"{Ce:.2f}", f"{Cn:.2f}", f"{Cb:.2f}", f"{Cr:.2f}", f"{Cs:.2f}"],
    "Descripción": [
        f"Eficiencia del {efficiency}%",
        f"Basado en σ'v = {sigma_v_eff:.1f} kPa",
        borehole_diam,
        f"Longitud {depth} m",
        sampler_type
    ]
}

df_factores = pd.DataFrame(factores_data)
st.table(df_factores)

# --- EXPLICACIÓN TÉCNICA (EXPANDER) ---
with st.expander("Ver Fórmulas Utilizadas"):
    st.latex(r"(N_1)_{60} = N_{campo} \times C_E \times C_N \times C_R \times C_B \times C_S")
    st.markdown("""
    Donde:
    * $C_E$: Corrección por energía del martillo ($ER/60$).
    * $C_N$: Corrección por presión de confinamiento ($\sqrt{P_a / \sigma'_v} \leq 1.7$).
    * $C_R$: Corrección por longitud del varillaje.
    * $C_B$: Corrección por diámetro de perforación.
    * $C_S$: Corrección por tipo de muestreador.
    """)
