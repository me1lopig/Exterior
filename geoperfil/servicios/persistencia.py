"""Serializacion trazable del proyecto y sus tablas."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pandas as pd

from perfil_geologico.modelos.dominio import Proyecto
from perfil_geologico.servicios.datos_demo import crear_datos_demo
from perfil_geologico.utiles.validacion import validar_datos


def _registros(tabla: pd.DataFrame) -> list[dict[str, Any]]:
    limpia = tabla.where(pd.notna(tabla), None)
    return limpia.to_dict(orient="records")


def proyecto_a_json(proyecto: Proyecto, datos: dict[str, pd.DataFrame]) -> bytes:
    contenido = {
        "proyecto": proyecto.to_dict(),
        "datos": {nombre: _registros(tabla) for nombre, tabla in datos.items()},
        "columnas_datos": {nombre: list(tabla.columns) for nombre, tabla in datos.items()},
    }
    return json.dumps(contenido, ensure_ascii=False, indent=2, default=str).encode("utf-8")


def proyecto_desde_json(origen: bytes | BytesIO) -> tuple[Proyecto, dict[str, pd.DataFrame]]:
    bruto = origen if isinstance(origen, bytes) else origen.read()
    contenido = json.loads(bruto.decode("utf-8"))
    proyecto = Proyecto.from_dict(contenido["proyecto"])
    modelos = crear_datos_demo()
    almacen = contenido["datos"]
    columnas_guardadas = contenido.get("columnas_datos", {})
    datos = {}
    for nombre, tabla_modelo in modelos.items():
        if nombre not in almacen:
            if nombre == "Eje":
                datos[nombre] = tabla_modelo.iloc[0:0].copy()
                continue
            raise ValueError(f"El proyecto no contiene la tabla {nombre}.")
        columnas = columnas_guardadas.get(nombre, list(tabla_modelo.columns))
        datos[nombre] = pd.DataFrame(almacen[nombre], columns=columnas)
    errores, _ = validar_datos(datos["Sondeos"], datos["Intervalos"], datos["Unidades"],
                              datos["Ensayos_DPSH"], datos["Lecturas_DPSH"])
    if errores:
        raise ValueError("Datos del proyecto incorrectos: " + "; ".join(errores))
    return proyecto, datos
