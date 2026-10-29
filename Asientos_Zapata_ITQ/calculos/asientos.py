from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from calculos.boussinesq import incremento_tension_rectangular
from calculos.geostatica import integrar_peso_especifico
from modelos.datos import Cimentacion, ModoModulo


@dataclass(frozen=True)
class ResultadoCalculo:
    perfiles: pd.DataFrame
    resumen_puntos: pd.DataFrame
    resumen_estratos: pd.DataFrame
    malla_corta: dict[str, NDArray[np.float64]]
    malla_larga: dict[str, NDArray[np.float64]]
    error_discretizacion_pct: float
    contribucion_tramo_final_pct: float


PUNTOS_CONTROL = {
    "Centro": (0.0, 0.0),
    "Borde B": (0.5, 0.0),
    "Borde L": (0.0, 0.5),
    "Esquina": (0.5, 0.5),
    "Exterior B": (1.0, 0.0),
    "Exterior L": (0.0, 1.0),
}


def modulo_confinado_kpa(estratos: pd.DataFrame, modo: ModoModulo) -> NDArray[np.float64]:
    """Devuelve M en kPa para cada fila de la tabla de estratos."""
    if modo == "M":
        return estratos["M_MPa"].to_numpy(dtype=float) * 1000.0
    e_kpa = estratos["E_MPa"].to_numpy(dtype=float) * 1000.0
    nu = estratos["nu"].to_numpy(dtype=float)
    return e_kpa * (1.0 - nu) / ((1.0 + nu) * (1.0 - 2.0 * nu))


def _indices_estratos(profundidad_terreno_m: NDArray[np.float64], estratos: pd.DataFrame) -> NDArray[np.int64]:
    limites = estratos["z_inf_m"].to_numpy(dtype=float)
    indices = np.searchsorted(limites, profundidad_terreno_m, side="right")
    return np.clip(indices, 0, len(estratos) - 1)


def _malla_profundidad(z_max_m: float, n_puntos: int, df_m: float, estratos: pd.DataFrame) -> NDArray[np.float64]:
    base = np.linspace(0.0, z_max_m, n_puntos)
    interfaces = estratos["z_inf_m"].to_numpy(dtype=float) - df_m
    interfaces = interfaces[(interfaces > 0.0) & (interfaces < z_max_m)]
    return np.unique(np.concatenate([base, interfaces]))


def _perfil_punto(
    nombre: str,
    x_m: float,
    y_m: float,
    z: NDArray[np.float64],
    cimentacion: Cimentacion,
    estratos: pd.DataFrame,
    m_capas_kpa: NDArray[np.float64],
    nivel_freatico_m: float,
) -> pd.DataFrame:
    profundidad_terreno = cimentacion.df_m + z
    indices = _indices_estratos(profundidad_terreno, estratos)
    m_local = m_capas_kpa[indices]
    delta_sigma = incremento_tension_rectangular(
        np.full_like(z, x_m), np.full_like(z, y_m), z,
        cimentacion.b_m, cimentacion.l_m, cimentacion.q_neta_kpa,
    )
    deformacion = delta_sigma / m_local
    z_medio = 0.5 * (z[:-1] + z[1:])
    indices_medio = _indices_estratos(cimentacion.df_m + z_medio, estratos)
    sigma_medio = incremento_tension_rectangular(
        np.full_like(z_medio, x_m), np.full_like(z_medio, y_m), z_medio,
        cimentacion.b_m, cimentacion.l_m, cimentacion.q_neta_kpa,
    )
    deformacion_media = sigma_medio / m_capas_kpa[indices_medio]
    incrementos_asiento = deformacion_media * np.diff(z)
    acumulado = np.concatenate(([0.0], np.cumsum(incrementos_asiento)))
    asiento_total = float(acumulado[-1])
    desplazamiento = asiento_total - acumulado
    sigma_total, u, sigma_efectiva = integrar_peso_especifico(
        profundidad_terreno, estratos, nivel_freatico_m
    )
    nombres = estratos.iloc[indices]["Estrato"].astype(str).to_numpy()
    return pd.DataFrame(
        {
            "Punto": nombre,
            "x_m": x_m,
            "y_m": y_m,
            "z_bajo_base_m": z,
            "prof_terreno_m": profundidad_terreno,
            "Estrato": nombres,
            "M_MPa": m_local / 1000.0,
            "sigma_v0_total_kPa": sigma_total,
            "u_kPa": u,
            "sigma_v0_ef_kPa": sigma_efectiva,
            "delta_sigma_z_kPa": delta_sigma,
            "sigma_ef_final_kPa": sigma_efectiva + delta_sigma,
            "epsilon_z": deformacion,
            "aporte_acum_mm": acumulado * 1000.0,
            "desplazamiento_mm": desplazamiento * 1000.0,
        }
    )


