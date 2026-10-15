from __future__ import annotations

import math
import unittest

from calculations.bearing_capacity import calculate_bearing_capacity, effective_geometry
from calculations.analysis import optimize_geometry
from calculations.stability import check_contact
from models.inputs import (
    ActionCase,
    DesignSituation,
    DrainageCondition,
    Foundation,
    FoundationType,
    SoilProfile,
)


def drained_soil(**changes) -> SoilProfile:
    values = dict(
        drainage=DrainageCondition.DRAINED,
        c_effective_kpa=0.0,
        phi_effective_deg=30.0,
        gamma_apparent_kn_m3=18.0,
        gamma_saturated_kn_m3=20.0,
        water_table_depth_m=10.0,
    )
    values.update(changes)
    return SoilProfile(**values)


def rectangular(**changes) -> Foundation:
    values = dict(
        kind=FoundationType.RECTANGULAR,
        width_m=2.0,
        length_m=3.0,
        embedment_m=1.0,
    )
    values.update(changes)
    return Foundation(**values)


class BearingCapacityTests(unittest.TestCase):
    def test_centered_circle_keeps_full_area(self) -> None:
        foundation = Foundation(FoundationType.CIRCULAR, 2.0, 2.0, 1.0)
        self.assertAlmostEqual(foundation.plan_area_m2, math.pi, places=12)
        geometry = effective_geometry(foundation, ActionCase("C", 1000.0))
        self.assertAlmostEqual(geometry.area_m2, math.pi, places=12)
        self.assertAlmostEqual(geometry.width_m, 2.0)
        self.assertFalse(geometry.is_equivalent_rectangle)

    def test_eccentricity_is_independent_of_moment_sign(self) -> None:
        foundation = rectangular()
        positive = effective_geometry(foundation, ActionCase("+", 1000.0, moment_b_knm=200.0))
        negative = effective_geometry(foundation, ActionCase("-", 1000.0, moment_b_knm=-200.0))
        self.assertEqual(positive, negative)
        self.assertAlmostEqual(positive.width_m, 1.6)
        self.assertAlmostEqual(positive.area_m2, 4.8)

    def test_undrained_overburden_uses_total_stress(self) -> None:
        soil = SoilProfile(
            drainage=DrainageCondition.UNDRAINED,
            cu0_kpa=50.0,
            gamma_apparent_kn_m3=18.0,
            gamma_saturated_kn_m3=20.0,
            water_table_depth_m=1.0,
        )
        result = calculate_bearing_capacity(
            soil, rectangular(embedment_m=2.0), ActionCase("U", 1000.0)
        )
        self.assertAlmostEqual(float(result.parameters["q0k_kpa"]), 38.0)

    def test_undrained_horizontal_load_outside_domain_is_rejected(self) -> None:
        soil = SoilProfile(drainage=DrainageCondition.UNDRAINED, cu0_kpa=10.0)
        with self.assertRaisesRegex(ValueError, "H supera"):
            calculate_bearing_capacity(
                soil,
                rectangular(),
                ActionCase("H", 1000.0, horizontal_b_kn=1000.0),
            )

    def test_directional_horizontal_factors_include_both_axes(self) -> None:
        result = calculate_bearing_capacity(
            drained_soil(),
            rectangular(),
            ActionCase("2D", 1000.0, horizontal_b_kn=100.0, horizontal_l_kn=100.0),
        )
        self.assertAlmostEqual(result.factors["iq"], (1 - 0.7 * 0.1) ** 3 * (1 - 0.1))
        self.assertAlmostEqual(result.factors["igamma"], (1 - 0.1) ** 3 * (1 - 0.1))

    def test_extraordinary_uses_gamma_r_two(self) -> None:
        result = calculate_bearing_capacity(
            drained_soil(),
            rectangular(),
            ActionCase("E", 1000.0, situation=DesignSituation.EXTRAORDINARY),
        )
        self.assertEqual(result.factors["gamma_R"], 2.0)
        self.assertAlmostEqual(
            result.design_resistance_kpa,
            result.characteristic_resistance_kpa / 2.0,
        )

    def test_depth_factors_are_disabled_near_slope(self) -> None:
        result = calculate_bearing_capacity(
            drained_soil(),
            rectangular(embedment_m=3.0, near_slope=True),
            ActionCase("S", 1000.0),
        )
        self.assertEqual(result.factors["dc"], 1.0)
        self.assertEqual(result.factors["dq"], 1.0)

    def test_upward_gradient_requires_saturated_base(self) -> None:
        soil = drained_soil(water_table_depth_m=5.0, upward_gradient=0.2)
        with self.assertRaisesRegex(ValueError, "F.17"):
            calculate_bearing_capacity(soil, rectangular(), ActionCase("F", 1000.0))

    def test_circle_contact_uses_circular_kern(self) -> None:
        foundation = Foundation(FoundationType.CIRCULAR, 2.0, 2.0, 1.0)
        _, full = check_contact(
            foundation, ActionCase("C", 1000.0, moment_b_knm=260.0)
        )
        self.assertFalse(full.passes)
        self.assertAlmostEqual(full.utilization, 1.04)

    def test_reference_centered_square_phi30_at_surface(self) -> None:
        result = calculate_bearing_capacity(
            drained_soil(),
            rectangular(length_m=2.0, embedment_m=0.0),
            ActionCase("R", 1.0),
        )
        self.assertAlmostEqual(result.characteristic_resistance_kpa, 190.0, delta=1.0)

    def test_optimizer_recalculates_added_weight_for_each_candidate(self) -> None:
        foundation = rectangular(width_m=1.0, length_m=1.0)
        result = optimize_geometry(
            drained_soil(),
            foundation,
            [ActionCase("P", 100.0)],
            1.0,
            2.0,
            1.0,
            2.0,
            1.0,
            additional_vertical_kpa=20.0,
        )
        one = result.loc[(result["B_m"] == 1.0) & (result["L_m"] == 1.0)].iloc[0]
        two = result.loc[(result["B_m"] == 2.0) & (result["L_m"] == 2.0)].iloc[0]
        self.assertAlmostEqual(one["q_b_max_kpa"], 120.0)
        self.assertAlmostEqual(two["q_b_max_kpa"], 45.0)


if __name__ == "__main__":
    unittest.main()
