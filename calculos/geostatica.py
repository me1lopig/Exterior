from __future__ import annotations

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray


def integrar_peso_especifico(
    profundidades_m: ArrayLike,
    estratos: pd.DataFrame,
    nivel_freatico_m: float,
    gamma_w_kN_m3: float = 9.81,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Calcula tensiones geostáticas total, presión de agua y efectiva.

    Las profundidades y el nivel freático se miden desde la superficie.
    Sobre el nivel freático se usa gamma_ap; por debajo, gamma_sat.
    """
    d = np.asarray(profundidades_m, dtype=float)
    if np.any(d < 0) or nivel_freatico_m < 0 or gamma_w_kN_m3 <= 0:
        raise ValueError("Profundidades y nivel freático deben ser no negativos.")
    total = np.zeros_like(d)
    for _, capa in estratos.iterrows():
        sup = float(capa["z_sup_m"])
        inf = float(capa["z_inf_m"])
        gamma_ap = float(capa["gamma_ap_kN_m3"])
        gamma_sat = float(capa["gamma_sat_kN_m3"])

        fin = np.minimum(d, inf)
        tramo_seco = np.maximum(0.0, np.minimum(fin, nivel_freatico_m) - sup)
        inicio_sat = max(sup, nivel_freatico_m)
        tramo_sat = np.maximum(0.0, fin - inicio_sat)
        total += gamma_ap * tramo_seco + gamma_sat * tramo_sat

    presion_agua = gamma_w_kN_m3 * np.maximum(d - nivel_freatico_m, 0.0)
    efectiva = total - presion_agua
    return total, presion_agua, efectiva

