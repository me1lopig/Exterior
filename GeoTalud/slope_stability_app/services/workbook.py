"""Exportacion de resultados a un libro XLSX para revision tecnica."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pandas as pd
from openpyxl import Workbook
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo

from slope_stability_app.calculations.search import SearchResult
from slope_stability_app.models import AnalysisConfig, ProjectData, SlopeGeometry, SoilProfile


GEO_BLUE = "2164AF"
PALE_BLUE = "EAF2FB"
PALE_GRAY = "F3F5F7"
GRID = "D9D9D9"
WHITE = "FFFFFF"


def _safe_value(value):
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def _style_header(cell) -> None:
    cell.fill = PatternFill("solid", fgColor=GEO_BLUE)
    cell.font = Font(name="Arial", size=10, bold=True, color=WHITE)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell.border = Border(
        left=Side(style="thin", color=GRID),
        right=Side(style="thin", color=GRID),
        top=Side(style="thin", color=GRID),
        bottom=Side(style="thin", color=GRID),
    )


def _style_body(cell, row_index: int, numeric: bool = False) -> None:
    if row_index % 2 == 0:
        cell.fill = PatternFill("solid", fgColor=PALE_GRAY)
    cell.font = Font(name="Arial", size=9, color="000000")
    cell.alignment = Alignment(horizontal="center" if numeric else "left", vertical="center", wrap_text=True)
    cell.border = Border(
        left=Side(style="thin", color=GRID),
        right=Side(style="thin", color=GRID),
        top=Side(style="thin", color=GRID),
        bottom=Side(style="thin", color=GRID),
    )
    if isinstance(cell.value, float):
        cell.number_format = "0.000"


def _set_widths(worksheet, minimum: float = 11.0, maximum: float = 34.0) -> None:
    for column_cells in worksheet.columns:
        letter = column_cells[0].column_letter
        longest = max((len(str(cell.value)) for cell in column_cells if cell.value is not None), default=0)
        worksheet.column_dimensions[letter].width = min(max(longest + 2, minimum), maximum)


def _add_table_sheet(workbook: Workbook, title: str, headers: list[str], rows: list[list], table_name: str):
    worksheet = workbook.create_sheet(title)
    worksheet.append(headers)
    for cell in worksheet[1]:
        _style_header(cell)
    for row_index, values in enumerate(rows, start=2):
        worksheet.append([_safe_value(value) for value in values])
        for cell in worksheet[row_index]:
            _style_body(cell, row_index, isinstance(cell.value, (int, float)))
    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    worksheet.sheet_view.showGridLines = False
    worksheet.page_setup.orientation = "landscape" if len(headers) > 5 else "portrait"
    worksheet.page_setup.fitToWidth = 1
    worksheet.sheet_properties.pageSetUpPr.fitToPage = True
    worksheet.print_title_rows = "1:1"
    if rows:
        table = Table(displayName=table_name, ref=worksheet.dimensions)
        table.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        worksheet.add_table(table)
    _set_widths(worksheet)
    return worksheet


def _summary_sheet(
    workbook: Workbook,
    project: ProjectData,
    geometry: SlopeGeometry,
    config: AnalysisConfig,
    result: SearchResult,
) -> None:
    worksheet = workbook.active
    worksheet.title = "Resumen"
    worksheet.sheet_view.showGridLines = False
    worksheet.merge_cells("A1:D1")
    worksheet["A1"] = "Estabilidad de talud temporal"
    worksheet["A1"].font = Font(name="Arial", size=16, bold=True, color=GEO_BLUE)
    worksheet["A1"].alignment = Alignment(horizontal="left", vertical="center")
    worksheet.row_dimensions[1].height = 26
    metadata = [
        ("Proyecto", project.name or "Analisis sin titulo"),
        ("Localizacion", project.location),
        ("Autor", project.author),
        ("Fecha de exportacion", datetime.now().strftime("%d/%m/%Y %H:%M")),
    ]
    for row, (label, value) in enumerate(metadata, start=3):
        worksheet.cell(row, 1, label).font = Font(name="Arial", size=9, bold=True, color=GEO_BLUE)
        worksheet.cell(row, 2, value).font = Font(name="Arial", size=9)

    worksheet["A8"] = "Datos principales"
    worksheet["A8"].font = Font(name="Arial", size=11, bold=True, color=GEO_BLUE)
    inputs = [
        ("Altura H", geometry.height, "m"),
        ("Pendiente", geometry.angle_deg, "grados"),
        ("Profundidad NF desde coronacion", geometry.water_depth, "m"),
        ("Cota interna NF respecto al pie", geometry.water_elevation, "m"),
        ("Profundidad del modelo", geometry.model_depth, "m"),
        ("Dovelas", config.slices, "-"),
        ("Densidad de busqueda", config.search_level, "-"),
        ("FS objetivo", config.target_factor, "-"),
    ]
    worksheet.append([])
    input_header_row = 9
    for column, value in enumerate(("Parametro", "Valor", "Unidad"), start=1):
        worksheet.cell(input_header_row, column, value)
        _style_header(worksheet.cell(input_header_row, column))
    for row_index, values in enumerate(inputs, start=input_header_row + 1):
        for column, value in enumerate(values, start=1):
            cell = worksheet.cell(row_index, column, value)
            _style_body(cell, row_index, column == 2 and isinstance(value, (int, float)))

    result_start = input_header_row + len(inputs) + 2
    worksheet.cell(result_start, 1, "Resultados criticos").font = Font(name="Arial", size=11, bold=True, color=GEO_BLUE)
    headers = ("Metodo", "FS minimo", "Centro x (m)", "Centro z (m)", "Radio (m)")
    for column, value in enumerate(headers, start=1):
        cell = worksheet.cell(result_start + 1, column, value)
        _style_header(cell)
    for row_index, critical in enumerate((result.fellenius, result.bishop), start=result_start + 2):
        circle = critical.evaluation.circle
        values = (critical.method, critical.factor_of_safety, circle.center_x, circle.center_y, circle.radius)
        for column, value in enumerate(values, start=1):
            cell = worksheet.cell(row_index, column, value)
            _style_body(cell, row_index, column > 1)
    worksheet.freeze_panes = "A9"
    worksheet.column_dimensions["A"].width = 36
    for letter in ("B", "C", "D", "E"):
        worksheet.column_dimensions[letter].width = 17


def _soil_rows(profile: SoilProfile) -> list[list]:
    rows: list[list] = []
    cumulative = 0.0
    for index, layer in enumerate(profile.layers, start=1):
        start = cumulative
        cumulative += layer.thickness
        rows.append(
            [
                index,
                layer.soil.name,
                layer.thickness,
                start,
                cumulative,
                layer.soil.gamma_dry,
                layer.soil.gamma_sat,
                layer.soil.cohesion,
                layer.soil.friction_deg,
            ]
        )
    return rows


def _surface_rows(result: SearchResult) -> list[list]:
    rows = []
    for critical in (result.fellenius, result.bishop):
        circle = critical.evaluation.circle
        rows.append(
            [
                critical.method,
                critical.factor_of_safety,
                circle.entry_x,
                circle.exit_x,
                circle.center_x,
                circle.center_y,
                circle.radius,
                critical.evaluation.total_weight,
                critical.evaluation.max_pore_pressure,
                critical.evaluation.bishop.iterations if critical.method.startswith("Bishop") else 1,
            ]
        )
    return rows


def _slice_rows(result: SearchResult, method: str) -> list[list]:
    critical = result.bishop if method == "Bishop" else result.fellenius
    return [
        [
            item.index,
            item.x_mid,
            item.base_elevation,
            item.top_elevation,
            item.width,
            item.base_angle_deg,
            item.base_length,
            item.weight,
            item.pore_pressure,
            item.pore_force,
            item.soil_name,
            item.cohesion,
            item.friction_deg,
        ]
        for item in critical.evaluation.slices
    ]


def build_results_workbook(
    project: ProjectData,
    geometry: SlopeGeometry,
    profile: SoilProfile,
    config: AnalysisConfig,
    result: SearchResult,
    sensitivity: pd.DataFrame | None = None,
) -> bytes:
    """Genera un libro XLSX autocontenido con entradas y resultados."""
    workbook = Workbook()
    workbook.properties.creator = project.author or "GeoSlope"
    workbook.properties.title = f"Resultados de estabilidad - {project.name}"
    _summary_sheet(workbook, project, geometry, config, result)
    _add_table_sheet(
        workbook,
        "Suelos",
        ["Capa", "Suelo", "Espesor (m)", "Prof. inicial (m)", "Prof. final (m)", "gamma seco (kN/m3)", "gamma sat. (kN/m3)", "c' (kPa)", "phi' (deg)"],
        _soil_rows(profile),
        "TablaSuelos",
    )
    _add_table_sheet(
        workbook,
        "Superficies criticas",
        ["Metodo", "FS", "Entrada x (m)", "Salida x (m)", "Centro x (m)", "Centro z (m)", "Radio (m)", "Peso (kN/m)", "u max (kPa)", "Iteraciones"],
        _surface_rows(result),
        "TablaSuperficies",
    )
    if sensitivity is not None and not sensitivity.empty:
        ordered = sensitivity.sort_values(["Pendiente (deg)", "Profundidad NF (m)"], kind="stable")
        rows = [[_safe_value(value) for value in row] for row in ordered.itertuples(index=False, name=None)]
        worksheet = _add_table_sheet(
            workbook,
            "Sensibilidad",
            list(ordered.columns),
            rows,
            "TablaSensibilidad",
        )
        bishop_column = list(ordered.columns).index("FS Bishop") + 1
        if len(rows) > 1:
            letter = worksheet.cell(1, bishop_column).column_letter
            worksheet.conditional_formatting.add(
                f"{letter}2:{letter}{len(rows) + 1}",
                ColorScaleRule(start_type="min", start_color="F8696B", mid_type="percentile", mid_value=50, mid_color="FFEB84", end_type="max", end_color="63BE7B"),
            )
    slice_headers = [
        "Dovela", "x medio (m)", "z base (m)", "z terreno (m)", "Ancho (m)", "alpha (deg)",
        "Longitud base (m)", "Peso (kN/m)", "u (kPa)", "Fuerza de poros (kN/m)", "Suelo en base", "c' (kPa)", "phi' (deg)",
    ]
    _add_table_sheet(workbook, "Dovelas Bishop", slice_headers, _slice_rows(result, "Bishop"), "TablaDovelasBishop")
    _add_table_sheet(workbook, "Dovelas Fellenius", slice_headers, _slice_rows(result, "Fellenius"), "TablaDovelasFellenius")
    workbook.active = 0
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
