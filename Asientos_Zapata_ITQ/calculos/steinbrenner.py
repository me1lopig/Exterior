from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from calculos.asientos import PUNTOS_CONTROL
from modelos.datos import Cimentacion


@dataclass(frozen=True)
class ResultadoSteinbrenner:
    """Resultados independientes del método elástico de Steinbrenner."""

    resumen_puntos: pd.DataFrame
    resumen_estratos: pd.DataFrame
    aportes: pd.DataFrame
    perfiles: pd.DataFrame


def factores_influencia(m: float, n: float) -> tuple[float, float]:
    """Calcula los factores I1 e I2 de Steinbrenner.

    Parameters
    ----------
    m:
        Relación L'/B', con L' >= B'.
    n:
        Relación H/B', donde H es el espesor deformable acumulado.
    """
    if not np.isfinite(m) or not np.isfinite(n) or m < 1.0 or n < 0.0:
        raise ValueError("Se requiere m >= 1 y n >= 0 finitos.")
    if n == 0.0:
        return 0.0, 0.0

    raiz_m = np.sqrt(m * m + 1.0)
    raiz_mn = np.sqrt(m * m + n * n)
    raiz_total = np.sqrt(m * m + n * n + 1.0)
    argumento_1 = ((1.0 + raiz_m) * raiz_mn) / (m * (1.0 + raiz_total))
    argumento_2 = ((m + raiz_m) * np.sqrt(1.0 + n * n)) / (m + raiz_total)
    if argumento_1 <= 0.0 or argumento_2 <= 0.0:
        raise FloatingPointError("Argumento logarítmico no positivo en Steinbrenner.")
    i1 = (m * np.log(argumento_1) + np.log(argumento_2)) / np.pi
    i2 = n * np.arctan2(m, n * raiz_total) / (2.0 * np.pi)
    return float(i1), float(i2)


def compresion_esquina_m(
    lado_a_m: float,
    lado_b_m: float,
    espesor_m: float,
    q_kpa: float,
    e_mpa: float,
    nu: float,
) -> float:
    """Compresión acumulada hasta H bajo la esquina de un rectángulo."""
    if lado_a_m <= 0.0 or lado_b_m <= 0.0 or espesor_m <= 0.0 or q_kpa == 0.0:
        return 0.0
    if q_kpa < 0.0 or e_mpa <= 0.0 or not 0.0 <= nu < 0.5:
        raise ValueError("q y E deben ser positivos y se requiere 0 <= nu < 0.5.")
    b_corta = min(lado_a_m, lado_b_m)
    l_larga = max(lado_a_m, lado_b_m)
    i1, i2 = factores_influencia(l_larga / b_corta, espesor_m / b_corta)
    factor_nu = (1.0 - 2.0 * nu) / (1.0 - nu)
    e_kpa = e_mpa * 1000.0
    return q_kpa * b_corta * (1.0 - nu * nu) * (i1 + factor_nu * i2) / e_kpa


def _primitiva_rectangular_m(
    a_m: float,
    b_m: float,
    espesor_m: float,
    q_kpa: float,
    e_mpa: float,
    nu: float,
) -> float:
    if a_m == 0.0 or b_m == 0.0:
        return 0.0
    signo = 1.0 if a_m * b_m > 0.0 else -1.0
    return signo * compresion_esquina_m(
        abs(a_m), abs(b_m), espesor_m, q_kpa, e_mpa, nu
    )


def compresion_rectangulo_m(
    x_m: float,
    y_m: float,
    espesor_m: float,
    b_m: float,
    l_m: float,
    q_kpa: float,
    e_mpa: float,
    nu: float,
) -> float:
    """Compresión acumulada en un punto mediante superposición de esquinas."""
    if espesor_m <= 0.0:
        return 0.0
    x1 = -b_m / 2.0 - x_m
    x2 = b_m / 2.0 - x_m
    y1 = -l_m / 2.0 - y_m
    y2 = l_m / 2.0 - y_m
    return (
        _primitiva_rectangular_m(x2, y2, espesor_m, q_kpa, e_mpa, nu)
        - _primitiva_rectangular_m(x1, y2, espesor_m, q_kpa, e_mpa, nu)
        - _primitiva_rectangular_m(x2, y1, espesor_m, q_kpa, e_mpa, nu)
        + _primitiva_rectangular_m(x1, y1, espesor_m, q_kpa, e_mpa, nu)
    )


