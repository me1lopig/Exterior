import math
from typing import Optional, Dict, Any

class Terreno:
    """Propiedades geotécnicas del terreno según CTE-DB-SE-C."""
    def __init__(self, c_0: float, m: float, phi_k: float, gamma_ap: float, 
                 gamma_sat: float, z_w: float, es_drenado: bool, i_v: float = 0.0,
                 ignorar_coef_profundidad: bool = False):
        self.c_0 = c_0
        self.m = m
        self.phi_k = math.radians(phi_k)
        self.gamma_ap = gamma_ap
        self.gamma_sat = gamma_sat
        self.gamma_w = 9.81
        self.gamma_sub = gamma_sat - self.gamma_w
        self.z_w = z_w
        self.es_drenado = es_drenado
        self.i_v = i_v
        self.ignorar_coef_profundidad = ignorar_coef_profundidad

    def obtener_cohesion(self, B: float) -> float:
        """Cálculo de cohesión sin drenaje limitada a 2*c_0."""
        if not self.es_drenado and self.m > 0:
            c_u_calculo = self.c_0 + self.m * (B / 4.0)
            return min(c_u_calculo, 2.0 * self.c_0)
        return self.c_0

class Cargas:
    """Solicitaciones transmitidas a la base."""
    def __init__(self, V: float, H: float = 0.0, M_B: float = 0.0, M_L: float = 0.0):
        self.V = V
        self.H = H
        self.M_B = M_B
        self.M_L = M_L
        self.delta = math.atan(H / V) if V > 0 else 0.0

class Cimentacion:
    """Geometría y entorno de la cimentación."""
    def __init__(self, D: float, beta_grados: float, tipo: str, c_base: float = 0.0, q_ext: float = 0.0):
        self.D = D
        self.beta = math.radians(beta_grados)
        self.tipo = tipo
        self.c_base = c_base 
        self.q_ext = q_ext # Sobrecarga uniforme al nivel de apoyo

