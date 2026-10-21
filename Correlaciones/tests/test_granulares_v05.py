import unittest
import math
from calculos.spt import DatosSPT, normalizar_spt, SalidaSPT
from calculos.granulares import calcular_phi_verificado, calcular_e_arenas_verificado
from calculos.cte_orientativos import (cu_por_consistencia,cu_por_nspt_cte,phi_por_tipo_cte,eu_desde_gmax)
from calculos.correlaciones import calcular_e_cte, K30_TABLA

class SPTTests(unittest.TestCase):
    def test_spt_energia_y_factor(self):
        s=normalizar_spt(DatosSPT(20,75,1.05,.8,1,100))
        self.assertAlmostEqual(s.n60,21.0)
        self.assertAlmostEqual(s.n1_60,21.0)
    def test_spt_sigma_25_cn_limited(self):
        s=normalizar_spt(DatosSPT(20,60,1,1,1,25,1.7))
        self.assertAlmostEqual(s.cn,1.7)
        self.assertAlmostEqual(s.n1_60,34.0)
    def test_spt_sigma_25_cn_unlimited(self):
        s=normalizar_spt(DatosSPT(20,60,1,1,1,25,None))
        self.assertAlmostEqual(s.cn,2.0)
        self.assertAlmostEqual(s.n1_60,40.0)
    def test_spt_sigma_negative_rejected(self):
        with self.assertRaises(ValueError):normalizar_spt(DatosSPT(20,60,1,1,1,-10))
    def test_spt_input_nan_invalid(self):
        with self.assertRaises(ValueError):normalizar_spt(DatosSPT(float('nan')))
    def test_spt_zero_is_allowed(self):
        self.assertEqual(normalizar_spt(DatosSPT(0)).n60,0.0)
    def test_spt_correction_is_not_silent(self):
        self.assertAlmostEqual(normalizar_spt(DatosSPT(20,80)).n60,26.66666666666667)

class PhiTests(unittest.TestCase):
    def setUp(self):
        self.s=SalidaSPT(20,20,20,1.)
    def test_hatanaka_fhwa(self):
        r=calcular_phi_verificado(self.s,100,'Arena limpia fina/media')
        self.assertEqual(len(r),5)
        self.assertAlmostEqual(r[0].valor,20+math.sqrt(15.4*20))
    def test_hatanaka_original_energy_not_confused(self):
        self.assertNotAlmostEqual(calcular_phi_verificado(self.s,100,'Arena limpia fina/media')[0].valor,20+math.sqrt(20*20))
    def test_hatanaka_domain(self):
        for x in (3.49,30.01):
            s=SalidaSPT(20,20,x,1.)
            self.assertFalse(calcular_phi_verificado(s,100,'Arena limpia fina/media')[0].aplicable)
    def test_hatanaka_boundary(self):
        for x in (3.5,30):
            s=SalidaSPT(20,20,x,1.)
            self.assertTrue(calcular_phi_verificado(s,100,'Arena limpia fina/media')[0].aplicable)
    def test_fhwa_stress_dependence(self):
        a=calcular_phi_verificado(self.s,100,'Arena limpia fina/media')[1]
        expected=math.degrees(math.atan((20/(12.2+20.3))**.34))
        self.assertAlmostEqual(a.valor,expected)
        b=calcular_phi_verificado(self.s,300,'Arena limpia fina/media')[1]
        self.assertLess(b.valor,a.valor)
    def test_phi_not_for_gravel(self):
        r=calcular_phi_verificado(self.s,100,'Grava/arena gravosa')
        self.assertEqual([x.aplicable for x in r],[False,False,False,False,True])
    def test_phi_without_n1(self):
        r=calcular_phi_verificado(SalidaSPT(20,20,None,None),100,'Arena limpia fina/media')
        self.assertIsNone(r[0].valor)
        self.assertIsNotNone(r[1].valor)

class ElasticidadTests(unittest.TestCase):
    def setUp(self):self.s=SalidaSPT(20,20,20,1.)
    def test_fhwa_three_conditions_select_one(self):
        res=calcular_e_arenas_verificado(self.s,'Arena limpia NC')
        self.assertEqual(len(res),5)
        self.assertEqual(sum(r.aplicable for r in res[:3]),1)
        self.assertEqual(res[1].valor,20.0)
    def test_fhwa_fines_and_oc(self):
        self.assertEqual(calcular_e_arenas_verificado(self.s,'Arena con finos')[0].valor,10.)
        self.assertEqual(calcular_e_arenas_verificado(self.s,'Arena limpia OC')[2].valor,30.)
    def test_begemann_sign_corrected(self):
        r=calcular_e_arenas_verificado(self.s,'Grava/arena gravosa',n_begemann=20)
        self.assertAlmostEqual(r[4].valor,(40+12*(20-6))*.0980665)
        self.assertAlmostEqual(r[4].valor,20.397832)
    def test_begemann_below_15(self):
        r=calcular_e_arenas_verificado(self.s,'Grava/arena gravosa',n_begemann=10)
        self.assertAlmostEqual(r[3].valor,12*16*.0980665)
    def test_begemann_15_has_no_formula(self):
        r=calcular_e_arenas_verificado(self.s,'Grava/arena gravosa',n_begemann=15)
        self.assertEqual([x.valor for x in r[3:]],[None,None])
    def test_no_multiply_n60_when_nonapplicable(self):
        r=calcular_e_arenas_verificado(self.s,'Grava/arena gravosa')
        self.assertTrue(all(not q.aplicable for q in r[:3]))

class CTETests(unittest.TestCase):
    def test_k30_d29_table_present(self):
        self.assertEqual(len(K30_TABLA),12)
        self.assertEqual(K30_TABLA[0],("Arcilla blanda",15.,30.))
        self.assertEqual(K30_TABLA[-1][1],5000.)
    def test_cu_d3(self):
        r=cu_por_consistencia('Firme')
        self.assertEqual((r.minimo,r.maximo),(50.,100.))
    def test_cu_d3_dura_unbounded(self):
        self.assertIsNone(cu_por_consistencia('Dura').maximo)
    def test_cu_d23(self):
        self.assertEqual((cu_por_nspt_cte(35).minimo,cu_por_nspt_cte(35).maximo),(75.,150.))
    def test_cu_d23_boundary(self):
        self.assertEqual(cu_por_nspt_cte(10).minimo,40.)
        self.assertEqual(cu_por_nspt_cte(25).minimo,40.)
        self.assertEqual(cu_por_nspt_cte(50).minimo,75.)
    def test_phi_d27(self):
        self.assertEqual((phi_por_tipo_cte('Arena').minimo,phi_por_tipo_cte('Arena').maximo),(30,36))
    def test_cte_e_f1(self):
        self.assertAlmostEqual(eu_desde_gmax(25,50).valor,60.)
        self.assertAlmostEqual(eu_desde_gmax(40,50).valor,80.)
        self.assertAlmostEqual(eu_desde_gmax(60,50).valor,95.)
    def test_cte_f1_bounds(self):
        for ip in (15,30,50):
            self.assertIsNone(eu_desde_gmax(ip,50).valor)
    def test_cte_e_boundary_10(self):
        a=[r for r in calcular_e_cte(10) if r.aplicable]
        self.assertEqual((a[0].valor,a[1].valor),(80.0,8.0))
    def test_cte_e_interpolation_35(self):
        self.assertEqual([r.valor for r in calcular_e_cte(35) if r.aplicable],[210.,64.])

if __name__ == '__main__': unittest.main()
