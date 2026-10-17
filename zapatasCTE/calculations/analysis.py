from __future__ import annotations

from dataclasses import replace
import math

import numpy as np
import pandas as pd

from calculations.bearing_capacity import calculate_bearing_capacity
from calculations.layers import assess_foundation_bulbs
from calculations.serviceability import (
    allowable_net_pressure_steinbrenner,
    resolve_influence_depth,
    subgrade_modulus_from_ksp30_cte,
)
from calculations.stability import check_contact
from models.inputs import (
    ActionCase,
    DesignSituation,
    DrainageCondition,
    Foundation,
    FoundationType,
    InfluenceDepthMode,
    SettlementMode,
    SoilLayer,
    SoilProfile,
    SubgradeSoilType,
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
    influence_depth_mode: InfluenceDepthMode = InfluenceDepthMode.MANUAL,
    stress_ratio_limit: float = 0.20,
    rigid_layer_depth_m: float | None = None,
    reference_pressure_kpa: float = 100.0,
    settlement_mode: SettlementMode = SettlementMode.RIGID_CHARACTERISTIC,
    embedment_correction: bool = True,
    include_subgrade_modulus: bool = False,
    ksp30_mn_m3: float | None = None,
    subgrade_soil_type: SubgradeSoilType | None = None,
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
                situation=(
                    DesignSituation.TRANSIENT
                    if soil.drainage is DrainageCondition.UNDRAINED
                    else DesignSituation.PERSISTENT
                ),
            )
            try:
                bearing = calculate_bearing_capacity(soil, foundation, centered)
            except ValueError:
                continue
            if foundation.kind is FoundationType.CIRCULAR:
                equivalent_side = math.sqrt(foundation.plan_area_m2)
                settlement_width = equivalent_side
                settlement_length = equivalent_side
            else:
                settlement_width = foundation.width_m
                settlement_length = foundation.length_m
            resolved_depth = resolve_influence_depth(
                influence_depth_mode,
                settlement_width,
                settlement_length,
                foundation.embedment_m,
                layers,
                soil.water_table_depth_m,
                influence_depth_m,
                stress_ratio_limit,
                rigid_layer_depth_m,
                reference_pressure_kpa,
            )
            geometry_influence_depth = float(resolved_depth["depth_m"])
            coverage = assess_foundation_bulbs(
                layers,
                foundation.embedment_m,
                foundation.width_m,
                geometry_influence_depth,
            )
            q0_available = float(bearing.parameters["q0k_disponible_kpa"])
            settlement_data: dict[str, object] | None = None
            q_settlement_net = math.nan
            q_settlement_gross = math.nan
            if (
                coverage["all_covered"]
                and foundation.kind is not FoundationType.STRIP
            ):
                settlement_data = allowable_net_pressure_steinbrenner(
                    allowable_settlement_mm,
                    settlement_width,
                    settlement_length,
                    foundation.embedment_m,
                    layers,
                    geometry_influence_depth,
                    embedment_correction=embedment_correction,
                    settlement_mode=settlement_mode,
                )
                q_settlement_net = float(settlement_data["allowable_net_pressure_kpa"])
                q_settlement_gross = q_settlement_net + q0_available
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
            plate_subgrade: dict[str, float | str] | None = None
            if ksp30_mn_m3 is not None and subgrade_soil_type is not None:
                if foundation.kind is FoundationType.RECTANGULAR:
                    plate_subgrade = subgrade_modulus_from_ksp30_cte(
                        ksp30_mn_m3,
                        foundation.width_m,
                        foundation.length_m,
                        subgrade_soil_type,
                    )
                elif foundation.kind is FoundationType.STRIP:
                    plate_subgrade = subgrade_modulus_from_ksp30_cte(
                        ksp30_mn_m3,
                        foundation.width_m,
                        None,
                        subgrade_soil_type,
                    )
            rows.append(
                {
                    "B_m": foundation.width_m,
                    "L_m": foundation.length_m,
                    "area_m2": foundation.plan_area_m2,
                    "q_h_kpa": bearing.characteristic_resistance_kpa,
                    "q_d_kpa": bearing.design_resistance_kpa,
                    "q0_disponible_kpa": q0_available,
                    "q_adm_asiento_neta_kpa": q_settlement_net,
                    "q_adm_asiento_bruta_kpa": q_settlement_gross,
                    "q_limite_bruta_kpa": q_limit,
                    "Q_limite_base_kn": base_load,
                    "Q_limite_estructura_kn": structure_load,
                    "criterio_gobernante": governing,
                    "perfil_cubre_bulbos": coverage["all_covered"],
                    "ZI_m": geometry_influence_depth,
                    "criterio_ZI": str(resolved_depth["basis"]),
                    "Ks_calculado_MN_m3": (
                        float(settlement_data["subgrade_modulus_mn_m3"])
                        if settlement_data is not None and include_subgrade_modulus
                        else math.nan
                    ),
                    "Ksp30_MN_m3": (
                        float(plate_subgrade["ksp30_mn_m3"])
                        if plate_subgrade is not None else math.nan
                    ),
                    "KsB_CTE_MN_m3": (
                        float(plate_subgrade["ksb_mn_m3"])
                        if plate_subgrade is not None else math.nan
                    ),
                    "KsBL_CTE_MN_m3": (
                        float(plate_subgrade["ksbl_mn_m3"])
                        if plate_subgrade is not None else math.nan
                    ),
                    "tipo_terreno_balasto": (
                        str(plate_subgrade["soil_type"])
                        if plate_subgrade is not None else ""
                    ),
                    "ecuaciones_balasto_CTE": (
                        f"{plate_subgrade['equation_ksb']} + "
                        f"{plate_subgrade['equation_ksbl']}"
                        if plate_subgrade is not None else ""
                    ),
                }
            )
            details.append(
                {
                    "foundation": foundation,
                    "bearing": bearing,
                    "coverage": coverage,
                    "settlement": settlement_data,
                    "plate_subgrade": plate_subgrade,
                    "influence_depth": resolved_depth,
                }
            )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.sort_values(["B_m", "L_m"]).reset_index(drop=True)
    return frame, details
