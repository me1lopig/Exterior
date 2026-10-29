from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import funciones_asientos as fa


def perfil(espesor=30.0, nu=0.30):
    return pd.DataFrame({
        "Descripción": ["Homogéneo"],
        "Espesor (m)": [espesor],
        "E (kPa)": [20000.0],
        "nu": [nu],
        "Peso Esp. (kN/m³)": [18.0],
        "Peso Esp. Sat (kN/m³)": [20.0],
    })


class TestFuncionesAsientos(unittest.TestCase):
    def test_holl_vertical_matches_reference_value(self):
        sz, _, _ = fa.holl_esquina(150.0, 2.0, 3.0, 2.0)
        self.assertAlmostEqual(float(sz), 29.04650791739277, places=11)

    def test_influence_depth_reports_reached_criterion(self):
        resultado = fa.evaluar_z_influencia_ec7(150.0, 2.0, 3.0, perfil(), 100.0)
        self.assertTrue(resultado.criterio_alcanzado)
        self.assertAlmostEqual(resultado.profundidad, 4.75)
        self.assertLessEqual(resultado.relacion_dsz_sv0, 0.20)

    def test_influence_depth_reports_insufficient_profile(self):
        resultado = fa.evaluar_z_influencia_ec7(150.0, 2.0, 3.0, perfil(2.0), 100.0)
        self.assertFalse(resultado.criterio_alcanzado)
        self.assertAlmostEqual(resultado.profundidad, 2.0)
        self.assertGreater(resultado.relacion_dsz_sv0, 0.20)

    def test_settlement_increases_with_integration_depth(self):
        df = perfil()
        s1 = fa.calcular_steinbrenner_zapata(150.0, 2.0, 3.0, df, 1.0).total
        s2 = fa.calcular_steinbrenner_zapata(150.0, 2.0, 3.0, df, 4.75).total
        self.assertGreater(s2, s1)
        self.assertGreater(s1, 0.0)

    def test_nu_equal_half_is_rejected_without_silent_clipping(self):
        df = perfil(nu=0.50)
        errores = fa.validar_estratigrafia(df)
        self.assertTrue(any("0 ≤ ν < 0,5" in error for error in errores))
        with self.assertRaisesRegex(ValueError, "Poisson"):
            fa.construir_malla_3d(2.0, 3.0, df, 4.0)

    def test_classical_solution_accepts_incompressible_limit(self):
        resultado = fa.calcular_steinbrenner_zapata(
            150.0, 2.0, 3.0, perfil(nu=0.50), 4.0
        )
        self.assertTrue(np.isfinite(resultado.total))
        self.assertGreater(resultado.total, 0.0)

    def test_homogeneous_layer_split_does_not_change_settlement(self):
        unico = perfil(espesor=10.0)
        dividido = pd.concat([perfil(espesor=4.0), perfil(espesor=6.0)], ignore_index=True)
        dividido["Descripción"] = ["Homogéneo 1", "Homogéneo 2"]
        s_unico = fa.calcular_steinbrenner_zapata(150.0, 2.0, 3.0, unico, 10.0).total
        s_dividido = fa.calcular_steinbrenner_zapata(150.0, 2.0, 3.0, dividido, 10.0).total
        self.assertAlmostEqual(s_unico, s_dividido, places=13)

    def test_effective_stress_when_water_table_crosses_layer(self):
        df = pd.DataFrame({
            "Descripción": ["A", "B"],
            "Espesor (m)": [2.0, 3.0],
            "E (kPa)": [20000.0, 30000.0],
            "nu": [0.3, 0.3],
            "Peso Esp. (kN/m³)": [18.0, 19.0],
            "Peso Esp. Sat (kN/m³)": [20.0, 21.0],
        })
        esperado = 18.0 + (20.0 - fa.GAMMA_AGUA) + 2.0 * (21.0 - fa.GAMMA_AGUA)
        self.assertAlmostEqual(fa.sigma_v0(4.0, df, NF=1.0), esperado, places=12)

    def test_flexible_embedment_profile_is_continuous_at_edge(self):
        df = perfil()
        resultado = fa.calcular_steinbrenner_zapata(150.0, 2.0, 3.0, df, 8.0, D=2.0, empotramiento=True)
        x = np.array([1.0 - 1e-6, 1.0, 1.0 + 1e-6])
        s = fa.perfil_steinbrenner(150.0, 2.0, 3.0, df, 8.0, 2.0, x, "x", resultado)
        self.assertLess(abs(s[2] - s[1]) / s[1], 1e-5)

    def test_rigid_profile_is_not_extrapolated_outside_footing(self):
        df = perfil()
        resultado = fa.calcular_steinbrenner_zapata(150.0, 2.0, 3.0, df, 8.0, rigida=True)
        s = fa.perfil_steinbrenner(150.0, 2.0, 3.0, df, 8.0, 0.0, np.array([0.0, 1.1]), "x", resultado)
        self.assertTrue(np.isfinite(s[0]))
        self.assertTrue(np.isnan(s[1]))

    def test_fem_bottom_is_deeper_than_reporting_depth(self):
        malla = fa.construir_malla_3d(2.0, 3.0, perfil(), 4.0, factor_prof=2.0)
        self.assertAlmostEqual(-malla.z[-1], 8.0)

    def test_angular_distortion_functionality_is_absent(self):
        self.assertFalse(hasattr(fa, "distorsion_angular"))
        app_text = (ROOT / "app.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("distorsión", app_text)
        self.assertNotIn("distorsion", app_text)
        self.assertNotIn("vecino", app_text)


if __name__ == "__main__":
    unittest.main()
