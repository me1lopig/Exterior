from __future__ import annotations

import math

import matplotlib.pyplot as plt
import pandas as pd

from calculos.ejes import calcular_limites_verticales
from modelos.configuracion import OpcionesGraficas
from modelos.datos import DatosProyecto, EstadoNF


def crear_vista_previa(
    datos: DatosProyecto,
    perfil: str,
    *,
    usar_ugeo: bool,
    mostrar_sondeos: bool,
    mostrar_dpsh: bool,
    limites_verticales: tuple[float, float, float] | None = None,
    graficos: OpcionesGraficas | None = None,
):
    graphics = graficos or OpcionesGraficas()
    rows = datos.perfiles[datos.perfiles["perfil"].astype(str) == perfil].copy()
    rows["distancia_m"] = pd.to_numeric(rows["distancia_m"], errors="coerce")
    rows["cota_m"] = pd.to_numeric(rows["cota_m"], errors="coerce")
    rows = rows.dropna(subset=["distancia_m", "cota_m"]).sort_values(["distancia_m", "orden"])
    figure, axis = plt.subplots(figsize=(13, 5.5), constrained_layout=True)
    if rows.empty:
        axis.text(0.5, 0.5, "Perfil sin puntos validos", ha="center", va="center")
        return figure

    axis.plot(rows["distancia_m"], rows["cota_m"], color="#23875b", linewidth=2.0, label="Terreno")
    source = datos.ugeo if usar_ugeo else datos.litologia
    code_column = "codigo" if usar_ugeo else "descripcion_corta"
    palette = plt.get_cmap("tab20")
    codes = list(source.get(code_column, pd.Series(dtype=str)).fillna("").astype(str).unique())
    colors = {code: palette(index % 20) for index, code in enumerate(codes)}

    for _, point in rows.iterrows():
        x = float(point["distancia_m"])
        z = float(point["cota_m"])
        station = str(point["estacion"])
        station_type = str(point["tipo"])
        if station_type == "Sondeo" and mostrar_sondeos:
            strata = source[source["sondeo"].astype(str) == station]
            for _, stratum in strata.iterrows():
                start = pd.to_numeric(stratum["profundidad_inicial_m"], errors="coerce")
                end = pd.to_numeric(stratum["profundidad_final_m"], errors="coerce")
                if pd.isna(start) or pd.isna(end):
                    continue
                code = str(stratum.get(code_column, ""))
                axis.fill_betweenx(
                    [z - float(end), z - float(start)],
                    x - 0.35,
                    x + 0.35,
                    color=colors.get(code, "#bbbbbb"),
                    edgecolor="#222222",
                    linewidth=0.5,
                )
                axis.text(
                    x + graphics.separacion_horizontal_m,
                    z - 0.5 * (float(start) + float(end)),
                    code,
                    fontsize=max(5.0, 7.0 * graphics.texto_estratos_m / 0.20),
                    va="center",
                )
            nf = datos.nivel_freatico[datos.nivel_freatico["sondeo"].astype(str) == station]
            if not nf.empty and str(nf.iloc[0]["estado"]) == EstadoNF.DETECTADO.value:
                depth = pd.to_numeric(nf.iloc[0]["profundidad_m"], errors="coerce")
                if not pd.isna(depth):
                    axis.scatter([x], [z - float(depth)], marker="v", s=30, color="#1769aa", zorder=6)
            assays = datos.ensayos[datos.ensayos["sondeo"].astype(str) == station].copy()
            assays["profundidad_m"] = pd.to_numeric(assays["profundidad_m"], errors="coerce")
            assays = assays.dropna(subset=["profundidad_m"]).sort_values(["profundidad_m", "tipo"])
            occurrences: dict[float, int] = {}
            for _, assay in assays.iterrows():
                depth = float(assay["profundidad_m"])
                key = round(depth, 3)
                label_y = z - depth - occurrences.get(key, 0) * graphics.separacion_vertical_ensayos_m
                occurrences[key] = occurrences.get(key, 0) + 1
                assay_type_value = assay.get("tipo", "ENSAYO")
                assay_type = "ENSAYO" if pd.isna(assay_type_value) else str(assay_type_value)
                n_spt_value = assay.get("n_spt", "")
                n_spt = "" if pd.isna(n_spt_value) else str(n_spt_value).strip()
                label = f"{assay_type} N={n_spt}" if assay_type.upper() == "SPT" and n_spt else assay_type
                axis.plot(
                    [x + 0.15, x + max(0.20, graphics.separacion_horizontal_m - 0.07)],
                    [z - depth, label_y],
                    color="#8a5d00",
                    linewidth=0.6,
                )
                axis.text(
                    x + graphics.separacion_horizontal_m,
                    label_y,
                    label,
                    fontsize=max(5.0, 7.0 * graphics.texto_ensayos_m / 0.18),
                    va="center",
                    color="#6b4900",
                )
        elif station_type == "DPSH" and mostrar_dpsh:
            tests = datos.dpsh[datos.dpsh["ensayo"].astype(str) == station]
            max_depth = pd.to_numeric(tests["profundidad_m"], errors="coerce").max()
            if not pd.isna(max_depth):
                axis.plot([x, x], [z, z - float(max_depth)], color="#cf3f4b", linewidth=1.5)
        axis.text(
            x,
            z + graphics.separacion_nombre_m,
            station,
            rotation=90,
            fontsize=max(5.0, 7.0 * graphics.nombre_prospeccion_m / 0.42),
            ha="center",
            va="bottom",
        )

    x_min, x_max = float(rows["distancia_m"].min()), float(rows["distancia_m"].max())
    axis.set_xlim(
        x_min - max((x_max - x_min) * 0.03, 1.0),
        x_max + max((x_max - x_min) * 0.08, graphics.separacion_horizontal_m * 4.0, 2.0),
    )
    axis_label_size = max(6.0, 9.0 * graphics.texto_ejes_m / 0.18)
    axis.set_xlabel("Distancia (m)", fontsize=axis_label_size)
    axis.set_ylabel("Cota (m)", fontsize=axis_label_size)
    axis.set_title(
        f"Perfil {perfil} - {'unidades geotecnicas' if usar_ugeo else 'litologia'}",
        loc="left",
        weight="bold",
        fontsize=max(8.0, 12.0 * graphics.titulo_m / 0.65),
    )
    axis.grid(True, color="#d9dee5", linewidth=0.6)
    axis.spines[["top", "right"]].set_visible(False)
    axis.set_aspect("auto")
    if limites_verticales is None:
        limits = calcular_limites_verticales(datos, perfil)
        limites_verticales = (limits.minimo, limits.maximo, limits.paso)
    axis_min, axis_max, vertical_step = limites_verticales
    axis.set_ylim(axis_min, axis_max)
    ticks: list[float] = []
    tick = math.ceil(axis_min / vertical_step) * vertical_step
    while tick <= axis_max + vertical_step * 1e-9:
        ticks.append(tick)
        tick += vertical_step
    axis.set_yticks(ticks)
    axis.tick_params(axis="both", labelsize=axis_label_size)
    return figure
