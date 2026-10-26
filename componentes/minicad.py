"""Envoltorio Python del miniCAD geologico basado en SVG."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit.components.v1 as components

from perfil_geologico.calculos.zonas import linea_terreno
from perfil_geologico.calculos.dpsh import curvas_dpsh
from perfil_geologico.modelos.dominio import Contacto


_componente = components.declare_component(
    "minicad_geologico",
    path=str(Path(__file__).with_name("minicad_frontend")),
)


def _rectangulos_sondeos(
    sondeos: pd.DataFrame,
    intervalos: pd.DataFrame,
    unidades: pd.DataFrame,
) -> tuple[list[dict], list[dict]]:
    colores = dict(zip(unidades["unidad_id"].astype(str), unidades["color"].astype(str)))
    rectangulos: list[dict] = []
    observados: list[dict] = []
    ancho = max(float(sondeos["s_m"].max() - sondeos["s_m"].min()) * 0.006, 0.45)
    for sondeo in sondeos.itertuples(index=False):
        grupo = intervalos[intervalos["sondeo_id"] == sondeo.sondeo_id].sort_values("desde_m")
        tramos = list(grupo.itertuples(index=False))
        for indice, tramo in enumerate(tramos):
            techo = float(sondeo.cota_boca_m) - float(tramo.desde_m)
            muro = float(sondeo.cota_boca_m) - float(tramo.hasta_m)
            rectangulos.append(
                {
                    "s0": float(sondeo.s_m) - ancho,
                    "s1": float(sondeo.s_m) + ancho,
                    "z0": muro,
                    "z1": techo,
                    "color": colores.get(str(tramo.unidad_id), "#C7CBD1"),
                    "unidad_id": str(tramo.unidad_id),
                    "sondeo_id": str(sondeo.sondeo_id),
                }
            )
            if indice > 0:
                superior = tramos[indice - 1]
                interfaz_id = f"{sondeo.sondeo_id}:I{indice:03d}"
                observados.append(
                    {
                        "s_m": float(sondeo.s_m),
                        "z_m": techo,
                        "referencia": str(sondeo.sondeo_id),
                        "interfaz_id": interfaz_id,
                        "profundidad_m": float(tramo.desde_m),
                        "unidad_superior": str(superior.unidad_id),
                        "unidad_inferior": str(tramo.unidad_id),
                    }
                )
    return rectangulos, observados


def modelo_minicad(
    sondeos: pd.DataFrame,
    intervalos: pd.DataFrame,
    unidades: pd.DataFrame,
    contactos: list[Contacto],
    zonas: list[dict],
    dpsh: pd.DataFrame,
    lecturas_dpsh: pd.DataFrame,
    escala_dpsh: float = 0.12,
    contactos_referencia: list[Contacto] | None = None,
    exageracion_vertical: float | None = None,
) -> dict:
    """Convierte el proyecto al modelo JSON del lienzo."""
    s_terreno, z_terreno = linea_terreno(sondeos)
    rectangulos, observados = _rectangulos_sondeos(sondeos, intervalos, unidades)
    base = float((sondeos["cota_boca_m"] - sondeos["profundidad_m"]).min()) - 2.0
    zmax = float(max(sondeos["cota_boca_m"].max(), dpsh["cota_inicio_m"].max() if len(dpsh) else -np.inf)) + 1.5
    xmin, xmax = float(s_terreno.min()), float(s_terreno.max())
    margen_x = max((xmax - xmin) * 0.04, 2.0)
    return {
        "bounds": {"xmin": xmin - margen_x, "xmax": xmax + margen_x, "ymin": base, "ymax": zmax},
        "exageracion_vertical": exageracion_vertical,
        "terreno": [{"s_m": float(s), "z_m": float(z)} for s, z in zip(s_terreno, z_terreno)],
        "sondeos": rectangulos,
        "observados": observados,
        "contactos": [asdict(contacto) for contacto in contactos],
        "contactos_referencia": [asdict(contacto) for contacto in contactos_referencia or []],
        "zonas": zonas,
        "dpsh": curvas_dpsh(dpsh, lecturas_dpsh, escala_dpsh),
        "unidades": [
            {"unidad_id": str(fila.unidad_id), "nombre": str(fila.nombre), "color": str(fila.color)}
            for fila in unidades.itertuples(index=False)
        ],
    }


def minicad_geologico(modelo: dict, key: str = "minicad-geologico") -> dict | None:
    """Monta el componente y devuelve contactos/zonas cuando el usuario guarda."""
    return _componente(model=modelo, default=None, key=key)
