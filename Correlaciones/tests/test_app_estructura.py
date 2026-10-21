import unittest
from pathlib import Path


class TestEstructuraApp(unittest.TestCase):
    def test_hay_un_unico_editor_propietario_por_dataset(self) -> None:
        fuente = Path("app.py").read_text(encoding="utf-8")
        self.assertEqual(fuente.count("editor_datos("), 2)  # definicion y llamada en Datos
        self.assertNotIn("+**Ensayo", fuente)

    def test_no_anuncia_penetracion_dinamica_sin_implementar(self) -> None:
        fuente = Path("modelos/dominio.py").read_text(encoding="utf-8")
        self.assertNotIn("PENETRACION_DINAMICA", fuente)


if __name__ == "__main__":
    unittest.main()
