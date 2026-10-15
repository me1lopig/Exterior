from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import funciones_asientos as fa


def perfil(espesor=20.0, nu=0.3):
    return pd.DataFrame({
        "Descripción": ["Estrato"],
        "Espesor (m)": [espesor],
        "E (kPa)": [20_000.0],
        "nu": [nu],
        "Peso Esp. (kN/m³)": [18.0],
        "Peso Esp. Sat (kN/m³)": [20.0],
    })


class TestFuncionesAsientos(unittest.TestCase):
    def test_nu_05_se_normaliza_a_0499_en_steinbrenner(self):
        df_05 = perfil(nu=0.5)
        df_0499 = perfil(nu=0.499)
        s_05 = fa.calcular_steinbrenner_zapata(150.0, 2.0, 3.0, df_05, 5.0).total
        s_0499 = fa.calcular_steinbrenner_zapata(150.0, 2.0, 3.0, df_0499, 5.0).total
        self.assertAlmostEqual(s_05, s_0499, places=12)
        self.assertEqual(fa.normalizar_estratigrafia(df_05).loc[0, "nu"], 0.499)

    def test_validacion_rechaza_valores_no_finitos_y_pesos_negativos(self):
        df = perfil()
        df.loc[0, "E (kPa)"] = np.inf
        df.loc[0, "Peso Esp. (kN/m³)"] = -1.0
        errores = fa.validar_estratigrafia(df)
        self.assertTrue(any("número finito" in error for error in errores))
        self.assertTrue(any("debe ser positivo" in error for error in errores))

    def test_profundidad_influencia_informa_si_el_perfil_es_insuficiente(self):
        resultado = fa.evaluar_z_influencia_ec7(150.0, 2.0, 3.0, perfil(espesor=1.0), 100.0)
        self.assertFalse(resultado.criterio_cumplido)
        self.assertAlmostEqual(resultado.profundidad, 1.0)
        self.assertGreater(resultado.ratio, 0.20)

    def test_profundidad_influencia_detecta_el_cruce_del_criterio(self):
        resultado = fa.evaluar_z_influencia_ec7(150.0, 2.0, 3.0, perfil(espesor=20.0), 100.0)
        self.assertTrue(resultado.criterio_cumplido)
        self.assertLessEqual(resultado.ratio, 0.20)
        self.assertGreater(resultado.profundidad, 0.0)

    def test_malla_no_extrapola_el_ultimo_estrato(self):
        with self.assertRaisesRegex(ValueError, "estratigrafía solo cubre"):
            fa.construir_malla_3d(2.0, 3.0, perfil(espesor=5.0), 4.0, factor_prof=2.0)

    def test_areas_tributarias_conservan_el_area_del_cuarto(self):
        x = fa._coords_graduadas(1.0, 8.0, 0.25, 1.3, 2.0)
        y = fa._coords_graduadas(1.5, 12.0, 0.25, 1.3, 2.0)
        area = fa._tributarias_1d_3d(x, 1.0).sum() * fa._tributarias_1d_3d(y, 1.5).sum()
        self.assertAlmostEqual(area, 2.0 * 3.0 / 4.0, places=12)

    def test_suma_por_estratos_coincide_con_el_total_analitico(self):
        df = pd.concat([perfil(3.0), perfil(7.0)], ignore_index=True)
        df.loc[1, "Descripción"] = "Estrato 2"
        df.loc[1, "E (kPa)"] = 35_000.0
        resultado = fa.calcular_steinbrenner_zapata(120.0, 2.0, 3.0, df, 8.0)
        self.assertAlmostEqual(resultado.tabla["Δs [mm]"].sum(), resultado.total * 1000.0, places=3)


if __name__ == "__main__":
    unittest.main()
