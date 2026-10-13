"""Metodos de Fellenius y Bishop simplificado para superficies circulares."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, radians, sin, tan

import numpy as np

from slope_stability_app.calculations.geometry import Circle, ground_elevation
from slope_stability_app.models import AnalysisConfig, SlopeGeometry, SoilProfile


@dataclass(frozen=True)
class SliceData:
    index: int
    x_mid: float
    width: float
    base_elevation: float
    top_elevation: float
    base_angle_deg: float
    base_length: float
    weight: float
    pore_pressure: float
    pore_force: float
    cohesion: float
    friction_deg: float
    soil_name: str


@dataclass(frozen=True)
class MethodResult:
    factor_of_safety: float
    converged: bool
    iterations: int


@dataclass(frozen=True)
class SurfaceEvaluation:
    circle: Circle
    fellenius: MethodResult
    bishop: MethodResult
    slices: tuple[SliceData, ...]
    total_weight: float
    max_pore_pressure: float


def _slice_weight(
    x_left: float,
    x_right: float,
    circle: Circle,
    geometry: SlopeGeometry,
    profile: SoilProfile,
) -> float:
    """Integra el peso por cuadratura vertical, separando estrato y saturacion."""
    xq, wq = np.polynomial.legendre.leggauss(5)
    x = 0.5 * (x_right - x_left) * xq + 0.5 * (x_right + x_left)
    weights = np.zeros_like(x)
    base = circle.base_elevation(x)
    top = ground_elevation(x, geometry)
    boundaries = [base]
    if profile.has_two_soils:
        boundaries.append(np.full_like(x, profile.interface_elevation))
    boundaries.append(np.full_like(x, geometry.water_elevation))
    boundaries.append(top)
    levels = np.sort(np.vstack(boundaries), axis=0)
    for low, high in zip(levels[:-1], levels[1:]):
        low_clipped = np.maximum(low, base)
        high_clipped = np.minimum(high, top)
        dz = np.maximum(high_clipped - low_clipped, 0.0)
        mid = 0.5 * (low_clipped + high_clipped)
        for j in range(x.size):
            if dz[j] <= 0:
                continue
            soil = profile.soil_at(float(mid[j]))
            gamma = soil.gamma_sat if mid[j] <= geometry.water_elevation else soil.gamma_dry
            weights[j] += dz[j] * gamma
    return float(0.5 * (x_right - x_left) * np.dot(wq, weights))


def build_slices(
    circle: Circle,
    geometry: SlopeGeometry,
    profile: SoilProfile,
    config: AnalysisConfig,
) -> tuple[SliceData, ...]:
    edges = np.linspace(circle.entry_x, circle.exit_x, config.slices + 1)
    slices: list[SliceData] = []
    for index, (x_left, x_right) in enumerate(zip(edges[:-1], edges[1:]), start=1):
        width = float(x_right - x_left)
        x_mid = 0.5 * (x_left + x_right)
        base = float(circle.base_elevation(np.array([x_mid]))[0])
        top = float(ground_elevation(x_mid, geometry))
        tangent_slope = (x_mid - circle.center_x) / max(circle.center_y - base, 1e-12)
        # Positivo cuando la base desciende hacia el pie (direccion del movimiento).
        alpha = -float(np.arctan(tangent_slope))
        cos_alpha = cos(alpha)
        if cos_alpha <= 1e-8:
            raise ValueError("Se ha generado una dovela con base casi vertical.")
        base_length = width / cos_alpha
        soil = profile.soil_at(base)
        phreatic_head = max(min(geometry.water_elevation, top) - base, 0.0)
        pore_pressure = config.gamma_water * phreatic_head
        weight = _slice_weight(x_left, x_right, circle, geometry, profile)
        slices.append(
            SliceData(
                index=index,
                x_mid=x_mid,
                width=width,
                base_elevation=base,
                top_elevation=top,
                base_angle_deg=float(np.degrees(alpha)),
                base_length=base_length,
                weight=weight,
                pore_pressure=pore_pressure,
                pore_force=pore_pressure * base_length,
                cohesion=soil.cohesion,
                friction_deg=soil.friction_deg,
                soil_name=soil.name,
            )
        )
    return tuple(slices)


def fellenius(slices: tuple[SliceData, ...]) -> MethodResult:
    resistance = 0.0
    driving = 0.0
    for item in slices:
        alpha = radians(item.base_angle_deg)
        normal_effective = item.weight * cos(alpha) - item.pore_force
        resistance += item.cohesion * item.base_length + max(normal_effective, 0.0) * tan(radians(item.friction_deg))
        driving += item.weight * sin(alpha)
    if driving <= 1e-9:
        return MethodResult(float("nan"), False, 0)
    return MethodResult(resistance / driving, True, 1)


def bishop_simplified(slices: tuple[SliceData, ...], config: AnalysisConfig) -> MethodResult:
    driving = sum(item.weight * sin(radians(item.base_angle_deg)) for item in slices)
    if driving <= 1e-9:
        return MethodResult(float("nan"), False, 0)
    factor = 1.5
    for iteration in range(1, config.bishop_max_iterations + 1):
        resistance = 0.0
        valid = True
        for item in slices:
            alpha = radians(item.base_angle_deg)
            tan_phi = tan(radians(item.friction_deg))
            m_alpha = cos(alpha) + sin(alpha) * tan_phi / factor
            if m_alpha <= 1e-8:
                valid = False
                break
            numerator = item.cohesion * item.width + (item.weight - item.pore_pressure * item.width) * tan_phi
            resistance += numerator / m_alpha
        if not valid:
            return MethodResult(float("nan"), False, iteration)
        updated = resistance / driving
        if not np.isfinite(updated) or updated <= 0:
            return MethodResult(float("nan"), False, iteration)
        if abs(updated - factor) <= config.bishop_tolerance * max(1.0, updated):
            return MethodResult(updated, True, iteration)
        factor = 0.5 * factor + 0.5 * updated
    return MethodResult(factor, False, config.bishop_max_iterations)


def evaluate_surface(
    circle: Circle,
    geometry: SlopeGeometry,
    profile: SoilProfile,
    config: AnalysisConfig,
) -> SurfaceEvaluation:
    slices = build_slices(circle, geometry, profile, config)
    result_f = fellenius(slices)
    result_b = bishop_simplified(slices, config)
    return SurfaceEvaluation(
        circle=circle,
        fellenius=result_f,
        bishop=result_b,
        slices=slices,
        total_weight=sum(item.weight for item in slices),
        max_pore_pressure=max((item.pore_pressure for item in slices), default=0.0),
    )

