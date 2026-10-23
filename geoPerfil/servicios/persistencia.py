"""Serializacion trazable del proyecto y sus tablas."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pandas as pd

from perfil_geologico.modelos.dominio import Proyecto


def _registros(tabla: pd.DataFrame) -> list[dict[str, Any]]:
    limpia = tabla.where(pd.notna(tabla), None)
    return limpia.to_dict(orient="records")


def proyecto_a_json(proyecto: Proyecto, datos: dict[str, pd.DataFrame]) -> bytes:
    contenido = {
        "proyecto": proyecto.to_dict(),
        "datos": {nombre: _registros(tabla) for nombre, tabla in datos.items()},
    }
    return json.dumps(contenido, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def proyecto_desde_json(origen: bytes | BytesIO) -> tuple[Proyecto, dict[str, pd.DataFrame]]:
    bruto = origen if isinstance(origen, bytes) else origen.read()
    contenido = json.loads(bruto.decode("utf-8"))
    proyecto = Proyecto.from_dict(contenido["proyecto"])
    datos = {nombre: pd.DataFrame(registros) for nombre, registros in contenido["datos"].items()}
    return proyecto, datos
