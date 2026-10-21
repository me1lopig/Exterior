"""Correlaciones SPT y tablas del CTE DB-SE-C."""

from __future__ import annotations

import math

from calculos.errores import ErrorCalculoGeotecnico, FueraDeDominio
from calculos.interpolacion import fraccion_intervalo, interpolar_lineal
from modelos.dominio import EstadoResultado, MetodoInterpolacion, Resultado, TipoN


N_PHI_CTE = (10.0, 15.0, 22.0, 30.0, 36.0, 45.0, 55.0)
PHI_CTE = (30.0, 32.0, 34.0, 36.0, 38.0, 40.0, 42.0)


def _validar_n(n: float) -> None:
    if not math.isfinite(n) or n < 0:
        raise ErrorCalculoGeotecnico("N debe ser un numero finito no negativo.")


def _advertencia_tipo_n(tipo_n: str, esperado: TipoN) -> list[str]:
    if tipo_n == esperado.value:
        return []
    return [
        f"La fuente emplea {esperado.value}; se ha recibido {tipo_n}. "
        "La compatibilidad debe ser justificada por el proyectista."
    ]


def phi_cte_41(
    n: float,
    tipo_n: str,
    tipo_suelo: str,
    porcentaje_mayor_20mm: float | None = None,
) -> Resultado:
    """Interpola la tabla 4.1 del CTE para suelos granulares limpios."""
    _validar_n(n)
    suelos_admitidos = {"Grava limpia", "Arena limpia", "Limo no cohesivo"}
    if tipo_suelo not in suelos_admitidos:
        raise FueraDeDominio(
            "La tabla 4.1 se limita a granulares limpios sin cohesion y limos no cohesivos."
        )
    if porcentaje_mayor_20mm is not None:
        if not math.isfinite(porcentaje_mayor_20mm) or porcentaje_mayor_20mm < 0:
            raise ErrorCalculoGeotecnico(
                "El porcentaje de particulas mayores de 20 mm debe ser finito y no negativo."
            )
        if porcentaje_mayor_20mm > 30:
            raise FueraDeDominio(
                "El CTE limita este uso a contenidos <=30 % de particulas mayores de 20 mm."
            )
    phi = interpolar_lineal(n, N_PHI_CTE, PHI_CTE)
    avisos = _advertencia_tipo_n(tipo_n, TipoN.N_CTE)
    condicionado = bool(avisos)
    return Resultado(
        correlacion_id="RES-PHI-SPT-CTE2019-T41",
        parametro="phi_eff",
        valor=phi,
        unidad="grados",
        interpolado=n not in N_PHI_CTE,
        valido=not condicionado,
        estado=EstadoResultado.CONDICIONADO if condicionado else EstadoResultado.VALIDO,
        advertencias=avisos,
        metadatos={"n": n, "tipo_n": tipo_n, "tipo_suelo": tipo_suelo, "tabla": "CTE 4.1"},
    )


def _intervalo_d23(n: float, parametro: str) -> tuple[float | None, float | None, str]:
    _validar_n(n)
    if parametro not in {"qu", "E"}:
        raise ErrorCalculoGeotecnico("Parametro D.23 no reconocido.")
    if n < 10:
        return (0.0, 80.0, "Muy flojo o muy blando") if parametro == "qu" else (None, 8.0, "Muy flojo o muy blando")
    if n <= 25:
        return (80.0, 150.0, "Flojo o blando") if parametro == "qu" else (8.0, 40.0, "Flojo o blando")
    if n <= 50:
        return (150.0, 300.0, "Medio") if parametro == "qu" else (40.0, 100.0, "Medio")
    return (300.0, 500.0, "Compacto o duro") if parametro == "qu" else (100.0, 500.0, "Compacto o duro")


def tabla_d23(
    n: float,
    tipo_n: str,
    parametro: str,
    metodo: MetodoInterpolacion,
    tipo_suelo: str | None = None,
) -> Resultado:
    """Evalua literalmente o interpola los intervalos cerrados de D.23."""
    if tipo_suelo in {"Roca", "Otro"}:
        raise FueraDeDominio("La evaluacion numerica D.23 implementada no cubre roca ni suelos sin clasificar.")
    if parametro == "qu" and tipo_suelo not in {"Arcilla", "Limo cohesivo"}:
        raise FueraDeDominio(
            "La resistencia a compresion simple qu de D.23 solo se aplica a suelos cohesivos."
        )
    minimo, maximo, clase = _intervalo_d23(n, parametro)
    unidad = "kPa" if parametro == "qu" else "MPa"
    corr_id = "RES-QU-SPT-CTE2019-D23" if parametro == "qu" else "DEF-E-SPT-CTE2019-D23"
    avisos = _advertencia_tipo_n(tipo_n, TipoN.N_CTE)
    if n in {25, 50}:
        avisos.append(
            "Convencion GeoCorr: el limite compartido se asigna al intervalo inferior de la tabla D.23."
        )
    valor: float | None = None
    interpolado = False
    if metodo == MetodoInterpolacion.LINEAL:
        avisos.append(
            "Interpolacion lineal adoptada por GeoCorr; el CTE D.23 publica rangos y no prescribe esta interpolacion."
        )
        if 10 <= n <= 25:
            f = fraccion_intervalo(n, 10, 25)
            y0, y1 = ((80.0, 150.0) if parametro == "qu" else (8.0, 40.0))
            valor = y0 + f * (y1 - y0)
            interpolado = n not in {10, 25}
        elif 25 < n <= 50:
            f = fraccion_intervalo(n, 25, 50)
            y0, y1 = ((150.0, 300.0) if parametro == "qu" else (40.0, 100.0))
            valor = y0 + f * (y1 - y0)
            interpolado = n not in {25, 50}
        else:
            avisos.append(
                "No existe un intervalo numerico cerrado para interpolar; se conserva el rango literal."
            )
    incompatibilidad_n = bool(_advertencia_tipo_n(tipo_n, TipoN.N_CTE))
    return Resultado(
        correlacion_id=corr_id,
        parametro=parametro,
        valor=valor,
        minimo=minimo,
        maximo=maximo,
        unidad=unidad,
        valido=not incompatibilidad_n,
        estado=EstadoResultado.CONDICIONADO if incompatibilidad_n else EstadoResultado.VALIDO,
        interpolado=interpolado,
        categoria=clase,
        advertencias=avisos,
        metadatos={
            "n": n,
            "tipo_n": tipo_n,
            "tipo_suelo": tipo_suelo,
            "clase_cte": clase,
            "tabla": "CTE D.23",
            "interpolacion": "Adoptada por GeoCorr; no prescrita por el CTE" if metodo == MetodoInterpolacion.LINEAL else "No aplicada",
        },
    )


