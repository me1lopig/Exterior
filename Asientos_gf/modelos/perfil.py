"""Discretizacion vertical del terreno y tensiones geostaticas."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .datos import Layer


@dataclass(frozen=True)
class SoilSlice:
    z_top_m: float
    z_bottom_m: float
    z_mid_m: float
    thickness_m: float
    layer_index: int
    layer_name: str
    saturated: bool
    sigma_v0_total_kpa: float
    pore_pressure_kpa: float
    sigma_v0_effective_kpa: float


def layer_at_depth(layers: list[Layer], depth_m: float) -> tuple[int, Layer, float, float]:
    """Devuelve indice, estrato y cotas superior/inferior; prolonga el ultimo."""
    top = 0.0
    for index, layer in enumerate(layers):
        bottom = top + layer.thickness_m
        if depth_m <= bottom + 1e-12 or index == len(layers) - 1:
            return index, layer, top, bottom
        top = bottom
    raise ValueError("Se requiere al menos un estrato.")


def _pore_profile(points: tuple[tuple[float, float], ...]) -> tuple[np.ndarray, np.ndarray]:
    ordered = sorted((float(z), float(u)) for z, u in points)
    if not ordered:
        raise ValueError("El perfil piezometrico no puede estar vacio.")
    if ordered[0][0] > 0:
        ordered.insert(0, (0.0, 0.0))
    return np.asarray([item[0] for item in ordered]), np.asarray([item[1] for item in ordered])


def pore_pressure(
    depth_m: float,
    water_table_m: float | None,
    gamma_water_kn_m3: float,
    pore_pressure_points: tuple[tuple[float, float], ...] | None = None,
) -> float:
    if pore_pressure_points:
        depths, pressures = _pore_profile(pore_pressure_points)
        if depth_m <= depths[-1]:
            return float(np.interp(depth_m, depths, pressures))
        if len(depths) == 1:
            return float(pressures[-1])
        slope = (pressures[-1] - pressures[-2]) / (depths[-1] - depths[-2])
        return float(pressures[-1] + slope * (depth_m - depths[-1]))
    if water_table_m is None or depth_m <= water_table_m:
        return 0.0
    return gamma_water_kn_m3 * (depth_m - water_table_m)


def _hydraulic_breaks(
    depth_m: float,
    water_table_m: float | None,
    pore_pressure_points: tuple[tuple[float, float], ...] | None,
) -> set[float]:
    breaks: set[float] = set()
    if pore_pressure_points:
        depths, pressures = _pore_profile(pore_pressure_points)
        for value in depths:
            if 0 < value < depth_m:
                breaks.add(float(value))
        for z1, z2, u1, u2 in zip(depths[:-1], depths[1:], pressures[:-1], pressures[1:]):
            if u1 * u2 < 0:
                zero = z1 - u1 * (z2 - z1) / (u2 - u1)
                if 0 < zero < depth_m:
                    breaks.add(float(zero))
    elif water_table_m is not None and 0 < water_table_m < depth_m:
        breaks.add(float(water_table_m))
    return breaks


def total_vertical_stress(
    layers: list[Layer],
    depth_m: float,
    water_table_m: float | None,
    pore_pressure_points: tuple[tuple[float, float], ...] | None = None,
    gamma_water_kn_m3: float = 9.81,
) -> float:
    """Tension vertical total geostatica, integrando exactamente fronteras de capa y agua."""
    if depth_m <= 0:
        return 0.0
    bounds = {0.0, float(depth_m)}
    z = 0.0
    for layer in layers[:-1]:
        z += layer.thickness_m
        if 0 < z < depth_m:
            bounds.add(z)
    bounds.update(_hydraulic_breaks(depth_m, water_table_m, pore_pressure_points))
    points = sorted(bounds)
    sigma = 0.0
    for za, zb in zip(points[:-1], points[1:]):
        zm = 0.5 * (za + zb)
        _, layer, _, _ = layer_at_depth(layers, zm)
        saturated = pore_pressure(zm, water_table_m, gamma_water_kn_m3, pore_pressure_points) > 1e-9
        gamma = layer.gamma_sat_kn_m3 if saturated else layer.gamma_unsat_kn_m3
        sigma += gamma * (zb - za)
    return sigma


def effective_vertical_stress(
    layers: list[Layer],
    depth_m: float,
    water_table_m: float | None,
    gamma_water_kn_m3: float,
    pore_pressure_points: tuple[tuple[float, float], ...] | None = None,
) -> float:
    return total_vertical_stress(
        layers, depth_m, water_table_m, pore_pressure_points, gamma_water_kn_m3
    ) - pore_pressure(
        depth_m, water_table_m, gamma_water_kn_m3, pore_pressure_points
    )


def discretize_profile(
    layers: list[Layer],
    foundation_base_m: float,
    analysis_depth_below_base_m: float,
    dz_m: float,
    water_table_m: float | None,
    gamma_water_kn_m3: float,
    pore_pressure_points: tuple[tuple[float, float], ...] | None = None,
) -> list[SoilSlice]:
    """Malla vertical alineada con base, capas y nivel freatico."""
    z_end = foundation_base_m + analysis_depth_below_base_m
    bounds = {float(foundation_base_m), float(z_end)}
    z = 0.0
    for layer in layers[:-1]:
        z += layer.thickness_m
        if foundation_base_m < z < z_end:
            bounds.add(z)
    bounds.update(
        value for value in _hydraulic_breaks(z_end, water_table_m, pore_pressure_points)
        if foundation_base_m < value < z_end
    )
    coarse = sorted(bounds)
    refined: list[float] = [coarse[0]]
    for za, zb in zip(coarse[:-1], coarse[1:]):
        count = max(1, int(np.ceil((zb - za) / dz_m)))
        refined.extend(np.linspace(za, zb, count + 1)[1:].tolist())
    slices: list[SoilSlice] = []
    for za, zb in zip(refined[:-1], refined[1:]):
        zm = 0.5 * (za + zb)
        index, layer, _, _ = layer_at_depth(layers, zm)
        sigma_total = total_vertical_stress(
            layers, zm, water_table_m, pore_pressure_points, gamma_water_kn_m3
        )
        u = pore_pressure(zm, water_table_m, gamma_water_kn_m3, pore_pressure_points)
        slices.append(SoilSlice(
            z_top_m=za,
            z_bottom_m=zb,
            z_mid_m=zm,
            thickness_m=zb - za,
            layer_index=index,
            layer_name=layer.name,
            saturated=u > 1e-9,
            sigma_v0_total_kpa=sigma_total,
            pore_pressure_kpa=u,
            sigma_v0_effective_kpa=sigma_total - u,
        ))
    return slices
