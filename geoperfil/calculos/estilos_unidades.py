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
    ordenes: dict[str, int] = {}
    for idx, fila in tabla.iterrows():
        codigo = str(fila["unidad_id"])
        datos = cambios.get(codigo, {})
        nombre = str(datos.get("nombre", fila["nombre"])).strip()
        color = str(datos.get("color", fila["color"])).upper()
        try:
            orden = int(datos.get("orden", fila["orden"]))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Orden no válido para {codigo}.") from exc
        if not nombre:
            raise ValueError(f"La unidad {codigo} debe tener nombre.")
        if COLOR.fullmatch(color) is None:
            raise ValueError(f"Color no válido para {codigo}: {color!r}.")
        if orden <= 0:
            raise ValueError(f"El orden de {codigo} debe ser positivo.")
        tabla.at[idx, "nombre"] = nombre
        tabla.at[idx, "color"] = color
        tabla.at[idx, "orden"] = orden
        colores[codigo] = color
        ordenes[codigo] = orden
    if len(set(ordenes.values())) != len(ordenes):
        raise ValueError("El orden estratigráfico no puede contener duplicados.")
    # Las zonas previamente clasificadas deben seguir la nueva paleta.
    nuevas_zonas = []
    for zona in zonas:
        copia = dict(zona)
        codigo = str(copia.get("unidad_id", ""))
        if codigo in colores:
            copia["color"] = colores[codigo]
        nuevas_zonas.append(copia)
    return tabla, nuevas_zonas


def aplicar_paleta_contactos(contactos: list, unidades: pd.DataFrame) -> None:
    """Actualiza el color gráfico de cada contacto sin alterar su geometría."""
    colores = dict(zip(unidades["unidad_id"].astype(str), unidades["color"].astype(str)))
    for contacto in contactos:
        if str(contacto.unidad_inferior) in colores:
            contacto.color = colores[str(contacto.unidad_inferior)]
