"""Geometria 2D del talud y de superficies circulares."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from slope_stability_app.models import SlopeGeometry


FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class Circle:
    center_x: float
    center_y: float
    radius: float
    entry_x: float
    exit_x: float

    def base_elevation(self, x: FloatArray) -> FloatArray:
        radicand = self.radius**2 - (x - self.center_x) ** 2
        return self.center_y - np.sqrt(np.maximum(radicand, 0.0))


def ground_elevation(x: FloatArray | float, geometry: SlopeGeometry) -> FloatArray:
    """Cota del terreno: coronacion, cara plana y berma inferior."""
    values = np.asarray(x, dtype=float)
    slope = geometry.height * (1.0 - values / geometry.run)
    return np.where(values <= 0.0, geometry.height, np.where(values < geometry.run, slope, 0.0))


def circle_from_endpoints(
    entry_x: float,
    exit_x: float,
    center_x: float,
    geometry: SlopeGeometry,
) -> Circle | None:
    """Construye un circulo que pasa por dos puntos del terreno y un centro_x dado."""
    y1 = float(ground_elevation(entry_x, geometry))
    y2 = float(ground_elevation(exit_x, geometry))
    denominator = 2.0 * (y2 - y1)
    if abs(denominator) < 1e-10:
        return None
    numerator = exit_x**2 + y2**2 - entry_x**2 - y1**2 - 2.0 * center_x * (exit_x - entry_x)
    center_y = numerator / denominator
    radius = float(np.hypot(entry_x - center_x, y1 - center_y))
    if not np.isfinite(radius) or radius <= 0:
        return None
    return Circle(center_x, center_y, radius, entry_x, exit_x)


def is_admissible(circle: Circle, geometry: SlopeGeometry, min_depth_ratio: float) -> bool:
    """Comprueba que el arco inferior quede bajo el terreno y tenga profundidad util."""
    if circle.center_y <= geometry.height:
        return False
    x = np.linspace(circle.entry_x, circle.exit_x, 121)
    radicand = circle.radius**2 - (x - circle.center_x) ** 2
    if np.any(radicand < -1e-7):
        return False
    base = circle.base_elevation(x)
    ground = ground_elevation(x, geometry)
    thickness = ground - base
    if np.min(thickness[1:-1]) < -1e-5:
        return False
    if np.max(thickness) < min_depth_ratio * geometry.height:
        return False
    lowest_x = float(np.clip(circle.center_x, circle.entry_x, circle.exit_x))
    lowest_base = float(circle.base_elevation(np.array([lowest_x]))[0])
    if lowest_base < geometry.model_base_elevation - 1e-7:
        return False
    return bool(np.all(np.isfinite(base)))
