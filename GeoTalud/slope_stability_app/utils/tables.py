"""Conversion de resultados a tablas de interfaz y exportacion."""

from __future__ import annotations

import pandas as pd

from slope_stability_app.calculations.search import CriticalResult


def slices_dataframe(critical: CriticalResult) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Dovela": item.index,
                "x medio (m)": item.x_mid,
                "z base (m)": item.base_elevation,
                "Ancho (m)": item.width,
                "alpha (deg)": item.base_angle_deg,
                "Peso (kN/m)": item.weight,
                "u (kPa)": item.pore_pressure,
                "Suelo en base": item.soil_name,
                "c' (kPa)": item.cohesion,
                "phi' (deg)": item.friction_deg,
            }
            for item in critical.evaluation.slices
        ]
    )
