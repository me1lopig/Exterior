"""Construccion y comprobacion de contactos geologicos."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from perfil_geologico.modelos.dominio import Contacto, VerticeContacto


def contactos_observados(
    sondeos_proyectados: pd.DataFrame,
    intervalos: pd.DataFrame,
    unidades: pd.DataFrame,
) -> list[Contacto]:
    """Genera contactos iniciales a partir de los muros observados."""
    nombres = dict(zip(unidades["unidad_id"].astype(str), unidades["nombre"].astype(str)))
    colores = dict(zip(unidades["unidad_id"].astype(str), unidades["color"].astype(str)))
    sondeos = sondeos_proyectados.set_index("sondeo_id")
    agrupados: dict[tuple[str, str], list[VerticeContacto]] = {}

    for sondeo_id, grupo in intervalos.groupby("sondeo_id"):
        if sondeo_id not in sondeos.index:
            continue
        filas = list(grupo.sort_values("desde_m").itertuples(index=False))
        datos_sondeo = sondeos.loc[sondeo_id]
        for actual, siguiente in zip(filas[:-1], filas[1:]):
            superior = str(actual.unidad_id)
            inferior = str(siguiente.unidad_id)
            if superior == inferior:
                continue
            z_contacto = float(datos_sondeo["cota_boca_m"]) - float(actual.hasta_m)
            agrupados.setdefault((superior, inferior), []).append(
                VerticeContacto(
                    s_m=float(datos_sondeo["s_m"]),
                    z_m=z_contacto,
                    origen="observado",
                    referencia=str(sondeo_id),
                )
            )

    contactos: list[Contacto] = []
    for (superior, inferior), vertices in agrupados.items():
        # En abscisas coincidentes se conserva el primer dato y se avisa despues.
        unicos = {round(punto.s_m, 6): punto for punto in vertices}
        contacto = Contacto(
            contacto_id=f"techo_{inferior}",
            nombre=f"Techo {nombres.get(inferior, inferior)}",
            unidad_superior=superior,
            unidad_inferior=inferior,
            color=colores.get(inferior, "#334155"),
            vertices=list(unicos.values()),
        )
        contacto.ordenar()
        contactos.append(contacto)
    return contactos


def interpolar_contacto(contacto: Contacto, estaciones: np.ndarray) -> np.ndarray:
    """Interpola linealmente sin extrapolar fuera de los vertices."""
    if len(contacto.vertices) < 2:
        return np.full_like(estaciones, np.nan, dtype=float)
    x = np.array([p.s_m for p in contacto.vertices], dtype=float)
    z = np.array([p.z_m for p in contacto.vertices], dtype=float)
    valores = np.interp(estaciones, x, z)
    valores[(estaciones < x.min()) | (estaciones > x.max())] = np.nan
    return valores


def detectar_cruces(contactos: Iterable[Contacto], muestras: int = 401) -> list[str]:
    """Detecta cruces entre contactos consecutivos en su dominio comun."""
    lista = list(contactos)
    avisos: list[str] = []
    for superior, inferior in zip(lista[:-1], lista[1:]):
        if len(superior.vertices) < 2 or len(inferior.vertices) < 2:
            continue
        inicio = max(superior.vertices[0].s_m, inferior.vertices[0].s_m)
        fin = min(superior.vertices[-1].s_m, inferior.vertices[-1].s_m)
        if fin <= inicio:
            continue
        estaciones = np.linspace(inicio, fin, muestras)
        z_sup = interpolar_contacto(superior, estaciones)
        z_inf = interpolar_contacto(inferior, estaciones)
        if np.any(z_inf > z_sup + 1e-6):
            avisos.append(
                f"Cruce entre '{superior.nombre}' y '{inferior.nombre}' "
                f"en el intervalo {inicio:.1f}-{fin:.1f} m."
            )
    return avisos


def vertices_a_dataframe(contacto: Contacto) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "s_m": punto.s_m,
                "z_m": punto.z_m,
                "origen": punto.origen,
                "referencia": punto.referencia,
            }
            for punto in contacto.vertices
        ],
        columns=["s_m", "z_m", "origen", "referencia"],
    )


def actualizar_vertices(contacto: Contacto, tabla: pd.DataFrame) -> Contacto:
    """Actualiza una polilinea desde la tabla editable."""
    vertices = []
    for fila in tabla.dropna(subset=["s_m", "z_m"]).itertuples(index=False):
        vertices.append(
            VerticeContacto(
                s_m=float(fila.s_m),
                z_m=float(fila.z_m),
                origen=str(getattr(fila, "origen", "interpretado")),
                referencia=str(getattr(fila, "referencia", "")),
            )
        )
    contacto.vertices = vertices
    contacto.ordenar()
    return contacto
