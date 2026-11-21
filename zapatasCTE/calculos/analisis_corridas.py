"""Estudios exploratorios de corridas y sensibilidad del nivel freático.

No reemplazan los resultados oficiales del motor ni constituyen por sí mismos
una validación normativa del límite de deformación plana.
"""
from __future__ import annotations

from dataclasses import replace
from math import isclose, isfinite

import numpy as np
import pandas as pd

from calculos.capacidad_portante import (
    calcular_hundimiento_rectangular, _peso_especifico_representativo,
)
from calculos.diagnostico_asientos import descarga_preexistente_kpa
from calculos.malla import calcular_corridas, calcular_geometria
from modelos.datos import DatosAsientos, DatosHundimiento

FACTORES_L_B = (2, 5, 10, 20, 50, 100, 200, 500)


def convergencia_corrida(b: float, h: DatosHundimiento, s: DatosAsientos) -> pd.DataFrame:
    """Compara zapatas físicas BxL con L/B creciente, sin usar L infinito."""
    if not isfinite(b) or b <= 0:
        raise ValueError("El ancho B debe ser positivo.")
    filas = []
    anterior = None
    for ratio in FACTORES_L_B:
        r = calcular_geometria(b, b * ratio, h, s)
        diferencia = (
            abs(r.q_asiento_neta_mpa - anterior) / abs(anterior) * 100
            if anterior is not None and anterior > 0 else float("nan")
        )
        filas.append({
            "L/B": ratio, "B (m)": b, "L (m)": b * ratio,
            "q hund. neta (MPa)": r.q_hund_neta_mpa,
            "q asientos neta (MPa)": r.q_asiento_neta_mpa,
            "q servicio neta (MPa)": r.q_serv_neta_mpa,
            "Variación asientos respecto L anterior (%)": diferencia,
        })
        anterior = r.q_asiento_neta_mpa
    return pd.DataFrame(filas)


def hundimiento_corrida_limite(b: float, h: DatosHundimiento) -> float:
    """Límite B/L->0 *de la fórmula implementada*, solo hundimiento bruto.

    La expresión del motor es afín en B/L: extrapolación exacta a orden
    máquina entre relaciones 100 y 200. No se extrapola asiento a L infinito.
    """
    if not isfinite(b) or b <= 0:
        raise ValueError("El ancho B debe ser positivo.")
    h100 = calcular_hundimiento_rectangular(h, b, 100 * b).q_h_d_mpa
    h200 = calcular_hundimiento_rectangular(h, b, 200 * b).q_h_d_mpa
    return 2 * h200 - h100


def comparativa_corridas(b: float, h: DatosHundimiento, s: DatosAsientos) -> pd.DataFrame:
    """Tres casos etiquetados explícitamente, sin suplantar un ELS Bx∞."""
    historial = calcular_corridas((b,), h, s)
    if not historial:
        raise ValueError("El ancho supera la longitud interna de asientos (100 m).")
    hist = historial[0]
    finito = calcular_geometria(b, 200 * b, h, s)
    qinf_bruta = hundimiento_corrida_limite(b, h)
    qinf_neta = qinf_bruta - descarga_preexistente_kpa(h, s) / 1000
    return pd.DataFrame([
        {"Hipótesis": "Histórica (L distintas)", "L hund. (m)": 1000.,
         "L asientos (m)": 100., "q hund. neta (MPa)": hist.q_hund_neta_mpa,
         "q asientos neta (MPa)": hist.q_asiento_neta_mpa,
         "q servicio neta (MPa)": hist.q_serv_neta_mpa},
        {"Hipótesis": "Rectangular finita (L/B=200)", "L hund. (m)": 200*b,
         "L asientos (m)": 200*b, "q hund. neta (MPa)": finito.q_hund_neta_mpa,
         "q asientos neta (MPa)": finito.q_asiento_neta_mpa,
         "q servicio neta (MPa)": finito.q_serv_neta_mpa},
        {"Hipótesis": "Límite B/L=0 (solo hundimiento)", "L hund. (m)": float("nan"),
         "L asientos (m)": float("nan"), "q hund. neta (MPa)": qinf_neta,
         "q asientos neta (MPa)": float("nan"),
         "q servicio neta (MPa)": float("nan")},
    ])


def sensibilidad_nivel_freatico(
    b: float, l: float, h: DatosHundimiento, s: DatosAsientos,
    nf_min_m: float, nf_max_m: float, puntos: int = 21
) -> pd.DataFrame:
    """Variación paramétrica de gamma_k y hundimiento, manteniendo resto fijo.

    No se atribuye variación de E, nu, asientos, ni presiones intersticiales
    adicionales. Con flujo ascendente gamma_k puede ser independiente del NF.
    """
    if not (0 < b <= l and isfinite(nf_min_m) and
            isfinite(nf_max_m) and 0 <= nf_min_m < nf_max_m
            and 2 <= puntos <= 201):
        raise ValueError("Rango de NF, número de puntos o geometría no válidos.")
    filas = []
    for nf in np.linspace(nf_min_m, nf_max_m, puntos):
        hi = replace(h, nivel_freatico_m=float(nf))
        gross = calcular_hundimiento_rectangular(hi, b, l).q_h_d_mpa
        descarga = descarga_preexistente_kpa(hi, s) / 1000
        filas.append({
            "NF bajo rasante (m)": float(nf),
            "gamma_k (kN/m³)": _peso_especifico_representativo(hi, b),
            "q hund. bruta (MPa)": gross,
            "q hund. neta (MPa)": gross - descarga,
        })
    return pd.DataFrame(filas)


def convergencia_porcentaje_final(tabla: pd.DataFrame) -> float:
    """Diferencia relativa entre las dos últimas aproximaciones FINITAS."""
    if len(tabla) < 2:
        raise ValueError("Faltan longitudes para comparar.")
    a,b = tabla["q asientos neta (MPa)"].iloc[-2:]
    if not (isfinite(a) and isfinite(b) and a > 0):
        raise ValueError("Presiones por asiento inválidas.")
    return abs(b-a)/a*100