def es_fhwa(n: float, tipo_n: str, factor: float, correlacion_id: str) -> Resultado:
    """Calcula Es/pa = factor*N60, con pa=0.101325 MPa."""
    _validar_n(n)
    if factor not in {5.0, 10.0, 15.0}:
        raise ErrorCalculoGeotecnico("Factor FHWA no implementado.")
    valor = factor * n * 0.101325
    avisos = _advertencia_tipo_n(tipo_n, TipoN.N60)
    return Resultado(
        correlacion_id=correlacion_id,
        parametro="Es",
        valor=valor,
        unidad="MPa",
        valido=not avisos,
        estado=EstadoResultado.CONDICIONADO if avisos else EstadoResultado.VALIDO,
        advertencias=avisos,
        metadatos={"n": n, "tipo_n": tipo_n, "factor": factor, "pa_mpa": 0.101325},
    )


def indice_compresibilidad_cte(n_medio: float, tipo_n: str) -> Resultado:
    """Evalua las expresiones F.24-F.26 del CTE."""
    _validar_n(n_medio)
    if n_medio < 7:
        raise FueraDeDominio("El CTE no considera aplicable el metodo para NSPT < 7.")
    potencia = n_medio**1.4
    avisos_tipo_n = _advertencia_tipo_n(tipo_n, TipoN.N_CTE)
    avisos = avisos_tipo_n.copy()
    avisos.append("N debe representar la media en la zona de influencia de la cimentacion.")
    return Resultado(
        correlacion_id="DEF-IC-SPT-CTE2019-F24",
        parametro="Ic",
        valor=1.71 / potencia,
        minimo=0.94 / potencia,
        maximo=3.0 / potencia,
        unidad="adimensional",
        valido=not avisos_tipo_n,
        estado=EstadoResultado.CONDICIONADO if avisos_tipo_n else EstadoResultado.VALIDO,
        advertencias=avisos,
        metadatos={"n_medio": n_medio, "tipo_n": tipo_n, "expresiones": "F.24-F.26"},
    )


POISSON_CTE = {
    "Arcilla blanda NC": 0.40,
    "Arcilla media": 0.30,
    "Arcilla dura OC": 0.15,
    "Arena o suelo granular": 0.30,
}

DENSIDADES_CTE = {
    "Grava": {"gamma_sat": (20.0, 22.0), "gamma_d": (15.0, 17.0)},
    "Arena": {"gamma_sat": (18.0, 20.0), "gamma_d": (13.0, 16.0)},
    "Limo": {"gamma_sat": (18.0, 20.0), "gamma_d": (14.0, 18.0)},
    "Arcilla": {"gamma_sat": (16.0, 22.0), "gamma_d": (14.0, 21.0)},
}

PROPIEDADES_BASICAS_CTE = {
    "Grava natural": {"gamma": (19.0, 22.0), "phi": (34.0, 45.0)},
    "Arena natural": {"gamma": (17.0, 20.0), "phi": (30.0, 36.0)},
    "Limo natural": {"gamma": (17.0, 20.0), "phi": (25.0, 32.0)},
    "Arcilla natural": {"gamma": (15.0, 22.0), "phi": (16.0, 28.0)},
    "Tierra vegetal": {"gamma": (17.0, 17.0), "phi": (25.0, 25.0)},
    "Terraplen": {"gamma": (17.0, 17.0), "phi": (30.0, 30.0)},
    "Pedraplen": {"gamma": (18.0, 18.0), "phi": (40.0, 40.0)},
}

PERMEABILIDAD_CTE = {
    "Grava limpia": (1e-2, None),
    "Arena limpia o grava y arena limpia": (1e-5, 1e-2),
    "Arena fina, limo o mezcla con arcilla": (1e-9, 1e-5),
    "Arcilla": (None, 1e-9),
}

K30_CTE = {
    "Arcilla blanda": (15.0, 30.0),
    "Arcilla media": (30.0, 60.0),
    "Arcilla dura": (60.0, 200.0),
    "Limo": (15.0, 45.0),
    "Arena floja": (10.0, 30.0),
    "Arena media": (30.0, 90.0),
    "Arena compacta": (90.0, 200.0),
    "Grava arenosa floja": (70.0, 120.0),
    "Grava arenosa compacta": (120.0, 300.0),
    "Margas arcillosas": (200.0, 400.0),
    "Roca algo alterada": (300.0, 5000.0),
    "Roca sana": (5000.0, None),
}
