from __future__ import annotations

from dataclasses import replace
import math

import numpy as np
import pandas as pd

from calculations.bearing_capacity import calculate_bearing_capacity
from calculations.stability import check_contact, check_sliding
from models.inputs import ActionCase, Foundation, FoundationType, SoilProfile


def evaluate_cases(
    soil: SoilProfile, foundation: Foundation, actions: list[ActionCase]
) -> tuple[pd.DataFrame, list[dict[str, object]]]:
    rows: list[dict[str, object]] = []
    details: list[dict[str, object]] = []
    for action in actions:
        bearing = calculate_bearing_capacity(soil, foundation, action)
        sliding = check_sliding(soil, foundation, action, bearing.geometry)
        inside, contact = check_contact(foundation, action)
        overall = bearing.passes and sliding.passes and inside.passes
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
                "util_deslizamiento": sliding.utilization,
                "contacto_completo": contact.passes,
                "cumple_geotecnia": overall,
            }
        )
        details.append(
            {
                "actions": action,
                "bearing": bearing,
                "sliding": sliding,
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
                    "util_d_max": float(table["util_deslizamiento"].max()),
                    "cumple": bool(table["cumple_geotecnia"].all()),
                }
            )
    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(["cumple", "area_m2"], ascending=[False, True]).reset_index(drop=True)


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
        "phi_effective_deg": soil.phi_effective_deg,
        "c_effective_kpa": soil.c_effective_kpa,
        "cu0_kpa": soil.cu0_kpa,
        "water_table_depth_m": soil.water_table_depth_m,
        "vertical_kn": actions.vertical_kn,
    }
    if soil.drainage.value == "drenado":
        variables.pop("cu0_kpa")
    else:
        variables.pop("phi_effective_deg")
        variables.pop("c_effective_kpa")
    for name, base in variables.items():
        if name.startswith("c_") and base == 0:
            continue
        for multiplier in (1.0 - variation_fraction, 1.0, 1.0 + variation_fraction):
            value = base * multiplier
            try:
                if name == "vertical_kn":
                    varied_actions = replace(actions, vertical_kn=value)
                    varied_soil = soil
                else:
                    varied_soil = replace(soil, **{name: value})
                    varied_actions = actions
                result = calculate_bearing_capacity(varied_soil, foundation, varied_actions)
            except ValueError:
                continue
            rows.append(
                {
                    "variable": name,
                    "factor": multiplier,
                    "valor": value,
                    "q_d_kpa": result.design_resistance_kpa,
                    "utilizacion": result.utilization,
                }
            )
    return pd.DataFrame(rows)
