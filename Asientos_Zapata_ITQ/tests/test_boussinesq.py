import numpy as np

from calculos.boussinesq import incremento_tension_rectangular, influencia_esquina


def test_influencia_esquina_cuadrado_unitario():
    assert np.isclose(float(influencia_esquina(1.0, 1.0)), 0.175221, rtol=2e-5)


def test_limite_area_muy_grande_bajo_centro():
    sigma = incremento_tension_rectangular(0.0, 0.0, 1.0, 1.0e5, 1.0e5, 100.0)
    assert np.isclose(float(sigma), 100.0, rtol=1e-5)


def test_tension_en_superficie_y_simetria():
    interior = incremento_tension_rectangular(0.0, 0.0, 0.0, 2.0, 4.0, 150.0)
    exterior = incremento_tension_rectangular(2.0, 0.0, 0.0, 2.0, 4.0, 150.0)
    izquierda = incremento_tension_rectangular(-0.7, 0.4, 2.0, 2.0, 4.0, 150.0)
    derecha = incremento_tension_rectangular(0.7, -0.4, 2.0, 2.0, 4.0, 150.0)
    assert float(interior) == 150.0
    assert float(exterior) == 0.0
    assert np.isclose(float(izquierda), float(derecha), rtol=1e-12)


def test_tension_decrece_en_eje_central():
    z = np.array([0.0, 0.5, 1.0, 2.0, 5.0, 10.0])
    sigma = incremento_tension_rectangular(np.zeros_like(z), np.zeros_like(z), z, 2.0, 3.0, 100.0)
    assert np.all(np.diff(sigma) < 0.0)
    assert np.all((sigma >= 0.0) & (sigma <= 100.0))

