"""Comprobaciones de aplicabilidad y predimensionamiento por fuste.
Guia DGC 2005, 3.3.1.1, 3.3.2.4, 3.4 y 4.4.2. SI: m, kN, kPa.
Las comprobaciones de datos no sustituyen la justificacion geotecnica.
"""
from math import cos, isfinite, radians
from .axial import Estrato, calcular

def validar_inyeccion(tipo, pi, plim):
    """Filtro conservador de las condiciones habituales de 4.4.2.
    pi: minima durante IU, final de ultima fase IR, minima de reinyeccion IRS.
    plim: representativo local. Fuera del filtro se requieren otros metodos.
    """
    if tipo not in ('IU','IR','IRS') or not all(isfinite(v) and v > 0 for v in (pi,plim)):
        raise ValueError('Tipo de inyeccion o presiones invalidos.')
    if tipo in ('IU','IR'):
        if not (pi >= 500 and .5*plim <= pi <= plim):
            raise ValueError('IU/IR fuera del filtro: pi >= 500 kPa y 0.5 Plim <= pi <= Plim.')
    elif not (pi > 1000 and pi >= plim):
        raise ValueError('IRS fuera del filtro: pi > 1000 kPa y pi >= Plim.')

def validar_punta(d, longitud, angulo, profundidad_reconocida, tipo, superior, inferior, empotramiento, referencia):
    """Parametros prudentes N corregido o qu en kPa; distancias medidas en eje.
    Filtro conservador: ambas zonas deben superar el umbral, sin suelos mixtos.
    El usuario debe acreditar continuidad, geometria y estimaciones representativas.
    """
    if not all(isfinite(v) for v in (d,longitud,angulo,profundidad_reconocida,superior,inferior,empotramiento)):
        raise ValueError('Datos de punta no finitos.')
    if not (0 < d < .3 and longitud > 0 and 0 <= angulo < 90):
        raise ValueError('Geometria de punta invalida.')
    umbral = {'Granular':30.,'Cohesivo':100.}.get(tipo)
    if umbral is None or min(superior,inferior) <= umbral:
        raise ValueError('Punta fuera de umbrales del filtro (N > 30 o qu > 100 kPa).')
    if empotramiento < 6*d or empotramiento > longitud:
        raise ValueError('Empotramiento requerido >= 6D y <= longitud.')
    if profundidad_reconocida + 1e-8 < (longitud+3*d)*cos(radians(angulo)):
        raise ValueError('Falta reconocimiento hasta 3D bajo el plano de punta.')
    if not referencia.strip():
        raise ValueError('Documente el terreno, los parametros y las zonas 6D/3D.')
    return (superior+inferior)/2

def longitud_necesaria(d, max_l, angulo, estratos, meses, alternancia, nc, nt, min_l=.1):
    """Solucion exacta por tramos lineales de fuste; sin punta ni peso favorable.
    Devuelve None si la longitud maxima no satisface las acciones.
    """
    if not all(isfinite(v) for v in (nc,nt,min_l,max_l)) or min(nc,nt)<0 or not 0<min_l<=max_l:
        raise ValueError('Acciones o intervalo de longitud invalidos.')
    r = calcular(d,max_l,angulo,estratos,meses,alternancia)
    objetivo=max(nc,nt/r['eta'])
    if objetivo == 0:
        return min_l
    if objetivo > r['fuste_compresion']:
        return None
    acumulado=largo=0.
    for t in r['tramos']:
        cap=t['compresion']
        if cap>0 and acumulado+cap>=objetivo:
            return max(min_l,largo+t['longitud_axial']*(objetivo-acumulado)/cap)
        acumulado+=cap
        largo+=t['longitud_axial']
    return min_l if objetivo==0 else max_l
