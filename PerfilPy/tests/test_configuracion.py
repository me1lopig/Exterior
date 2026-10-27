import unittest

from modelos.configuracion import OpcionesGraficas, PRESETS_GRAFICOS, validar_opciones_graficas


class GraphicConfigurationTests(unittest.TestCase):
    def test_presets_are_ordered_by_text_size(self):
        self.assertLess(
            PRESETS_GRAFICOS["Compacta"].texto_ejes_m,
            PRESETS_GRAFICOS["Normal"].texto_ejes_m,
        )
        self.assertLess(
            PRESETS_GRAFICOS["Normal"].texto_ejes_m,
            PRESETS_GRAFICOS["Ampliada"].texto_ejes_m,
        )

    def test_default_configuration_is_valid(self):
        self.assertEqual(validar_opciones_graficas(OpcionesGraficas()), [])

    def test_negative_spacing_is_rejected(self):
        options = OpcionesGraficas(separacion_horizontal_m=-0.1)
        self.assertTrue(validar_opciones_graficas(options))


if __name__ == "__main__":
    unittest.main()
