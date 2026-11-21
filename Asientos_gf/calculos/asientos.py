"""Orquestacion de tensiones, asientos y evolucion temporal."""

from __future__ import annotations

from dataclasses import dataclass
from math import log10

import numpy as np
from numpy.typing import NDArray

from modelos.datos import AnalysisOptions, Foundation, Layer, ValidationIssue
from modelos.perfil import SoilSlice, discretize_profile, effective_vertical_stress, layer_at_depth, total_vertical_stress
from utiles.constantes import KPA_PER_MPA, MM_PER_M

from .consolidacion import degree_of_consolidation, primary_settlement_slice, secondary_settlement, time_for_degree
from .tensiones import PressureField, build_pressure_field, stress_from_field, vertical_displacement_elastic_from_field


@dataclass(frozen=True)
class PointResult:
    name: str
    x_m: float
    y_m: float
    immediate_mm: float
    primary_final_mm: float
    secondary_service_mm: float
    total_service_mm: float


@dataclass(frozen=True)
class CalculationResult:
    foundation: Foundation
    pressure_field: PressureField
    excavation_pressure_kpa: float
    net_resultant_kn: float
    analysis_depth_m: float
    influence_reached: bool
    slices: tuple[dict[str, float | str | bool], ...]
    points: tuple[PointResult, ...]
    time_years: NDArray[np.float64]
    time_settlement_mm: NDArray[np.float64]
    warnings: tuple[str, ...]
    assumptions: tuple[str, ...]


def validate_case(
    foundation: Foundation,
    layers: list[Layer],
    options: AnalysisOptions,
    water_table_m: float | None,
    pore_pressure_points: tuple[tuple[float, float], ...] | None = None,
) -> list[ValidationIssue]:
    issues = foundation.validate() + options.validate()
    if not layers:
        issues.append(ValidationIssue("estratos", "Se requiere al menos un estrato."))
        return issues
    for index, layer in enumerate(layers):
        issues.extend(layer.validate(index))
    if water_table_m is not None and (not np.isfinite(water_table_m) or water_table_m < 0):
        issues.append(ValidationIssue("water_table_m", "Debe ser nulo/ausente o una profundidad no negativa."))
    if pore_pressure_points:
        previous_depth = -np.inf
        for index, (depth, pressure) in enumerate(pore_pressure_points):
            if not np.isfinite(depth) or depth < 0 or depth <= previous_depth:
                issues.append(ValidationIssue(
                    f"pore_pressure_points[{index}]", "Las profundidades deben ser finitas, no negativas y crecientes."
                ))
            if not np.isfinite(pressure):
                issues.append(ValidationIssue(f"pore_pressure_points[{index}]", "La presion debe ser finita."))
            previous_depth = depth
    if foundation.shape == "banda" and options.immediate_model == "elastico_3d":
        issues.append(ValidationIssue(
            "immediate_model",
            "La deformacion elastica 3D no es aplicable al modelo bidimensional de banda; use el modelo edometrico 1D.",
        ))
    if foundation.rigidity == "rigida" and options.immediate_model != "elastico_3d":
        issues.append(ValidationIssue(
            "immediate_model",
            "La base rigida requiere el modelo elastico 3D para mantener la compatibilidad de desplazamientos.",
        ))
    return issues


def representative_elastic_properties(layers: list[Layer], base_m: float, width_m: float) -> tuple[float, float]:
    """Promedio armonico de E y promedio de nu en los primeros 2B bajo la base."""
    end = base_m + 2.0 * width_m
    bounds = [base_m, end]
    z = 0.0
    for layer in layers[:-1]:
        z += layer.thickness_m
        if base_m < z < end:
            bounds.append(z)
    bounds.sort()
    compliance = 0.0
    nu_sum = 0.0
    total = 0.0
    for za, zb in zip(bounds[:-1], bounds[1:]):
        _, layer, _, _ = layer_at_depth(layers, 0.5 * (za + zb))
        thickness = zb - za
        compliance += thickness / (layer.e_mpa * KPA_PER_MPA)
        nu_sum += layer.nu * thickness
        total += thickness
    return total / compliance, nu_sum / total


