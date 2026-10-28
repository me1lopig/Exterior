import unittest

import numpy as np

from calculos.tensiones import PressureField, build_pressure_field, circle_quadrature
from calculos.tensiones import stress_circle_axis, stress_from_field, stress_rect_uniform, stress_strip_uniform
from modelos.datos import Foundation


class StressTests(unittest.TestCase):
    def test_rectangulo_centro_reproduce_solucion_cerrada(self):
        foundation = Foundation(shape="rectangular", width_m=2.0, length_m=3.0,
                                load_mode="presion", pressure_kpa=100.0, pressure_basis="neta")
        field = build_pressure_field(foundation, 0.0, 30_000.0, 0.30)
        for depth in (0.05, 0.10, 1.0, 10.0):
            expected = stress_rect_uniform(100.0, 2.0, 3.0, depth)
            self.assertAlmostEqual(stress_from_field(field, depth), expected, delta=abs(expected) * 2e-12)

    def test_circulo_real_reproduce_solucion_analitica_en_el_eje(self):
        x, y, weights = circle_quadrature(1.0, radial_order=24, angular_order=72)
        field = PressureField(x, y, weights, np.full_like(x, 100.0), np.full_like(x, 100.0), "test")
        for depth in (0.10, 1.0, 5.0):
            expected = stress_circle_axis(100.0, 1.0, depth)
            self.assertAlmostEqual(stress_from_field(field, depth), expected, delta=abs(expected) * 2e-5)

    def test_banda_casos_limite(self):
        self.assertAlmostEqual(stress_strip_uniform(120.0, 2.0, 1e-5), 120.0, delta=120e-6)
        self.assertLess(stress_strip_uniform(120.0, 2.0, 1.0e9), 1e-6)

    def test_contacto_rigido_equilibra_y_no_admite_tracciones(self):
        foundation = Foundation(shape="rectangular", width_m=2.0, length_m=3.0,
                                load_mode="fuerza", vertical_load_kn=800.0, mx_knm=80.0, my_knm=30.0,
                                pressure_basis="bruta", rigidity="rigida")
        field = build_pressure_field(foundation, 18.0, 25_000.0, 0.30)
        self.assertAlmostEqual(field.gross_resultant_kn, 800.0, places=7)
        self.assertAlmostEqual(np.sum(field.gross_pressure_kpa * field.area_weights_m2 * field.y_m), 80.0, places=7)
        self.assertAlmostEqual(np.sum(field.gross_pressure_kpa * field.area_weights_m2 * field.x_m), 30.0, places=7)
        self.assertGreaterEqual(np.min(field.gross_pressure_kpa), 0.0)
        self.assertIsNotNone(field.rigid_settlement_center_m)

    def test_carga_neta_negativa_se_conserva(self):
        foundation = Foundation(shape="rectangular", width_m=2.0, length_m=2.0,
                                load_mode="presion", pressure_kpa=-5.0, pressure_basis="neta")
        field = build_pressure_field(foundation, 20.0, 20_000.0, 0.30)
        self.assertAlmostEqual(field.resultant_kn, -20.0)
        self.assertTrue(np.all(field.gross_pressure_kpa > 0.0))
        self.assertLess(stress_from_field(field, 1.0), 0.0)


if __name__ == "__main__":
    unittest.main()
