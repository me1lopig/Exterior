"""Formulaciones geotecnicas verificadas y controles de dominio."""

import math

from models.domain import CalculationResult


CTE_D23 = (
    ("Muy flojo o muy blando", "N < 10", "0-80", "< 8"),
    ("Flojo o blando", "10-25", "80-150", "8-40"),
    ("Medio", "25-50", "150-300", "40-100"),
    ("Compacto o duro", "50-rechazo", "300-500", "100-500"),
    ("Roca blanda", "Rechazo", "500-5 000", "500-8 000"),
    ("Roca dura", "Rechazo", "5 000-40 000", "8 000-15 000"),
    ("Roca muy dura", "Rechazo", "> 40 000", "> 15 000"),
)

CTE_K30 = (
    ("Arcilla blanda", 15, 30),
    ("Arcilla media", 30, 60),
    ("Arcilla dura", 60, 200),
    ("Limo", 15, 45),
    ("Arena floja", 10, 30),
    ("Arena media", 30, 90),
    ("Arena compacta", 90, 200),
    ("Grava arenosa floja", 70, 120),
    ("Grava arenosa compacta", 120, 300),
    ("Margas arcillosas", 200, 400),
    ("Rocas algo alteradas", 300, 5000),
    ("Rocas sanas", 5000, math.inf),
)

CTE_POISSON = (
    ("Arcillas blandas normalmente consolidadas", 0.40),
    ("Arcillas medias", 0.30),
    ("Arcillas duras preconsolidadas", 0.15),
    ("Arenas y suelos granulares", 0.30),
)


def _positive(name: str, value: float) -> None:
    if value <= 0 or not math.isfinite(value):
        raise ValueError(f"{name} debe ser positivo y finito.")


def cte_d23_linear(n_spt: float, n_refusal: float) -> tuple[CalculationResult, CalculationResult]:
    """Interpola linealmente qu y E entre los intervalos de la tabla D.23.

    El CTE no asigna un golpeo numerico al rechazo. Por ello, el extremo superior
    del ultimo tramo se recibe como hipotesis explicita ``n_refusal``. Para el
    primer tramo se adopta el origen (N, qu, E) = (0, 0, 0).
    """

    if not math.isfinite(n_spt) or n_spt < 0:
        raise ValueError("N SPT debe ser no negativo y finito.")
    if not math.isfinite(n_refusal) or n_refusal <= 50:
        raise ValueError("El N equivalente al rechazo debe ser finito y mayor que 50.")
    if n_spt > n_refusal:
        raise ValueError("N SPT no puede superar el N equivalente al rechazo adoptado.")

    points = (
        (0.0, 0.0, 0.0),
        (10.0, 80.0, 8.0),
        (25.0, 150.0, 40.0),
        (50.0, 300.0, 100.0),
        (n_refusal, 500.0, 500.0),
    )
    lower, upper = points[0], points[1]
    for candidate_lower, candidate_upper in zip(points, points[1:]):
        if candidate_lower[0] <= n_spt <= candidate_upper[0]:
            lower, upper = candidate_lower, candidate_upper
            break

    ratio = (n_spt - lower[0]) / (upper[0] - lower[0])
    qu = lower[1] + ratio * (upper[1] - lower[1])
    modulus = lower[2] + ratio * (upper[2] - lower[2])
    interval = f"N = {lower[0]:g}-{upper[0]:g}"
    warning = (
        "Interpolacion adoptada por la herramienta; no es una correlacion prescrita por el CTE. "
        f"Se ha definido rechazo = {n_refusal:g} golpes/0.30 m."
    )
    formula = "Y = Yi + (Yi+1-Yi)*(N-Ni)/(Ni+1-Ni)"
    common = {
        "formula": formula,
        "input_basis": f"N SPT de campo; {interval}",
        "applicability": "Interpolacion por tramos de la tabla D.23; valores orientativos.",
        "reference_id": "CTE2019",
        "warning": warning,
    }
    return (
        CalculationResult("CTE D.23, interpolacion lineal de qu", qu, "kPa", **common),
        CalculationResult("CTE D.23, interpolacion lineal de E", modulus, "MPa", **common),
    )


