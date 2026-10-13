from math import cos, isclose, radians, sin, tan

from slope_stability_app.calculations import search_critical_surfaces
from slope_stability_app.calculations.stability import SliceData, bishop_simplified, fellenius
from slope_stability_app.models import AnalysisConfig, SlopeGeometry, Soil, SoilProfile


def _slice(alpha_deg: float = 25.0, pore_pressure: float = 12.0) -> SliceData:
    width = 2.0
    return SliceData(
        index=1,
        x_mid=0.0,
        width=width,
        base_elevation=-1.0,
        top_elevation=4.0,
        base_angle_deg=alpha_deg,
        base_length=width / cos(radians(alpha_deg)),
        weight=180.0,
        pore_pressure=pore_pressure,
        pore_force=pore_pressure * width / cos(radians(alpha_deg)),
        cohesion=8.0,
        friction_deg=28.0,
        soil_name="Control",
    )


def test_fellenius_matches_hand_calculation_for_one_slice():
    item = _slice()
    alpha = radians(item.base_angle_deg)
    expected = (
        item.cohesion * item.base_length
        + (item.weight * cos(alpha) - item.pore_force) * tan(radians(item.friction_deg))
    ) / (item.weight * sin(alpha))
    assert isclose(fellenius((item,)).factor_of_safety, expected, rel_tol=1e-12)


def test_bishop_converges_to_positive_value():
    config = AnalysisConfig()
    result = bishop_simplified((_slice(18.0), _slice(30.0)), config)
    assert result.converged
    assert result.factor_of_safety > 0
    assert result.iterations < config.bishop_max_iterations


def test_higher_water_table_reduces_critical_factor():
    soil = Soil("Suelo", 18.0, 20.0, 5.0, 28.0)
    profile = SoilProfile(soil)
    config = AnalysisConfig(slices=20, search_level="Rapida")
    dry = search_critical_surfaces(SlopeGeometry(8.0, 45.0, 0.0), profile, config)
    wet = search_critical_surfaces(SlopeGeometry(8.0, 45.0, 7.0), profile, config)
    assert wet.bishop.factor_of_safety < dry.bishop.factor_of_safety
    assert wet.fellenius.factor_of_safety < dry.fellenius.factor_of_safety


def test_stronger_lower_layer_does_not_weaken_same_search_domain():
    upper = Soil("Superior", 18.0, 20.0, 2.0, 24.0)
    weak = SoilProfile(upper)
    strong = SoilProfile(upper, Soil("Inferior", 19.0, 21.0, 25.0, 36.0), interface_elevation=4.0)
    geometry = SlopeGeometry(8.0, 45.0, 2.0)
    config = AnalysisConfig(slices=20, search_level="Rapida")
    homogeneous = search_critical_surfaces(geometry, weak, config)
    layered = search_critical_surfaces(geometry, strong, config)
    assert layered.bishop.factor_of_safety >= homogeneous.bishop.factor_of_safety


def test_layer_thicknesses_are_measured_from_crest():
    upper = Soil("Superior", 18.0, 20.0, 5.0, 28.0)
    lower = Soil("Inferior", 19.0, 21.0, 10.0, 32.0)
    # H=8 m y espesor superior=3 m implican contacto en z=5 m.
    profile = SoilProfile(upper, lower, interface_elevation=5.0)
    assert profile.upper_thickness(8.0) == 3.0
    assert profile.lower_thickness_within_slope(8.0) == 5.0
