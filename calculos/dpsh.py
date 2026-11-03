"""Operaciones auxiliares para series de penetracion dinamica DPSH."""

from __future__ import annotations

import numpy as np
import pandas as pd


def separar_tramos_contiguos(tabla: pd.DataFrame) -> list[pd.DataFrame]:
    """Separa una serie DPSH en tramos sin convertirla en arrays NumPy.

    Se considera discontinuidad una separacion mayor que 1,5 veces el paso
    mediano positivo entre lecturas consecutivas.
    """
    ordenada = tabla.sort_values("profundidad_m").dropna(
        subset=["profundidad_m", "n20"]
    )
    if len(ordenada) < 2:
        return [ordenada.copy()] if len(ordenada) else []

    diferencias = np.diff(ordenada["profundidad_m"].to_numpy(dtype=float))
    positivas = diferencias[diferencias > 0]
    paso = float(np.median(positivas)) if len(positivas) else 0.0
    cortes = (
        (np.where(diferencias > 1.5 * paso)[0] + 1).tolist()
        if paso > 0
        else []
    )
    limites = [0, *cortes, len(ordenada)]
    return [
        ordenada.iloc[inicio:fin].copy()
        for inicio, fin in zip(limites[:-1], limites[1:])
        if fin > inicio
    ]


def curvas_dpsh(dpsh: pd.DataFrame, lecturas: pd.DataFrame, escala: float, sentidos: dict[str,int] | None = None) -> list[dict]:
    """Devuelve las curvas con tramos independientes cuando hay lagunas."""
    curvas = []
    for ensayo in dpsh.itertuples(index=False):
        grupo = lecturas[lecturas["ensayo_id"] == ensayo.ensayo_id]
        sentido = (sentidos or {}).get(str(ensayo.ensayo_id),1)
        tramos = []
        for tramo in separar_tramos_contiguos(grupo):
            tramos.append([
                {"s_m": float(ensayo.s_m) + sentido * float(fila.n20) * escala,
                 "z_m": float(ensayo.cota_inicio_m) - float(fila.profundidad_m),
                 "n20": float(fila.n20)}
                for fila in tramo.itertuples(index=False)
            ])
        curvas.append({
            "ensayo_id": str(ensayo.ensayo_id),
            "s_m": float(ensayo.s_m),
            "cota_inicio_m": float(ensayo.cota_inicio_m),
            "profundidad_m": float(ensayo.profundidad_m),
            "sentido": sentido, "escala_grafica": escala,
            "tramos": tramos,
        })
    return curvas



def distribucion_curvas(
    dpsh: pd.DataFrame,
    lecturas: pd.DataFrame | None,
    escala_solicitada: float,
    sondeos: pd.DataFrame | None = None,
    rango_pk: tuple[float, float] | None = None,
) -> tuple[float, dict[str, int]]:
    """Escala comun segura para N20 y direccion por ensayo en el dibujo.

    Las cotas y el PK reales son invariantes. El N20 se representa como una
    abscisa auxiliar junto al eje; se limita al espacio comprendido entre los
    puntos medios de los reconocimientos mas proximos y los extremos del perfil.
    En el borde derecho el grafico crece a la izquierda, sin falsear N20.
    """
    if dpsh.empty:
        return float(escala_solicitada), {}
    if not np.isfinite(escala_solicitada) or escala_solicitada <= 0:
        raise ValueError('Escala grafica de penetracion no valida.')
    posiciones = [float(x) for x in dpsh['s_m']]
    if sondeos is not None and not sondeos.empty:
        posiciones.extend(float(x) for x in sondeos['s_m'])
    posiciones = sorted(set(posiciones))
    if rango_pk is None:
        return float(escala_solicitada), {str(r.ensayo_id): 1 for r in dpsh.itertuples(index=False)}
    xmin,xmax = map(float,rango_pk)
    if not np.isfinite(xmin+xmax) or xmax <= xmin:
        raise ValueError('Limites PK de penetracion no validos.')
    posiciones = sorted(set([xmin,xmax,*posiciones]))
    maximos = lecturas.groupby('ensayo_id')['n20'].max().to_dict() if lecturas is not None and not lecturas.empty else {}
    sentidos: dict[str,int] = {}
    candidatos = [float(escala_solicitada)]
    for r in dpsh.itertuples(index=False):
        s = float(r.s_m)
        if not (xmin - 1e-8 <= s <= xmax + 1e-8):
            continue  # Ensayo fuera del tramo visible.
        menores = [x for x in posiciones if x < s-1e-8]
        mayores = [x for x in posiciones if x > s+1e-8]
        izq = max(xmin, (menores[-1]+s)/2) if menores else xmin
        der = min(xmax, (mayores[0]+s)/2) if mayores else xmax
        ancho_izq = max(0.0,s-izq)
        ancho_der = max(0.0,der-s)
        # Preferir la derecha salvo en el ultimo reconocimiento o si apenas hay sitio.
        sentido = 1 if ancho_der >= max(0.15, ancho_izq * .20) else -1
        espacio = ancho_der if sentido == 1 else ancho_izq
        if espacio <= 1e-9 and ancho_izq > 0:
            sentido,espacio=-1,ancho_izq
        sentidos[str(r.ensayo_id)] = sentido
        max_n = max(0.0,float(maximos.get(r.ensayo_id,0) or 0))
        if max_n > 0:
            candidatos.append(max(0.0, .90 * espacio / max_n))
    return min(candidatos), sentidos
