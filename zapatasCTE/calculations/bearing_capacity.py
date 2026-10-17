from __future__ import annotations

import math

from models.inputs import (
    ActionCase,
    DesignSituation,
    DrainageCondition,
    Foundation,
    FoundationType,
    SoilProfile,
    bearing_resistance_factor,
)
from models.results import BearingCapacityResult, EffectiveGeometry


def effective_geometry(foundation: Foundation, actions: ActionCase) -> EffectiveGeometry:
    """Return the CTE 4.3.1.3 effective footing geometry.

    Eccentricities are magnitudes because the maximum cobarycentric section is
    independent of the moment sign. Circular footings with eccentric load are
    converted to a rectangle preserving area and inertia about the moment axis.
    """
    e_b = abs(actions.moment_b_knm) / actions.vertical_kn
    e_l = abs(actions.moment_l_knm) / actions.vertical_kn

    if foundation.kind is FoundationType.CIRCULAR:
        diameter = foundation.width_m
        resultant_e = math.hypot(e_b, e_l)
        if resultant_e <= 1e-12:
            return EffectiveGeometry(
                width_m=diameter,
                length_m=diameter,
                area_m2=math.pi * diameter**2 / 4.0,
                eccentricity_b_m=0.0,
                eccentricity_l_m=0.0,
                note="Zapata circular centrada; se conserva la seccion real.",
            )
        equivalent_width = math.sqrt(3.0) * diameter / 2.0
        equivalent_length = math.pi * diameter / (2.0 * math.sqrt(3.0))
        width_eff = equivalent_width - 2.0 * resultant_e
        if width_eff <= 0:
            raise ValueError("La resultante queda fuera de la seccion circular equivalente")
        return EffectiveGeometry(
            width_m=width_eff,
            length_m=equivalent_length,
            area_m2=width_eff * equivalent_length,
            eccentricity_b_m=resultant_e,
            eccentricity_l_m=0.0,
            is_equivalent_rectangle=True,
            note=(
                "Equivalencia rectangular de zapata circular excentrica conservando "
                "area e inercia de la seccion real antes de reducir por excentricidad."
            ),
        )

    if foundation.kind is FoundationType.STRIP:
        width_eff = foundation.width_m - 2.0 * e_b
        if width_eff <= 0:
            raise ValueError("La resultante queda fuera del ancho de la zapata corrida")
        if e_l > 1e-12 or abs(actions.horizontal_l_kn) > 1e-12:
            raise ValueError("La zapata corrida solo admite acciones por metro en la direccion B")
        return EffectiveGeometry(
            width_m=width_eff,
            length_m=1.0,
            area_m2=width_eff,
            eccentricity_b_m=e_b,
            eccentricity_l_m=0.0,
            note="Calculo por franja de un metro; acciones expresadas por metro lineal.",
        )

    width_eff = foundation.width_m - 2.0 * e_b
    length_eff = foundation.length_m - 2.0 * e_l
    if width_eff <= 0 or length_eff <= 0:
        raise ValueError("La resultante queda fuera de la base de la zapata")
    swapped = width_eff > length_eff
    width, length = (length_eff, width_eff) if swapped else (width_eff, length_eff)
    return EffectiveGeometry(
        width_m=width,
        length_m=length,
        area_m2=width_eff * length_eff,
        eccentricity_b_m=e_b,
        eccentricity_l_m=e_l,
        axes_swapped=swapped,
        note="Dimensiones efectivas CTE: B*=B-2|eB| y L*=L-2|eL|.",
    )


def _overburden_kpa(soil: SoilProfile, foundation: Foundation) -> float:
    if soil.overburden_soil_kpa is not None:
        return soil.overburden_soil_kpa + foundation.surcharge_kpa
    depth = foundation.embedment_m
    water = soil.water_table_depth_m
    above = min(depth, water)
    below = max(depth - water, 0.0)
    if soil.drainage is DrainageCondition.UNDRAINED:
        soil_weight = (
            above * soil.gamma_apparent_kn_m3
            + below * soil.gamma_saturated_kn_m3
        )
    else:
        soil_weight = (
            above * soil.gamma_apparent_kn_m3
            + below * soil.gamma_submerged_kn_m3
        )
    return soil_weight + foundation.surcharge_kpa


