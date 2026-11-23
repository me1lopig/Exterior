"""PROP-13: trazabilidad numérica de la ficha B x L (sin alterar el motor).

La memoria recompone los tres términos de la expresión implementada y
contrasta sus sumas con las salidas de calcular_geometria. Todas las presiones
internas de la descomposición se expresan en kPa.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isclose, radians

from calculos.asientos import asiento_centro_cm
from calculos.capacidad_portante import (
    FactoresCapacidad,
    _cohesion_representativa,
    _factores_talud,
    _peso_especifico_representativo,
    calcular_hundimiento_rectangular,
    factores_capacidad,
)
from modelos.datos import DatosAsientos, DatosHundimiento
from modelos.geometrias import ResultadoGeometria


@dataclass(frozen=True)
class MemoriaCalculo:
    b_m: float
    l_m: float
    drenaje: str
    nc: float
    nq: float
    ngamma: float
    sc: float
    sq: float
    sgamma: float
    dc: float
    dq: float
    dgamma: float
    tc: float
    tq: float
    tgamma: float
    gamma_r: float
    cohesion_kpa: float
    gamma_k_kn_m3: float
    q0_kpa: float
    termino_cohesion_kpa: float
    termino_sobrecarga_kpa: float
    termino_gamma_kpa: float
    correccion_talud_kpa: float
    q_h_caracteristica_kpa: float
    q_h_d_bruta_mpa: float
    sigma_pre_base_kpa: float
    q_h_d_neta_mpa: float
    flexibilidad_cm_mpa: float
    asiento_admisible_cm: float
    q_asiento_neta_mpa: float
    q_servicio_neta_mpa: float | None
    q_servicio_bruta_mpa: float | None
    ks_bl_mn_m3: float
    ksp30_mn_m3: float
    limitacion: str
    metodo_asientos: str
    tipo_balasto: str


def elaborar_memoria(
    h: DatosHundimiento, s: DatosAsientos, r: ResultadoGeometria
) -> MemoriaCalculo:
    """Recupera factores del motor; verifica los términos contra el resultado.

    Solo admite una solución real B x L de calcular_geometria, no la tabla de
    corridas históricas que combina L de hundimiento y de asientos distintos.
    """
    b, l = r.b_m, r.l_m
    detalle = calcular_hundimiento_rectangular(h, b, l)
    sin_drenaje = h.situacion_drenaje == "Transitoria a corto plazo (sin drenaje)"
    factores = (FactoresCapacidad(5.14, 1.0, 0.0) if sin_drenaje
               else factores_capacidad(h.phi_deg))
    tc, tq, tg = ((1., 1., 1.) if sin_drenaje else _factores_talud(h))
    cohesion = _cohesion_representativa(h, b)
    gamma_k = _peso_especifico_representativo(h, b)
    tc_kpa = cohesion * factores.nc * detalle.dc * detalle.sc * tc
    tq_kpa = detalle.q0_kpa * factores.nq * detalle.dq * detalle.sq * tq
    tgamma_kpa = 0.5 * b * gamma_k * factores.ngamma * detalle.sgamma * tg
    correccion_kpa = (
        -2 * radians(h.inclinacion_talud_deg) * cohesion
        if sin_drenaje and h.inclinacion_talud_deg > 0 else 0.0
    )
    qh_carac = tc_kpa + tq_kpa + tgamma_kpa + correccion_kpa
    gamma_r = 2.0 if h.situacion_seguridad == "Situación extraordinaria" else 3.0
    qh_bruta = qh_carac / gamma_r / 1000
    flex = asiento_centro_cm(1.0, b, l, s.capas)
    if flex <= 0:
        raise ValueError("Flexibilidad de asiento no positiva.")
    qa_neta = s.asiento_admisible_cm / flex
    for etiqueta, calculado, guardado in (
        ("hundimiento", qh_bruta, r.q_hund_bruta_mpa),
        ("asientos", qa_neta, r.q_asiento_neta_mpa),
        ("descarga", r.q_hund_bruta_mpa-r.q_hund_neta_mpa,
         r.sigma_pre_base_kpa/1000),
    ):
        if not isclose(calculado, guardado, rel_tol=1e-9, abs_tol=1e-10):
            raise ValueError(
                f"Memoria incompatible con el resultado de {etiqueta}: "
                "recalcule las geometrías con los parámetros actuales."
            )
    return MemoriaCalculo(
        b_m=b, l_m=l, drenaje=h.situacion_drenaje,
        nc=factores.nc, nq=factores.nq, ngamma=factores.ngamma,
        sc=detalle.sc, sq=detalle.sq, sgamma=detalle.sgamma,
        dc=detalle.dc, dq=detalle.dq, dgamma=1.0,
        tc=tc, tq=tq, tgamma=tg, gamma_r=gamma_r,
        cohesion_kpa=cohesion, gamma_k_kn_m3=gamma_k,
        q0_kpa=detalle.q0_kpa, termino_cohesion_kpa=tc_kpa,
        termino_sobrecarga_kpa=tq_kpa, termino_gamma_kpa=tgamma_kpa,
        correccion_talud_kpa=correccion_kpa,
        q_h_caracteristica_kpa=qh_carac, q_h_d_bruta_mpa=r.q_hund_bruta_mpa,
        sigma_pre_base_kpa=r.sigma_pre_base_kpa,
        q_h_d_neta_mpa=r.q_hund_neta_mpa,
        flexibilidad_cm_mpa=flex, asiento_admisible_cm=s.asiento_admisible_cm,
        q_asiento_neta_mpa=r.q_asiento_neta_mpa,
        q_servicio_neta_mpa=r.q_serv_neta_mpa,
        q_servicio_bruta_mpa=r.q_serv_bruta_mpa,
        ks_bl_mn_m3=r.ks_bl_mn_m3, ksp30_mn_m3=r.ksp30_mn_m3,
        limitacion=r.limitacion, metodo_asientos="superposicion",
        tipo_balasto=s.tipo_material_balasto,
    )
