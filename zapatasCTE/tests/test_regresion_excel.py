"""Regresión frente a los valores guardados en la pestaña SUELOS."""

from __future__ import annotations

import unittest

import numpy as np

from calculos.asientos import calcular_presiones_asiento
from calculos.capacidad_portante import calcular_presiones_hundimiento
from calculos.servicio import convertir_ksbl_a_ksp30
from modelos.datos import CapaSuelo, DatosAsientos, DatosHundimiento


class RegresionExcelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.hundimiento = DatosHundimiento()
        self.asientos = DatosAsientos(
            capas=(
                CapaSuelo("NIVEL 1", 0.0, 2.5, 15.0, 0.3),
                CapaSuelo("NIVEL 2", 2.5, 10.0, 1200.0, 0.2),
            )
        )

    def test_hundimiento_reproduce_excel(self) -> None:
        cuadrada, corrida = calcular_presiones_hundimiento(self.hundimiento)
        np.testing.assert_allclose(
            cuadrada,
            [0.1504807983, 0.1599747811, 0.1663041029, 0.1821274075, 0.1979507121],
            rtol=1e-9,
        )
        np.testing.assert_allclose(
            corrida,
            [0.1230587241, 0.1366224716, 0.1456636137, 0.1682617220, 0.1908530488],
            rtol=1e-9,
        )

    def test_asientos_corregidos_discrepan_del_goal_seek_excel(self) -> None:
        cuadrada, corrida = calcular_presiones_asiento(
            self.hundimiento.anchos_m, self.asientos
        )
        # Valores externos calculados mediante la ecuacion corregida de
        # Steinbrenner, contrastados con la auditoria independiente.
        valores_corregidos_c = [
            0.948756309534, 0.900346314231, 0.880634523251,
            0.855949187925, 0.850029326670,
        ]
        valores_corregidos_l = [
            0.919299616765, 0.897488951781, 0.889728131075,
            0.883513946911, 0.887026494299,
        ]
        np.testing.assert_allclose(cuadrada, valores_corregidos_c, rtol=1e-10)
        np.testing.assert_allclose(corrida, valores_corregidos_l, rtol=1e-10)
        # La v4 no pretende reproducir el error historico de Poisson del VBA.
        self.assertGreater(abs(cuadrada[0]-0.9263561049),0.01)

    def test_superposicion_central_es_mas_conservadora(self) -> None:
        revisado = DatosAsientos(
            asiento_admisible_cm=5.0,
            longitud_corrida_m=100.0,
            capas=self.asientos.capas,
            metodo_centro="superposicion",
        )
        q_excel, _ = calcular_presiones_asiento(self.hundimiento.anchos_m, self.asientos)
        q_revisado, _ = calcular_presiones_asiento(self.hundimiento.anchos_m, revisado)
        self.assertTrue(np.all(q_revisado < q_excel))

    def test_balasto_cte_cohesivo_y_granular(self) -> None:
        ks_bl = 20.0
        ancho = 2.0
        longitud = 4.0
        ks_b = ks_bl / 1.25

        self.assertAlmostEqual(
            convertir_ksbl_a_ksp30(ks_bl, ancho, longitud, "Cohesivo"),
            ks_b * ancho / 0.30,
        )
        self.assertAlmostEqual(
            convertir_ksbl_a_ksp30(ks_bl, ancho, longitud, "Granular"),
            ks_b * (2.0 * ancho / (ancho + 0.30)) ** 2,
        )


if __name__ == "__main__":
    unittest.main()