def skempton_su(pi_percent: float, sigma_v_eff_kpa: float) -> CalculationResult:
    """Resistencia no drenada de arcilla NC a partir de veleta de campo."""

    if not 0 <= pi_percent <= 100:
        raise ValueError("IP debe estar entre 0 y 100 %.")
    _positive("sigma'v0", sigma_v_eff_kpa)
    value = (0.11 + 0.0037 * pi_percent) * sigma_v_eff_kpa
    return CalculationResult(
        "Skempton (1957)", value, "kPa",
        "su/sigma'v0 = 0.11 + 0.0037*IP",
        "IP en %; sigma'v0 en kPa",
        "Arcillas normalmente consolidadas; su de veleta de campo; estimacion preliminar.",
        "SKEMPTON1957",
    )


def bjerrum_simons_su(pi_percent: float, sigma_v_eff_kpa: float) -> CalculationResult:
    if pi_percent < 50:
        warning = "Fuera del dominio publicado IP > 50 %."
    else:
        warning = ""
    _positive("sigma'v0", sigma_v_eff_kpa)
    if pi_percent < 0:
        raise ValueError("IP no puede ser negativo.")
    value = 0.45 * math.sqrt(pi_percent / 100.0) * sigma_v_eff_kpa
    return CalculationResult(
        "Bjerrum y Simons (1960)", value, "kPa",
        "su/sigma'v0 = 0.45*sqrt(IP/100)",
        "IP en %; sigma'v0 en kPa", "Arcillas normalmente consolidadas, IP > 50 %.",
        "BJERRUM1960", warning,
    )


def mesri_su(sigma_p_eff_kpa: float) -> CalculationResult:
    _positive("sigma'p", sigma_p_eff_kpa)
    return CalculationResult(
        "Mesri (1975)", 0.22 * sigma_p_eff_kpa, "kPa",
        "su(mob)/sigma'p = 0.22", "sigma'p efectiva en kPa",
        "Resistencia movilizada en campo; usar presion efectiva de preconsolidacion, no sigma'v0.",
        "MESRI1975",
    )


def phi_wolff(n1_60: float) -> CalculationResult:
    if n1_60 < 0:
        raise ValueError("(N1)60 no puede ser negativo.")
    warning = "" if n1_60 <= 60 else "Extrapolacion: contrastar con ensayos y limitar por mineralogia/dilatancia."
    value = 27.1 + 0.3 * n1_60 - 0.00054 * n1_60**2
    return CalculationResult(
        "Wolff (1989), sintesis NCHRP 651", value, "grados",
        "phi' = 27.1 + 0.3*(N1)60 - 0.00054*(N1)60^2",
        "(N1)60", "Arenas; angulo de pico estimado empiricamente.", "NCHRP651", warning,
    )


def phi_hatanaka_uchida(n1_60: float) -> CalculationResult:
    if n1_60 < 0:
        raise ValueError("(N1)60 no puede ser negativo.")
    warning = "" if 3.5 <= n1_60 <= 30 else "Fuera del intervalo 3.5-30 asociado a la base experimental original."
    return CalculationResult(
        "Hatanaka y Uchida (1996)", 20 + math.sqrt(20 * n1_60), "grados",
        "phi' = 20 + sqrt(20*(N1)60)", "(N1)60",
        "Arenas naturales; 3.5 <= (N1)60 <= 30.", "HATANAKA1996", warning,
    )


def phi_mayne(n1_60: float) -> CalculationResult:
    if n1_60 < 0:
        raise ValueError("(N1)60 no puede ser negativo.")
    warning = "" if n1_60 <= 60 else "Extrapolacion elevada: contrastar con ensayos y mineralogia."
    return CalculationResult(
        "Mayne et al. (2001), basado en Hatanaka-Uchida", 20 + math.sqrt(15.4 * n1_60), "grados",
        "phi' = 20 + sqrt(15.4*(N1)60)", "(N1)60",
        "Arenas; modificacion recogida en la sintesis NCHRP 651.", "NCHRP651", warning,
    )


