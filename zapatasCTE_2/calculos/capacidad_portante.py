"""Capacidad portante reproducida a partir de la hoja SUELOS."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan, exp, pi, radians, sin, tan

import numpy as np

from modelos.datos import DatosHundimiento


@dataclass(frozen=True)
class FactoresCapacidad:
    nc: float
    nq: float
    ngamma: float


def factores_capacidad(phi_deg: float) -> FactoresCapacidad:
    """Devuelve Nc, Nq y N-gamma usando exactamente las expresiones del Excel."""
    phi = radians(phi_deg)
    nq = tan(pi / 4 + phi / 2) ** 2 * exp(pi * tan(phi))
    nc = pi + 2 if phi_deg == 0 else (nq - 1) / tan(phi)
    ngamma = 1.5 * (nq - 1) * tan(phi)
    return FactoresCapacidad(nc=nc, nq=nq, ngamma=ngamma)


def _cohesion_representativa(datos: DatosHundimiento, ancho_m: float) -> float:
    if not (
        datos.cu_aumenta_con_profundidad
        and datos.situacion_drenaje == "Transitoria a corto plazo (sin drenaje)"
    ):
        return datos.cohesion_kpa
    pendiente = (datos.cu_final_kpa - datos.cu_inicial_kpa) / (
        datos.cu_z_final_m - datos.cu_z_inicial_m
    )
    estimada = pendiente * (datos.profundidad_base_m + ancho_m / 4) + datos.cu_inicial_kpa
    return min(2 * datos.cu_inicial_kpa, estimada)


def _peso_especifico_representativo(datos: DatosHundimiento, ancho_m: float) -> float:
    if datos.flujo_ascendente:
        return datos.gamma_efectivo_kn_m3 - datos.gradiente_vertical * 10.0
    fraccion_sobre_nf = max(
        0.0,
        min(datos.nivel_freatico_m - datos.profundidad_base_m, ancho_m),
    ) / ancho_m
    return datos.gamma_efectivo_kn_m3 + fraccion_sobre_nf * (
        datos.gamma_aparente_kn_m3 - datos.gamma_efectivo_kn_m3
    )


def _factores_geometricos(
    datos: DatosHundimiento,
    ancho_m: float,
    cuadrada: bool,
    factores: FactoresCapacidad,
) -> tuple[float, float, float, float, float, float]:
    phi = radians(datos.phi_deg)
    if datos.considerar_terreno_sobre_base:
        dc = 1 + 0.34 * atan(datos.profundidad_base_m / ancho_m)
        dq = (
            1.0
            if datos.phi_deg < 1
            else 1
            + 2
            * factores.nq
            / factores.nc
            * (1 - sin(phi)) ** 2
            * atan(min(datos.profundidad_base_m, 2 * ancho_m) / ancho_m)
        )
    else:
        dc = dq = 1.0
    dgamma = 1.0

    if cuadrada:
        sc = 1.2
        sq = 1.2 if datos.forma == "Circular" else 1 + 1.5 * tan(phi)
        sgamma = 0.7
    elif datos.forma == "Circular":
        sc, sq, sgamma = 1.2, 1.2, 0.6
    else:
        relacion = ancho_m / datos.longitud_corrida_m
        sc = 1 + 0.2 * relacion
        sq = 1 + 1.5 * tan(phi) * relacion
        sgamma = 1 - 0.3 * relacion
    return dc, dq, dgamma, sc, sq, sgamma


def _factores_talud(datos: DatosHundimiento) -> tuple[float, float, float]:
    if datos.talud_transitorio_sin_drenaje:
        return 1.0, 1.0, 1.0
    beta = radians(datos.inclinacion_talud_deg)
    phi = radians(datos.phi_deg)
    return exp(-2 * beta * tan(phi)), 1 - sin(2 * beta), 1 - sin(2 * beta)


def calcular_presiones_hundimiento(
    datos: DatosHundimiento,
) -> tuple[np.ndarray, np.ndarray]:
    """Calcula qd para zapata cuadrada y corrida, en MPa."""
    errores = datos.validar()
    if errores:
        raise ValueError(" ".join(errores))
    factores = factores_capacidad(datos.phi_deg)
    gamma_r = 2.0 if datos.situacion_seguridad == "Situación extraordinaria" else 3.0
    q0_kpa = (
        datos.gamma_sobrecarga_kn_m3 * datos.altura_sobrecarga_m
        if datos.considerar_sobrecarga
        else 0.0
    )
    tc, tq, tgamma = _factores_talud(datos)
    resultados: list[list[float]] = [[], []]
    for ancho_m in datos.anchos_m:
        cohesion = _cohesion_representativa(datos, ancho_m)
        gamma = _peso_especifico_representativo(datos, ancho_m)
        for indice, cuadrada in enumerate((True, False)):
            dc, dq, dg, sc, sq, sg = _factores_geometricos(
                datos, ancho_m, cuadrada, factores
            )
            q_ult_kpa = (
                cohesion * factores.nc * dc * sc * tc
                + q0_kpa * factores.nq * dq * sq * tq
                + 0.5 * ancho_m * gamma * factores.ngamma * dg * sg * tgamma
            )
            resultados[indice].append(q_ult_kpa / gamma_r / 1000.0)
    return np.asarray(resultados[0]), np.asarray(resultados[1])
