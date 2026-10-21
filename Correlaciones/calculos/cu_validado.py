"""Resistencia sin drenaje: cuatro relaciones bibliograficas trazables.

NO usar como parametro de proyecto sin contrastar con ensayos y criterio tecnico.
Version de modelo 0.4 / 2026-10-21.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from modelos.esquemas import EstadoRevision, ResultadoCorrelacion

FUENTE_SKEMPTON = (
    "Skempton (1957), relacion VST sin corregir para arcillas NC; "
    "reproducida en Soils and Foundations (2015): "
    "https://www.sciencedirect.com/science/article/pii/S1674775515000955"
)
FUENTE_BOWLES = (
    "Bowles, Foundation Analysis and Design, 5a ed., ecuaciones (2-59) y (2-61); "
    "https://abrand-co.com/wp-content/uploads/2023/06/Foundation-Analysis-and-Design-Bowels.pdf"
)
FUENTE_MESRI = (
    "Mesri (1975), resistencia movilizada de arcillas blandas inorganicas; "
    "confirmacion en ASCE (2017): "
    "https://ascelibrary.org/doi/full/10.1061/%28ASCE%29GT.1943-5606.0001697"
)

CONSOLIDACION = ("No definida", "Normalmente consolidada (NC)", "Sobreconsolidada (OC)")
TIPOS_SUELO = ("No identificado", "Arcilla inorgánica blanda", "Otra arcilla")


@dataclass(frozen=True)
class DatosCu:
    sigma_v_ef_kpa: float
    ip_pct: float
    ll_pct: float
    consolidacion: str
    tipo_suelo: str
    sigma_p_kpa: float | None = None


def _numero(nombre: str, valor: float, *, positivo: bool = False) -> float:
    try:
        v = float(valor)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{nombre}: introducir un valor numerico.") from exc
    if not math.isfinite(v) or v < 0 or (positivo and v <= 0):
        raise ValueError(f"{nombre}: valor finito {'mayor que cero' if positivo else 'no negativo'} obligatorio.")
    return v


def _fila(*, autor: str, aplicacion: str, formula: str,
          parametros: str, referencia: str, nota: str,
          valor: float | None, causas: list[str]) -> ResultadoCorrelacion:
    apta = not causas
    return ResultadoCorrelacion(
        autor=autor, aplicacion=aplicacion, formula=formula,
        valor=valor if apta else None, unidad="kPa", parametros=parametros,
        aplicable=apta, estado=EstadoRevision.VERIFICADA_BIBLIOGRAFIA,
        criterio="Cumple condiciones" if apta else "; ".join(causas),
        nota=nota, referencia=referencia,
    )


def calcular_cu(datos: DatosCu) -> list[ResultadoCorrelacion]:
    """Cuatro relaciones independientes; metodo no aplicable => salida sin valor.

    IP y LL en PORCENTAJE; tensiones efectivas y cu en kPa.
    Skempton: c_u(VST) crudo, NC. Bjerrum-Simons: NC e IP>50%.
    Karlsson-Viberg: NC y LL>20%. Mesri: su,mov y sigma'_p,
    solo arcilla blanda inorganica. Ninguna relacion emplea N_SPT.
    """
    if not isinstance(datos, DatosCu):
        raise TypeError("calcular_cu necesita DatosCu.")
    sv = _numero("sigma'_v0 [kPa]", datos.sigma_v_ef_kpa)
    ip = _numero("IP [%]", datos.ip_pct)
    ll = _numero("LL [%]", datos.ll_pct)
    if ll < ip:
        raise ValueError("IP [%] no puede ser mayor que LL [%]: revisar los limites de Atterberg.")
    if datos.consolidacion not in CONSOLIDACION:
        raise ValueError("Estado de consolidacion desconocido.")
    if datos.tipo_suelo not in TIPOS_SUELO:
        raise ValueError("Clasificacion de terreno desconocida.")
    sp = _numero("sigma'_p [kPa]", datos.sigma_p_kpa) if datos.sigma_p_kpa is not None else None

    base = []
    # Cuando se declara sigma'_p, no aceptar simultaneamente "NC" y OCR>1.
    if (sp is not None and sv > 0 and sp > sv
            and datos.consolidacion == "Normalmente consolidada (NC)"):
        base.append("sigma'_p > sigma'_v0 implica OCR > 1: revisar estado NC")
    if datos.tipo_suelo == "No identificado":
        base.append("se requiere identificar que el material es arcilla")
    if datos.consolidacion != "Normalmente consolidada (NC)":
        base.append("requiere arcilla normalmente consolidada")
    if sv <= 0:
        base.append("sigma'_v0 debe ser mayor que cero")

    filas = []
    filas.append(_fila(
        autor="Skempton (1957)", aplicacion="Arcillas NC; resistencia de molinete in situ sin correccion",
        formula=r"c_{u,\mathrm{VST}}=(0.11+0.0037 I_P)\,\sigma'_{v0}",
        parametros="IP [%]; sigma'_v0 [kPa]", referencia=FUENTE_SKEMPTON,
        nota="Relación empírica para resultados VST (molinete) sin corregir, no cu de proyecto; presenta dispersión. No extrapolar a arcillas OC.",
        valor=(0.11 + 0.0037 * ip) * sv,
        causas=base + (["IP debe ser mayor que 0 %"] if ip <= 0 else []),
    ))
    filas.append(_fila(
        autor="Bjerrum y Simons (1960)", aplicacion="Arcillas NC de elevada plasticidad (IP > 50 %)",
        formula=r"c_u=0.45\,\sqrt{I_P/100}\,\sigma'_{v0}",
        parametros="IP [%]; sigma'_v0 [kPa]", referencia=FUENTE_BOWLES,
        nota="IP en porcentaje (equivalente al IP decimal de Bowles); dispersión aproximada ±25 %. Para IP = 50 % no aplica.",
        valor=0.45 * math.sqrt(ip / 100) * sv,
        causas=base + (["IP debe ser > 50 %"] if ip <= 50 else []),
    ))
    filas.append(_fila(
        autor="Karlsson y Viberg (1967)", aplicacion="Arcillas NC, LL > 20 %",
        formula=r"c_u=0.5\,(LL/100)\,\sigma'_{v0}=0.005\,LL\,\sigma'_{v0}",
        parametros="LL [%]; sigma'_v0 [kPa]", referencia=FUENTE_BOWLES,
        nota="LL en porcentaje; dispersión aproximada ±30 %. No utilizar como resistencia de diseño sin ensayos.",
        valor=0.005 * ll * sv,
        causas=base + (["LL debe ser > 20 %"] if ll <= 20 else []),
    ))
    mesri_causas = []
    if datos.tipo_suelo != "Arcilla inorgánica blanda":
        mesri_causas.append("requiere arcilla blanda inorganica")
    if sp is None:
        mesri_causas.append("falta sigma'_p de preconsolidacion")
    elif sp <= 0:
        mesri_causas.append("sigma'_p debe ser > 0")
    elif sv > 0 and sp < sv:
        mesri_causas.append("sigma'_p no puede ser menor que sigma'_v0 (OCR < 1)")
    filas.append(_fila(
        autor="Mesri (1975)", aplicacion="Resistencia movilizada de arcillas blandas inorgánicas",
        formula=r"c_{u,\mathrm{mov}}=0.22\,\sigma'_p",
        parametros="sigma'_p [kPa], presión efectiva de preconsolidación", referencia=FUENTE_MESRI,
        nota="Es resistencia movilizada, no resistencia VST ni resistencia pico. sigma'_p procede de ensayos o interpretación; nunca se sustituye automáticamente por sigma'_v0.",
        valor=0.22 * sp if sp is not None else None,
        causas=mesri_causas,
    ))
    return filas
