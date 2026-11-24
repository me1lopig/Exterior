import math
import unittest
from calculos.axial import Estrato, calcular


class AxialTests(unittest.TestCase):
    def test_estrato_y_cambio_cinco_metros(self):
        r = calcular(.2, 10, 0, [Estrato(0, 10, 100, 200)], 12, False)
        self.assertAlmostEqual(r['compresion'], math.pi*.2*(5*100+5*200)/1.65)
        self.assertAlmostEqual(r['traccion'], .75*r['compresion'])

    def test_inclinado_y_peso(self):
        r = calcular(.2, 10, 60, [Estrato(0, 6, 100, 100)], 6, True, 12)
        self.assertAlmostEqual(r['profundidad'], 5)
        self.assertAlmostEqual(r['traccion'], .6*r['fuste_compresion']+10)

    def test_cavidad(self):
        r = calcular(.2, 6, 0, [Estrato(0, 3, 100, 100), Estrato(3, 6, 100, 100, False)], 12, False)
        self.assertAlmostEqual(r['fuste_compresion'], math.pi*.2*3*100/1.65)

    def test_punta_y_estratigrafia(self):
        with self.assertRaises(ValueError):
            calcular(.2, 10, 0, [Estrato(0, 9, 100, 100)], 12, False)
        with self.assertRaises(ValueError):
            calcular(.2, 10, 0, [Estrato(0, 10, 100, 100)], 12, False, punta=1000, punta_justificada=True)


if __name__ == '__main__':
    unittest.main()
