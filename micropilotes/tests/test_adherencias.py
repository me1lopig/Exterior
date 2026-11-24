import unittest
from math import pi
from modelos.adherencias import preparar_estratos, resumen_aplicado, coeficiente_comun
from calculos.axial import calcular

def fila(h,t,lim,fr=1.65,activo=True):
    return dict(nombre='UG',espesor_m=h,inyeccion=t,adlim_kPa=lim,fr=fr,activo=activo)

class AdherenciasTests(unittest.TestCase):
    def test_factor_una_vez(self):
        e,d,fr=preparar_estratos([fila(10,'IU',165)],10)
        self.assertEqual(d[0]['admisible_kPa'],100)
        self.assertAlmostEqual(calcular(.2,10,0,e,12,False)['fuste_compresion'],pi*.2*10*100)
    def test_cruce_iu(self):
        e,d,fr=preparar_estratos([fila(2,'IU',66),fila(8,'IRS',165)],10,{1:99})
        self.assertEqual([x['adlim_kPa'] for x in resumen_aplicado(d,10)],[66,99,165])
        self.assertAlmostEqual(calcular(.2,10,0,e,12,False)['fuste_compresion'],pi*.2*(2*40+3*60+5*100))
        with self.assertRaises(ValueError): preparar_estratos([fila(10,'IR',165)],10)
    def test_sin_iu_innecesario(self):
        e,d,_=preparar_estratos([fila(5,'IU',80),fila(5,'IRS',165)],10)
        self.assertIsNone(d[1]['iu_kPa'])
    def test_fr_incoherente(self):
        with self.assertRaises(ValueError): coeficiente_comun([fila(5,'IU',80,1.45),fila(5,'IU',80,1.65)])
        with self.assertRaises(ValueError): coeficiente_comun([fila(5,'IU',80,1.5)])
    def test_control_opcional_y_fallo(self):
        preparar_estratos([fila(10,'IU',80)],10)
        with self.assertRaises(ValueError): preparar_estratos([fila(10,'IU',80)],10,presiones={0:(300,800)})
        preparar_estratos([fila(10,'IU',80)],10,presiones={0:(600,800)})
    def test_inactivo(self):
        e,d,_=preparar_estratos([fila(5,'IRS',None,activo=False)],5)
        self.assertEqual(resumen_aplicado(d,5)[0]['admisible_kPa'],0)
