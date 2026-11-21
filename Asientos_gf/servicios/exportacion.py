"""Exportacion reproducible y neutralizacion de formulas en CSV."""

from __future__ import annotations

from dataclasses import asdict
from io import BytesIO
import json
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from calculos.asientos import CalculationResult
from modelos.datos import AnalysisOptions, Foundation, Layer


def _safe_spreadsheet_text(value: Any) -> Any:
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def detailed_csv_bytes(result: CalculationResult) -> bytes:
    frame = pd.DataFrame(result.slices).map(_safe_spreadsheet_text)
    return frame.to_csv(index=False, sep=";", decimal=",", encoding="utf-8-sig").encode("utf-8-sig")


def result_manifest(
    result: CalculationResult,
    foundation: Foundation,
    layers: list[Layer],
    options: AnalysisOptions,
    water_table_m: float | None,
    pore_pressure_points: tuple[tuple[float, float], ...] | None = None,
    project_name: str = "",
) -> dict[str, Any]:
    return {
        "aplicacion": "Calculo de asientos de cimentaciones",
        "version_motor": "2.0.0",
        "proyecto": project_name,
        "convencion": "Profundidad positiva hacia abajo; compresion/asiento positivo.",
        "unidades": {"longitud": "m", "tension": "kPa", "asiento": "mm", "tiempo": "anos"},
        "cimentacion": asdict(foundation),
        "nivel_freatico_m": water_table_m,
        "perfil_piezometrico_z_u": pore_pressure_points,
        "estratos": [asdict(layer) for layer in layers],
        "opciones": asdict(options),
        "resultados": {
            "presion_excavada_kpa": result.excavation_pressure_kpa,
            "resultante_neta_kn": result.net_resultant_kn,
            "profundidad_analisis_m": result.analysis_depth_m,
            "criterio_influencia_alcanzado": result.influence_reached,
            "modelo_contacto": result.pressure_field.contact_model,
            "presion_bruta_min_kpa": float(result.pressure_field.gross_pressure_kpa.min()),
            "presion_bruta_max_kpa": float(result.pressure_field.gross_pressure_kpa.max()),
            "puntos": [asdict(point) for point in result.points],
        },
        "hipotesis": list(result.assumptions),
        "advertencias": list(result.warnings),
        "metodos": {
            "tensiones": "Boussinesq integrado sobre el area real cargada",
            "asiento_inmediato": options.immediate_model,
            "consolidacion": "Terzaghi 1D por unidad drenante saturada",
            "secundario": "C_alpha desde t95 propio de cada unidad drenante",
        },
    }


def manifest_json_bytes(manifest: dict[str, Any]) -> bytes:
    return json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")


def export_bundle_bytes(result: CalculationResult, manifest: dict[str, Any]) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("resultados_detallados.csv", detailed_csv_bytes(result))
        archive.writestr("trazabilidad_calculo.json", manifest_json_bytes(manifest))
    return buffer.getvalue()
