from __future__ import annotations

import hashlib
import io
import math
import re
from dataclasses import dataclass, field
from typing import Any

import ezdxf
import pandas as pd
from ezdxf.enums import TextEntityAlignment

from calculos.ejes import calcular_limites_verticales
from modelos.configuracion import OpcionesGraficas
from modelos.datos import DatosProyecto, EstadoNF


@dataclass(frozen=True)
class OpcionesDXF:
    perfiles: list[str]
    modo_columna: str = "Litologia"
    mostrar_sondeos: bool = True
    mostrar_dpsh: bool = True
    anotar_nf_ausente: bool = True
    version: str = "R2010"
    limites_verticales: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    graficos: OpcionesGraficas = field(default_factory=OpcionesGraficas)


LAYERS = {
    "RETICULA": 8,
    "TERRENO": 3,
    "SONDEOS": 5,
    "DPSH": 1,
    "NIVEL_FREATICO": 5,
    "UGEO": 30,
    "ENSAYOS": 6,
    "TEXTOS": 7,
}


def _block_name(prefix: str, source: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9_-]+", "_", source).strip("_") or "SIN_NOMBRE"
    digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:6]
    return f"{prefix}_{clean}_{digest}"


def _float(value: object, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _add_text(
    layout: Any,
    text: str,
    position: tuple[float, float],
    height: float = 0.22,
    layer: str = "TEXTOS",
    align: TextEntityAlignment = TextEntityAlignment.MIDDLE_LEFT,
) -> None:
    entity = layout.add_text(str(text), dxfattribs={"height": height, "layer": layer})
    entity.set_placement(position, align=align)


def _nf_row(datos: DatosProyecto, name: str) -> pd.Series | None:
    rows = datos.nivel_freatico[datos.nivel_freatico["sondeo"].astype(str) == name]
    return None if rows.empty else rows.iloc[0]


def _draw_nf(
    block: Any,
    datos: DatosProyecto,
    name: str,
    max_depth: float,
    annotate_absent: bool,
    graphics: OpcionesGraficas,
) -> None:
    row = _nf_row(datos, name)
    if row is None:
        return
    state = str(row.get("estado", ""))
    if state == EstadoNF.DETECTADO.value:
        depth = _float(row.get("profundidad_m"))
        block.add_lwpolyline(
            [(-0.28, -depth), (0.28, -depth)],
            dxfattribs={"const_width": 0.08, "layer": "NIVEL_FREATICO"},
        )
        _add_text(
            block,
            f"NF {depth:.2f} m",
            (-0.38, -depth),
            graphics.texto_estratos_m,
            "NIVEL_FREATICO",
            TextEntityAlignment.MIDDLE_RIGHT,
        )
    elif annotate_absent and state == EstadoNF.NO_DETECTADO.value:
        _add_text(
            block,
            "NF no detectado",
            (graphics.separacion_horizontal_m, -max_depth),
            graphics.texto_estratos_m,
            "NIVEL_FREATICO",
        )
    elif annotate_absent and state == EstadoNF.NO_MEDIDO.value:
        _add_text(
            block,
            "NF no medido",
            (graphics.separacion_horizontal_m, -max_depth),
            graphics.texto_estratos_m,
            "NIVEL_FREATICO",
        )


def _assay_label(row: pd.Series) -> str:
    assay_type = str(row.get("tipo", "")).strip().upper()
    parts = [assay_type or "ENSAYO"]
    n_spt = str(row.get("n_spt", "")).strip()
    if assay_type == "SPT" and n_spt:
        parts.append(f"N={n_spt}")
    uscs = str(row.get("uscs", "")).strip()
    if uscs:
        parts.append(f"USCS={uscs}")
    rcs = str(row.get("rcs_kpa", "")).strip()
    phi = str(row.get("phi_deg", "")).strip()
    cohesion = str(row.get("cohesion_kpa", "")).strip()
    if rcs:
        parts.append(f"RCS={rcs} kPa")
    if phi:
        parts.append(f"phi={phi} deg")
    if cohesion:
        parts.append(f"c={cohesion} kPa")
    return "; ".join(parts)


def _create_column_block(
    doc: ezdxf.document.Drawing,
    datos: DatosProyecto,
    name: str,
    *,
    use_ugeo: bool,
    annotate_absent: bool,
    graphics: OpcionesGraficas,
) -> str:
    prefix = "UGEO" if use_ugeo else "SONDEO"
    block_name = _block_name(prefix, name)
    block = doc.blocks.new(block_name)
    source = datos.ugeo if use_ugeo else datos.litologia
    id_column = "sondeo"
    rows = source[source[id_column].astype(str) == name].copy()
    rows["profundidad_inicial_m"] = pd.to_numeric(rows["profundidad_inicial_m"], errors="coerce")
    rows["profundidad_final_m"] = pd.to_numeric(rows["profundidad_final_m"], errors="coerce")
    rows = rows.sort_values("profundidad_inicial_m")
    max_depth = float(rows["profundidad_final_m"].max()) if not rows.empty else 0.0

    _add_text(
        block,
        name,
        (0, graphics.separacion_nombre_m),
        graphics.nombre_prospeccion_m,
        "TEXTOS",
        TextEntityAlignment.BOTTOM_CENTER,
    )
    for _, row in rows.iterrows():
        start = _float(row["profundidad_inicial_m"])
        end = _float(row["profundidad_final_m"])
        layer = "UGEO" if use_ugeo else "SONDEOS"
        block.add_lwpolyline(
            [(-0.12, -start), (-0.12, -end), (0.12, -end), (0.12, -start), (-0.12, -start)],
            dxfattribs={"layer": layer},
        )
        label = str(row.get("codigo", "")).strip() if use_ugeo else str(row.get("descripcion_corta", "")).strip()
        if not label:
            label = "Sin descripcion"
        middle = -0.5 * (start + end)
        leader_end = max(0.20, graphics.separacion_horizontal_m - 0.07)
        block.add_line((0.12, middle), (leader_end, middle), dxfattribs={"layer": layer})
        _add_text(
            block,
            label,
            (graphics.separacion_horizontal_m, middle),
            graphics.texto_estratos_m,
            layer,
        )

    assays = datos.ensayos[datos.ensayos["sondeo"].astype(str) == name].copy()
    assays["profundidad_m"] = pd.to_numeric(assays["profundidad_m"], errors="coerce")
    assays = assays.sort_values(["profundidad_m", "tipo"])
    occurrences: dict[float, int] = {}
    for _, row in assays.iterrows():
        depth = _float(row["profundidad_m"])
        key = round(depth, 3)
        offset = occurrences.get(key, 0) * graphics.separacion_vertical_ensayos_m
        occurrences[key] = occurrences.get(key, 0) + 1
        label_y = -depth - offset
        leader_end = max(0.20, graphics.separacion_horizontal_m - 0.07)
        block.add_line((0.18, -depth), (leader_end, label_y), dxfattribs={"layer": "ENSAYOS"})
        _add_text(
            block,
            _assay_label(row),
            (graphics.separacion_horizontal_m, label_y),
            graphics.texto_ensayos_m,
            "ENSAYOS",
        )

    _draw_nf(block, datos, name, max_depth, annotate_absent, graphics)
    return block_name


def _create_dpsh_block(
    doc: ezdxf.document.Drawing,
    datos: DatosProyecto,
    name: str,
    graphics: OpcionesGraficas,
) -> str:
    block_name = _block_name("DPSH", name)
    block = doc.blocks.new(block_name)
    rows = datos.dpsh[datos.dpsh["ensayo"].astype(str) == name].copy()
    rows["profundidad_m"] = pd.to_numeric(rows["profundidad_m"], errors="coerce")
    rows["golpes"] = pd.to_numeric(rows["golpes"], errors="coerce")
    rows = rows.sort_values("profundidad_m")
    max_depth = float(rows["profundidad_m"].max()) if not rows.empty else 0.0
    width = 5.0
    scale = width / 100.0
    _add_text(
        block,
        name,
        (0, graphics.separacion_nombre_m),
        graphics.nombre_prospeccion_m,
        "TEXTOS",
        TextEntityAlignment.BOTTOM_CENTER,
    )
    block.add_line((0, 0), (width, 0), dxfattribs={"layer": "DPSH"})
    for blows in (0, 50, 100):
        x = blows * scale
        block.add_line((x, 0), (x, 0.5), dxfattribs={"layer": "DPSH"})
        _add_text(
            block,
            "R" if blows == 100 else str(blows),
            (x, 0.65),
            graphics.texto_ejes_m,
            "DPSH",
            TextEntityAlignment.BOTTOM_CENTER,
        )
    block.add_line((0, 0), (0, -max_depth), dxfattribs={"layer": "DPSH"})
    points = [(0.0, 0.0)]
    for _, row in rows.iterrows():
        blows = min(max(_float(row["golpes"]), 0.0), 100.0)
        points.append((blows * scale, -_float(row["profundidad_m"])))
    if len(points) > 1:
        block.add_lwpolyline(points, dxfattribs={"layer": "DPSH"})
    return block_name


def _create_profile_block(
    doc: ezdxf.document.Drawing,
    datos: DatosProyecto,
    profile_name: str,
    options: OpcionesDXF,
    *,
    use_ugeo: bool,
) -> tuple[str, float, float]:
    suffix = "UGEO" if use_ugeo else "LITO"
    name = _block_name(f"PERFIL_{suffix}", profile_name)
    block = doc.blocks.new(name)
    profile = datos.perfiles[datos.perfiles["perfil"].astype(str) == profile_name].copy()
    profile["distancia_m"] = pd.to_numeric(profile["distancia_m"], errors="coerce")
    profile["cota_m"] = pd.to_numeric(profile["cota_m"], errors="coerce")
    profile = profile.sort_values(["distancia_m", "orden"])
    min_x = float(profile["distancia_m"].min())
    max_x = float(profile["distancia_m"].max())
    width = max(max_x - min_x, 1.0)
    if profile_name in options.limites_verticales:
        datum, axis_top, vertical_step = options.limites_verticales[profile_name]
    else:
        limits = calcular_limites_verticales(datos, profile_name)
        datum, axis_top, vertical_step = limits.minimo, limits.maximo, limits.paso
    height = axis_top - datum

    graphics = options.graficos
    title_offset = max(1.0, graphics.separacion_nombre_m)
    _add_text(
        block,
        f"{profile_name} - {suffix}",
        (0, height + title_offset),
        graphics.titulo_m,
        "TEXTOS",
    )
    block.add_line((0, 0), (width, 0), dxfattribs={"layer": "RETICULA"})
    for x in range(0, int(math.ceil(width)) + 1):
        if x % 25 == 0:
            block.add_line((x, 0), (x, height), dxfattribs={"layer": "RETICULA"})
            label_offset = max(0.35, graphics.texto_ejes_m * 2.5)
            _add_text(
                block,
                f"{min_x + x:g}",
                (x, -label_offset),
                graphics.texto_ejes_m,
                "TEXTOS",
                TextEntityAlignment.TOP_CENTER,
            )
    z = math.ceil(datum / vertical_step) * vertical_step
    while z <= axis_top + vertical_step * 1e-9:
        y = z - datum
        block.add_line((0, y), (width, y), dxfattribs={"layer": "RETICULA"})
        _add_text(
            block,
            f"{z:g}",
            (-max(0.35, graphics.separacion_horizontal_m), y),
            graphics.texto_ejes_m,
            "TEXTOS",
            TextEntityAlignment.MIDDLE_RIGHT,
        )
        z += vertical_step

    terrain = [(_float(row["distancia_m"]) - min_x, _float(row["cota_m"]) - datum) for _, row in profile.iterrows()]
    if len(terrain) >= 2:
        block.add_lwpolyline(terrain, dxfattribs={"layer": "TERRENO"})

    for _, row in profile.iterrows():
        station = str(row["estacion"]).strip()
        station_type = str(row["tipo"]).strip()
        insertion = (_float(row["distancia_m"]) - min_x, _float(row["cota_m"]) - datum)
        if station_type == "Sondeo" and options.mostrar_sondeos:
            block_ref = _block_name("UGEO" if use_ugeo else "SONDEO", station)
            if block_ref in doc.blocks:
                block.add_blockref(block_ref, insertion)
        elif station_type == "DPSH" and options.mostrar_dpsh:
            block_ref = _block_name("DPSH", station)
            if block_ref in doc.blocks:
                block.add_blockref(block_ref, insertion)
    return name, width, height


def _create_legend(
    doc: ezdxf.document.Drawing,
    datos: DatosProyecto,
    use_ugeo: bool,
    graphics: OpcionesGraficas,
) -> str:
    name = _block_name("LEYENDA", "UGEO" if use_ugeo else "LITO")
    block = doc.blocks.new(name)
    _add_text(block, "LEYENDA", (0, 0), graphics.titulo_m, "TEXTOS", TextEntityAlignment.BOTTOM_LEFT)
    y = -0.8
    if use_ugeo:
        for code in datos.ugeo["codigo"].dropna().astype(str).drop_duplicates():
            block.add_lwpolyline([(0, y), (0, y - 0.5), (0.8, y - 0.5), (0.8, y), (0, y)], dxfattribs={"layer": "UGEO"})
            _add_text(block, code, (1.0, y - 0.25), graphics.texto_estratos_m, "UGEO")
            y -= 0.75
    _add_text(
        block,
        "NF: profundidad bajo boca de sondeo",
        (0, y - 0.3),
        graphics.texto_estratos_m,
        "NIVEL_FREATICO",
    )
    _add_text(
        block,
        "SPT N: suma de los tramos centrales",
        (0, y - 0.7),
        graphics.texto_ensayos_m,
        "ENSAYOS",
    )
    return name


def generar_dxf(datos: DatosProyecto, options: OpcionesDXF) -> bytes:
    doc = ezdxf.new(dxfversion=options.version)
    for layer, color in LAYERS.items():
        if layer not in doc.layers:
            doc.layers.add(layer, color=color)
    modelspace = doc.modelspace()

    modes = [False, True] if options.modo_columna == "Ambos" else [options.modo_columna == "UGEO"]
    for use_ugeo in modes:
        if use_ugeo and datos.ugeo.empty:
            continue
        source = datos.ugeo if use_ugeo else datos.litologia
        boreholes = source["sondeo"].dropna().astype(str).drop_duplicates()
        for name in boreholes:
            _create_column_block(
                doc,
                datos,
                name,
                use_ugeo=use_ugeo,
                annotate_absent=options.anotar_nf_ausente,
                graphics=options.graficos,
            )
    for name in datos.dpsh["ensayo"].dropna().astype(str).drop_duplicates():
        _create_dpsh_block(doc, datos, name, options.graficos)

    cursor_x = 0.0
    legends: set[bool] = set()
    for profile_name in options.perfiles:
        for use_ugeo in modes:
            if use_ugeo and datos.ugeo.empty:
                continue
            block_name, width, _ = _create_profile_block(
                doc, datos, profile_name, options, use_ugeo=use_ugeo
            )
            modelspace.add_blockref(block_name, (cursor_x, 0))
            cursor_x += width + 25.0
            legends.add(use_ugeo)
    legend_x = 0.0
    for use_ugeo in sorted(legends):
        legend = _create_legend(doc, datos, use_ugeo, options.graficos)
        modelspace.add_blockref(legend, (legend_x, -15.0))
        legend_x += 25.0

    auditor = doc.audit()
    if auditor.errors:
        raise RuntimeError(f"La auditoria DXF encontro {len(auditor.errors)} errores.")
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue().encode("utf-8")
