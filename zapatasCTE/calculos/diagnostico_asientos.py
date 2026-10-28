"""Interpretacion elastica: Steinbrenner por estratos y tensiones Boussinesq.

El bulbo (incremento vertical) NO es el metodo de deformacion empleado
por Steinbrenner. Se representa como control de profundidad independiente.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import atan2, hypot, pi
import numpy as np

from calculos.asientos import _asiento_esquina_en_profundidad_m
from modelos.datos import DatosAsientos, DatosHundimiento

GAMMA_AGUA_KN_M3 = 9.81


def tension_inicial_kpa(profundidad_rasante_m: float, h: DatosHundimiento, *, efectiva: bool) -> float:
    """Tension vertical geostatica estimada con peso superior/aparente y gamma sumergido.

    gamma aparente se interpreta como gamma por encima del fre Atico.
    gamma sat = gamma sumergido + gamma agua en la parte saturada.
    """
    z = max(0.0, profundidad_rasante_m)
    arriba = min(z, h.nivel_freatico_m)
    abajo = max(0.0, z - h.nivel_freatico_m)
    gamma_abajo = h.gamma_efectivo_kn_m3 if efectiva else h.gamma_efectivo_kn_m3 + GAMMA_AGUA_KN_M3
    return h.gamma_aparente_kn_m3 * arriba + gamma_abajo * abajo


def descarga_preexistente_kpa(h: DatosHundimiento, s: DatosAsientos) -> float:
    """Presion geostatica TOTAL retirada en la excavacion o valor manual."""
    if s.descarga_excavacion_kpa is not None:
        return s.descarga_excavacion_kpa
    return tension_inicial_kpa(h.profundidad_base_m, h, efectiva=False)


def factor_boussinesq_centro(b: float, l: float, z: float) -> float:
    """Influencia de sigma_z bajo centro de rectangulo uniformemente cargado.

    Integral cerrada de Boussinesq/Fadum con superposicion de cuatro esquinas.
    Factor adimensional; para z=0+ la influencia es 1.
    """
    if not (b > 0 and l >= b and z >= 0):
        raise ValueError("Se exige 0 < B <= L y z >= 0.")
    if z == 0:
        return 1.0
    a, c = b / 2.0, l / 2.0
    r = hypot(hypot(a, c), z)
    u = atan2(a*c, z*r)
    v = (a*c*z/r) * (1.0/(a*a+z*z)+1.0/(c*c+z*z))
    return min(1.0, max(0.0, 2.0/pi*(u+v)))


def contribuciones_steinbrenner(b: float, l: float, datos: DatosAsientos, q_neta_mpa: float):
    """Desglose de asiento por capas y acumulado, sin integrar Delta sigma/E.

    Cada tramo es el salto del desplazamiento de esquina entre extremos.
    Metodo bajo centro: cuatro cuadrantes o aproximacion historica.
    """
    if not (0 < b <= l and q_neta_mpa >= 0):
        raise ValueError("Geometria o presion neta invalida.")
    if datos.metodo_centro == "superposicion":
        multiplicador, ancho, largo = 4.0, b/2.0, l/2.0
    elif datos.metodo_centro == "excel":
        multiplicador, ancho, largo = 2.0, b, l
    else:
        raise ValueError("Metodo de asientos desconocido.")
    rows = []
    acumulado_mm = 0.0
    for capa in datos.capas:
        arriba = _asiento_esquina_en_profundidad_m(q_neta_mpa, ancho, largo, capa.z_superior_m, capa)
        abajo = _asiento_esquina_en_profundidad_m(q_neta_mpa, ancho, largo, capa.z_inferior_m, capa)
        contrib_mm = multiplicador * (arriba - abajo) * 1000.0
        acumulado_mm += contrib_mm
        rows.append({
            "Unidad": capa.nombre, "z sup. (m)": capa.z_superior_m,
            "z inf. (m)": capa.z_inferior_m, "E (MPa)": capa.modulo_mpa,
            "nu": capa.poisson, "Asiento (mm)": contrib_mm,
            "Asiento acumulado (mm)": acumulado_mm,
        })
    total = acumulado_mm
    for row in rows:
        row["Contribucion (%)"] = row["Asiento (mm)"] / total * 100.0 if total > 0 else 0.0
    return rows


@dataclass(frozen=True)
class PerfilBulbo:
    z_m: np.ndarray
    delta_sigma_kpa: np.ndarray
    sigma_efectiva_inicial_kpa: np.ndarray
    umbral_cte_kpa: np.ndarray
    profundidad_influencia_m: float | None
    profundidad_modelo_m: float
    suficiente: bool
    avisos: tuple[str, ...]


def calcular_perfil_bulbo(b: float, l: float, q_neta_mpa: float,
                          h: DatosHundimiento, s: DatosAsientos,
                          paso_m: float = 0.1, profundidad_manual_m: float | None = None) -> PerfilBulbo:
    """Reproduce los criterios de tension del CTE 4.4.3 sobre el eje vertical.

    Si no se encuentra el cruce con el umbral dentro de la profundidad explorada,
    se extrapola exclusivamente la curva de tensiones para evaluar la alerta.
    No se inventan capas ni asiento por debajo del perfil aportado.
    """
    if not (b > 0 and l >= b and q_neta_mpa > 0 and paso_m > 0):
        raise ValueError("Parametros invalidos para bulbo de tensiones.")
    prof_perfil = max(c.z_inferior_m for c in s.capas)
    max_z = profundidad_manual_m if profundidad_manual_m is not None else max(prof_perfil*1.1, 20*b)
    if max_z <= 0:
        raise ValueError("La profundidad de representacion debe ser positiva.")
    n = min(1500, max(100, int(max_z / paso_m)+1))
    z = np.linspace(0, max_z, n)
    influencia = np.array([factor_boussinesq_centro(b,l,float(zz)) for zz in z])
    delta = q_neta_mpa*1000.0 * influencia
    inicial = np.array([tension_inicial_kpa(h.profundidad_base_m+float(zz),h,efectiva=True) for zz in z])
    umbral = np.minimum(0.1*q_neta_mpa*1000.0, 0.05*inicial)
    # El cruce se considera desde z>0, no sobre la cota de cimentacion.
    corte = None
    diferencia = delta - umbral
    for i in range(1,len(z)):
        if diferencia[i] <= 0 and diferencia[i-1] > 0:
            frac = diferencia[i-1] / (diferencia[i-1]-diferencia[i])
            corte = float(z[i-1] + frac*(z[i]-z[i-1]))
            break
    suficiente = corte is not None and prof_perfil >= corte
    avisos = []
    if corte is None:
        avisos.append("No se alcanza el criterio de tensiones en el intervalo representado: ampliar profundidad.")
    if corte is not None and prof_perfil < corte:
        avisos.append("El perfil de E y nu termina antes de la profundidad activa estimada por tensiones.")
    if any(row.z_inferior_m < 2*b for row in s.capas) and prof_perfil < 2*b:
        avisos.append("La profundidad disponible es inferior a 2B (solo criterio orientativo).")
    avisos.append("El bulbo se calcula para una zapata aislada y un semiespacio elastico homogeneo; no modela solape de zapatas.")
    return PerfilBulbo(z,delta,inicial,umbral,corte,prof_perfil,suficiente,tuple(avisos))


def profundidad_porcentaje_asiento(rows: list[dict], porcentaje: float) -> float | None:
    """Primer nivel donde la suma por estratos supera el porcentaje solicitado.

    Se informa en limites de estrato, NO se inventa distribucion continua interior.
    """
    if not rows or not (0 < porcentaje <= 100):
        return None
    total = rows[-1]["Asiento acumulado (mm)"]
    if total <= 0:
        return None
    for row in rows:
        if row["Asiento acumulado (mm)"] >= total*porcentaje/100.0-1e-10:
            return row["z inf. (m)"]
    return None
