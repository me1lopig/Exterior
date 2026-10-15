from __future__ import annotations

import math

from models.inputs import (
    ActionCase,
    DrainageCondition,
    Foundation,
    FoundationType,
    SoilProfile,
    sliding_resistance_factor,
)
from models.results import CheckResult, EffectiveGeometry


def check_sliding(
    soil: SoilProfile,
    foundation: Foundation,
    actions: ActionCase,
    geometry: EffectiveGeometry,
) -> CheckResult:
    """Check local sliding resistance using CTE 4.2.3.1 contact parameters."""
    horizontal = actions.horizontal_kn
    if soil.drainage is DrainageCondition.DRAINED:
        interface_phi = 0.75 * soil.phi_effective_deg
        characteristic = actions.vertical_kn * math.tan(math.radians(interface_phi))
        basis = "CTE 4.2.3.1: a'=0 y delta'=3/4 phi'"
    else:
        characteristic = geometry.area_m2 * soil.cohesion_kpa(foundation.width_m)
        basis = "CTE 4.2.3.1: delta=0 y adhesion de contacto igual a cu"
    gamma_r = sliding_resistance_factor(actions.situation)
    design = characteristic / gamma_r
    utilization = horizontal / design if design > 0 else math.inf
    warnings: list[str] = []
    if horizontal == 0:
        utilization = 0.0
    warnings.append("No se considera empuje pasivo ni rozamiento de elementos auxiliares.")
    return CheckResult(
        name="Deslizamiento local",
        demand=horizontal,
        resistance=design,
        utilization=utilization,
        passes=utilization <= 1.0,
        units="kN" if foundation.kind.value != "corrida" else "kN/m",
        basis=f"{basis}; gamma_R={gamma_r:.2f}",
        warnings=tuple(warnings),
    )


def check_contact(foundation: Foundation, actions: ActionCase) -> tuple[CheckResult, CheckResult]:
    e_b = abs(actions.moment_b_knm) / actions.vertical_kn
    e_l = abs(actions.moment_l_knm) / actions.vertical_kn
    if foundation.kind is FoundationType.CIRCULAR:
        eccentricity = math.hypot(e_b, e_l)
        inside_base_ratio = 2.0 * eccentricity / foundation.width_m
        kern_ratio = 8.0 * eccentricity / foundation.width_m
        kern_basis = "Nucleo central circular: e <= D/8"
    else:
        inside_base_ratio = max(
            2.0 * e_b / foundation.width_m,
            2.0 * e_l / foundation.length_m,
        )
        kern_ratio = max(
            6.0 * e_b / foundation.width_m,
            6.0 * e_l / foundation.length_m,
        )
        kern_basis = "Nucleo central rectangular: eB <= B/6 y eL <= L/6"
    inside = CheckResult(
        name="Resultante dentro de la base",
        demand=inside_base_ratio,
        resistance=1.0,
        utilization=inside_base_ratio,
        passes=inside_base_ratio < 1.0,
        units="adimensional",
        basis="eB < B/2 y eL < L/2",
    )
    full_contact = CheckResult(
        name="Contacto completo",
        demand=kern_ratio,
        resistance=1.0,
        utilization=kern_ratio,
        passes=kern_ratio <= 1.0,
        units="adimensional",
        basis=kern_basis,
        warnings=(
            "No es una comprobacion CTE de vuelco; informa sobre perdida de contacto elastico.",
        ),
    )
    return inside, full_contact
