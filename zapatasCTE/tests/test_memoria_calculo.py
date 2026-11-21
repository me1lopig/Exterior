"""PROP-13: verificación de la memoria descriptiva contra el motor existente."""
from __future__ import annotations

from dataclasses import replace
from math import isclose
import unittest

from calculos.memoria_calculo import elaborar_memoria
from calculos.malla import calcular_geometria
from modelos.datos import CapaSuelo, DatosAsientos, DatosHundimiento


class MemoriaCalculoTest(unittest.TestCase):
    def setUp(self):
        self.h = DatosHundimiento()
        self.s = DatosAsientos(
            metodo_centro="superposicion",
            capas=(CapaSuelo("A", 0, 2.5, 15, .3),
                   CapaSuelo("B", 2.5, 10, 1200, .2)),
        )

    def test_desglose_reproduce_capacidad_y_presion_asiento(self):
        for b,l in ((1.5,1.5),(2,3),(3,5)):
            with self.subTest(b=b,l=l):
                r=calcular_geometria(b,l,self.h,self.s)
                m=elaborar_memoria(self.h,self.s,r)
                terminos=(m.termino_cohesion_kpa+m.termino_sobrecarga_kpa
                          +m.termino_gamma_kpa+m.correccion_talud_kpa)
                self.assertAlmostEqual(terminos,m.q_h_caracteristica_kpa,places=9)
                self.assertAlmostEqual(m.q_h_caracteristica_kpa/m.gamma_r/1000,
                                       r.q_hund_bruta_mpa,places=11)
                self.assertAlmostEqual(m.asiento_admisible_cm/m.flexibilidad_cm_mpa,
                                       r.q_asiento_neta_mpa,places=11)
                self.assertEqual(m.limitacion,r.limitacion)
                self.assertAlmostEqual(m.sc,1+.2*b/l,places=11)

    def test_sin_drenaje_y_talud_aditivo(self):
        h=replace(self.h,
            situacion_drenaje="Transitoria a corto plazo (sin drenaje)",
            phi_deg=0,cohesion_kpa=50,
            inclinacion_talud_deg=10,
            situacion_seguridad="Situación extraordinaria")
        r=calcular_geometria(2,4,h,self.s)
        m=elaborar_memoria(h,self.s,r)
        self.assertAlmostEqual(m.nc,5.14)
        self.assertEqual(m.ngamma,0)
        self.assertEqual((m.tc,m.tq,m.tgamma),(1.,1.,1.))
        self.assertLess(m.correccion_talud_kpa,0)
        self.assertEqual(m.gamma_r,2.)
        self.assertAlmostEqual(m.q_h_d_bruta_mpa,r.q_hund_bruta_mpa)

    def test_nivel_freatico_y_gradiente(self):
        h=replace(self.h,
            profundidad_base_m=1,nivel_freatico_m=2,
            gamma_aparente_kn_m3=19,gamma_efectivo_kn_m3=10)
        r=calcular_geometria(2,3,h,self.s)
        m=elaborar_memoria(h,self.s,r)
        self.assertAlmostEqual(m.gamma_k_kn_m3,14.5)
        hf=replace(h,flujo_ascendente=True,gradiente_vertical=.4)
        r2=calcular_geometria(2,3,hf,self.s)
        m2=elaborar_memoria(hf,self.s,r2)
        self.assertAlmostEqual(m2.gamma_k_kn_m3,10-.4*9.81)

    def test_resultados_incompatibles_se_rechazan(self):
        r=calcular_geometria(2,3,self.h,self.s)
        adulterado=replace(r,q_hund_bruta_mpa=r.q_hund_bruta_mpa+.01)
        with self.assertRaisesRegex(ValueError,"hundimiento"):
            elaborar_memoria(self.h,self.s,adulterado)
        otro=replace(self.h,phi_deg=27.)
        with self.assertRaisesRegex(ValueError,"hundimiento"):
            elaborar_memoria(otro,self.s,r)

    def test_servicio_invalido_se_representa_sin_inventar_presion(self):
        h=replace(self.h,phi_deg=0,cohesion_kpa=0,considerar_sobrecarga=False)
        r=calcular_geometria(2,3,h,self.s)
        m=elaborar_memoria(h,self.s,r)
        self.assertIsNone(m.q_servicio_neta_mpa)
        self.assertIsNone(m.q_servicio_bruta_mpa)
        self.assertEqual(m.limitacion,"No válido")


if __name__ == "__main__":
    unittest.main()
