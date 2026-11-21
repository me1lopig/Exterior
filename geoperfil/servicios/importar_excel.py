"""Lectura y generacion de la plantilla Excel."""

from __future__ import annotations

from io import BytesIO
import json
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


def _unidad_columna(nombre: str) -> str:
    if nombre.endswith("_m") or nombre in {"s_m", "z_m"}:
        return "m"
    if nombre.endswith("_kpa"):
        return "kPa"
    if nombre.endswith("_kn_m3"):
        return "kN/m3"
    if nombre.endswith("_pct"):
        return "%"
    if nombre.endswith("_grados"):
        return "grados"
    if nombre.endswith("_mg_kg"):
        return "mg/kg"
    return ""


def datos_a_excel(datos: dict[str, pd.DataFrame], proyecto=None, manifest: dict | None = None) -> bytes:
    """Exporta datos y, si se proporciona, toda la interpretacion del proyecto."""
    salida = BytesIO()
    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        for nombre, tabla in datos.items():
            tabla.to_excel(writer, sheet_name=nombre[:31], index=False)
        if proyecto is not None:
            proyecto_simple = {
                clave: valor for clave, valor in proyecto.to_dict().items()
                if clave not in {"contactos", "zonas", "hipotesis", "capas"}
            }
            pd.DataFrame([
                {"campo": clave, "valor": json.dumps(valor, ensure_ascii=False)
                 if isinstance(valor, (dict, list)) else valor}
                for clave, valor in proyecto_simple.items()
            ]).to_excel(writer, sheet_name="Proyecto", index=False)
            pd.DataFrame([
                {
                    "contacto_id": contacto.contacto_id,
                    "nombre": contacto.nombre,
                    "unidad_superior": contacto.unidad_superior,
                    "unidad_inferior": contacto.unidad_inferior,
                    "color": contacto.color,
                    "visible": contacto.visible,
                    "bloqueado": contacto.bloqueado,
                    "evidencia": contacto.evidencia,
                    "incertidumbre_m": contacto.incertidumbre_m,
                }
                for contacto in proyecto.contactos
            ], columns=[
                "contacto_id", "nombre", "unidad_superior", "unidad_inferior",
                "color", "visible", "bloqueado", "evidencia", "incertidumbre_m",
            ]).to_excel(writer, sheet_name="Contactos", index=False)
            pd.DataFrame([
                {
                    "contacto_id": contacto.contacto_id,
                    "orden": orden,
                    "s_m": punto.s_m,
                    "z_m": punto.z_m,
                    "origen": punto.origen,
                    "referencia": punto.referencia,
                    "interfaz_id": punto.interfaz_id,
                }
                for contacto in proyecto.contactos
                for orden, punto in enumerate(contacto.vertices, start=1)
            ], columns=[
                "contacto_id", "orden", "s_m", "z_m", "origen",
                "referencia", "interfaz_id",
            ]).to_excel(writer, sheet_name="Vertices_Contactos", index=False)
            pd.DataFrame([
                {clave: valor for clave, valor in zona.items()
                 if clave not in {"coordenadas", "huecos"}}
                for zona in proyecto.zonas
            ]).to_excel(writer, sheet_name="Zonas", index=False)
            anillos = []
            for zona in proyecto.zonas:
                for tipo, numero, anillo in [
                    ("exterior", 0, zona.get("coordenadas", [])),
                    *(("hueco", indice, hueco) for indice, hueco in enumerate(zona.get("huecos", []), start=1)),
                ]:
                    for orden, punto in enumerate(anillo, start=1):
                        anillos.append({
                            "zona_id": zona.get("zona_id", ""), "tipo_anillo": tipo,
                            "numero_anillo": numero, "orden": orden,
                            "s_m": punto[0], "z_m": punto[1],
                        })
            pd.DataFrame(anillos, columns=[
                "zona_id", "tipo_anillo", "numero_anillo", "orden", "s_m", "z_m",
            ]).to_excel(writer, sheet_name="Anillos_Zonas", index=False)
            pd.DataFrame([
                {
                    "nombre": item.get("nombre", ""),
                    "creada": item.get("creada", ""),
                    "contactos_json": json.dumps(item.get("contactos", []), ensure_ascii=False),
                    "zonas_json": json.dumps(item.get("zonas", []), ensure_ascii=False),
                }
                for item in proyecto.hipotesis
            ], columns=["nombre", "creada", "contactos_json", "zonas_json"]).to_excel(
                writer, sheet_name="Hipotesis", index=False)
            pd.DataFrame([
                {"grupo": "capas", "clave": clave, "valor": valor}
                for clave, valor in proyecto.capas.items()
            ] + [
                {"grupo": "texto", "clave": "general_pt", "valor": proyecto.texto_general_pt},
                {"grupo": "texto", "clave": "ensayos_pt", "valor": proyecto.texto_ensayos_pt},
                {"grupo": "texto", "clave": "guitarra_pt", "valor": proyecto.texto_guitarra_pt},
            ]).to_excel(writer, sheet_name="Configuracion", index=False)
        esquema = []
        for tabla_nombre, tabla in datos.items():
            for columna in tabla.columns:
                esquema.append({
                    "tabla": tabla_nombre, "columna": columna,
                    "tipo_origen": str(tabla[columna].dtype),
                    "unidad": _unidad_columna(str(columna)),
                })
        pd.DataFrame(esquema).to_excel(writer, sheet_name="Esquema", index=False)
        if manifest is not None:
            pd.DataFrame([
                {"campo": clave, "valor": json.dumps(valor, ensure_ascii=False)
                 if isinstance(valor, (dict, list)) else valor}
                for clave, valor in manifest.items()
            ]).to_excel(writer, sheet_name="Manifest", index=False)
    return salida.getvalue()
