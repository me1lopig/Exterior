from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from modelos.datos import DatosProyecto, EstadoNF


@dataclass(frozen=True)
class LimitesVerticales:
    minimo: float
    maximo: float
    paso: float
    cota_fondo_minima: float
    cota_terreno_maxima: float
    margen_inferior: float
    margen_superior: float


def _maximo_numerico(frame: pd.DataFrame, column: str) -> float | None:
    if frame.empty or column not in frame:
        return None
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return None
    value = float(values.max())
    return value if math.isfinite(value) else None


def _profundidad_efectiva(datos: DatosProyecto, station: str, station_type: str) -> float:
    candidates: list[float] = [0.0]
    if station_type == "Sondeo":
        lithology = datos.litologia[datos.litologia["sondeo"].astype(str) == station]
        ugeo = datos.ugeo[datos.ugeo["sondeo"].astype(str) == station]
        assays = datos.ensayos[datos.ensayos["sondeo"].astype(str) == station]
        for frame, column in (
            (lithology, "profundidad_final_m"),
            (ugeo, "profundidad_final_m"),
            (assays, "profundidad_m"),
        ):
            value = _maximo_numerico(frame, column)
            if value is not None and value >= 0:
                candidates.append(value)
        nf = datos.nivel_freatico[
            (datos.nivel_freatico["sondeo"].astype(str) == station)
            & (datos.nivel_freatico["estado"].astype(str) == EstadoNF.DETECTADO.value)
        ]
        value = _maximo_numerico(nf, "profundidad_m")
        if value is not None and value >= 0:
            candidates.append(value)
    elif station_type == "DPSH":
        dpsh = datos.dpsh[datos.dpsh["ensayo"].astype(str) == station]
        value = _maximo_numerico(dpsh, "profundidad_m")
        if value is not None and value >= 0:
            candidates.append(value)
    return max(candidates)


def _paso_agradable(span: float, target_divisions: int = 8) -> float:
    if not math.isfinite(span) or span <= 0:
        return 1.0
    raw = span / target_divisions
    exponent = math.floor(math.log10(raw))
    candidates = [
        factor * (10.0**power)
        for power in range(exponent - 1, exponent + 2)
        for factor in (1.0, 2.0, 5.0)
    ]
    return min(candidates, key=lambda step: (abs(span / step - target_divisions), step))


def calcular_limites_verticales(datos: DatosProyecto, perfil: str) -> LimitesVerticales:
    points = datos.perfiles[datos.perfiles["perfil"].astype(str) == perfil].copy()
    points["cota_m"] = pd.to_numeric(points["cota_m"], errors="coerce")
    points = points.dropna(subset=["cota_m"])
    if points.empty:
        raise ValueError(f"El perfil {perfil!r} no contiene cotas validas.")

    ground_max = float(points["cota_m"].max())
    bottom_min = float(points["cota_m"].min())
    max_depth = 0.0
    for _, point in points.iterrows():
        depth = _profundidad_efectiva(
            datos,
            str(point.get("estacion", "")).strip(),
            str(point.get("tipo", "")).strip(),
        )
        max_depth = max(max_depth, depth)
        bottom_min = min(bottom_min, float(point["cota_m"]) - depth)

    occupied_span = max(ground_max - bottom_min, 0.0)
    lower_margin = max(1.0, min(5.0, 0.10 * max_depth))
    upper_margin = max(1.0, min(3.0, 0.05 * occupied_span))
    unrounded_min = bottom_min - lower_margin
    unrounded_max = ground_max + upper_margin
    step = _paso_agradable(unrounded_max - unrounded_min)
    axis_min = math.floor(unrounded_min / step) * step
    axis_max = math.ceil(unrounded_max / step) * step
    if axis_max <= axis_min:
        axis_max = axis_min + step

    return LimitesVerticales(
        minimo=axis_min,
        maximo=axis_max,
        paso=step,
        cota_fondo_minima=bottom_min,
        cota_terreno_maxima=ground_max,
        margen_inferior=lower_margin,
        margen_superior=upper_margin,
    )
