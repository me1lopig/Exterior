"""Published Steinbrenner regression suite for the unmodified v1.5 calculation engine."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import pytest
from calculos.steinbrenner import calcular_steinbrenner, compresion_rectangulo_m
from modelos.datos import Cimentacion, COLUMNAS_ESTRATOS, validar_estratos

DATA=json.loads((Path(__file__).parent/'casos_referencias_publicadas.json').read_text(encoding='utf8'))


def layers(items):
    return pd.DataFrame([[name,top,bottom,18.,20.,E,nu] for name,top,bottom,E,nu in items],columns=COLUMNAS_ESTRATOS)


def settlement_center(case):
    H=case.get('numerical_H_m',case['H'])
    if case['H']=='infinite':
        return 1000.*compresion_rectangulo_m(0,0,H,case['B'],case['L'],case['q'],case['E'],case['nu'])
    st=layers([('Soil',0,H,case['E'],case['nu'])])
    r=calcular_steinbrenner(Cimentacion(case['B'],case['L'],case['q'],0),st,H,paso_perfil_m=max(H/12,.1))
    return float(r.resumen_puntos.set_index('Punto').loc['Centro','asiento_base_mm'])


@pytest.mark.parametrize('case',DATA['ministerio'],ids=lambda c:c['id'])
def test_ministerio_tabla_71(case):
    result=settlement_center(case)
    assert abs(result-case['reference_mm']) <= case['tol_mm'], (case['id'],result,case['reference_mm'])


@pytest.mark.parametrize('point', ['center','corner'])
def test_hkie_hb1_point(point):
    c=DATA['hkie']
    st=layers([('Soil',0,c['H'],c['E'],c['nu'])])
    r=calcular_steinbrenner(Cimentacion(c['B'],c['L'],c['q'],0),st,c['H'],paso_perfil_m=.8)
    label={'center':'Centro','corner':'Esquina'}[point]
    result=float(r.resumen_puntos.set_index('Punto').loc[label,'asiento_base_mm'])
    assert abs(result-c['points'][point]) <= c['tolerances_mm'][point]


def test_hkie_hb1_mean_trapezoidal_441_nodes():
    c=DATA['hkie']
    xs=np.linspace(-c['B']/2,c['B']/2,21)
    ys=np.linspace(-c['L']/2,c['L']/2,21)
    vals=np.array([[compresion_rectangulo_m(x,y,c['H'],c['B'],c['L'],c['q'],c['E'],c['nu'])*1000. for y in ys] for x in xs])
    wx=np.ones(21);wy=np.ones(21)
    wx[[0,-1]]=.5;wy[[0,-1]]=.5
    result=float(np.sum(vals*np.outer(wx,wy))/400.)
    assert abs(result-c['points']['average_441']) <= c['tolerances_mm']['average_441']


def geo_parts():
    c=DATA['geo']; results=[]
    for layer in c['layers']:
        kwargs=dict(x_m=c['x'],y_m=c['y'],b_m=c['B'],l_m=c['L'],q_kpa=c['q'],e_mpa=layer['E'],nu=c['nu'])
        part=(compresion_rectangulo_m(espesor_m=layer['z_bottom'],**kwargs)-compresion_rectangulo_m(espesor_m=layer['z_top'],**kwargs))*1000.
        results.append(part)
    return results


@pytest.mark.parametrize('i',[0,1,2])
def test_geo_tools_characteristic_point_by_layer(i):
    c=DATA['geo'];result=geo_parts()[i]
    assert abs(result-c['layers'][i]['reference_mm']) <= c['tol_mm']


def test_geo_tools_total_characteristic_point():
    c=DATA['geo']
    assert abs(sum(geo_parts())-c['reference_total_mm']) <= c['tol_mm']


def test_geo_tools_nu_zero_is_accepted_by_UI_validation():
    c=DATA['geo']
    st=layers([(v['name'],v['z_top'],v['z_bottom'],v['E'],c['nu']) for v in c['layers']])
    _,errors=validar_estratos(st,18.)
    assert not errors, f'nu=0 es admisible en el modelo elastico: {errors}'


@pytest.mark.parametrize('point', ['center','corner'])
def test_a4_se20_annex(point):
    c=DATA['a4'];q=c['q_kg_cm2']*c['kgf_cm2_kPa'];E=c['E_kg_cm2']*c['kgf_cm2_kPa']/1000
    st=layers([('Soil',0,c['H'],E,c['nu'])])
    r=calcular_steinbrenner(Cimentacion(c['B'],c['L'],q,0),st,c['H'],paso_perfil_m=1.0)
    label={'center':'Centro','corner':'Esquina'}[point]
    result=float(r.resumen_puntos.set_index('Punto').loc[label,'asiento_base_mm'])
    assert abs(result-c['reference_mm'][point]) <= c['tol_mm']


def test_excel_asientos_3_total():
    c=DATA['excel']
    st=layers([(f'Layer{i}',z0,z1,E,c['nu']) for i,(z0,z1,E) in enumerate(c['layers'],1)])
    r=calcular_steinbrenner(Cimentacion(c['B'],c['L'],c['q'],0),st,20.,paso_perfil_m=1.)
    result=float(r.resumen_puntos.set_index('Punto').loc['Centro','asiento_base_mm'])
    assert abs(result-c['reference_total_mm']) <= c['tol_total_mm']


def test_excel_asientos_3_q_admissible():
    c=DATA['excel']
    st=layers([(f'Layer{i}',z0,z1,E,c['nu']) for i,(z0,z1,E) in enumerate(c['layers'],1)])
    r=calcular_steinbrenner(Cimentacion(c['B'],c['L'],c['q'],0),st,20.,paso_perfil_m=1.)
    settlement=float(r.resumen_puntos.set_index('Punto').loc['Centro','asiento_base_mm'])
    q_limit=c['q']*50./settlement
    assert abs(q_limit-c['reference_q_50mm_kPa']) <= c['tol_q_kpa']
