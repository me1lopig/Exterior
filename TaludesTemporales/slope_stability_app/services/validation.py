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
    upper_thickness: float,
    lower_thickness: float,
) -> list[ValidationIssue]:
    """Devuelve errores bloqueantes y avisos tecnicos sin lanzar excepciones."""
    issues: list[ValidationIssue] = []
    issues.extend(_model_error("geometry", geometry.validate))
    issues.extend(_model_error("upper_soil", profile.upper.validate))
    if profile.lower is not None:
        issues.extend(_model_error("lower_soil", profile.lower.validate))
    issues.extend(_model_error("profile", lambda: profile.validate(geometry.height)))
    issues.extend(_model_error("analysis", config.validate))

    if not isinstance(project.name, str) or not project.name.strip():
        issues.append(ValidationIssue("warning", "project_name", "El proyecto no tiene nombre; el informe usara una denominacion generica."))

    if profile.has_two_soils:
        thicknesses = (upper_thickness, lower_thickness)
        try:
            finite_thicknesses = all(isfinite(value) for value in thicknesses)
        except TypeError:
            finite_thicknesses = False
        if not finite_thicknesses:
            issues.append(ValidationIssue("error", "thickness_finite", "Los espesores deben ser numeros finitos."))
        elif not _is_finite_number(geometry.height):
            pass
        else:
            if upper_thickness <= 0:
                issues.append(ValidationIssue("error", "upper_thickness", "El espesor del suelo superior debe ser mayor que cero."))
            if lower_thickness <= 0:
                issues.append(ValidationIssue("error", "lower_thickness", "El espesor del suelo inferior dentro de H debe ser mayor que cero."))
            total = upper_thickness + lower_thickness
            tolerance = max(1e-6 * geometry.height, 1e-6)
            difference = geometry.height - total
            if difference > tolerance:
                issues.append(
                    ValidationIssue(
                        "error",
                        "thickness_gap",
                        f"La suma de espesores es {total:.3f} m y no cubre H={geometry.height:.3f} m; faltan {difference:.3f} m.",
                    )
                )
            elif difference < -tolerance:
                issues.append(
                    ValidationIssue(
                        "error",
                        "thickness_overlap",
                        f"La suma de espesores es {total:.3f} m y supera H={geometry.height:.3f} m en {-difference:.3f} m.",
                    )
                )
            expected_interface = geometry.height - upper_thickness
            if _is_finite_number(profile.interface_elevation) and abs(profile.interface_elevation - expected_interface) > tolerance:
                issues.append(ValidationIssue("error", "interface_consistency", "La cota del contacto no es coherente con el espesor superior."))
            thin_limit = 0.03 * geometry.height
            if 0 < upper_thickness < thin_limit or 0 < lower_thickness < thin_limit:
                issues.append(
                    ValidationIssue(
                        "warning",
                        "thin_layer",
                        "Hay un estrato con espesor inferior al 3 % de H; aumente las dovelas y compruebe la sensibilidad de la discretizacion.",
                    )
                )
            if (
                isinstance(profile.upper.name, str)
                and isinstance(profile.lower.name, str)
                and profile.upper.name.strip().casefold() == profile.lower.name.strip().casefold()
            ):
                issues.append(ValidationIssue("warning", "duplicate_names", "Los dos estratos tienen el mismo nombre; revise que sus propiedades sean las previstas."))

    for soil in (profile.upper, profile.lower):
        if soil is None:
            continue
        if _is_finite_number(soil.cohesion) and _is_finite_number(soil.friction_deg) and soil.cohesion == 0 and soil.friction_deg == 0:
            issues.append(ValidationIssue("warning", "zero_strength", f"{soil.name} tiene c'=0 y phi'=0: no aporta resistencia cortante."))
        if _is_finite_number(soil.cohesion) and soil.cohesion > 100:
            issues.append(ValidationIssue("warning", "high_cohesion", f"La cohesion de {soil.name} supera 100 kPa; confirme unidades y representatividad."))
        if _is_finite_number(soil.friction_deg) and soil.friction_deg > 45:
            issues.append(ValidationIssue("warning", "high_friction", f"El rozamiento de {soil.name} supera 45 grados; confirme el valor adoptado."))

    if _is_finite_number(geometry.water_elevation) and _is_finite_number(geometry.height) and geometry.water_elevation == geometry.height:
        issues.append(ValidationIssue("warning", "water_at_crest", "El nivel freatico esta en coronacion: compruebe si existe agua exterior o filtracion no hidrostatica no modelada."))
    if isinstance(config.slices, int) and not isinstance(config.slices, bool) and config.slices < 20:
        issues.append(ValidationIssue("warning", "few_slices", "Menos de 20 dovelas puede ser insuficiente; compruebe convergencia aumentando la discretizacion."))
    return _deduplicate(issues)


def audit_sweep_inputs(sweep: SweepConfig, height: float) -> list[ValidationIssue]:
    issues = _model_error("sweep", lambda: sweep.validate(height))
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
