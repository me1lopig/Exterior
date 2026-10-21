"""Despachador de correlaciones para evaluacion tabular."""

from __future__ import annotations

from typing import Any

import pandas as pd

from calculos.errores import ErrorCalculoGeotecnico
from calculos.spt import es_fhwa, indice_compresibilidad_cte, phi_cte_41, tabla_d23
from modelos.dominio import MetodoInterpolacion, Resultado


FACTORES_FHWA = {
    "DEF-ES-SPT-FHWA2002-FINOS": 5.0,
    "DEF-ES-SPT-FHWA2002-ARENA-NC": 10.0,
    "DEF-ES-SPT-FHWA2002-ARENA-OC": 15.0,
}


def _numero(fila: dict[str, Any], clave: str, obligatorio: bool = True) -> float | None:
    valor = fila.get(clave)
    if valor is None or pd.isna(valor) or valor == "":
        if obligatorio:
            raise ErrorCalculoGeotecnico(f"Falta el dato obligatorio: {clave}.")
        return None
    return float(valor)


def evaluar_spt(
    correlacion_id: str,
    fila: dict[str, Any],
    metodo_interpolacion: MetodoInterpolacion,
) -> Resultado:
    n = _numero(fila, "n")
    assert n is not None
    tipo_n = str(fila.get("tipo_n") or "No indicado")
    if correlacion_id == "RES-PHI-SPT-CTE2019-T41":
        gruesos = _numero(fila, "porcentaje_mayor_20mm", obligatorio=False)
        tipo_suelo = str(fila.get("tipo_suelo") or "")
        return phi_cte_41(n, tipo_n, tipo_suelo, gruesos)
    if correlacion_id == "RES-QU-SPT-CTE2019-D23":
        return tabla_d23(n, tipo_n, "qu", metodo_interpolacion, str(fila.get("tipo_suelo") or ""))
    if correlacion_id == "DEF-E-SPT-CTE2019-D23":
        return tabla_d23(n, tipo_n, "E", metodo_interpolacion, str(fila.get("tipo_suelo") or ""))
    if correlacion_id in FACTORES_FHWA:
        return es_fhwa(n, tipo_n, FACTORES_FHWA[correlacion_id], correlacion_id)
    if correlacion_id == "DEF-IC-SPT-CTE2019-F24":
        return indice_compresibilidad_cte(n, tipo_n)
    raise ErrorCalculoGeotecnico(f"Correlacion no implementada: {correlacion_id}.")
