import unittest
from calculos.avanzado import estrato_con_inyeccion
from calculos.axial import calcular


class InyeccionTramosTests(unittest.TestCase):
    def test_cambio_y_cinco_metros(self):
        filas = [
            dict(inicio_m=0, fin_m=7, inyeccion='IR', iu_kPa=100, seleccion_kPa=200, pi_kPa=600, plim_kPa=800, activo=True),
            dict(inicio_m=7, fin_m=10, inyeccion='IU', iu_kPa=75, seleccion_kPa=999, pi_kPa=600, plim_kPa=800, activo=True),
        ]
        r = calcular(.2, 10, 0, [estrato_con_inyeccion(f, 10) for f in filas], 12, True)
        self.assertEqual([t['r_lim'] for t in r['tramos']], [100, 200, 75])
        self.assertEqual([t['longitud_axial'] for t in r['tramos']], [5, 2, 3])

    def test_validacion_por_fila(self):
        fila = dict(inicio_m=0, fin_m=10, inyeccion='IRS', iu_kPa=100, seleccion_kPa=200, pi_kPa=600, plim_kPa=800, activo=True)
        with self.assertRaises(ValueError):
            estrato_con_inyeccion(fila, 10)
        fila['inyeccion'] = 'desconocida'
        with self.assertRaises(ValueError):
            estrato_con_inyeccion(fila, 10)
