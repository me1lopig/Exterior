import unittest

from calculos.asientos import calculate_settlement
from modelos.datos import AnalysisOptions, Foundation, Layer
from servicios.exportacion import detailed_csv_bytes, export_bundle_bytes, result_manifest


class ExportTests(unittest.TestCase):
    def test_csv_neutraliza_formulas_y_bundle_es_zip(self):
        foundation = Foundation(shape="rectangular", pressure_basis="neta", load_mode="presion", pressure_kpa=50.0)
        layers = [Layer("=CMD()", "granular", 15.0, 18.0, 20.0, 30.0)]
        options = AnalysisOptions(dz_m=0.5, immediate_model="edometrico_1d")
        result = calculate_settlement(foundation, layers, options, None)
        csv_text = detailed_csv_bytes(result).decode("utf-8-sig")
        self.assertIn("'=CMD()", csv_text)
        manifest = result_manifest(result, foundation, layers, options, None)
        self.assertTrue(export_bundle_bytes(result, manifest).startswith(b"PK"))


if __name__ == "__main__":
    unittest.main()
