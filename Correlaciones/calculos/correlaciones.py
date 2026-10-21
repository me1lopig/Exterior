from __future__ import annotations

import math
import numpy as np

from modelos.esquemas import EstadoRevision, ResultadoCorrelacion


CTE_URL = "https://www.codigotecnico.org/pdf/Documentos/SE/DBSE-C.pdf"

# Tabla D.29 CTE DB SE-C, k30 orientativo en MN/m3.
# Los extremos abiertos (<, >) se guardan como None/inf para consulta;
# no se crean valores puntuales ficticios.
K30_TABLA = [
    ("Arcilla blanda", 15., 30.),
    ("Arcilla media", 30., 60.),
    ("Arcilla dura", 60., 200.),
    ("Limo", 15., 45.),
    ("Arena floja", 10., 30.),
    ("Arena media", 30., 90.),
    ("Arena compacta", 90., 200.),
    ("Grava arenosa floja", 70., 120.),
    ("Grava arenosa compacta", 120., 300.),
    ("Margas arcillosas", 200., 400.),
    ("Rocas algo alteradas", 300., 5000.),
    ("Rocas sanas", 5000., float('inf')),
]


def _finito_no_negativo(nombre: str, valor: float) -> float:
    valor = float(valor)
    if not math.isfinite(valor) or valor < 0:
        raise ValueError(f"{nombre} debe ser un número finito mayor o igual que cero.")
    return valor


def _positivo(nombre: str, valor: float) -> float:
    valor = float(valor)
    if not math.isfinite(valor) or valor <= 0:
        raise ValueError(f"{nombre} debe ser un número finito mayor que cero.")
    return valor


def _r(
    autor: str,
    aplicacion: str,
    formula: str,
    valor: float | None,
    unidad: str,
    parametros: str,
    *,
    aplicable: bool = True,
    estado: EstadoRevision = EstadoRevision.TRANSCRITA,
    criterio: str = "",
    nota: str = "",
    referencia: str = "Excel aportado por el usuario",
) -> ResultadoCorrelacion:
    if valor is not None and (not math.isfinite(valor) or valor < 0):
        aplicable = False
        nota = (nota + " Resultado no físico para las entradas indicadas.").strip()
    return ResultadoCorrelacion(
        autor=autor,
        aplicacion=aplicacion,
        formula=formula,
        valor=valor,
        unidad=unidad,
        parametros=parametros,
        aplicable=aplicable,
        estado=estado,
        criterio=criterio,
        nota=nota,
        referencia=referencia,
    )


# Cu: motor actualizado en calculos/cu_validado.py (v0.4).
# El bloque historico de 19 salidas no verificadas fue retirado deliberadamente.


def calcular_phi(nspt: float, ip: float) -> list[ResultadoCorrelacion]:
    """Deshabilitado: correlaciones no aprobadas en v0.4."""
    raise RuntimeError("Correlaciones de phi bloqueadas: falta normalización y verificación bibliográfica.")


def calcular_e_arenas(nspt: float) -> list[ResultadoCorrelacion]:
    """Deshabilitado: correlaciones no aprobadas en v0.4."""
    raise RuntimeError("Correlaciones de E-arenas bloqueadas: faltan fuentes y verificación de unidades.")


def _factor_cte_f2(ip: float, ocr: float) -> tuple[float | None, str]:
    if ip == 30 or ip == 50:
        return None, "El CTE deja abiertos los límites IP = 30 e IP = 50; requiere criterio de proyecto."
    columna = 0 if ip < 30 else 1 if ip < 50 else 2
    if ocr < 3:
        fila = 0
    elif ocr <= 5:
        fila = 1
    else:
        fila = 2
    factores = ((800, 350, 150), (600, 250, 100), (300, 130, 50))
    return float(factores[fila][columna]), ""


def calcular_e_arcillas(ip: float, nspt: float, cu_kpa: float, ocr: float) -> list[ResultadoCorrelacion]:
    """Solo la relacion Eu/cu CTE F.2. El argumento nspt queda obsoleto."""
    ip = _finito_no_negativo("IP", ip)
    cu = _positivo("c_u", cu_kpa)
    ocr = _positivo("OCR", ocr)
    if ocr < 1:
        raise ValueError("OCR debe ser mayor o igual que 1.")
    factor, nota = _factor_cte_f2(ip, ocr)
    return [_r(
        "CTE DB SE-C, tabla F.2",
        "Arcillas sobreconsolidadas: módulo de elasticidad sin drenaje",
        r"E_u=(E_u/c_u)c_u/1000",
        factor * cu / 1000 if factor is not None else None,
        "MPa", "IP [%], OCR [-], c_u [kPa]",
        aplicable=factor is not None,
        estado=EstadoRevision.VERIFICADA_CTE,
        criterio=f"E_u/c_u = {factor:g}" if factor is not None else "Límite abierto",
        nota=nota or "Valor orientativo CTE para asiento inmediato; requiere arcilla sobreconsolidada.",
        referencia=f"CTE DB SE-C, tabla F.2 ({CTE_URL})",
    )]


