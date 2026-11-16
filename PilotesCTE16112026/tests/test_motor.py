import math
import pytest

from pilotes_cte.core import (
    Estrato, Configuracion, Geometria, ErrorDatos, CLASES_RN,
    comprobar_estratos, comprobar_nf, crear_seccion, seleccionar_gamma,
    tensiones, perfil_tensiones, punta, calcular_pilote,
    matriz_calculo, _area_tau_drenada,
)


def granular(h=30,phi=30, gamma=18, nombre='G',clase='No definida'):
    return Estrato(nombre,h,gamma,20,'Granular','Largo Plazo',0,phi,clase)


def fino(h=30,cu=40,phi=0,nombre='F',cond='Corto Plazo',clase='No definida'):
    return Estrato(nombre,h,18,20,'Fino',cond,cu,phi,clase)


def conf(zw=None,**kwargs):
    return Configuracion(nivel_freatico=zw,fuste_nulo=0,**kwargs)


def test_nf_ausente_tension_lineal():
    e=[granular(10),granular(5,gamma=19,nombre='G2')]
    assert tensiones(15,e,None)==pytest.approx((275,0,275))


def test_nf_superficie():
    s=tensiones(10,[granular()],0)
    assert s==(pytest.approx(200),pytest.approx(98.1),pytest.approx(101.9))


def test_nf_entre_estratos_exactitud():
    e=[granular(4),granular(10,gamma=19,nombre='G2')]
    # 4 m seco (18), 2 m seco (19), 4 m saturado (20)
    assert tensiones(10,e,6)==pytest.approx((72+38+80,4*9.81,190-4*9.81))


def test_nf_dentro_estrato():
    assert tensiones(10,[granular()],6)==pytest.approx((6*18+4*20,4*9.81,6*18+4*20-4*9.81))


def test_nf_en_fondo_equivalente_seco():
    a=tensiones(10,[granular(10)],None)
    b=tensiones(10,[granular(10)],10)
    assert a==pytest.approx(b)


@pytest.mark.parametrize('z', [-.01, 20.01, float('nan'),float('inf')])
def test_tension_fuera_sondeo(z):
    with pytest.raises(ErrorDatos):tensiones(z,[granular(20)],None)


@pytest.mark.parametrize('zw', [-1,30,float('nan'),float('inf')])
def test_nf_fuera_rango(zw):
    with pytest.raises(ErrorDatos):comprobar_nf(zw,20)


def test_perfil_termina_fondo_sondeo():
    zs,sv,u,se=perfil_tensiones([granular(2),granular(3,nombre='G2')],None)
    assert zs[0]==0 and zs[-1]==5 and all(z<=5 for z in zs)
    assert all(v==0 for v in u)


def test_area_circular():
    d=.8;s=crear_seccion(Geometria(diametro=d))
    assert s.area_punta==pytest.approx(math.pi*d*d/4)
    assert s.area_estructural==s.area_punta
    assert s.perimetro_fuste==pytest.approx(math.pi*d)


def test_tubular_estructural_vs_punta():
    s=crear_seccion(Geometria(tipo='Tubular acero',diametro=.5,espesor_pared=.02))
    assert s.area_punta==pytest.approx(math.pi*.5**2/4)
    assert s.area_estructural==pytest.approx(math.pi*(.5**2-.46**2)/4)
    assert s.perimetro_fuste==pytest.approx(math.pi*.5)


@pytest.mark.parametrize('b,h,expected',[(.3,.3,.3*.3),(.3,.6,1.5*.3**2)])
def test_perfil_H_min_area(b,h,expected):
    geo=Geometria(tipo='Perfil H acero',ancho_ala=b,canto=h,espesor_ala=.02,espesor_alma=.01)
    s=crear_seccion(geo)
    assert s.area_punta==pytest.approx(expected)
    assert s.area_estructural==pytest.approx(2*b*.02+(h-.04)*.01)
    assert s.perimetro_fuste==pytest.approx(2*(b+h))
    assert s.d_equivalente==pytest.approx(math.sqrt(4*expected/math.pi))


