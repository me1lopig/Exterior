from __future__ import annotations

import math
import unittest

from calculos.cu_validado import DatosCu, calcular_cu
from calculos.correlaciones import (
    calcular_e_arcillas, calcular_e_arenas, calcular_e_cte,
    calcular_k30, calcular_phi, obtener_poisson,
)
from modelos.esquemas import EstadoRevision


class CuBibliograficoTest(unittest.TestCase):
    def datos(self, **cambios):
        base = {
            "sigma_v_ef_kpa": 150.0, "ip_pct": 60.0, "ll_pct": 80.0,
            "consolidacion": "Normalmente consolidada (NC)",
            "tipo_suelo": "Arcilla inorgánica blanda", "sigma_p_kpa": 150.0,
        }
        base.update(cambios)
        return DatosCu(**base)

    def test_cu_solo_cuatro_metodos_con_fuente(self):
        filas = calcular_cu(self.datos())
        self.assertEqual(len(filas), 4)
        self.assertEqual([r.aplicable for r in filas], [True]*4)
        self.assertTrue(all(r.estado == EstadoRevision.VERIFICADA_BIBLIOGRAFIA for r in filas))
        self.assertTrue(all(r.referencia.startswith(('Skempton','Bowles','Mesri')) for r in filas))

    def test_skempton_valor_referencia_independiente(self):
        r = calcular_cu(self.datos())[0]
        self.assertAlmostEqual(r.valor, 49.8)  # (0.11 + 0.0037*60)*150
        self.assertIn('VST', r.formula)

    def test_bjerrum_porcentajes_y_ejemplo(self):
        r = calcular_cu(self.datos())[1]
        self.assertAlmostEqual(r.valor, 0.45 * math.sqrt(.60) * 150)

    def test_karlsson_porcentajes_y_ejemplo(self):
        r = calcular_cu(self.datos())[2]
        self.assertAlmostEqual(r.valor, 60.0)

    def test_mesri_usa_preconsolidacion_no_tension_actual(self):
        r = calcular_cu(self.datos(sigma_p_kpa=300))[3]
        self.assertAlmostEqual(r.valor, 66.)
        self.assertNotAlmostEqual(r.valor, 0.22*150)

    def test_bjerrum_ip_50_no_aplica(self):
        r = calcular_cu(self.datos(ip_pct=50))[1]
        self.assertFalse(r.aplicable)
        self.assertIsNone(r.valor)
        self.assertIn('> 50', r.criterio)

    def test_bjerrum_ip_superior_50_aplica(self):
        self.assertTrue(calcular_cu(self.datos(ip_pct=50.0001))[1].aplicable)

    def test_karlsson_ll_20_no_aplica(self):
        r = calcular_cu(self.datos(ip_pct=10, ll_pct=20))[2]
        self.assertFalse(r.aplicable)
        self.assertIsNone(r.valor)

    def test_karlsson_ll_21_aplica(self):
        self.assertTrue(calcular_cu(self.datos(ip_pct=10,ll_pct=21))[2].aplicable)

    def test_nc_requerido_para_3_metodos(self):
        filas = calcular_cu(self.datos(consolidacion='Sobreconsolidada (OC)', sigma_p_kpa=300))
        self.assertEqual([r.aplicable for r in filas], [False,False,False,True])
        self.assertTrue(all(r.valor is None for r in filas[:3]))

    def test_no_identificar_consolidacion_impide_tres_metodos(self):
        filas = calcular_cu(self.datos(consolidacion='No definida'))
        self.assertTrue(all(not r.aplicable for r in filas[:3]))

    def test_mesri_sin_presion_preconsolidacion_bloqueado(self):
        fila = calcular_cu(self.datos(sigma_p_kpa=None))[3]
        self.assertFalse(fila.aplicable)
        self.assertIsNone(fila.valor)

    def test_mesri_no_arcilla_blanda_inorganica_bloqueado(self):
        fila = calcular_cu(self.datos(tipo_suelo='Otra arcilla'))[3]
        self.assertFalse(fila.aplicable)

    def test_mesri_presion_inferior_actual_bloqueado(self):
        fila = calcular_cu(self.datos(sigma_p_kpa=130))[3]
        self.assertFalse(fila.aplicable)
        self.assertIn('OCR < 1', fila.criterio)

    def test_suelo_desconocido_todos_bloqueados(self):
        filas = calcular_cu(self.datos(tipo_suelo='No identificado'))
        self.assertTrue(all(not r.aplicable for r in filas))

    def test_input_ip_mayor_ll_rechazado(self):
        with self.assertRaisesRegex(ValueError,'IP.*LL'):
            calcular_cu(self.datos(ip_pct=80,ll_pct=70))

    def test_tension_efectiva_cero_bloquea_nc(self):
        filas = calcular_cu(self.datos(sigma_v_ef_kpa=0))
        self.assertTrue(all(not r.aplicable for r in filas[:3]))

    def test_valor_no_finito_rechazado(self):
        for v in (float('nan'), float('inf'), -1.):
            with self.subTest(v=v), self.assertRaises(ValueError):
                calcular_cu(self.datos(sigma_v_ef_kpa=v))

    def test_nc_con_sigmap_mayor_reconoce_contradiccion(self):
        filas = calcular_cu(self.datos(sigma_p_kpa=300))
        self.assertEqual([r.aplicable for r in filas], [False,False,False,True])
        self.assertIn('OCR > 1', filas[0].criterio)

    def test_metodo_distinto_de_sigma_preconsolidacion_no_usa_sigmap(self):
        r1 = calcular_cu(self.datos(sigma_p_kpa=150))
        r2 = calcular_cu(self.datos(sigma_p_kpa=900))
        self.assertTrue(all(not x.aplicable for x in r2[:3]))
        self.assertNotEqual(r1[3].valor, r2[3].valor)

    def test_export_no_aplica_no_contiene_valor(self):
        fila = calcular_cu(self.datos(ip_pct=5))[1]
        self.assertIsNone(fila.como_fila()['valor'])


