"""Incrementos de tensión vertical en sección por Boussinesq.

Zapata finita: integración analítica sobre rectángulo uniformemente cargado.
Corrida ideal: solución de banda infinita en semiespacio homogéneo.
Las isobaras representan Delta sigma_z TOTAL debida a presión NETA;
no se calculan cambios de presión intersticial ni Delta sigma' en no drenado.
"""
from __future__ import annotations

import numpy as np

ISOBARAS = (0.05, 0.10, 0.20, 0.30, 0.50, 0.70)


def _primitiva_rectangulo(x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
    r = np.sqrt(x*x + y*y + z*z)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (np.arctan2(x*y, z*r)
                + (x*y*z/r) * (1/(x*x + z*z) + 1/(y*y + z*z))) / (2*np.pi)


def influencia_rectangular(x, z, b: float, l: float):
    """Delta sigma_z / q en y=0 para la zapata B x L; z desde su base (m).

    x=0 en el centro de B. Admite escalares o arrays compatibles por broadcasting.
    """
    if not (np.isfinite(b) and np.isfinite(l) and 0 < b <= l):
        raise ValueError("Se exige 0 < B <= L.")
    xx, zz = np.broadcast_arrays(np.asarray(x, dtype=float), np.asarray(z, dtype=float))
    if np.any(~np.isfinite(xx)) or np.any(~np.isfinite(zz)) or np.any(zz < 0):
        raise ValueError("Coordenadas no válidas; se exige z >= 0.")
    zp = np.maximum(zz, 1e-12)
    xp, xm = xx+b/2, xx-b/2
    yp, ym = l/2, -l/2
    a = (_primitiva_rectangulo(xp,yp,zp) - _primitiva_rectangulo(xm,yp,zp)
         - _primitiva_rectangulo(xp,ym,zp) + _primitiva_rectangulo(xm,ym,zp))
    # En z=0, el incremento coincide con q dentro del rectángulo.
    return np.where(zz == 0, np.where(np.abs(xx) < b/2, 1., 0.), np.clip(a, 0., 1.))


def influencia_corrida(x, z, b: float):
    """Delta sigma_z / q para una banda infinita de anchura B (carga uniforme)."""
    if not np.isfinite(b) or b <= 0:
        raise ValueError("B debe ser positivo.")
    xx, zz = np.broadcast_arrays(np.asarray(x, dtype=float), np.asarray(z, dtype=float))
    if np.any(~np.isfinite(xx)) or np.any(~np.isfinite(zz)) or np.any(zz < 0):
        raise ValueError("Coordenadas no válidas; se exige z >= 0.")
    zp = np.maximum(zz, 1e-12)
    xp, xm = xx+b/2, xx-b/2
    a = (np.arctan(xp/zp)-np.arctan(xm/zp)
         +zp*xp/(xp*xp+zp*zp)-zp*xm/(xm*xm+zp*zp)) / np.pi
    return np.where(zz == 0, np.where(np.abs(xx) < b/2, 1., 0.), np.clip(a, 0., 1.))


def malla_influencia(b: float, l: float | None = None, *,
                    corrida: bool = False, zmax_m: float | None = None,
                    nx: int = 181, nz: int = 241):
    """Devuelve (x, z, I) para isobaras 2D; z es profundidad BAJO la base.

    En corrida=True se ignora L por ser una banda infinita; no usar las
    longitudes artificiales 100 m/1000 m de la comparativa de cálculo.
    """
    if not np.isfinite(b) or b <= 0 or not corrida and (l is None or l < b):
        raise ValueError("Geometría B/L inválida.")
    if nx < 21 or nz < 21 or nx > 601 or nz > 801:
        raise ValueError("Resolución de malla fuera de límites.")
    profundidad = (14*b if corrida else max(6*b, 2*float(l))) if zmax_m is None else zmax_m
    if not np.isfinite(profundidad) or profundidad <= 0:
        raise ValueError("Profundidad del gráfico no válida.")
    alcance_x = max(3*b, profundidad*.6)
    x = np.linspace(-alcance_x, alcance_x, nx)
    z = np.linspace(max(1e-4, profundidad/(nz*20)), profundidad, nz)
    X, Z = np.meshgrid(x, z)
    factor = influencia_corrida(X,Z,b) if corrida else influencia_rectangular(X,Z,b,float(l))
    return x,z,factor
