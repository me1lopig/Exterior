"""Seccion axial tubular sin barras adicionales. DGC 2005, 3.6.1-2.
Entradas: D, de, t, re en mm; resistencias de materiales en MPa; salida kN.
No comprueba conexion al encepado, flexion, cortante ni durabilidad quimica.
"""
from math import isfinite, pi

# Tipologias de union segun tablas 3.4 y 3.7; no inferir por nombre comercial.
UNIONES={'Manguito exterior sin perdida de seccion':(1.,1.),
         'Machihembrada con seccion ensanchada':(1.,1.),
         'Machihembrada sin ensanchar y contacto a tope':(1.,.5),
         'Otra union acreditada sin perdida':(1.,1.),
         'Resto de casos':(.5,.5)}
EJECUCION={'Sin revestir, sin lodos, agua sobre punta':1.50,
           'Sin revestir, sin lodos, agua siempre bajo punta':1.30,
           'Con lodos':1.15,'Revestimiento recuperable':1.05,
           'Camisa perdida':1.00}

# Seleccion inicial de dimensiones nominales, catalogo Comercial de Sondeos, p. 6 impresa.
# El grado de acero y capacidad de union se introducen con certificado, no se deducen.
PERFILES=[(88.9,6.),(88.9,8.),(101.6,6.),(101.6,9.),(114.3,7.),
          (114.3,9.),(127.,8.),(127.,10.),(139.7,7.),(139.7,9.),
          (152.4,9.),(168.3,10.),(177.8,10.),(219.,10.)]

def seccion(d,t,re):
    if not all(isfinite(v) for v in (d,t,re)) or not (0<t<d/2 and 0<=re<t):
        raise ValueError('Diametro, espesor o corrosion incompatibles.')
    di=d-2*t
    dr=d-2*re
    a=pi/4*(dr**2-di**2)
    i=pi/64*(dr**4-di**4)
    return {'di_mm':di,'de_residual_mm':dr,'a_nominal_mm2':pi/4*(d*d-di*di),
            'a_residual_mm2':a,'i_residual_mm4':i,'w_residual_mm3':2*i/dr}

def axial_estructural(D,de,t,re,fy,fck,union,ejecucion,cr,referencia,
                      relleno_interior=False, limite_union_c=None, limite_union_t=None):
    if not all(isfinite(v) for v in (D,fy,fck,cr)) or not (de<D<300 and fy>0 and fck>0 and cr>=0):
        raise ValueError('Geometria, materiales o pandeo invalidos.')
    if union not in UNIONES or ejecucion not in EJECUCION or not referencia.strip():
        raise ValueError('Justifique materiales, corrosion, union, ejecucion y coaccion lateral.')
    s=seccion(de,t,re)
    r=min(1.,1.07-.027*cr)
    if r<=0:
        raise ValueError('Factor empirico de pandeo no positivo: requiere analisis especifico.')
    fuc,fut=UNIONES[union]
    fe=EJECUCION[ejecucion]
    # Seccion de lechada conservadora: no recuperar el area perdida por corrosion.
    ac=pi/4*D**2-s['a_nominal_mm2']
    if not relleno_interior:
        ac-=pi/4*s['di_mm']**2
    fyd_c=min(fy/1.10,400.)
    fyd_t=fy/1.10
    nc=(.85*ac*fck/1.50+s['a_residual_mm2']*fuc*fyd_c)*r/(1.20*fe)/1000
    nt=s['a_residual_mm2']*fut*fyd_t/1.10/1000
    for lim in (limite_union_c,limite_union_t):
        if lim is not None and (not isfinite(lim) or lim<=0):
            raise ValueError('Capacidad de union acreditada invalida.')
    return {**s,'ac_mm2':ac,'fyd_c_MPa':fyd_c,'fyd_t_MPa':fyd_t,'fu_c':fuc,'fu_t':fut,
            'fe':fe,'R':r,'nc_seccion_kN':nc,'nt_seccion_kN':nt,
            'nc_kN':min(nc,limite_union_c) if limite_union_c is not None else nc,
            'nt_kN':min(nt,limite_union_t) if limite_union_t is not None else nt,
            'uniones_acreditadas':limite_union_c is not None and limite_union_t is not None}
