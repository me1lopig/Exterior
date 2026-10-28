"""Tablas para consulta y CSV, con convención de esfuerzos explícita."""
from __future__ import annotations

import pandas as pd
from modelos.geometrias import ResultadoGeometria


def tabla_malla(resultados: list[ResultadoGeometria]) -> pd.DataFrame:
    rows=[]
    for r in resultados:
        rows.append({
            "B (m)": r.b_m,
            "L (m)": r.l_m,
            "L/B": r.relacion_l_b,
            "Área (m²)": r.area_m2,
            "q0 contorno (MPa)": r.q0_kpa/1000,
            "sigma preexcavacion (MPa)": r.sigma_pre_base_kpa/1000,
            "q hund. bruta (MPa)": r.q_hund_bruta_mpa,
            "q hund. neta (MPa)": r.q_hund_neta_mpa,
            "q asientos neta (MPa)": r.q_asiento_neta_mpa,
            "q asientos bruta (MPa)": r.q_asiento_bruta_mpa,
            "q servicio neta (MPa)": r.q_serv_neta_mpa,
            "q servicio bruta (MPa)": r.q_serv_bruta_mpa,
            "Limitación": r.limitacion,
            "ks,BL (MN/m³)": r.ks_bl_mn_m3,
            "Ksp30 (MN/m³)": r.ksp30_mn_m3,
            "sc": r.sc, "sq": r.sq, "sγ": r.sgamma,
            "Prof. perfil (m)": r.profundidad_estudiada_m,
            "Perfil >= 2B": "Sí" if r.espesor_2b else "No",
            "Avisos": " | ".join(r.avisos),
        })
    return pd.DataFrame(rows)


CAMPOS_MAPA = {
    "Presión admisible de servicio (neta)": "q servicio neta (MPa)",
    "Presión admisible por hundimiento (neta)": "q hund. neta (MPa)",
    "Presión admisible por asientos (neta)": "q asientos neta (MPa)",
    "Coeficiente de balasto k_s,BL": "ks,BL (MN/m³)",
    "Balasto equivalente Ksp30": "Ksp30 (MN/m³)",
    "Estado límite gobernante": "Limitación",
}
