from __future__ import annotations

import math

from models.inputs import (
    InfluenceDepthMode,
    SettlementMode,
    SoilLayer,
    SubgradeSoilType,
)


CHARACTERISTIC_POINT_FRACTION = 0.37


def subgrade_modulus_from_ksp30_cte(
    ksp30_mn_m3: float,
    width_m: float,
    length_m: float | None,
    soil_type: SubgradeSoilType,
) -> dict[str, float | str]:
    """Transform ksp30 to ksB and ksBL following CTE DB SE-C E.6-E.8.

    ``length_m=None`` represents a strip footing (the limit L -> infinity).
    Units are preserved: all returned moduli are in MN/m3.
    """
    if not math.isfinite(ksp30_mn_m3) or ksp30_mn_m3 <= 0:
        raise ValueError("Ksp30 debe ser finito y positivo")
    if not math.isfinite(width_m) or width_m <= 0:
        raise ValueError("B debe ser finito y positivo")
    if length_m is not None:
        if not math.isfinite(length_m) or length_m < width_m:
            raise ValueError("Para zapata rectangular se requiere L >= B")

    if soil_type is SubgradeSoilType.COHESIVE:
        scale_factor = 0.30 / width_m
        equation = "E.6"
    elif soil_type is SubgradeSoilType.GRANULAR:
        scale_factor = ((width_m + 0.30) / (2.0 * width_m)) ** 2
        equation = "E.7"
    else:
        raise ValueError("Tipo de terreno no reconocido para el modulo de balasto")

    ksb = ksp30_mn_m3 * scale_factor
    rectangular_factor = 1.0 if length_m is None else 1.0 + width_m / (2.0 * length_m)
    ksbl = ksb * rectangular_factor
    return {
        "ksp30_mn_m3": ksp30_mn_m3,
        "ksb_mn_m3": ksb,
        "ksbl_mn_m3": ksbl,
        "scale_factor": scale_factor,
        "rectangular_factor": rectangular_factor,
        "soil_type": soil_type.value,
        "equation_ksb": equation,
        "equation_ksbl": "E.8 (limite L->infinito)" if length_m is None else "E.8",
    }


def _steinbrenner_phi1(m: float, n: float) -> float:
    if math.isclose(m, 0.0, abs_tol=1e-12):
        term_1 = math.log(math.sqrt(1.0 + n**2) + n)
        term_2 = n * math.log((math.sqrt(1.0 + n**2) + 1.0) / n)
    else:
        term_1 = math.log(
            (math.sqrt(1.0 + m**2 + n**2) + n) / math.sqrt(1.0 + m**2)
        )
        term_2 = n * math.log(
            (math.sqrt(1.0 + m**2 + n**2) + 1.0) / math.sqrt(n**2 + m**2)
        )
    return (term_1 + term_2) / math.pi


def _steinbrenner_phi2(m: float, n: float) -> float:
    if math.isclose(m, 0.0, abs_tol=1e-12):
        return 0.0
    return m / (2.0 * math.pi) * math.atan(
        n / (m * math.sqrt(1.0 + m**2 + n**2))
    )


def _steinbrenner_corner_displacement_m(
    pressure_kpa: float,
    width_m: float,
    length_m: float,
    modulus_kpa: float,
    poisson_ratio: float,
    depth_m: float,
) -> float:
    """Displacement below a loaded rectangle corner (Steinbrenner).

    The internal influence functions are normalized as phi1=F1/2 and
    phi2=F2/2. Therefore, the expression below is identical to the common
    reference form q*B/(2*E)*[(1-nu**2)*F1-(1-nu-2*nu**2)*F2].
    """
    if width_m <= 1e-12 or length_m <= 1e-12:
        return 0.0
    m = depth_m / width_m
    n = length_m / width_m
    bracket = (
        (1.0 - poisson_ratio**2) * _steinbrenner_phi1(m, n)
        - (1.0 - poisson_ratio - 2.0 * poisson_ratio**2)
        * _steinbrenner_phi2(m, n)
    )
    return pressure_kpa * width_m / modulus_kpa * bracket


