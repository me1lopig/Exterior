from math import inf, nan

from slope_stability_app.models import AnalysisConfig, ProjectData, SlopeGeometry, Soil, SoilLayer, SoilProfile, SweepConfig
from slope_stability_app.services.validation import audit_case_inputs, audit_sweep_inputs


def _valid_case():
    project = ProjectData("Control")
    geometry = SlopeGeometry(8.0, 45.0, 5.0, 16.0)
    profile = SoilProfile(
        (
            SoilLayer(Soil("Superior", 18.0, 20.0, 5.0, 28.0), 6.0),
            SoilLayer(Soil("Inferior", 19.0, 21.0, 10.0, 32.0), 10.0),
        )
    )
    return project, geometry, profile, AnalysisConfig()


def _codes(issues, level="error"):
    return {issue.code for issue in issues if issue.level == level}


def test_valid_two_layer_case_has_no_errors():
    project, geometry, profile, config = _valid_case()
    issues = audit_case_inputs(project, geometry, profile, config)
    assert not _codes(issues)


def test_negative_thickness_is_rejected():
    project, geometry, _, config = _valid_case()
    profile = SoilProfile((SoilLayer(Soil("Invalido", 18.0, 20.0, 5.0, 28.0), -1.0),))
    issues = audit_case_inputs(project, geometry, profile, config)
    assert "layer_1" in _codes(issues)


def test_total_thickness_below_model_depth_reports_gap():
    project, geometry, _, config = _valid_case()
    profile = SoilProfile((SoilLayer(Soil("Corto", 18.0, 20.0, 5.0, 28.0), 15.0),))
    issues = audit_case_inputs(project, geometry, profile, config)
    assert "profile_coverage" in _codes(issues)
    assert any("faltan 1.000 m" in issue.message for issue in issues)


def test_total_thickness_above_model_depth_is_allowed():
    project, geometry, _, config = _valid_case()
    profile = SoilProfile((SoilLayer(Soil("Profundo", 18.0, 20.0, 5.0, 28.0), 20.0),))
    issues = audit_case_inputs(project, geometry, profile, config)
    assert "profile_coverage" not in _codes(issues)


def test_nan_and_infinite_values_are_rejected_by_domain_models():
    invalid_soil = Soil("Invalido", 18.0, 20.0, nan, 30.0)
    try:
        invalid_soil.validate()
    except ValueError as exc:
        assert "finitos" in str(exc)
    else:
        raise AssertionError("NaN no fue rechazado")

    invalid_geometry = SlopeGeometry(8.0, inf, 5.0, 16.0)
    try:
        invalid_geometry.validate()
    except ValueError as exc:
        assert "finitos" in str(exc)
    else:
        raise AssertionError("Infinito no fue rechazado")


def test_saturated_unit_weight_below_dry_is_rejected():
    soil = Soil("Error de pesos", 20.0, 18.0, 5.0, 28.0)
    try:
        soil.validate()
    except ValueError as exc:
        assert "gamma_sat" in str(exc)
    else:
        raise AssertionError("Relacion de pesos no fisica no fue rechazada")


def test_sweep_requires_a_real_range():
    same_angle = SweepConfig(True, 45.0, 45.0, 5, False, 0.0, 0.0, 5)
    assert "sweep" in _codes(audit_sweep_inputs(same_angle, 16.0))


def test_sweep_requires_at_least_one_variable():
    inactive = SweepConfig(False, 35.0, 55.0, 5, False, 0.0, 8.0, 5)
    issues = audit_sweep_inputs(inactive, 16.0)
    assert "sweep" in _codes(issues)


def test_extreme_but_allowed_strength_values_emit_warning():
    project, geometry, _, config = _valid_case()
    profile = SoilProfile((SoilLayer(Soil("Muy resistente", 18.0, 20.0, 120.0, 47.0), 16.0),))
    issues = audit_case_inputs(project, geometry, profile, config)
    warning_codes = _codes(issues, "warning")
    assert "high_cohesion" in warning_codes
    assert "high_friction" in warning_codes


def test_large_sweep_emits_runtime_warning():
    sweep = SweepConfig(True, 30.0, 60.0, 15, True, 0.0, 8.0, 15)
    assert "large_sweep" in _codes(audit_sweep_inputs(sweep, 16.0), "warning")


def test_remaining_domain_guards_reject_invalid_values():
    invalid_objects = [
        Soil("", 18.0, 20.0, 5.0, 28.0),
        Soil("Cohesion negativa", 18.0, 20.0, -1.0, 28.0),
        Soil("Rozamiento invalido", 18.0, 20.0, 5.0, 50.0),
        Soil("Tipo invalido", "18", 20.0, 5.0, 28.0),
    ]
    for soil in invalid_objects:
        try:
            soil.validate()
        except ValueError:
            pass
        else:
            raise AssertionError(f"No se rechazo el suelo invalido: {soil}")

    for geometry in (
        SlopeGeometry(0.0, 45.0, 0.0, 16.0),
        SlopeGeometry(8.0, 45.0, 17.0, 16.0),
        SlopeGeometry(8.0, 45.0, 5.0, 7.0),
    ):
        try:
            geometry.validate()
        except ValueError:
            pass
        else:
            raise AssertionError(f"No se rechazo la geometria invalida: {geometry}")

    for config in (
        AnalysisConfig(slices=5),
        AnalysisConfig(bishop_tolerance=0.0),
        AnalysisConfig(min_depth_ratio=0.8),
    ):
        try:
            config.validate()
        except ValueError:
            pass
        else:
            raise AssertionError(f"No se rechazo la configuracion invalida: {config}")
