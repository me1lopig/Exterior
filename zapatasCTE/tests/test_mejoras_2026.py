"""Pruebas de MOD-01/02/03 y del diagnóstico Boussinesq 2D."""
from __future__ import annotations

from dataclasses import replace
import unittest

import numpy as np
import pandas as pd

from calculos.agua import GAMMA_AGUA_KN_M3, gamma_sumergido_desde_saturado
from calculos.capacidad_portante import _peso_especifico_representativo
from calculos.bulbo_2d import influencia_rectangular, influencia_corrida, malla_influencia
from calculos.diagnostico_asientos import factor_boussinesq_centro
from modelos.datos import CapaSuelo, DatosHundimiento, DatosAsientos
from calculos.malla import calcular_geometria
from utiles.tablas_malla import CAMPOS_MAPA, tabla_malla
from visualizacion.graficos_malla import AZULES, mapa_calor
from visualizacion.graficos_bulbo_2d import figura_seccion_bulbo


class MejorasZapatasTest(unittest.TestCase):
    def test_peso_saturado_y_casos_cte(self):
        self.assertAlmostEqual(gamma_sumergido_desde_saturado(20.0), 10.19)
        with self.assertRaises(ValueError):
            gamma_sumergido_desde_saturado(9.81)
        with self.assertRaises(ValueError):
            gamma_sumergido_desde_saturado(float("nan"))
        h=DatosHundimiento(profundidad_base_m=1.,gamma_aparente_kn_m3=19.,
                          gamma_efectivo_kn_m3=10.,nivel_freatico_m=1.)
        self.assertAlmostEqual(_peso_especifico_representativo(h,2),10.)
        self.assertAlmostEqual(_peso_especifico_representativo(replace(h,nivel_freatico_m=2.),2),14.5)
        self.assertAlmostEqual(_peso_especifico_representativo(replace(h,nivel_freatico_m=3.),2),19.)
        hf=replace(h,flujo_ascendente=True,gradiente_vertical=.4)
        self.assertAlmostEqual(_peso_especifico_representativo(hf,2),10.-.4*GAMMA_AGUA_KN_M3)

    def test_mapa_nueve_campos_y_azules_claros(self):
        self.assertEqual(len(CAMPOS_MAPA),9)
        self.assertTrue(all("bruta" in v for v in [
            CAMPOS_MAPA["Presión admisible de servicio (bruta)"],
            CAMPOS_MAPA["Presión admisible por hundimiento (bruta)"],
            CAMPOS_MAPA["Presión admisible por asientos (bruta)"]]))
        self.assertEqual(AZULES[-1][1],"#78add4")
        h=DatosHundimiento()
        s=DatosAsientos(metodo_centro="superposicion",
                        capas=(CapaSuelo("A",0,20,20,.3),))
        df=tabla_malla([calcular_geometria(2,3,h,s)])
        fig=mapa_calor(df,"Presión admisible por asientos (bruta)")
        self.assertGreaterEqual(len(fig.data),2)
        self.assertTrue(any(a.text for a in fig.layout.annotations))

    def test_rectangulo_coincide_con_1d_bajo_centro(self):
        for b,l,z in [(2.,2.,.5),(2.,3.,1.),(2.,4.,3.),(1.5,8.,7.)]:
            actual=float(influencia_rectangular(0.,z,b,l))
            esperado=factor_boussinesq_centro(b,l,z)
            self.assertAlmostEqual(actual,esperado,places=10)

    def test_rectangulo_simetria_y_banda_infinita(self):
        x=np.array([.0,.5,1.5,3.])
        z=np.array([1.,1.,1.,1.])
        np.testing.assert_allclose(influencia_rectangular(x,z,2,3),
                                   influencia_rectangular(-x,z,2,3),atol=1e-12)
        for profundidad in (.2,1.,4.):
            self.assertAlmostEqual(float(influencia_rectangular(0,profundidad,2,2000)),
                                   float(influencia_corrida(0,profundidad,2)),delta=1e-6)
        self.assertAlmostEqual(float(influencia_corrida(0,1,2)),.8183098861837907,places=10)
        xx,zz,matriz=malla_influencia(2,3,nx=41,nz=51)
        self.assertEqual(matriz.shape,(51,41))
        self.assertTrue(np.isfinite(matriz).all())

    def test_representacion_capas_nivel_freatico_y_corrida(self):
        capas=(CapaSuelo("A",0,3,30,.3),CapaSuelo("B",3,9,100,.2))
        fig=figura_seccion_bulbo(2,3,1.5,4.2,capas,200)
        self.assertEqual(len(fig.data),6)
        self.assertTrue(any("freático" in (a.text or "").lower() for a in fig.layout.annotations))
        fig_corrida=figura_seccion_bulbo(2,None,1.5,4.2,capas,200,corrida=True)
        self.assertEqual(len(fig_corrida.data),6)
        with self.assertRaises(ValueError):
            figura_seccion_bulbo(2,3,1.5,4.2,capas,-10)


if __name__ == "__main__":
    unittest.main()
