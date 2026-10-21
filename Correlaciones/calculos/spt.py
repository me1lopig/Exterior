"""Normalizacion SPT explicita y reproducible, sin correcciones implicitas.

N60 = Ncampo * (ER/60) * CB * CR * CS (FHWA / guia SPT).
(N1)60 = CN*N60, CN=sqrt(100/sigma'_v0[kPa]) (Liao y Whitman).
El limite de CN se expone como opcion, no se aplica clandestinamente.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite, sqrt

FUENTE = "FHWA GEC 5 (2016), secc. 7.6; Liao y Whitman (1986) https://doi.org/10.1061/(ASCE)0733-9410(1986)112:3(373)"


def positivo(nombre: str, x: float, *, permitir_cero: bool = False) -> float:
    try:
        x = float(x)
    except (TypeError, ValueError) as e:
        raise ValueError(f"{nombre}: valor numerico necesario") from e
    if not isfinite(x) or (x < 0 if permitir_cero else x <= 0):
        raise ValueError(f"{nombre}: valor {'no negativo' if permitir_cero else 'positivo'} y finito necesario")
    return x


@dataclass(frozen=True)
class DatosSPT:
    n_campo: float
    energia_pct: float = 60.
    factor_cb: float = 1.
    factor_cr: float = 1.
    factor_cs: float = 1.
    sigma_v_ef_kpa: float | None = None
    cn_max: float | None = 1.7


@dataclass(frozen=True)
class SalidaSPT:
    n_campo: float
    n60: float
    n1_60: float | None
    cn: float | None
    fuente: str = FUENTE


def normalizar_spt(d: DatosSPT) -> SalidaSPT:
    n = positivo("N de campo", d.n_campo, permitir_cero=True)
    er = positivo("Energia (%)", d.energia_pct)
    if er > 200:
        raise ValueError("Energia del SPT fuera de rango fisico del formulario (0-200 %)")
    cb = positivo("Factor CB", d.factor_cb)
    cr = positivo("Factor CR", d.factor_cr)
    cs = positivo("Factor CS", d.factor_cs)
    for titulo, f in (("CB",cb),("CR",cr),("CS",cs)):
        if f > 2:
            raise ValueError(f"Factor {titulo} superior a 2: compruebe origen y unidades")
    n60 = n * (er / 60.) * cb * cr * cs
    if d.sigma_v_ef_kpa is None:
        return SalidaSPT(n, n60, None, None)
    sv = positivo("Tension efectiva vertical", d.sigma_v_ef_kpa)
    cn = sqrt(100. / sv)
    if d.cn_max is not None:
        cn = min(cn, positivo("Limite CN", d.cn_max))
    return SalidaSPT(n, n60, n60*cn, cn)
