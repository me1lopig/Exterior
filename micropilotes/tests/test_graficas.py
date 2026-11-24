import unittest
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
