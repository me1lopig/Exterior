import unittest

import pandas as pd

from servicios.adopcion import validar_adopciones


class TestAdopcion(unittest.TestCase):
    def test_exige_valor_y_justificacion(self) -> None:
        resultados = pd.DataFrame([{
            "adoptado": True, "valor_adoptado": pd.NA, "justificacion": "", "estado": "Valido",
            "parametro": "E", "grupo": "G01", "unidad_geotecnica": "UG-1",
            "minimo": 8.0, "maximo": 40.0,
        }])
        errores = validar_adopciones(resultados)
        self.assertTrue(any("falta el valor" in error for error in errores))

    def test_acepta_condicionado_justificado_en_intervalo(self) -> None:
        resultados = pd.DataFrame([{
            "adoptado": True, "valor_adoptado": 20.0, "justificacion": "Conversion de N documentada.",
            "estado": "Condicionado", "parametro": "E", "grupo": "G01", "unidad_geotecnica": "UG-1",
            "minimo": 8.0, "maximo": 40.0,
        }])
        self.assertEqual(validar_adopciones(resultados), [])

    def test_rechaza_adopcion_duplicada(self) -> None:
        base = {
            "adoptado": True, "valor_adoptado": 20.0, "justificacion": "Seleccion tecnica.",
            "estado": "Valido", "parametro": "E", "grupo": "G01", "unidad_geotecnica": "UG-1",
            "minimo": 8.0, "maximo": 40.0,
        }
        errores = validar_adopciones(pd.DataFrame([base, base]))
        self.assertTrue(any("Solo puede adoptarse" in error for error in errores))

    def test_rechaza_resultado_no_valido(self) -> None:
        resultados = pd.DataFrame([{
            "adoptado": True, "valor_adoptado": 20.0, "justificacion": "Seleccion tecnica.",
            "estado": "No valido", "parametro": "E", "grupo": "G01", "unidad_geotecnica": "UG-1",
            "minimo": 8.0, "maximo": 40.0,
        }])
        self.assertTrue(any("no valido" in error for error in validar_adopciones(resultados)))


if __name__ == "__main__":
    unittest.main()
