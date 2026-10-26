"""Polygonizacion topologica del perfil a partir de contactos dibujados."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

import numpy as np
import pandas as pd

from perfil_geologico.modelos.dominio import Contacto


TRAMAS = (
    "sin_trama",
    "horizontal",
    "vertical",
    "diagonal_45",
    "diagonal_135",
    "cruzada",
    "puntos",
    "grava",
    "roca",
)


def linea_terreno(sondeos_proyectados: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Obtiene una linea de terreno ordenada a partir de las bocas."""
    terreno = (
        sondeos_proyectados.groupby("s_m", as_index=False)["cota_boca_m"]
        .mean()
        .sort_values("s_m")
    )
    return terreno["s_m"].to_numpy(float), terreno["cota_boca_m"].to_numpy(float)


def construir_zonas(
    sondeos_proyectados: pd.DataFrame,
    contactos: Iterable[Contacto],
    zonas_previas: list[dict] | None = None,
    margen_inferior_m: float = 2.0,
) -> tuple[list[dict], list[str]]:
    """Divide el dominio terreno-base mediante la red de contactos.

    Los extremos de un contacto deben alcanzar el contorno o coincidir con otro
    contacto para crear caras cerradas. Shapely realiza el noding de cruces.
    """
    try:
        from shapely.geometry import LineString, Point, Polygon
        from shapely.ops import polygonize, unary_union
    except ImportError as exc:
        raise RuntimeError("La generacion de zonas requiere Shapely >= 2.0.") from exc

    if sondeos_proyectados.empty:
        return [], ["No hay sondeos proyectados para definir el dominio."]
    s_terreno, z_terreno = linea_terreno(sondeos_proyectados)
    if len(s_terreno) < 2:
        return [], ["Se necesitan al menos dos bocas en abscisas distintas."]
    base = float(
        (sondeos_proyectados["cota_boca_m"] - sondeos_proyectados["profundidad_m"]).min()
        - margen_inferior_m
    )
    contorno = [*zip(s_terreno, z_terreno), (s_terreno[-1], base), (s_terreno[0], base)]
    dominio = Polygon(contorno)
    if not dominio.is_valid or dominio.area <= 0:
        raise ValueError("El terreno y la base no forman un dominio geologico valido.")
    lineas = [dominio.boundary]
    lineas_contactos: list[tuple[Contacto, object]] = []
    contactos_validos = 0
    avisos: list[str] = []
    for contacto in contactos:
        if len(contacto.vertices) < 2:
            continue
        coords = [(p.s_m, p.z_m) for p in contacto.vertices]
        linea = LineString(coords)
        if linea.length <= 0:
            continue
        if not linea.is_simple:
            avisos.append(f"El contacto '{contacto.nombre}' se autointerseca.")
        recortada = linea.intersection(dominio)
        if not recortada.is_empty:
            lineas.append(recortada)
            lineas_contactos.append((contacto, recortada))
            contactos_validos += 1

    tolerancia = max(float(dominio.length) * 1e-6, 1e-5)
    extremos_abiertos: list[str] = []
    for contacto, linea in lineas_contactos:
        if linea.geom_type != "LineString" or linea.is_closed:
            continue
        otras = [dominio.boundary, *(otra for otro, otra in lineas_contactos if otro is not contacto)]
        for extremo in (Point(linea.coords[0]), Point(linea.coords[-1])):
            if min(extremo.distance(otra) for otra in otras) > tolerancia:
                extremos_abiertos.append(contacto.nombre)
                break
    if extremos_abiertos:
        nombres = ", ".join(sorted(set(extremos_abiertos)))
        avisos.append(f"Contactos con extremos libres que no cierran zonas: {nombres}.")

    for indice, (contacto_a, linea_a) in enumerate(lineas_contactos):
        for contacto_b, linea_b in lineas_contactos[indice + 1:]:
            if linea_a.crosses(linea_b):
                avisos.append(
                    f"Cruce interior entre '{contacto_a.nombre}' y '{contacto_b.nombre}'. "
                    "Revise si corresponde a una union geologica."
                )
    red = unary_union(lineas)
    caras = [poligono for poligono in polygonize(red) if dominio.covers(poligono.representative_point())]
    caras.sort(key=lambda p: (-p.centroid.y, p.centroid.x))
    area_minima = max(float(dominio.area) * 1e-6, 1e-4)
    caras_pequenas = sum(poligono.area < area_minima for poligono in caras)
    if caras_pequenas:
        avisos.append(
            f"Se han detectado {caras_pequenas} zonas de area grafica muy pequena; "
            "revise vertices casi coincidentes."
        )

    previas_geometrias = []
    for zona in zonas_previas or []:
        coords = zona.get("coordenadas", [])
        if len(coords) >= 3:
            poligono = Polygon(coords, holes=zona.get("huecos", []))
            if poligono.is_valid:
                previas_geometrias.append((zona, poligono))

    zonas: list[dict] = []
    for indice, poligono in enumerate(caras, start=1):
        punto = poligono.representative_point()
        anterior = _mejor_asignacion(poligono, punto, previas_geometrias)
        coordenadas = [[round(float(x), 6), round(float(y), 6)] for x, y in poligono.exterior.coords[:-1]]
        huecos = [
            [[round(float(x), 6), round(float(y), 6)] for x, y in anillo.coords[:-1]]
            for anillo in poligono.interiors
        ]
        huella = hashlib.sha1(repr(coordenadas).encode("utf-8")).hexdigest()[:10]
        zonas.append(
            {
                "zona_id": f"Z{indice:02d}-{huella}",
                "etiqueta": f"Z{indice:02d}",
                "coordenadas": coordenadas,
                "huecos": huecos,
                "unidad_id": anterior.get("unidad_id", "") if anterior else "",
                "trama": anterior.get("trama", "sin_trama") if anterior else "sin_trama",
                "color": anterior.get("color", "#D9DDE2") if anterior else "#D9DDE2",
                "area_m2": round(float(poligono.area), 3),
                "centro_s_m": round(float(punto.x), 3),
                "centro_z_m": round(float(punto.y), 3),
            }
        )

    if contactos_validos and len(caras) <= 1:
        avisos.append(
            "Los contactos no dividen el dominio. Ajuste sus extremos al contorno o a otros contactos."
        )
    sin_asignar = sum(not zona["unidad_id"] for zona in zonas)
    if sin_asignar:
        avisos.append(f"Hay {sin_asignar} zonas sin unidad asignada.")
    return zonas, avisos


