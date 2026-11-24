import unittest
from visualizacion.vista_geotecnica import tabla_calculada
from visualizacion.graficas import perfil_adherencias

class VistaGeotecnicaTests(unittest.TestCase):
    def setUp(self):
        self.f=[dict(nombre='UG-01',inicio_m=0.,fin_m=3.,activo=True,inyeccion='IU'),
                dict(nombre='UG-02',inicio_m=3.,fin_m=25.,activo=True,inyeccion='IRS')]
        self.resumen=[dict(nombre='UG-01',espesor_m=3.,inyeccion='IU',admisible_kPa=40.),
                      dict(nombre='UG-02',espesor_m=2.,inyeccion='IU',admisible_kPa=60.),
                      dict(nombre='UG-02',espesor_m=7.,inyeccion='IRS',admisible_kPa=100.)]
    def test_cotas_y_recorte(self):
        t=tabla_calculada(self.f,self.resumen,0.)
        self.assertEqual([(x['inicio_m'],x['fin_efectivo_m']) for x in t],[(0,3),(3,5),(5,12)])
        self.assertAlmostEqual(sum(x['longitud_axial_m'] for x in t),12.)
        self.assertEqual([x['criterio'] for x in t],['','IU por limite de 5 m',''])
        self.assertEqual(t[-1]['admisible_kPa'],100.)
    def test_longitud_inclinada(self):
        t=tabla_calculada(self.f,self.resumen,60.)
        self.assertAlmostEqual(sum(x['longitud_axial_m'] for x in t),24.)
        self.assertEqual(t[-1]['fin_efectivo_m'],12.)
    def test_perfil_reconocido_y_punta(self):
        r={'profundidad':12.,'tramos':[
            dict(z_inicio=0,z_fin=3,r_lim=66,r_calculo=40),
            dict(z_inicio=3,z_fin=5,r_lim=99,r_calculo=60),
            dict(z_inicio=5,z_fin=12,r_lim=165,r_calculo=100)]}
        fig=perfil_adherencias(self.f,r,12.,0.)
        self.assertEqual(list(fig.layout.yaxis.range),[25.,0.])
        self.assertTrue(any(s.type=='rect' and s.y0==12 and s.y1==25 for s in fig.layout.shapes))
        self.assertTrue(any('L máxima' in a.text for a in fig.layout.annotations))
        self.assertEqual(max(fig.data[-1].y),12.)
        self.assertTrue(fig.to_json())
    def test_sin_terreno_sobrante(self):
        f=[dict(nombre='UG',inicio_m=0.,fin_m=5.,activo=True,inyeccion='IU')]
        r={'profundidad':5.,'tramos':[dict(z_inicio=0,z_fin=5,r_lim=66,r_calculo=40)]}
        fig=perfil_adherencias(f,r,5.,0.)
        self.assertFalse(any(s.type=='rect' for s in fig.layout.shapes))
