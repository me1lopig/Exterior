"""Verificacion aritmetica, dimensional, dominio y procedencia Webb/Stroud.

Valores calculados manualmente a partir de ecuaciones publicadas. Para Webb
la publicacion original no se ha contrastado de forma integral.
"""
import math
import unittest
from calculos.webb_stroud import (calcular_webb, calcular_stroud_butler,
                                  WEBB_MATERIALES, STROUD_MATERIALES)
from modelos.esquemas import EstadoRevision


class WebbDocumentado(unittest.TestCase):
    def test_arena_saturada_n20(self):
        x=calcular_webb(20,'Arena saturada')
        self.assertAlmostEqual(x[0].valor,17.5)
        self.assertEqual(x[0].unidad,'MPa')
        self.assertFalse(x[1].aplicable)
        self.assertEqual(x[0].estado,EstadoRevision.SECUNDARIA)

    def test_arena_arcillosa_n20_corrige_offset(self):
        x=calcular_webb(20,'Arena arcillosa')
        self.assertAlmostEqual(x[1].valor,8.25)
        self.assertNotAlmostEqual(x[1].valor,0.33*(20+15))
        self.assertIsNone(x[0].valor)

    def test_perfil_medio(self):
        x=calcular_webb(20,'Perfil arenoso medio/heterogeneo')
        self.assertAlmostEqual(x[2].valor,12.8)

    def test_comprobacion_por_dos_n(self):
        # Diferencia de modulo / incremento de N = pendiente de coef. /1000.
        for material,slope in [(WEBB_MATERIALES[0],0.5),(WEBB_MATERIALES[1],0.33),(WEBB_MATERIALES[2],0.4)]:
            i=WEBB_MATERIALES.index(material)
            a=calcular_webb(10,material)[i].valor
            b=calcular_webb(30,material)[i].valor
            self.assertAlmostEqual((b-a)/20,slope)

    def test_no_extrapolacion_ni_n_cero(self):
        for n in (0,60.001,100):
            res=calcular_webb(n,'Arena saturada')
            self.assertFalse(any(x.aplicable for x in res))

    def test_limite_60_incluido(self):
        self.assertAlmostEqual(calcular_webb(60,'Arena saturada')[0].valor,37.5)

    def test_invalidos(self):
        for n in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):calcular_webb(n,'Arena saturada')
        with self.assertRaises(ValueError):calcular_webb(10,'Arena inexistente')

    def test_no_confunde_referencia_con_cte(self):
        x=calcular_webb(10,'Arena saturada')[0]
        self.assertIn('Wagh',x.referencia)
        self.assertNotIn('CTE DB',x.referencia)
        self.assertIn('SPT bruto',x.parametros)


class StroudButlerDocumentado(unittest.TestCase):
    def test_f2_450_ip23_n20_figura_primaria(self):
        # f2=450 kPa e IP~23 se documentan en ejemplo de sitio 5 del original.
        # N=20 es SINTETICO, no dato del sitio 5.
        r=calcular_stroud_butler(20,23,450,'Arcilla glacial / till',f2_confirmado=True)
        self.assertAlmostEqual(r[0].valor,9.0)
        self.assertEqual(r[0].unidad,'MPa')
        self.assertAlmostEqual(r[1].valor,1000/9000)
        self.assertEqual(r[1].unidad,'1/MPa')
        self.assertEqual(r[0].estado,EstadoRevision.VERIFICADA_BIBLIOGRAFIA)

    def test_estricta_inversa(self):
        r=calcular_stroud_butler(40,35,500,'Arcilla glacial laminada',f2_confirmado=True)
        self.assertAlmostEqual(r[0].valor*r[1].valor,1.0)

    def test_sin_f2_confirmado_bloquea(self):
        r=calcular_stroud_butler(20,23,450,'Arcilla glacial / till',f2_confirmado=False)
        self.assertFalse(any(x.aplicable for x in r))
        self.assertTrue(all(x.valor is None for x in r))

    def test_otros_materiales_bloqueados(self):
        r=calcular_stroud_butler(20,23,450,'Otro material (fuera del alcance)',f2_confirmado=True)
        self.assertFalse(any(x.aplicable for x in r))

    def test_ip_fuera_figura_bloquea(self):
        for ip in (14.99,60.01):
            r=calcular_stroud_butler(20,ip,450,'Arcilla glacial / till',f2_confirmado=True)
            self.assertFalse(any(x.aplicable for x in r))

    def test_ip_limites(self):
        for ip in (15,60):
            r=calcular_stroud_butler(20,ip,450,'Arcilla glacial / till',f2_confirmado=True)
            self.assertTrue(all(x.aplicable for x in r))

    def test_n_fuera_limite(self):
        for n in (0,100.1):
            r=calcular_stroud_butler(n,23,450,'Arcilla glacial / till',f2_confirmado=True)
            self.assertFalse(any(x.aplicable for x in r))

    def test_f2_unidades(self):
        r1=calcular_stroud_butler(20,30,500,'Arcilla glacial / till',f2_confirmado=True)
        self.assertAlmostEqual(r1[0].valor,10) # 500 kPa * 20 /1000 = 10 MPa
        self.assertAlmostEqual(r1[1].valor,0.1) # 1/10MPa = 0.1 /MPa

    def test_numeros_invalidos(self):
        for caso in [(-1,23,450),(20,-1,450),(20,23,0),(20,23,-10),(20,23,float('nan'))]:
            with self.assertRaises(ValueError):
                calcular_stroud_butler(*caso,'Arcilla glacial / till',f2_confirmado=True)

    def test_fuente_primaria_y_no_e_young(self):
        r=calcular_stroud_butler(20,23,450,'Arcilla glacial / till',f2_confirmado=True)
        self.assertIn('1975',r[0].referencia)
        self.assertIn('edometrico',r[0].aplicacion)
        self.assertIn('Young',r[0].nota)
        self.assertNotIn('Young',r[0].aplicacion)

if __name__=='__main__':unittest.main()
