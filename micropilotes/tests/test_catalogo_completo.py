import unittest
from math import pi
from modelos.tuberias_catalogo import CATALOGO, POR_ETIQUETA, personalizada
from modelos.aceros_catalogo import fy_referencia
from modelos.tablas_guia import perdida, recubrimiento, cr_libre
from calculos.limites_acero import limite_acero, longitud_cruce, envolvente

class CatalogoTests(unittest.TestCase):
    def test_catalogo_completo(self):
        self.assertEqual(len(CATALOGO),74)
        self.assertEqual(len(POR_ETIQUETA),74)
        self.assertEqual(min(t.de_mm for t in CATALOGO),43)
        self.assertEqual(max(t.de_mm for t in CATALOGO),298)
        self.assertEqual(sum(t.carga_catalogo_tf is None for t in CATALOGO),1)
        self.assertIsNone(POR_ETIQUETA['273 × 6 mm'].carga_catalogo_kN)
        t=POR_ETIQUETA['139.7 × 9 mm']
        self.assertEqual((t.A_cm2,t.I_cm4,t.W_cm3,t.peso_kg_m),(36.94,792.43,113.45,31))
        self.assertAlmostEqual(t.carga_catalogo_kN,194.2*9.80665)
    def test_geometria_personalizada(self):
        t=personalizada(100,10)
        self.assertAlmostEqual(t.A_cm2,9*pi)
        self.assertIsNone(t.carga_catalogo_tf)
    def test_tablas(self):
        self.assertEqual(fy_referencia('N80'),552)
        self.assertEqual(fy_referencia('S420'),420)
        self.assertEqual(perdida('Suelo natural sin alterar',50),.6)
        self.assertEqual(perdida('Relleno agresivo sin compactar',100),5.75)
        self.assertEqual(cr_libre(1,100),10)
        r=recubrimiento(200,150,'Lechada','Traccion',160)
        self.assertTrue(r['cuerpo_compatible'])
        self.assertFalse(r['union_compatible'])
        self.assertIsNone(recubrimiento(200,150,'Lechada','Compresion')['union_compatible'])
    def test_limites(self):
        t=POR_ETIQUETA['139.7 × 9 mm']
        s=limite_acero(t,550,0,'Resto de casos','Camisa perdida',0)
        A=pi/4*(139.7**2-121.7**2)
        self.assertAlmostEqual(s['A_fyd_c_kN'],A*400/1000)
        self.assertAlmostEqual(s['nc_kN'],A*400*.5/1200)
        self.assertAlmostEqual(s['nt_kN'],A*550*.5/1.21/1000)
        cor=limite_acero(t,550,1,'Resto de casos','Camisa perdida',10,100,50)
        self.assertEqual((cor['nc_kN'],cor['nt_kN']),(100,50))
        with self.assertRaises(ValueError): limite_acero(t,550,9,'Resto de casos','Camisa perdida',0)
    def test_envolvente(self):
        self.assertEqual(longitud_cruce([3,5,10],[10,20,70],40),7)
        self.assertEqual(envolvente([3,5,10],[10,20,70],40),([3,5,7,10],[10,20,40,40]))
        self.assertIsNone(longitud_cruce([3,5],[10,20],30))
        self.assertEqual(longitud_cruce([3,5],[10,20],5),3)