@pytest.mark.parametrize('geo', [Geometria(diametro=0),
                                  Geometria(tipo='Tubular acero',diametro=.2,espesor_pared=.12),
                                  Geometria(tipo='Perfil H acero',ancho_ala=.3,canto=.3,espesor_ala=.2)])
def test_geometria_invalida(geo):
    with pytest.raises(ErrorDatos):crear_seccion(geo)


def test_f30_punta_con_phi_constante_nq():
    e=[granular()]
    geo=Geometria(diametro=1)
    cfg=conf()
    q0,q,limit,detalle,notas=punta(e,crear_seccion(geo),10,cfg)
    rad=math.radians(30)
    nq=(1+math.sin(rad))/(1-math.sin(rad))*math.exp(math.pi*math.tan(rad))
    assert q==pytest.approx(min(2.5*(10*18)*nq,20000))
    assert limit is None


def test_f30_phi_medio_antes_de_Nq():
    e=[granular(10,phi=25,nombre='A'),granular(20,phi=35,nombre='B')]
    geo=Geometria(diametro=1)
    cfg=conf()
    # tip 11m: [5,14] -> 5m de A, 4m B
    q0,q,_,audit,_=punta(e,crear_seccion(geo),11,cfg)
    phi_eq=(5*25+4*35)/9
    rad=math.radians(phi_eq)
    nq=(1+math.sin(rad))/(1-math.sin(rad))*math.exp(math.pi*math.tan(rad))
    assert q==pytest.approx(2.5*(11*18)*nq)
    assert any(a['Parámetro']=='φ equivalente' and a['Valor']==pytest.approx(phi_eq) for a in audit)


def test_f32_cu_promedio_2D_2D():
    e=[fino(10,cu=30,nombre='F1'),fino(20,cu=90,nombre='F2')]
    geo=Geometria(diametro=1)
    # Punta a z=9: 2D above=7, below=11 => 3 m F1 and 1 m F2 => cu_eq=45
    q0,q,_,audit,_=punta(e,crear_seccion(geo),9,conf())
    assert q0==pytest.approx(9*45)
    assert q==pytest.approx(q0)
    assert any(a['Parámetro']=='cu equivalente' and a['Valor']==pytest.approx(45) for a in audit)


def test_511_capa_blanca_limita_punta():
    e=[fino(11,cu=160,nombre='Fuerte'),fino(10,cu=20,nombre='Blanda')]
    r=calcular_pilote(e,Geometria(diametro=1),10,conf())
    # H=1m; qp<=6*(1+1/1)^2*20 = 480 kPa
    assert r.q_limite_511==pytest.approx(480)
    assert r.q_p==pytest.approx(480)
    assert r.q_p_sin_limite>480
    assert r.r_pk==pytest.approx(480*math.pi/4)


def test_511_sin_capa_inferior_no_aplicable():
    r=calcular_pilote([fino(20,cu=100)],Geometria(diametro=.7),10,conf())
    assert r.q_limite_511 is None


def test_511_capa_limita_por_menor_h():
    e=[granular(10),fino(3,cu=10,nombre='F1'),fino(10,cu=8,nombre='F2')]
    r=calcular_pilote(e,Geometria(diametro=1),10,conf())
    # F1 at tip -> H=0 => 60 kPa, F2 at H=3 => 6*(4)^2*8=768 kPa
    assert r.q_limite_511==pytest.approx(60)


def test_f31_fuste_suelo_granular_tope_120():
    e=[granular(30,phi=55)]
    r=calcular_pilote(e,Geometria(diametro=1),20,conf())
    # deep portion high, but all portions capped; verify no unit segment >120
    assert all(x['τ media (kPa)']<=120+1e-7 for x in r.detalles_fuste)
    assert any(x['τ media (kPa)']>100 for x in r.detalles_fuste)


def test_f31_fuste_suelo_fino_largo_tope_100():
    e=[fino(30,cu=100,phi=55,cond='Largo Plazo')]
    r=calcular_pilote(e,Geometria(diametro=1),20,conf())
    assert all(x['τ media (kPa)']<=100+1e-8 for x in r.detalles_fuste)
    # La integral es menor que 100 porque el tramo empieza sin confinamiento.
    z_cap=100/(18*0.75*math.tan(math.radians(55)))
    media=(100*z_cap/2+100*(20-z_cap))/20
    assert r.detalles_fuste[-1]['τ media (kPa)']==pytest.approx(media)


