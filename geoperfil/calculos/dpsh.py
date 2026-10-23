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
