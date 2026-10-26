"""Construccion y comprobacion de contactos geologicos."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from perfil_geologico.modelos.dominio import Contacto, VerticeContacto


def generar_borrador_geologico(
    sondeos_proyectados: pd.DataFrame,
    intervalos: pd.DataFrame,
    unidades: pd.DataFrame,
) -> tuple[list[Contacto], list[str]]:
    """Propone contactos correlacionables y lentes locales con control lateral.

    Una intercalacion A-B-A que solo aparece en un sondeo se cierra como lente
    exclusivamente si los sondeos contiguos cubren todo el intervalo de cotas
    y registran A. Los acunamientos se situan a media distancia y se marcan
    como interpretados; no constituyen una conclusion geologica automatica.
    """
    nombres = dict(zip(unidades["unidad_id"].astype(str), unidades["nombre"].astype(str)))
    colores = dict(zip(unidades["unidad_id"].astype(str), unidades["color"].astype(str)))
    sondeos_ordenados = sondeos_proyectados.sort_values("s_m").reset_index(drop=True)
    sondeos_por_id = sondeos_ordenados.set_index("sondeo_id")
    posiciones = {
        str(fila.sondeo_id): indice
        for indice, fila in enumerate(sondeos_ordenados.itertuples(index=False))
    }
    grupos = {
        str(sondeo_id): grupo.sort_values("desde_m").reset_index(drop=True)
        for sondeo_id, grupo in intervalos.groupby("sondeo_id")
    }
    presencia = {
        unidad: set(
            intervalos.loc[
                intervalos["unidad_id"].astype(str) == unidad, "sondeo_id"
            ].astype(str)
        )
        for unidad in intervalos["unidad_id"].astype(str).unique()
    }
    transiciones_lente: set[tuple[str, int]] = set()
    repeticiones_lente: dict[tuple[str, str], int] = {}
    lentes: list[Contacto] = []
    avisos: list[str] = []

    for sondeo_id, grupo in grupos.items():
        if sondeo_id not in sondeos_por_id.index or len(grupo) < 3:
            continue
        indice_sondeo = posiciones[sondeo_id]
        datos_sondeo = sondeos_por_id.loc[sondeo_id]
        for indice in range(1, len(grupo) - 1):
            superior = str(grupo.iloc[indice - 1]["unidad_id"])
            unidad = str(grupo.iloc[indice]["unidad_id"])
            inferior = str(grupo.iloc[indice + 1]["unidad_id"])
            if superior != inferior or unidad == superior or len(presencia.get(unidad, set())) != 1:
                continue

            profundidad_techo = float(grupo.iloc[indice]["desde_m"])
            profundidad_muro = float(grupo.iloc[indice]["hasta_m"])
            z_techo = float(datos_sondeo["cota_boca_m"]) - profundidad_techo
            z_muro = float(datos_sondeo["cota_boca_m"]) - profundidad_muro
            controles: dict[str, tuple[bool, float | None, str]] = {}
            for direccion, vecino_indice in (
                ("izquierda", indice_sondeo - 1), ("derecha", indice_sondeo + 1)
            ):
                if vecino_indice < 0 or vecino_indice >= len(sondeos_ordenados):
                    controles[direccion] = (False, None, "no existe sondeo contiguo")
                    continue
                vecino = sondeos_ordenados.iloc[vecino_indice]
                vecino_id = str(vecino["sondeo_id"])
                confirmado, motivo = _intervalo_confirmado_en_unidad(
                    vecino, grupos.get(vecino_id, pd.DataFrame()), z_muro, z_techo, superior
                )
                if abs(float(vecino["s_m"]) - float(datos_sondeo["s_m"])) <= 1e-6:
                    confirmado, motivo = False, "abscisa coincidente con el sondeo central"
                controles[direccion] = (confirmado, float(vecino["s_m"]), motivo)

            izquierda, derecha = controles["izquierda"], controles["derecha"]
            if not izquierda[0] or not derecha[0]:
                detalles = "; ".join(
                    f"{lado}: {control[2]}" for lado, control in controles.items() if not control[0]
                )
                avisos.append(
                    f"Unidad local '{nombres.get(unidad, unidad)}' en {sondeo_id} sin extension "
                    f"lateral determinable; no se ha cerrado una lente ({detalles})."
                )
                transiciones_lente.update({(sondeo_id, indice), (sondeo_id, indice + 1)})
                continue

            s_centro = float(datos_sondeo["s_m"])
            s_izquierda = 0.5 * (s_centro + float(izquierda[1]))
            s_derecha = 0.5 * (s_centro + float(derecha[1]))
            z_acunamiento = 0.5 * (z_techo + z_muro)
            vertices = [
                VerticeContacto(s_izquierda, z_acunamiento, "inferido_acunamiento"),
                VerticeContacto(
                    s_centro, z_techo, "observado", sondeo_id, f"{sondeo_id}:I{indice:03d}"
                ),
                VerticeContacto(s_derecha, z_acunamiento, "inferido_acunamiento"),
                VerticeContacto(
                    s_centro, z_muro, "observado", sondeo_id, f"{sondeo_id}:I{indice + 1:03d}"
                ),
                VerticeContacto(s_izquierda, z_acunamiento, "inferido_acunamiento"),
            ]
            clave_lente = (unidad, sondeo_id)
            repeticion = repeticiones_lente.get(clave_lente, 0) + 1
            repeticiones_lente[clave_lente] = repeticion
            sufijo = "" if repeticion == 1 else f"_{repeticion:02d}"
            ordinal = "" if repeticion == 1 else f" ({repeticion})"
            lentes.append(
                Contacto(
                    contacto_id=f"lente_{unidad}_{sondeo_id}{sufijo}",
                    nombre=(
                        f"Lente provisional {nombres.get(unidad, unidad)} - "
                        f"{sondeo_id}{ordinal}"
                    ),
                    unidad_superior=superior,
                    unidad_inferior=unidad,
                    color=colores.get(unidad, "#334155"),
                    vertices=vertices,
                    evidencia="interpretado",
                )
            )
            transiciones_lente.update({(sondeo_id, indice), (sondeo_id, indice + 1)})
            avisos.append(
                f"Lente provisional de '{nombres.get(unidad, unidad)}' en {sondeo_id}: "
                "los acunamientos se han situado a media distancia de los sondeos contiguos."
            )

    agrupados: dict[tuple[str, str], list[VerticeContacto]] = {}
    for sondeo_id, grupo in grupos.items():
        if sondeo_id not in sondeos_por_id.index:
            continue
        datos_sondeo = sondeos_por_id.loc[sondeo_id]
        filas = list(grupo.itertuples(index=False))
        for indice, (actual, siguiente) in enumerate(zip(filas[:-1], filas[1:]), start=1):
            if (sondeo_id, indice) in transiciones_lente:
                continue
            unidad_superior = str(actual.unidad_id)
            unidad_inferior = str(siguiente.unidad_id)
            if unidad_superior == unidad_inferior:
                continue
            agrupados.setdefault((unidad_superior, unidad_inferior), []).append(
                VerticeContacto(
                    s_m=float(datos_sondeo["s_m"]),
                    z_m=float(datos_sondeo["cota_boca_m"]) - float(actual.hasta_m),
                    origen="observado",
                    referencia=sondeo_id,
                    interfaz_id=f"{sondeo_id}:I{indice:03d}",
                )
            )

    contactos: list[Contacto] = []
    identificadores: set[str] = set()
    for (unidad_superior, unidad_inferior), vertices in agrupados.items():
        unicos = {round(punto.s_m, 6): punto for punto in vertices}
        if len(unicos) < 2:
            avisos.append(
                f"Interfaz {unidad_superior}/{unidad_inferior} observada en un solo sondeo; "
                "se conserva como referencia, pero no se genera una polilinea automatica."
            )
            continue
        identificador = f"techo_{unidad_inferior}"
        if identificador in identificadores:
            identificador = f"{identificador}_{unidad_superior}"
        identificadores.add(identificador)
        contacto = Contacto(
            contacto_id=identificador,
            nombre=f"Techo {nombres.get(unidad_inferior, unidad_inferior)}",
            unidad_superior=unidad_superior,
            unidad_inferior=unidad_inferior,
            color=colores.get(unidad_inferior, "#334155"),
            vertices=sorted(unicos.values(), key=lambda punto: punto.s_m),
            evidencia="proyectado",
        )
        contacto.ordenar()
        contactos.append(contacto)
    return [*contactos, *lentes], avisos


def _intervalo_confirmado_en_unidad(
    sondeo: pd.Series,
    intervalos_sondeo: pd.DataFrame,
    z_muro: float,
    z_techo: float,
    unidad_encajante: str,
    tolerancia_m: float = 1e-6,
) -> tuple[bool, str]:
    """Comprueba cobertura continua del intervalo de cotas en la unidad encajante."""
    if intervalos_sondeo.empty:
        return False, "sin estratigrafia"
    cota_boca = float(sondeo["cota_boca_m"])
    cota_fondo = cota_boca - float(sondeo["profundidad_m"])
    if cota_boca < z_techo - tolerancia_m or cota_fondo > z_muro + tolerancia_m:
        return False, "profundidad insuficiente"
    segmentos = []
    for tramo in intervalos_sondeo.itertuples(index=False):
        techo = cota_boca - float(tramo.desde_m)
        muro = cota_boca - float(tramo.hasta_m)
        solape = max(0.0, min(techo, z_techo) - max(muro, z_muro))
        if solape > tolerancia_m:
            segmentos.append((max(muro, z_muro), min(techo, z_techo), str(tramo.unidad_id)))
    cobertura = sum(techo - muro for muro, techo, _ in segmentos)
    if cobertura < (z_techo - z_muro) - tolerancia_m:
        return False, "intervalo no cubierto completamente"
    if any(unidad != unidad_encajante for _, _, unidad in segmentos):
        return False, "la unidad encajante no es continua"
    return True, "ausencia comprobada"


def contactos_observados(
    sondeos_proyectados: pd.DataFrame,
    intervalos: pd.DataFrame,
    unidades: pd.DataFrame,
) -> list[Contacto]:
    """Compatibilidad: devuelve solo los contactos del borrador geologico."""
    contactos, _ = generar_borrador_geologico(sondeos_proyectados, intervalos, unidades)
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
    # Los puntos observados son datos de campo y no pueden modificarse
    # numericamente sin actualizar antes el sondeo de origen.
    observados = {v.interfaz_id: (v.s_m, v.z_m) for v in contacto.vertices
                  if v.origen == "observado" and v.interfaz_id}
    nuevos = {v.interfaz_id: (v.s_m, v.z_m) for v in vertices
              if v.origen == "observado" and v.interfaz_id}
    for referencia, coords in observados.items():
        if referencia not in nuevos or any(abs(a-b) > 1e-8 for a, b in zip(coords, nuevos[referencia])):
            raise ValueError(f"El vertice observado {referencia} esta protegido; modifique el sondeo de origen.")
    temporal = Contacto(
        contacto_id=contacto.contacto_id, nombre=contacto.nombre,
        unidad_superior=contacto.unidad_superior, unidad_inferior=contacto.unidad_inferior,
        vertices=vertices,
    )
    temporal.ordenar()
    contacto.vertices = vertices
    return contacto