def calcular_e_cte(nspt: float) -> list[ResultadoCorrelacion]:
    """CTE D.23 tabular intervals + explicitly non-normative interpolation for 10 < N <= 50."""
    n = _finito_no_negativo("N_SPT", nspt)
    rangos = [
        ("Suelos muy flojos o muy blandos", "N < 10", n < 10,
         None, None, "q_u < 80 kPa; E < 8 MPa"),
        ("Suelos flojos o blandos", "10 ≤ N ≤ 25", 10 <= n <= 25,
         80 + 70 * (n - 10) / 15, 8 + 32 * (n - 10) / 15,
         "Interpolación lineal (hipótesis): q_u 80-150 kPa; E 8-40 MPa"),
        ("Suelos medios", "25 < N ≤ 50", 25 < n <= 50,
         150 + 150 * (n - 25) / 25, 40 + 60 * (n - 25) / 25,
         "Interpolación lineal (hipótesis): q_u 150-300 kPa; E 40-100 MPa"),
        ("Suelos compactos o duros", "N > 50 (rechazo)", n > 50,
         None, None, "q_u 300-500 kPa; E 100-500 MPa, sin interpolación"),
    ]
    resultados = []
    for nombre, criterio, aplica, qu, e, descripcion in rangos:
        for valor, unidad, magnitud in [(qu, "kPa", "q_u"), (e, "MPa", "E")]:
            resultados.append(_r(
                "CTE DB SE-C, tabla D.23", nombre,
                rf"\mathrm{{{magnitud}}}:\;\text{{{descripcion}}}",
                valor, unidad, "N_SPT", aplicable=aplica,
                estado=EstadoRevision.VERIFICADA_CTE if valor is None else EstadoRevision.INTERPOLACION,
                criterio=criterio,
                nota=("Valor tabulado como intervalo; no existe valor puntual normativo. " if valor is None else
                      "Estimación interpolada añadida al Excel, no prescrita por el CTE. ") + descripcion,
                referencia=f"CTE DB SE-C, tabla D.23 ({CTE_URL})",
            ))
    return resultados


def obtener_poisson() -> list[ResultadoCorrelacion]:
    datos = [
        ("Arcillas blandas normalmente consolidadas", 0.40),
        ("Arcillas medias", 0.30),
        ("Arcillas duras preconsolidadas", 0.15),
        ("Arenas y suelos granulares", 0.30),
    ]
    return [_r("CTE DB SE-C, tabla D.24", tipo, r"\nu=\mathrm{valor\ tabulado}", valor, "-", "Tipo de suelo", estado=EstadoRevision.VERIFICADA_CTE, referencia=f"CTE DB SE-C, tabla D.24 ({CTE_URL})") for tipo, valor in datos]



def calcular_k30(b: float, l: float, k30: float) -> list[ResultadoCorrelacion]:
    b = _positivo("B", b)
    l = _positivo("L", l)
    k30 = _finito_no_negativo("k30", k30)
    if l < b:
        raise ValueError("Debe cumplirse L ≥ B; B representa el lado menor de la cimentación.")
    k_coh = k30 * 0.3 / b
    k_gran = k30 * ((b + 0.3) / (2 * b)) ** 2
    factor_rect = 1 + b / (2 * l)
    return [
        _r("CTE DB SE-C, E.6", "Zapata cuadrada sobre terreno cohesivo", r"k_{sB}=k_{s30}(0.3/B)", k_coh, "MN/m³", "B, k30", estado=EstadoRevision.VERIFICADA_CTE, referencia=f"CTE DB SE-C, E.6 ({CTE_URL})"),
        _r("CTE DB SE-C, E.7", "Zapata cuadrada sobre terreno granular", r"k_{sB}=k_{s30}[(B+0.3)/(2B)]^2", k_gran, "MN/m³", "B, k30", estado=EstadoRevision.VERIFICADA_CTE, referencia=f"CTE DB SE-C, E.7 ({CTE_URL})"),
        _r("CTE DB SE-C, E.8", "Zapata rectangular sobre terreno cohesivo", r"k_{sBL}=k_{sB}(1+B/(2L))", k_coh * factor_rect, "MN/m³", "B, L, k30", estado=EstadoRevision.VERIFICADA_CTE, referencia=f"CTE DB SE-C, E.8 ({CTE_URL})"),
        _r("CTE DB SE-C, E.8", "Zapata rectangular sobre terreno granular", r"k_{sBL}=k_{sB}(1+B/(2L))", k_gran * factor_rect, "MN/m³", "B, L, k30", estado=EstadoRevision.VERIFICADA_CTE, referencia=f"CTE DB SE-C, E.8 ({CTE_URL})"),
    ]


def estadisticos_validos(resultados: list[ResultadoCorrelacion]) -> dict[str, float | int | None]:
    valores = np.array([r.valor for r in resultados if r.aplicable and r.valor is not None and r.valor > 0], dtype=float)
    if valores.size == 0:
        return {"n": 0, "mínimo": None, "máximo": None, "media": None, "desviación": None}
    return {
        "n": int(valores.size),
        "mínimo": float(valores.min()),
        "máximo": float(valores.max()),
        "media": float(valores.mean()),
        "desviación": float(valores.std(ddof=1)) if valores.size > 1 else 0.0,
    }
