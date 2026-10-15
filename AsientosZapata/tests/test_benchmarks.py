"""Contrastes independientes del motor analitico de asientos.

Referencias:
* Brown y Gibson (1973): https://trid.trb.org/View/139107
* Pantelidis (2021): https://doi.org/10.21203/rs.3.rs-252543/v1
"""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd
from numpy.polynomial.legendre import leggauss


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import funciones_asientos as fa


def _integrar_desplazamiento_boussinesq(p, B, L, E, nu, x, y, z, orden=80):
    """Integra el desplazamiento vertical de una carga puntual sobre B x L."""
    g, w = leggauss(orden)
    xs = 0.5 * B * g
    ys = 0.5 * L * g
    pesos = w[:, None] * w[None, :] * B * L / 4.0
    radio = np.sqrt((xs[:, None] - x) ** 2 + (ys[None, :] - y) ** 2 + z**2)
    nucleo = (1.0 + nu) / (2.0 * np.pi * E) * (
        2.0 * (1.0 - nu) / radio + z**2 / radio**3
    )
    return float(p * np.sum(pesos * nucleo))


def _integrar_tension_boussinesq(p, B, L, x, y, z, orden=80):
    """Integra sigma_z de una carga puntual sobre B x L."""
    g, w = leggauss(orden)
    xs = 0.5 * B * g
    ys = 0.5 * L * g
    pesos = w[:, None] * w[None, :] * B * L / 4.0
    radio = np.sqrt((xs[:, None] - x) ** 2 + (ys[None, :] - y) ** 2 + z**2)
    nucleo = 3.0 * z**3 / (2.0 * np.pi * radio**5)
    return float(p * np.sum(pesos * nucleo))


def _perfil_homogeneo(espesor=200.0, E=20_000.0, nu=0.3):
    return pd.DataFrame({
        "Descripción": ["Semiespacio de contraste"],
        "Espesor (m)": [espesor],
        "E (kPa)": [E],
        "nu": [nu],
        "Peso Esp. (kN/m³)": [18.0],
        "Peso Esp. Sat (kN/m³)": [20.0],
    })


class TestBenchmarksAnaliticos(unittest.TestCase):
    def test_factores_publicados_en_esquina_para_rectangulos(self):
        publicados = {1.0: 0.561, 1.5: 0.679, 2.0: 0.766,
                      3.0: 0.892, 5.0: 1.052, 10.0: 1.272}
        for relacion, esperado in publicados.items():
            calculado = fa.s_z(1.0, 1.0, 1.0, 0.0, 0.0, relacion)
            self.assertAlmostEqual(calculado, esperado, delta=5e-4)

    def test_centro_cuadrado_coincide_con_solucion_cerrada(self):
        p, B, E, nu = 150.0, 2.0, 20_000.0, 0.3
        factor_centro = 4.0 * np.arcsinh(1.0) / np.pi
        esperado = p * B / E * (1.0 - nu**2) * factor_centro
        calculado = fa.w_punto(p, B, B, E, nu, 0.0, 0.0, 0.0)
        self.assertAlmostEqual(calculado, esperado, places=12)

    def test_desplazamiento_interior_con_cuadratura_independiente(self):
        datos = dict(p=150.0, B=2.0, L=3.0, E=20_000.0, nu=0.3,
                     x=0.2, y=-0.4, z=1.3)
        esperado = _integrar_desplazamiento_boussinesq(**datos)
        calculado = fa.w_punto(**datos)
        self.assertAlmostEqual(calculado, esperado, delta=1e-10)

    def test_tension_central_holl_con_cuadratura_independiente(self):
        p, B, L, z = 150.0, 2.0, 3.0, 2.0
        esperado = _integrar_tension_boussinesq(p, B, L, 0.0, 0.0, z)
        calculado = float(fa.holl_centro(p, B, L, z)[0])
        self.assertAlmostEqual(calculado, esperado, delta=1e-9)

    def test_calculo_completo_homogeneo_con_corte_profundo(self):
        p, B, L, E, nu, z_max = 150.0, 2.0, 3.0, 20_000.0, 0.3, 100.0
        resultado = fa.calcular_steinbrenner_zapata(
            p, B, L, _perfil_homogeneo(E=E, nu=nu), z_max
        )
        superficie = 2.0 * p * (1.0 - nu**2) / (np.pi * E) * (
            B * np.arcsinh(L / B) + L * np.arcsinh(B / L)
        )
        corte = _integrar_desplazamiento_boussinesq(
            p, B, L, E, nu, 0.0, 0.0, z_max
        )
        self.assertAlmostEqual(resultado.total, superficie - corte, delta=2e-6)

    def test_caso_publicado_cuadrado_flexible_h_sobre_b_4(self):
        # Pantelidis (2021), tabla 5: A_Ce = rho E / (q B), B=L=1 y H/B=4.
        publicados = {0.0: 1.004, 0.1: 0.990, 0.2: 0.954, 0.3: 0.898,
                      0.4: 0.821, 0.45: 0.775, 0.499: 0.724}
        for nu, esperado in publicados.items():
            resultado = fa.calcular_steinbrenner_zapata(
                1.0, 1.0, 1.0, _perfil_homogeneo(espesor=4.0, E=1.0, nu=nu), 4.0
            )
            self.assertAlmostEqual(resultado.total, esperado, delta=1e-3)


@unittest.skipUnless(fa.OPENSEES_DISPONIBLE, "OpenSeesPy no esta instalado")
class TestBenchmarkOpenSees(unittest.TestCase):
    def test_medio_homogeneo_frente_a_steinbrenner(self):
        """Prueba de integracion; tolerancia compatible con dominio y malla finitos."""
        df = _perfil_homogeneo(espesor=40.0)
        st = fa.calcular_steinbrenner_zapata(100.0, 2.0, 2.0, df, 8.0)
        mef = fa.calcular_opensees_3d(
            100.0, 2.0, 2.0, df, 8.0,
            tamaño_malla=0.5, factor_dominio=8.0, factor_prof=4.0,
            graduada=True, tamaño_max=1.5,
        )
        error = abs(mef.total - st.total) / st.total
        self.assertLess(error, 0.12)
        self.assertLess(mef.error_equilibrio, 1e-4)


if __name__ == "__main__":
    unittest.main()
