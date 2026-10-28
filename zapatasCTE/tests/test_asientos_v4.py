"""Comprobacion independiente de formula, reparto, tensiones y profundidad."""
from __future__ import annotations

from dataclasses import replace
from math import pi
import unittest

import numpy as np

from calculos.asientos import asiento_centro_cm
from calculos.diagnostico_asientos import (
    calcular_perfil_bulbo, contribuciones_steinbrenner, descarga_preexistente_kpa,
    factor_boussinesq_centro, profundidad_porcentaje_asiento, tension_inicial_kpa,
)
from calculos.malla import calcular_geometria
from modelos.datos import CapaSuelo,DatosAsientos,DatosHundimiento
from visualizacion.graficos_asientos import figura_bulbo, figura_asiento_acumulado, figura_contribuciones
import pandas as pd


class AsientosV4Test(unittest.TestCase):
    def setUp(self):
        self.h = DatosHundimiento()
        self.s = DatosAsientos(metodo_centro="superposicion",capas=(
            CapaSuelo("A",0,2.5,15,.30),CapaSuelo("B",2.5,10,1200,.20)))

    def test_referencia_ministerio_5_casos(self):
        # Cinco ejemplos publicados, parametros transcritos en informe de auditoria.
        casos=[("E-1",112,30,.3,2.3,12,17,13.7),
               ("P-1",269,30,.3,4,6,9.95,33.9),
               ("P-2",681,900,.25,3,3,100000,2.4),
               ("P-3",648,900,.25,3,3,100000,2.3),
               ("E-2",112,30,.3,2.3,12,6,9.8)]
        for nombre, q_kpa, e, nu, b, l, h, ref_mm in casos:
            with self.subTest(nombre=nombre):
                capas=(CapaSuelo('Unica',0,h,e,nu),)
                obtenido_mm=10*asiento_centro_cm(q_kpa/1000,b,l,capas,'superposicion')
                self.assertAlmostEqual(obtenido_mm,ref_mm,delta=.10)

    def test_sumatoria_por_capas_igual_motor_centro(self):
        for metodo in ('excel','superposicion'):
            s=replace(self.s,metodo_centro=metodo)
            filas=contribuciones_steinbrenner(2,3,s,.2)
            self.assertAlmostEqual(filas[-1]['Asiento acumulado (mm)'],
                                   asiento_centro_cm(.2,2,3,s.capas,metodo)*10,places=8)
            self.assertAlmostEqual(sum(f['Contribucion (%)'] for f in filas),100,places=10)
            self.assertEqual(profundidad_porcentaje_asiento(filas,90),2.5)

    def test_proporcionalidad_lineal_y_punto_limite_admisible(self):
        r=calcular_geometria(2,3,self.h,self.s)
        filas=contribuciones_steinbrenner(2,3,self.s,r.q_asiento_neta_mpa)
        self.assertAlmostEqual(filas[-1]['Asiento acumulado (mm)'],50,places=8)
        fila_mitad=contribuciones_steinbrenner(2,3,self.s,r.q_asiento_neta_mpa/2)
        self.assertAlmostEqual(fila_mitad[-1]['Asiento acumulado (mm)'],25,places=8)

    def test_boussinesq_influencia_y_farfield(self):
        self.assertEqual(factor_boussinesq_centro(2,3,0),1.0)
        s=[factor_boussinesq_centro(2,3,z) for z in [0,1,2,5,10,20]]
        self.assertTrue(all(a>b for a,b in zip(s,s[1:])))
        z=1000
        esperado=3*2*3/(2*pi*z*z)
        self.assertAlmostEqual(factor_boussinesq_centro(2,3,z)/esperado,1,delta=1e-4)

    def test_boussinesq_contraste_cuadratura_independiente(self):
        # Integracion numerica directa de la carga puntual Boussinesq:
        # d sigma_z = 3 q z^3/(2 pi R^5) dA, bajo centro.
        b,l,z=2.,3.,1.5
        x,wx=np.polynomial.legendre.leggauss(48)
        y,wy=np.polynomial.legendre.leggauss(48)
        xx=x*(b/2)
        yy=y*(l/2)
        r2=z*z+xx[:,None]**2+yy[None,:]**2
        integrando=3*z**3/(2*pi*(r2**2.5))
        integral=float((integrando*wx[:,None]*wy[None,:]).sum()*(b/2)*(l/2))
        self.assertAlmostEqual(factor_boussinesq_centro(b,l,z),integral,delta=2e-10)

    def test_bulbo_y_aviso_profundidad_incompleta(self):
        r=calcular_geometria(2,3,self.h,self.s)
        p=calcular_perfil_bulbo(2,3,r.q_serv_neta_mpa,self.h,self.s)
        self.assertTrue(p.suficiente)
        self.assertGreater(p.profundidad_influencia_m,2)
        s_corta=replace(self.s,capas=(CapaSuelo('A',0,2,15,.3),))
        p2=calcular_perfil_bulbo(2,3,.15,self.h,s_corta)
        self.assertFalse(p2.suficiente)
        self.assertTrue(any('antes' in w for w in p2.avisos))

    def test_distincion_q0_contorno_y_descarga_excavacion(self):
        h=replace(self.h,gamma_sobrecarga_kn_m3=18,altura_sobrecarga_m=3)
        r=calcular_geometria(2,3,h,self.s)
        self.assertAlmostEqual(r.q0_kpa,54)
        self.assertAlmostEqual(r.sigma_pre_base_kpa,9)
        self.assertAlmostEqual(r.q_serv_neta_mpa+r.sigma_pre_base_kpa/1000,r.q_serv_bruta_mpa)
        manual=replace(self.s,descarga_excavacion_kpa=25)
        self.assertAlmostEqual(descarga_preexistente_kpa(h,manual),25)
        self.assertAlmostEqual(calcular_geometria(2,3,h,manual).sigma_pre_base_kpa,25)

    def test_freatico_tensiones_efectivas_y_totales(self):
        h=replace(self.h,nivel_freatico_m=1,gamma_aparente_kn_m3=18,gamma_efectivo_kn_m3=9)
        self.assertAlmostEqual(tension_inicial_kpa(2,h,efectiva=True),27)
        self.assertAlmostEqual(tension_inicial_kpa(2,h,efectiva=False),36.81)

    def test_graficos_y_tabla_de_contribucion(self):
        r=calcular_geometria(2,3,self.h,self.s)
        filas=contribuciones_steinbrenner(2,3,self.s,r.q_serv_neta_mpa)
        p=calcular_perfil_bulbo(2,3,r.q_serv_neta_mpa,self.h,self.s)
        df=pd.DataFrame(filas)
        self.assertGreater(len(figura_bulbo(p).data),1)
        self.assertEqual(len(figura_asiento_acumulado(df).data),1)
        self.assertEqual(len(figura_contribuciones(df).data),1)


if __name__=='__main__': unittest.main()
