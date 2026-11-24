"""Barrido axial de capacidades por fuste. DGC 2005, 3.3 y 3.4.
La punta al 15% es una envolvente hipotetica, nunca capacidad acreditada.
"""
from math import cos, radians, isfinite, floor
from .axial import calcular

DIAMETROS_GUIA={114.3:120.,133.:140.,152.4:160.,177.8:185.,193.7:200.,219.1:225.}

def longitudes_barrido(minimo,maximo,paso,angulo,estratos):
    if not all(isfinite(x) for x in (minimo,maximo,paso,angulo)) or not (0<minimo<=maximo and paso>0 and 0<=angulo<90):
        raise ValueError('Intervalo de longitudes o inclinacion invalido.')
    if not estratos:
        raise ValueError('Introduzca el perfil geotecnico.')
    c=cos(radians(angulo))
    if maximo*c>estratos[-1].fin+1e-8:
        raise ValueError('La longitud maxima supera la profundidad reconocida.')
    n=(maximo-minimo)/paso
    if not isfinite(n) or n>5000:
        raise ValueError('Maximo 5001 puntos regulares por alternativa; aumente el incremento.')
    valores=[minimo+i*paso for i in range(floor(n)+1)]+[maximo]
    valores += [z/c for z in [5.]+[e.fin for e in estratos] if minimo<z/c<maximo]
    salida=[]
    for v in sorted(valores):
        if not salida or v-salida[-1]>1e-9:
            salida.append(v)
    salida[-1]=maximo
    return salida

def barrido(d,minimo,maximo,paso,angulo,estratos,meses,alternancia,punta_teorica=False):
    filas=[]
    for L in longitudes_barrido(minimo,maximo,paso,angulo,estratos):
        r=calcular(d,L,angulo,estratos,meses,alternancia)
        rc=r['fuste_compresion']
        p=.15*rc if punta_teorica else None
        filas.append(dict(D_mm=d*1000,L_m=L,z_m=r['profundidad'],Rc_fuste_kN=rc,
                          Rt_fuste_kN=r['fuste_traccion'],punta_max_hipotetica_kN=p,
                          Rc_max_hipotetica_kN=rc+p if p is not None else None))
    return filas
