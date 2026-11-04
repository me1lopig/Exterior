"""Serializacion trazable del proyecto y sus tablas."""

from __future__ import annotations

import json
import math
from hashlib import sha256
from datetime import datetime, timezone
from io import BytesIO
from typing import Any

import pandas as pd

from perfil_geologico import __version__
from perfil_geologico.modelos.dominio import Proyecto
from perfil_geologico.servicios.datos_demo import crear_datos_demo
from perfil_geologico.utiles.validacion import validar_datos

FORMATO_ACTUAL = "2.0"


def _registros(tabla: pd.DataFrame) -> list[dict[str, Any]]:
    limpia = tabla.astype(object).where(pd.notna(tabla), None)
    return _normalizar_json(limpia.to_dict(orient="records"))


def _normalizar_json(valor: Any) -> Any:
    """Convierte escalares científicos y no finitos a JSON estándar."""
    if isinstance(valor, dict):
        return {str(clave): _normalizar_json(contenido) for clave, contenido in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_normalizar_json(contenido) for contenido in valor]
    if valor is None or isinstance(valor, (str, bool, int)):
        return valor
    if hasattr(valor, "item"):
        try:
            return _normalizar_json(valor.item())
        except (TypeError, ValueError):
            pass
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else None
    if hasattr(valor, "isoformat"):
        return valor.isoformat()
    return str(valor)


def contenido_canonico(proyecto: Proyecto, datos: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """Estado completo, estable y sin datos volátiles para comparar exportaciones."""
    proyecto.version_formato = FORMATO_ACTUAL
    return {
        "proyecto": _normalizar_json(proyecto.to_dict()),
        "datos": {nombre: _registros(tabla) for nombre, tabla in datos.items()},
        "columnas_datos": {nombre: list(tabla.columns) for nombre, tabla in datos.items()},
        "tipos_datos": {
            nombre: {columna: str(tipo) for columna, tipo in tabla.dtypes.items()}
            for nombre, tabla in datos.items()
        },
    }


def proyecto_canonico_json(proyecto: Proyecto, datos: dict[str, pd.DataFrame]) -> bytes:
    return json.dumps(
        contenido_canonico(proyecto, datos), ensure_ascii=False,
        sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")


def huella_proyecto(proyecto: Proyecto, datos: dict[str, pd.DataFrame]) -> str:
    return sha256(proyecto_canonico_json(proyecto, datos)).hexdigest()


def proyecto_a_json(proyecto: Proyecto, datos: dict[str, pd.DataFrame]) -> bytes:
    estado = contenido_canonico(proyecto, datos)
    contenido = {
        "meta": {
            "aplicacion": "GeoPerfil 2D",
            "version_aplicacion": __version__,
            "version_formato": proyecto.version_formato,
            "guardado_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sha256_estado_canonico": sha256(
                json.dumps(
                    estado, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"), allow_nan=False,
                ).encode("utf-8")
            ).hexdigest(),
        },
        **estado,
    }
    return json.dumps(
        contenido, ensure_ascii=False, indent=2, allow_nan=False
    ).encode("utf-8")


def proyecto_desde_json(origen: bytes | BytesIO) -> tuple[Proyecto, dict[str, pd.DataFrame]]:
    bruto = origen if isinstance(origen, bytes) else origen.read()
    contenido = json.loads(bruto.decode("utf-8"))
    proyecto = Proyecto.from_dict(contenido["proyecto"])
    modelos = crear_datos_demo()
    almacen = contenido["datos"]
    columnas_guardadas = contenido.get("columnas_datos", {})
    tipos_guardados = contenido.get("tipos_datos", {})
    datos = {}
    for nombre, tabla_modelo in modelos.items():
        if nombre not in almacen:
            if nombre == "Eje":
                datos[nombre] = tabla_modelo.iloc[0:0].copy()
                continue
            raise ValueError(f"El proyecto no contiene la tabla {nombre}.")
        columnas = columnas_guardadas.get(nombre, list(tabla_modelo.columns))
        datos[nombre] = pd.DataFrame(almacen[nombre], columns=columnas)
    # Los proyectos antiguos pueden contener esta columna de presentacion, ya retirada.
    if "Unidades" in datos:
        datos["Unidades"] = datos["Unidades"].drop(columns=["observaciones"], errors="ignore")
    # Conserva todas las tablas adicionales de campana, incluidas las vacias.
    for nombre, registros in almacen.items():
        if nombre not in datos:
            if not isinstance(registros, list):
                raise ValueError(f'Tabla {nombre}: contenido incorrecto.')
            columnas = columnas_guardadas.get(nombre)
            if columnas is None:
                columnas = list(registros[0]) if registros else []
            datos[nombre] = pd.DataFrame(registros, columns=columnas)
    for nombre, tipos in tipos_guardados.items():
        if nombre not in datos or not isinstance(tipos, dict):
            continue
        for columna, tipo in tipos.items():
            if columna not in datos[nombre].columns or tipo == "object":
                continue
            try:
                datos[nombre][columna] = datos[nombre][columna].astype(tipo)
            except (TypeError, ValueError):
                # La validacion posterior informara si un tipo numerico esencial
                # no puede recuperarse; tablas auxiliares antiguas siguen siendo legibles.
                pass
    # Migracion sin perdida de proyectos v0.8.0: STA era denominado "origen",
    # pero es realmente un punto topografico que forma parte del terreno.
    if 'Estaciones' in datos and 'tipo_punto' not in datos['Estaciones'].columns:
        estaciones = datos['Estaciones']
        if 'reconocimiento' in estaciones.columns:
            estaciones['tipo_punto'] = estaciones['reconocimiento'].astype(str).str.upper().map(
                lambda identificador: 'terreno' if identificador == 'STA' else 'reconocimiento'
            )
        if 'es_origen' in estaciones.columns:
            estaciones.drop(columns=['es_origen'], inplace=True)
    errores, _ = validar_datos(datos["Sondeos"], datos["Intervalos"], datos["Unidades"],
                              datos["Ensayos_DPSH"], datos["Lecturas_DPSH"])
    if errores:
        raise ValueError("Datos del proyecto incorrectos: " + "; ".join(errores))
    ids_contactos: set[str] = set()
    for contacto in proyecto.contactos:
        if contacto.contacto_id in ids_contactos:
            raise ValueError(f"Identificador de contacto duplicado: {contacto.contacto_id}.")
        ids_contactos.add(contacto.contacto_id)
        # Los formatos anteriores admitian codigos libres en contactos. Se conservan
        # para no perder interpretaciones heredadas; al editar, la interfaz propone
        # exclusivamente las unidades vigentes del catalogo.
    for zona in proyecto.zonas:
        # Se preservan asignaciones historicas aunque el catalogo haya cambiado.
        # La tabla de edicion solo permite seleccionar codigos actuales.
        for anillo in [zona.get("coordenadas", []), *zona.get("huecos", [])]:
            for punto in anillo:
                if len(punto) != 2 or not all(math.isfinite(float(valor)) for valor in punto):
                    raise ValueError(f"La zona {zona.get('zona_id', '?')} contiene coordenadas no válidas.")
    return proyecto, datos
