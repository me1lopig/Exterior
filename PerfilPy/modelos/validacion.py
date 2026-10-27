from __future__ import annotations

import math

import pandas as pd

from modelos.datos import DatosProyecto, EstadoNF, Incidencia, Severidad


def _blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip()) or pd.isna(value)


def _number(value: object) -> float | None:
    if _blank(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _required_text(
    issues: list[Incidencia], table: str, frame: pd.DataFrame, columns: tuple[str, ...]
) -> None:
    for idx, row in frame.iterrows():
        for column in columns:
            if _blank(row.get(column)):
                issues.append(
                    Incidencia(Severidad.ERROR, table, int(idx) + 2, column, "Valor obligatorio vacio.")
                )


def _numeric(
    issues: list[Incidencia],
    table: str,
    frame: pd.DataFrame,
    columns: tuple[str, ...],
    *,
    nonnegative: bool = False,
) -> None:
    for idx, row in frame.iterrows():
        for column in columns:
            value = _number(row.get(column))
            if value is None:
                issues.append(
                    Incidencia(Severidad.ERROR, table, int(idx) + 2, column, "Debe ser un numero valido.")
                )
            elif nonnegative and value < 0:
                issues.append(
                    Incidencia(Severidad.ERROR, table, int(idx) + 2, column, "No puede ser negativo.")
                )


def validar_datos(datos: DatosProyecto, perfiles_activos: list[str] | None = None) -> list[Incidencia]:
    issues: list[Incidencia] = []
    profiles = datos.perfiles
    if perfiles_activos is not None:
        profiles = profiles[profiles["perfil"].isin(perfiles_activos)]

    _required_text(issues, "Perfiles", profiles, ("perfil", "estacion"))
    _numeric(issues, "Perfiles", profiles, ("distancia_m", "cota_m"))
    _required_text(issues, "Litologia", datos.litologia, ("sondeo",))
    _numeric(
        issues,
        "Litologia",
        datos.litologia,
        ("profundidad_inicial_m", "profundidad_final_m"),
        nonnegative=True,
    )
    _required_text(issues, "DPSH", datos.dpsh, ("ensayo",))
    _numeric(issues, "DPSH", datos.dpsh, ("profundidad_m", "golpes"), nonnegative=True)
    _required_text(issues, "Ensayos", datos.ensayos, ("sondeo", "tipo"))
    _numeric(issues, "Ensayos", datos.ensayos, ("profundidad_m",), nonnegative=True)
    if not datos.ugeo.empty:
        _required_text(issues, "UGEO", datos.ugeo, ("sondeo", "codigo"))
        _numeric(
            issues,
            "UGEO",
            datos.ugeo,
            ("profundidad_inicial_m", "profundidad_final_m"),
            nonnegative=True,
        )

    for table_name, frame in (("Litologia", datos.litologia), ("UGEO", datos.ugeo)):
        if frame.empty:
            continue
        for idx, row in frame.iterrows():
            start = _number(row.get("profundidad_inicial_m"))
            end = _number(row.get("profundidad_final_m"))
            if start is not None and end is not None and end <= start:
                issues.append(
                    Incidencia(
                        Severidad.ERROR,
                        table_name,
                        int(idx) + 2,
                        "profundidad_final_m",
                        "La profundidad final debe ser mayor que la inicial.",
                    )
                )

        for name, group in frame.groupby("sondeo", sort=False):
            ordered = group.copy()
            ordered["_start"] = pd.to_numeric(ordered["profundidad_inicial_m"], errors="coerce")
            ordered["_end"] = pd.to_numeric(ordered["profundidad_final_m"], errors="coerce")
            ordered = ordered.dropna(subset=["_start", "_end"]).sort_values("_start")
            previous_end: float | None = None
            for idx, row in ordered.iterrows():
                start = float(row["_start"])
                if previous_end is not None and start < previous_end:
                    issues.append(
                        Incidencia(
                            Severidad.ERROR,
                            table_name,
                            int(idx) + 2,
                            "profundidad_inicial_m",
                            f"El intervalo se solapa con el anterior en {name}.",
                        )
                    )
                previous_end = max(previous_end or float("-inf"), float(row["_end"]))

    known = set(datos.litologia.get("sondeo", pd.Series(dtype=str)).astype(str))
    known |= set(datos.dpsh.get("ensayo", pd.Series(dtype=str)).astype(str))
    for idx, row in profiles.iterrows():
        station = str(row.get("estacion", "")).strip()
        station_type = str(row.get("tipo", "")).strip()
        if station_type != "Punto de terreno" and station not in known:
            issues.append(
                Incidencia(
                    Severidad.AVISO,
                    "Perfiles",
                    int(idx) + 2,
                    "estacion",
                    f"La estacion {station!r} no tiene sondeo ni DPSH asociado.",
                )
            )

    for profile, group in profiles.groupby("perfil", sort=False):
        distances = pd.to_numeric(group["distancia_m"], errors="coerce")
        if distances.duplicated().any():
            issues.append(
                Incidencia(
                    Severidad.AVISO,
                    "Perfiles",
                    None,
                    "distancia_m",
                    f"El perfil {profile!r} contiene distancias duplicadas.",
                )
            )
        if not distances.dropna().is_monotonic_increasing:
            issues.append(
                Incidencia(
                    Severidad.AVISO,
                    "Perfiles",
                    None,
                    "distancia_m",
                    f"El perfil {profile!r} no esta ordenado por distancia; se ordenara al dibujar.",
                )
            )

    borehole_depths = (
        datos.litologia.assign(
            _depth=pd.to_numeric(datos.litologia["profundidad_final_m"], errors="coerce")
        )
        .groupby("sondeo")["_depth"]
        .max()
        .to_dict()
        if not datos.litologia.empty
        else {}
    )
    for idx, row in datos.ensayos.iterrows():
        name = str(row.get("sondeo", ""))
        depth = _number(row.get("profundidad_m"))
        max_depth = borehole_depths.get(name)
        if depth is not None and max_depth is not None and depth > float(max_depth) + 1e-9:
            issues.append(
                Incidencia(
                    Severidad.AVISO,
                    "Ensayos",
                    int(idx) + 2,
                    "profundidad_m",
                    f"El ensayo queda por debajo de la profundidad litologica de {name}.",
                )
            )

    for idx, row in datos.dpsh.iterrows():
        blows = _number(row.get("golpes"))
        if blows is not None and blows > 100:
            issues.append(
                Incidencia(
                    Severidad.AVISO,
                    "DPSH",
                    int(idx) + 2,
                    "golpes",
                    "El valor supera 100; el grafico DXF lo limita al extremo de rechazo.",
                )
            )
    allowed_nf = {item.value for item in EstadoNF}
    for idx, row in datos.nivel_freatico.iterrows():
        state = str(row.get("estado", ""))
        depth = _number(row.get("profundidad_m"))
        if state not in allowed_nf:
            issues.append(
                Incidencia(Severidad.ERROR, "Nivel freatico", int(idx) + 2, "estado", "Estado no reconocido.")
            )
        elif state == EstadoNF.REVISAR.value:
            issues.append(
                Incidencia(
                    Severidad.ERROR,
                    "Nivel freatico",
                    int(idx) + 2,
                    "estado",
                    "El cero importado es ambiguo: indique si fue detectado o no.",
                )
            )
        elif state == EstadoNF.DETECTADO.value and (depth is None or depth < 0):
            issues.append(
                Incidencia(
                    Severidad.ERROR,
                    "Nivel freatico",
                    int(idx) + 2,
                    "profundidad_m",
                    "Un nivel detectado requiere profundidad mayor o igual que cero.",
                )
            )
        elif state == EstadoNF.DETECTADO.value:
            name = str(row.get("sondeo", ""))
            max_depth = borehole_depths.get(name)
            if max_depth is not None and depth is not None and depth > float(max_depth) + 1e-9:
                issues.append(
                    Incidencia(
                        Severidad.AVISO,
                        "Nivel freatico",
                        int(idx) + 2,
                        "profundidad_m",
                        f"El nivel indicado queda por debajo de la profundidad investigada en {name}.",
                    )
                )
        elif state in {EstadoNF.NO_DETECTADO.value, EstadoNF.NO_MEDIDO.value} and depth is not None:
            issues.append(
                Incidencia(
                    Severidad.AVISO,
                    "Nivel freatico",
                    int(idx) + 2,
                    "profundidad_m",
                    "La profundidad se ignorara para este estado.",
                )
            )

    return issues


def incidencias_dataframe(issues: list[Incidencia]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "severidad": issue.severidad.value,
                "tabla": issue.tabla,
                "fila": issue.fila,
                "campo": issue.campo,
                "mensaje": issue.mensaje,
            }
            for issue in issues
        ]
    )
