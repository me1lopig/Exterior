import math
import numpy as np
import pandas as pd
import pytest
from src.engine import (Parametros,Estrato,dimensiones,validar_estratos,calculo_hundimiento,
    calcular_geometria,ejecutar_malla,contribuciones_asiento,esquina_m,bulbo_tensiones,
    factor_boussinesq_centro,tension_preexistente_kpa,descarga_pre_kpa,tabla_resultados,MAPA,numero)
from src.balasto_cte import calcular_detalle_balasto,comparar_criterios

CAPAS=(Estrato('A',0,2.5,15,.3), Estrato('B',2.5,10,1200,.2))

@pytest.mark.parametrize('x',[True,False,float('nan'),float('inf'),'0.1',-2])
def test_invalidos_numero(x):
    with pytest.raises(ValueError): numero(x,'x',minval=0)

def test_geometria_dimensionamiento():
    geoms=dimensiones(1,2,.5,1,3,.5)
    assert len(geoms)==3+4+5
    assert all(0<b<=l for b,l in geoms)

@pytest.mark.parametrize('bounds',[(2,1,.5,1,4,.5),(1,2,0,1,2,.5),(1,3,.1,1,3,.00001)])
def test_rechazo_mallas_invalidas(bounds):
    with pytest.raises(ValueError): dimensiones(*bounds)

def test_estratos_contiguos():
    assert len(validar_estratos(CAPAS))==2
    with pytest.raises(ValueError): validar_estratos((Estrato('A',.1,3,10,.3),))
    with pytest.raises(ValueError): validar_estratos((Estrato('A',0,3,10,.3),Estrato('B',2.9,10,20,.2)))
    with pytest.raises(ValueError): validar_estratos((Estrato('A',0,3,10,.3),Estrato('B',3.1,10,20,.2)))

@pytest.mark.parametrize('nu',[-.01,.5,.7])
def test_poisson_incorrecto(nu):
    with pytest.raises(ValueError): Estrato('x',0,1,100,nu).validar()

def test_q0_vs_sigma_explicitos():
    p=Parametros()
    assert tension_preexistente_kpa(1.,p)==18
    assert descarga_pre_kpa(p)==9
    assert calculo_hundimiento(2,3,p)['q0_kpa']==pytest.approx(9)

def test_nivel_freatico_total_efectivo():
    p=Parametros(nf_m=1,gamma_ap_kn_m3=18,gamma_sub_kn_m3=9)
    assert tension_preexistente_kpa(3,p,efectiva=True)==pytest.approx(36)
    assert tension_preexistente_kpa(3,p,efectiva=False)==pytest.approx(55.62)

def test_hundimiento_drenado_positivo_y_factores():
    h=calculo_hundimiento(2,3,Parametros())
    assert h['qh_bruta_mpa']>0
    assert h['sc']==pytest.approx(1+0.2*2/3)
    assert h['sgamma']==pytest.approx(1-0.3*2/3)

def test_phi_cero_y_no_drenado():
    p=Parametros(drenaje='No drenada',phi_deg=0,cohesion_kpa=50)
    h=calculo_hundimiento(2,3,p)
    assert h['Ngamma']==0
    assert h['Nc']==pytest.approx(5.14)

@pytest.mark.parametrize('mal_p',[Parametros(drenaje='No drenada',phi_deg=30),Parametros(factor_profundidad=True,D_m=.5),
  Parametros(flujo_ascendente=True,gradiente=100),Parametros(cu_gradiente=True,cu_z0_m=5,cu_z1_m=3)])
def test_parametros_invalidos(mal_p):
    with pytest.raises(ValueError): mal_p.validar()

def test_esquina_lineal_p():
    capa=CAPAS[0]
    u=esquina_m(1,1,1,1,capa)
    assert esquina_m(.25,1,1,1,capa)==pytest.approx(u*.25)

def test_asientos_mayor_presion_aumenta_linealmente():
    s1=contribuciones_asiento(2,3,CAPAS,'superposicion',.20)[-1]['Asiento acumulado (mm)']
    s2=contribuciones_asiento(2,3,CAPAS,'superposicion',.40)[-1]['Asiento acumulado (mm)']
    assert s2==pytest.approx(2*s1)
    assert s1>0

def test_calculo_servicio_y_balasto_consistentes():
    r=calcular_geometria(2,3,Parametros(),CAPAS)
    assert r['q_asiento_bruta_mpa']-r['q_asiento_neta_mpa']==pytest.approx(.009)
    assert r['q_hund_bruta_mpa']-r['q_hund_neta_mpa']==pytest.approx(.009)
    assert r['ks_bl_mn_m3']==pytest.approx(1000/r['flexibilidad_mm_mpa'])
    assert r['q_asiento_neta_mpa']*r['flexibilidad_mm_mpa']==pytest.approx(50)
    assert r['q_serv_neta_mpa']==pytest.approx(min(r['q_hund_neta_mpa'],r['q_asiento_neta_mpa']))
    assert r['q_serv_bruta_mpa']-r['q_serv_neta_mpa']==pytest.approx(.009)

