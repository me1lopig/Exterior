"""Preferencias de visualizacion editables para las unidades geologicas."""
from __future__ import annotations
from collections.abc import Mapping
import re
import pandas as pd

COLOR = re.compile(r"#[0-9A-Fa-f]{6}\Z")


def aplicar_edicion_unidades(
    unidades: pd.DataFrame, zonas: list[dict], cambios: Mapping[str, Mapping[str, str]]
) -> tuple[pd.DataFrame, list[dict]]:
    """Edita nombre/color sin cambiar unidad_id ni perder el estilo de las zonas.

    Devuelve copias: un error deja la campana intacta. Observaciones no forma parte
    del catalogo de unidades editable; los datos originales quedan en BKFL/Fuentes.
    """
    tabla = unidades.drop(columns=["observaciones"], errors="ignore").copy(deep=True)
    codigos = set(tabla["unidad_id"].astype(str))
    if not set(cambios).issubset(codigos):
        raise ValueError("Hay códigos de unidad inexistentes.")
    colores = {}
    for idx, fila in tabla.iterrows():
        codigo = str(fila["unidad_id"])
        datos = cambios.get(codigo, {})
        nombre = str(datos.get("nombre", fila["nombre"])).strip()
        color = str(datos.get("color", fila["color"])).upper()
        if not nombre:
            raise ValueError(f"La unidad {codigo} debe tener nombre.")
        if COLOR.fullmatch(color) is None:
            raise ValueError(f"Color no válido para {codigo}: {color!r}.")
        tabla.at[idx, "nombre"] = nombre
        tabla.at[idx, "color"] = color
        colores[codigo] = color
    # Las zonas previamente clasificadas deben seguir la nueva paleta.
    nuevas_zonas = []
    for zona in zonas:
        copia = dict(zona)
        codigo = str(copia.get("unidad_id", ""))
        if codigo in colores:
            copia["color"] = colores[codigo]
        nuevas_zonas.append(copia)
    return tabla, nuevas_zonas
