import numpy as np
import pandas as pd



def calcular_mejora_excel(
    diametros: np.ndarray, separacion: float, tipo_malla: int, 
    phi_c: float, E_c: float, c_s: float, phi_s: float, E_s: float, nu_s: float
):
    """
    Motor vectorizado que reproduce de forma exacta la lógica y estructura tabular
    de 'Columnas de grava.xlsx'.
    """
# --- 1. DATOS GEOMÉTRICOS ---
    Ac = np.pi * 0.25 * diametros**2
    Area_cuad = np.full_like(diametros, separacion**2)
    Area_tres = np.full_like(diametros, 0.8667 * separacion**2) 
    
    # Calculamos ambas relaciones independientemente de la seleccionada
    r_cuad = Ac / Area_cuad
    r_tres = Ac / Area_tres
    
    # La variable r de cálculo sigue dependiendo del tipo de malla elegido
    r = r_cuad if tipo_malla == 1 else r_tres
        
    df_geo = pd.DataFrame({
        'Diámetro Columa de grava (m)': diametros,
        'Ac (m2)': Ac,
        'Separación (m)': separacion,
        'Area cuadricula (m2)': Area_cuad,
        'Area Tresbolillo (m2)': Area_tres,
        'Ac/A (Cuadricula)': r_cuad,  # Columna F oculta en Excel
        'Ac/A (Tresbolillo)': r_tres  # Columna G oculta en Excel
    })



    # --- 2. CÁLCULOS INTERMEDIOS 1 ---
    uno_mas_r = 1.0 + r
    uno_menos_r = 1.0 - r
    
    df_int1 = pd.DataFrame({
        'Diámetro Columa de grava (m)': diametros,
        'Ac (m2)': Ac,
        'r (--)': r,
        '1+r (--)': uno_mas_r,
        '1-r (--)': uno_menos_r
    })

    # --- 3. CÁLCULOS INTERMEDIOS 2 ---
    # Variables ocultas en columnas F y G de la fila 46
    f1 = nu_s + r
    f2 = uno_menos_r / f1
    
    Cn = 0.5 + 2.0 * f2 / 3.0
    K_ac = np.tan(np.radians(45.0) - 0.5 * np.radians(phi_c))**2
    Cd = K_ac * 2.0 * f2 / 3.0
    C = Cn / Cd
    no = 1.0 + r * C
    
    df_int2 = pd.DataFrame({
        'Diámetro Columa de grava (m)': diametros,
        'Cn (--)': Cn,
        'Cd (--)': Cd,
        'C (--)': C,
        'no (--)': no
    })

    # --- 4. CÁLCULOS PARÁMETROS ---
    # Fila oculta F61 para coeficiente m
    m = (no - 1.0) / no
    
    f_final = np.degrees(np.arctan(m * np.tan(np.radians(phi_c)) + (1.0 - m) * np.tan(np.radians(phi_s))))
    c_final = c_s * (1.0 - m)
    E_final = E_s * (1.0 - m) + E_c * m
    
    df_params = pd.DataFrame({
        'Diámetro Columa de grava (m)': diametros,
        'f inicial (º)': np.full_like(diametros, phi_s),
        'c inicial (kPa)': np.full_like(diametros, c_s),
        'E inicial (kPa)': np.full_like(diametros, E_s),
        'f final (º)': f_final,
        'c final (kPa)': c_final,
        'E final (kPa)': E_final
    })
    
    return df_geo, df_int1, df_int2, df_params
