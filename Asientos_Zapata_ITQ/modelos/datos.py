from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Cimentacion:
    """Geometría y carga de una zapata rectangular flexible."""

    b_m: float
    l_m: float
    q_neta_kpa: float
    df_m: float

    def validar(self) -> list[str]:
        errores: list[str] = []
        if not np.isfinite(self.b_m) or self.b_m <= 0:
            errores.append("B debe ser mayor que cero.")
        if not np.isfinite(self.l_m) or self.l_m <= 0:
            errores.append("L debe ser mayor que cero.")
        if self.b_m > self.l_m:
            errores.append("Debe cumplirse B <= L.")
        if not np.isfinite(self.q_neta_kpa) or self.q_neta_kpa <= 0:
            errores.append("La presión neta debe ser mayor que cero.")
        if not np.isfinite(self.df_m) or self.df_m < 0:
            errores.append("La profundidad de apoyo no puede ser negativa.")
        return errores


COLUMNAS_ESTRATOS = [
    "Estrato",
    "z_sup_m",
    "z_inf_m",
    "gamma_ap_kN_m3",
    "gamma_sat_kN_m3",
    "E_MPa",
    "nu",
]


def estratos_ejemplo() -> pd.DataFrame:
    """Caso inicial editable; sus valores no constituyen recomendaciones de proyecto."""
    return pd.DataFrame(
        [
            ["Relleno", 0.0, 2.0, 18.0, 20.0, 15.0, 0.30],
            ["Arena", 2.0, 8.0, 19.0, 21.0, 35.0, 0.28],
            ["Sustrato", 8.0, 25.0, 20.0, 22.0, 80.0, 0.25],
        ],
        columns=COLUMNAS_ESTRATOS,
    )


def validar_estratos(
    tabla: pd.DataFrame,
    profundidad_requerida_m: float,
) -> tuple[pd.DataFrame, list[str]]:
    """Normaliza y valida una tabla de capas horizontales contiguas."""
    errores: list[str] = []
    faltantes = [c for c in COLUMNAS_ESTRATOS if c not in tabla.columns]
    if faltantes:
        return tabla.copy(), [f"Faltan columnas: {', '.join(faltantes)}."]

    capas = tabla[COLUMNAS_ESTRATOS].copy().reset_index(drop=True)
    if capas.empty:
        return capas, ["Debe definirse al menos un estrato."]

    numericas = [c for c in COLUMNAS_ESTRATOS if c != "Estrato"]
    for columna in numericas:
        capas[columna] = pd.to_numeric(capas[columna], errors="coerce")
    requeridas = [
        "z_sup_m", "z_inf_m", "gamma_ap_kN_m3", "gamma_sat_kN_m3", "E_MPa", "nu"
    ]
    if capas[requeridas].isna().any().any():
        errores.append("La tabla contiene celdas vacías o valores no numéricos.")
        return capas, errores
    if not np.isfinite(capas[requeridas].to_numpy(dtype=float)).all():
        errores.append("La tabla contiene valores infinitos o no finitos.")
        return capas, errores

    capas = capas.sort_values("z_sup_m", kind="stable").reset_index(drop=True)
    if abs(float(capas.loc[0, "z_sup_m"])) > 1e-8:
        errores.append("El primer estrato debe comenzar en z = 0 m.")
    espesores = capas["z_inf_m"] - capas["z_sup_m"]
    if (espesores <= 0).any():
        errores.append("Todos los estratos deben tener espesor positivo.")
    if len(capas) > 1:
        saltos = (
            capas["z_sup_m"].iloc[1:].to_numpy(dtype=float)
            - capas["z_inf_m"].iloc[:-1].to_numpy(dtype=float)
        )
        if not np.allclose(saltos, 0.0, atol=1e-6):
            errores.append("Los estratos deben ser contiguos, sin huecos ni solapes.")
    if float(capas.iloc[-1]["z_inf_m"]) + 1e-8 < profundidad_requerida_m:
        errores.append(
            "El perfil estratigráfico no alcanza la profundidad final del análisis."
        )
    if (capas["gamma_ap_kN_m3"] <= 0).any() or (capas["gamma_sat_kN_m3"] <= 0).any():
        errores.append("Los pesos específicos deben ser positivos.")
    if (capas["gamma_sat_kN_m3"] < capas["gamma_ap_kN_m3"]).any():
        errores.append("Debe cumplirse gamma_sat >= gamma_ap en cada estrato.")

    if (capas["E_MPa"] <= 0).any():
        errores.append("E debe ser positivo en todos los estratos.")
    if ((capas["nu"] <= 0.10) | (capas["nu"] >= 0.499)).any():
        errores.append("Se exige 0.10 < nu < 0.499 en todos los estratos.")
    return capas, errores

