from __future__ import annotations

from copy import copy
from io import BytesIO

import pandas as pd


def capacity_grid_to_excel(
    capacity_grid: pd.DataFrame,
    layers: pd.DataFrame,
    cu_profile: pd.DataFrame | None = None,
) -> bytes:
    """Export the main calculation tables to a formatted XLSX workbook."""
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        capacity_grid.to_excel(writer, sheet_name="Capacidad B-L", index=False)
        layers.to_excel(writer, sheet_name="Estratigrafia", index=False)
        if cu_profile is not None and not cu_profile.empty:
            cu_profile.to_excel(writer, sheet_name="Perfil cu", index=False)
        for worksheet in writer.book.worksheets:
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions
            for cell in worksheet[1]:
                font = copy(cell.font)
                font.bold = True
                font.color = "FFFFFF"
                cell.font = font
                fill = copy(cell.fill)
                fill.fill_type = "solid"
                fill.fgColor.rgb = "2164AF"
                cell.fill = fill
            for column in worksheet.columns:
                width = min(
                    max(len(str(cell.value)) if cell.value is not None else 0 for cell in column)
                    + 2,
                    32,
                )
                worksheet.column_dimensions[column[0].column_letter].width = width
    return buffer.getvalue()
