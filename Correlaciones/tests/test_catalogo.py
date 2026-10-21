import unittest

from servicios.catalogo import CORRELACIONES, FUENTES


class TestCatalogo(unittest.TestCase):
    def test_identificadores_y_fuentes(self) -> None:
        self.assertEqual(len(CORRELACIONES), len(set(CORRELACIONES)))
        for identificador, correlacion in CORRELACIONES.items():
            self.assertEqual(identificador, correlacion.id)
            self.assertIn(correlacion.fuente_id, FUENTES)
            self.assertTrue(correlacion.entradas_requeridas)
            self.assertTrue(correlacion.dominio)
            self.assertTrue(correlacion.formula)
            self.assertTrue(correlacion.version_metodo)

    def test_urls_de_fuente(self) -> None:
        for fuente in FUENTES.values():
            self.assertTrue(fuente.url.startswith("https://"))
        self.assertEqual(FUENTES["ISO22476-4"].url, "https://www.iso.org/standard/75662.html")
        self.assertEqual(FUENTES["FHWA1989-PMT"].url, "https://rosap.ntl.bts.gov/view/dot/74774")


if __name__ == "__main__":
    unittest.main()
