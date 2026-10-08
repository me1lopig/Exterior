import unittest

from calculations.correlations import (
    calip,
    cte_d23_linear,
    cte_eu,
    cte_subgrade_modulus,
    mesri_su,
    phi_hatanaka_uchida,
    phi_jra,
    phi_mayne,
    phi_residual_from_calip,
    phi_wolff,
    skempton_su,
    stroud_drained_vertical_modulus,
)


class CorrelationTests(unittest.TestCase):
    def test_stroud_graph_digitization_returns_ordered_drained_modulus_bounds(self) -> None:
        lower, upper = stroud_drained_vertical_modulus(20, 20)
        self.assertAlmostEqual(lower.value, 25.776, places=3)
        self.assertAlmostEqual(upper.value, 35.756, places=3)
        self.assertLess(lower.value, upper.value)
        self.assertIn("drenado", lower.applicability)

    def test_stroud_graph_digitization_rejects_extrapolation(self) -> None:
        with self.assertRaisesRegex(ValueError, "0 <= IP <= 60"):
            stroud_drained_vertical_modulus(20, 65)

    def test_cte_d23_linear_interpolation_at_nodes_and_inside_segments(self) -> None:
        qu, modulus = cte_d23_linear(10, 100)
        self.assertAlmostEqual(qu.value, 80.0)
        self.assertAlmostEqual(modulus.value, 8.0)
        qu, modulus = cte_d23_linear(17.5, 100)
        self.assertAlmostEqual(qu.value, 115.0)
        self.assertAlmostEqual(modulus.value, 24.0)
        qu, modulus = cte_d23_linear(75, 100)
        self.assertAlmostEqual(qu.value, 400.0)
        self.assertAlmostEqual(modulus.value, 300.0)

    def test_cte_d23_rejects_undefined_or_exceeded_refusal(self) -> None:
        with self.assertRaisesRegex(ValueError, "mayor que 50"):
            cte_d23_linear(50, 50)
        with self.assertRaisesRegex(ValueError, "superar"):
            cte_d23_linear(101, 100)

    def test_skempton_uses_linear_plasticity_index(self) -> None:
        result = skempton_su(20, 100)
        self.assertAlmostEqual(result.value, 18.4)
        self.assertNotIn("log", result.formula.lower())

    def test_mesri_uses_preconsolidation_pressure(self) -> None:
        result = mesri_su(200)
        self.assertAlmostEqual(result.value, 44.0)
        self.assertIn("sigma'p", result.input_basis)

    def test_calip_uses_plasticity_index_not_plastic_limit(self) -> None:
        cf, pi, value = calip(80, 40, 50, 20)
        self.assertAlmostEqual(cf, 50)
        self.assertAlmostEqual(pi, 30)
        self.assertAlmostEqual(value, 37.5)

    def test_calip_rejects_impossible_gradation(self) -> None:
        with self.assertRaisesRegex(ValueError, "contenido de arcilla"):
            calip(40, 60, 50, 20)

    def test_residual_angle_uses_published_non_linear_calip_fit(self) -> None:
        at_zero = phi_residual_from_calip(0)
        at_sixty = phi_residual_from_calip(60)
        self.assertAlmostEqual(at_zero.value, 28.9)
        self.assertAlmostEqual(at_sixty.value, 8.214756, places=5)
        self.assertLess(at_sixty.value, at_zero.value)
        self.assertIn("100-500 kPa", at_sixty.applicability)
        self.assertAlmostEqual(phi_residual_from_calip(10000).value, 7.7)

    def test_calip_accepts_liquid_limits_above_one_hundred_percent(self) -> None:
        _, pi, value = calip(100, 80, 150, 50)
        self.assertAlmostEqual(pi, 100)
        self.assertAlmostEqual(value, 960.0)

    def test_phi_correlations_use_n1_60(self) -> None:
        cases = (
            (phi_wolff, 32.884),
            (phi_hatanaka_uchida, 40.0),
            (phi_mayne, 37.5499287748),
            (phi_jra, 32.3205080757),
        )
        for function, expected in cases:
            with self.subTest(function=function.__name__):
                self.assertAlmostEqual(function(20).value, expected)

    def test_cte_eu_selects_bands_and_converts_to_mpa(self) -> None:
        self.assertAlmostEqual(cte_eu(100, 25, 2).value, 80.0)
        self.assertAlmostEqual(cte_eu(100, 40, 4).value, 25.0)
        self.assertAlmostEqual(cte_eu(100, 55, 6).value, 5.0)

    def test_cte_eu_flags_undefined_ip_boundaries(self) -> None:
        with self.assertRaisesRegex(ValueError, "IP = 30 o 50"):
            cte_eu(100, 30, 2)

    def test_rectangular_subgrade_modulus_and_geometry_validation(self) -> None:
        result = cte_subgrade_modulus(50, 2, 4, "Cohesivo")
        self.assertAlmostEqual(result.value, 9.375)
        with self.assertRaisesRegex(ValueError, "B <= L"):
            cte_subgrade_modulus(50, 4, 2, "Cohesivo")


if __name__ == "__main__":
    unittest.main()
