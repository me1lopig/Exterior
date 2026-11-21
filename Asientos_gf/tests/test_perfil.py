import unittest

from modelos.datos import Layer
from modelos.perfil import effective_vertical_stress, pore_pressure, total_vertical_stress


LAYERS = [Layer("Suelo", "granular", 5.0, 18.0, 20.0, 30.0)]


class ProfileTests(unittest.TestCase):
    def test_nivel_freatico_en_superficie_no_es_ausencia_de_agua(self):
        wet = effective_vertical_stress(LAYERS, 3.0, 0.0, 9.81)
        dry = effective_vertical_stress(LAYERS, 3.0, None, 9.81)
        self.assertAlmostEqual(wet, (20.0 - 9.81) * 3.0)
        self.assertAlmostEqual(dry, 18.0 * 3.0)
        self.assertNotEqual(wet, dry)

    def test_extension_integra_exactamente_el_nivel_freatico(self):
        self.assertAlmostEqual(total_vertical_stress(LAYERS, 7.0, 6.0), 6.0 * 18.0 + 20.0)
        self.assertAlmostEqual(total_vertical_stress(LAYERS, 7.1, 6.0), 6.0 * 18.0 + 1.1 * 20.0)
        jump = effective_vertical_stress(LAYERS, 7.1, 6.0, 9.81) - effective_vertical_stress(LAYERS, 7.0, 6.0, 9.81)
        self.assertAlmostEqual(jump, (20.0 - 9.81) * 0.1)

    def test_perfil_piezometrico_se_interpola_y_extrapola(self):
        points = ((0.0, 0.0), (2.0, 0.0), (6.0, 40.0))
        self.assertAlmostEqual(pore_pressure(4.0, None, 9.81, points), 20.0)
        self.assertAlmostEqual(pore_pressure(8.0, None, 9.81, points), 60.0)
        effective = effective_vertical_stress(LAYERS, 4.0, None, 9.81, points)
        self.assertAlmostEqual(effective, 2.0 * 18.0 + 2.0 * 20.0 - 20.0)


if __name__ == "__main__":
    unittest.main()
