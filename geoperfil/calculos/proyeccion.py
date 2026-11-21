"""Proyeccion de reconocimientos sobre un eje poligonal 2D."""

from __future__ import annotations

import numpy as np
import pandas as pd


def validar_eje(eje: pd.DataFrame) -> None:
    """Valida que el eje contenga al menos dos puntos distintos."""
    requeridas = {"x_m", "y_m"}
    if not requeridas.issubset(eje.columns):
        raise ValueError("El eje debe contener las columnas x_m e y_m.")
    if len(eje) < 2:
        raise ValueError("El eje debe contener al menos dos puntos.")
    coordenadas = eje[["x_m", "y_m"]].to_numpy(dtype=float)
    if not np.isfinite(coordenadas).all():
        raise ValueError("El eje contiene coordenadas no numericas.")
    if np.all(np.linalg.norm(np.diff(coordenadas, axis=0), axis=1) == 0.0):
        raise ValueError("El eje no puede tener longitud nula.")


def proyectar_puntos(puntos: pd.DataFrame, eje: pd.DataFrame) -> pd.DataFrame:
    """Proyecta puntos XY sobre la polilinea y devuelve abscisa y separacion.

    La distancia lateral es positiva a la izquierda del segmento orientado y
    negativa a la derecha. La seleccion del segmento se basa en distancia minima.
    """
    validar_eje(eje)
    if not {"x_m", "y_m"}.issubset(puntos.columns):
        raise ValueError("Los puntos deben contener las columnas x_m e y_m.")

    linea = eje[["x_m", "y_m"]].to_numpy(dtype=float)
    origenes = linea[:-1]
    vectores = linea[1:] - linea[:-1]
    longitudes2 = np.einsum("ij,ij->i", vectores, vectores)
    validos = longitudes2 > 0.0
    origenes = origenes[validos]
    vectores = vectores[validos]
    longitudes2 = longitudes2[validos]
    longitudes = np.sqrt(longitudes2)
    acumuladas = np.concatenate(([0.0], np.cumsum(longitudes)))[:-1]

    xy = puntos[["x_m", "y_m"]].to_numpy(dtype=float)
    if not np.isfinite(xy).all():
        raise ValueError("Los reconocimientos contienen coordenadas no numericas.")

    relativos = xy[:, None, :] - origenes[None, :, :]
    t = np.einsum("nsi,si->ns", relativos, vectores) / longitudes2[None, :]
    t = np.clip(t, 0.0, 1.0)
    proyectados = origenes[None, :, :] + t[:, :, None] * vectores[None, :, :]
    diferencias = xy[:, None, :] - proyectados
    distancias2 = np.einsum("nsi,nsi->ns", diferencias, diferencias)
    segmento = np.argmin(distancias2, axis=1)
    fila = np.arange(len(xy))
    t_mejor = t[fila, segmento]
    proyeccion = proyectados[fila, segmento]
    abscisa = acumuladas[segmento] + t_mejor * longitudes[segmento]
    vector = vectores[segmento]
    diferencia = xy - proyeccion
    cruz = vector[:, 0] * diferencia[:, 1] - vector[:, 1] * diferencia[:, 0]
    separacion = np.sqrt(distancias2[fila, segmento]) * np.sign(cruz)

    resultado = puntos.copy()
    resultado["s_m"] = abscisa
    resultado["distancia_eje_m"] = separacion
    resultado["x_proyectada_m"] = proyeccion[:, 0]
    resultado["y_proyectada_m"] = proyeccion[:, 1]
    return resultado


def longitud_eje(eje: pd.DataFrame) -> float:
    validar_eje(eje)
    coordenadas = eje[["x_m", "y_m"]].to_numpy(dtype=float)
    return float(np.linalg.norm(np.diff(coordenadas, axis=0), axis=1).sum())
