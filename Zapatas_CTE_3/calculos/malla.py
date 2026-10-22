"""Integración geométrica: comparaciones netas/brutas, balasto y alertas."""
from __future__ import annotations

from math import isfinite
from dataclasses import replace

from calculos.asientos import asiento_centro_cm
from calculos.capacidad_portante import calcular_hundimiento_rectangular
from calculos.servicio import convertir_ksbl_a_ksp30
from modelos.datos import DatosAsientos, DatosHundimiento
from modelos.geometrias import ResultadoGeometria

# Se mantiene como aproximación interna y no editable de cimentación corrida.
LONGITUD_CORRIDA_ASIENTOS_M = 100.0
LONGITUD_CORRIDA_HUNDIMIENTO_M = 1000.0
# Alias para mostrar la longitud que modela la deformación.
LONGITUD_CORRIDA_INTERNA_M = LONGITUD_CORRIDA_ASIENTOS_M


def validar_entrada(h: DatosHundimiento, s: DatosAsientos) -> list[str]:
    errores = [e for e in h.validar() if "anchos" not in e and "longitud equivalente" not in e]
    errores.extend(s.validar())
    if s.capas:
        ordenadas = sorted(s.capas, key=lambda c: c.z_superior_m)
        if abs(ordenadas[0].z_superior_m) > 1e-8:
            errores.append("El perfil elástico debe comenzar a z=0 m bajo la base.")
        for previa, actual in zip(ordenadas, ordenadas[1:]):
            if actual.z_superior_m > previa.z_inferior_m + 1e-8:
                errores.append("Existen huecos entre estratos del perfil elástico.")
    if h.situacion_drenaje == "Transitoria a corto plazo (sin drenaje)" and h.phi_deg != 0:
        errores.append("En condiciones sin drenaje, debe emplearse phi = 0°.")
    if h.considerar_terreno_sobre_base and h.profundidad_base_m < 2:
        errores.append("CTE Anejo F: no aplicar factores de profundidad con D < 2 m.")
    if h.considerar_terreno_sobre_base and h.inclinacion_talud_deg > 0:
        errores.append("CTE Anejo F: no combinar factores de profundidad con proximidad a talud.")
    if h.flujo_ascendente and h.gamma_efectivo_kn_m3 - h.gradiente_vertical * 10 <= 0:
        errores.append("El peso específico corregido por flujo ascendente debe ser positivo.")
    return errores


def avisos_globales(h: DatosHundimiento, s: DatosAsientos, geometria_incluye_corrida: bool) -> list[str]:
    avisos = [
        "Modelo limitado a carga vertical centrada y base horizontal. No contempla fuerzas horizontales, momentos ni excentricidades.",
        "Los asientos son elásticos e inmediatos; no se calculan consolidación primaria, secundaria ni asientos diferenciales.",
        "ksp30 es una equivalencia aproximada E.6–E.8; en perfiles estratificados no sustituye un ensayo de placa ni un análisis de interacción suelo-estructura.",
        "El criterio profundidad >= 2B es orientativo; no reemplaza la comprobación del bulbo de tensiones del CTE DB-SE-C.",
        "El hundimiento y los asientos se comparan en presión NETA. La presión bruta se muestra también para trazabilidad.",
    ]
    if s.metodo_centro == "excel":
        avisos.append("Se ha elegido Aproximación 2 × (B × L), mantenida para comparar con el VBA; no es el método recomendado para estratificados.")
    if len(s.capas) > 1:
        avisos.append("Perfil estratificado: revisar la representatividad de E, nu y la profundidad de exploración en cada zapata.")
    if h.inclinacion_talud_deg:
        avisos.append("La influencia del talud se aproxima con factores simplificados; comprobar la geometría y la estabilidad global.")
        if not (h.situacion_drenaje == "Transitoria a corto plazo (sin drenaje)") and h.inclinacion_talud_deg > h.phi_deg/2:
            avisos.append("CTE Anejo F: beta > phi/2 exige un estudio específico de estabilidad global.")
    if h.considerar_sobrecarga:
        avisos.append("El valor q0 considera la sobrecarga declarada. Verificar su permanencia alrededor de la cimentación.")
    if geometria_incluye_corrida:
        avisos.append("Comparativa corrida de la hoja original: L de asientos = 100 m y L de hundimiento = 1000 m, ambos internos. No representa una única zapata de longitud física finita.")
    if h.flujo_ascendente:
        avisos.append("Flujo ascendente: se reproduce la corrección aproximada de peso específico del modelo de origen.")
    return avisos


