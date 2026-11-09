"""Busqueda determinista de superficies circulares criticas."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from slope_stability_app.calculations.geometry import Circle, circle_from_endpoints, is_admissible
from slope_stability_app.calculations.stability import SurfaceEvaluation, evaluate_surface
from slope_stability_app.models import AnalysisConfig, SlopeGeometry, SoilProfile


@dataclass(frozen=True)
class CriticalResult:
    method: str
    factor_of_safety: float
    evaluation: SurfaceEvaluation


@dataclass(frozen=True)
class SearchResult:
    fellenius: CriticalResult
    bishop: CriticalResult
    evaluated_surfaces: int
    valid_surfaces: int


_SEARCH_GRIDS = {
    # Cada nivel contiene exactamente los puntos del anterior: n_siguiente = 2*n_anterior - 1.
    "Rapida": (3, 4, 5),
    "Equilibrada": (5, 7, 9),
    "Detallada": (9, 13, 17),
}


def _candidate_circles(geometry: SlopeGeometry, config: AnalysisConfig):
    n_entry, n_exit, n_center = _SEARCH_GRIDS[config.search_level]
    entry_values = np.unique(
        np.concatenate((np.linspace(geometry.x_min, 0.65 * geometry.run, n_entry), np.array([0.0])))
    )
    exit_values = np.unique(
        np.concatenate((np.linspace(0.25 * geometry.run, geometry.x_max, n_exit), np.array([geometry.run])))
    )
    center_ratios = np.linspace(0.25, 1.60, n_center)
    for entry_x in entry_values:
        for exit_x in exit_values:
            span = exit_x - entry_x
            if span < 0.10 * geometry.height:
                continue
            for center_ratio in center_ratios:
                center_x = entry_x + center_ratio * span
                circle = circle_from_endpoints(float(entry_x), float(exit_x), float(center_x), geometry)
                if circle is not None:
                    yield circle


def search_critical_surfaces(
    geometry: SlopeGeometry,
    profile: SoilProfile,
    config: AnalysisConfig,
) -> SearchResult:
    geometry.validate()
    profile.validate(geometry.model_depth)
    config.validate()
    best_f: SurfaceEvaluation | None = None
    best_b: SurfaceEvaluation | None = None
    evaluated = 0
    valid = 0
    for circle in _candidate_circles(geometry, config):
        evaluated += 1
        if not is_admissible(circle, geometry, config.min_depth_ratio):
            continue
        try:
            result = evaluate_surface(circle, geometry, profile, config)
        except (FloatingPointError, ValueError):
            continue
        fs_f = result.fellenius.factor_of_safety
        fs_b = result.bishop.factor_of_safety
        if not np.isfinite(fs_f) or not np.isfinite(fs_b) or not result.bishop.converged:
            continue
        valid += 1
        if best_f is None or fs_f < best_f.fellenius.factor_of_safety:
            best_f = result
        if best_b is None or fs_b < best_b.bishop.factor_of_safety:
            best_b = result
    if best_f is None or best_b is None:
        raise RuntimeError("No se encontraron superficies circulares admisibles. Revise geometria y parametros.")
    return SearchResult(
        fellenius=CriticalResult("Fellenius", best_f.fellenius.factor_of_safety, best_f),
        bishop=CriticalResult("Bishop simplificado", best_b.bishop.factor_of_safety, best_b),
        evaluated_surfaces=evaluated,
        valid_surfaces=valid,
    )