class OtrosModulosTest(unittest.TestCase):
    def test_phi_y_e_arenas_bloqueados(self):
        with self.assertRaises(RuntimeError):
            calcular_phi(30, 20)
        with self.assertRaises(RuntimeError):
            calcular_e_arenas(25)

    def test_e_arcillas_cte_solo_una(self):
        resultado = calcular_e_arcillas(23, 0, 200, 2)
        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0].valor, 160.0)
        self.assertTrue(resultado[0].aplicable)

    def test_e_arcillas_ocr_menor_uno_rechazado(self):
        with self.assertRaises(ValueError):
            calcular_e_arcillas(23, 0, 200, .9)

    def test_cte_f2_no_inventa_limite_ip(self):
        resultado = calcular_e_arcillas(30, 0, 200, 3)[0]
        self.assertIsNone(resultado.valor)
        self.assertFalse(resultado.aplicable)

    def test_e_cte_sin_extrapolar_desde_n50(self):
        aplicables = [r for r in calcular_e_cte(100) if r.aplicable]
        self.assertEqual([r.valor for r in aplicables], [None, None])

    def test_e_cte_interpolacion_35(self):
        aplicables = [r for r in calcular_e_cte(35) if r.aplicable]
        self.assertEqual(len(aplicables), 2)
        self.assertAlmostEqual(aplicables[1].valor, 64.0)
        self.assertIn('no prescrita', aplicables[1].nota)

    def test_e_cte_frontera_25(self):
        aplicables = [r for r in calcular_e_cte(25) if r.aplicable]
        self.assertEqual([r.valor for r in aplicables], [150.0,40.0])

    def test_poisson_cte(self):
        self.assertEqual([r.valor for r in obtener_poisson()], [.4,.3,.15,.3])

    def test_k30_cte(self):
        valores = [r.valor for r in calcular_k30(2,2,25)]
        esperados = [3.75, 8.265625, 5.625, 12.3984375]
        for x,y in zip(valores, esperados):
            self.assertAlmostEqual(x,y)

    def test_k30_geometria_invalida(self):
        with self.assertRaises(ValueError):
            calcular_k30(3,2,25)

    def test_modulos_eliminados(self):
        import calculos.correlaciones as motor
        for nombre in ('calcular_cc','calcular_cs','calcular_k0','calcular_ocr'):
            self.assertFalse(hasattr(motor, nombre))


if __name__ == '__main__':
    unittest.main()