def _steinbrenner_point_displacement_m(
    pressure_kpa: float,
    width_m: float,
    length_m: float,
    modulus_kpa: float,
    poisson_ratio: float,
    x_m: float,
    y_m: float,
    depth_m: float,
) -> float:
    def signed_corner(a: float, b: float) -> float:
        if math.isclose(a, 0.0, abs_tol=1e-12) or math.isclose(
            b, 0.0, abs_tol=1e-12
        ):
            return 0.0
        value = _steinbrenner_corner_displacement_m(
            pressure_kpa,
            abs(a),
            abs(b),
            modulus_kpa,
            poisson_ratio,
            depth_m,
        )
        return math.copysign(value, a * b)

    x_right = width_m / 2.0 - x_m
    x_left = -width_m / 2.0 - x_m
    y_top = length_m / 2.0 - y_m
    y_bottom = -length_m / 2.0 - y_m
    return (
        signed_corner(x_right, y_top)
        - signed_corner(x_left, y_top)
        - signed_corner(x_right, y_bottom)
        + signed_corner(x_left, y_bottom)
    )


def vertical_stress_ratio_center(
    width_m: float, length_m: float, depth_below_base_m: float
) -> float:
    """Boussinesq vertical-stress increment below the rectangle centre for q=1."""
    if width_m <= 0 or length_m <= 0 or depth_below_base_m < 0:
        raise ValueError("B, L y z deben ser validos")
    if depth_below_base_m <= 1e-12:
        return 1.0
    a = width_m / 2.0
    b = length_m / 2.0
    z = depth_below_base_m
    r1 = math.sqrt(b**2 + z**2)
    r2 = math.sqrt(a**2 + z**2)
    r3 = math.sqrt(a**2 + b**2 + z**2)
    quadrant = (
        math.atan(a * b / (z * r3))
        + a * b * z / r3 * (1.0 / r1**2 + 1.0 / r2**2)
    ) / (2.0 * math.pi)
    return 4.0 * quadrant


def _effective_vertical_stress_kpa(
    layers: list[SoilLayer], depth_m: float, water_table_depth_m: float
) -> float:
    from calculations.layers import vertical_overburden_from_layers

    return vertical_overburden_from_layers(
        layers, depth_m, water_table_depth_m, drained=True
    )


def resolve_influence_depth(
    mode: InfluenceDepthMode,
    width_m: float,
    length_m: float,
    foundation_base_depth_m: float,
    layers: list[SoilLayer],
    water_table_depth_m: float,
    manual_depth_m: float,
    stress_ratio_limit: float = 0.20,
    rigid_layer_depth_m: float | None = None,
    reference_pressure_kpa: float = 100.0,
) -> dict[str, float | str]:
    """Resolve ZI below the base according to the selected engineering criterion."""
    if mode is InfluenceDepthMode.MANUAL:
        depth = manual_depth_m
        basis = "Valor definido por el usuario"
    elif mode is InfluenceDepthMode.TWO_B:
        depth = 2.0 * width_m
        basis = "ZI = 2B"
    elif mode is InfluenceDepthMode.RIGID_LAYER:
        if rigid_layer_depth_m is None or rigid_layer_depth_m <= 0:
            raise ValueError("Debe indicar la profundidad del estrato rigido bajo la base")
        depth = rigid_layer_depth_m
        basis = "ZI hasta el techo del estrato practicamente rigido"
    else:
        if not 0 < stress_ratio_limit < 1:
            raise ValueError("El limite Delta sigma/sigma'v0 debe estar entre 0 y 1")
        if reference_pressure_kpa <= 0:
            raise ValueError("La presion de referencia debe ser positiva")
        maximum = max(layer.bottom_depth_m for layer in layers) - foundation_base_depth_m
        if maximum <= 0:
            raise ValueError("No hay terreno caracterizado bajo la base")
        step = min(0.05, width_m / 40.0)
        depth = step
        found = False
        while depth <= maximum + 1e-9:
            delta_sigma = reference_pressure_kpa * vertical_stress_ratio_center(
                width_m, length_m, depth
            )
            sigma_v0 = _effective_vertical_stress_kpa(
                layers, foundation_base_depth_m + depth, water_table_depth_m
            )
            if sigma_v0 > 0 and delta_sigma / sigma_v0 <= stress_ratio_limit:
                found = True
                break
            depth += step
        if not found:
            raise ValueError(
                "El perfil no alcanza el criterio Delta sigma/sigma'v0; amplie la estratigrafia"
            )
        basis = (
            f"Delta sigma/sigma'v0 <= {stress_ratio_limit:.3f} "
            f"para qref={reference_pressure_kpa:.1f} kPa"
        )
    if depth <= 0:
        raise ValueError("La profundidad de influencia debe ser positiva")
    return {"depth_m": float(depth), "basis": basis}


