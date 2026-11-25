import unittest
import pandas as pd
from visualizacion.perfiles import series_entrada,series_efectivas
from visualizacion.graficas import perfil_adherencias

class PerfilesTests(unittest.TestCase):
    def setUp(self):
        self.filas=[dict(nombre='UG-01',inicio_m=0.,fin_m=8.,activo=True,inyeccion='IRS',IU_MPa=.08,IR_MPa=.11,IRS_MPa=.15),
                    dict(nombre='UG-02',inicio_m=8.,fin_m=15.,activo=False,inyeccion='IR',IU_MPa=.10,IR_MPa=None,IRS_MPa=.20)]
        self.r=dict(profundidad=12.,tramos=[
            dict(z_inicio=0.,z_fin=5.,r_lim=80.,r_calculo=80/1.65),
            dict(z_inicio=5.,z_fin=8.,r_lim=150.,r_calculo=150/1.65),
            dict(z_inicio=8.,z_fin=12.,r_lim=0.,r_calculo=0.)])
        self.datos={'IRS':dict(casos={200:self.r},unitarios=pd.DataFrame(dict(D_mm=[200.,200.,200.],z_inicio_m=[0.,5.,8.],z_fin_m=[5.,8.,12.],qc_kN_m=[30.,57.,0.],qt_kN_m=[22.5,42.75,0.])))}

    def test_entrada_no_altera_valores(self):
        s=series_entrada(self.filas,['IR','IRS'])
        self.assertEqual(s[0]['x'],[110.,110.,None,None])
        self.assertEqual(s[1]['x'],[150.,150.,200.,200.])
        self.assertEqual(s[1]['y'],[0.,8.,8.,15.])

    def test_efectivas_sin_recalculo(self):
        s=series_efectivas(self.datos,['IU','IRS'],200,'r_lim')
        self.assertEqual(len(s),1)
        self.assertEqual(s[0]['nombre'],'IRS')
        self.assertEqual(s[0]['x'],[80.,80.,150.,150.,0.,0.])
        self.assertEqual(s[0]['y'],[0.,5.,5.,8.,8.,12.])
        adm=series_efectivas(self.datos,['IRS'],200,'r_calculo')[0]
        self.assertAlmostEqual(adm['x'][2],150/1.65)

    def test_unitarios_y_figura(self):
        s=series_efectivas(self.datos,['IRS'],200,'qt_kN_m')
        self.assertEqual(s[0]['x'],[22.5,22.5,42.75,42.75,0.,0.])
        f=perfil_adherencias(self.filas,self.r,12,0,series=s,unidad='Resistencia unitaria (kN/ml)')
        self.assertEqual(f.layout.xaxis2.title.text,'Resistencia unitaria (kN/ml)')
        self.assertEqual(list(f.data[-1].y),s[0]['y'])
        self.assertFalse(f.data[-1].connectgaps)
        self.assertTrue(f.to_json())

    def test_modo_original_y_vacio(self):
        f=perfil_adherencias(self.filas,self.r,12,0)
        self.assertEqual([t.name for t in f.data[-2:]],['Adherencia límite','Adherencia de cálculo'])
        f=perfil_adherencias(self.filas,self.r,12,0,series=[],entrada=True)
        self.assertEqual(len(f.data),3)
        self.assertTrue(f.to_json())
