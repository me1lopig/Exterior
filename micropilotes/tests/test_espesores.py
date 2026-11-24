import unittest
from math import pi
from modelos.espesores import intervalos_desde_espesores, espesores_desde_cotas
from calculos.avanzado import estrato_con_inyeccion
from calculos.axial import calcular


class EspesoresTests(unittest.TestCase):
    def test_acumulacion(self):
        filas = [{'espesor_m': 2}, {'espesor_m': 4}, {'espesor_m': 6}]
        r = intervalos_desde_espesores(filas)
        self.assertEqual([(x['inicio_m'], x['fin_m']) for x in r], [(0,2),(2,6),(6,12)])
        self.assertNotIn('inicio_m', filas[0])

    def test_migracion(self):
        r = espesores_desde_cotas([{'inicio_m':0,'fin_m':2},{'inicio_m':2,'fin_m':6}])
        self.assertEqual([x['espesor_m'] for x in r], [2,4])
        for a in (1,3):
            with self.assertRaises(ValueError):
                espesores_desde_cotas([{'inicio_m':0,'fin_m':2},{'inicio_m':a,'fin_m':6}])

    def test_espesores_invalidos(self):
        for h in (0,-1,None,float('nan'),float('inf'),'texto'):
            with self.subTest(h=h), self.assertRaises(ValueError):
                intervalos_desde_espesores([{'espesor_m':h}])
        with self.assertRaises(ValueError):
            intervalos_desde_espesores([])

    def test_cruce_cinco_metros_e_inyeccion(self):
        filas = [
            dict(espesor_m=2, inyeccion='IU', iu_kPa=50, seleccion_kPa=50, pi_kPa=600, plim_kPa=800, activo=True),
            dict(espesor_m=4, inyeccion='IR', iu_kPa=80, seleccion_kPa=120, pi_kPa=600, plim_kPa=800, activo=True),
            dict(espesor_m=6, inyeccion='IRS', iu_kPa=100, seleccion_kPa=200, pi_kPa=1200, plim_kPa=800, activo=True),
        ]
        e = [estrato_con_inyeccion(f,10) for f in intervalos_desde_espesores(filas)]
        r = calcular(.2,10,0,e,12,True)
        self.assertEqual([t['r_lim'] for t in r['tramos']], [50,80,120,200])
        self.assertAlmostEqual(r['fuste_compresion'], pi*.2*(2*50+3*80+120+4*200)/1.65)

    def test_inclinado(self):
        filas = [dict(espesor_m=6,inyeccion='IR',iu_kPa=80,seleccion_kPa=120,pi_kPa=600,plim_kPa=800,activo=True)]
        e = [estrato_con_inyeccion(f,5.5) for f in intervalos_desde_espesores(filas)]
        r = calcular(.2,11,60,e,12,True)
        self.assertAlmostEqual(r['profundidad'],5.5)
        self.assertAlmostEqual(r['tramos'][0]['longitud_axial'],10)
        self.assertAlmostEqual(r['tramos'][1]['longitud_axial'],1)
