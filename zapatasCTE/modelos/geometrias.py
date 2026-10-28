"""Dominio de la malla rectangular y resultados con presión neta/bruta explícita."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class RangoGeometrico:
    bmin: float = 1.5
    bmax: float = 3.0
    incr_b: float = 0.5
    lmin: float = 1.5
    lmax: float = 5.0
    incr_l: float = 0.5

    def validar(self) -> list[str]:
        errores = []
        for clave, valor in vars(self).items():
            if not isfinite(valor) or valor <= 0:
                errores.append(f"{clave}: debe ser positivo y finito.")
        if errores:
            return errores
        if self.bmax < self.bmin or self.lmax < self.lmin:
            errores.append("El valor máximo no puede ser inferior al mínimo.")
        if self.bmin > self.lmax:
            errores.append("No existen combinaciones posibles con B <= L.")
        return errores


def serie_rango(inicio: float, fin: float, paso: float) -> tuple[float, ...]:
    """Serie decimal estable; incluye fin sólo si cae en la malla."""
    if not all(isfinite(x) for x in (inicio, fin, paso)) or paso <= 0 or inicio <= 0 or fin < inicio:
        raise ValueError("Rango inválido: compruebe mínimo, máximo e incremento positivo.")
    n = int((fin - inicio) / paso + 1e-8) + 1
    if n > 300:
        raise ValueError("Demasiados valores por eje (máximo 300). Aumente el incremento.")
    return tuple(round(inicio + k * paso, 10) for k in range(n))


def generar_geometrias(rango: RangoGeometrico, limite: int = 2500) -> tuple[tuple[float,float], ...]:
    errores = rango.validar()
    if errores:
        raise ValueError(" ".join(errores))
    bs = serie_rango(rango.bmin, rango.bmax, rango.incr_b)
    ls = serie_rango(rango.lmin, rango.lmax, rango.incr_l)
    combinaciones = tuple((b,l) for b in bs for l in ls if b <= l + 1e-9)
    if not combinaciones:
        raise ValueError("No hay zapatas válidas con B <= L.")
    if len(combinaciones) > limite:
        raise ValueError(f"Se han solicitado {len(combinaciones)} zapatas. Máximo: {limite}.")
    return combinaciones


@dataclass(frozen=True)
class ResultadoGeometria:
    b_m: float
    l_m: float
    q0_kpa: float
    q_hund_bruta_mpa: float
    q_hund_neta_mpa: float
    q_asiento_neta_mpa: float
    q_serv_neta_mpa: float | None
    q_serv_bruta_mpa: float | None
    ks_bl_mn_m3: float
    ksp30_mn_m3: float
    limitacion: str
    sc: float
    sq: float
    sgamma: float
    profundidad_estudiada_m: float
    espesor_2b: bool
    avisos: tuple[str, ...]
    sigma_pre_base_kpa: float = 0.0
    q_asiento_bruta_mpa: float = 0.0

    @property
    def area_m2(self) -> float:
        return self.b_m * self.l_m

    @property
    def relacion_l_b(self) -> float:
        return self.l_m / self.b_m
