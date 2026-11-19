"""Conversión trazable de balasto para zapatas (CTE DB-SE-C, Anejo E.5).

E.6 y E.7: obtienen k_sB de k_sp30 para zapata cuadrada.
E.8: obtiene k_sBL a partir de k_sB para zapata rectangular.

Dos interpretaciones: 'literal_cte' mantiene ambas reglas por separado,
con una discontinuidad en B=L; 'continuo' normaliza la variación geométrica
de E.8 respecto de su valor formal en B=L para garantizar continuidad.

IMPORTANTE: 'continuo' es un criterio técnico propuesto, NO la expresión
literal E.8 y requiere aceptación/justificación del técnico responsable.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


VERSION_BALASTO = "4.2.0"
NORMA_BALASTO = "CTE DB-SE-C, anejo E.5, expresiones E.5 a E.8 (20/12/2019)"
TIPOS_TERRENO = ("Cohesivo", "Granular")
CRITERIOS_GEOMETRICOS = ("continuo", "literal_cte")
PLACA_REFERENCIA_M = 0.30


@dataclass(frozen=True)
class DetalleBalasto:
    ks_bl_mn_m3: float
    ks_b_mn_m3: float
    ksp30_mn_m3: float
    b_m: float
    l_m: float
    material: str
    criterio: str
    factor_escala: float
    factor_forma: float
    ecuaciones: str
    advertencias: tuple[str, ...]


def calcular_detalle_balasto(
    ks_bl_mn_m3: float,
    ancho_m: float,
    longitud_m: float,
    tipo_material: str,
    *,
    criterio: str = "literal_cte",
) -> DetalleBalasto:
    """Invierte E.6/E.7 usando una regla de forma explícita.

    k_s,BL representa q_neta/s_elastico en MN/m3. El factor de escala
    responde a la formulación de placa para suelo cohesivo/granular, sin
    alterar la determinación del asiento ni k_s,BL.
    """
    valores = (ks_bl_mn_m3, ancho_m, longitud_m)
    if not all(isinstance(x, (float, int)) and not isinstance(x, bool) and isfinite(x) for x in valores):
        raise ValueError("Balasto y dimensiones deben ser números finitos.")
    if ks_bl_mn_m3 <= 0:
        raise ValueError("k_s,BL debe ser estrictamente positivo (MN/m³).")
    if ancho_m <= 0 or longitud_m < ancho_m:
        raise ValueError("La geometría de balasto debe cumplir 0 < B <= L.")
    if tipo_material not in TIPOS_TERRENO:
        raise ValueError("Material de balasto: seleccione Cohesivo o Granular.")
    if criterio not in CRITERIOS_GEOMETRICOS:
        raise ValueError("Criterio geométrico no reconocido.")

    if tipo_material == "Cohesivo":
        factor_escala = PLACA_REFERENCIA_M / ancho_m   # E.6: k_sB = k_sp30 * f
        ref_escala = "E.6"
    else:
        factor_escala = ((ancho_m + PLACA_REFERENCIA_M) / (2 * ancho_m)) ** 2
        ref_escala = "E.7"

    # Regla E.8: f_rect = 1 + B/(2L).
    # B=L -> 1.5, mientras que E.6/E.7 definen la zapata cuadrada sin ese 1.5.
    # La regla continua utiliza f_rect / f_rect(B,L=B), conservando la
    # VARIACIÓN RELATIVA con L de E.8 y la calibración cuadrada E.6/E.7.
    casi_cuadrada = abs(longitud_m - ancho_m) <= 1e-12 * ancho_m
    f_rect = 1.0 + ancho_m / (2.0 * longitud_m)
    if criterio == "continuo":
        factor_forma = f_rect / 1.5
        geometria_ref = "E.8 normalizada al caso cuadrado (criterio técnico NO literal)"
        avisos = (
            "Factor de forma CONTINUO: (1+B/(2L))/1,5. Adaptación técnica, "
            "NO aplicación literal de E.8; requiere justificación y aceptación.",
        )
    else:
        factor_forma = 1.0 if casi_cuadrada else f_rect
        geometria_ref = "E.8 literal para L>B; regla cuadrada E.6/E.7 para B=L"
        avisos = (
            "Regla CTE LITERAL: existe salto en k_sp30 al pasar de B=L a L>B; "
            "no interpretar el salto como cambio físico del terreno.",
        )

    k_s_b = ks_bl_mn_m3 / factor_forma
    k_sp30 = k_s_b / factor_escala
    if not isfinite(k_sp30) or k_sp30 <= 0:
        raise ValueError("Conversión de balasto fuera del rango numérico representable.")
    return DetalleBalasto(
        ks_bl_mn_m3=float(ks_bl_mn_m3),
        ks_b_mn_m3=float(k_s_b),
        ksp30_mn_m3=float(k_sp30),
        b_m=float(ancho_m), l_m=float(longitud_m),
        material=tipo_material,
        criterio=criterio,
        factor_escala=float(factor_escala), factor_forma=float(factor_forma),
        ecuaciones=f"E.5 + {ref_escala} invertida + {geometria_ref}",
        advertencias=avisos + (
            "k_sp30 es equivalencia INVERSA estimada a partir de parámetros de "
            "deformabilidad, no resultado de ensayo de placa de 30 cm.",
        ),
    )


def comparar_criterios(ks_bl_mn_m3: float, b_m: float, l_m: float, material: str) -> dict:
    """Permite ver cuánto cambia la equivalencia, sin modificar k_s,BL."""
    continuo = calcular_detalle_balasto(ks_bl_mn_m3, b_m, l_m, material, criterio="continuo")
    literal = calcular_detalle_balasto(ks_bl_mn_m3, b_m, l_m, material, criterio="literal_cte")
    return {
        "ksp30_continuo_mn_m3": continuo.ksp30_mn_m3,
        "ksp30_literal_mn_m3": literal.ksp30_mn_m3,
        "diferencia_porcentaje_sobre_literal": 100.0 * (continuo.ksp30_mn_m3 / literal.ksp30_mn_m3 - 1.0),
    }
