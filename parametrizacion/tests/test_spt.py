import unittest

from calculations.spt import SPTCorrection


class SPTCorrectionTests(unittest.TestCase):
    def test_n60_and_n1_60_are_computed_from_explicit_factors(self) -> None:
        correction = SPTCorrection(
            n_field=20,
            energy_ratio_percent=75,
            borehole_factor=1.05,
            rod_factor=0.85,
            sampler_factor=1.1,
            effective_overburden_kpa=25,
        )
        self.assertAlmostEqual(correction.n60, 24.54375)
        self.assertAlmostEqual(correction.cn, 1.7)
        self.assertAlmostEqual(correction.n1_60, 41.724375)

    def test_invalid_effective_stress_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "sigma_v_eff"):
            SPTCorrection(20, effective_overburden_kpa=0)


if __name__ == "__main__":
    unittest.main()