def test_integral_drenado_corte_cap():
    # τ(z) grows linearly from 0 to 200, capped at 100 halfway -> area 25+50=75 over L1
    assert _area_tau_drenada(0,1,0,200,1,100)==pytest.approx(75)
    # τ falls 200→0 -> 50 + 25 = 75
    assert _area_tau_drenada(0,1,200,0,1,100)==pytest.approx(75)


def test_f33_fuste_cu_constante():
    e=[fino(30,cu=100)]
    r=calcular_pilote(e,Geometria(diametro=1),10,conf())
    assert r.r_fk==pytest.approx((100*100/(100+100))*math.pi*10)


def test_acero_corto_fuste_08():
    e=[fino(30,cu=100)]
    g=Geometria(tipo='Tubular acero',diametro=1,espesor_pared=.05)
    cfg=conf(ejecucion='Hincados',material='Metálicos',sigma_tope_mpa=80)
    r=calcular_pilote(e,g,10,cfg)
    assert r.r_fk==pytest.approx(50*.8*math.pi*10)
    assert r.r_estructural==pytest.approx(crear_seccion(g).area_estructural*80000)


def test_integracion_fuste_no_mas_allá_de_nulo():
    e=[fino(30,cu=100)]
    cfg=Configuracion(nivel_freatico=None,fuste_nulo=12)
    r=calcular_pilote(e,Geometria(diametro=1),10,cfg)
    assert r.r_fk==0


def test_roz_negativo_sin_solape_positivo_y_beta():
    e=[granular(30,phi=30,clase='Arena floja')]
    cfg=conf(rozamiento_negativo=True,rn_desde=0,rn_hasta=4)
    r=calcular_pilote(e,Geometria(diametro=1),10,cfg)
    # β=0.10, sigma=18z, integral over [0,4] = 18*8
    assert r.rn_k==pytest.approx(.1*18*8*math.pi)
    assert all(x['Desde (m)']>=4-1e-8 for x in r.detalles_fuste)
    assert r.rn_d==pytest.approx(r.rn_k)
    assert r.r_cabeza_orientativa<=r.r_cd


def test_roz_negativo_por_capas_y_NF():
    e=[granular(4,phi=30,nombre='A',clase='Arena floja'),
       granular(20,phi=30,nombre='B',clase='Arena densa')]
    cfg=conf(zw=2,rozamiento_negativo=True,rn_desde=1,rn_hasta=6)
    r=calcular_pilote(e,Geometria(diametro=1),10,cfg)
    # expected exact integral independently from mean sigma on pieces: 1..2, 2..4, 4..6
    s=lambda z:tensiones(z,e,2)[2]
    expected=math.pi*(.1*((s(1)+s(2))/2*1+(s(2)+s(4))/2*2)+
                     .8*((s(4)+s(6))/2*2))
    assert r.rn_k==pytest.approx(expected)
    assert all(not (x['Desde (m)']<6 and x['Hasta (m)']>1) for x in r.detalles_fuste)


def test_roz_negativo_sin_beta_rechazado():
    cfg=conf(rozamiento_negativo=True,rn_desde=0,rn_hasta=3)
    with pytest.raises(ErrorDatos,match='definir la clase'):
        calcular_pilote([granular(30)],Geometria(diametro=.7),10,cfg)


def test_roz_negativo_fuera_sondeo():
    cfg=conf(rozamiento_negativo=True,rn_desde=0,rn_hasta=40)
    with pytest.raises(ErrorDatos):calcular_pilote([granular(30,clase='Arena floja')],Geometria(diametro=.7),10,cfg)


def test_gamma_persistente_largo():
    assert seleccionar_gamma([granular()], 'Persistente/transitoria')[0]==3


def test_gamma_corto_analitico():
    assert seleccionar_gamma([fino()], 'Persistente/transitoria')[0]==2


def test_gamma_mezcla_conservador_3():
    assert seleccionar_gamma([fino(10),granular(10,nombre='G')], 'Persistente/transitoria')[0]==3