def _embedment_factor_mayne_poulos(
    width_m: float, length_m: float, embedment_m: float, poisson_ratio: float
) -> float:
    if embedment_m <= 1e-12:
        return 1.0
    equivalent_diameter = math.sqrt(4.0 * width_m * length_m / math.pi)
    return 1.0 - 1.0 / (
        3.5
        * math.exp(1.22 * poisson_ratio - 0.4)
        * (equivalent_diameter / embedment_m + 1.6)
    )


def steinbrenner_layered_settlement(
    pressure_net_kpa: float,
    width_m: float,
    length_m: float,
    foundation_base_depth_m: float,
    layers: list[SoilLayer],
    influence_depth_m: float,
    rigid_foundation: bool = True,
    embedment_correction: bool = True,
    settlement_mode: SettlementMode | None = None,
) -> dict[str, object]:
    """Elastic settlement by layerwise Steinbrenner superposition.

    The pressure is net and the layer depths are measured from ground level.
    """
    if pressure_net_kpa < 0 or width_m <= 0 or length_m < width_m:
        raise ValueError("Se requiere p>=0 y 0<B<=L para Steinbrenner")
    if influence_depth_m <= 0:
        raise ValueError("La profundidad de influencia debe ser positiva")

    from calculations.layers import check_layer_coverage

    coverage = check_layer_coverage(
        layers,
        foundation_base_depth_m,
        foundation_base_depth_m + influence_depth_m,
        "Bulbo de asientos D a D+ZI",
    )
    if not coverage["covered"]:
        raise ValueError("La estratigrafia no cubre completamente el bulbo de asientos")

    mode = settlement_mode or (
        SettlementMode.RIGID_CHARACTERISTIC
        if rigid_foundation
        else SettlementMode.FLEXIBLE_CENTER
    )
    if mode is SettlementMode.RIGID_CHARACTERISTIC:
        x_m = CHARACTERISTIC_POINT_FRACTION * width_m
        y_m = CHARACTERISTIC_POINT_FRACTION * length_m
    elif mode is SettlementMode.FLEXIBLE_CENTER:
        x_m = y_m = 0.0
    else:
        x_m = width_m / 2.0
        y_m = length_m / 2.0
    ordered = sorted(layers, key=lambda item: item.top_depth_m)
    components: list[dict[str, float | str]] = []
    total_m = 0.0
    first_layer = next(
        layer
        for layer in ordered
        if layer.bottom_depth_m > foundation_base_depth_m
        and layer.top_depth_m < foundation_base_depth_m + influence_depth_m
    )
    embedment_factor = (
        _embedment_factor_mayne_poulos(
            width_m,
            length_m,
            foundation_base_depth_m,
            first_layer.poisson_ratio,
        )
        if embedment_correction
        else 1.0
    )

    for layer in ordered:
        top_abs = max(layer.top_depth_m, foundation_base_depth_m)
        bottom_abs = min(
            layer.bottom_depth_m, foundation_base_depth_m + influence_depth_m
        )
        if bottom_abs <= top_abs:
            continue
        top = top_abs - foundation_base_depth_m
        bottom = bottom_abs - foundation_base_depth_m
        modulus_kpa = layer.deformation_modulus_mpa * 1000.0
        top_displacement = _steinbrenner_point_displacement_m(
            pressure_net_kpa,
            width_m,
            length_m,
            modulus_kpa,
            layer.poisson_ratio,
            x_m,
            y_m,
            top,
        )
        bottom_displacement = _steinbrenner_point_displacement_m(
            pressure_net_kpa,
            width_m,
            length_m,
            modulus_kpa,
            layer.poisson_ratio,
            x_m,
            y_m,
            bottom,
        )
        component_m = embedment_factor * (top_displacement - bottom_displacement)
        total_m += component_m
        components.append(
            {
                "layer": layer.name,
                "top_m": top_abs,
                "bottom_m": bottom_abs,
                "settlement_mm": component_m * 1000.0,
            }
        )
    cumulative_mm = 0.0
    settlement_profile = [{"depth_below_base_m": 0.0, "settlement_mm": 0.0}]
    for component in components:
        cumulative_mm += float(component["settlement_mm"])
        settlement_profile.append(
            {
                "depth_below_base_m": float(component["bottom_m"]) - foundation_base_depth_m,
                "settlement_mm": cumulative_mm,
            }
        )
    stress_profile = []
    for index in range(41):
        depth = influence_depth_m * index / 40.0
        stress_profile.append(
            {
                "depth_below_base_m": depth,
                "delta_sigma_kpa": pressure_net_kpa
                * vertical_stress_ratio_center(width_m, length_m, depth),
            }
        )
    return {
        "settlement_mm": total_m * 1000.0,
        "components": components,
        "embedment_factor": embedment_factor,
        "rigid_foundation": mode is SettlementMode.RIGID_CHARACTERISTIC,
        "settlement_mode": mode.value,
        "point_x_m": x_m,
        "point_y_m": y_m,
        "settlement_profile": settlement_profile,
        "stress_profile": stress_profile,
    }


