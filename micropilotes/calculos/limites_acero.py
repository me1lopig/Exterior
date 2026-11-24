"""Predimensionamiento por acero solo, sin sumar lechada ni punta.
DGC 2005 3.6.1/2: contribucion de acero con factores de union, ejecucion,
corrosion y pandeo. No constituye verificacion completa de micropilote.
"""
from math import isfinite
from .estructural import seccion, UNIONES, EJECUCION
from modelos.tablas_guia import recubrimiento

def limite_acero(tubo,fy,re,union,ejec,cr,uc=None,ut=None):
    if not isfinite(fy) or fy<=0 or (cr is not None and (not isfinite(cr) or cr<0)):
        raise ValueError('fy o CR invalido.')
    s=seccion(tubo.de_mm,tubo.t_mm,re)
    R=None if cr is None else min(1.,1.07-.027*cr)
    if R is not None and R<=0: R=None  # no evaluar compresion; traccion independiente
    fuc,fut=UNIONES[union]; fe=EJECUCION[ejec]
    ac=s['a_residual_mm2']
    fc=min(fy/1.10,400.); ft=fy/1.10
    base_c=ac*fc/1000
    nc=None if R is None else base_c*fuc*R/(1.20*fe)
    nt=ac*ft*fut/1.10/1000
    for v in (uc,ut):
        if v is not None and (not isfinite(v) or v<=0): raise ValueError('Limite de union invalido.')
    return {**s,'fyd_c_MPa':fc,'fyd_t_MPa':ft,'fu_c':fuc,'fu_t':fut,'Fe':fe,'R':R,
            'A_fyd_c_kN':base_c,'nc_kN':min(nc,uc) if nc is not None and uc is not None else nc,
            'nt_kN':min(nt,ut) if ut is not None else nt,
            'carga_catalogo_kN':tubo.carga_catalogo_kN}

def longitud_cruce(L,capacidades,limite):
    """Primer cruce exacto dentro del intervalo, incluido su inicio."""
    if capacidades[0]>=limite: return L[0]
    for a,b,u,v in zip(L,L[1:],capacidades,capacidades[1:]):
        if u<limite<=v:
            return a+(b-a)*(limite-u)/(v-u)
    return None

def envolvente(L,capacidades,limite):
    x=list(L)
    cr=longitud_cruce(L,capacidades,limite)
    if cr is not None and all(abs(cr-l)>1e-9 for l in L):
        x.append(cr)
    x.sort()
    if cr is None: return x,list(capacidades)
    valores=dict(zip(L,capacidades))
    return x,[limite if l>=cr else valores[l] for l in x]