def calcular_geometria(b: float, l: float, h: DatosHundimiento, s: DatosAsientos) -> ResultadoGeometria:
    if not (isfinite(b) and isfinite(l) and 0 < b <= l):
        raise ValueError("Las dimensiones deben cumplir 0 < B <= L.")
    capacidad = calcular_hundimiento_rectangular(h, b, l)
    flexibilidad_cm_mpa = asiento_centro_cm(1.0, b, l, s.capas, s.metodo_centro)
    if not isfinite(flexibilidad_cm_mpa) or flexibilidad_cm_mpa <= 0:
        raise ValueError(f"Flexibilidad no positiva para B={b:g}, L={l:g}.")
    qa_neta = s.asiento_admisible_cm / flexibilidad_cm_mpa
    qh_bruta = capacidad.q_h_d_mpa
    qh_neta = qh_bruta - capacidad.q0_kpa / 1000
    avisos: list[str] = []
    if qh_neta <= 0:
        servicio_neta = None
        servicio_bruta = None
        limitacion = "No válido"
        avisos.append("La resistencia de cálculo bruta no supera la sobrecarga q0: margen neto no positivo.")
    else:
        servicio_neta = min(qh_neta, qa_neta)
        servicio_bruta = servicio_neta + capacidad.q0_kpa / 1000
        limitacion = "Asientos" if qa_neta < qh_neta else "Hundimiento"
    # k_s,BL se basa en respuesta elástica a una presión NETA unitaria; para el
    # modelo lineal su valor no depende de la presión de servicio alcanzada.
    ksbl = (qa_neta) / (s.asiento_admisible_cm / 100.0)
    ksp30 = convertir_ksbl_a_ksp30(ksbl, b, l, s.tipo_material_balasto)
    espesor = max(c.z_inferior_m for c in s.capas)
    if espesor < 2 * b:
        avisos.append(f"Profundidad elástica {espesor:g} m inferior a 2B={2*b:g} m (indicador orientativo).")
    return ResultadoGeometria(
        b_m=b,l_m=l,q0_kpa=capacidad.q0_kpa,
        q_hund_bruta_mpa=qh_bruta, q_hund_neta_mpa=qh_neta,
        q_asiento_neta_mpa=qa_neta, q_serv_neta_mpa=servicio_neta,
        q_serv_bruta_mpa=servicio_bruta, ks_bl_mn_m3=ksbl,
        ksp30_mn_m3=ksp30, limitacion=limitacion,
        sc=capacidad.sc,sq=capacidad.sq,sgamma=capacidad.sgamma,
        profundidad_estudiada_m=espesor, espesor_2b=espesor >= 2*b,
        avisos=tuple(avisos),
    )


def calcular_malla(geometrias: tuple[tuple[float,float],...], h: DatosHundimiento, s: DatosAsientos) -> list[ResultadoGeometria]:
    errores = validar_entrada(h,s)
    if errores:
        raise ValueError(" ".join(errores))
    return [calcular_geometria(b,l,h,s) for b,l in geometrias]


def calcular_corridas(anchos: tuple[float,...], h: DatosHundimiento, s: DatosAsientos) -> list[ResultadoGeometria]:
    """Répl. de la comparación corrida histórica: L_hund.=1000, L_asiento=100.

    NO se mezclan longitudes para una zapata rectangular ordinaria; sólo en
    esta vista explícitamente etiquetada como aproximación corrida del Excel.
    """
    errores = validar_entrada(h,s)
    if errores:
        raise ValueError(" ".join(errores))
    salida = []
    for b in anchos:
        if not (0 < b <= LONGITUD_CORRIDA_ASIENTOS_M):
            continue
        asiento = calcular_geometria(b,LONGITUD_CORRIDA_ASIENTOS_M,h,s)
        hund = calcular_hundimiento_rectangular(h,b,LONGITUD_CORRIDA_HUNDIMIENTO_M)
        neto_h = hund.q_h_d_mpa - hund.q0_kpa/1000
        valido = neto_h > 0
        neto_s = min(neto_h,asiento.q_asiento_neta_mpa) if valido else None
        bruto_s = neto_s + hund.q0_kpa/1000 if valido else None
        limitacion = ("Asientos" if asiento.q_asiento_neta_mpa < neto_h else "Hundimiento") if valido else "No válido"
        avisos = list(asiento.avisos)
        avisos.append("Corrida histórica: L_hund.=1000 m; L_asientos=100 m. No es una geometría BxL individual.")
        if LONGITUD_CORRIDA_ASIENTOS_M/b < 10:
            avisos.append("L_asiento/B < 10: comprobar que la aproximación a zapata corrida es adecuada.")
        salida.append(replace(asiento,q_hund_bruta_mpa=hund.q_h_d_mpa,
            q_hund_neta_mpa=neto_h,q_serv_neta_mpa=neto_s,q_serv_bruta_mpa=bruto_s,
            limitacion=limitacion,sc=hund.sc,sq=hund.sq,sgamma=hund.sgamma,
            avisos=tuple(avisos)))
    return salida