def _capas_bajo_base(
    estratos: pd.DataFrame,
    df_m: float,
    z_max_m: float,
) -> list[dict[str, float | str]]:
    capas: list[dict[str, float | str]] = []
    limite_inferior = df_m + z_max_m
    for _, capa in estratos.iterrows():
        sup_terreno = max(float(capa["z_sup_m"]), df_m)
        inf_terreno = min(float(capa["z_inf_m"]), limite_inferior)
        if inf_terreno <= sup_terreno:
            continue
        capas.append(
            {
                "Estrato": str(capa["Estrato"]),
                "z_sup_bajo_base_m": sup_terreno - df_m,
                "z_inf_bajo_base_m": inf_terreno - df_m,
                "E_MPa": float(capa["E_MPa"]),
                "nu": float(capa["nu"]),
            }
        )
    return capas


def calcular_steinbrenner(
    cimentacion: Cimentacion,
    estratos: pd.DataFrame,
    z_max_m: float,
) -> ResultadoSteinbrenner:
    """Calcula asientos elásticos por Steinbrenner en todos los puntos de control."""
    if z_max_m <= 0.0:
        raise ValueError("La profundidad analizada debe ser positiva.")
    capas = _capas_bajo_base(estratos, cimentacion.df_m, z_max_m)
    if not capas:
        raise ValueError("No existen estratos bajo la base dentro del dominio analizado.")

    aportes: list[dict[str, float | str]] = []
    perfiles: list[dict[str, float | str]] = []
    resumen: list[dict[str, float | str]] = []
    for nombre, (rx, ry) in PUNTOS_CONTROL.items():
        x_m = rx * cimentacion.b_m
        y_m = ry * cimentacion.l_m
        contribuciones: list[float] = []
        for capa in capas:
            sup = float(capa["z_sup_bajo_base_m"])
            inf = float(capa["z_inf_bajo_base_m"])
            acumulada_sup = compresion_rectangulo_m(x_m, y_m, sup, cimentacion.b_m, cimentacion.l_m, cimentacion.q_neta_kpa, float(capa["E_MPa"]), float(capa["nu"]))
            acumulada_inf = compresion_rectangulo_m(x_m, y_m, inf, cimentacion.b_m, cimentacion.l_m, cimentacion.q_neta_kpa, float(capa["E_MPa"]), float(capa["nu"]))
            aporte_mm = (acumulada_inf - acumulada_sup) * 1000.0
            contribuciones.append(aporte_mm)
            aportes.append(
                {
                    "Punto": nombre,
                    "Estrato": capa["Estrato"],
                    "z_sup_bajo_base_m": sup,
                    "z_inf_bajo_base_m": inf,
                    "E_MPa": capa["E_MPa"],
                    "nu": capa["nu"],
                    "asiento_mm": aporte_mm,
                }
            )

        total_mm = float(np.sum(contribuciones))
        resumen.append(
            {
                "Punto": nombre,
                "x_m": x_m,
                "y_m": y_m,
                "asiento_base_mm": total_mm,
            }
        )
        desplazamiento = total_mm
        perfiles.append(
            {
                "Punto": nombre,
                "z_bajo_base_m": 0.0,
                "desplazamiento_mm": desplazamiento,
            }
        )
        for capa, aporte_mm in zip(capas, contribuciones):
            desplazamiento -= aporte_mm
            perfiles.append(
                {
                    "Punto": nombre,
                    "z_bajo_base_m": capa["z_inf_bajo_base_m"],
                    "desplazamiento_mm": desplazamiento,
                }
            )

    tabla_aportes = pd.DataFrame(aportes)
    resumen_estratos = (
        tabla_aportes[tabla_aportes["Punto"] == "Centro"]
        .drop(columns="Punto")
        .reset_index(drop=True)
    )
    return ResultadoSteinbrenner(
        resumen_puntos=pd.DataFrame(resumen),
        resumen_estratos=resumen_estratos,
        aportes=tabla_aportes,
        perfiles=pd.DataFrame(perfiles),
    )
