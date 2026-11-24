import unittest
from math import pi
from calculos.axial import Estrato, calcular
from calculos.barrido import barrido, longitudes_barrido

class BarridoTests(unittest.TestCase):
    def setUp(self):
        self.e=[Estrato(0,3,80,80),Estrato(3,15,100,200)]
    def test_nodos_y_extremos(self):
        self.assertEqual(longitudes_barrido(2,8,2,0,self.e),[2,3,4,5,6,8])
        self.assertEqual(longitudes_barrido(2,7,2,0,self.e),[2,3,4,5,6,7])
    def test_inclinado(self):
        x=longitudes_barrido(2,12,4,60,self.e)
        self.assertTrue(any(abs(v-10)<1e-8 for v in x))
        self.assertTrue(any(abs(v-6)<1e-8 for v in x))
    def test_punta_solo_hipotetica(self):
        r=barrido(.2,10,10,1,0,self.e,12,False,True)[0]
        rc=pi*.2*(3*80+2*100+5*200)/1.65
        self.assertAlmostEqual(r['Rc_fuste_kN'],rc)
        self.assertAlmostEqual(r['punta_max_hipotetica_kN'],.15*rc)
        self.assertAlmostEqual(r['Rc_max_hipotetica_kN'],1.15*rc)
        self.assertAlmostEqual(r['Rt_fuste_kN'],.75*rc)
        self.assertIsNone(barrido(.2,10,10,1,0,self.e,12,False)[0]['Rc_max_hipotetica_kN'])
    def test_sin_extrapolar(self):
        for args in [(2,16,1,0),(3,2,1,0),(2,3,0,0),(2,3,1e-9,0)]:
            with self.assertRaises(ValueError): longitudes_barrido(*args,self.e)
    def test_cavidad_y_minoracion(self):
        e=[Estrato(0,3,100,100,False),Estrato(3,10,100,200)]
        for f in barrido(.2,1,10,1,0,e,6,True):
            r=calcular(.2,f['L_m'],0,e,6,True)
            self.assertAlmostEqual(f['Rc_fuste_kN'],r['fuste_compresion'])
            self.assertAlmostEqual(f['Rt_fuste_kN'],.6*f['Rc_fuste_kN'])
