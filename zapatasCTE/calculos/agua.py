"""Constantes del agua y conversión de pesos específicos del terreno.

Unidades: kN/m³. gamma_sat es peso específico saturado TOTAL.
gamma' es peso específico sumergido, no aparente.
"""
from __future__ import annotations

from math import isfinite

GAMMA_AGUA_KN_M3 = 9.81


def gamma_sumergido_desde_saturado(gamma_sat_kn_m3: float) -> float:
    """Calcula gamma' = gamma_sat - gamma_agua con validación física."""
    if not isfinite(gamma_sat_kn_m3) or gamma_sat_kn_m3 <= GAMMA_AGUA_KN_M3:
        raise ValueError("El peso específico saturado debe superar al del agua (9,81 kN/m³).")
    return gamma_sat_kn_m3 - GAMMA_AGUA_KN_M3