def _resumen_por_estrato(perfil_centro: pd.DataFrame, estratos: pd.DataFrame) -> pd.DataFrame:
    filas: list[dict[str, float | str]] = []
    for _, capa in estratos.iterrows():
        sup_rel = max(float(capa["z_sup_m"]) - float(perfil_centro["prof_terreno_m"].iloc[0]), 0.0)
        inf_rel = float(capa["z_inf_m"]) - float(perfil_centro["prof_terreno_m"].iloc[0])
        z_final = float(perfil_centro["z_bajo_base_m"].iloc[-1])
        sup_util = max(sup_rel, 0.0)
        inf_util = min(inf_rel, z_final)
        mascara = (perfil_centro["z_bajo_base_m"] >= sup_util) & (perfil_centro["z_bajo_base_m"] <= inf_util)
        tramo = perfil_centro.loc[mascara]
        if inf_util <= sup_util or tramo.empty:
            continue
        z_perfil = perfil_centro["z_bajo_base_m"].to_numpy(dtype=float)
        acumulado = perfil_centro["aporte_acum_mm"].to_numpy(dtype=float)
        asiento_mm = float(np.interp(inf_util, z_perfil, acumulado) - np.interp(sup_util, z_perfil, acumulado))
        delta_media = float(np.trapezoid(tramo["delta_sigma_z_kPa"], tramo["z_bajo_base_m"]) / (inf_util - sup_util)) if len(tramo) >= 2 else float(tramo["delta_sigma_z_kPa"].iloc[0])
        filas.append(
            {
                "Estrato": str(capa["Estrato"]),
                "z_sup_bajo_base_m": sup_util,
                "z_inf_bajo_base_m": inf_util,
                "M_MPa": float(tramo["M_MPa"].iloc[0]),
                "delta_sigma_media_kPa": delta_media,
                "asiento_mm": asiento_mm,
            }
        )
    return pd.DataFrame(filas)


def _malla_bulbo(cimentacion: Cimentacion, z_max_m: float, eje: str) -> dict[str, NDArray[np.float64]]:
    semiancho = cimentacion.b_m / 2.0 if eje == "B" else cimentacion.l_m / 2.0
    alcance = max(2.0 * semiancho, 1.25 * z_max_m)
    x = np.linspace(-alcance, alcance, 181)
    z = np.linspace(max(z_max_m / 250.0, 1e-4), z_max_m, 151)
    xx, zz = np.meshgrid(x, z)
    yy = np.zeros_like(xx)
    if eje == "B":
        sigma = incremento_tension_rectangular(xx, yy, zz, cimentacion.b_m, cimentacion.l_m, cimentacion.q_neta_kpa)
    else:
        sigma = incremento_tension_rectangular(yy, xx, zz, cimentacion.b_m, cimentacion.l_m, cimentacion.q_neta_kpa)
    return {"x_m": x, "z_m": z, "delta_sigma_kPa": sigma, "eje": np.array([eje])}


def calcular_caso(
    cimentacion: Cimentacion,
    estratos: pd.DataFrame,
    modo_modulo: ModoModulo,
    nivel_freatico_m: float,
    z_max_m: float,
    n_puntos: int = 601,
) -> ResultadoCalculo:
    """Ejecuta el cálculo multicapa de tensiones y asiento elástico."""
    if z_max_m <= 0 or n_puntos < 80:
        raise ValueError("La profundidad debe ser positiva y se requieren al menos 80 puntos.")
    m_capas = modulo_confinado_kpa(estratos, modo_modulo)
    z = _malla_profundidad(z_max_m, n_puntos, cimentacion.df_m, estratos)

    perfiles: list[pd.DataFrame] = []
    for nombre, (rx, ry) in PUNTOS_CONTROL.items():
        perfiles.append(
            _perfil_punto(
                nombre,
                rx * cimentacion.b_m,
                ry * cimentacion.l_m,
                z,
                cimentacion,
                estratos,
                m_capas,
                nivel_freatico_m,
            )
        )
    tabla_perfiles = pd.concat(perfiles, ignore_index=True)
    resumen = (
        tabla_perfiles.groupby("Punto", sort=False)
        .agg(
            x_m=("x_m", "first"),
            y_m=("y_m", "first"),
            asiento_base_mm=("desplazamiento_mm", "first"),
            delta_sigma_zmax_kPa=("delta_sigma_z_kPa", "last"),
        )
        .reset_index()
    )
    centro = tabla_perfiles[tabla_perfiles["Punto"] == "Centro"].reset_index(drop=True)
    resumen_estratos = _resumen_por_estrato(centro, estratos)

    z_refinado = _malla_profundidad(z_max_m, 2 * n_puntos - 1, cimentacion.df_m, estratos)
    centro_refinado = _perfil_punto(
        "Centro", 0.0, 0.0, z_refinado, cimentacion, estratos, m_capas, nivel_freatico_m
    )
    s1 = float(centro["desplazamiento_mm"].iloc[0])
    s2 = float(centro_refinado["desplazamiento_mm"].iloc[0])
    error = 100.0 * abs(s2 - s1) / max(abs(s2), 1e-12)
    z_corte = 0.9 * z_max_m
    aporte_final = float(
        centro_refinado["aporte_acum_mm"].iloc[-1]
        - np.interp(z_corte, centro_refinado["z_bajo_base_m"], centro_refinado["aporte_acum_mm"])
    )
    proporcion_final = 100.0 * aporte_final / max(abs(s2), 1e-12)

    return ResultadoCalculo(
        perfiles=tabla_perfiles,
        resumen_puntos=resumen,
        resumen_estratos=resumen_estratos,
        malla_corta=_malla_bulbo(cimentacion, z_max_m, "B"),
        malla_larga=_malla_bulbo(cimentacion, z_max_m, "L"),
        error_discretizacion_pct=error,
        contribucion_tramo_final_pct=proporcion_final,
    )
