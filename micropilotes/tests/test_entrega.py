import unittest, json
from io import BytesIO
from openpyxl import load_workbook
from docx import Document
from servicios.proyecto import serializar,cargar
from servicios.informes import excel,word,pdf
from calculos.axial import Estrato,calcular
from calculos.limites_acero import limite_acero
from modelos.tuberias_catalogo import POR_ETIQUETA
from math import pi

class EntregaTests(unittest.TestCase):
    def test_proyecto(self):
        rows=[dict(nombre='UG',espesor_m=10,inyeccion='IU',adlim_kPa=80,fr=1.65,activo=True)]
        x=cargar(serializar({'L':10},rows,'0.5.0'))
        self.assertEqual(x['estratos'],rows)
        self.assertEqual(x['widgets'],{'L':10})
        with self.assertRaises(ValueError):cargar(b'{"esquema":0}')
        with self.assertRaises(ValueError):cargar(b'{"esquema":1,"widgets":{"L":NaN},"estratos":[{}]}')
    def test_referencia_manual(self):
        r=calcular(.2,10,0,[Estrato(0,5,80,80),Estrato(5,10,100,150)],12,True)
        self.assertAlmostEqual(r['fuste_compresion'],pi*.2*(5*80+5*150)/1.65)
        self.assertAlmostEqual(r['fuste_traccion'],.6*pi*.2*(5*80+5*150)/1.65)
    def test_traccion_sin_pandeo(self):
        s=limite_acero(POR_ETIQUETA['139.7 × 9 mm'],550,0,'Resto de casos','Con lodos',None)
        self.assertIsNone(s['nc_kN'])
        self.assertGreater(s['nt_kN'],0)
    def test_documentos(self):
        r=calcular(.2,10,0,[Estrato(0,10,80,80)],12,True)
        e=dict(proyecto='=1+1',autor='Prueba',revision='00',L_min_m=5.,L_max_m=10.,paso_m=5.,angulo_grados=0.,Fr=1.65,alternancia=True,punta_hipotetica=False,control_presiones=False,estratos=[dict(nombre='UG',espesor_m=10,inicio_m=0,fin_m=10,inyeccion='IU',adlim_kPa=80,fr=1.65,activo=True)])
        s=dict(version='0.5.0',entrada=e,barrido=[dict(D_mm=200,L_m=L,z_m=L,Rc_fuste_kN=r['fuste_compresion']*L/10,Rt_fuste_kN=r['fuste_traccion']*L/10) for L in (5,10)],detalle_Lmax={'200':r},armaduras=[])
        wb=load_workbook(BytesIO(excel(s)))
        self.assertEqual(wb['Proyecto']['B2'].data_type,'s')
        self.assertEqual(len(wb['Graficas']._charts),2)
        self.assertEqual(wb['Compresion']['B3'].value,10)
        self.assertTrue(Document(BytesIO(word(s))).paragraphs)
        self.assertTrue(pdf(s).startswith(b'%PDF'))
