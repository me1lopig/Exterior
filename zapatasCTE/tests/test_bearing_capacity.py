from __future__ import annotations

import math
import unittest

from calculations.bearing_capacity import calculate_bearing_capacity, effective_geometry
from calculations.analysis import admissible_capacity_grid, optimize_geometry
from calculations.stability import check_contact
from models.inputs import (
    ActionCase,
    CuModel,
    DesignSituation,
    DrainageCondition,
    Foundation,
    FoundationType,
    SoilProfile,
    SoilLayer,
    SubgradeSoilType,
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
            soil,
            rectangular(embedment_m=2.0),
            ActionCase("U", 1000.0, situation=DesignSituation.TRANSIENT),
        )
        self.assertAlmostEqual(float(result.parameters["q0k_kpa"]), 38.0)
        self.assertAlmostEqual(
            result.design_resistance_kpa,
            result.terms_kpa["cohesion"] / 3.0
            + result.terms_kpa["sobrecarga"],
        )

    def test_undrained_profile_is_interpolated_at_d_plus_b_over_four(self) -> None:
        soil = SoilProfile(
            drainage=DrainageCondition.UNDRAINED,
            cu_model=CuModel.TABULATED,
            cu_profile=((0.0, 40.0), (4.0, 80.0)),
        )
        self.assertAlmostEqual(soil.cohesion_kpa(2.0, 1.0), 55.0)

    def test_undrained_profile_rejects_extrapolation(self) -> None:
        soil = SoilProfile(
            drainage=DrainageCondition.UNDRAINED,
            cu_model=CuModel.TABULATED,
            cu_profile=((0.0, 40.0), (1.0, 50.0)),
        )
        with self.assertRaisesRegex(ValueError, "no cubre"):
            soil.cohesion_kpa(2.0, 1.0)

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

    def test_depth_factor_dq_uses_exact_nq_over_nc(self) -> None:
        foundation = rectangular(embedment_m=3.0)
        result = calculate_bearing_capacity(
            drained_soil(), foundation, ActionCase("D", 1000.0)
        )
        phi = math.radians(30.0)
        arc = math.atan(min(3.0, 4.0) / 2.0)
        expected = 1.0 + 2.0 * result.factors["Nq"] / result.factors["Nc"] * (
            1.0 - math.sin(phi)
        ) ** 2 * arc
        self.assertAlmostEqual(result.factors["dq"], expected)

    def test_overburden_term_can_be_omitted_without_losing_available_q0(self) -> None:
        result = calculate_bearing_capacity(
            drained_soil(overburden_soil_kpa=36.0),
            rectangular(include_overburden_term=False),
            ActionCase("Q0", 1000.0),
        )
        self.assertEqual(result.terms_kpa["sobrecarga"], 0.0)
        self.assertEqual(result.parameters["q0k_kpa"], 0.0)
        self.assertEqual(result.parameters["q0k_disponible_kpa"], 36.0)

    def test_non_permanent_overburden_is_not_resistant(self) -> None:
        result = calculate_bearing_capacity(
            drained_soil(overburden_soil_kpa=36.0),
            rectangular(
                embedment_m=3.0,
                include_overburden_term=True,
                overburden_permanent=False,
            ),
            ActionCase("Q0", 1000.0),
        )
        self.assertEqual(result.terms_kpa["sobrecarga"], 0.0)
        self.assertEqual(result.parameters["q0k_kpa"], 0.0)
        self.assertEqual(result.factors["dc"], 1.0)
        self.assertEqual(result.factors["dq"], 1.0)

    def test_linear_cte_cu_uses_absolute_depth_and_cap(self) -> None:
        soil = SoilProfile(
            drainage=DrainageCondition.UNDRAINED,
            cu_model=CuModel.LINEAR_CTE,
            cu0_kpa=40.0,
            cu_gradient_kpa_m=10.0,
        )
        self.assertAlmostEqual(soil.cohesion_kpa(2.0, 1.0), 55.0)
        self.assertAlmostEqual(soil.cohesion_kpa(4.0, 10.0), 80.0)

    def test_undrained_slope_reduction_only_applies_to_transient_case(self) -> None:
        soil = SoilProfile(drainage=DrainageCondition.UNDRAINED, cu0_kpa=50.0)
        foundation = rectangular(ground_slope_deg=10.0)
        persistent = calculate_bearing_capacity(
            soil, foundation, ActionCase("P", 1000.0)
        )
        transient = calculate_bearing_capacity(
            soil,
            foundation,
            ActionCase("T", 1000.0, situation=DesignSituation.TRANSIENT),
        )
        self.assertEqual(persistent.terms_kpa["reduccion_talud_no_drenado"], 0.0)
        self.assertLess(transient.terms_kpa["reduccion_talud_no_drenado"], 0.0)

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

    def test_capacity_grid_returns_governing_admissible_load(self) -> None:
        grid, details = admissible_capacity_grid(
            drained_soil(overburden_soil_kpa=18.0),
            rectangular(width_m=1.0, length_m=1.0),
            [SoilLayer("A", 0.0, 10.0, 25.0, poisson_ratio=0.30)],
            1.0,
            1.0,
            1.0,
            1.0,
            0.25,
            25.0,
            4.0,
        )
        self.assertEqual(len(grid), 1)
        self.assertEqual(len(details), 1)
        self.assertTrue(bool(grid.iloc[0]["perfil_cubre_bulbos"]))
        self.assertGreater(float(grid.iloc[0]["Q_limite_base_kn"]), 0.0)

    def test_capacity_grid_propagates_cte_plate_subgrade_moduli(self) -> None:
        layers = [SoilLayer("A", 0.0, 10.0, 20.0)]
        grid, _ = admissible_capacity_grid(
            drained_soil(), rectangular(), layers,
            2.0, 2.0, 4.0, 4.0, 0.5,
            25.0, 4.0,
            ksp30_mn_m3=100.0,
            subgrade_soil_type=SubgradeSoilType.COHESIVE,
        )
        row = grid.iloc[0]
        self.assertAlmostEqual(float(row["KsB_CTE_MN_m3"]), 15.0)
        self.assertAlmostEqual(float(row["KsBL_CTE_MN_m3"]), 18.75)
        self.assertEqual(row["ecuaciones_balasto_CTE"], "E.6 + E.8")


if __name__ == "__main__":
    unittest.main()
