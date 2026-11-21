"""Lectura y generacion de la plantilla Excel."""

from __future__ import annotations

from io import BytesIO
from typing import BinaryIO

import pandas as pd

from perfil_geologico.servicios.datos_demo import crear_datos_demo

HOJAS_OBLIGATORIAS = ("Sondeos", "Intervalos", "Unidades", "Ensayos_DPSH", "Lecturas_DPSH")


def leer_excel(origen: str | BinaryIO | BytesIO) -> dict[str, pd.DataFrame]:
    """Lee las hojas conocidas y comprueba su presencia."""
    libro = pd.ExcelFile(origen)
    faltantes = [hoja for hoja in HOJAS_OBLIGATORIAS if hoja not in libro.sheet_names]
    if faltantes:
        raise ValueError(f"Faltan hojas obligatorias: {', '.join(faltantes)}.")
    datos = {hoja: pd.read_excel(libro, sheet_name=hoja) for hoja in HOJAS_OBLIGATORIAS}
    datos["Eje"] = (
        pd.read_excel(libro, sheet_name="Eje")
        if "Eje" in libro.sheet_names
        else pd.DataFrame(columns=["orden", "x_m", "y_m"])
    )
    return datos


def crear_plantilla_excel(incluir_demo: bool = True) -> bytes:
    """Crea la plantilla oficial en memoria."""
    datos = crear_datos_demo()
    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        for nombre, tabla in datos.items():
            contenido = tabla if incluir_demo else tabla.iloc[0:0]
            contenido.to_excel(writer, sheet_name=nombre, index=False)
        instrucciones = pd.DataFrame(
            {
                "campo": ["Convencion vertical", "DPSH", "Unidades", "Eje"],
                "criterio": [
                    "Profundidad positiva hacia abajo; cotas positivas hacia arriba.",
                    "N20 se representa graficamente; no se interpreta automaticamente.",
                    "El orden aumenta de techo a muro.",
                    "Los puntos se conectan por orden para formar la polilinea del perfil.",
                ],
            }
        )
        instrucciones.to_excel(writer, sheet_name="Instrucciones", index=False)
    return salida.getvalue()


def datos_a_excel(datos: dict[str, pd.DataFrame]) -> bytes:
    """Exporta las tablas actuales sin alterar tipos ni indices."""
    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        for nombre, tabla in datos.items():
            tabla.to_excel(writer, sheet_name=nombre[:31], index=False)
    return salida.getvalue()
