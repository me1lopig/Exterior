"""Adaptadores entre tablas editables y el nucleo de calculo."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

from calculos.campo import dmt, molinete, placa_carga, presiometro, sismica
from calculos.errores import ErrorCalculoGeotecnico
from calculos.motor import evaluar_spt
from modelos.dominio import EstadoResultado, MetodoInterpolacion, Resultado
from servicios.catalogo import CORRELACIONES


COLUMNAS_RESULTADO = [
    "grupo", "registro_id", "punto", "profundidad_m", "unidad_geotecnica",
    "correlacion_id", "parametro", "metodo", "valor", "minimo", "maximo", "unidad",
    "valido", "estado", "interpolado", "categoria", "advertencias", "valor_grafico",
    "fuente_id", "formula", "version_metodo", "dominio",
]


def _base(fila: pd.Series) -> dict[str, Any]:
    return {
        "grupo": fila.get("grupo", ""),
        "registro_id": fila.get("registro_id", ""),
        "punto": fila.get("punto", ""),
        "profundidad_m": fila.get("profundidad_m"),
        "unidad_geotecnica": fila.get("unidad_geotecnica", ""),
    }


def _fila_resultado(fila: pd.Series, resultado: Resultado, metodo: str) -> dict[str, Any]:
    base = _base(fila)
    valor_grafico = resultado.valor
    if valor_grafico is None and resultado.minimo is not None and resultado.maximo is not None:
        valor_grafico = (resultado.minimo + resultado.maximo) / 2
    correlacion = CORRELACIONES.get(resultado.correlacion_id)
    base.update({
        "correlacion_id": resultado.correlacion_id,
        "parametro": resultado.parametro,
        "metodo": metodo,
        "valor": resultado.valor,
        "minimo": resultado.minimo,
        "maximo": resultado.maximo,
        "unidad": resultado.unidad,
        "valido": resultado.valido,
        "estado": resultado.estado.value,
        "interpolado": resultado.interpolado,
        "categoria": resultado.categoria,
        "advertencias": " | ".join(resultado.advertencias),
        "valor_grafico": valor_grafico,
        "fuente_id": correlacion.fuente_id if correlacion else "",
        "formula": correlacion.formula if correlacion else "",
        "version_metodo": correlacion.version_metodo if correlacion else "",
        "dominio": correlacion.dominio if correlacion else "",
    })
    return base


def _fila_error(
    fila: pd.Series,
    parametro: str,
    correlacion_id: str,
    metodo: str,
    error: Exception,
) -> dict[str, Any]:
    base = _base(fila)
    base.update({
        "correlacion_id": correlacion_id,
        "parametro": parametro,
        "metodo": metodo,
        "valor": None,
        "minimo": None,
        "maximo": None,
        "unidad": "",
        "valido": False,
        "estado": EstadoResultado.NO_VALIDO.value,
        "interpolado": False,
        "categoria": None,
        "advertencias": str(error),
        "valor_grafico": None,
        "fuente_id": CORRELACIONES[correlacion_id].fuente_id if correlacion_id in CORRELACIONES else "",
        "formula": CORRELACIONES[correlacion_id].formula if correlacion_id in CORRELACIONES else "",
        "version_metodo": CORRELACIONES[correlacion_id].version_metodo if correlacion_id in CORRELACIONES else "",
        "dominio": CORRELACIONES[correlacion_id].dominio if correlacion_id in CORRELACIONES else "",
    })
    return base


def calcular_spt(
    datos: pd.DataFrame,
    correlaciones: list[str],
    metodo_interpolacion: MetodoInterpolacion,
) -> pd.DataFrame:
    filas: list[dict[str, Any]] = []
    for _, fila in datos.iterrows():
        for correlacion_id in correlaciones:
            correlacion = CORRELACIONES[correlacion_id]
            try:
                resultado = evaluar_spt(correlacion_id, fila.to_dict(), metodo_interpolacion)
                filas.append(_fila_resultado(fila, resultado, correlacion.nombre))
            except (ErrorCalculoGeotecnico, TypeError, ValueError) as exc:
                filas.append(_fila_error(fila, correlacion.parametro, correlacion_id, correlacion.nombre, exc))
    return pd.DataFrame(filas, columns=COLUMNAS_RESULTADO)


def _calcular_campo(
    datos: pd.DataFrame,
    calculador: Callable[[pd.Series], dict[str, tuple[float | None, str, list[str]]]],
    metodo_id: str,
    metodo_nombre: str,
    metodos_parametro: dict[str, tuple[str, str]] | None = None,
) -> pd.DataFrame:
    filas: list[dict[str, Any]] = []
    for _, fila in datos.iterrows():
        try:
            resultados = calculador(fila)
            for parametro, (valor, unidad, advertencias) in resultados.items():
                if valor is None:
                    continue
                correlacion_id, nombre = (metodos_parametro or {}).get(
                    parametro, (metodo_id, metodo_nombre)
                )
                resultado = Resultado(
                    correlacion_id=correlacion_id,
                    parametro=parametro,
                    valor=float(valor),
                    unidad=unidad,
                    advertencias=advertencias,
                )
                filas.append(_fila_resultado(fila, resultado, nombre))
        except (ErrorCalculoGeotecnico, TypeError, ValueError) as exc:
            filas.append(_fila_error(fila, "No calculado", metodo_id, metodo_nombre, exc))
    return pd.DataFrame(filas, columns=COLUMNAS_RESULTADO)


def calcular_molinete(datos: pd.DataFrame) -> pd.DataFrame:
    def calculador(f: pd.Series) -> dict[str, tuple[float | None, str, list[str]]]:
        r = molinete(
            float(f["torque_pico_kNm"]), float(f["diametro_m"]), float(f["altura_m"]),
            None if pd.isna(f.get("torque_rem_kNm")) else float(f["torque_rem_kNm"]),
            str(f.get("tipo_suelo") or ""),
        )
        return {
            "su_pico": (r["su_pico_kpa"], "kPa", []),
            "su_rem": (r["su_rem_kpa"], "kPa", []),
            "St": (r["sensibilidad"], "adimensional", []),
        }
    return _calcular_campo(
        datos, calculador, "RES-SU-FVT-ISO22476-9", "Molinete de campo"
    )


def calcular_sismica(datos: pd.DataFrame) -> pd.DataFrame:
    def calculador(f: pd.Series) -> dict[str, tuple[float | None, str, list[str]]]:
        r = sismica(
            float(f["Vs_m_s"]), float(f["gamma_kN_m3"]),
            None if pd.isna(f.get("Vp_m_s")) else float(f["Vp_m_s"]),
        )
        return {"G0": (r["G0_MPa"], "MPa", []), "nu_din": (r["nu_din"], "adimensional", []), "E0": (r["E0_MPa"], "MPa", [])}
    return _calcular_campo(
        datos, calculador, "DEF-DIN-VS-FHWA2016", "Sismica de campo"
    )


def calcular_dmt(datos: pd.DataFrame) -> pd.DataFrame:
    def calculador(f: pd.Series) -> dict[str, tuple[float | None, str, list[str]]]:
        cementado = f.get("cementado")
        cementado_bool = None if pd.isna(cementado) else bool(cementado)
        r = dmt(
            float(f["p0_kPa"]), float(f["p1_kPa"]), float(f["u0_kPa"]),
            float(f["sigma_v_eff_kPa"]), str(f.get("tipo_suelo") or ""), cementado_bool,
        )
        avisos = [str(r["advertencia_derivadas"])] if r["advertencia_derivadas"] else []
        return {
            "ID": (r["ID"], "adimensional", avisos), "KD": (r["KD"], "adimensional", avisos),
            "ED": (r["ED_MPa"], "MPa", avisos), "OCR": (r["OCR_estimado"], "adimensional", []),
            "su": (r["su_estimado_kPa"], "kPa", []),
        }
    return _calcular_campo(
        datos, calculador, "EST-DMT-MARCHETTI1980", "DMT - interpretacion Marchetti",
        {"su": ("RES-SU-DMT-MARCHETTI1980", "Resistencia no drenada desde DMT")},
    )


def calcular_pmt(datos: pd.DataFrame) -> pd.DataFrame:
    def calculador(f: pd.Series) -> dict[str, tuple[float | None, str, list[str]]]:
        opcional = lambda c: None if pd.isna(f.get(c)) else float(f[c])
        r = presiometro(
            float(f["EM_MPa"]), float(f["plM_MPa"]), opcional("pf_MPa"), opcional("alpha"),
            opcional("p0h_MPa"), str(f.get("tipo_suelo") or ""),
        )
        avisos = [str(r["advertencia_su"])] if r["advertencia_su"] else []
        return {
            "EM": (r["EM_MPa"], "MPa", avisos), "plM": (r["plM_MPa"], "MPa", avisos),
            "pf": (r["pf_MPa"], "MPa", avisos), "E_equiv": (r["E_equiv_MPa"], "MPa", avisos),
            "su": (r["su_estimado_kPa"], "kPa", []),
        }
    return _calcular_campo(
        datos, calculador, "DEF-PMT-ISO22476-4", "Presiometro Menard",
        {"su": ("RES-SU-PMT-FHWA1989", "Resistencia no drenada desde presiometro")},
    )


def calcular_placa(datos: pd.DataFrame) -> pd.DataFrame:
    def calculador(f: pd.Series) -> dict[str, tuple[float | None, str, list[str]]]:
        k30 = None if pd.isna(f.get("K30_MN_m3")) else float(f["K30_MN_m3"])
        r = placa_carga(float(f["Ev1_MPa"]), float(f["Ev2_MPa"]), k30)
        return {
            "Ev1": (r["Ev1_MPa"], "MPa", []), "Ev2": (r["Ev2_MPa"], "MPa", []),
            "Ev2/Ev1": (r["Ev2_Ev1"], "adimensional", []), "K30": (r["K30_MN_m3"], "MN/m3", []),
        }
    return _calcular_campo(datos, calculador, "INT-PLACA-NLT357", "Placa de carga")
