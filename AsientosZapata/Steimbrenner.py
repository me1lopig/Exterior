import math
import matplotlib.pyplot as plt
import pandas as pd

def calcular_Is(m_prime, n_prime, nu):
    if n_prime == 0:
        return 0.0
    m2, n2 = m_prime**2, n_prime**2
    num_a0 = (1 + math.sqrt(m2 + 1)) * math.sqrt(m2 + n2)
    den_a0 = m_prime * (1 + math.sqrt(m2 + n2 + 1))
    A0 = m_prime * math.log(num_a0 / den_a0)
    num_a1 = (m_prime + math.sqrt(m2 + 1)) * math.sqrt(1 + n2)
    den_a1 = m_prime + math.sqrt(m2 + n2 + 1)
    A1 = math.log(num_a1 / den_a1)
    A2 = m_prime / (n_prime * math.sqrt(m2 + n2 + 1))
    F1 = (A0 + A1) / math.pi
    F2 = (n_prime / (2 * math.pi)) * math.atan(A2)
    return F1 + ((1 - 2 * nu) / (1 - nu)) * F2

def calcular_I_sigma(B_prime, L_prime, z):
    if z == 0: return 0.25
    m, n = B_prime / z, L_prime / z
    m2, n2 = m**2, n**2
    v1 = m2 + n2 + 1
    v2 = m2 + n2 + m2 * n2 + 1
    term1 = (2 * m * n * math.sqrt(v1)) / v2
    term2 = (v1 + 1) / v1
    term3 = math.atan2(2 * m * n * math.sqrt(v1), v1 - 2 * m2 * n2)
    return (1 / (4 * math.pi)) * (term1 * term2 + term3)

def calcular_factor_empotramiento(Df, B):
    """
    Calcula el factor reductor por profundidad de empotramiento (If).
    Criterio analítico de Burland / Bowles (límite inferior 0.60).
    """
    if Df <= 0:
        return 1.0
    factor = 1.0 - 0.4 * (Df / B)
    return max(0.60, factor)

