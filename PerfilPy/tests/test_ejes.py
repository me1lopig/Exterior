import unittest

import pandas as pd

from calculos.ejes import calcular_limites_verticales
from modelos.datos import DatosProyecto


class VerticalAxisTests(unittest.TestCase):
    def _data(self, elevation: float, depth: float) -> DatosProyecto:
        return DatosProyecto(
            perfiles=pd.DataFrame(
                [
                    {"perfil": "P", "orden": 0, "estacion": "STA", "tipo": "Punto de terreno", "distancia_m": 0, "cota_m": elevation},
                    {"perfil": "P", "orden": 1, "estacion": "S-01", "tipo": "Sondeo", "distancia_m": 10, "cota_m": elevation},
                ]
            ),
            litologia=pd.DataFrame(
                [{"sondeo": "S-01", "profundidad_inicial_m": 0, "profundidad_final_m": depth}]
            ),
            dpsh=pd.DataFrame(columns=["ensayo", "profundidad_m", "golpes"]),
            ensayos=pd.DataFrame(columns=["sondeo", "profundidad_m"]),
            ugeo=pd.DataFrame(columns=["sondeo", "profundidad_final_m"]),
            nivel_freatico=pd.DataFrame(columns=["sondeo", "estado", "profundidad_m"]),
        )

    def test_current_project_depth_produces_margin_below_bottom(self):
        limits = calcular_limites_verticales(self._data(0.0, 9.48), "P")
        self.assertEqual(limits.cota_fondo_minima, -9.48)
        self.assertEqual((limits.minimo, limits.maximo, limits.paso), (-12.0, 2.0, 2.0))
        self.assertLess(limits.minimo, limits.cota_fondo_minima)

    def test_bottom_uses_elevation_minus_depth(self):
        limits = calcular_limites_verticales(self._data(615.30, 18.70), "P")
        self.assertAlmostEqual(limits.cota_fondo_minima, 596.60)
        self.assertLessEqual(limits.minimo, limits.cota_fondo_minima - limits.margen_inferior)
        self.assertGreaterEqual(limits.maximo, limits.cota_terreno_maxima + limits.margen_superior)


if __name__ == "__main__":
    unittest.main()
