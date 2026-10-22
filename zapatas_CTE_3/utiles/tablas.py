"""Conversión de resultados a tablas para interfaz y exportación."""

from __future__ import annotations

import pandas as pd

from modelos.datos import ResultadoAncho


def tabla_resultados(resultados: list[ResultadoAncho], geometria: str) -> pd.DataFrame:
    cuadrada = geometria == "Cuadrada"
    filas = []
    for resultado in resultados:
        filas.append(
            {
                "B* (m)": resultado.ancho_m,
                "Hundimiento (MPa)": (
                    resultado.hundimiento_cuadrada_mpa
                    if cuadrada
                    else resultado.hundimiento_corrida_mpa
                ),
                "Asientos (MPa)": (
                    resultado.asiento_cuadrada_mpa
                    if cuadrada
                    else resultado.asiento_corrida_mpa
                ),
                "Servicio (MPa)": (
                    resultado.servicio_cuadrada_mpa
                    if cuadrada
                    else resultado.servicio_corrida_mpa
                ),
                "Limitación": (
                    resultado.limitacion_cuadrada
                    if cuadrada
                    else resultado.limitacion_corrida
                ),
                "Espesor >= 2B": "Sí" if resultado.espesor_suficiente else "No",
                "Ksp30 (MN/m³)": (
                    resultado.ksp30_cuadrada_mn_m3
                    if cuadrada
                    else resultado.ksp30_corrida_mn_m3
                ),
            }
        )
    return pd.DataFrame(filas)
