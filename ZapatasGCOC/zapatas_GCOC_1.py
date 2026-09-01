import math
from dataclasses import dataclass

@dataclass
class ResultadosHundimiento:
    cumple_normativa: bool
    p_vh: float
    p_v_adm: float
    F_real: float
    p_v_actuante: float
    delta_deg: float
    area_efectiva: float

def comprobacion_hundimiento(
    V: float, H: float, c: float, phi_deg: float, 
    gamma_ap: float, gamma_sat: float, D_w: float, D: float, 
    B_star: float, L_star: float = 1.0, psi_deg: float = 0.0, 
    eta_deg: float = 0.0, F_h_exigido: float = 3.0,
    gamma_w: float = 9.81, tipo_cimentacion: str = "Rectangular"
) -> ResultadosHundimiento:
    """
    Comprobación analítica de la carga de hundimiento (Brinch-Hansen modificado).
    Admite zapatas Rectangulares, Corridas y Circulares.
    """
    
    # 1. ADAPTACIÓN GEOMÉTRICA Y ÁREA EFECTIVA
    if tipo_cimentacion == "Corrida":
        ratio_forma = 0.0
        area_efectiva = B_star * 1.0  # Cálculo por metro lineal
    elif tipo_cimentacion == "Circular":
        ratio_forma = 1.0
        # Simplificación de área efectiva para círculo excéntrico
        area_efectiva = math.pi * (B_star**2) / 4.0 
    else: # Rectangular
        ratio_forma = B_star / L_star if L_star > 0 else 1.0
        area_efectiva = B_star * L_star

    p_v = V / area_efectiva if area_efectiva > 0 else 0.0
    delta = math.atan(H / V) if V > 0 else 0.0

    # 2. EVALUACIÓN DEL EFECTO DEL NIVEL FREÁTICO
    gamma_prima = gamma_sat - gamma_w  
    
    if D_w >= D:
        D1, D2, h_w = D, 0, D_w - D
    else:
        D1, D2, h_w = max(0, D_w), D - max(0, D_w), 0
        
    q = (gamma_ap * D1) + (gamma_prima * D2)
    
    if h_w == 0:
        gamma_calc = gamma_prima
    else:
        gamma_calc = gamma_prima + 0.6 * (gamma_ap - gamma_prima) * (h_w / B_star)
        gamma_calc = min(gamma_calc, gamma_ap)  

    # 3. CONVERSIÓN DE ÁNGULOS Y DETECCIÓN DE CORTO PLAZO
    phi = math.radians(phi_deg)
    psi = math.radians(psi_deg)
    eta = math.radians(eta_deg)
    es_corto_plazo = phi_deg < 0.1  

    # 4. FACTORES DE CAPACIDAD DE CARGA Y CORRECCIÓN
    if es_corto_plazo:
        Nq, Nc, Ngamma = 1.0, math.pi + 2, 0.0
    else:
        Nq = ((1 + math.sin(phi)) / (1 - math.sin(phi))) * math.exp(math.pi * math.tan(phi))
        Nc = (Nq - 1) / math.tan(phi)
        Ngamma = 2 * (Nq - 1) * math.tan(phi)

    D_cal = min(D, 2 * B_star)
    
    if es_corto_plazo:
        dq = 1.0
        dc = 1 + 2 * (1 / Nc) * math.atan(D_cal / B_star)
        dgamma = 1.0
        
        iq = 1.0
        radicando = 1 - (H / (area_efectiva * max(c, 0.001)))
        ic = 0.5 * (1 + math.sqrt(max(0, radicando)))
        igamma = 0.0
        
        tq = (1 - 0.5 * math.tan(psi))**5
        tc = 1 - 0.4 * psi
        tgamma = 0.0
        
        rq = 1.0
        rc = 1 - 0.4 * eta
        rgamma = 0.0
    else:
        dq = 1 + 2 * math.tan(phi) * (1 - math.sin(phi))**2 * math.atan(D_cal / B_star)
        dc = 1 + 2 * (Nq / Nc) * (1 - math.sin(phi))**2 * math.atan(D_cal / B_star)
        dgamma = 1.0
        
        iq = (1 - 0.7 * math.tan(delta))**3
        ic = iq - (1 - iq) / (Nc * math.tan(phi)) if phi > 0 else 1.0
        igamma = (1 - math.tan(delta))**3
        
        tq = (1 - 0.5 * math.tan(psi))**5
        tc = tq - (1 - tq) / (Nc * math.tan(phi)) if phi > 0 else 1.0
        tgamma = tq
        
        rq = math.exp(-2 * eta * math.tan(phi))
        rc = rq - (1 - rq) / (Nc * math.tan(phi)) if phi > 0 else 1.0
        rgamma = rq

    # FACTORES DE FORMA ADAPTADOS AL TIPO DE ZAPATA
    if es_corto_plazo:
        sq = 1.0
        sc = 1 + 0.2 * ratio_forma
        sgamma = 1.0
    else:
        sq = 1 + ratio_forma * math.tan(phi)
        sc = 1 + 0.2 * ratio_forma
        sgamma = 0.6 if tipo_cimentacion == "Circular" else (1 - 0.3 * ratio_forma)

    # 5. CÁLCULO DE HUNDIMIENTO Y COEFICIENTE DE SEGURIDAD
    termino_q = q * Nq * dq * iq * sq * tq * rq
    termino_c = c * Nc * dc * ic * sc * tc * rc
    termino_gamma = 0.5 * gamma_calc * B_star * Ngamma * dgamma * igamma * sgamma * tgamma * rgamma

    p_vh = termino_q + termino_c + termino_gamma
    p_v_adm = p_vh / F_h_exigido  
    
    F_real = p_vh / p_v if p_v > 0 else float('inf')
    cumple = F_real >= F_h_exigido

    return ResultadosHundimiento(
        cumple_normativa=cumple,
        p_vh=p_vh,
        p_v_adm=p_v_adm,
        F_real=F_real,
        p_v_actuante=p_v,
        delta_deg=math.degrees(delta),
        area_efectiva=area_efectiva
    )