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
        for indice, (actual, siguiente) in enumerate(zip(filas[:-1], filas[1:]), start=1):
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
                    interfaz_id=f"{sondeo_id}:I{indice:03d}",
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
            vertices=sorted(unicos.values(), key=lambda punto: punto.s_m),
        )
        contacto.ordenar()
        contactos.append(contacto)
    return contactos


def interfaces_observadas(
    sondeos_proyectados: pd.DataFrame,
    intervalos: pd.DataFrame,
) -> dict[str, tuple[float, float]]:
    """Devuelve la posicion vigente de cada interfaz identificada por sondeo y profundidad."""
    sondeos = sondeos_proyectados.set_index("sondeo_id")
    resultado: dict[str, tuple[float, float]] = {}
    for sondeo_id, grupo in intervalos.groupby("sondeo_id"):
        if sondeo_id not in sondeos.index:
            continue
        datos_sondeo = sondeos.loc[sondeo_id]
        for indice, tramo in enumerate(
            list(grupo.sort_values("desde_m").itertuples(index=False))[1:], start=1
        ):
            profundidad = float(tramo.desde_m)
            interfaz_id = f"{sondeo_id}:I{indice:03d}"
            resultado[interfaz_id] = (
                float(datos_sondeo["s_m"]),
                float(datos_sondeo["cota_boca_m"]) - profundidad,
            )
    return resultado


def vinculos_observados_desactualizados(
    contactos: Iterable[Contacto],
    interfaces: dict[str, tuple[float, float]],
    tolerancia_m: float = 1e-4,
) -> list[tuple[str, int, str]]:
    """Localiza vertices vinculados cuya interfaz falta o ha cambiado de posicion."""
    resultado: list[tuple[str, int, str]] = []
    for contacto in contactos:
        for indice, vertice in enumerate(contacto.vertices):
            if not vertice.interfaz_id:
                continue
            posicion = interfaces.get(vertice.interfaz_id)
            if posicion is None:
                resultado.append((contacto.contacto_id, indice, "interfaz no disponible"))
                continue
            diferencia = float(np.hypot(vertice.s_m - posicion[0], vertice.z_m - posicion[1]))
            if diferencia > tolerancia_m:
                resultado.append((contacto.contacto_id, indice, f"desplazamiento {diferencia:.3f} m"))
    return resultado


def actualizar_vinculos_observados(
    contactos: Iterable[Contacto],
    interfaces: dict[str, tuple[float, float]],
) -> int:
    """Actualiza explicitamente vertices vinculados y devuelve el numero modificado."""
    actualizados = 0
    for contacto in contactos:
        if contacto.bloqueado:
            continue
        for vertice in contacto.vertices:
            posicion = interfaces.get(vertice.interfaz_id)
            if not vertice.interfaz_id or posicion is None:
                continue
            if vertice.s_m != posicion[0] or vertice.z_m != posicion[1]:
                vertice.s_m, vertice.z_m = posicion
                actualizados += 1
    return actualizados


def interpolar_contacto(contacto: Contacto, estaciones: np.ndarray) -> np.ndarray:
    """Interpola linealmente sin extrapolar fuera de los vertices."""
    if len(contacto.vertices) < 2:
        return np.full_like(estaciones, np.nan, dtype=float)
    x = np.array([p.s_m for p in contacto.vertices], dtype=float)
    z = np.array([p.z_m for p in contacto.vertices], dtype=float)
    orden = np.argsort(x)
    x, z = x[orden], z[orden]
    x, indices = np.unique(x, return_index=True)
    z = z[indices]
    if len(x) < 2:
        return np.full_like(estaciones, np.nan, dtype=float)
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
        inicio = max(min(p.s_m for p in superior.vertices), min(p.s_m for p in inferior.vertices))
        fin = min(max(p.s_m for p in superior.vertices), max(p.s_m for p in inferior.vertices))
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
                "interfaz_id": punto.interfaz_id,
            }
            for punto in contacto.vertices
        ],
        columns=["s_m", "z_m", "origen", "referencia", "interfaz_id"],
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
                interfaz_id=str(getattr(fila, "interfaz_id", "")),
            )
        )
    contacto.vertices = vertices
    contacto.ordenar()
    return contacto