def _wedge_unit_weight(
    soil: SoilProfile, foundation: Foundation, width_eff_m: float
) -> float:
    if soil.drainage is DrainageCondition.UNDRAINED:
        return soil.gamma_saturated_kn_m3
    if soil.upward_gradient > 0:
        if soil.water_table_depth_m > foundation.embedment_m:
            raise ValueError(
                "La expresion F.17 requiere la base dentro de la zona saturada; "
                "revise nivel freatico y gradiente."
            )
        gamma = soil.gamma_submerged_kn_m3 - soil.upward_gradient * soil.gamma_water_kn_m3
        if gamma <= 0:
            raise ValueError(
                "El gradiente ascendente anula el peso sumergido; se requiere "
                "comprobacion especifica de sifonamiento o levantamiento."
            )
        return gamma
    distance_below_base = soil.water_table_depth_m - foundation.embedment_m
    if distance_below_base <= 0:
        return soil.gamma_submerged_kn_m3
    if distance_below_base >= width_eff_m:
        return soil.gamma_apparent_kn_m3
    ratio = distance_below_base / width_eff_m
    return soil.gamma_submerged_kn_m3 + ratio * (
        soil.gamma_apparent_kn_m3 - soil.gamma_submerged_kn_m3
    )


def _capacity_factors(phi_rad: float) -> tuple[float, float, float]:
    if math.isclose(phi_rad, 0.0, abs_tol=1e-12):
        return 1.0, 5.14, 0.0
    nq = ((1.0 + math.sin(phi_rad)) / (1.0 - math.sin(phi_rad))) * math.exp(
        math.pi * math.tan(phi_rad)
    )
    nc = (nq - 1.0) / math.tan(phi_rad)
    ngamma = 1.5 * (nq - 1.0) * math.tan(phi_rad)
    return nq, nc, ngamma


def _shape_factors(
    foundation: Foundation, geometry: EffectiveGeometry, phi_rad: float
) -> tuple[float, float, float]:
    if foundation.kind is FoundationType.CIRCULAR and not geometry.is_equivalent_rectangle:
        return 1.20, 1.20, 0.60
    if foundation.kind is FoundationType.STRIP:
        return 1.0, 1.0, 1.0
    ratio = geometry.width_m / geometry.length_m
    return (
        1.0 + 0.2 * ratio,
        1.0 + 1.5 * math.tan(phi_rad) * ratio if phi_rad > 0 else 1.0,
        1.0 - 0.3 * ratio,
    )


def _depth_factors(
    soil: SoilProfile,
    foundation: Foundation,
    width_eff_m: float,
    phi_rad: float,
    nq: float,
    nc: float,
) -> tuple[float, float, float, tuple[str, ...]]:
    reasons: list[str] = []
    if not foundation.include_depth_factors:
        reasons.append("desactivados por el usuario")
    if foundation.embedment_m < 2.0:
        reasons.append("D < 2 m")
    if foundation.near_slope:
        reasons.append("cimentacion proxima a talud")
    if not foundation.overburden_permanent:
        reasons.append("no se garantiza la permanencia del terreno sobre la base")
    if foundation.shrinkage_cracks:
        reasons.append("posibles grietas de retraccion en terreno arcilloso")
    if reasons:
        return 1.0, 1.0, 1.0, tuple(reasons)
    depth = min(foundation.embedment_m, 2.0 * width_eff_m)
    arc = math.atan(depth / width_eff_m)
    dc = 1.0 + 0.34 * arc
    dq = (
        1.0 + 2.0 * nq / nc * (1.0 - math.sin(phi_rad)) ** 2 * arc
        if phi_rad > 0
        else 1.0
    )
    return dc, dq, 1.0, ()


def _directional_horizontal(
    foundation: Foundation, geometry: EffectiveGeometry, actions: ActionCase
) -> tuple[float, float]:
    hb = abs(actions.horizontal_b_kn)
    hl = abs(actions.horizontal_l_kn)
    if foundation.kind is FoundationType.CIRCULAR:
        return actions.horizontal_kn, 0.0
    if geometry.axes_swapped:
        return hl, hb
    return hb, hl


