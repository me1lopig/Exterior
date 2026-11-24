import unittest
from math import pi
from calculos.axial import Estrato, calcular
from calculos.avanzado import validar_inyeccion, validar_punta, longitud_necesaria
from calculos.estructural import seccion, axial_estructural

class AvanzadoTests(unittest.TestCase):
    def test_i_u_presiones(self):
        validar_inyeccion('IU',500,800)
        for tipo,p,pl in [('IU',499,800),('IR',600,1500),('IRS',1000,800),('IRS',1200,1500)]:
            with self.assertRaises(ValueError): validar_inyeccion(tipo,p,pl)
        validar_inyeccion('IRS',1500,1200)
    def test_diametro_limite(self):
        with self.assertRaises(ValueError): calcular(.3,10,0,[Estrato(0,15,100,100)],12,False)
    def test_punta_umbral_y_reconocimiento(self):
        self.assertEqual(validar_punta(.2,10,0,11,'Granular',40,50,2,'sintetico'),45)
        for prof,ns,emp in [(10.5,40,2),(11,30,2),(11,40,1.)]:
            with self.assertRaises(ValueError): validar_punta(.2,10,0,prof,'Granular',ns,50,emp,'sintetico')
    def test_longitud_exacta(self):
        e=[Estrato(0,5,100,200),Estrato(5,15,100,200)]
        nc=pi*.2*(5*100+3*200)/1.65
        self.assertAlmostEqual(longitud_necesaria(.2,12,0,e,12,False,nc,0),8)
        self.assertAlmostEqual(longitud_necesaria(.2,12,0,e,12,True,0,nc*.6),8)
        self.assertIsNone(longitud_necesaria(.2,12,0,e,12,False,1e6,0))
    def test_longitud_cavidad(self):
        e=[Estrato(0,5,100,100,False),Estrato(5,12,100,100)]
        self.assertAlmostEqual(longitud_necesaria(.2,10,0,e,6,False,pi*.2*200/1.45,0),7)
    def test_longitud_acciones_nulas(self):
        e=[Estrato(0,5,0,0,False),Estrato(5,12,100,100)]
        self.assertEqual(longitud_necesaria(.2,10,0,e,6,False,0,0),.1)
    def test_catalogo_geometria(self):
        s=seccion(139.7,7,0)
        self.assertAlmostEqual(s['a_nominal_mm2']/100,29.17,delta=.02)
        self.assertAlmostEqual(s['i_residual_mm4']/10000,643.81,delta=.5)
        self.assertLess(seccion(139.7,7,1)['a_residual_mm2'],s['a_residual_mm2'])
    def test_estructura_manual(self):
        s=axial_estructural(200,139.7,7,0,550,25,'Resto de casos','Con lodos',0,'sintetico',True)
        A=pi/4*(139.7**2-125.7**2)
        Ac=pi/4*200**2-A
        self.assertAlmostEqual(s['nc_kN'],(.85*Ac*25/1.5+.5*A*400)/(1.2*1.15)/1000)
        self.assertAlmostEqual(s['nt_kN'],.5*A*500/1.1/1000)
        self.assertFalse(s['uniones_acreditadas'])
    def test_pandeo_y_union(self):
        s=axial_estructural(200,139.7,7,1,550,25,'Machihembrada sin ensanchar y contacto a tope','Con lodos',10,'sintetico',True,100,50)
        self.assertAlmostEqual(s['R'],.8)
        self.assertEqual((s['fu_c'],s['fu_t']),(1,.5))
        self.assertEqual((s['nc_kN'],s['nt_kN']),(100,50))
        with self.assertRaises(ValueError): seccion(139.7,7,7)

if __name__=='__main__': unittest.main()