def phi_jra(n1_60: float) -> CalculationResult:
    if n1_60 < 0:
        raise ValueError("(N1)60 no puede ser negativo.")
    raw = 15 + math.sqrt(15 * n1_60)
    warnings = []
    if n1_60 <= 5:
        warnings.append("El criterio publicado exige (N1)60 > 5.")
    if raw > 45:
        warnings.append("Resultado limitado a 45 grados por la propia formulacion.")
    return CalculationResult(
        "Japan Road Association (sintesis NCHRP 651)", min(raw, 45.0), "grados",
        "phi' = 15 + sqrt(15*(N1)60), con phi' <= 45 grados", "(N1)60",
        "Arenas; (N1)60 > 5.", "NCHRP651", " ".join(warnings),
    )


def navfac_sand_modulus(n_field: float, soil_type: str) -> CalculationResult:
    """Modulo Es segun NAVFAC DM 7.1; coeficientes en tsf por golpe."""

    if n_field < 0:
        raise ValueError("N no puede ser negativo.")
    factors = {
        "Limos y arenas limosas": 4.0,
        "Arenas limpias finas-medias": 7.0,
        "Arenas gruesas con poca grava": 10.0,
        "Gravas arenosas y gravas": 12.0,
    }
    if soil_type not in factors:
        raise ValueError("Tipo de suelo NAVFAC no reconocido.")
    factor = factors[soil_type]
    value_mpa = factor * n_field * 0.0957605
    return CalculationResult(
        "NAVFAC DM 7.1 (1982)", value_mpa, "MPa", f"Es = {factor:g}*N [tsf]",
        "N de la base historica NAVFAC; 1 tsf = 0.0957605 MPa",
        "Estimacion de deformabilidad para el metodo de asientos NAVFAC; no es modulo unico del suelo.",
        "NAVFAC1982", "Correlacion historica: verificar compatibilidad del equipo SPT y nivel de deformacion.",
    )


def stroud_drained_vertical_modulus(
    n_spt_historical: float,
    pi_percent: float,
) -> tuple[CalculationResult, CalculationResult]:
    """Banda aproximada de E'v/N digitalizada de Stroud y Butler (1975).

    Las expresiones cubicas no fueron propuestas como ecuaciones por los autores;
    son aproximaciones posteriores a los limites graficos de su Figura 6. Se
    restringen a 0 <= IP <= 60 para evitar extrapolaciones y el cruce no fisico
    de ambos polinomios cerca del extremo del grafico.
    """

    if not math.isfinite(n_spt_historical) or n_spt_historical < 0:
        raise ValueError("El N SPT historico debe ser no negativo y finito.")
    if not math.isfinite(pi_percent) or not 0 <= pi_percent <= 60:
        raise ValueError("La aproximacion grafica de Stroud se limita a 0 <= IP <= 60 %.")

    lower_kpa_per_blow = (
        -0.003 * pi_percent**3
        + 0.859 * pi_percent**2
        - 72.04 * pi_percent
        + 2410
    )
    upper_kpa_per_blow = (
        -0.008 * pi_percent**3
        + 1.732 * pi_percent**2
        - 127.2 * pi_percent
        + 3703
    )
    warning = (
        "Polinomios de digitalizacion, no ecuaciones originales de Stroud. "
        "La correlacion original uso equipo SPT britanico historico; no sustituir N por N60 sin calibracion local."
    )
    common = {
        "input_basis": "N SPT de la base historica; IP en %",
        "applicability": "Modulo vertical drenado E'v de arcillas/materiales sobreconsolidados; 0 <= IP <= 60 %.",
        "reference_id": "STROUD1975",
        "warning": warning,
    }
    return (
        CalculationResult(
            "Stroud-Butler, limite inferior digitalizado",
            n_spt_historical * lower_kpa_per_blow / 1000.0,
            "MPa",
            "E'v = N*(-0.003*IP^3 + 0.859*IP^2 - 72.04*IP + 2410)",
            **common,
        ),
        CalculationResult(
            "Stroud-Butler, limite superior digitalizado",
            n_spt_historical * upper_kpa_per_blow / 1000.0,
            "MPa",
            "E'v = N*(-0.008*IP^3 + 1.732*IP^2 - 127.2*IP + 3703)",
            **common,
        ),
    )


