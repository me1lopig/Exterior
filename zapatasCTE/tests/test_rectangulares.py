"""Pruebas de la malla B x L, estados de presión y advertencias."""
from __future__ import annotations

from dataclasses import replace
from math import tan, radians
import unittest

import numpy as np

from calculos.asientos import asiento_centro_cm, asiento_esquina_cm
from calculos.capacidad_portante import calcular_hundimiento_rectangular
from calculos.malla import calcular_geometria, calcular_malla, calcular_corridas, validar_entrada
from calculos.servicio import convertir_ksbl_a_ksp30
from modelos.datos import CapaSuelo, DatosAsientos, DatosHundimiento
from modelos.geometrias import RangoGeometrico, generar_geometrias, serie_rango
from utiles.tablas_malla import tabla_malla
from visualizacion.graficos_malla import mapa_calor,curvas_seccion,grafico_presiones_corridas


class MallaRectangularTest(unittest.TestCase):
    def setUp(self):
        self.h = DatosHundimiento(anchos_m=(1.5,2,2.5,3),longitud_corrida_m=100)
        self.s = DatosAsientos(capas=(
            CapaSuelo("A",0,2.5,15,.3),CapaSuelo("B",2.5,10,1200,.2)))

    def test_geometrias_solo_b_menor_igual_l(self):
        g=generar_geometrias(RangoGeometrico())
        self.assertEqual(len(g),26)
        self.assertTrue(all(0<b<=l for b,l in g))
        self.assertIn((3.,3.),g)
        self.assertNotIn((3.,2.5),g)
        self.assertEqual(serie_rango(1.5,3.1,.5),(1.5,2.,2.5,3.))

    def test_incrementos_invalidos(self):
        for r in [RangoGeometrico(incr_b=0),RangoGeometrico(bmin=5,bmax=2),
                  RangoGeometrico(bmin=5,bmax=6,lmin=1,lmax=3)]:
            with self.assertRaises(ValueError): generar_geometrias(r)

    def test_factores_rectangulares_cte(self):
        r=calcular_hundimiento_rectangular(self.h,2,4)
        self.assertAlmostEqual(r.sc,1.1)
        self.assertAlmostEqual(r.sq,1+1.5*tan(radians(30))*.5)
        self.assertAlmostEqual(r.sgamma,.85)
        self.assertAlmostEqual(r.q0_kpa,9)

    def test_cuadrada_reproduce_hundimiento_original(self):
        r=calcular_hundimiento_rectangular(self.h,1.5,1.5)
        self.assertAlmostEqual(r.q_h_d_mpa,.15048079832640052,places=12)

    def test_neto_bruto_es_consistente(self):
        r=calcular_geometria(2,3,self.h,self.s)
        q0=r.q0_kpa/1000
        self.assertAlmostEqual(r.q_hund_bruta_mpa,r.q_hund_neta_mpa+q0)
        self.assertAlmostEqual(r.q_serv_bruta_mpa,r.q_serv_neta_mpa+q0)
        self.assertAlmostEqual(r.q_serv_neta_mpa,min(r.q_hund_neta_mpa,r.q_asiento_neta_mpa))

    def test_asiento_centro_usa_cuatro_cuadrantes(self):
        capas=(CapaSuelo('A',0,5000,50,.3),)
        centro=asiento_centro_cm(1,2,4,capas)
        cuadrante=asiento_esquina_cm(1,1,2,capas)
        self.assertAlmostEqual(centro,4*cuadrante,places=10)

    def test_balasto_rectangular(self):
        r=calcular_geometria(2,3,self.h,self.s)
        self.assertAlmostEqual(r.ksp30_mn_m3,convertir_ksbl_a_ksp30(
            r.ks_bl_mn_m3,2,3,'Cohesivo'))
        granular=calcular_geometria(2,3,self.h,replace(self.s,tipo_material_balasto='Granular'))
        self.assertNotAlmostEqual(granular.ksp30_mn_m3,r.ksp30_mn_m3)

    def test_no_se_inventa_presion_si_no_hay_margen(self):
        h=replace(self.h,phi_deg=0,cohesion_kpa=0,
                  considerar_sobrecarga=False)
        r=calcular_geometria(2,3,h,self.s)
        self.assertIsNone(r.q_serv_neta_mpa)
        self.assertEqual(r.limitacion,'No válido')
        self.assertGreater(len(r.avisos),0)

    def test_avisos_de_profundidad(self):
        s=replace(self.s,capas=(CapaSuelo('A',0,3,20,.3),))
        r=calcular_geometria(2,3,self.h,s)
        self.assertFalse(r.espesor_2b)
        self.assertTrue(any('2B' in w for w in r.avisos))

    def test_entrada_estratos_discontinuos(self):
        s=replace(self.s,capas=(CapaSuelo('A',0,2,20,.3),CapaSuelo('B',3,5,20,.3)))
        self.assertTrue(any('huecos' in e for e in validar_entrada(self.h,s)))

    def test_no_drenaje_impone_phi_cero(self):
        h=replace(self.h,situacion_drenaje='Transitoria a corto plazo (sin drenaje)',phi_deg=30)
        self.assertTrue(any('phi = 0' in e for e in validar_entrada(h,self.s)))
        h=replace(h,phi_deg=0,cohesion_kpa=50)
        self.assertGreater(calcular_hundimiento_rectangular(h,2,3).q_h_d_mpa,0)

    def test_prohibido_factor_profundidad_baja(self):
        h=replace(self.h,considerar_terreno_sobre_base=True,profundidad_base_m=.5)
        self.assertTrue(any('D < 2' in e for e in validar_entrada(h,self.s)))

    def test_corrida_interna_100(self):
        res=calcular_corridas((1.5,2),self.h,self.s)
        self.assertTrue(all(r.l_m==100 for r in res))

    def test_grafico_corridas_presiones_netas_brutas_y_sin_servicio(self):
        corridas=calcular_corridas((1.5,2.,2.5),self.h,self.s)
        tabla=tabla_malla(corridas)
        for modo,sufijo in (("Netas","neta"),("Brutas","bruta")):
            fig=grafico_presiones_corridas(tabla,modo)
            self.assertEqual(len(fig.data),3)
            self.assertEqual(list(fig.data[0].x),sorted(tabla["B (m)"].tolist()))
            for i,columna in enumerate((f"q hund. {sufijo} (MPa)",
                                       f"q asientos {sufijo} (MPa)",
                                       f"q servicio {sufijo} (MPa)")):
                np.testing.assert_allclose(fig.data[i].y,tabla.sort_values("B (m)")[columna])
            self.assertIn("Presión",fig.layout.yaxis.title.text)
        inv=tabla.copy()
        inv.loc[inv.index[1],"q servicio neta (MPa)"]=None
        fig=grafico_presiones_corridas(inv,"Netas")
        self.assertTrue(np.isnan(fig.data[2].y[1]))
        self.assertFalse(fig.data[2].connectgaps)
        with self.assertRaises(ValueError):
            grafico_presiones_corridas(tabla,"Efectivas")
        with self.assertRaises(ValueError):
            grafico_presiones_corridas(tabla.iloc[0:0])

    def test_tabla_graficos_generan_figuras(self):
        g=generar_geometrias(RangoGeometrico())
        df=tabla_malla(calcular_malla(g,self.h,self.s))
        self.assertEqual(len(df),26)
        self.assertGreaterEqual(len(mapa_calor(df,'Presión admisible de servicio (neta)').data),2)
        self.assertGreaterEqual(len(curvas_seccion(df,2).data),3)

if __name__=='__main__': unittest.main()
