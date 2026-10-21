import unittest

from calculos.errores import ErrorCalculoGeotecnico, FueraDeDominio
from calculos.interpolacion import interpolar_lineal


class TestInterpolacion(unittest.TestCase):
    def test_interpolacion(self) -> None:
        self.assertAlmostEqual(interpolar_lineal(5, [0, 10], [20, 40]), 30)

    def test_bloqueo_extrapolacion(self) -> None:
        with self.assertRaises(FueraDeDominio):
            interpolar_lineal(-1, [0, 10], [20, 40])

    def test_tabla_mal_formada(self) -> None:
        with self.assertRaises(ErrorCalculoGeotecnico):
            interpolar_lineal(2, [0, 0, 3], [1, 2, 3])


if __name__ == "__main__":
    unittest.main()

