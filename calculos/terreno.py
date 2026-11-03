"""Cotas observadas de los reconocimientos del perfil (sin extrapolacion)."""
from __future__ import annotations
import pandas as pd


def terreno_de_campana(datos: dict, sondeos: pd.DataFrame) -> pd.DataFrame:
    """Pares PK/cota de PERFIL1, incluido STA como punto topografico.

    STA determina la linea del terreno pero nunca crea sondeo ni penetracion.
    Los proyectos JSON anteriores sin Estaciones utilizan las bocas de sondeo.
    """
    estaciones=datos.get('Estaciones')
    if estaciones is not None and not estaciones.empty:
        t=estaciones[['pk_m','cota_m']].copy()
        if not t.empty:
            t=t.rename(columns={'pk_m':'s_m','cota_m':'cota_boca_m'})
            t['s_m']=pd.to_numeric(t['s_m'])
            t['cota_boca_m']=pd.to_numeric(t['cota_boca_m'])
            if t.groupby('s_m')['cota_boca_m'].agg(lambda x: x.max()-x.min()).gt(1e-5).any():
                raise ValueError('Puntos de terreno con cotas distintas en el mismo PK. Corrija PERFIL1.')
            return t.groupby('s_m',as_index=False)['cota_boca_m'].mean().sort_values('s_m')
    if sondeos.empty:
        return pd.DataFrame(columns=['s_m','cota_boca_m'])
    return sondeos.groupby('s_m',as_index=False)['cota_boca_m'].mean().sort_values('s_m')


def incidencias_cota_inicio(
    terreno: pd.DataFrame, sondeos: pd.DataFrame, penetraciones: pd.DataFrame,
    tolerancia_m: float = 0.001,
) -> list[str]:
    """Detecta si una boca o inicio no coincide con la topografia de PERFIL1.

    Se compara a PK exacto/interpolado; nunca se cambian las cotas observadas.
    El resultado se bloquea si hay discordancias de origen, que requieren
    corregir los libros y volver a importar (no desplazar el dibujo).
    """
    import numpy as np

    if terreno is None or terreno.empty:
        return ['No hay puntos de terreno para comprobar las cotas de inicio.']
    t = terreno.sort_values('s_m')
    s = t['s_m'].to_numpy(float)
    z = t['cota_boca_m'].to_numpy(float)
    avisos = []
    for tabla, nombre, cota in (
        (sondeos, 'sondeo_id', 'cota_boca_m'),
        (penetraciones, 'ensayo_id', 'cota_inicio_m'),
    ):
        if tabla is None or tabla.empty:
            continue
        for r in tabla.itertuples(index=False):
            pk = float(r.s_m)
            cota_inicio = float(getattr(r, cota))
            if not np.isfinite(pk) or not np.isfinite(cota_inicio):
                avisos.append(f'{getattr(r, nombre)}: PK o cota de inicio no finitos.')
                continue
            if not (s[0] - 1e-6 <= pk <= s[-1] + 1e-6):
                avisos.append(f'{getattr(r, nombre)}: PK {pk:.3f} m fuera de la topografia de PERFIL1.')
                continue
            cota_terreno = float(np.interp(pk, s, z))
            if abs(cota_inicio - cota_terreno) > tolerancia_m:
                avisos.append(
                    f'{getattr(r, nombre)}: cota de inicio {cota_inicio:.3f} m distinta del terreno '
                    f'{cota_terreno:.3f} m en PK {pk:.3f} m; revise PERFIL1.'
                )
    return avisos
