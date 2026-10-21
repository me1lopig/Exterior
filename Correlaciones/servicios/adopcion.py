"""Reglas de integridad para la seleccion de valores adoptados."""

from __future__ import annotations

import math

import pandas as pd

from modelos.dominio import EstadoResultado


def validar_adopciones(resultados: pd.DataFrame) -> list[str]:
    """Devuelve errores que impiden consolidar la seleccion tecnica."""
    if resultados.empty or "adoptado" not in resultados:
        return []
    errores: list[str] = []
    adoptados = resultados[resultados["adoptado"].fillna(False).astype(bool)]
    for indice, fila in adoptados.iterrows():
        referencia = f"fila {indice + 1} ({fila.get('parametro', 'parametro')})"
        valor = fila.get("valor_adoptado")
        if pd.isna(valor):
            errores.append(f"{referencia}: falta el valor adoptado.")
            continue
        try:
            valor_num = float(valor)
        except (TypeError, ValueError):
            errores.append(f"{referencia}: el valor adoptado no es numerico.")
            continue
        if not math.isfinite(valor_num):
            errores.append(f"{referencia}: el valor adoptado debe ser finito.")
        if valor_num < 0:
            errores.append(f"{referencia}: el valor adoptado no puede ser negativo.")
        justificacion_raw = fila.get("justificacion")
        justificacion = "" if pd.isna(justificacion_raw) else str(justificacion_raw).strip()
        if not justificacion:
            errores.append(f"{referencia}: la justificacion tecnica es obligatoria.")
        if fila.get("estado") == EstadoResultado.NO_VALIDO.value:
            errores.append(f"{referencia}: no se puede adoptar un resultado no valido.")
        minimo = fila.get("minimo")
        maximo = fila.get("maximo")
        if not pd.isna(minimo) and valor_num < float(minimo):
            errores.append(f"{referencia}: el valor queda por debajo del intervalo calculado.")
        if not pd.isna(maximo) and valor_num > float(maximo):
            errores.append(f"{referencia}: el valor supera el intervalo calculado.")

    claves = [c for c in ("grupo", "unidad_geotecnica", "parametro") if c in adoptados]
    if claves and not adoptados.empty:
        duplicados = adoptados.groupby(claves, dropna=False).size()
        for clave, cantidad in duplicados[duplicados > 1].items():
            errores.append(f"Solo puede adoptarse un resultado por {dict(zip(claves, clave if isinstance(clave, tuple) else (clave,)))}.")
    return errores
