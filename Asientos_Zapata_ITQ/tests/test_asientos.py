import numpy as np
import pandas as pd

from calculos.asientos import calcular_caso, modulo_confinado_kpa
from modelos.datos import Cimentacion


def capas_uniformes() -> pd.DataFrame:
    return pd.DataFrame(
        [["Suelo", 0.0, 20.0, 18.0, 20.0, 25.0, 0.30, 33.65]],
        columns=["Estrato", "z_sup_m", "z_inf_m", "gamma_ap_kN_m3", "gamma_sat_kN_m3", "E_MPa", "nu", "M_MPa"],
    )


def test_conversion_modulo_confinado():
    capas = capas_uniformes()
    esperado = 25_000.0 * 0.7 / (1.3 * 0.4)
    assert np.isclose(modulo_confinado_kpa(capas, "E_nu")[0], esperado)


def test_asiento_positivo_y_menor_fuera_de_la_huella():
    resultado = calcular_caso(Cimentacion(2.0, 3.0, 150.0, 1.0), capas_uniformes(), "E_nu", 2.0, 10.0, 301)
    resumen = resultado.resumen_puntos.set_index("Punto")
    assert resumen.loc["Centro", "asiento_base_mm"] > 0.0
    assert resumen.loc["Centro", "asiento_base_mm"] > resumen.loc["Exterior B", "asiento_base_mm"]
    assert resultado.error_discretizacion_pct < 0.1


def test_area_extensa_reproduce_compresion_unidimensional():
    capas = capas_uniformes()
    cimentacion = Cimentacion(1000.0, 1000.0, 100.0, 0.0)
    resultado = calcular_caso(cimentacion, capas, "M", 50.0, 2.0, 401)
    calculado = resultado.resumen_puntos.set_index("Punto").loc["Centro", "asiento_base_mm"]
    esperado = 100.0 / (33.65 * 1000.0) * 2.0 * 1000.0
    assert np.isclose(calculado, esperado, rtol=2e-4)