def _find_influence_depth(
    field: PressureField,
    foundation: Foundation,
    layers: list[Layer],
    water_table_m: float | None,
    options: AnalysisOptions,
    pore_pressure_points: tuple[tuple[float, float], ...] | None,
) -> tuple[float, bool]:
    width = foundation.characteristic_width_m
    maximum = options.max_depth_factor * width
    step = max(0.02, min(options.dz_m, width / 50.0))
    consecutive = 0
    depth = step
    while depth <= maximum:
        delta = abs(float(stress_from_field(field, depth)))
        sigma_0 = effective_vertical_stress(
            layers, foundation.embedment_m + depth, water_table_m, options.gamma_water_kn_m3,
            pore_pressure_points,
        )
        if delta <= options.influence_ratio * max(sigma_0, 0.1):
            consecutive += 1
            if consecutive >= 5:
                return depth - 4.0 * step, True
        else:
            consecutive = 0
        depth += step
    return maximum, False


def _evaluation_points(foundation: Foundation) -> list[tuple[str, float, float]]:
    if foundation.rigidity == "rigida":
        return [("Centro de la base rigida", 0.0, 0.0)]
    if foundation.shape == "circular":
        return [("Centro", 0.0, 0.0), ("Borde", foundation.diameter_m / 2.0, 0.0)]
    if foundation.shape == "banda":
        return [("Centro", 0.0, 0.0), ("Borde", foundation.width_m / 2.0, 0.0)]
    return [
        ("Centro", 0.0, 0.0),
        ("Borde", foundation.width_m / 2.0, 0.0),
        ("Esquina", foundation.width_m / 2.0, foundation.length_m / 2.0),
    ]


def _drainage_paths(slices: list[SoilSlice], layers: list[Layer]) -> dict[int, float]:
    ranges: dict[int, list[float]] = {}
    for soil_slice in slices:
        layer = layers[soil_slice.layer_index]
        if layer.soil_type != "cohesivo" or not soil_slice.saturated:
            continue
        ranges.setdefault(soil_slice.layer_index, []).extend([soil_slice.z_top_m, soil_slice.z_bottom_m])
    paths: dict[int, float] = {}
    for index, values in ranges.items():
        saturated_thickness = max(values) - min(values)
        paths[index] = saturated_thickness / 2.0 if layers[index].drainage == "doble" else saturated_thickness
    return paths


