import numpy as np
import pandas as pd

from calculos.rigidez import AjusteRigidez, tabla_aportes_con_porcentaje


def test_modelo_flexible_no_modifica_asiento():
    ajuste = AjusteRigidez()
    assert ajuste.tipo == "Flexible"
    assert ajuste.asiento_adoptado_mm(12.5) == 12.5


def test_modelo_rigido_aplica_factor_al_centro():
    ajuste = AjusteRigidez(considerar_rigida=True, factor=0.80)
    assert ajuste.tipo == "Rígida simplificada"
    assert np.isclose(ajuste.asiento_adoptado_mm(12.5), 10.0)


def test_factor_fuera_de_rango_se_rechaza():
    assert AjusteRigidez(True, 0.0).validar()
    assert AjusteRigidez(True, 1.01).validar()


def test_porcentajes_de_aporte_suman_cien():
    tabla = pd.DataFrame({"Estrato": ["A", "B"], "asiento_mm": [3.0, 7.0]})
    salida = tabla_aportes_con_porcentaje(tabla)
    assert np.isclose(salida["aporte_pct"].sum(), 100.0)
