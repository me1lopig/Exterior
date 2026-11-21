"""Manifest verificable y paquete maestro de entrega de GeoPerfil 2D."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
from typing import Mapping
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd

from perfil_geologico import __version__
from perfil_geologico.modelos.dominio import Proyecto
from perfil_geologico.servicios.persistencia import huella_proyecto


def crear_manifest(
    proyecto: Proyecto,
    datos: Mapping[str, pd.DataFrame],
    archivos: Mapping[str, bytes] | None = None,
) -> dict:
    """Describe el estado exportado y, opcionalmente, cada archivo derivado."""
    manifest = {
        "aplicacion": "GeoPerfil 2D",
        "version_aplicacion": __version__,
        "version_formato": proyecto.version_formato,
        "exportado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sha256_estado_canonico": huella_proyecto(proyecto, dict(datos)),
        "proyecto": {
            "nombre": proyecto.nombre,
            "localizacion": proyecto.localizacion,
            "autor": proyecto.autor,
            "sistema_referencia": proyecto.sistema_referencia,
            "unidades_horizontales": "m",
            "convencion_vertical": "cota positiva hacia arriba; profundidad positiva hacia abajo",
            "escala_horizontal": proyecto.escala_horizontal,
            "escala_vertical": proyecto.escala_vertical,
            "exageracion_vertical": proyecto.exageracion_vertical,
            "extension_modo": proyecto.extension_modo,
            "pk_inicio_m": proyecto.pk_inicio_m,
            "pk_fin_m": proyecto.pk_fin_m,
            "capas": dict(proyecto.capas),
        },
        "recuentos": {nombre: int(len(tabla)) for nombre, tabla in datos.items()},
        "interpretacion": {
            "contactos": len(proyecto.contactos),
            "zonas": len(proyecto.zonas),
            "hipotesis": len(proyecto.hipotesis),
        },
        "archivos": {},
    }
    for nombre, contenido in (archivos or {}).items():
        manifest["archivos"][nombre] = {
            "bytes": len(contenido),
            "sha256": sha256(contenido).hexdigest(),
        }
    return manifest


def manifest_a_json(manifest: dict) -> bytes:
    return json.dumps(
        manifest, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False
    ).encode("utf-8")


def crear_paquete_entrega(
    proyecto: Proyecto,
    datos: Mapping[str, pd.DataFrame],
    archivos: Mapping[str, bytes],
) -> tuple[bytes, dict]:
    """Empaqueta entregables y un manifest que permite verificar cada byte."""
    contenidos = {str(nombre): bytes(valor) for nombre, valor in archivos.items()}
    manifest = crear_manifest(proyecto, datos, contenidos)
    salida = BytesIO()
    with ZipFile(salida, "w", compression=ZIP_DEFLATED, compresslevel=9) as paquete:
        for nombre in sorted(contenidos):
            paquete.writestr(nombre, contenidos[nombre])
        paquete.writestr("manifest.json", manifest_a_json(manifest))
    return salida.getvalue(), deepcopy(manifest)


def verificar_paquete(contenido: bytes) -> list[str]:
    """Devuelve incidencias de integridad; una lista vacía implica coincidencia."""
    incidencias: list[str] = []
    with ZipFile(BytesIO(contenido), "r") as paquete:
        manifest = json.loads(paquete.read("manifest.json").decode("utf-8"))
        for nombre, esperado in manifest.get("archivos", {}).items():
            try:
                datos = paquete.read(nombre)
            except KeyError:
                incidencias.append(f"Falta {nombre}.")
                continue
            if len(datos) != int(esperado["bytes"]):
                incidencias.append(f"Tamaño incorrecto en {nombre}.")
            if sha256(datos).hexdigest() != esperado["sha256"]:
                incidencias.append(f"SHA-256 incorrecto en {nombre}.")
    return incidencias
