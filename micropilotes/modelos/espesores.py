"""Adaptacion de espesores verticales a intervalos del motor axial."""
from math import isfinite, isclose


def intervalos_desde_espesores(filas):
    """Conserva el orden de las filas y devuelve nuevas filas con cotas acumuladas."""
    salida = []
    z = 0.0
    for i, fila in enumerate(filas, 1):
        try:
            h = float(fila['espesor_m'])
        except (KeyError, ValueError, TypeError):
            raise ValueError(f'Fila {i}: introduzca un espesor numerico.') from None
        fin = z + h
        if not isfinite(h) or h <= 0 or not isfinite(fin) or fin <= z:
            raise ValueError(f'Fila {i}: el espesor vertical debe ser positivo y finito.')
        salida.append({**fila, 'espesor_m': h, 'inicio_m': z, 'fin_m': fin})
        z = fin
    if not salida:
        raise ValueError('Introduzca al menos un tramo.')
    return salida


def espesores_desde_cotas(filas):
    """Migra CSV antiguos, rechazando huecos, solapes y cotas invalidas."""
    salida = []
    z = 0.0
    for i, fila in enumerate(filas, 1):
        try:
            a, b = float(fila['inicio_m']), float(fila['fin_m'])
        except (KeyError, ValueError, TypeError):
            raise ValueError(f'Fila {i}: cotas antiguas invalidas.') from None
        if not (isfinite(a) and isfinite(b) and a >= 0 and
                isclose(a, z, rel_tol=0.0, abs_tol=1e-8) and b > a):
            raise ValueError(f'Fila {i}: cotas no contiguas desde la superficie o espesor no positivo.')
        salida.append({**fila, 'espesor_m': b-a})
        z = b
    if not salida:
        raise ValueError('Introduzca al menos un tramo.')
    return salida
