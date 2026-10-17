from __future__ import annotations

import pandas as pd


def cpt_to_equivalent_spt(qc_mpa: pd.Series, qc_over_n_mpa: float) -> pd.Series:
    """Convert qc to equivalent N using a project-selected, justified ratio."""
    if qc_over_n_mpa <= 0:
        raise ValueError("La relacion qc/N debe ser positiva")
    return qc_mpa.astype(float) / qc_over_n_mpa


def normalize_field_data(
    data: pd.DataFrame, qc_over_n_mpa: float | None = None
) -> pd.DataFrame:
    required_depth = "depth_m"
    if required_depth not in data.columns:
        raise ValueError("El CSV debe incluir la columna depth_m")
    normalized = data.copy()
    if "N_spt" not in normalized.columns:
        if "qc_MPa" not in normalized.columns or qc_over_n_mpa is None:
            raise ValueError("Incluya N_spt o qc_MPa junto con una relacion qc/N")
        normalized["N_spt"] = cpt_to_equivalent_spt(
            normalized["qc_MPa"], qc_over_n_mpa
        )
    normalized = normalized[["depth_m", "N_spt"]].apply(pd.to_numeric, errors="coerce")
    normalized = normalized.dropna().sort_values("depth_m")
    if normalized.empty or (normalized["N_spt"] <= 0).any():
        raise ValueError("El perfil no contiene valores SPT validos")
    return normalized


def mean_spt_in_cte_zone(
    data: pd.DataFrame,
    foundation_base_depth_m: float,
    width_eff_m: float,
    apply_terzaghi_correction: bool = False,
    water_table_depth_m: float | None = None,
) -> dict[str, object]:
    """Average N in the CTE 4.3.3 influence interval D-0.5B* to D+2B*."""
    upper = max(0.0, foundation_base_depth_m - 0.5 * width_eff_m)
    lower = foundation_base_depth_m + 2.0 * width_eff_m
    selected = data.loc[data["depth_m"].between(upper, lower)].copy()
    if selected.empty:
        raise ValueError("No hay ensayos dentro de la zona de influencia CTE")
    selected["N_used"] = selected["N_spt"].astype(float)
    if apply_terzaghi_correction:
        if water_table_depth_m is None:
            raise ValueError("Indique la profundidad del nivel freatico")
        mask = (selected["depth_m"] >= water_table_depth_m) & (selected["N_spt"] > 15)
        selected.loc[mask, "N_used"] = 15.0 + 0.5 * (
            selected.loc[mask, "N_spt"] - 15.0
        )
    return {
        "mean_n": float(selected["N_used"].mean()),
        "upper_depth_m": upper,
        "lower_depth_m": lower,
        "count": int(len(selected)),
        "selected": selected,
    }
