"""Datos comunes de la extension del perfil y de su guitarra (sin extrapolacion geologica)."""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

from perfil_geologico.calculos.proyeccion import longitud_eje


def limites_perfil(proyecto, eje: pd.DataFrame, sondeos: pd.DataFrame, dpsh: pd.DataFrame) -> tuple[float, float]:
    """Devuelve PK inicial/final reales para el dibujo, restringidos al eje."""
    longitud = longitud_eje(eje)
    modo = getattr(proyecto, 'extension_modo', 'eje_completo')
    if modo == 'eje_completo':
        inicio, fin = 0.0, longitud
    elif modo == 'reconocimientos':
        puntos = []
        for tabla in (sondeos, dpsh):
            if not tabla.empty and 's_m' in tabla:
                puntos.extend(float(p) for p in tabla['s_m'] if pd.notna(p))
        margen = max(0.0, float(getattr(proyecto, 'margen_pk_m', 10.0)))
        inicio = max(0.0, min(puntos) - margen) if puntos else 0.0
        fin = min(longitud, max(puntos) + margen) if puntos else longitud
    elif modo == 'manual':
        inicio = float(getattr(proyecto, 'pk_inicio_m', 0.0))
        fin = float(getattr(proyecto, 'pk_fin_m', 100.0))
        if not all(map(math.isfinite, (inicio, fin))) or not 0 <= inicio < fin <= longitud + 1e-6:
            raise ValueError('El intervalo manual debe estar dentro del eje y tener PK final mayor que PK inicial.')
    else:
        raise ValueError('Modo de extension de perfil no reconocido.')
    if fin - inicio < 1e-6:
        raise ValueError('La extension del perfil tiene longitud nula.')
    return inicio, fin


def preparar_guitarra(sondeos: pd.DataFrame, dpsh: pd.DataFrame, limites: tuple[float, float], paso_m: float = 50.0, terreno_puntos: pd.DataFrame | None = None):
    """PK de cuadricula, cota interpolada *solo* dentro del rango observado y reconocimientos reales."""
    inicio, fin = (float(limites[0]), float(limites[1]))
    paso = float(paso_m)
    if not math.isfinite(paso) or paso <= 0 or not 0 <= inicio < fin:
        raise ValueError('Paso o limites de guitarra incorrectos.')
    primera = math.ceil((inicio - 1e-9)/paso)*paso
    marcas = [round(float(x), 6) for x in np.arange(primera, fin + 1e-7, paso)]
    if not marcas or abs(marcas[0] - inicio) > 1e-6:
        marcas.insert(0, inicio)
    if abs(marcas[-1] - fin) > 1e-6:
        # Evita etiquetas superpuestas entre un PK de cuadricula y el final exacto.
        if fin - marcas[-1] < max(0.25*paso, 1.0):
            marcas[-1] = fin
        else:
            marcas.append(fin)
    fuente = terreno_puntos if terreno_puntos is not None and not terreno_puntos.empty else sondeos
    terreno = fuente.groupby('s_m', as_index=False)['cota_boca_m'].mean().sort_values('s_m') if not fuente.empty else pd.DataFrame()
    muestras = []
    if len(terreno):
        sx = terreno['s_m'].to_numpy(float)
        sy = terreno['cota_boca_m'].to_numpy(float)
        for pk in marcas:
            z = float(np.interp(pk, sx, sy)) if sx[0] - 1e-7 <= pk <= sx[-1] + 1e-7 else None
            muestras.append({'pk_m': pk, 'terreno_m': z})
    else:
        muestras = [{'pk_m': pk, 'terreno_m': None} for pk in marcas]
    reconocimientos = []
    for tabla, columna, tipo in ((sondeos, 'sondeo_id', 'Sondeo'), (dpsh, 'ensayo_id', 'DPSH')):
        if tabla.empty:
            continue
        for fila in tabla.itertuples(index=False):
            pk = float(getattr(fila, 's_m'))
            if inicio - 1e-7 <= pk <= fin + 1e-7:
                reconocimientos.append({'pk_m': pk, 'nombre': str(getattr(fila, columna)), 'tipo': tipo})
    reconocimientos.sort(key=lambda r:(r['pk_m'], r['tipo'], r['nombre']))
    return {'limites': (inicio, fin), 'marcas': muestras, 'reconocimientos': reconocimientos}
