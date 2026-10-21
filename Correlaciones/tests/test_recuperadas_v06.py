"""Casos de prueba para Wolff/Peck, Shioi-Fukui y D'Appolonia.

Se usan evaluaciones matematicas independientes y comprobacion dimensional.
La comprobacion numerica no sustituye a validacion experimental local.
"""
import math
import unittest
from calculos.spt import SalidaSPT, DatosSPT, normalizar_spt
from calculos.granulares import calcular_phi_verificado
from calculos.dappolonia import calcular_m_dappolonia, TSF_A_MPA

class WolffPeck(unittest.TestCase):
    def test_formula_20(self):
        r=calcular_phi_verificado(SalidaSPT(20,20,20,1),100,'Arena limpia fina/media')[2]
        self.assertAlmostEqual(r.valor,32.884,places=6)
        self.assertEqual(r.unidad,'grados')
        self.assertTrue(r.aplicable)
    def test_uses_n1_not_n60(self):
        r=calcular_phi_verificado(SalidaSPT(20,20,40,2),25,'Arena limpia fina/media')[2]
        self.assertAlmostEqual(r.valor,27.1+0.3*40-0.00054*40**2)
        self.assertNotAlmostEqual(r.valor,27.1+0.3*20-0.00054*20**2)
    def test_bounds_and_non_granular(self):
        for v in (-1,60.01):
            self.assertIsNone(calcular_phi_verificado(SalidaSPT(20,20,v,None),100,'Arena limpia fina/media')[2].valor)
        self.assertTrue(calcular_phi_verificado(SalidaSPT(20,20,0,1),100,'Arena limpia fina/media')[2].aplicable)
    def test_wolff_gravel_blocked(self):
        r=calcular_phi_verificado(SalidaSPT(20,20,20,1),100,'Grava/arena gravosa')[2]
        self.assertFalse(r.aplicable)

class ShioiFukui(unittest.TestCase):
    def test_n70_from_n60_and_both_equations(self):
        r=calcular_phi_verificado(SalidaSPT(20,20,20,1),100,'Arena limpia fina/media')
        n70=20*60/70
        self.assertAlmostEqual(r[3].valor,15+math.sqrt(18*n70))
        self.assertAlmostEqual(r[4].valor,27+0.36*n70)
    def test_n70_not_confounded_with_n1(self):
        a=calcular_phi_verificado(SalidaSPT(20,20,10,.5),200,'Arena limpia fina/media')
        b=calcular_phi_verificado(SalidaSPT(20,20,40,2),25,'Arena limpia fina/media')
        self.assertAlmostEqual(a[3].valor,b[3].valor)
        self.assertAlmostEqual(a[4].valor,b[4].valor)
        self.assertNotAlmostEqual(a[2].valor,b[2].valor)
    def test_normalization_70pct_energy(self):
        s=normalizar_spt(DatosSPT(20,70,1,1,1,100))
        # Con ER=70% el N70 equivale al N bruto para factores 1.
        self.assertAlmostEqual(s.n60*60/70,20)
        r=calcular_phi_verificado(s,100,'Arena limpia fina/media')
        self.assertAlmostEqual(r[3].valor,15+math.sqrt(18*20))
        self.assertAlmostEqual(r[4].valor,34.2)
    def test_high_values_not_extrapolated(self):
        s=SalidaSPT(100,100,100,1)
        r=calcular_phi_verificado(s,100,'Arena limpia fina/media')
        self.assertFalse(r[3].aplicable)
        self.assertFalse(r[4].aplicable)
    def test_material_filters(self):
        s=SalidaSPT(20,20,20,1)
        r=calcular_phi_verificado(s,100,'Grava/arena gravosa')
        self.assertFalse(r[3].aplicable)
        self.assertTrue(r[4].aplicable)
    def test_negative_n60_rejected(self):
        with self.assertRaises(ValueError):
            calcular_phi_verificado(SalidaSPT(20,-1,1,1),100,'Arena limpia fina/media')

class Dappolonia(unittest.TestCase):
    def test_nc_is_m_not_young(self):
        r=calcular_m_dappolonia(20,2,'Normalmente cargada','Arena limpia NC')
        self.assertTrue(r[0].aplicable)
        self.assertFalse(r[1].aplicable)
        self.assertAlmostEqual(r[0].valor,(196+7.9*20)*TSF_A_MPA)
        self.assertEqual(r[0].unidad,'MPa')
        self.assertIn('NO modulo de Young',r[0].aplicacion)
    def test_oc(self):
        r=calcular_m_dappolonia(20,2,'Precargada / OC','Arena limpia OC')
        self.assertFalse(r[0].aplicable)
        self.assertAlmostEqual(r[1].valor,(416+10.9*20)*TSF_A_MPA)
    def test_reference_example_n11_nc(self):
        # Ejemplo representativo del manual: con N=11 el grafico arroja aprox 285 tsf.
        # La expresion lineal reproducida da 282.9 tsf: diferencia < 1%.
        v=calcular_m_dappolonia(11,3,'Normalmente cargada','Arena limpia NC')[0]
        self.assertAlmostEqual(v.valor/TSF_A_MPA,282.9)
        self.assertLess(abs(v.valor/TSF_A_MPA-285)/285,0.01)
    def test_effect_of_B_only_in_definition_of_N(self):
        # El ancho B define la zona de promedio, sin entrar directamente a la recta.
        x=calcular_m_dappolonia(15,1,'Normalmente cargada','Arena limpia NC')[0].valor
        y=calcular_m_dappolonia(15,3,'Normalmente cargada','Arena limpia NC')[0].valor
        self.assertEqual(x,y)
    def test_invalid_inputs(self):
        for n,b in [(-1,2),(20,0),(float('nan'),2),(20,float('inf'))]:
            with self.assertRaises(ValueError):
                calcular_m_dappolonia(n,b,'Normalmente cargada','Arena limpia NC')
    def test_rejects_mismatch(self):
        r=calcular_m_dappolonia(20,2,'Precargada / OC','Arena limpia NC')
        self.assertFalse(any(x.aplicable for x in r))
    def test_missing_state_or_fines(self):
        r=calcular_m_dappolonia(20,2,'No definido','Arena limpia NC')
        self.assertFalse(any(x.aplicable for x in r))
        r=calcular_m_dappolonia(20,2,'Normalmente cargada','Arena con finos')
        self.assertFalse(any(x.aplicable for x in r))
    def test_gravel_sand_allow_both_states(self):
        for estado in ('Normalmente cargada','Precargada / OC'):
            r=calcular_m_dappolonia(15,2,estado,'Grava/arena gravosa')
            self.assertEqual(sum(x.aplicable for x in r),1)
    def test_out_of_operational_n_domain(self):
        for n in (0,60.1):
            r=calcular_m_dappolonia(n,2,'Normalmente cargada','Arena limpia NC')
            self.assertFalse(any(x.aplicable for x in r))

if __name__=='__main__':unittest.main()