def allowable_net_pressure_steinbrenner(
    allowable_settlement_mm: float,
    width_m: float,
    length_m: float,
    foundation_base_depth_m: float,
    layers: list[SoilLayer],
    influence_depth_m: float,
    rigid_foundation: bool = True,
    embedment_correction: bool = True,
    settlement_mode: SettlementMode | None = None,
) -> dict[str, object]:
    """Invert the linear Steinbrenner model to obtain net allowable pressure."""
    if allowable_settlement_mm <= 0:
        raise ValueError("El asiento admisible debe ser positivo")
    unit = steinbrenner_layered_settlement(
        1.0,
        width_m,
        length_m,
        foundation_base_depth_m,
        layers,
        influence_depth_m,
        rigid_foundation,
        embedment_correction,
        settlement_mode,
    )
    flexibility_mm_per_kpa = float(unit["settlement_mm"])
    if flexibility_mm_per_kpa <= 0:
        raise ValueError("La flexibilidad calculada no es positiva")
    pressure = allowable_settlement_mm / flexibility_mm_per_kpa
    settlement_m = allowable_settlement_mm / 1000.0
    subgrade_modulus_kn_m3 = pressure / settlement_m
    return {
        "allowable_net_pressure_kpa": pressure,
        "flexibility_mm_per_kpa": flexibility_mm_per_kpa,
        "unit_pressure_result": unit,
        "subgrade_modulus_kn_m3": subgrade_modulus_kn_m3,
        "subgrade_modulus_mn_m3": subgrade_modulus_kn_m3 / 1000.0,
    }
