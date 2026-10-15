from __future__ import annotations

import math

from models.inputs import SoilLayer


CHARACTERISTIC_POINT_FRACTION = 0.37


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

    x_m = CHARACTERISTIC_POINT_FRACTION * width_m if rigid_foundation else 0.0
    y_m = CHARACTERISTIC_POINT_FRACTION * length_m if rigid_foundation else 0.0
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
    return {
        "settlement_mm": total_m * 1000.0,
        "components": components,
        "embedment_factor": embedment_factor,
        "rigid_foundation": rigid_foundation,
        "point_x_m": x_m,
        "point_y_m": y_m,
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
    )
    flexibility_mm_per_kpa = float(unit["settlement_mm"])
    if flexibility_mm_per_kpa <= 0:
        raise ValueError("La flexibilidad calculada no es positiva")
    pressure = allowable_settlement_mm / flexibility_mm_per_kpa
    return {
        "allowable_net_pressure_kpa": pressure,
        "flexibility_mm_per_kpa": flexibility_mm_per_kpa,
        "unit_pressure_result": unit,
    }


def spt_allowable_pressure_cte(
    n_spt: float,
    width_eff_m: float,
    embedment_m: float,
    allowable_settlement_mm: float = 25.0,
) -> float:
    """CTE DB-SE-C equations 4.9 and 4.10 for granular soils."""
    if n_spt <= 0 or width_eff_m <= 0:
        raise ValueError("N_SPT y B* deben ser positivos")
    if not 0 < allowable_settlement_mm <= 25:
        raise ValueError("El asiento admisible debe estar en (0, 25] mm")
    if width_eff_m > 5.0:
        raise ValueError("El metodo simplificado CTE no es aplicable para B > 5 m")
    depth_factor = min(1.0 + embedment_m / (3.0 * width_eff_m), 1.3)
    settlement_factor = allowable_settlement_mm / 25.0
    if width_eff_m < 1.2:
        return 12.0 * n_spt * depth_factor * settlement_factor
    width_factor = ((width_eff_m + 0.3) / width_eff_m) ** 2
    return 8.0 * n_spt * width_factor * depth_factor * settlement_factor


def spt_settlement_burland_burbidge(
    q_effective_gross_kpa: float,
    width_m: float,
    length_m: float,
    n_spt_mean: float,
    influence_depth_m: float,
    rigid_layer_depth_below_base_m: float | None = None,
) -> dict[str, float]:
    """Estimate mean settlement with CTE F.19 to F.24.

    The caller supplies the influence depth obtained from the project profile.
    """
    if q_effective_gross_kpa < 0:
        raise ValueError("La presion efectiva bruta no puede ser negativa")
    if width_m <= 0 or length_m < width_m:
        raise ValueError("Se requiere 0 < B <= L")
    if n_spt_mean < 7:
        raise ValueError("F.1.2.2 no se considera aplicable para N_SPT < 7")
    if influence_depth_m <= 0:
        raise ValueError("La profundidad de influencia debe ser positiva")
    ratio = length_m / width_m
    shape_factor = (1.25 * ratio / (ratio + 0.25)) ** 2
    compressibility_index = 1.71 / n_spt_mean**1.4
    rigid_factor = 1.0
    if rigid_layer_depth_below_base_m is not None:
        if not 0 < rigid_layer_depth_below_base_m < influence_depth_m:
            raise ValueError("La capa rigida debe encontrarse dentro de ZI")
        relative = rigid_layer_depth_below_base_m / influence_depth_m
        rigid_factor = relative * (2.0 - relative)
    settlement_mm = (
        rigid_factor
        * shape_factor
        * q_effective_gross_kpa
        * width_m**0.7
        * compressibility_index
    )
    return {
        "settlement_mm": settlement_mm,
        "shape_factor_fs": shape_factor,
        "rigid_layer_factor_fl": rigid_factor,
        "compressibility_index_Ic": compressibility_index,
    }


def elastic_settlement(
    q_net_kpa: float,
    width_m: float,
    deformation_modulus_mpa: float,
    poisson_ratio: float,
    influence_factor: float = 1.0,
) -> float:
    """Elastic half-space settlement, returned in millimetres."""
    if q_net_kpa < 0 or width_m <= 0 or deformation_modulus_mpa <= 0:
        raise ValueError("q_neta, B y E deben ser validos y positivos")
    if not 0 <= poisson_ratio < 0.5 or influence_factor <= 0:
        raise ValueError("nu o el factor de influencia quedan fuera de dominio")
    modulus_kpa = deformation_modulus_mpa * 1000.0
    return (
        q_net_kpa
        * width_m
        * (1.0 - poisson_ratio**2)
        * influence_factor
        / modulus_kpa
        * 1000.0
    )


def layered_settlement_2to1(
    q_net_kpa: float,
    width_m: float,
    length_m: float,
    foundation_base_depth_m: float,
    layers: list[SoilLayer],
    influence_depth_m: float | None = None,
) -> dict[str, object]:
    """Approximate layered settlement by 2:1 stress spread and constrained moduli."""
    if q_net_kpa < 0 or width_m <= 0 or length_m <= 0:
        raise ValueError("Datos de presion o geometria no validos")
    target_depth = influence_depth_m or 2.0 * width_m
    components: list[dict[str, float | str]] = []
    total_m = 0.0
    for layer in layers:
        overlap_top = max(layer.top_depth_m, foundation_base_depth_m)
        overlap_bottom = min(
            layer.bottom_depth_m, foundation_base_depth_m + target_depth
        )
        if overlap_bottom <= overlap_top:
            continue
        thickness = overlap_bottom - overlap_top
        z_mid = (overlap_top + overlap_bottom) / 2.0 - foundation_base_depth_m
        stress = q_net_kpa * width_m * length_m / (
            (width_m + z_mid) * (length_m + z_mid)
        )
        modulus_kpa = layer.deformation_modulus_mpa * 1000.0
        settlement_m = stress * thickness / modulus_kpa
        total_m += settlement_m
        components.append(
            {
                "layer": layer.name,
                "thickness_m": thickness,
                "z_mid_m": z_mid,
                "delta_sigma_kpa": stress,
                "settlement_mm": settlement_m * 1000.0,
            }
        )
    if not components:
        raise ValueError("Ninguna capa cubre la zona de influencia")
    return {"settlement_mm": total_m * 1000.0, "components": components}
