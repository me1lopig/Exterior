from __future__ import annotations

import math

from models.inputs import (
    ActionCase,
    Foundation,
    FoundationType,
)
from models.results import CheckResult


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
