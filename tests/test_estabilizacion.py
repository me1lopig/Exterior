"""Pruebas de regresion para la revision de estabilidad 0.6 (datos sinteticos)."""
from __future__ import annotations

from io import BytesIO
import json
import unittest

import numpy as np
import pandas as pd

from perfil_geologico.calculos.contactos import actualizar_vertices
from perfil_geologico.calculos.dpsh import separar_tramos_contiguos
from perfil_geologico.calculos.proyeccion import proyectar_puntos
from perfil_geologico.calculos.zonas import construir_zonas
from perfil_geologico.calculos.dpsh import curvas_dpsh
from perfil_geologico.modelos.dominio import Contacto, Proyecto, VerticeContacto
from perfil_geologico.servicios.datos_demo import crear_datos_demo
from perfil_geologico.servicios.exportacion import contactos_a_dxf, figura_perfil_pdf
from perfil_geologico.servicios.persistencia import proyecto_a_json, proyecto_desde_json
from perfil_geologico.utiles.validacion import validar_datos
from perfil_geologico.visualizacion.perfil_plotly import crear_figura_perfil


class EstabilizacionTests(unittest.TestCase):
    def setUp(self):
        self.datos = crear_datos_demo()

    def validar(self):
        d = self.datos
        return validar_datos(d['Sondeos'], d['Intervalos'], d['Unidades'], d['Ensayos_DPSH'], d['Lecturas_DPSH'])

    def test_no_dpsh_json_compatible(self):
        self.datos['Ensayos_DPSH'] = self.datos['Ensayos_DPSH'].iloc[:0].copy()
        self.datos['Lecturas_DPSH'] = self.datos['Lecturas_DPSH'].iloc[:0].copy()
        pro, datos = proyecto_desde_json(proyecto_a_json(Proyecto(), self.datos))
        self.assertEqual(list(datos['Ensayos_DPSH']), list(self.datos['Ensayos_DPSH']))
        self.assertEqual(list(datos['Lecturas_DPSH']), list(self.datos['Lecturas_DPSH']))
        self.assertFalse(validar_datos(datos['Sondeos'], datos['Intervalos'], datos['Unidades'],
                                      datos['Ensayos_DPSH'], datos['Lecturas_DPSH'])[0])

    def test_json_anterior_sin_columnas_datos_compatible(self):
        brute = json.loads(proyecto_a_json(Proyecto(), self.datos))
        brute.pop('columnas_datos')
        self.datos['Lecturas_DPSH'] = self.datos['Lecturas_DPSH'].iloc[:0].copy()
        brute['datos']['Lecturas_DPSH'] = []
        _, data = proyecto_desde_json(json.dumps(brute).encode())
        self.assertEqual(list(data['Lecturas_DPSH']), list(self.datos['Lecturas_DPSH']))

    def test_rechaza_cotas_invalidas_y_colores(self):
        self.datos['Sondeos'].loc[0, 'cota_boca_m'] = np.inf
        self.datos['Unidades'].loc[0, 'color'] = '#GGGGGG'
        errores, _ = self.validar()
        self.assertTrue(any('cota_boca_m' in x for x in errores))
        self.assertTrue(any('color' in x for x in errores))

    def test_rechaza_dpsh_fuera_de_profundidad_final(self):
        ident = self.datos['Ensayos_DPSH'].iloc[0]['ensayo_id']
        final = float(self.datos['Ensayos_DPSH'].iloc[0]['profundidad_m'])
        self.datos['Lecturas_DPSH'] = pd.concat([
            self.datos['Lecturas_DPSH'], pd.DataFrame([{'ensayo_id': ident, 'profundidad_m': final + 4, 'n20': 10}])
        ], ignore_index=True)
        errores, _ = self.validar()
        self.assertTrue(any('mas profundas' in x for x in errores))

    def test_zona_dividida_no_hereda_unidad(self):
        sondeos = pd.DataFrame({'s_m': [0., 10.], 'cota_boca_m': [100., 100.], 'profundidad_m': [10., 10.]})
        original, _ = construir_zonas(sondeos, [])
        original[0]['unidad_id'] = 'ARC'
        original[0]['color'] = '#888888'
        contact = Contacto('C', 'Division', '', '', vertices=[VerticeContacto(0, 95), VerticeContacto(10, 95)])
        zonas, _ = construir_zonas(sondeos, [contact], original)
        self.assertEqual(len(zonas), 2)
        self.assertTrue(all(z['unidad_id'] == '' for z in zonas))
        iguales, _ = construir_zonas(sondeos, [], original)
        self.assertEqual(iguales[0]['unidad_id'], 'ARC')

    def test_observado_no_se_desplaza_en_edicion_numerica(self):
        c = Contacto('C', 'Contacto', '', '', vertices=[
            VerticeContacto(0, 80, 'observado', 'S-01', 'S-01:I001'), VerticeContacto(10, 78)])
        tabla = pd.DataFrame([{'s_m': 0, 'z_m': 81, 'origen': 'observado',
                               'referencia': 'S-01', 'interfaz_id': 'S-01:I001'},
                              {'s_m': 10, 'z_m': 78, 'origen': 'interpretado',
                               'referencia': '', 'interfaz_id': ''}])
        with self.assertRaises(ValueError):
            actualizar_vertices(c, tabla)
        self.assertEqual(c.vertices[0].z_m, 80)

    def test_dpsh_curvas_muestran_dos_tramos(self):
        p = pd.DataFrame([{'ensayo_id': 'P1', 's_m': 4., 'cota_inicio_m': 120., 'profundidad_m': 2.}])
        d = pd.DataFrame({'ensayo_id': ['P1']*4, 'profundidad_m': [.2, .4, 1.4, 1.6], 'n20': [4,6,8,10]})
        curvas = curvas_dpsh(p, d, .12)
        self.assertEqual([len(t) for t in curvas[0]['tramos']], [2,2])
        self.assertAlmostEqual(curvas[0]['tramos'][0][0]['z_m'], 119.8)

    def test_dxf_polilinea_lente_cerrada(self):
        c = Contacto('L1', 'Lentejon', '', 'A', vertices=[VerticeContacto(0,10),
            VerticeContacto(5,10), VerticeContacto(5,5), VerticeContacto(0,10)])
        dxf = contactos_a_dxf([c]).decode('ascii')
        self.assertIn('70\n1\n', dxf)

    def test_vista_hueco_geologico_plotly(self):
        z = {'zona_id':'Z1','unidad_id':'A','color':'#888888','trama':'sin_trama',
             'coordenadas': [[0,100],[10,100],[10,90],[0,90]],
             'huecos': [[[3,97],[7,97],[7,93],[3,93]]],
             'centro_s_m':1,'centro_z_m':95,'area_m2':84}
        sondeos = pd.DataFrame({'sondeo_id':['S1','S2'],'s_m':[0.,10.],
                                 'cota_boca_m':[100.,100.],'profundidad_m':[10.,10.]})
        unidades = pd.DataFrame({'unidad_id':['A'], 'nombre':['A'], 'orden':[1], 'color':['#888888']})
        itvs = pd.DataFrame({'sondeo_id':['S1','S2'],'desde_m':[0.,0.],
                             'hasta_m':[10.,10.], 'unidad_id':['A','A']})
        fig=crear_figura_perfil(Proyecto(),sondeos,itvs,unidades,[],pd.DataFrame(),pd.DataFrame(),zonas=[z])
        self.assertTrue(any(sh.fillrule == 'evenodd' for sh in fig.layout.shapes))

    def test_pdf_sintetico_genera_archivo(self):
        sondeos = proyectar_puntos(self.datos['Sondeos'], self.datos['Eje'])
        dpsh = proyectar_puntos(self.datos['Ensayos_DPSH'], self.datos['Eje'])
        pdf = figura_perfil_pdf(Proyecto(), sondeos, self.datos['Intervalos'], self.datos['Unidades'],
            [], dpsh, self.datos['Lecturas_DPSH'], .12, zonas=[])
        self.assertTrue(pdf.startswith(b'%PDF'))
        self.assertGreater(len(pdf), 1000)

if __name__ == '__main__':
    unittest.main()