def main():
    print("=" * 110)
    print(" CÁLCULO DE ASIENTOS, EMPOTRAMIENTO Y BALASTO (CON EXCEL Y GRÁFICO)")
    print("=" * 110 + "\n")
    
    # 1. Datos de la cimentación
    print("--- 1. DATOS DE LA CIMENTACIÓN ---")
    B = float(input("Ancho de la zapata, B (m): "))
    L = float(input("Largo de la zapata, L (m): "))
    Df = float(input("Profundidad de empotramiento de la zapata, Df (m): "))
    gamma_df = 0.0
    if Df > 0:
        gamma_df = float(input("Peso específico efectivo del terreno sobre el apoyo (0 a Df) (kN/m³): "))
        
    q_net = float(input("Presión neta transmitida, q (kPa): "))
    tipo_zapata = input("Comportamiento de la zapata (F: Flexible / R: Rígida): ").strip().upper()
    
    z_w = float(input("Profundidad del Nivel Freático medido desde el apoyo de la zapata (m) [100 si no hay]: "))
    num_capas = int(input("\nNúmero de estratos bajo el apoyo a definir: "))
    
    B_prime, L_prime = B / 2, L / 2
    m_prime = L_prime / B_prime
    GAMMA_W = 9.81 
    
    # Cálculo del factor de corrección por empotramiento
    factor_If = calcular_factor_empotramiento(Df, B)
    
    # 2. Datos del terreno (bajo la cota de apoyo)
    estratos = []
    z_acumulada = 0.0
    # La tensión efectiva inicial en z=0 (plano de apoyo) incluye las tierras del empotramiento Df
    sigma_v0_acumulada = Df * gamma_df
    
    for i in range(num_capas):
        print(f"\n> Estrato {i+1} (bajo la zapata):")
        espesor = float(input("  Espesor de la capa (m): "))
        E = float(input("  Módulo de elasticidad, E (kPa): "))
        nu = float(input("  Coeficiente de Poisson, nu (0-0.5): "))
        gamma_nat = float(input("  Peso específico natural/aparente (kN/m³): "))
        gamma_sat = float(input("  Peso específico saturado (kN/m³): "))
        
        z_techo = z_acumulada
        z_base = z_acumulada + espesor
        
        if z_base <= z_w:
            delta_sv0 = gamma_nat * espesor
        elif z_techo >= z_w:
            delta_sv0 = (gamma_sat - GAMMA_W) * espesor
        else:
            espesor_seco = z_w - z_techo
            espesor_sumergido = z_base - z_w
            delta_sv0 = (gamma_nat * espesor_seco) + ((gamma_sat - GAMMA_W) * espesor_sumergido)
            
        sigma_v0_base = sigma_v0_acumulada + delta_sv0
        
        estratos.append({
            'id': i+1, 'espesor': espesor, 'E': E, 'nu': nu,
            'gamma_nat': gamma_nat, 'gamma_sat': gamma_sat,
            'z_techo': z_techo, 'z_base': z_base,
            'sv0_techo': sigma_v0_acumulada,
            'sv0_base': sigma_v0_base
        })
        
        z_acumulada = z_base
        sigma_v0_acumulada = sigma_v0_base

    # 3. Procesamiento y cálculo
    print("\n" + "=" * 110)
    col_sigma = "10% σ'_v0"
    print(f"{'Capa':<5} | {'Z bajo zap.(m)':<14} | {'Δσ_z (kPa)':<12} | {col_sigma:<12} | {'Estado':<16} | {'Asiento s/emp (mm)':<18}")
    print("-" * 110)
    
    asiento_total_superficial = 0.0
    
    z_plot = [0.0]
    dsz_plot = [q_net]
    lim_plot = [0.10 * (Df * gamma_df)]
    s_acum_plot = [0.0]
    datos_excel = []
    
    for capa in estratos:
        n_techo, n_base = capa['z_techo'] / B_prime, capa['z_base'] / B_prime
        Is_techo = calcular_Is(m_prime, n_techo, capa['nu'])
        Is_base = calcular_Is(m_prime, n_base, capa['nu'])
        delta_Is = Is_base - Is_techo
        factor_rigidez = (1 - capa['nu']**2) / capa['E']
        
        s_centro_mm = (q_net * B_prime * factor_rigidez * delta_Is) * 4 * 1000
        
        I_sigma = calcular_I_sigma(B_prime, L_prime, capa['z_base'])
        delta_sigma_z = q_net * 4 * I_sigma
        limite_10_porciento = 0.10 * capa['sv0_base']
        
        rango_z = f"{capa['z_techo']:.1f}-{capa['z_base']:.1f}"
        
        if delta_sigma_z > limite_10_porciento:
            estado = "Activo"
            asiento_total_superficial += s_centro_mm
            print(f"{capa['id']:<5} | {rango_z:<14} | {delta_sigma_z:<12.2f} | {limite_10_porciento:<12.2f} | {estado:<16} | {s_centro_mm:<18.2f}")
        else:
            estado = "Corte (Bulbo)"
            asiento_total_superficial += s_centro_mm
            print(f"{capa['id']:<5} | {rango_z:<14} | {delta_sigma_z:<12.2f} | {limite_10_porciento:<12.2f} | {estado:<16} | {s_centro_mm:<18.2f}")
            print("-" * 110)
            print(f">>> Criterio de corte alcanzado en la base de esta capa.")
            
        datos_excel.append({
            'Capa N°': capa['id'],
            'Prof. Techo bajo zapata (m)': capa['z_techo'],
            'Prof. Base bajo zapata (m)': capa['z_base'],
            'Espesor (m)': capa['espesor'],
            'Módulo E (kPa)': capa['E'],
            'Poisson (nu)': capa['nu'],
            'Δσ_z Base (kPa)': round(delta_sigma_z, 2),
            "10% σ'_v0 (kPa)": round(limite_10_porciento, 2),
            'Estado Bulbo': estado,
            'Asiento Base s/emp (mm)': round(s_centro_mm, 2),
            'Asiento Acum. s/emp (mm)': round(asiento_total_superficial, 2),
            'Asiento Acum. Empotrado (mm)': round(asiento_total_superficial * factor_If, 2)
        })

        z_plot.append(capa['z_base'])
        dsz_plot.append(delta_sigma_z)
        lim_plot.append(limite_10_porciento)
        s_acum_plot.append(asiento_total_superficial)
        
        if delta_sigma_z <= limite_10_porciento:
            break 
            
    print("-" * 110)
    
    # 4. Aplicación de factores correctores (Empotramiento y Rigidez)
    asiento_empotrado_flex = asiento_total_superficial * factor_If
    
    print(f"1. ASIENTO TEÓRICO SUPERFICIAL (Flexible, Df=0):     {asiento_total_superficial:.2f} mm")
    print(f"2. FACTOR DE CORRECCIÓN POR EMPOTRAMIENTO (If):      {factor_If:.3f} (para Df={Df}m, B={B}m)")
    print(f"3. ASIENTO CORREGIDO POR EMPOTRAMIENTO (Flexible):   {asiento_empotrado_flex:.2f} mm")
    
    asiento_diseno = asiento_empotrado_flex
    if tipo_zapata == 'R':
        asiento_diseno = asiento_empotrado_flex * 0.80
        print(f"4. ASIENTO FINAL DE DISEÑO (Zapata Rígida, x0.80):   {asiento_diseno:.2f} mm")
    else:
        print(f"4. ASIENTO FINAL DE DISEÑO (Zapata Flexible):        {asiento_diseno:.2f} mm")

    # --- CÁLCULO DEL MÓDULO DE BALASTO (Ks) ---
    if asiento_diseno > 0:
        asiento_diseno_m = asiento_diseno / 1000.0
        ks_kn_m3 = q_net / asiento_diseno_m
        ks_mn_m3 = ks_kn_m3 / 1000.0
        
        print("-" * 110)
        print(f"MÓDULO DE BALASTO EQUIVALENTE (Ks): {ks_kn_m3:.2f} kN/m³  ({ks_mn_m3:.2f} MN/m³)")
        
        datos_excel.append({
            'Capa N°': 'RESUMEN DISEÑO',
            'Estado Bulbo': f"{'Rígida' if tipo_zapata == 'R' else 'Flexible'} (If={factor_If:.2f})",
            'Asiento Acum. Empotrado (mm)': round(asiento_diseno, 2),
            'Ks (kN/m³)': round(ks_kn_m3, 2)
        })
        
    print("=" * 110)
    
    # 5. Exportación a Excel
    try:
        df = pd.DataFrame(datos_excel)
        nombre_archivo = "Resultados_Steinbrenner.xlsx"
        df.to_excel(nombre_archivo, index=False)
        print(f"\n[+] Datos exportados exitosamente a: {nombre_archivo}")
    except Exception as e:
        print(f"\n[-] Error al exportar a Excel: {e}")

    # 6. Generación del gráfico con Matplotlib
    print("\nGenerando gráfico... (Cierra la ventana del gráfico para finalizar el programa)")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6), sharey=True)
    
    # Subgráfico 1: Tensiones
    ax1.plot(dsz_plot, z_plot, 'b-o', linewidth=2, label='Δσ_z (Tensión Inducida)')
    ax1.plot(lim_plot, z_plot, 'r--', linewidth=2, label="10% σ'_v0 (Con sobrecarga Df)")
    ax1.fill_betweenx(z_plot, dsz_plot, lim_plot, where=[d > l for d, l in zip(dsz_plot, lim_plot)], color='blue', alpha=0.1)
    
    ax1.set_ylim(max(z_plot) + 0.5, 0)
    ax1.set_xlim(left=0)
    ax1.set_xlabel('Tensión Vertical (kPa)', fontsize=11)
    ax1.set_ylabel('Profundidad bajo el plano de apoyo (m)', fontsize=11)
    ax1.set_title('Bulbo de Tensiones', fontsize=13, fontweight='bold')
    ax1.legend()
    ax1.grid(True, linestyle=':', alpha=0.7)
    
    # Subgráfico 2: Asientos comparados
    ax2.plot(s_acum_plot, z_plot, 'k:o', linewidth=1.5, label='Superficial s/emp (Flexible)')
    
    s_acum_emp = [s * factor_If for s in s_acum_plot]
    ax2.plot(s_acum_emp, z_plot, 'g-s', linewidth=2, label=f'Con Empotramiento (If={factor_If:.2f})')
    
    if tipo_zapata == 'R':
        s_acum_rig = [s * 0.80 for s in s_acum_emp]
        ax2.plot(s_acum_rig, z_plot, 'm--^', linewidth=2, label='Diseño Final (Empotrada + Rígida)')
        
    ax2.set_xlim(left=0)
    ax2.set_xlabel('Asiento Acumulado (mm)', fontsize=11)
    ax2.set_title('Evolución del Asiento en Profundidad', fontsize=13, fontweight='bold')
    ax2.legend()
    ax2.grid(True, linestyle=':', alpha=0.7)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()