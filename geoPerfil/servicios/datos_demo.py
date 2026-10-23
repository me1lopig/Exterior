"""Caso sintetico reproducible incluido con la aplicacion."""

from __future__ import annotations

import pandas as pd


def crear_datos_demo() -> dict[str, pd.DataFrame]:
    """Devuelve un perfil coherente con cuatro sondeos y dos DPSH."""
    sondeos = pd.DataFrame(
        [
            ["S-01", 500000.0, 4400002.0, 112.4, 18.0, "Sondeo mecanico"],
            ["S-02", 500055.0, 4399996.0, 110.8, 20.0, "Sondeo mecanico"],
            ["S-03", 500118.0, 4400005.0, 109.7, 17.0, "Sondeo mecanico"],
            ["S-04", 500180.0, 4399998.0, 111.1, 21.0, "Sondeo mecanico"],
        ],
        columns=["sondeo_id", "x_m", "y_m", "cota_boca_m", "profundidad_m", "descripcion"],
    )
    intervalos = pd.DataFrame(
        [
            ["S-01", 0.0, 1.4, "R", "Relleno heterogeneo"],
            ["S-01", 1.4, 6.2, "AL", "Arcilla limosa"],
            ["S-01", 6.2, 11.5, "GA", "Grava arenosa"],
            ["S-01", 11.5, 18.0, "SR", "Sustrato alterado"],
            ["S-02", 0.0, 1.0, "R", "Relleno"],
            ["S-02", 1.0, 7.4, "AL", "Arcilla limosa"],
            ["S-02", 7.4, 13.0, "GA", "Grava arenosa"],
            ["S-02", 13.0, 20.0, "SR", "Sustrato alterado"],
            ["S-03", 0.0, 0.8, "R", "Tierra vegetal y relleno"],
            ["S-03", 0.8, 5.5, "AL", "Arcilla limosa"],
            ["S-03", 5.5, 10.2, "GA", "Grava arenosa"],
            ["S-03", 10.2, 17.0, "SR", "Sustrato alterado"],
            ["S-04", 0.0, 1.8, "R", "Relleno"],
            ["S-04", 1.8, 6.8, "AL", "Arcilla limosa"],
            ["S-04", 6.8, 12.3, "GA", "Grava arenosa"],
            ["S-04", 12.3, 21.0, "SR", "Sustrato alterado"],
        ],
        columns=["sondeo_id", "desde_m", "hasta_m", "unidad_id", "descripcion"],
    )
    unidades = pd.DataFrame(
        [
            ["R", "Rellenos", 1, "#C8A977", "Sin interpretacion geotecnica"],
            ["AL", "Arcilla limosa", 2, "#89A96B", "Unidad geologica-geotecnica"],
            ["GA", "Grava arenosa", 3, "#E7C96B", "Unidad geologica-geotecnica"],
            ["SR", "Sustrato alterado", 4, "#8B9098", "Base del perfil"],
        ],
        columns=["unidad_id", "nombre", "orden", "color", "observaciones"],
    )
    dpsh = pd.DataFrame(
        [
            ["DPSH-01", 500030.0, 4400001.0, 111.5, 10.0, "2026-01-15"],
            ["DPSH-02", 500145.0, 4399997.0, 110.0, 11.0, "2026-01-16"],
        ],
        columns=["ensayo_id", "x_m", "y_m", "cota_inicio_m", "profundidad_m", "fecha"],
    )
    lecturas = []
    valores = {
        "DPSH-01": [3, 4, 5, 7, 8, 11, 15, 18, 23, 29, 34, 39, 47, 55, 63, 72, 84, 96, 100, 100],
        "DPSH-02": [2, 3, 5, 6, 7, 9, 12, 14, 18, 22, 27, 31, 38, 44, 52, 61, 70, 78, 87, 96, 100, 100],
    }
    for ensayo_id, serie in valores.items():
        for indice, n20 in enumerate(serie, start=1):
            estado = "rechazo" if indice == len(serie) else "valido"
            lecturas.append([ensayo_id, indice * 0.5, n20, estado, ""])
    lecturas_dpsh = pd.DataFrame(
        lecturas,
        columns=["ensayo_id", "profundidad_m", "n20", "estado", "observaciones"],
    )
    eje = pd.DataFrame(
        [[1, 499985.0, 4400000.0], [2, 500195.0, 4400000.0]],
        columns=["orden", "x_m", "y_m"],
    )
    return {
        "Sondeos": sondeos,
        "Intervalos": intervalos,
        "Unidades": unidades,
        "Ensayos_DPSH": dpsh,
        "Lecturas_DPSH": lecturas_dpsh,
        "Eje": eje,
    }
