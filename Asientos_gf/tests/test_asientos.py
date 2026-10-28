import unittest

from calculos.asientos import calculate_settlement
from modelos.datos import AnalysisOptions, Foundation, Layer


FOUNDATION = Foundation(shape="rectangular", width_m=2.0, length_m=3.0, embedment_m=1.0,
                        load_mode="presion", pressure_kpa=100.0, pressure_basis="neta")
OPTIONS = AnalysisOptions(dz_m=0.4, service_years=50.0, immediate_model="edometrico_1d")


class SettlementTests(unittest.TestCase):
    def test_arcilla_no_saturada_no_consolida(self):
        layers = [Layer("Arcilla seca", "cohesivo", 20.0, 17.0, 19.0, 12.0, 0.35,
                        0.25, 0.04, 0.85, 500.0, 0.8, 0.006, "doble")]
        result = calculate_settlement(FOUNDATION, layers, OPTIONS, None)
        self.assertEqual(result.points[0].primary_final_mm, 0.0)
        self.assertEqual(result.points[0].secondary_service_mm, 0.0)

    def test_circulo_no_inventa_una_esquina(self):
        foundation = Foundation(shape="circular", diameter_m=2.0, embedment_m=1.0,
                                load_mode="presion", pressure_kpa=100.0, pressure_basis="neta")
        layers = [Layer("Arena", "granular", 20.0, 18.0, 20.0, 30.0)]
        result = calculate_settlement(foundation, layers, OPTIONS, 2.0)
        self.assertEqual([point.name for point in result.points], ["Centro", "Borde"])

    def test_curva_llega_a_vida_de_servicio_e_incluye_secundario(self):
        layers = [Layer("Arcilla", "cohesivo", 20.0, 17.0, 19.0, 12.0, 0.35,
                        0.25, 0.04, 0.85, 500.0, 5.0, 0.01, "doble")]
        result = calculate_settlement(FOUNDATION, layers, OPTIONS, 0.0)
        self.assertGreaterEqual(result.time_years[-1], OPTIONS.service_years)
        self.assertGreater(result.points[0].secondary_service_mm, 0.0)
        self.assertAlmostEqual(result.time_settlement_mm[-1], result.points[0].total_service_mm, places=9)

    def test_avisa_si_no_alcanza_criterio_de_influencia(self):
        layers = [Layer("Suelo muy blando", "granular", 50.0, 1.0, 11.0, 5.0)]
        options = AnalysisOptions(dz_m=0.5, influence_ratio=0.01, max_depth_factor=5.0,
                                  immediate_model="edometrico_1d")
        result = calculate_settlement(FOUNDATION, layers, options, None)
        self.assertFalse(result.influence_reached)
        self.assertTrue(any("truncado" in warning for warning in result.warnings))


if __name__ == "__main__":
    unittest.main()
