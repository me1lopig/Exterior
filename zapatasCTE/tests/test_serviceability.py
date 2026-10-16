from __future__ import annotations

import math
import unittest

from calculations.serviceability import (
    _steinbrenner_corner_displacement_m,
    allowable_net_pressure_steinbrenner,
    resolve_influence_depth,
    steinbrenner_layered_settlement,
    subgrade_modulus_from_ksp30_cte,
    vertical_stress_ratio_center,
)
from calculations.layers import (
    assess_foundation_bulbs,
    check_layer_coverage,
    vertical_overburden_from_layers,
)
from models.inputs import (
    InfluenceDepthMode,
    SettlementMode,
    SoilLayer,
    SubgradeSoilType,
)


class ServiceabilityTests(unittest.TestCase):
    def test_steinbrenner_matches_classic_f1_f2_expression(self) -> None:
        q_kpa = 137.0
        width_m = 2.4
        length_m = 4.1
        modulus_kpa = 28_000.0
        poisson_ratio = 0.32
        depth_m = 1.7

        m = depth_m / width_m
        n = length_m / width_m
        root = math.sqrt(1.0 + m**2 + n**2)
        f1 = (
            math.log((root + n) / (root - n))
            + n * math.log((root + 1.0) / (root - 1.0))
        ) / math.pi
        f2 = m / math.pi * math.atan(n / (m * root))
        expected = q_kpa * width_m / (2.0 * modulus_kpa) * (
            (1.0 - poisson_ratio**2) * f1
            - (1.0 - poisson_ratio - 2.0 * poisson_ratio**2) * f2
        )

        calculated = _steinbrenner_corner_displacement_m(
            q_kpa,
            width_m,
            length_m,
            modulus_kpa,
            poisson_ratio,
            depth_m,
        )
        self.assertAlmostEqual(calculated, expected, places=14)

    def test_steinbrenner_is_linear_with_pressure(self) -> None:
        layers = [SoilLayer("A", 0.0, 10.0, 20.0, poisson_ratio=0.30)]
        first = steinbrenner_layered_settlement(
            100.0, 2.0, 3.0, 1.0, layers, 5.0
        )
        second = steinbrenner_layered_settlement(
            200.0, 2.0, 3.0, 1.0, layers, 5.0
        )
        self.assertAlmostEqual(
            float(second["settlement_mm"]),
            2.0 * float(first["settlement_mm"]),
        )

    def test_steinbrenner_allowable_pressure_reproduces_target_settlement(self) -> None:
        layers = [SoilLayer("A", 0.0, 10.0, 20.0, poisson_ratio=0.30)]
        result = allowable_net_pressure_steinbrenner(
            25.0, 2.0, 3.0, 1.0, layers, 5.0
        )
        check = steinbrenner_layered_settlement(
            float(result["allowable_net_pressure_kpa"]),
            2.0,
            3.0,
            1.0,
            layers,
            5.0,
        )
        self.assertAlmostEqual(float(check["settlement_mm"]), 25.0)

    def test_settlement_modes_evaluate_different_points(self) -> None:
        layers = [SoilLayer("A", 0.0, 10.0, 20.0, poisson_ratio=0.30)]
        center = steinbrenner_layered_settlement(
            100.0, 2.0, 3.0, 0.0, layers, 5.0,
            settlement_mode=SettlementMode.FLEXIBLE_CENTER,
        )
        corner = steinbrenner_layered_settlement(
            100.0, 2.0, 3.0, 0.0, layers, 5.0,
            settlement_mode=SettlementMode.FLEXIBLE_CORNER,
        )
        self.assertGreater(float(center["settlement_mm"]), float(corner["settlement_mm"]))

    def test_two_b_influence_depth_is_geometry_dependent(self) -> None:
        layers = [SoilLayer("A", 0.0, 20.0, 20.0)]
        result = resolve_influence_depth(
            InfluenceDepthMode.TWO_B, 2.5, 4.0, 1.0, layers, 5.0, 4.0
        )
        self.assertAlmostEqual(float(result["depth_m"]), 5.0)

    def test_stress_ratio_influence_depth_reaches_selected_limit(self) -> None:
        layers = [SoilLayer("A", 0.0, 30.0, 20.0)]
        result = resolve_influence_depth(
            InfluenceDepthMode.STRESS_RATIO,
            2.0,
            3.0,
            1.0,
            layers,
            50.0,
            4.0,
            stress_ratio_limit=0.20,
            reference_pressure_kpa=100.0,
        )
        depth = float(result["depth_m"])
        delta_sigma = 100.0 * vertical_stress_ratio_center(2.0, 3.0, depth)
        sigma_v0 = vertical_overburden_from_layers(layers, 1.0 + depth, 50.0, True)
        self.assertLessEqual(delta_sigma / sigma_v0, 0.20)

    def test_allowable_pressure_returns_subgrade_moduli(self) -> None:
        layers = [SoilLayer("A", 0.0, 10.0, 20.0, poisson_ratio=0.30)]
        result = allowable_net_pressure_steinbrenner(
            25.0, 2.0, 3.0, 1.0, layers, 5.0
        )
        expected = float(result["allowable_net_pressure_kpa"]) / 0.025 / 1000.0
        self.assertAlmostEqual(float(result["subgrade_modulus_mn_m3"]), expected)

    def test_cte_ksp30_cohesive_rectangular(self) -> None:
        result = subgrade_modulus_from_ksp30_cte(
            100.0, 2.0, 4.0, SubgradeSoilType.COHESIVE
        )
        expected_ksb = 100.0 * 0.30 / 2.0
        self.assertAlmostEqual(float(result["ksb_mn_m3"]), expected_ksb)
        self.assertAlmostEqual(
            float(result["ksbl_mn_m3"]), expected_ksb * (1.0 + 2.0 / 8.0)
        )
        self.assertEqual(result["equation_ksb"], "E.6")

    def test_cte_ksp30_granular_strip(self) -> None:
        result = subgrade_modulus_from_ksp30_cte(
            80.0, 3.0, None, SubgradeSoilType.GRANULAR
        )
        expected = 80.0 * ((3.0 + 0.30) / (2.0 * 3.0)) ** 2
        self.assertAlmostEqual(float(result["ksb_mn_m3"]), expected)
        self.assertAlmostEqual(float(result["ksbl_mn_m3"]), expected)
        self.assertEqual(result["equation_ksb"], "E.7")

    def test_layered_overburden_integrates_water_table(self) -> None:
        layers = [
            SoilLayer(
                "A", 0.0, 1.0, 20.0,
                gamma_apparent_kn_m3=18.0,
                gamma_saturated_kn_m3=20.0,
            ),
            SoilLayer(
                "B", 1.0, 3.0, 20.0,
                gamma_apparent_kn_m3=19.0,
                gamma_saturated_kn_m3=21.0,
            ),
        ]
        value = vertical_overburden_from_layers(layers, 2.0, 1.0, True)
        self.assertAlmostEqual(value, 18.0 + (21.0 - 9.81))

    def test_layer_coverage_accepts_continuous_profile(self) -> None:
        layers = [
            SoilLayer("A", 0.0, 2.0, 20.0),
            SoilLayer("B", 2.0, 6.0, 15.0),
        ]
        result = assess_foundation_bulbs(layers, 1.0, 2.0, 4.0)
        self.assertTrue(result["all_covered"])

    def test_layer_coverage_detects_internal_gap(self) -> None:
        layers = [
            SoilLayer("A", 0.0, 2.0, 20.0),
            SoilLayer("B", 3.0, 8.0, 15.0),
        ]
        result = check_layer_coverage(layers, 1.0, 6.0, "Bulbo")
        self.assertFalse(result["covered"])
        self.assertEqual(result["gaps"], [(2.0, 3.0)])

    def test_layer_coverage_detects_insufficient_bottom(self) -> None:
        layers = [SoilLayer("A", 0.0, 4.0, 20.0)]
        result = check_layer_coverage(layers, 1.0, 6.0, "Bulbo")
        self.assertFalse(result["covered"])
        self.assertEqual(result["gaps"], [(4.0, 6.0)])



if __name__ == "__main__":
    unittest.main()
    resolve_influence_depth,
