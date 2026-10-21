"""Derivaciones de ensayos de campo distintas del SPT."""

from __future__ import annotations

import math

from calculos.errores import ErrorCalculoGeotecnico, FueraDeDominio


def _positivo_finito(nombre: str, valor: float) -> None:
    if not math.isfinite(valor) or valor <= 0:
        raise ErrorCalculoGeotecnico(f"{nombre} debe ser un numero finito positivo.")


def _finito(nombre: str, valor: float) -> None:
    if not math.isfinite(valor):
        raise ErrorCalculoGeotecnico(f"{nombre} debe ser un numero finito.")


def molinete(
    torque_pico_knm: float,
    diametro_m: float,
    altura_m: float,
    torque_remoldeado_knm: float | None = None,
    tipo_suelo: str | None = None,
) -> dict[str, float | None]:
    """Calcula su para una veleta rectangular suponiendo corte uniforme."""
    if tipo_suelo not in {"Arcilla", "Limo cohesivo"}:
        raise FueraDeDominio("El molinete de campo se limita a arcillas y limos cohesivos.")
    _positivo_finito("El par de pico", torque_pico_knm)
    _positivo_finito("El diametro del molinete", diametro_m)
    _positivo_finito("La altura del molinete", altura_m)
    factor = math.pi * diametro_m**2 * (altura_m / 2 + diametro_m / 6)
    su_pico = torque_pico_knm / factor
    su_rem = None
    sensibilidad = None
    if torque_remoldeado_knm is not None:
        _positivo_finito("El par remoldeado", torque_remoldeado_knm)
        if torque_remoldeado_knm <= 0 or torque_remoldeado_knm > torque_pico_knm:
            raise ErrorCalculoGeotecnico(
                "El par remoldeado debe ser positivo y no superar el par de pico."
            )
        su_rem = torque_remoldeado_knm / factor
        sensibilidad = su_pico / su_rem
    return {"su_pico_kpa": su_pico, "su_rem_kpa": su_rem, "sensibilidad": sensibilidad}


def sismica(vs_ms: float, gamma_kn_m3: float, vp_ms: float | None = None) -> dict[str, float | None]:
    """Obtiene modulos a pequenas deformaciones desde velocidades de onda."""
    _positivo_finito("Vs", vs_ms)
    _positivo_finito("gamma", gamma_kn_m3)
    rho = gamma_kn_m3 * 1000 / 9.80665
    g0_mpa = rho * vs_ms**2 / 1e6
    nu = None
    e0_mpa = None
    if vp_ms is not None:
        _positivo_finito("Vp", vp_ms)
        if vp_ms <= vs_ms * math.sqrt(2):
            raise FueraDeDominio("Vp debe ser mayor que sqrt(2)*Vs para obtener un nu fisico.")
        ratio = vp_ms**2
        nu = (ratio - 2 * vs_ms**2) / (2 * (ratio - vs_ms**2))
        if not -1 < nu < 0.5:
            raise FueraDeDominio("Las velocidades producen un coeficiente de Poisson no fisico.")
        e0_mpa = 2 * g0_mpa * (1 + nu)
    return {"rho_kg_m3": rho, "G0_MPa": g0_mpa, "nu_din": nu, "E0_MPa": e0_mpa}


def dmt(
    p0_kpa: float,
    p1_kpa: float,
    u0_kpa: float,
    sigma_v_eff_kpa: float,
    tipo_suelo: str | None = None,
    cementado: bool | None = None,
) -> dict[str, float | str | None]:
    """Calcula los indices intermedios normalizados del DMT."""
    for nombre, valor in (("p0", p0_kpa), ("p1", p1_kpa), ("u0", u0_kpa)):
        _finito(nombre, valor)
    _positivo_finito("La tension vertical efectiva", sigma_v_eff_kpa)
    if p1_kpa <= p0_kpa or p0_kpa <= u0_kpa:
        raise FueraDeDominio("Se requiere p1>p0>u0 para interpretar el DMT.")
    delta = p0_kpa - u0_kpa
    id_material = (p1_kpa - p0_kpa) / delta
    kd = delta / sigma_v_eff_kpa
    ed_kpa = 34.7 * (p1_kpa - p0_kpa)
    ocr_marchetti = None
    su_kpa = None
    aviso = None
    if tipo_suelo == "Arcilla" and cementado is False:
        if kd < 2.0:
            aviso = "KD<2 produciria OCR<1; no se aplican las correlaciones OCR y su."
        else:
            ocr_marchetti = (0.5 * kd) ** 1.56
            su_kpa = 0.22 * sigma_v_eff_kpa * (0.5 * kd) ** 1.25
    else:
        aviso = "OCR y su requieren arcilla no cementada identificada expresamente."
    return {
        "ID": id_material,
        "KD": kd,
        "ED_MPa": ed_kpa / 1000,
        "OCR_estimado": ocr_marchetti,
        "su_estimado_kPa": su_kpa,
        "advertencia_derivadas": aviso,
    }


def presiometro(
    em_mpa: float,
    plm_mpa: float,
    pf_mpa: float | None = None,
    alpha_reologico: float | None = None,
    presion_horizontal_mpa: float | None = None,
    tipo_suelo: str | None = None,
) -> dict[str, float | str | None]:
    """Conserva parametros Menard y aplica derivaciones opcionales explicitas."""
    _positivo_finito("EM", em_mpa)
    _positivo_finito("plM", plm_mpa)
    if pf_mpa is not None:
        _positivo_finito("pf", pf_mpa)
    if pf_mpa is not None and not 0 < pf_mpa <= plm_mpa:
        raise ErrorCalculoGeotecnico("pf debe ser positiva y no superar plM.")
    e_equiv = None
    if alpha_reologico is not None:
        _finito("El factor reologico", alpha_reologico)
        if not 0 < alpha_reologico <= 1:
            raise ErrorCalculoGeotecnico("El factor reologico debe estar en (0, 1].")
        e_equiv = em_mpa / alpha_reologico
    su_kpa = None
    advertencia_su = None
    if presion_horizontal_mpa is not None:
        _finito("La presion horizontal", presion_horizontal_mpa)
        if tipo_suelo not in {"Arcilla", "Limo cohesivo"}:
            advertencia_su = "su presiometrica requiere un suelo cohesivo identificado expresamente."
        else:
            p_neta = plm_mpa - presion_horizontal_mpa
            if p_neta <= 0:
                raise FueraDeDominio("La presion limite neta debe ser positiva.")
            su_kpa = p_neta * 1000 / 5.5
    return {
        "EM_MPa": em_mpa,
        "plM_MPa": plm_mpa,
        "pf_MPa": pf_mpa,
        "E_equiv_MPa": e_equiv,
        "su_estimado_kPa": su_kpa,
        "advertencia_su": advertencia_su,
    }


def placa_carga(ev1_mpa: float, ev2_mpa: float, k30_mn_m3: float | None = None) -> dict[str, float | None]:
    """Valida los resultados principales de una placa de carga."""
    _positivo_finito("Ev1", ev1_mpa)
    _positivo_finito("Ev2", ev2_mpa)
    if k30_mn_m3 is not None:
        _positivo_finito("K30", k30_mn_m3)
    return {"Ev1_MPa": ev1_mpa, "Ev2_MPa": ev2_mpa, "Ev2_Ev1": ev2_mpa / ev1_mpa, "K30_MN_m3": k30_mn_m3}
