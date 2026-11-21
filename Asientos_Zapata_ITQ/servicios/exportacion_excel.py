from __future__ import annotations

from io import BytesIO

import pandas as pd
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from calculos.asientos import ResultadoCalculo
from calculos.steinbrenner import ResultadoSteinbrenner
from modelos.datos import Cimentacion


AZUL = "2164AF"
AZUL_OSCURO = "12304A"
AZUL_SUAVE = "DCE8F5"
BLANCO = "FFFFFF"
GRIS = "E8ECF1"


def _formatear_hoja(ws, congelar: str = "A2") -> None:
    ws.freeze_panes = congelar
    ws.auto_filter.ref = ws.dimensions
    ws.sheet_view.showGridLines = False
    for celda in ws[1]:
        celda.fill = PatternFill("solid", fgColor=AZUL)
        celda.font = Font(name="Arial", size=10, bold=True, color=BLANCO)
        celda.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    borde = Side(style="thin", color="C7CED8")
    for fila in ws.iter_rows(min_row=2):
        for celda in fila:
            celda.font = Font(name="Arial", size=9, color=AZUL_OSCURO)
            celda.border = Border(bottom=borde)
            if isinstance(celda.value, (int, float)):
                celda.number_format = "0.000"
    for idx, columna in enumerate(ws.columns, start=1):
        longitud = max(len(str(c.value)) if c.value is not None else 0 for c in columna)
        ws.column_dimensions[get_column_letter(idx)].width = min(max(longitud + 2, 11), 28)


def crear_excel(
    cimentacion: Cimentacion,
    estratos: pd.DataFrame,
    nivel_freatico_m: float,
    z_max_m: float,
    resultado: ResultadoCalculo,
    resultado_steinbrenner: ResultadoSteinbrenner,
) -> bytes:
    """Genera un libro auditable con entradas y resultados numéricos."""
    salida = BytesIO()
    resumen_caso = pd.DataFrame(
        {
            "Parámetro": [
                "B", "L", "q neta", "Df", "Nivel freático", "Profundidad analizada",
            ],
            "Valor": [
                cimentacion.b_m, cimentacion.l_m, cimentacion.q_neta_kpa, cimentacion.df_m,
                nivel_freatico_m, z_max_m,
            ],
            "Unidad": ["m", "m", "kPa", "m", "m", "m"],
        }
    )
    control_integracion = pd.DataFrame(
        {
            "Parámetro": ["Paso adoptado", "Intervalos adoptados", "Paso de control", "Intervalos de control", "Error discretización", "Aporte último 10 %"],
            "Valor": [resultado.paso_adoptado_m, resultado.intervalos_adoptados, resultado.paso_control_m, resultado.intervalos_control, resultado.error_discretizacion_pct, resultado.contribucion_tramo_final_pct],
            "Unidad": ["m", "-", "m", "-", "%", "%"],
        }
    )
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        resumen_caso.to_excel(writer, sheet_name="Resumen", index=False)
        estratos.to_excel(writer, sheet_name="Estratos", index=False)
        control_integracion.to_excel(writer, sheet_name="Integración - Control", index=False)
        resultado.resumen_puntos.to_excel(writer, sheet_name="Integración - Puntos", index=False)
        resultado.resumen_estratos.to_excel(writer, sheet_name="Integración - Estratos", index=False)
        resultado.perfiles.to_excel(writer, sheet_name="Integración - Perfiles", index=False)
        resultado_steinbrenner.resumen_puntos.to_excel(writer, sheet_name="Steinbrenner - Puntos", index=False)
        resultado_steinbrenner.resumen_estratos.to_excel(writer, sheet_name="Steinbrenner - Estratos", index=False)
        resultado_steinbrenner.perfiles.to_excel(writer, sheet_name="Steinbrenner - Perfiles", index=False)

        for nombre, malla in [("Bulbo eje B", resultado.malla_corta), ("Bulbo eje L", resultado.malla_larga)]:
            datos = pd.DataFrame(malla["delta_sigma_kPa"], index=malla["z_m"], columns=malla["x_m"])
            datos.index.name = "z_bajo_base_m"
            datos.to_excel(writer, sheet_name=nombre)

        for ws in writer.book.worksheets:
            _formatear_hoja(ws)
    return salida.getvalue()

