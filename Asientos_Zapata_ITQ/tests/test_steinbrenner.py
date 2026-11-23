import numpy as np
import pandas as pd

from calculos.steinbrenner import (
    calcular_steinbrenner,
    compresion_esquina_m,
    compresion_rectangulo_m,
    factores_influencia,
)
from modelos.datos import Cimentacion


def _capas() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["C1", 0.0, 3.0, 18.0, 20.0, 20.0, 0.30],
            ["C2", 3.0, 15.0, 19.0, 21.0, 40.0, 0.25],
        ],
        columns=["Estrato", "z_sup_m", "z_inf_m", "gamma_ap_kN_m3", "gamma_sat_kN_m3", "E_MPa", "nu"],
    )


def test_factores_nulos_para_espesor_nulo():
    assert factores_influencia(2.0, 0.0) == (0.0, 0.0)


def test_compresion_crece_con_espesor_y_disminuye_con_e():
    s1 = compresion_esquina_m(2.0, 3.0, 1.0, 100.0, 20.0, 0.30)
    s2 = compresion_esquina_m(2.0, 3.0, 5.0, 100.0, 20.0, 0.30)
    s3 = compresion_esquina_m(2.0, 3.0, 5.0, 100.0, 40.0, 0.30)
    assert 0.0 < s1 < s2
    assert np.isclose(s3, 0.5 * s2, rtol=1e-12)


def test_centro_equivale_a_cuatro_cuadrantes():
    centro = compresion_rectangulo_m(0.0, 0.0, 5.0, 2.0, 4.0, 100.0, 25.0, 0.30)
    esquina_cuarto = compresion_esquina_m(1.0, 2.0, 5.0, 100.0, 25.0, 0.30)
    assert np.isclose(centro, 4.0 * esquina_cuarto, rtol=1e-12)


def test_aditividad_de_dos_capas_identicas():
    capas = _capas()
    capas[["E_MPa", "nu"]] = [30.0, 0.30]
    resultado = calcular_steinbrenner(Cimentacion(2.0, 3.0, 100.0, 0.0), capas, 10.0)
    suma = resultado.resumen_estratos["asiento_mm"].sum()
    directo = compresion_rectangulo_m(0.0, 0.0, 10.0, 2.0, 3.0, 100.0, 30.0, 0.30) * 1000.0
    assert np.isclose(suma, directo, rtol=1e-12)


def test_resultados_positivos_y_menores_fuera_de_huella():
    resultado = calcular_steinbrenner(Cimentacion(2.0, 3.0, 120.0, 1.0), _capas(), 10.0)
    puntos = resultado.resumen_puntos.set_index("Punto")
    assert puntos.loc["Centro", "asiento_base_mm"] > 0.0
    assert puntos.loc["Centro", "asiento_base_mm"] > puntos.loc["Exterior B", "asiento_base_mm"] > 0.0


def test_perfil_refinado_conserva_asiento_y_nodos_de_interfaz():
    resultado = calcular_steinbrenner(
        Cimentacion(2.0, 3.0, 120.0, 1.0), _capas(), 10.0, paso_perfil_m=0.20
    )
    centro = resultado.perfiles[resultado.perfiles["Punto"] == "Centro"]
    asiento = resultado.resumen_puntos.set_index("Punto").loc["Centro", "asiento_base_mm"]
    assert len(centro) > 20
    assert np.isclose(centro.iloc[0]["desplazamiento_mm"], asiento, rtol=1e-12)
    assert abs(float(centro.iloc[-1]["desplazamiento_mm"])) < 1e-10
    assert centro["es_interfaz"].any()


def test_validacion_acepta_poisson_cero_y_rechaza_limites_invalidos():
    from modelos.datos import validar_estratos
    capas = _capas()
    capas.loc[0, "nu"] = 0.0
    _, errores = validar_estratos(capas, 10.0)
    assert not errores
    capas.loc[0, "nu"] = 0.5
    _, errores = validar_estratos(capas, 10.0)
    assert any("nu" in error for error in errores)
    capas.loc[0, "nu"] = -0.1
    _, errores = validar_estratos(capas, 10.0)
    assert any("nu" in error for error in errores)
