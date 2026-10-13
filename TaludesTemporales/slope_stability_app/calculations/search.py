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
    "Rapida": (4, 6, 8),
    "Equilibrada": (6, 9, 12),
    "Detallada": (8, 12, 18),
}


def _candidate_circles(geometry: SlopeGeometry, config: AnalysisConfig):
    n_entry, n_exit, n_center = _SEARCH_GRIDS[config.search_level]
    entry_values = np.linspace(geometry.x_min, -0.04 * geometry.height, n_entry)
    exit_start = min(0.35 * geometry.run, geometry.run - 0.05 * geometry.height)
    exit_values = np.linspace(max(exit_start, 0.08 * geometry.run), geometry.x_max, n_exit)
    for entry_x in entry_values:
        for exit_x in exit_values:
            span = exit_x - entry_x
            center_values = np.linspace(entry_x + 0.52 * span, entry_x + 1.18 * span, n_center)
            for center_x in center_values:
                circle = circle_from_endpoints(float(entry_x), float(exit_x), float(center_x), geometry)
                if circle is not None:
                    yield circle


def search_critical_surfaces(
    geometry: SlopeGeometry,
    profile: SoilProfile,
    config: AnalysisConfig,
) -> SearchResult:
    geometry.validate()
    profile.validate(geometry.height)
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