def _inclination_factors(
    soil: SoilProfile,
    foundation: Foundation,
    geometry: EffectiveGeometry,
    actions: ActionCase,
    cohesion_kpa: float,
    phi_rad: float,
    nc: float,
) -> tuple[float, float, float]:
    horizontal = actions.horizontal_kn
    if horizontal < 0.10 * actions.vertical_kn:
        return 1.0, 1.0, 1.0
    hb, hl = _directional_horizontal(foundation, geometry, actions)
    if phi_rad > 0 and foundation.base_adhesion_kpa > 0:
        tan_delta = horizontal / actions.vertical_kn
        tan_delta_star = tan_delta / (
            1.0
            + geometry.area_m2
            * foundation.base_adhesion_kpa
            / (actions.vertical_kn * math.tan(phi_rad))
        )
        scale = tan_delta_star / tan_delta
        hb *= scale
        hl *= scale
    tan_b = hb / actions.vertical_kn
    tan_l = hl / actions.vertical_kn
    iq = (1.0 - 0.7 * tan_b) ** 3 * (1.0 - tan_l)
    igamma = (1.0 - tan_b) ** 3 * (1.0 - tan_l)
    if phi_rad > 0:
        ic = iq - (1.0 - iq) / (nc * math.tan(phi_rad))
    else:
        shear_ratio = horizontal / (geometry.area_m2 * cohesion_kpa)
        if shear_ratio > 1.0:
            raise ValueError(
                "H supera A'·cu; los factores de inclinacion no son aplicables."
            )
        ic = 0.5 * (1.0 + math.sqrt(1.0 - shear_ratio))
    if min(ic, iq, igamma) < 0:
        raise ValueError(
            "La inclinacion de la resultante produce factores negativos; "
            "el caso queda fuera del dominio del modelo de hundimiento."
        )
    return ic, iq, igamma


def _slope_factors(
    drainage: DrainageCondition, beta_rad: float, phi_rad: float
) -> tuple[float, float, float]:
    if drainage is DrainageCondition.UNDRAINED or beta_rad <= math.radians(5.0):
        return 1.0, 1.0, 1.0
    return (
        math.exp(-2.0 * beta_rad * math.tan(phi_rad)),
        1.0 - math.sin(2.0 * beta_rad),
        1.0 - math.sin(2.0 * beta_rad),
    )