def _calculate_point(
    name: str,
    x_m: float,
    y_m: float,
    slices: list[SoilSlice],
    layers: list[Layer],
    field: PressureField,
    foundation: Foundation,
    options: AnalysisOptions,
    drainage_paths: dict[int, float],
) -> tuple[PointResult, list[dict[str, float | str | bool]], list[tuple[int, float, float, float]]]:
    relative_depths = np.asarray([item.z_mid_m - foundation.embedment_m for item in slices])
    delta_sigma = np.asarray(stress_from_field(field, relative_depths, x_m, y_m))
    layer_moduli = np.asarray([layers[item.layer_index].e_mpa * KPA_PER_MPA for item in slices])
    layer_nu = np.asarray([layers[item.layer_index].nu for item in slices])
    if options.immediate_model == "elastico_3d":
        immediate_parts = np.empty(len(slices), dtype=float)
        for index, soil_slice in enumerate(slices):
            layer = layers[soil_slice.layer_index]
            top = soil_slice.z_top_m - foundation.embedment_m
            bottom = soil_slice.z_bottom_m - foundation.embedment_m
            displacement_top = vertical_displacement_elastic_from_field(
                field, top, layer.e_mpa * KPA_PER_MPA, layer.nu, x_m, y_m
            )
            displacement_bottom = vertical_displacement_elastic_from_field(
                field, bottom, layer.e_mpa * KPA_PER_MPA, layer.nu, x_m, y_m
            )
            immediate_parts[index] = displacement_top - displacement_bottom
    else:
        immediate_parts = delta_sigma * np.asarray([item.thickness_m for item in slices]) / layer_moduli

    primary_parts = np.zeros(len(slices), dtype=float)
    secondary_parts = np.zeros(len(slices), dtype=float)
    temporal_components: list[tuple[int, float, float, float]] = []
    rows: list[dict[str, float | str | bool]] = []
    for index, (soil_slice, stress_increment) in enumerate(zip(slices, delta_sigma)):
        layer = layers[soil_slice.layer_index]
        drainage_path = drainage_paths.get(soil_slice.layer_index, 0.0)
        t95 = 0.0
        if options.include_primary and layer.soil_type == "cohesivo" and soil_slice.saturated:
            primary_parts[index] = primary_settlement_slice(
                soil_slice.thickness_m,
                soil_slice.sigma_v0_effective_kpa,
                float(stress_increment),
                layer.sigma_pc_kpa,
                layer.cc,
                layer.cr,
                layer.e0,
            )
            t95 = time_for_degree(0.95, layer.cv_m2_year, drainage_path)
            if options.include_secondary and primary_parts[index] > 0:
                secondary_parts[index] = secondary_settlement(
                    soil_slice.thickness_m,
                    layer.c_alpha,
                    layer.e0,
                    options.service_years,
                    t95,
                )
            temporal_components.append((index, primary_parts[index], drainage_path, t95))
        rows.append({
            "punto": name,
            "estrato": soil_slice.layer_name,
            "z_m": soil_slice.z_mid_m,
            "espesor_m": soil_slice.thickness_m,
            "saturado": soil_slice.saturated,
            "sigma_v0_total_kpa": soil_slice.sigma_v0_total_kpa,
            "u0_kpa": soil_slice.pore_pressure_kpa,
            "sigma_v0_efectiva_kpa": soil_slice.sigma_v0_effective_kpa,
            "delta_sigma_z_kpa": float(stress_increment),
            "asiento_inmediato_mm": immediate_parts[index] * MM_PER_M,
            "asiento_primario_final_mm": primary_parts[index] * MM_PER_M,
            "asiento_secundario_servicio_mm": secondary_parts[index] * MM_PER_M,
            "t95_anos": t95,
        })

    if foundation.rigidity == "rigida" and field.rigid_settlement_center_m is not None and options.immediate_model == "elastico_3d":
        immediate_m = field.rigid_settlement_center_m
    else:
        immediate_m = float(np.sum(immediate_parts))
    primary_m = float(np.sum(primary_parts))
    secondary_m = float(np.sum(secondary_parts))
    return PointResult(
        name,
        x_m,
        y_m,
        immediate_m * MM_PER_M,
        primary_m * MM_PER_M,
        secondary_m * MM_PER_M,
        (immediate_m + primary_m + secondary_m) * MM_PER_M,
    ), rows, temporal_components