def cte_eu(cu_kpa: float, pi_percent: float, ocr: float) -> CalculationResult:
    """Modulo no drenado Eu de la tabla F.2 del CTE DB-SE-C."""

    _positive("cu", cu_kpa)
    _positive("OCR", ocr)
    if pi_percent < 0:
        raise ValueError("IP no puede ser negativo.")
    if math.isclose(pi_percent, 30.0) or math.isclose(pi_percent, 50.0):
        raise ValueError("La tabla F.2 no asigna de forma inequivoca IP = 30 o 50; adopte una banda justificadamente.")
    pi_band = 0 if pi_percent < 30 else 1 if pi_percent < 50 else 2
    ocr_band = 0 if ocr < 3 else 1 if ocr <= 5 else 2
    ratios = ((800, 600, 300), (350, 250, 130), (150, 100, 50))
    ratio = ratios[pi_band][ocr_band]
    return CalculationResult(
        "CTE DB-SE-C, tabla F.2", ratio * cu_kpa / 1000.0, "MPa",
        f"Eu = {ratio}*cu", "cu en kPa; resultado convertido a MPa",
        "Arcillas sobreconsolidadas; modulo no drenado. Seleccionar bandas de IP y OCR de la tabla.", "CTE2019",
    )


def calip(percent_passing_no40: float, clay_content_percent: float, ll_percent: float, pl_percent: float) -> tuple[float, float, float]:
    """Devuelve (CF, IP, CALIP) segun Collotta et al. (1989)."""

    if not 0 < percent_passing_no40 <= 100:
        raise ValueError("El porcentaje que pasa el tamiz No. 40 debe estar en (0, 100].")
    if not 0 <= clay_content_percent <= percent_passing_no40:
        raise ValueError("El contenido de arcilla debe estar entre 0 y el porcentaje que pasa No. 40.")
    if not math.isfinite(ll_percent) or not math.isfinite(pl_percent) or not 0 <= pl_percent < ll_percent:
        raise ValueError("Se requiere LL y LP finitos, con 0 <= LP < LL.")
    cf = 100.0 * clay_content_percent / percent_passing_no40
    pi = ll_percent - pl_percent
    return cf, pi, cf**2 * ll_percent * pi * 1e-5


def phi_residual_from_calip(calip_value: float) -> CalculationResult:
    """Angulo residual secante del ajuste de Tzampoglou et al. a Collotta.

    El ajuste representa datos de corte anular. No introduce dependencia explicita
    con la tension normal efectiva porque la fuente ajusta valores medios medidos
    aproximadamente entre 100 y 500 kPa.
    """

    if calip_value < 0 or not math.isfinite(calip_value):
        raise ValueError("CALIP debe ser no negativo y finito.")
    value = 21.2 * math.exp(-0.008 * calip_value**1.5) + 7.7
    warning = ""
    if calip_value > 200:
        warning = "CALIP > 200 queda fuera del eje publicado por Collotta et al.; no extrapolar sin ensayos."
    return CalculationResult(
        "Tzampoglou et al. (2026), ajuste de Collotta et al. (1989)",
        value,
        "grados",
        "phi_R = 21.2/exp(0.008*CALIP^1.5) + 7.7",
        "CALIP adimensional",
        "Angulo residual secante de corte anular; base italiana de 150 muestras; sigma'n aproximada 100-500 kPa.",
        "TZAMPOGLOU2026",
        warning,
    )


def cte_subgrade_modulus(k30_mn_m3: float, width_m: float, length_m: float, soil: str) -> CalculationResult:
    _positive("k30", k30_mn_m3)
    _positive("B", width_m)
    _positive("L", length_m)
    if width_m > length_m:
        raise ValueError("Use B como lado menor: debe cumplirse B <= L.")
    if soil == "Cohesivo":
        square = k30_mn_m3 * 0.3 / width_m
        formula = "ksB = ksp30*(0.3/B); ksBL = ksB*(1+B/(2L))"
    elif soil == "Granular":
        square = k30_mn_m3 * ((width_m + 0.3) / (2 * width_m)) ** 2
        formula = "ksB = ksp30*((B+0.3)/(2B))^2; ksBL = ksB*(1+B/(2L))"
    else:
        raise ValueError("Tipo de suelo no reconocido.")
    value = square * (1 + width_m / (2 * length_m))
    return CalculationResult(
        "CTE DB-SE-C, anejo E, eqs. E.6-E.8", value, "MN/m3", formula,
        "ksp30 en MN/m3; B y L en m; B <= L", "Zapata rectangular.", "CTE2019",
    )
