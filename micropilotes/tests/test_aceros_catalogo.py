import unittest
from dataclasses import asdict
from modelos.aceros_catalogo import CALIDADES


class CatalogoAceroTests(unittest.TestCase):
    def test_tabla_completa(self):
        self.assertEqual(set(CALIDADES), {'S235', 'S275', 'S355', 'S550', 'J55', 'K55', 'N80'})
        self.assertEqual(asdict(CALIDADES['S355']), {
            'norma_tabla': 'EN 10025', 'limite_elastico_mpa': '355',
            'resistencia_traccion_mpa': '490-630', 'alargamiento_min_pct': 22})
        self.assertEqual(CALIDADES['N80'].limite_elastico_mpa, '552-758')
        self.assertEqual(CALIDADES['K55'].resistencia_traccion_mpa, '655')


if __name__ == '__main__':
    unittest.main()
