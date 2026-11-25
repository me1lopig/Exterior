import unittest
from math import pi
from modelos.inyecciones import preparar,migrar,COLS
from calculos.axial import calcular
from resultados.inyecciones import calcular_escenario,filas_comparativas
from servicios.proyecto import serializar,cargar

class InyeccionesTests(unittest.TestCase):
    def setUp(self):
        self.f=[dict(nombre='UG',espesor_m=10.,IU_MPa=.08,IR_MPa=.12,IRS_MPa=.15,inyeccion='IRS',activo=True)]
    def test_tres_metodos_y_corte(self):
        for modo,v in [('IU',80),('IR',120),('IRS',150),('Mixto',150)]:
            e,d=preparar(self.f,10,1.65,modo)
            r=calcular(.2,10,0,e,12,True)
            self.assertAlmostEqual(r['fuste_compresion'],pi*.2*(5*80+5*v)/1.65)
            self.assertAlmostEqual(r['fuste_traccion'],.6*r['fuste_compresion'])
            self.assertEqual(r['tramos'][0]['r_lim'],80)
            self.assertEqual(r['tramos'][1]['r_lim'],v)
    def test_ausencia_no_es_cero(self):
        self.f[0]['IR_MPa']=None
        with self.assertRaises(ValueError): preparar(self.f,10,1.65,'IR')
        e,d=preparar(self.f,4,1.65,'IR')
        self.assertIsNone(d[0]['adlim_kPa'])
        self.assertEqual(calcular(.2,4,0,e,12,False)['tramos'][0]['r_lim'],80)
        self.f[0]['activo']=False
        e,d=preparar(self.f,10,1.65,'IR')
        self.assertEqual(calcular(.2,10,0,e,12,False)['fuste_compresion'],0)
    def test_presiones_independientes(self):
        preparar(self.f,10,1.65,'IR',{(0,'IR'):(600,1000)})
        with self.assertRaises(ValueError): preparar(self.f,10,1.65,'IRS',{(0,'IRS'):(600,1000)})
    def test_migracion_y_esquema(self):
        f=[dict(nombre='UG',espesor_m=10.,inyeccion='IRS',adlim_kPa=150.,fr=1.65,activo=True)]
        x=migrar(f,{'iu_0_UG_IRS_0.0_10.0':80.})
        self.assertEqual(x[0]['IU_MPa'],.08);self.assertEqual(x[0]['IRS_MPa'],.15);self.assertIsNone(x[0]['IR_MPa'])
        self.assertEqual(cargar(serializar({},x,'0.7.0'))['estratos'],x)
        self.assertEqual(cargar(serializar({},f,'0.6.1'))['estratos'],f)
    def test_comparacion_armadura(self):
        datos={}
        for n in ('IU','IR','IRS'):
            e,d=preparar(self.f,10,1.65,n)
            datos[n]=calcular_escenario(e,d,{200:220},3,10,.5,0,12,True,False,[dict(alternativa='A',D_mm=200,limite_c_kN=400.,limite_t_kN=200.)])
        self.assertEqual(len(filas_comparativas(datos)),3)
        self.assertAlmostEqual(datos['IRS']['armaduras'][0]['Rc_parcial_Lmax_kN'],400)
        self.assertLess(datos['IU']['armaduras'][0]['Rc_parcial_Lmax_kN'],400)
