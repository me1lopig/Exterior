"""Auditoria defensiva de entradas antes de ejecutar calculos costosos."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Literal

from slope_stability_app.models import AnalysisConfig, ProjectData, SlopeGeometry, SoilProfile, SweepConfig


@dataclass(frozen=True)
class ValidationIssue:
    level: Literal["error", "warning"]
    code: str
    message: str


def _is_finite_number(value) -> bool:
    try:
        return isfinite(value)
    except TypeError:
        return False


def _model_error(code: str, callback) -> list[ValidationIssue]:
    try:
        callback()
    except (TypeError, ValueError) as exc:
        return [ValidationIssue("error", code, str(exc))]
    return []


def audit_case_inputs(
    project: ProjectData,
    geometry: SlopeGeometry,
    profile: SoilProfile,
    config: AnalysisConfig,
) -> list[ValidationIssue]:
    """Devuelve errores bloqueantes y avisos tecnicos sin lanzar excepciones."""
    issues: list[ValidationIssue] = []
    issues.extend(_model_error("geometry", geometry.validate))
    for index, layer in enumerate(profile.layers, start=1):
        issues.extend(_model_error(f"layer_{index}", layer.validate))

    thicknesses = tuple(layer.thickness for layer in profile.layers)
    finite_thicknesses = bool(thicknesses) and all(_is_finite_number(value) for value in thicknesses)
    if not profile.layers:
        issues.append(ValidationIssue("error", "empty_profile", "Debe definir al menos una capa de suelo."))
    elif not finite_thicknesses:
        issues.append(ValidationIssue("error", "thickness_finite", "Todos los espesores deben ser numeros finitos."))
    elif _is_finite_number(geometry.model_depth):
        missing = geometry.model_depth - profile.total_thickness
        tolerance = max(1e-6 * geometry.model_depth, 1e-6)
        if missing > tolerance:
            issues.append(
                ValidationIssue(
                    "error",
                    "profile_coverage",
                    f"La suma de espesores es {profile.total_thickness:.3f} m y no cubre la profundidad "
                    f"del modelo ({geometry.model_depth:.3f} m); faltan {missing:.3f} m.",
                )
            )
        thin_limit = 0.03 * geometry.height
        if any(0 < value < thin_limit for value in thicknesses):
            issues.append(
                ValidationIssue(
                    "warning",
                    "thin_layer",
                    "Hay una capa con espesor inferior al 3 % de H; aumente las dovelas y compruebe la discretizacion.",
                )
            )

    issues.extend(_model_error("profile", lambda: profile.validate(geometry.model_depth)))
    issues.extend(_model_error("analysis", config.validate))

    if not isinstance(project.name, str) or not project.name.strip():
        issues.append(ValidationIssue("warning", "project_name", "El proyecto no tiene nombre; el informe usara una denominacion generica."))

    names = [layer.soil.name.strip().casefold() for layer in profile.layers if isinstance(layer.soil.name, str)]
    if len(names) != len(set(names)):
        issues.append(ValidationIssue("warning", "duplicate_names", "Hay capas con el mismo nombre; revise su identificacion y propiedades."))

    for layer in profile.layers:
        soil = layer.soil
        if _is_finite_number(soil.cohesion) and _is_finite_number(soil.friction_deg) and soil.cohesion == 0 and soil.friction_deg == 0:
            issues.append(ValidationIssue("warning", "zero_strength", f"{soil.name} tiene c'=0 y phi'=0: no aporta resistencia cortante."))
        if _is_finite_number(soil.cohesion) and soil.cohesion > 100:
            issues.append(ValidationIssue("warning", "high_cohesion", f"La cohesion de {soil.name} supera 100 kPa; confirme unidades y representatividad."))
        if _is_finite_number(soil.friction_deg) and soil.friction_deg > 45:
            issues.append(ValidationIssue("warning", "high_friction", f"El rozamiento de {soil.name} supera 45 grados; confirme el valor adoptado."))

    if _is_finite_number(geometry.water_depth) and geometry.water_depth == 0:
        issues.append(ValidationIssue("warning", "water_at_crest", "El nivel freatico esta en coronacion: compruebe si existe agua exterior o filtracion no hidrostatica no modelada."))
    if isinstance(config.slices, int) and not isinstance(config.slices, bool) and config.slices < 20:
        issues.append(ValidationIssue("warning", "few_slices", "Menos de 20 dovelas puede ser insuficiente; compruebe convergencia aumentando la discretizacion."))
    return _deduplicate(issues)


def audit_sweep_inputs(sweep: SweepConfig, model_depth: float) -> list[ValidationIssue]:
    issues = _model_error("sweep", lambda: sweep.validate(model_depth))
    valid_angle_steps = isinstance(sweep.angle_steps, int) and not isinstance(sweep.angle_steps, bool)
    valid_water_steps = isinstance(sweep.water_steps, int) and not isinstance(sweep.water_steps, bool)
    cases = (sweep.angle_steps if sweep.vary_angle and valid_angle_steps else 1) * (
        sweep.water_steps if sweep.vary_water and valid_water_steps else 1
    )
    if cases > 100:
        issues.append(ValidationIssue("warning", "large_sweep", f"El barrido contiene {cases} casos y puede tardar varios minutos."))
    return _deduplicate(issues)


def _deduplicate(issues: list[ValidationIssue]) -> list[ValidationIssue]:
    unique: list[ValidationIssue] = []
    seen: set[tuple[str, str]] = set()
    for issue in issues:
        key = (issue.level, issue.message)
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return unique
