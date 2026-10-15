from __future__ import annotations

import unittest

import pandas as pd

from calculations.serviceability import (
    allowable_net_pressure_steinbrenner,
    elastic_settlement,
    layered_settlement_2to1,
    spt_allowable_pressure_cte,
    spt_settlement_burland_burbidge,
    steinbrenner_layered_settlement,
)
from calculations.layers import (
    assess_foundation_bulbs,
    check_layer_coverage,
    vertical_overburden_from_layers,
)
from models.inputs import SoilLayer
from services.field_data import mean_spt_in_cte_zone, normalize_field_data


class ServiceabilityTests(unittest.TestCase):
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

    def test_spt_allowable_pressure_narrow_footing(self) -> None:
        value = spt_allowable_pressure_cte(10.0, 1.0, 0.5, 25.0)
        self.assertAlmostEqual(value, 140.0)

    def test_spt_depth_factor_is_capped(self) -> None:
        shallow = spt_allowable_pressure_cte(10.0, 1.0, 0.9, 25.0)
        deep = spt_allowable_pressure_cte(10.0, 1.0, 5.0, 25.0)
        self.assertAlmostEqual(shallow, deep)

    def test_burland_burbidge_rejects_low_n(self) -> None:
        with self.assertRaisesRegex(ValueError, "N_SPT < 7"):
            spt_settlement_burland_burbidge(100.0, 2.0, 3.0, 6.0, 4.0)

    def test_elastic_settlement_dimensions(self) -> None:
        value = elastic_settlement(100.0, 2.0, 20.0, 0.3, 1.0)
        self.assertAlmostEqual(value, 9.1)

    def test_layered_settlement_sums_components(self) -> None:
        layers = [
            SoilLayer("A", 1.0, 3.0, 20.0),
            SoilLayer("B", 3.0, 6.0, 10.0),
        ]
        result = layered_settlement_2to1(100.0, 2.0, 3.0, 1.0, layers, 4.0)
        component_sum = sum(item["settlement_mm"] for item in result["components"])
        self.assertAlmostEqual(float(result["settlement_mm"]), component_sum)

    def test_field_profile_zone_and_terzaghi_correction(self) -> None:
        raw = pd.DataFrame(
            {"depth_m": [0, 1, 2, 3, 4, 5], "N_spt": [10, 20, 30, 40, 50, 60]}
        )
        normalized = normalize_field_data(raw)
        result = mean_spt_in_cte_zone(normalized, 1.0, 2.0, True, 1.0)
        self.assertEqual(result["count"], 6)
        self.assertLess(float(result["mean_n"]), raw["N_spt"].mean())

    def test_cpt_conversion_requires_declared_ratio(self) -> None:
        raw = pd.DataFrame({"depth_m": [1.0], "qc_MPa": [8.0]})
        normalized = normalize_field_data(raw, qc_over_n_mpa=0.4)
        self.assertAlmostEqual(normalized.iloc[0]["N_spt"], 20.0)


if __name__ == "__main__":
    unittest.main()