def test_cambio_tipo_balasto_no_cambia_elastico():
    a=calcular_geometria(2,3,Parametros(tipo_balasto='Cohesivo'),CAPAS)
    b=calcular_geometria(2,3,Parametros(tipo_balasto='Granular'),CAPAS)
    assert a['ks_bl_mn_m3']==pytest.approx(b['ks_bl_mn_m3'])
    assert a['q_hund_neta_mpa']==pytest.approx(b['q_hund_neta_mpa'])
    assert a['q_asiento_neta_mpa']==pytest.approx(b['q_asiento_neta_mpa'])
    assert a['ksp30_mn_m3']!=pytest.approx(b['ksp30_mn_m3'])

def test_balasto_literal_vs_continuo_en_cuadrado():
    a=calcular_detalle_balasto(20,2,2,'Cohesivo',criterio='literal_cte')
    b=calcular_detalle_balasto(20,2,2,'Cohesivo',criterio='continuo')
    assert a.ksp30_mn_m3==pytest.approx(b.ksp30_mn_m3)

def test_salto_literal_y_continuidad_al_limite():
    a=calcular_detalle_balasto(20,2,2,'Cohesivo',criterio='literal_cte').ksp30_mn_m3
    b=calcular_detalle_balasto(20,2,2.000001,'Cohesivo',criterio='literal_cte').ksp30_mn_m3
    assert abs((b-a)/a)>.3
    x=calcular_detalle_balasto(20,2,2,'Cohesivo',criterio='continuo').ksp30_mn_m3
    y=calcular_detalle_balasto(20,2,2.000001,'Cohesivo',criterio='continuo').ksp30_mn_m3
    assert y==pytest.approx(x,rel=1e-6)

def test_rechazo_booleano_balasto():
    with pytest.raises(ValueError): calcular_detalle_balasto(True,2,3,'Cohesivo')

def test_boussinesq_invariantes():
    assert factor_boussinesq_centro(2,3,0)==1
    assert 0<factor_boussinesq_centro(2,3,1)<1
    assert factor_boussinesq_centro(2,3,30)<.01

def test_bulbo_datos_validos():
    f,z=bulbo_tensiones(2,3,Parametros(),CAPAS,.2,paso=.1)
    assert len(f)>50
    assert f.iloc[0]['Delta sigma vertical (kPa)']==pytest.approx(200)
    assert f['Delta sigma vertical (kPa)'].is_monotonic_decreasing

@pytest.mark.parametrize('tipo',['Cohesivo','Granular'])
def test_inversion_balasto_referencia(tipo):
    x=calcular_detalle_balasto(25,2,3,tipo,criterio='continuo')
    assert x.ks_b_mn_m3*x.factor_forma==pytest.approx(25)
    assert x.ksp30_mn_m3*x.factor_escala==pytest.approx(x.ks_b_mn_m3)

def test_mapa_nueve_metricas_y_brutas():
    assert len(MAPA)==9
    assert len([k for k in MAPA if '(bruta)' in k])==3
    row=ejecutar_malla(((2,3),),Parametros(),CAPAS)
    for field in MAPA.values(): assert field in row[0]
    df=tabla_resultados(row)
    assert 'q servicio bruta (MPa)' in df

def test_no_valida_presion_neta_negativa():
    p=Parametros(descarga_manual_kpa=3000)
    r=calcular_geometria(2,3,p,CAPAS)
    assert r['q_serv_neta_mpa'] is None
    assert r['q_serv_bruta_mpa'] is None
    assert r['limitacion']=='No valido'

def test_malla_reproducible():
    g=dimensiones(1,2,.5,1,3,.5)
    a=ejecutar_malla(g,Parametros(),CAPAS)
    b=ejecutar_malla(g,Parametros(),CAPAS)
    assert a==b

def test_500_casos_aleatorios_balasto_invariante():
    rng=np.random.default_rng(2026)
    for _ in range(500):
        b=float(rng.uniform(.30,5.0));l=float(b*rng.uniform(1,9))
        ks=float(rng.uniform(1,1000));tipo=str(rng.choice(['Cohesivo','Granular']))
        for criterio in ['literal_cte','continuo']:
            x=calcular_detalle_balasto(ks,b,l,tipo,criterio=criterio)
            assert x.ks_b_mn_m3*x.factor_forma==pytest.approx(ks)
            assert x.ksp30_mn_m3*x.factor_escala==pytest.approx(x.ks_b_mn_m3)

def test_corrida_historica_documentada():
    from src.engine import calcular_corrida_historica,calculo_hundimiento,calcular_geometria
    p=Parametros()
    r=calcular_corrida_historica(2,p,CAPAS)
    cuadrado_elastico=calcular_geometria(2,100,p,CAPAS)
    hund=calculo_hundimiento(2,1000,p)
    assert r['q_asiento_neta_mpa']==pytest.approx(cuadrado_elastico['q_asiento_neta_mpa'])
    assert r['q_hund_bruta_mpa']==pytest.approx(hund['qh_bruta_mpa'])
    assert 'Corrida aproximada' in r['avisos'][-1]

@pytest.mark.parametrize('capas,esperado',[
 ((Estrato('Homog.',0,10,20,.3),),21.757653365161516),
 ((Estrato('A',0,2.5,15,.3),Estrato('B',2.5,10,1200,.2)),19.176886203665354),
])
def test_casos_referencia_elasticos(capas,esperado):
    resultado=contribuciones_asiento(2,3,capas,'superposicion',.2)[-1]['Asiento acumulado (mm)']
    assert resultado==pytest.approx(esperado,rel=1e-10)
