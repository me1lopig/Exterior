"""Comprobacion axial por valores limite de rozamiento aportados por el usuario."""
from dataclasses import dataclass
from math import cos, isfinite, pi, radians


@dataclass(frozen=True)
class Estrato:
    inicio: float
    fin: float
    iu: float
    inyeccion: float
    activo: bool = True


def calcular(diametro, longitud, angulo, estratos, duracion_meses, alternancia,
             peso_axial=0.0, punta=0.0, punta_justificada=False):
    """Longitudes en m, rozamientos en kPa, fuerzas en kN; angulo desde vertical."""
    valores = [diametro, longitud, angulo, duracion_meses, peso_axial, punta]
    if not all(isfinite(x) for x in valores):
        raise ValueError('Todas las entradas deben ser finitas.')
    if not 0 < diametro < .300 or longitud <= 0 or not 0 <= angulo < 90 or duracion_meses <= 0 or peso_axial < 0 or punta < 0:
        raise ValueError('Revise diametro, longitud, angulo, duracion y resistencias.')
    c = cos(radians(angulo))
    profundidad = longitud * c
    if not estratos:
        raise ValueError('Introduzca al menos un estrato.')
    fr = 1.45 if duracion_meses <= 6 else 1.65
    eta = 0.60 if alternancia else 0.75
    anterior = 0.0
    tramos = []
    for e in estratos:
        if not all(isfinite(x) for x in (e.inicio, e.fin, e.iu, e.inyeccion)):
            raise ValueError('Los datos de estratos deben ser finitos.')
        if type(e.activo) is not bool or e.inicio < 0 or abs(e.inicio - anterior) > 1e-8 or e.fin <= e.inicio or min(e.iu, e.inyeccion) < 0:
            raise ValueError('Los estratos deben ser contiguos desde la superficie y tener valores no negativos.')
        anterior = e.fin
        a, b = e.inicio, min(e.fin, profundidad)
        if b <= a:
            continue
        limites = [a] + ([5.0] if a < 5.0 < b else []) + [b]
        for z0, z1 in zip(limites, limites[1:]):
            rf = (e.iu if z0 < 5 else e.inyeccion) if e.activo else 0.0
            largo = (z1-z0)/c
            comp = pi * diametro * largo * rf / fr
            tramos.append({'z_inicio': z0, 'z_fin': z1, 'longitud_axial': largo,
                           'r_lim': rf, 'r_calculo': rf/fr, 'compresion': comp,
                           'traccion': eta*comp})
    if anterior + 1e-8 < profundidad:
        raise ValueError('La estratigrafia no cubre la punta del micropilote.')
    fuste = sum(t['compresion'] for t in tramos)
    if punta and not punta_justificada:
        raise ValueError('La punta requiere justificacion expresa.')
    if punta > 0.15*fuste + 1e-9:
        raise ValueError('La resistencia por punta supera el 15 % del fuste de calculo.')
    traccion = sum(t['traccion'] for t in tramos)
    return {'tramos': tramos, 'fr': fr, 'eta': eta, 'profundidad': profundidad,
            'fuste_compresion': fuste, 'punta': punta, 'compresion': fuste+punta,
            'fuste_traccion': traccion, 'peso_reducido': peso_axial/1.2,
            'traccion': traccion+peso_axial/1.2}
