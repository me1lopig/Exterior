"""Contrastes independientes de ecuaciones, geometría y salidas visuales."""
from __future__ import annotations

from dataclasses import replace
from math import radians, exp, pi, sin, tan
import unittest

import pandas as pd

from calculos.capacidad_portante import (
    _cohesion_representativa, factores_capacidad, calcular_hundimiento_rectangular,
)
from calculos.servicio import convertir_ksbl_a_ksp30
from modelos.datos import CapaSuelo, DatosAsientos, DatosHundimiento
from calculos.malla import calcular_malla
from modelos.geometrias import RangoGeometrico, generar_geometrias
from utiles.tablas_malla import tabla_malla
from visualizacion.graficos_malla import mapa_calor, AZULES


class AuditoriaCTETest(unittest.TestCase):
    def test_factores_capacidad_cte_f13_f15_independiente(self):
        phi=radians(30)
        nq=(1+sin(phi))/(1-sin(phi))*exp(pi*tan(phi))
        nc=(nq-1)/tan(phi)
        ng=1.5*(nq-1)*tan(phi)
        calculados=factores_capacidad(30)
        self.assertAlmostEqual(calculados.nq,nq,places=11)
        self.assertAlmostEqual(calculados.nc,nc,places=11)
        self.assertAlmostEqual(calculados.ngamma,ng,places=11)

    def test_sin_drenaje_cte_n_c_514_y_reduccion_talud(self):
        h=DatosHundimiento(situacion_drenaje='Transitoria a corto plazo (sin drenaje)',
                            phi_deg=0,cohesion_kpa=50,considerar_sobrecarga=False,
                            inclinacion_talud_deg=0)
        b,l=2,4
        esperado=50*5.14*(1+.2*b/l)/3/1000
        self.assertAlmostEqual(calcular_hundimiento_rectangular(h,b,l).q_h_d_mpa,esperado,places=11)
        con_talud=replace(h,inclinacion_talud_deg=10)
        calculo=calcular_hundimiento_rectangular(con_talud,b,l)
        self.assertAlmostEqual(calculo.q_h_d_mpa,esperado-2*radians(10)*50/3/1000,places=11)

    def test_perfil_cu_respecto_z_inicial(self):
        h=DatosHundimiento(situacion_drenaje='Transitoria a corto plazo (sin drenaje)',
            cu_aumenta_con_profundidad=True,profundidad_base_m=2,
            cu_z_inicial_m=1,cu_inicial_kpa=30,
            cu_z_final_m=6,cu_final_kpa=60)
        self.assertAlmostEqual(_cohesion_representativa(h,2),39.,places=10)

    def test_balasto_cte_zapata_cuadrada_sin_factor_rectangular(self):
        ks=18.0; B=2.0
        self.assertAlmostEqual(convertir_ksbl_a_ksp30(ks,B,B,'Cohesivo'),ks*B/0.30)
        self.assertAlmostEqual(convertir_ksbl_a_ksp30(ks,B,B,'Granular'),ks*(2*B/(B+.3))**2)
        L=4.0
        self.assertAlmostEqual(convertir_ksbl_a_ksp30(ks,B,L,'Cohesivo'),ks/(1+B/(2*L))*B/.3)

    def test_q0_automatica_9kpa_y_conmutador(self):
        h=DatosHundimiento(gamma_sobrecarga_kn_m3=18,altura_sobrecarga_m=.5)
        r=calcular_hundimiento_rectangular(h,2,3)
        self.assertAlmostEqual(r.q0_kpa,9)
        self.assertAlmostEqual(calcular_hundimiento_rectangular(replace(h,considerar_sobrecarga=False),2,3).q0_kpa,0)

    def test_mapa_azul_textos_y_celdas_invalidas(self):
        h=DatosHundimiento()
        s=DatosAsientos(metodo_centro='superposicion',capas=(CapaSuelo('A',0,20,20,.3),))
        g=generar_geometrias(RangoGeometrico(bmin=1,bmax=2,incr_b=.5,lmin=1,lmax=2,incr_l=.5))
        df=tabla_malla(calcular_malla(g,h,s))
        fig=mapa_calor(df,'Presión admisible de servicio (neta)')
        self.assertEqual(fig.data[0].colorscale[0][1],AZULES[0][1])
        self.assertIsNone(fig.data[0].z[2][0])
        texto_neto=f"{df.iloc[0]['q servicio neta (MPa)']:.3f}"
        self.assertIn(texto_neto,[ann.text for ann in fig.layout.annotations])
        self.assertTrue(any(ann.text=='–' for ann in fig.layout.annotations))
        self.assertGreater(len(fig.data[1].text),0)
        self.assertIn('Hundimiento neto',fig.data[1].text[0])


if __name__ == '__main__': unittest.main()
