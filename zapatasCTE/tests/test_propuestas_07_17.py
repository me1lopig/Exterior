"""PROP-07..12 y PROP-14..17: pruebas de gráficas y estudios exploratorios."""
from __future__ import annotations

from dataclasses import replace
import unittest

import numpy as np

from calculos.analisis_corridas import (
    FACTORES_L_B, convergencia_corrida, convergencia_porcentaje_final,
    comparativa_corridas, hundimiento_corrida_limite,
    sensibilidad_nivel_freatico,
)
from calculos.capacidad_portante import calcular_hundimiento_rectangular
from calculos.malla import calcular_corridas, calcular_malla
from modelos.datos import CapaSuelo, DatosAsientos, DatosHundimiento
from modelos.geometrias import RangoGeometrico, generar_geometrias
from utiles.tablas_malla import CAMPOS_MAPA, tabla_malla
from visualizacion.graficos_corridas import (
    mapa_calor_corridas, grafico_balasto, grafico_convergencia,
    grafico_comparativa, grafico_sensibilidad,
)


class NuevasMejorasTest(unittest.TestCase):
    def setUp(self):
        self.h=DatosHundimiento(
            profundidad_base_m=1, gamma_efectivo_kn_m3=10,
            gamma_aparente_kn_m3=19, nivel_freatico_m=2,
        )
        self.s=DatosAsientos(
            metodo_centro="superposicion",
            capas=(CapaSuelo("A",0,3,20,.30),
                   CapaSuelo("B",3,20,120,.22)),
        )

    def test_mapas_corridas_mismas_nueve_variables_y_una_columna(self):
        tc=tabla_malla(calcular_corridas((1.5,2.,2.5),self.h,self.s))
        self.assertEqual(len(CAMPOS_MAPA),9)
        for etiqueta in CAMPOS_MAPA:
            with self.subTest(variable=etiqueta):
                fig=mapa_calor_corridas(tc,etiqueta)
                self.assertEqual(len(fig.data[0].z),3)
                self.assertTrue(all(len(fila)==1 for fila in fig.data[0].z))
                self.assertEqual(len(fig.data[1].y),3)
                self.assertEqual(len(fig.layout.annotations),3)

    def test_mapa_corridas_sin_servicio_valido(self):
        tc=tabla_malla(calcular_corridas((1.5,2.),self.h,self.s))
        tc.loc[tc.index[0],"q servicio neta (MPa)"]=None
        fig=mapa_calor_corridas(tc,"Presión admisible de servicio (neta)")
        self.assertTrue(np.isnan(fig.data[0].z[0][0]))
        self.assertIn("—",[a.text for a in fig.layout.annotations])

    def test_balasto_rectangular_y_corridas(self):
        tc=tabla_malla(calcular_corridas((1.5,2.,2.5),self.h,self.s))
        fig=grafico_balasto(tc,corrida=True)
        self.assertEqual(len(fig.data),2)
        np.testing.assert_allclose(fig.data[0].y,tc["ks,BL (MN/m³)"])
        g=generar_geometrias(RangoGeometrico())
        t=tabla_malla(calcular_malla(g,self.h,self.s))
        fig2=grafico_balasto(t,b=2.)
        self.assertEqual(len(fig2.data),2)
        self.assertTrue(all(float(x)==2. for x in t[t["B (m)"]==2.]["B (m)"]))

    def test_convergencia_finitos_y_limite_hundimiento(self):
        b=2.
        t=convergencia_corrida(b,self.h,self.s)
        self.assertEqual(tuple(t["L/B"]),FACTORES_L_B)
        self.assertAlmostEqual(t.iloc[0]["L (m)"],4.)
        self.assertEqual(len(grafico_convergencia(t).data),3)
        self.assertGreaterEqual(convergencia_porcentaje_final(t),0)
        q_lim=hundimiento_corrida_limite(b,self.h)
        q_fin=calcular_hundimiento_rectangular(self.h,b,1000000*b).q_h_d_mpa
        self.assertAlmostEqual(q_lim,q_fin,places=5)

    def test_comparativa_distingue_asientos_finitos_de_limite(self):
        df=comparativa_corridas(2.,self.h,self.s)
        self.assertEqual(len(df),3)
        self.assertTrue(np.isnan(df.iloc[-1]["q asientos neta (MPa)"]))
        self.assertTrue(np.isnan(df.iloc[-1]["q servicio neta (MPa)"]))
        self.assertEqual(len(grafico_comparativa(df).data),3)
        historical=calcular_corridas((2.,),self.h,self.s)[0]
        self.assertAlmostEqual(df.iloc[0]["q hund. neta (MPa)"],
                               historical.q_hund_neta_mpa)

    def test_sensibilidad_nf_tramos_y_caso_flujo(self):
        df=sensibilidad_nivel_freatico(2,3,self.h,self.s,0,6,61)
        self.assertEqual(len(df),61)
        self.assertAlmostEqual(df.iloc[0]["gamma_k (kN/m³)"],10.)
        self.assertAlmostEqual(
            float(df.loc[np.isclose(df["NF bajo rasante (m)"],2),
                         "gamma_k (kN/m³)"].iloc[0]),14.5)
        self.assertAlmostEqual(df.iloc[-1]["gamma_k (kN/m³)"],19.)
        self.assertEqual(len(grafico_sensibilidad(df).data),3)
        hf=replace(self.h,flujo_ascendente=True,gradiente_vertical=.4)
        flujo=sensibilidad_nivel_freatico(2,3,hf,self.s,0,6,7)
        self.assertTrue(np.allclose(flujo["gamma_k (kN/m³)"],10-.4*9.81))

    def test_entradas_invalidas(self):
        with self.assertRaises(ValueError): convergencia_corrida(0,self.h,self.s)
        with self.assertRaises(ValueError): sensibilidad_nivel_freatico(2,3,self.h,self.s,5,2)
        with self.assertRaises(ValueError): grafico_balasto(tabla_malla([]),corrida=True)
        with self.assertRaises(ValueError): mapa_calor_corridas(tabla_malla([]),
            "Presión admisible de servicio (neta)")


if __name__=="__main__":
    unittest.main()
