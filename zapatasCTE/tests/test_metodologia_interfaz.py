"""Regresión de la separación entre metodología documental y datos numéricos."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SeparacionMetodologiaTest(unittest.TestCase):
    def test_metodologia_no_contiene_tablas_ni_memoria_numerica(self):
        ruta = ROOT / "visualizacion" / "metodologia.py"
        arbol = ast.parse(ruta.read_text(encoding="utf-8"))
        funciones = {
            nodo.name: nodo for nodo in arbol.body if isinstance(nodo, ast.FunctionDef)
        }
        self.assertIn("mostrar_compendio", funciones)
        self.assertIn("mostrar_memoria_numerica", funciones)

        compendio = ast.get_source_segment(
            ruta.read_text(encoding="utf-8"), funciones["mostrar_compendio"]
        )
        memoria = ast.get_source_segment(
            ruta.read_text(encoding="utf-8"), funciones["mostrar_memoria_numerica"]
        )
        self.assertNotIn("st.dataframe(", compendio)
        self.assertNotIn("elaborar_memoria(", compendio)
        self.assertEqual(memoria.count("st.dataframe("), 2)
        self.assertIn("elaborar_memoria(", memoria)

    def test_las_tablas_estan_en_ficha_bxl_y_no_en_metodologia(self):
        codigo = (ROOT / "app.py").read_text(encoding="utf-8")
        inicio = codigo.index("    with an_tab:")
        corridas = codigo.index("    with co_tab:")
        met = codigo.index("    with met_tab:")
        self.assertLess(inicio, corridas)
        self.assertLess(corridas, met)
        self.assertIn("mostrar_memoria_numerica(", codigo[inicio:corridas])
        self.assertNotIn("mostrar_memoria_numerica(", codigo[corridas:met])
        self.assertIn("mostrar_compendio()", codigo[met:])
        self.assertNotIn("mostrar_memoria_numerica(", codigo[met:])


if __name__ == "__main__":
    unittest.main()