def test_gamma_extraordinario():
    assert seleccionar_gamma([granular()], 'Extraordinaria')[0]==2


def test_gamma_manual_requiere_justificacion():
    with pytest.raises(ErrorDatos):seleccionar_gamma([granular()], 'Persistente/transitoria', 1.4, 'No')
    x,y=seleccionar_gamma([granular()], 'Persistente/transitoria', 3.4, 'Justificación de proyecto')
    assert x==pytest.approx(3.4) and 'Justificación' in y


@pytest.mark.parametrize('suelo', [granular(phi=90),granular(phi=float('nan')),
                                      granular(gamma=0),fino(cu=0),
                                      Estrato('X',10,20,18,'Fino','Corto Plazo',40,0)])
def test_estratos_invalidos(suelo):
    with pytest.raises(ErrorDatos):comprobar_estratos([suelo])


def test_perfil_vacio_y_nombres_repetidos():
    with pytest.raises(ErrorDatos):comprobar_estratos([])
    with pytest.raises(ErrorDatos):comprobar_estratos([granular(2),granular(2)])


def test_matriz_nd_para_bulbo_fuera_sondeo():
    e=[granular(12)]
    rs,err=matriz_calculo(e,conf(),[Geometria(diametro=1)], [6,10])
    assert len(rs)==1 and rs[0].longitud==6
    assert len(err)==1 and 'Bulbo' in err[0]['Causa']


def test_transicion_heterogenea_se_marca_y_acota():
    e=[fino(8,cu=20),granular(20,phi=40)]
    r=calcular_pilote(e,Geometria(diametro=1),10,conf())
    assert any('Transición' in s for s in r.observaciones)


def test_invariantes_positividad():
    e=[granular(30)]
    r=calcular_pilote(e,Geometria(diametro=.6),10,conf())
    assert r.r_pk>=0 and r.r_fk>=0 and r.r_cd>=0
    assert r.r_ck==pytest.approx(r.r_pk+r.r_fk)
    assert r.r_cd==pytest.approx(r.r_ck/3)


def test_beta_incompatible_con_tipo_suelo():
    with pytest.raises(ErrorDatos,match='incompatible'):
        comprobar_estratos([granular(clase='Arcilla/limo blando')])
    with pytest.raises(ErrorDatos,match='incompatible'):
        comprobar_estratos([fino(clase='Arena densa')])


def test_regresion_modelo_granular_homogeneo_sin_nf():
    """Referencia manual: coincide con F.30/F.31 sin cambios de estrato ni topes."""
    d=.6;L=10.;phi=30;gamma=18.
    rad=math.radians(phi)
    nq=(1+math.sin(rad))/(1-math.sin(rad))*math.exp(math.pi*math.tan(rad))
    q=2.5*gamma*L*nq
    punta_ref=q*math.pi*d*d/4
    fuste_ref=(gamma*L**2/2)*.75*math.tan(rad)*math.pi*d
    r=calcular_pilote([granular(30,phi=phi)],Geometria(diametro=d),L,conf())
    assert r.r_pk==pytest.approx(punta_ref,rel=1e-12)
    assert r.r_fk==pytest.approx(fuste_ref,rel=1e-12)
    assert r.r_cd==pytest.approx((punta_ref+fuste_ref)/3,rel=1e-12)


def test_regresion_fino_corto_homogeneo_sin_nf():
    """Referencia manual: Rpk=9cu Ap, Rfk=(100cu/(100+cu))·πDL."""
    d=.8;L=12.;cu=60
    r=calcular_pilote([fino(30,cu=cu)],Geometria(diametro=d),L,conf())
    assert r.r_pk==pytest.approx(9*cu*math.pi*d*d/4)
    assert r.r_fk==pytest.approx((100*cu/(100+cu))*math.pi*d*L)


def test_magnitudes_extremas_rechazadas():
    with pytest.raises(ErrorDatos): comprobar_estratos([fino(cu=1e308)])
    with pytest.raises(ErrorDatos): comprobar_estratos([granular(h=1e308)])
    with pytest.raises(ErrorDatos): crear_seccion(Geometria(diametro=1e308))