def calculate_settlement(
    foundation: Foundation,
    layers: list[Layer],
    options: AnalysisOptions,
    water_table_m: float | None,
    pore_pressure_points: tuple[tuple[float, float], ...] | None = None,
) -> CalculationResult:
    issues = validate_case(foundation, layers, options, water_table_m, pore_pressure_points)
    errors = [item for item in issues if item.severity == "error"]
    if errors:
        raise ValueError("\n".join(f"{item.field}: {item.message}" for item in errors))
    warnings = [f"{item.field}: {item.message}" for item in issues if item.severity == "warning"]
    excavation_pressure = total_vertical_stress(
        layers, foundation.embedment_m, water_table_m, pore_pressure_points, options.gamma_water_kn_m3
    )
    representative_e, representative_nu = representative_elastic_properties(
        layers, foundation.embedment_m, foundation.characteristic_width_m
    )
    field = build_pressure_field(
        foundation, excavation_pressure, representative_e, representative_nu, options.quadrature_order
    )
    warnings.extend(field.warnings)
    analysis_depth, reached = _find_influence_depth(
        field, foundation, layers, water_table_m, options, pore_pressure_points
    )
    if not reached:
        warnings.append(
            f"No se alcanzo el criterio de influencia antes de {analysis_depth:.2f} m bajo la base; "
            "el resultado queda truncado y debe ampliarse el factor de profundidad."
        )
    defined_depth = sum(layer.thickness_m for layer in layers)
    if foundation.embedment_m + analysis_depth > defined_depth:
        warnings.append(
            f"El perfil termina a {defined_depth:.2f} m; se prolonga el ultimo estrato hasta "
            f"{foundation.embedment_m + analysis_depth:.2f} m."
        )
    slices = discretize_profile(
        layers,
        foundation.embedment_m,
        analysis_depth,
        options.dz_m,
        water_table_m,
        options.gamma_water_kn_m3,
        pore_pressure_points,
    )
    paths = _drainage_paths(slices, layers)
    point_results: list[PointResult] = []
    all_rows: list[dict[str, float | str | bool]] = []
    center_temporal: list[tuple[int, float, float, float]] = []
    for point_index, (name, x_m, y_m) in enumerate(_evaluation_points(foundation)):
        point, rows, temporal = _calculate_point(
            name, x_m, y_m, slices, layers, field, foundation, options, paths
        )
        point_results.append(point)
        all_rows.extend(rows)
        if point_index == 0:
            center_temporal = temporal

    center = point_results[0]
    positive_times = [component[3] for component in center_temporal if component[3] > 0]
    maximum_time = max([options.service_years, *positive_times, 0.01])
    minimum_time = min(1e-4, maximum_time / 10000.0)
    time_years = np.concatenate(([0.0], np.geomspace(minimum_time, maximum_time, 140)))
    time_settlement = np.full(time_years.shape, center.immediate_mm, dtype=float)
    center_rows = [row for row in all_rows if row["punto"] == center.name]
    for slice_index, primary_m, drainage_path, t95 in center_temporal:
        layer = layers[slices[slice_index].layer_index]
        for time_index, time in enumerate(time_years[1:], start=1):
            degree = degree_of_consolidation(time, layer.cv_m2_year, drainage_path)
            time_settlement[time_index] += primary_m * degree * MM_PER_M
            if options.include_secondary and primary_m > 0:
                time_settlement[time_index] += secondary_settlement(
                    slices[slice_index].thickness_m, layer.c_alpha, layer.e0, time, t95
                ) * MM_PER_M

    assumptions = (
        "Semiespacio elastico lineal de Boussinesq para la transmision de tensiones.",
        "Estratos horizontales; parametros constantes dentro de cada estrato.",
        "Consolidacion 1D de Terzaghi solo en material cohesivo situado bajo el nivel freatico.",
        "La presion de poros inicial es hidrostatica y el nivel freatico es horizontal.",
        "La etiqueta de cumplimiento compara exclusivamente con el limite introducido por el usuario.",
    )
    if foundation.rigidity == "rigida":
        assumptions += (
            "La redistribucion rigida se obtiene con un semiespacio homogeneo equivalente; la consolidacion usa esa presion inicial sin acoplamiento evolutivo suelo-estructura.",
        )
    if pore_pressure_points:
        assumptions = tuple(
            "La presion intersticial inicial se interpola linealmente entre los puntos piezometricos y se extrapola con el ultimo gradiente."
            if text.startswith("La presion de poros inicial") else text
            for text in assumptions
        )
    return CalculationResult(
        foundation,
        field,
        excavation_pressure,
        field.resultant_kn,
        analysis_depth,
        reached,
        tuple(all_rows),
        tuple(point_results),
        time_years,
        time_settlement,
        tuple(dict.fromkeys(warnings)),
        assumptions,
    )
