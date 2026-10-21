"""Inicializacion y operaciones del estado de sesion Streamlit."""

from __future__ import annotations

from uuid import uuid4

import pandas as pd


ESQUEMAS: dict[str, list[str]] = {
    "spt": [
        "registro_id", "grupo", "punto", "profundidad_m", "unidad_geotecnica",
        "tipo_suelo", "tipo_n", "n", "porcentaje_mayor_20mm", "observaciones",
    ],
    "molinete": [
        "registro_id", "grupo", "punto", "profundidad_m", "unidad_geotecnica",
        "tipo_suelo", "diametro_m", "altura_m", "torque_pico_kNm", "torque_rem_kNm", "observaciones",
    ],
    "sismica": [
        "registro_id", "grupo", "punto", "profundidad_m", "unidad_geotecnica",
        "Vs_m_s", "Vp_m_s", "gamma_kN_m3", "observaciones",
    ],
    "dmt": [
        "registro_id", "grupo", "punto", "profundidad_m", "unidad_geotecnica",
        "tipo_suelo", "cementado", "p0_kPa", "p1_kPa", "u0_kPa", "sigma_v_eff_kPa", "observaciones",
    ],
    "pmt": [
        "registro_id", "grupo", "punto", "profundidad_m", "unidad_geotecnica",
        "tipo_suelo", "EM_MPa", "plM_MPa", "pf_MPa", "alpha", "p0h_MPa", "observaciones",
    ],
    "placa": [
        "registro_id", "grupo", "punto", "profundidad_m", "unidad_geotecnica",
        "Ev1_MPa", "Ev2_MPa", "K30_MN_m3", "observaciones",
    ],
    "permeabilidad": [
        "registro_id", "grupo", "punto", "profundidad_m", "unidad_geotecnica",
        "tipo_ensayo", "k_m_s", "observaciones",
    ],
}


def dataframe_vacio(tipo: str) -> pd.DataFrame:
    return pd.DataFrame(columns=ESQUEMAS[tipo])


def normalizar_ids(df: pd.DataFrame) -> pd.DataFrame:
    resultado = df.copy()
    if "registro_id" not in resultado:
        resultado.insert(0, "registro_id", "")
    for indice in resultado.index:
        valor = resultado.at[indice, "registro_id"]
        if pd.isna(valor) or not str(valor).strip():
            resultado.at[indice, "registro_id"] = uuid4().hex[:10].upper()
    return resultado


def inicializar_estado(state: object) -> None:
    valores = {
        "proyecto_nombre": "Proyecto geotecnico",
        "proyecto_localizacion": "",
        "grupos": [{"id": "G01", "nombre": "Sondeo S-1", "ensayo": "SPT"}],
        "resultados": pd.DataFrame(),
    }
    for clave, valor in valores.items():
        if clave not in state:
            state[clave] = valor
    for tipo in ESQUEMAS:
        clave = f"datos_{tipo}"
        if clave not in state:
            state[clave] = dataframe_vacio(tipo)
