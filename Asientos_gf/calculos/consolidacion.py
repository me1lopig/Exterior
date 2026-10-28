"""Consolidacion unidimensional de Terzaghi por unidad drenante."""

from __future__ import annotations

from math import exp, log10, pi

from scipy.optimize import brentq


def degree_of_consolidation(time_years: float, cv_m2_year: float, drainage_path_m: float, terms: int = 80) -> float:
    """Grado medio U mediante la serie exacta para carga instantanea."""
    if time_years <= 0:
        return 0.0
    if cv_m2_year <= 0 or drainage_path_m <= 0:
        raise ValueError("cv y la longitud de drenaje deben ser positivos.")
    time_factor = cv_m2_year * time_years / drainage_path_m**2
    remainder = 0.0
    for m in range(terms):
        odd = 2 * m + 1
        remainder += exp(-(odd**2) * pi**2 * time_factor / 4.0) / odd**2
    return min(1.0, max(0.0, 1.0 - 8.0 * remainder / pi**2))


def time_for_degree(target_u: float, cv_m2_year: float, drainage_path_m: float) -> float:
    if not 0 < target_u < 1:
        raise ValueError("El grado objetivo debe estar entre cero y uno.")
    function = lambda t: degree_of_consolidation(t, cv_m2_year, drainage_path_m) - target_u
    upper = drainage_path_m**2 / cv_m2_year
    while function(upper) < 0:
        upper *= 2.0
    return float(brentq(function, 0.0, upper))


def primary_settlement_slice(
    thickness_m: float,
    sigma_v0_effective_kpa: float,
    delta_sigma_kpa: float,
    sigma_pc_kpa: float,
    cc: float,
    cr: float,
    e0: float,
) -> float:
    """Asiento final de una rebanada; signo positivo en compresion."""
    sigma_0 = sigma_v0_effective_kpa
    sigma_f = sigma_0 + delta_sigma_kpa
    if sigma_0 <= 0 or sigma_f <= 0:
        raise ValueError("La tension efectiva inicial y final deben ser positivas.")
    if sigma_pc_kpa + 1e-9 < sigma_0:
        raise ValueError(
            f"La tension de preconsolidacion ({sigma_pc_kpa:.2f} kPa) es menor que "
            f"la tension efectiva inicial ({sigma_0:.2f} kPa)."
        )
    factor = thickness_m / (1.0 + e0)
    if sigma_f <= sigma_pc_kpa:
        return factor * cr * log10(sigma_f / sigma_0)
    recompression = cr * log10(sigma_pc_kpa / sigma_0) if sigma_pc_kpa > sigma_0 else 0.0
    virgin = cc * log10(sigma_f / sigma_pc_kpa)
    return factor * (recompression + virgin)


def secondary_settlement(
    thickness_m: float,
    c_alpha: float,
    e0: float,
    time_years: float,
    reference_time_years: float,
) -> float:
    if c_alpha <= 0 or time_years <= reference_time_years or reference_time_years <= 0:
        return 0.0
    return thickness_m * c_alpha / (1.0 + e0) * log10(time_years / reference_time_years)
