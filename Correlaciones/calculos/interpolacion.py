"""Interpolacion numerica con bloqueo explicito de extrapolaciones."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from calculos.errores import ErrorCalculoGeotecnico, FueraDeDominio


def interpolar_lineal(
    x: float,
    puntos_x: Sequence[float],
    puntos_y: Sequence[float],
) -> float:
    """Interpola por tramos sin admitir extrapolacion."""
    if len(puntos_x) != len(puntos_y) or len(puntos_x) < 2:
        raise ErrorCalculoGeotecnico("La tabla de interpolacion no es valida.")
    if any(b <= a for a, b in zip(puntos_x, puntos_x[1:], strict=False)):
        raise ErrorCalculoGeotecnico("Los puntos de entrada deben ser crecientes.")
    if not np.isfinite(x):
        raise ErrorCalculoGeotecnico("El valor de entrada debe ser finito.")
    if x < puntos_x[0] or x > puntos_x[-1]:
        raise FueraDeDominio(
            f"{x:g} queda fuera del intervalo [{puntos_x[0]:g}, {puntos_x[-1]:g}]."
        )
    return float(np.interp(x, puntos_x, puntos_y))


def fraccion_intervalo(x: float, x0: float, x1: float) -> float:
    """Devuelve la posicion relativa de x dentro de un intervalo cerrado."""
    if x1 <= x0:
        raise ErrorCalculoGeotecnico("El intervalo debe tener amplitud positiva.")
    if x < x0 or x > x1:
        raise FueraDeDominio(f"{x:g} queda fuera del intervalo [{x0:g}, {x1:g}].")
    return (x - x0) / (x1 - x0)

