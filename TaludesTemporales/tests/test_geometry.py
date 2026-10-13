import numpy as np

from slope_stability_app.calculations.geometry import circle_from_endpoints, ground_elevation, is_admissible
from slope_stability_app.models import SlopeGeometry


def test_ground_profile_matches_crest_face_and_toe():
    geometry = SlopeGeometry(height=10.0, angle_deg=45.0, water_depth=8.0, model_depth=20.0)
    x = np.array([-2.0, 0.0, 5.0, 10.0, 14.0])
    np.testing.assert_allclose(ground_elevation(x, geometry), [10.0, 10.0, 5.0, 0.0, 0.0], atol=1e-10)


def test_circle_passes_through_selected_ground_points():
    geometry = SlopeGeometry(height=8.0, angle_deg=45.0, water_depth=6.0, model_depth=16.0)
    circle = circle_from_endpoints(-2.0, 8.0, 7.0, geometry)
    assert circle is not None
    z = circle.base_elevation(np.array([-2.0, 8.0]))
    np.testing.assert_allclose(z, ground_elevation(np.array([-2.0, 8.0]), geometry), atol=1e-8)
    assert is_admissible(circle, geometry, min_depth_ratio=0.05)


def test_surface_below_model_base_is_rejected():
    geometry = SlopeGeometry(height=8.0, angle_deg=45.0, water_depth=6.0, model_depth=8.0)
    circle = circle_from_endpoints(-2.0, 8.0, 7.0, geometry)
    assert circle is not None
    assert not is_admissible(circle, geometry, min_depth_ratio=0.05)
