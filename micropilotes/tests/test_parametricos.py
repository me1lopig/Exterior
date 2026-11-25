import unittest
from math import pi
import pandas as pd
from calculos.axial import calcular,Estrato
from resultados.parametricos import *
from visualizacion.parametricas import perfil_unitario,barras_unitarias,multiples

class ResultadosTests(unittest.TestCase):
    def test_unitario_iu_inclinado_inactivo(self):
        filas=[dict(nombre='A',inicio_m=0,fin_m=8,inyeccion='IRS',activo=True),
               dict(nombre='B',inicio_m=8,fin_m=12,inyeccion='IR',activo=False)]
        r=calcular(.2,12,30,[Estrato(0,8,80,150),Estrato(8,12,0,0,False)],12,True)
        df=unitarios(filas,{200:r})
        self.assertEqual(df.inyeccion_efectiva.tolist(),['IU','IRS','Inactivo'])
        self.assertAlmostEqual(df.qc_kN_m.iloc[0],pi*.2*80/1.65)
        self.assertAlmostEqual(df.qc_kN_m.iloc[1],pi*.2*150/1.65)
        self.assertEqual(df.qc_kN_m.iloc[2],0)
        self.assertAlmostEqual((df.qc_kN_m*df.L_axial_m).sum(),r['fuste_compresion'])
        self.assertAlmostEqual((df.qt_kN_m*df.L_axial_m).sum(),r['fuste_traccion'])
        self.assertEqual(len(matriz_unitaria(df,'c')),3)
        self.assertEqual(len(perfil_unitario(df,'c').data),2)
        self.assertEqual(len(barras_unitarias(df,'t').data),1)
    def test_matrices_cruce_y_sensibilidad(self):
        b=pd.DataFrame(dict(D_mm=[200,200,200],L_m=[5.,10.,15.],Rc_fuste_kN=[100.,200.,300.],Rt_fuste_kN=[75.,150.,225.]))
        a=[dict(alternativa='A',D_mm=200,limite_c_kN=250.,limite_t_kN=180.),
           dict(alternativa='B',D_mm=200,limite_c_kN=None,limite_t_kN=None)]
        m=matriz_parcial(b,a,'c')
        self.assertEqual(m.A.tolist(),[100,200,250])
        self.assertTrue(m.B.isna().all())
        self.assertAlmostEqual(longitudes(b,a,'c',250).L_necesaria_m.iloc[0],12.5)
        self.assertEqual(longitudes(b,a,'c',260).estado.iloc[0],'Límite de armadura')
        self.assertAlmostEqual(aprovechamiento(m,250).A.iloc[-1],100)
        self.assertEqual(matriz_fuste(b,'t').iloc[-1,0],225)
        self.assertAlmostEqual(sensibilidad(b,20).iloc[0].Rc_fuste_kN,80)
        self.assertEqual(len(multiples(b,a,'c').data),1)
