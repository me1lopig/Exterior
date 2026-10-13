"""Barridos parametricos de pendiente y nivel freatico."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from slope_stability_app.calculations.search import search_critical_surfaces
from slope_stability_app.models import AnalysisConfig, SlopeGeometry, SoilProfile, SweepConfig


def run_sensitivity(
    base_geometry: SlopeGeometry,
    profile: SoilProfile,
    config: AnalysisConfig,
    sweep: SweepConfig,
) -> pd.DataFrame:
    sweep.validate(base_geometry.height)
    angles = (
        np.linspace(sweep.angle_min, sweep.angle_max, sweep.angle_steps)
        if sweep.vary_angle
        else np.array([base_geometry.angle_deg])
    )
    waters = (
        np.linspace(sweep.water_min, sweep.water_max, sweep.water_steps)
        if sweep.vary_water
        else np.array([base_geometry.water_elevation])
    )
    records: list[dict[str, float | int]] = []
    for angle in angles:
        for water in waters:
            geometry = replace(base_geometry, angle_deg=float(angle), water_elevation=float(water))
            result = search_critical_surfaces(geometry, profile, config)
            records.append(
                {
                    "Pendiente (deg)": float(angle),
                    "Nivel freatico (m)": float(water),
                    "FS Fellenius": result.fellenius.factor_of_safety,
                    "FS Bishop": result.bishop.factor_of_safety,
                    "Superficies validas": result.valid_surfaces,
                }
            )
    return pd.DataFrame.from_records(records)