class CalculadoraCapacidad:
    """Motor analítico CTE-DB-SE-C."""
    def __init__(self, terreno: Terreno, cimentacion: Cimentacion, cargas: Cargas, gamma_R: float = 3.0):
        self.terreno = terreno
        self.cim = cimentacion
        self.cargas = cargas
        self.gamma_R = gamma_R

    def calcular(self, B_real: float, L_real: float = 1.0) -> Optional[Dict[str, Any]]:
        # Dimensiones Efectivas
        e_B = self.cargas.M_B / self.cargas.V if self.cargas.V > 0 else 0.0
        e_L = self.cargas.M_L / self.cargas.V if self.cargas.V > 0 else 0.0

        if self.cim.tipo == 'circular':
            e = math.sqrt(e_B**2 + e_L**2)
            R = B_real / 2.0
            if e >= R: return None  
            theta = 2.0 * math.acos(e / R)
            Area = 0.5 * (R**2) * (theta - math.sin(theta))
            B_ast, L_ast, ratio_BL = B_real - 2 * e, B_real, 1.0
        elif self.cim.tipo == 'rectangular':
            B_ast, L_ast = B_real - 2 * e_B, L_real - 2 * e_L
            if B_ast <= 0 or L_ast <= 0: return None
            if B_ast > L_ast: B_ast, L_ast = L_ast, B_ast  
            Area, ratio_BL = B_ast * L_ast, B_ast / L_ast
        else: # corrida
            B_ast, L_ast = B_real - 2 * e_B, 1.0  
            if B_ast <= 0: return None
            Area, ratio_BL = B_ast * 1.0, 0.0

        c_k = self.terreno.obtener_cohesion(B_real)
        phi = self.terreno.phi_k if self.terreno.es_drenado else 0.0
        D = self.cim.D
        z_w = self.terreno.z_w
        
        # Sobrecarga q0k = Tierras + Sobrecarga externa
        z = z_w - D
        if z_w <= D:
            q0k_tierras = z_w * self.terreno.gamma_ap + (D - z_w) * self.terreno.gamma_sub
        else:
            q0k_tierras = D * self.terreno.gamma_ap
            
        q0k = q0k_tierras + self.cim.q_ext

        # Peso específico de la cuña de rotura
        if self.terreno.i_v > 0:
            gamma_k = self.terreno.gamma_sub - (self.terreno.i_v * self.terreno.gamma_w)
        else:
            if z <= 0: gamma_k = self.terreno.gamma_sub
            elif z >= B_ast: gamma_k = self.terreno.gamma_ap
            else: gamma_k = self.terreno.gamma_sub + (z / B_ast) * (self.terreno.gamma_ap - self.terreno.gamma_sub)

        # Capacidad de Carga (Forzando 1.5 en N_gamma por criterio experto)
        if phi == 0.0:
            N_q, N_c, N_gamma = 1.0, 5.14, 0.0
        else:
            N_q = ((1 + math.sin(phi)) / (1 - math.sin(phi))) * math.exp(math.pi * math.tan(phi))
            N_c = (N_q - 1) / math.tan(phi)
            N_gamma = 1.5 * (N_q - 1) * math.tan(phi)

        # Forma
        if self.cim.tipo == 'circular': s_c, s_q, s_gamma = 1.20, 1.20, 0.60
        elif self.cim.tipo == 'corrida': s_c, s_q, s_gamma = 1.0, 1.0, 1.0
        else:
            s_c = 1 + 0.2 * ratio_BL
            s_q = 1 + 1.5 * math.tan(phi) * ratio_BL if phi > 0 else 1.0
            s_gamma = max(1 - 0.3 * ratio_BL, 0.6)

        # Profundidad
        if self.terreno.ignorar_coef_profundidad or D < 2.0:
            d_c, d_q, d_gamma = 1.0, 1.0, 1.0
        else:
            D_calc = min(D, 2 * B_ast)
            arc_val = math.atan(D_calc / B_ast)
            d_c = 1 + 0.34 * arc_val
            d_q = 1 + 2 * math.tan(phi) * (1 - math.sin(phi))**2 * arc_val if phi > 0 else 1.0
            d_gamma = 1.0

        # Inclinación
        if self.cargas.H < 0.10 * self.cargas.V:
            i_c, i_q, i_gamma = 1.0, 1.0, 1.0
        else:
            if self.cim.c_base > 0 and phi > 0:
                tan_delta_calc = math.tan(self.cargas.delta) / (1 + (Area * self.cim.c_base) / (self.cargas.V * math.tan(phi)))
                delta_calc = math.atan(tan_delta_calc)
            else:
                delta_calc = self.cargas.delta

            i_q = (1 - 0.7 * math.tan(delta_calc))**3
            i_gamma = (1 - math.tan(delta_calc))**3
            
            if phi > 0:
                i_c = i_q - (1 - i_q) / (N_c * math.tan(phi))
            else:
                rad = max(0, 1 - self.cargas.H / (Area * c_k)) if c_k * Area > 0 else 1.0
                i_c = 0.5 * (1 + math.sqrt(rad))

        # Talud
        beta = self.cim.beta
        if beta <= math.radians(5):
            t_c, t_q, t_gamma = 1.0, 1.0, 1.0
        else:
            t_c = math.exp(-2 * beta * math.tan(phi)) if phi > 0 else 1.0
            t_q = 1 - math.sin(2 * beta)
            t_gamma = 1 - math.sin(2 * beta)

        # Hundimiento
        term_c = c_k * N_c * s_c * d_c * i_c * t_c
        term_q = q0k * N_q * s_q * d_q * i_q * t_q
        term_g = 0.5 * gamma_k * B_ast * N_gamma * s_gamma * d_gamma * i_gamma * t_gamma

        q_h = term_c + term_q + term_g

        if phi == 0.0 and beta > 0:
            q_h = q_h - (2 * beta * c_k)

        # Coeficiente de seguridad
        if not self.terreno.es_drenado:
            q_adm = (term_c / self.gamma_R) + term_q + term_g
        else:
            q_adm = q_h / self.gamma_R
            
        presion_trabajo = self.cargas.V / Area if Area > 0 else 0.0
        L_disp = L_real if self.cim.tipo == 'rectangular' else (B_real if self.cim.tipo == 'circular' else 1.0)

        return {
            "B": B_real, "L": L_disp, "B*": B_ast, "Área Ef.": Area,
            "q_trabajo": presion_trabajo, "q_h": q_h, "q_adm": q_adm,
            "Cumple": bool(presion_trabajo <= q_adm),
            "Detalles": {
                "Nc": N_c, "Nq": N_q, "Ng": N_gamma,
                "sc": s_c, "sq": s_q, "sg": s_gamma,
                "dc": d_c, "dq": d_q, "dg": d_gamma,
                "ic": i_c, "iq": i_q, "ig": i_gamma,
                "tc": t_c, "tq": t_q, "tg": t_gamma,
                "q0k": q0k, "gamma_k": gamma_k, "c_calc": c_k
            }
        }
