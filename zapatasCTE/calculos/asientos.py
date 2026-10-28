"""Asiento elástico estratificado por la formulación de Steinbrenner."""

from __future__ import annotations

from math import asinh, atan2, hypot, pi, sqrt

import numpy as np

from modelos.datos import CapaSuelo, DatosAsientos


def _asiento_esquina_en_profundidad_m(
    presion_mpa: float,
    ancho_m: float,
    largo_m: float,
    profundidad_m: float,
    capa: CapaSuelo,
) -> float:
    """Desplazamiento en una esquina a una profundidad, en metros."""
    m = profundidad_m / ancho_m
    n = largo_m / ancho_m
    tau = hypot(hypot(1.0, n), m)
    # Formas equivalentes numericamente estables de los logaritmos del
    # factor F1 (evitan cancelacion tau-n y tau-1 para zapatas corridas).
    f1 = (2 * asinh(n / sqrt(1.0 + m * m))
          + 2 * n * asinh(1.0 / hypot(n, m))) / pi
    f2 = 0.0 if m == 0 else m / pi * atan2(n, tau * m)
    a = 1 - capa.poisson**2
    b = 1 - capa.poisson - 2 * capa.poisson**2
    return presion_mpa * ancho_m / (2 * capa.modulo_mpa) * (a * f1 - b * f2)


def asiento_esquina_cm(
    presion_mpa: float,
    ancho_m: float,
    largo_m: float,
    capas: tuple[CapaSuelo, ...],
) -> float:
    """Suma el acortamiento de los estratos bajo la esquina, en cm."""
    asiento_m = 0.0
    for capa in capas:
        superior = _asiento_esquina_en_profundidad_m(
            presion_mpa, ancho_m, largo_m, capa.z_superior_m, capa
        )
        inferior = _asiento_esquina_en_profundidad_m(
            presion_mpa, ancho_m, largo_m, capa.z_inferior_m, capa
        )
        asiento_m += superior - inferior
    return asiento_m * 100.0


def asiento_centro_cm(
    presion_mpa: float,
    ancho_m: float,
    largo_m: float,
    capas: tuple[CapaSuelo, ...],
    metodo: str,
) -> float:
    """Calcula el asiento central según la convención seleccionada."""
    if metodo == "excel":
        return 2.0 * asiento_esquina_cm(presion_mpa, ancho_m, largo_m, capas)
    return 4.0 * asiento_esquina_cm(presion_mpa, ancho_m / 2, largo_m / 2, capas)


def _presion_para_asiento(
    asiento_objetivo_cm: float,
    ancho_m: float,
    largo_m: float,
    datos: DatosAsientos,
) -> float:
    asiento_unitario = asiento_centro_cm(
        1.0, ancho_m, largo_m, datos.capas, datos.metodo_centro
    )
    if not np.isfinite(asiento_unitario) or asiento_unitario <= 0:
        raise ValueError("La flexibilidad calculada debe ser positiva y finita.")
    return asiento_objetivo_cm / asiento_unitario


def calcular_presiones_asiento(
    anchos_m: tuple[float, ...],
    datos: DatosAsientos,
) -> tuple[np.ndarray, np.ndarray]:
    """Presión admisible por asiento para geometría cuadrada y corrida, en MPa."""
    errores = datos.validar()
    if errores:
        raise ValueError(" ".join(errores))
    if any(b <= 0 for b in anchos_m):
        raise ValueError("Los anchos deben ser mayores que cero.")
    cuadradas = [
        _presion_para_asiento(datos.asiento_admisible_cm, b, b, datos) for b in anchos_m
    ]
    corridas = [
        _presion_para_asiento(
            datos.asiento_admisible_cm, b, datos.longitud_corrida_m, datos
        )
        for b in anchos_m
    ]
    return np.asarray(cuadradas), np.asarray(corridas)
