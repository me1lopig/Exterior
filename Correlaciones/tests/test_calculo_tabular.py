import unittest
import math

import pandas as pd

from modelos.dominio import MetodoInterpolacion, TipoN
from servicios.calculo_tabular import calcular_dmt, calcular_pmt, calcular_sismica, calcular_spt


class TestCalculoTabular(unittest.TestCase):
    def test_conserva_grupo_registro_y_correlacion(self) -> None:
        datos = pd.DataFrame([{
            "grupo": "G02",
            "registro_id": "R01",
            "punto": "S-2",
            "profundidad_m": 5.0,
            "unidad_geotecnica": "UG-1",
            "tipo_suelo": "Arena limpia",
            "tipo_n": TipoN.N_CTE.value,
            "n": 26,
            "porcentaje_mayor_20mm": 5,
        }])
        resultado = calcular_spt(
            datos, ["RES-PHI-SPT-CTE2019-T41"], MetodoInterpolacion.LINEAL
        )
        self.assertEqual(resultado.loc[0, "grupo"], "G02")
        self.assertEqual(resultado.loc[0, "registro_id"], "R01")
        self.assertEqual(resultado.loc[0, "correlacion_id"], "RES-PHI-SPT-CTE2019-T41")
        self.assertAlmostEqual(resultado.loc[0, "valor"], 35.0)

    def test_nan_de_campo_genera_error_no_valido(self) -> None:
        datos = pd.DataFrame([{
            "grupo": "G01", "registro_id": "R01", "punto": "S-1", "profundidad_m": 2.0,
            "unidad_geotecnica": "UG-1", "Vs_m_s": math.nan, "gamma_kN_m3": 19.0,
            "Vp_m_s": math.nan,
        }])
        resultado = calcular_sismica(datos)
        self.assertEqual(len(resultado), 1)
        self.assertFalse(resultado.loc[0, "valido"])
        self.assertEqual(resultado.loc[0, "estado"], "No valido")

    def test_dmt_y_pmt_asignan_fuente_por_parametro(self) -> None:
        base = {"grupo": "G01", "registro_id": "R01", "punto": "S-1", "profundidad_m": 2.0, "unidad_geotecnica": "UG-1"}
        dmt_df = pd.DataFrame([{**base, "tipo_suelo": "Arcilla", "cementado": False, "p0_kPa": 300, "p1_kPa": 500, "u0_kPa": 50, "sigma_v_eff_kPa": 100}])
        dmt_resultado = calcular_dmt(dmt_df)
        self.assertEqual(
            dmt_resultado.loc[dmt_resultado["parametro"] == "su", "correlacion_id"].iloc[0],
            "RES-SU-DMT-MARCHETTI1980",
        )
        pmt_df = pd.DataFrame([{**base, "tipo_suelo": "Arcilla", "EM_MPa": 12, "plM_MPa": 1.2, "pf_MPa": 0.8, "alpha": 0.5, "p0h_MPa": 0.1}])
        pmt_resultado = calcular_pmt(pmt_df)
        self.assertEqual(
            pmt_resultado.loc[pmt_resultado["parametro"] == "su", "correlacion_id"].iloc[0],
            "RES-SU-PMT-FHWA1989",
        )


if __name__ == "__main__":
    unittest.main()
