import unittest
import math

from calculos.campo import dmt, molinete, placa_carga, presiometro, sismica
from calculos.errores import ErrorCalculoGeotecnico, FueraDeDominio


class TestEnsayosCampo(unittest.TestCase):
    def test_molinete_y_sensibilidad(self) -> None:
        resultado = molinete(0.10, 0.065, 0.13, 0.025, "Arcilla")
        self.assertGreater(resultado["su_pico_kpa"], 0)
        self.assertAlmostEqual(resultado["sensibilidad"], 4.0)

    def test_molinete_rechaza_par_remoldeado_mayor(self) -> None:
        with self.assertRaises(ErrorCalculoGeotecnico):
            molinete(0.10, 0.065, 0.13, 0.11, "Arcilla")

    def test_molinete_rechaza_suelo_no_cohesivo(self) -> None:
        with self.assertRaises(FueraDeDominio):
            molinete(0.10, 0.065, 0.13, tipo_suelo="Arena limpia")

    def test_sismica(self) -> None:
        resultado = sismica(200, 19.6133, 400)
        self.assertAlmostEqual(resultado["rho_kg_m3"], 2000.0, places=2)
        self.assertAlmostEqual(resultado["G0_MPa"], 80.0, places=2)
        self.assertAlmostEqual(resultado["nu_din"], 1 / 3, places=6)
        self.assertAlmostEqual(resultado["E0_MPa"], 213.333333, places=4)

    def test_sismica_rechaza_relacion_no_fisica(self) -> None:
        with self.assertRaises(FueraDeDominio):
            sismica(200, 19, 250)

    def test_dmt_indices(self) -> None:
        resultado = dmt(200, 500, 50, 100)
        self.assertAlmostEqual(resultado["ID"], 2.0)
        self.assertAlmostEqual(resultado["KD"], 1.5)
        self.assertAlmostEqual(resultado["ED_MPa"], 10.41)
        self.assertIsNone(resultado["OCR_estimado"])
        self.assertIsNotNone(resultado["advertencia_derivadas"])

    def test_dmt_derivadas_solo_en_arcilla_no_cementada(self) -> None:
        resultado = dmt(300, 500, 50, 100, "Arcilla", False)
        self.assertGreater(resultado["OCR_estimado"], 1.0)
        self.assertGreater(resultado["su_estimado_kPa"], 0.0)
        fuera_dominio = dmt(150, 250, 50, 100, "Arcilla", False)
        self.assertIsNone(fuera_dominio["OCR_estimado"])
        self.assertIn("KD<2", fuera_dominio["advertencia_derivadas"])

    def test_presiometro(self) -> None:
        resultado = presiometro(12, 1.2, 0.8, 0.5, 0.1, "Arcilla")
        self.assertAlmostEqual(resultado["E_equiv_MPa"], 24.0)
        self.assertAlmostEqual(resultado["su_estimado_kPa"], 200.0)

    def test_presiometro_no_calcula_su_en_suelo_no_cohesivo(self) -> None:
        resultado = presiometro(12, 1.2, presion_horizontal_mpa=0.1, tipo_suelo="Arena limpia")
        self.assertIsNone(resultado["su_estimado_kPa"])
        self.assertIn("cohesivo", resultado["advertencia_su"])

    def test_placa(self) -> None:
        resultado = placa_carga(40, 100, 35)
        self.assertAlmostEqual(resultado["Ev2_Ev1"], 2.5)

    def test_todos_los_ensayos_rechazan_nan(self) -> None:
        casos = [
            lambda: molinete(math.nan, 0.065, 0.13, tipo_suelo="Arcilla"),
            lambda: sismica(math.nan, 19.0),
            lambda: dmt(math.nan, 300, 50, 100),
            lambda: presiometro(math.nan, 1.2, tipo_suelo="Arcilla"),
            lambda: placa_carga(math.nan, 100),
        ]
        for caso in casos:
            with self.subTest(caso=caso):
                with self.assertRaises(ErrorCalculoGeotecnico):
                    caso()


if __name__ == "__main__":
    unittest.main()
