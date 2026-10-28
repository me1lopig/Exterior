import unittest

from calculos.consolidacion import degree_of_consolidation, primary_settlement_slice, time_for_degree


class ConsolidationTests(unittest.TestCase):
    def test_cada_cv_produce_su_propia_evolucion(self):
        slow = degree_of_consolidation(0.1, 0.1, 1.0)
        fast = degree_of_consolidation(0.1, 10.0, 1.0)
        self.assertLess(slow, fast)
        self.assertGreater(0.5 * slow + 0.5 * fast, 0.50)

    def test_t95_se_recupera_con_la_serie(self):
        time = time_for_degree(0.95, 0.8, 1.5)
        self.assertAlmostEqual(degree_of_consolidation(time, 0.8, 1.5), 0.95, places=10)

    def test_preconsolidacion_inconsistente_se_rechaza(self):
        with self.assertRaisesRegex(ValueError, "preconsolidacion"):
            primary_settlement_slice(1.0, 120.0, 30.0, 100.0, 0.25, 0.04, 0.8)


if __name__ == "__main__":
    unittest.main()
