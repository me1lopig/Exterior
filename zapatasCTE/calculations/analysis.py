from __future__ import annotations

from dataclasses import replace
import math

import numpy as np
import pandas as pd

from calculations.bearing_capacity import calculate_bearing_capacity
from calculations.layers import assess_foundation_bulbs
from calculations.serviceability import allowable_net_pressure_steinbrenner
from calculations.stability import check_contact
from models.inputs import (
    ActionCase,
    Foundation,
    FoundationType,
    SoilLayer,
    SoilProfile,
)


def evaluate_cases(
    soil: SoilProfile, foundation: Foundation, actions: list[ActionCase]
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    details: list[dict[str, object]] = []
    for action in actions:
        bearing = calculate_bearing_capacity(soil, foundation, action)
        inside, contact = check_contact(foundation, action)
        overall = bearing.passes and inside.passes
        rows.append(
            {
                "combinacion": action.name,
                "situacion": action.situation.value,
                "B_eff_m": bearing.geometry.width_m,
                "L_eff_m": bearing.geometry.length_m,
                "area_eff_m2": bearing.geometry.area_m2,
                "q_b_kpa": bearing.pressure_gross_kpa,
                "q_h_kpa": bearing.characteristic_resistance_kpa,
                "q_d_kpa": bearing.design_resistance_kpa,
                "util_hundimiento": bearing.utilization,
                "contacto_completo": contact.passes,
                "cumple_geotecnia": overall,
            }
        )
        details.append(
            {
                "actions": action,
                "bearing": bearing,
                "inside_base": inside,
                "full_contact": contact,
            }
        )
    return pd.DataFrame(rows), details


def optimize_geometry(
    soil: SoilProfile,
    foundation_template: Foundation,
    actions: list[ActionCase],
    width_min_m: float,
    width_max_m: float,
    length_min_m: float,
    length_max_m: float,
    step_m: float,
    additional_vertical_kpa: float = 0.0,
) -> pd.DataFrame:
    if step_m <= 0 or width_min_m <= 0 or width_max_m < width_min_m:
        raise ValueError("Rango de optimizacion no valido")
    widths = np.arange(width_min_m, width_max_m + step_m / 2.0, step_m)
    if foundation_template.kind is FoundationType.RECTANGULAR:
        if length_max_m < length_min_m:
            raise ValueError("Rango de longitudes no valido")
        lengths = np.arange(length_min_m, length_max_m + step_m / 2.0, step_m)
    else:
        lengths = widths if foundation_template.kind is FoundationType.CIRCULAR else np.array([1.0])
    rows: list[dict[str, object]] = []
    for width in widths:
        candidate_lengths = lengths
        for length in candidate_lengths:
            if foundation_template.kind is FoundationType.RECTANGULAR and width > length:
                continue
            if foundation_template.kind is FoundationType.CIRCULAR and not math.isclose(width, length):
                continue
            foundation = replace(
                foundation_template,
                width_m=float(width),
                length_m=float(length),
            )
            try:
                candidate_actions = [
                    replace(
                        action,
                        vertical_kn=(
                            action.vertical_kn
                            + foundation.plan_area_m2 * additional_vertical_kpa
                        ),
                    )
                    for action in actions
                ]
                table, _ = evaluate_cases(soil, foundation, candidate_actions)
            except ValueError:
                continue
            rows.append(
                {
                    "B_m": float(width),
                    "L_m": float(length),
                    "area_m2": foundation.plan_area_m2,
                    "q_b_max_kpa": float(table["q_b_kpa"].max()),
                    "util_h_max": float(table["util_hundimiento"].max()),
                    "cumple": bool(table["cumple_geotecnia"].all()),
                }
            )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(["cumple", "area_m2"], ascending=[False, True]).reset_index(drop=True)


def admissible_capacity_grid(
    soil: SoilProfile,
    foundation_template: Foundation,
    layers: list[SoilLayer],
    width_min_m: float,
    width_max_m: float,
    length_min_m: float,
    length_max_m: float,
    step_m: float,
    allowable_settlement_mm: float,
    influence_depth_m: float,
    additional_vertical_kpa: float = 0.0,
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    """Calculate ELU and settlement limits for a B-L geometry grid."""
    if step_m <= 0 or width_min_m <= 0 or width_max_m < width_min_m:
        raise ValueError("Rango B-L no valido")
    widths = np.arange(width_min_m, width_max_m + step_m / 2.0, step_m)
    if foundation_template.kind is FoundationType.RECTANGULAR:
        if length_max_m < length_min_m:
            raise ValueError("Rango de longitudes no valido")
        lengths = np.arange(length_min_m, length_max_m + step_m / 2.0, step_m)
    elif foundation_template.kind is FoundationType.CIRCULAR:
        lengths = widths
    else:
        lengths = np.array([1.0])

    rows: list[dict[str, object]] = []
    details: list[dict[str, object]] = []
    for width in widths:
        for length in lengths:
            if foundation_template.kind is FoundationType.RECTANGULAR and width > length:
                continue
            if foundation_template.kind is FoundationType.CIRCULAR and not math.isclose(
                width, length
            ):
                continue
            foundation = replace(
                foundation_template,
                width_m=float(width),
                length_m=float(length),
            )
            centered = ActionCase(
                name="Capacidad centrada",
                vertical_kn=max(foundation.plan_area_m2, 1e-6),
            )
            try:
                bearing = calculate_bearing_capacity(soil, foundation, centered)
            except ValueError:
                continue
            coverage = assess_foundation_bulbs(
                layers,
                foundation.embedment_m,
                foundation.width_m,
                influence_depth_m,
            )
            q0 = float(bearing.parameters["q0k_kpa"])
            settlement_data: dict[str, object] | None = None
            q_settlement_gross = math.nan
            if (
                coverage["all_covered"]
                and foundation.kind is not FoundationType.STRIP
            ):
                if foundation.kind is FoundationType.CIRCULAR:
                    equivalent_side = math.sqrt(foundation.plan_area_m2)
                    settlement_width = equivalent_side
                    settlement_length = equivalent_side
                else:
                    settlement_width = foundation.width_m
                    settlement_length = foundation.length_m
                settlement_data = allowable_net_pressure_steinbrenner(
                    allowable_settlement_mm,
                    settlement_width,
                    settlement_length,
                    foundation.embedment_m,
                    layers,
                    influence_depth_m,
                )
                q_settlement_gross = (
                    float(settlement_data["allowable_net_pressure_kpa"]) + q0
                )
            q_limit = (
                min(bearing.design_resistance_kpa, q_settlement_gross)
                if math.isfinite(q_settlement_gross)
                else math.nan
            )
            governing = "Sin cobertura"
            if math.isfinite(q_limit):
                governing = (
                    "Hundimiento ELU"
                    if bearing.design_resistance_kpa <= q_settlement_gross
                    else "Asiento ELS"
                )
            base_load = q_limit * foundation.plan_area_m2 if math.isfinite(q_limit) else math.nan
            structure_load = (
                max(base_load - additional_vertical_kpa * foundation.plan_area_m2, 0.0)
                if math.isfinite(base_load)
                else math.nan
            )
            rows.append(
                {
                    "B_m": foundation.width_m,
                    "L_m": foundation.length_m,
                    "area_m2": foundation.plan_area_m2,
                    "q_h_kpa": bearing.characteristic_resistance_kpa,
                    "q_d_kpa": bearing.design_resistance_kpa,
                    "q_adm_asiento_bruta_kpa": q_settlement_gross,
                    "q_limite_bruta_kpa": q_limit,
                    "Q_limite_base_kn": base_load,
                    "Q_limite_estructura_kn": structure_load,
                    "criterio_gobernante": governing,
                    "perfil_cubre_bulbos": coverage["all_covered"],
                }
            )
            details.append(
                {
                    "foundation": foundation,
                    "bearing": bearing,
                    "coverage": coverage,
                    "settlement": settlement_data,
                }
            )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["B_m", "L_m"]).reset_index(drop=True)
    return frame, details


def sensitivity_analysis(
    soil: SoilProfile,
    foundation: Foundation,
    actions: ActionCase,
    variation_fraction: float = 0.20,
) -> pd.DataFrame:
    if not 0 < variation_fraction < 1:
        raise ValueError("La variacion debe estar entre 0 y 1")
    rows: list[dict[str, float | str]] = []
    variables = {
        "Angulo de rozamiento efectivo": ("phi_effective_deg", soil.phi_effective_deg),
        "Cohesion efectiva": ("c_effective_kpa", soil.c_effective_kpa),
        "Resistencia no drenada": (
            "cu_profile_scale" if soil.cu_profile else "cu0_kpa",
            1.0 if soil.cu_profile else soil.cu0_kpa,
        ),
        "Profundidad del nivel freatico": (
            "water_table_depth_m",
            soil.water_table_depth_m,
        ),
        "Carga vertical": ("vertical_kn", actions.vertical_kn),
    }
    if soil.drainage.value == "drenado":
        variables.pop("Resistencia no drenada")
    else:
        variables.pop("Angulo de rozamiento efectivo")
        variables.pop("Cohesion efectiva")
    for label, (name, base) in variables.items():
        if name.startswith("c_") and base == 0:
            continue
        for multiplier in (1.0 - variation_fraction, 1.0, 1.0 + variation_fraction):
            value = base * multiplier
            try:
                if name == "vertical_kn":
                    varied_actions = replace(actions, vertical_kn=value)
                    varied_soil = soil
                elif name == "cu_profile_scale":
                    varied_soil = replace(
                        soil,
                        cu0_kpa=soil.cu0_kpa * multiplier,
                        cu_profile=tuple(
                            (depth, cu * multiplier)
                            for depth, cu in soil.cu_profile
                        ),
                    )
                    varied_actions = actions
                else:
                    varied_soil = replace(soil, **{name: value})
                    varied_actions = actions
                result = calculate_bearing_capacity(varied_soil, foundation, varied_actions)
            except ValueError:
                continue
            rows.append(
                {
                    "variable": label,
                    "factor": multiplier,
                    "valor": (
                        soil.cohesion_kpa(
                            foundation.width_m, foundation.embedment_m
                        )
                        * multiplier
                        if name == "cu_profile_scale"
                        else value
                    ),
                    "q_d_kpa": result.design_resistance_kpa,
                    "utilizacion": result.utilization,
                }
            )
    return pd.DataFrame(rows)
