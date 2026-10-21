import unittest

from calculos.errores import ErrorCalculoGeotecnico, FueraDeDominio
from calculos.spt import es_fhwa, indice_compresibilidad_cte, phi_cte_41, tabla_d23
from modelos.dominio import MetodoInterpolacion, TipoN


class TestCorrelacionesSPT(unittest.TestCase):
    def test_phi_reproduce_nodo_cte(self) -> None:
        resultado = phi_cte_41(22, TipoN.N_CTE.value, "Arena limpia", 10)
        self.assertAlmostEqual(resultado.valor, 34.0)
        self.assertFalse(resultado.interpolado)

    def test_phi_interpola_entre_nodos(self) -> None:
        resultado = phi_cte_41(26, TipoN.N_CTE.value, "Arena limpia")
        self.assertAlmostEqual(resultado.valor, 35.0)
        self.assertTrue(resultado.interpolado)

    def test_phi_bloquea_extrapolacion_y_gruesos(self) -> None:
        with self.assertRaises(FueraDeDominio):
            phi_cte_41(8, TipoN.N_CTE.value, "Arena limpia")
        with self.assertRaises(FueraDeDominio):
            phi_cte_41(20, TipoN.N_CTE.value, "Arena limpia", 31)

    def test_phi_rechaza_suelo_cohesivo(self) -> None:
        with self.assertRaises(FueraDeDominio):
            phi_cte_41(20, TipoN.N_CTE.value, "Arcilla")

    def test_d23_devuelve_intervalo_literal(self) -> None:
        resultado = tabla_d23(20, TipoN.N_CTE.value, "E", MetodoInterpolacion.LITERAL)
        self.assertIsNone(resultado.valor)
        self.assertEqual((resultado.minimo, resultado.maximo), (8.0, 40.0))

    def test_d23_interpola_intervalo_cerrado(self) -> None:
        modulo = tabla_d23(17.5, TipoN.N_CTE.value, "E", MetodoInterpolacion.LINEAL)
        resistencia = tabla_d23(
            17.5, TipoN.N_CTE.value, "qu", MetodoInterpolacion.LINEAL, "Arcilla"
        )
        self.assertAlmostEqual(modulo.valor, 24.0)
        self.assertAlmostEqual(resistencia.valor, 115.0)
        self.assertIn("adoptada por GeoCorr", resistencia.advertencias[0])
        self.assertTrue(resistencia.valido)

    def test_d23_qu_rechaza_suelo_no_cohesivo(self) -> None:
        with self.assertRaises(FueraDeDominio):
            tabla_d23(20, TipoN.N_CTE.value, "qu", MetodoInterpolacion.LINEAL, "Arena limpia")

    def test_d23_no_inventa_limite_abierto(self) -> None:
        resultado = tabla_d23(6, TipoN.N_CTE.value, "E", MetodoInterpolacion.LINEAL)
        self.assertIsNone(resultado.valor)
        self.assertTrue(resultado.advertencias)

    def test_d23_documenta_convencion_en_limites(self) -> None:
        for n in (25, 50):
            resultado = tabla_d23(
                n, TipoN.N_CTE.value, "E", MetodoInterpolacion.LITERAL, "Arena limpia"
            )
            self.assertTrue(any("intervalo inferior" in aviso for aviso in resultado.advertencias))

    def test_fhwa_modulo_y_tipo_n(self) -> None:
        resultado = es_fhwa(10, TipoN.N60.value, 10, "DEF-ES-SPT-FHWA2002-ARENA-NC")
        self.assertAlmostEqual(resultado.valor, 10.1325)
        self.assertFalse(resultado.advertencias)
        condicionado = es_fhwa(10, TipoN.N_CTE.value, 10, "DEF-ES-SPT-FHWA2002-ARENA-NC")
        self.assertFalse(condicionado.valido)
        self.assertEqual(condicionado.estado.value, "Condicionado")

    def test_phi_rechaza_porcentaje_negativo(self) -> None:
        with self.assertRaises(ErrorCalculoGeotecnico):
            phi_cte_41(20, TipoN.N_CTE.value, "Arena limpia", -1)

    def test_indice_compresibilidad_y_limite(self) -> None:
        resultado = indice_compresibilidad_cte(10, TipoN.N_CTE.value)
        self.assertAlmostEqual(resultado.valor, 1.71 / (10**1.4))
        self.assertLess(resultado.minimo, resultado.valor)
        self.assertGreater(resultado.maximo, resultado.valor)
        with self.assertRaises(FueraDeDominio):
            indice_compresibilidad_cte(6.9, TipoN.N_CTE.value)


if __name__ == "__main__":
    unittest.main()
