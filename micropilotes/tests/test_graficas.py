import unittest
from math import pi
from calculos.estructural import seccion
from visualizacion.graficas import (puntos_fuste, _envolvente, curvas_fuste,
    perfil_adherencias, contribucion, seccion_transversal, comparacion_parcial)

class GraficasTests(unittest.TestCase):
    def setUp(self):
        self.r={'profundidad':6.,'tramos':[
            dict(z_inicio=0,z_fin=5,longitud_axial=5,compresion=100,traccion=75,r_lim=80,r_calculo=48.5),
            dict(z_inicio=5,z_fin=6,longitud_axial=1,compresion=40,traccion=30,r_lim=150,r_calculo=90.9)]}
    def test_nodos(self):
        self.assertEqual(puntos_fuste(self.r),([0.,5.,6.],[0.,100.,140.],[0.,75.,105.]))
    def test_cruce_exacto(self):
        self.assertEqual(_envolvente([0,5,6],[0,100,140],120),([0,5,5.5,6],[0,100,120,120]))
    def test_figuras_serializables(self):
        filas=[dict(inicio_m=0,fin_m=6,activo=True,nombre='UG-01',inyeccion='IR')]
        figs=[perfil_adherencias(filas,self.r,6,0),curvas_fuste([('D=200',self.r)],0),
              contribucion(self.r),seccion_transversal(200,220,139.7,7,1,True),
              comparacion_parcial(self.r,dict(nc_kN=120,nt_kN=90),(110,80))]
        for f in figs:
            self.assertTrue(f.to_json())

class SeccionMermaTests(unittest.TestCase):
    def test_merma_a_escala(self):
        f=seccion_transversal(177.8,195.58,114.3,9,.6,False)
        sh=f.layout.shapes
        self.assertEqual(len(sh),5)
        self.assertAlmostEqual(sh[2].x1,57.15)
        self.assertAlmostEqual(sh[3].x1,56.55)
        self.assertAlmostEqual(sh[4].x1,48.15)
        self.assertEqual(sh[2].fillcolor,'#e58c47')
        self.assertIn('Acero perdido por corrosión',[x.name for x in f.data])
        s=seccion(114.3,9,.6)
        perdida=(s['a_nominal_mm2']-s['a_residual_mm2'])/100
        self.assertAlmostEqual(perdida,pi*.6*(114.3-.6)/100)
        self.assertIn(f'{perdida:.2f} cm²',f.layout.title.text)
        self.assertTrue(f.to_json())

    def test_sin_merma(self):
        f=seccion_transversal(177.8,195.58,114.3,9,0,True)
        self.assertEqual(len(f.layout.shapes),4)
        self.assertNotIn('Acero perdido por corrosión',[x.name for x in f.data])
        self.assertIn('0.00 cm² (0.00 %)',f.layout.title.text)

    def test_merma_invalida(self):
        with self.assertRaises(ValueError):
            seccion_transversal(177.8,195.58,114.3,9,9,False)
