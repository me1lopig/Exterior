"""Validacion temprana de entradas geologico-geotecnicas."""

from __future__ import annotations

import numpy as np
import pandas as pd


def validar_datos(
    sondeos: pd.DataFrame,
    intervalos: pd.DataFrame,
    unidades: pd.DataFrame,
    dpsh: pd.DataFrame,
    lecturas_dpsh: pd.DataFrame,
) -> tuple[list[str], list[str]]:
    """Devuelve listas de errores bloqueantes y advertencias."""
    errores: list[str] = []
    avisos: list[str] = []
    requeridas = {
        "Sondeos": (sondeos, {"sondeo_id", "x_m", "y_m", "cota_boca_m", "profundidad_m"}),
        "Intervalos": (intervalos, {"sondeo_id", "desde_m", "hasta_m", "unidad_id"}),
        "Unidades": (unidades, {"unidad_id", "nombre", "orden", "color"}),
        "Ensayos_DPSH": (dpsh, {"ensayo_id", "x_m", "y_m", "cota_inicio_m", "profundidad_m"}),
        "Lecturas_DPSH": (lecturas_dpsh, {"ensayo_id", "profundidad_m", "n20"}),
    }
    for nombre, (tabla, columnas) in requeridas.items():
        faltantes = columnas.difference(tabla.columns)
        if faltantes:
            errores.append(f"{nombre}: faltan columnas {', '.join(sorted(faltantes))}.")
    if errores:
        return errores, avisos

    if sondeos["sondeo_id"].duplicated().any():
        errores.append("Existen identificadores de sondeo duplicados.")
    if unidades["unidad_id"].duplicated().any() or unidades["orden"].duplicated().any():
        errores.append("Las unidades deben tener identificadores y ordenes unicos.")
    if (sondeos["profundidad_m"] <= 0).any():
        errores.append("Las profundidades de los sondeos deben ser positivas.")
    if (intervalos["hasta_m"] <= intervalos["desde_m"]).any():
        errores.append("Todos los intervalos deben cumplir hasta_m > desde_m.")
    if (lecturas_dpsh["profundidad_m"] < 0).any() or (lecturas_dpsh["n20"] < 0).any():
        errores.append("Las profundidades y N20 de DPSH no pueden ser negativos.")

    ids_sondeo = set(sondeos["sondeo_id"].astype(str))
    ids_unidad = set(unidades["unidad_id"].astype(str))
    ids_dpsh = set(dpsh["ensayo_id"].astype(str))
    if not set(intervalos["sondeo_id"].astype(str)).issubset(ids_sondeo):
        errores.append("Hay intervalos asociados a sondeos inexistentes.")
    if not set(intervalos["unidad_id"].astype(str)).issubset(ids_unidad):
        errores.append("Hay intervalos con unidades no definidas.")
    if not set(lecturas_dpsh["ensayo_id"].astype(str)).issubset(ids_dpsh):
        errores.append("Hay lecturas asociadas a DPSH inexistentes.")

    for sondeo_id, grupo in intervalos.groupby("sondeo_id"):
        ordenado = grupo.sort_values("desde_m")
        desde = ordenado["desde_m"].to_numpy(dtype=float)
        hasta = ordenado["hasta_m"].to_numpy(dtype=float)
        if len(grupo) and not np.isclose(desde[0], 0.0):
            avisos.append(f"{sondeo_id}: el primer intervalo no comienza en 0 m.")
        if len(grupo) > 1 and not np.allclose(desde[1:], hasta[:-1]):
            errores.append(f"{sondeo_id}: existen huecos o solapes entre intervalos.")
        profundidad = float(sondeos.loc[sondeos["sondeo_id"] == sondeo_id, "profundidad_m"].iloc[0])
        if len(grupo) and not np.isclose(hasta[-1], profundidad):
            avisos.append(f"{sondeo_id}: los intervalos no terminan en la profundidad declarada.")

    if lecturas_dpsh.duplicated(["ensayo_id", "profundidad_m"]).any():
        errores.append("Existen lecturas DPSH duplicadas a la misma profundidad.")
    for ensayo_id, grupo in lecturas_dpsh.groupby("ensayo_id"):
        if not grupo["profundidad_m"].is_monotonic_increasing:
            avisos.append(f"{ensayo_id}: las lecturas se ordenaran por profundidad.")
    return errores, avisos