def calculate_bearing_capacity(
    soil: SoilProfile, foundation: Foundation, actions: ActionCase
) -> BearingCapacityResult:
    geometry = effective_geometry(foundation, actions)
    warnings: list[str] = []
    if geometry.note:
        warnings.append(geometry.note)
    if foundation.surcharge_kpa > 0:
        warnings.append(
            "La sobrecarga exterior solo es resistente si se mantiene durante la vida util."
        )
    if not foundation.include_overburden_term:
        warnings.append("Se omite prudentemente el termino resistente de sobrecarga q0.")
    elif not foundation.overburden_permanent:
        warnings.append(
            "Se anula q0 porque no se garantiza la permanencia del terreno sobre la base."
        )

    phi_rad = (
        math.radians(soil.phi_effective_deg)
        if soil.drainage is DrainageCondition.DRAINED
        else 0.0
    )
    cohesion = soil.cohesion_kpa(foundation.width_m, foundation.embedment_m)
    overburden_available = _overburden_kpa(soil, foundation)
    overburden_resistant = (
        overburden_available
        if foundation.include_overburden_term and foundation.overburden_permanent
        else 0.0
    )
    gamma_wedge = _wedge_unit_weight(soil, foundation, geometry.width_m)
    nq, nc, ngamma = _capacity_factors(phi_rad)
    sc, sq, sgamma = _shape_factors(foundation, geometry, phi_rad)
    dc, dq, dgamma, depth_factor_reasons = _depth_factors(
        soil, foundation, geometry.width_m, phi_rad, nq, nc
    )
    if depth_factor_reasons:
        warnings.append(
            "Factores de profundidad anulados: " + "; ".join(depth_factor_reasons) + "."
        )
    ic, iq, igamma = _inclination_factors(
        soil, foundation, geometry, actions, cohesion, phi_rad, nc
    )
    beta_rad = math.radians(foundation.ground_slope_deg)
    tc, tq, tgamma = _slope_factors(soil.drainage, beta_rad, phi_rad)

    term_c = cohesion * nc * sc * dc * ic * tc
    term_q = overburden_resistant * nq * sq * dq * iq * tq
    term_gamma = (
        0.5
        * gamma_wedge
        * geometry.width_m
        * ngamma
        * sgamma
        * dgamma
        * igamma
        * tgamma
    )
    undrained_slope_reduction = 0.0
    if (
        soil.drainage is DrainageCondition.UNDRAINED
        and actions.situation is DesignSituation.TRANSIENT
        and beta_rad > 0
    ):
        undrained_slope_reduction = 2.0 * beta_rad * cohesion
    elif soil.drainage is DrainageCondition.UNDRAINED and beta_rad > 0:
        warnings.append(
            "No se aplica 2*beta*cu: el CTE lo vincula a situaciones transitorias sin drenaje."
        )
    qh = term_c + term_q + term_gamma - undrained_slope_reduction
    if qh <= 0:
        raise ValueError("La resistencia caracteristica resultante no es positiva")

    gamma_r = bearing_resistance_factor(actions.situation)
    if soil.drainage is DrainageCondition.UNDRAINED:
        q_design = (
            term_c / gamma_r
            + term_q
            + term_gamma
            - undrained_slope_reduction
        )
        gamma_application = "solo termino de cohesion, CTE F.1.1.2.5"
    else:
        q_design = qh / gamma_r
        gamma_application = "resistencia caracteristica total"
    if q_design <= 0:
        raise ValueError("La resistencia de calculo resultante no es positiva")

    pressure_gross = actions.vertical_kn / geometry.area_m2
    pressure_net = pressure_gross - overburden_available
    utilization = pressure_gross / q_design
    if beta_rad > phi_rad / 2.0 and soil.drainage is DrainageCondition.DRAINED:
        warnings.append(
            "beta > phi'/2: el CTE exige un estudio especifico de estabilidad global."
        )
    if soil.upward_gradient > 0:
        warnings.append(
            "Existe flujo ascendente: comprobar adicionalmente sifonamiento y levantamiento."
        )

    factors = {
        "Nq": nq,
        "Nc": nc,
        "Ngamma": ngamma,
        "sc": sc,
        "sq": sq,
        "sgamma": sgamma,
        "dc": dc,
        "dq": dq,
        "dgamma": dgamma,
        "ic": ic,
        "iq": iq,
        "igamma": igamma,
        "tc": tc,
        "tq": tq,
        "tgamma": tgamma,
        "gamma_R": gamma_r,
    }
    return BearingCapacityResult(
        action_name=actions.name,
        geometry=geometry,
        pressure_gross_kpa=pressure_gross,
        pressure_net_kpa=pressure_net,
        characteristic_resistance_kpa=qh,
        design_resistance_kpa=q_design,
        utilization=utilization,
        passes=utilization <= 1.0,
        terms_kpa={
            "cohesion": term_c,
            "sobrecarga": term_q,
            "peso_especifico": term_gamma,
            "reduccion_talud_no_drenado": -undrained_slope_reduction,
        },
        factors=factors,
        parameters={
        "regimen": soil.drainage.value,
            "c_k_kpa": cohesion,
            "phi_k_deg": math.degrees(phi_rad),
            "q0k_disponible_kpa": overburden_available,
            "q0k_kpa": overburden_resistant,
            "gamma_k_kn_m3": gamma_wedge,
            "aplicacion_gamma_R": gamma_application,
            "factores_profundidad": (
                "aplicados" if not depth_factor_reasons else "anulados"
            ),
            "motivo_factores_profundidad": "; ".join(depth_factor_reasons) or "cumple condiciones",
        },
        warnings=tuple(warnings),
    )
