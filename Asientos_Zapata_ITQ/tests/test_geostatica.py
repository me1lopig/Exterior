import numpy as np
import pandas as pd

from calculos.geostatica import integrar_peso_especifico


def test_tensiones_con_nivel_freatico_en_interfaz():
    capas = pd.DataFrame(
        {
            "z_sup_m": [0.0, 2.0], "z_inf_m": [2.0, 10.0],
            "gamma_ap_kN_m3": [18.0, 19.0], "gamma_sat_kN_m3": [20.0, 21.0],
        }
    )
    total, u, efectiva = integrar_peso_especifico(np.array([0.0, 2.0, 5.0]), capas, 2.0)
    assert np.allclose(total, [0.0, 36.0, 99.0])
    assert np.allclose(u, [0.0, 0.0, 29.43])
    assert np.allclose(efectiva, total - u)

