"""Integración de los estados límite y resultados de servicio."""

from __future__ import annotations

from statistics import mean

from modelos.datos import DatosAsientos, DatosHundimiento, ResultadoAncho

from .asientos import calcular_presiones_asiento
from .capacidad_portante import calcular_presiones_hundimiento


def convertir_ksbl_a_ksp30(
    ks_bl_mn_m3: float,
    ancho_m: float,
    longitud_m: float,
    tipo_material: str,
) -> float:
    """Convierte k_s,BL a k_sp,30 según CTE DB SE-C, expresiones E.6-E.8."""
    if ancho_m <= 0 or longitud_m < ancho_m:
        raise ValueError("La geometría de balasto debe cumplir 0 < B <= L.")

    ks_b = ks_bl_mn_m3 / (1.0 + ancho_m / (2.0 * longitud_m))
    if tipo_material == "Cohesivo":
        return ks_b * ancho_m / 0.30
    if tipo_material == "Granular":
        return ks_b * (2.0 * ancho_m / (ancho_m + 0.30)) ** 2
    raise ValueError("El material para el coeficiente de balasto debe ser Cohesivo o Granular.")


def calcular_resultados(
    hundimiento: DatosHundimiento,
    asientos: DatosAsientos,
) -> tuple[list[ResultadoAncho], dict[str, float]]:
    qh_cuadrada, qh_corrida = calcular_presiones_hundimiento(hundimiento)
    qa_cuadrada, qa_corrida = calcular_presiones_asiento(hundimiento.anchos_m, asientos)
    espesor_total = max(capa.z_inferior_m for capa in asientos.capas) - min(
        capa.z_superior_m for capa in asientos.capas
    )
    resultados: list[ResultadoAncho] = []
    ksp30_cuadrada: list[float] = []
    ksp30_corrida: list[float] = []
    for i, ancho in enumerate(hundimiento.anchos_m):
        ks_b_c = qa_cuadrada[i] / (asientos.asiento_admisible_cm / 100.0)
        ks_b_l = qa_corrida[i] / (asientos.asiento_admisible_cm / 100.0)
        k30_c = convertir_ksbl_a_ksp30(
            ks_b_c, ancho, ancho, asientos.tipo_material_balasto
        )
        k30_l = convertir_ksbl_a_ksp30(
            ks_b_l, ancho, asientos.longitud_corrida_m, asientos.tipo_material_balasto
        )
        ksp30_cuadrada.append(k30_c)
        ksp30_corrida.append(k30_l)
        resultados.append(
            ResultadoAncho(
                ancho_m=ancho,
                hundimiento_cuadrada_mpa=float(qh_cuadrada[i]),
                asiento_cuadrada_mpa=float(qa_cuadrada[i]),
                servicio_cuadrada_mpa=float(min(qh_cuadrada[i], qa_cuadrada[i])),
                limitacion_cuadrada=(
                    "Asientos" if qa_cuadrada[i] < qh_cuadrada[i] else "Hundimiento"
                ),
                hundimiento_corrida_mpa=float(qh_corrida[i]),
                asiento_corrida_mpa=float(qa_corrida[i]),
                servicio_corrida_mpa=float(min(qh_corrida[i], qa_corrida[i])),
                limitacion_corrida=(
                    "Asientos" if qa_corrida[i] < qh_corrida[i] else "Hundimiento"
                ),
                espesor_suficiente=espesor_total > 2 * ancho,
                ksp30_cuadrada_mn_m3=float(k30_c),
                ksp30_corrida_mn_m3=float(k30_l),
            )
        )
    resumen = {
        "ksp30_cuadrada_media_mn_m3": mean(ksp30_cuadrada),
        "ksp30_corrida_media_mn_m3": mean(ksp30_corrida),
    }
    return resultados, resumen