def _mejor_asignacion(poligono, punto, previas_geometrias: list[tuple[dict, object]]) -> dict | None:
    """Conserva la unidad solo cuando la cara geometrica permanece igual.

    Al dividir una zona, las nuevas caras quedan sin clasificar: no se debe
    heredar una unidad sin una decision del geologo.
    """
    for zona, geometria in previas_geometrias:
        if not poligono.intersects(geometria):
            continue
        union = poligono.union(geometria).area
        if union > 0 and poligono.symmetric_difference(geometria).area / union < 1e-7:
            return zona
    return None


def asignar_estilos_zonas(zonas: list[dict], tabla: pd.DataFrame, unidades: pd.DataFrame) -> list[dict]:
    """Aplica unidad y trama desde una tabla editable."""
    colores = dict(zip(unidades["unidad_id"].astype(str), unidades["color"].astype(str)))
    por_id = {str(fila.zona_id): fila for fila in tabla.itertuples(index=False)}
    resultado = []
    for zona in zonas:
        copia = dict(zona)
        fila = por_id.get(str(zona["zona_id"]))
        if fila is not None:
            unidad = str(getattr(fila, "unidad_id", ""))
            trama = str(getattr(fila, "trama", "sin_trama"))
            copia["unidad_id"] = "" if unidad == "nan" else unidad
            copia["trama"] = trama if trama in TRAMAS else "sin_trama"
            copia["color"] = colores.get(copia["unidad_id"], "#D9DDE2")
        resultado.append(copia)
    return resultado


def asignar_lentes_del_borrador(
    zonas: list[dict],
    contactos: Iterable[Contacto],
    unidades: pd.DataFrame,
) -> list[dict]:
    """Asigna provisionalmente la unidad a caras interiores de lentes cerradas."""
    colores = dict(zip(unidades["unidad_id"].astype(str), unidades["color"].astype(str)))
    lentes = []
    for contacto in contactos:
        coordenadas = [(vertice.s_m, vertice.z_m) for vertice in contacto.vertices]
        if len(coordenadas) >= 4 and np.allclose(coordenadas[0], coordenadas[-1]):
            lentes.append((contacto, coordenadas[:-1]))
    resultado = []
    for zona in zonas:
        copia = dict(zona)
        punto = (float(zona["centro_s_m"]), float(zona["centro_z_m"]))
        for contacto, poligono in lentes:
            if _punto_en_poligono(punto, poligono):
                copia["unidad_id"] = contacto.unidad_inferior
                copia["color"] = colores.get(contacto.unidad_inferior, "#D9DDE2")
                copia["trama"] = "sin_trama"
                break
        resultado.append(copia)
    return resultado


def _punto_en_poligono(punto: tuple[float, float], poligono: list[tuple[float, float]]) -> bool:
    """Prueba par-impar para asignaciones graficas sencillas."""
    x, y = punto
    dentro = False
    j = len(poligono) - 1
    for i, (xi, yi) in enumerate(poligono):
        xj, yj = poligono[j]
        if (yi > y) != (yj > y):
            corte = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < corte:
                dentro = not dentro
        j = i
    return dentro
