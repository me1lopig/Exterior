import unittest

import pandas as pd

from modelos.datos import DatosProyecto, EstadoNF, Severidad
from modelos.validacion import validar_datos


class ValidationTests(unittest.TestCase):
    def _data(self) -> DatosProyecto:
        return DatosProyecto(
            perfiles=pd.DataFrame(
                [{"perfil": "P", "orden": 0, "estacion": "S-01", "tipo": "Sondeo", "distancia_m": 100, "cota_m": 50}]
            ),
            litologia=pd.DataFrame(
                [{"sondeo": "S-01", "profundidad_inicial_m": 0, "profundidad_final_m": 5, "descripcion_corta": "Grava", "descripcion": ""}]
            ),
            dpsh=pd.DataFrame(columns=["ensayo", "profundidad_m", "golpes"]),
            ensayos=pd.DataFrame(columns=["sondeo", "tipo", "profundidad_m"]),
            ugeo=pd.DataFrame(columns=["sondeo", "profundidad_inicial_m", "profundidad_final_m", "codigo", "descripcion"]),
            nivel_freatico=pd.DataFrame(
                [{"sondeo": "S-01", "estado": EstadoNF.REVISAR.value, "profundidad_m": 0.0}]
            ),
        )

    def test_zero_imported_is_blocking_until_resolved(self):
        data = self._data()
        issues = validar_datos(data, ["P"])
        self.assertTrue(any(issue.severidad == Severidad.ERROR and issue.tabla == "Nivel freatico" for issue in issues))
        data.nivel_freatico.loc[0, "estado"] = EstadoNF.DETECTADO.value
        issues = validar_datos(data, ["P"])
        self.assertFalse(any(issue.severidad == Severidad.ERROR for issue in issues))

    def test_no_detectado_does_not_require_depth(self):
        data = self._data()
        data.nivel_freatico.loc[0, "estado"] = EstadoNF.NO_DETECTADO.value
        data.nivel_freatico.loc[0, "profundidad_m"] = None
        issues = validar_datos(data, ["P"])
        self.assertFalse(any(issue.severidad == Severidad.ERROR for issue in issues))

    def test_inverted_stratum_is_an_error(self):
        data = self._data()
        data.nivel_freatico.loc[0, "estado"] = EstadoNF.DETECTADO.value
        data.litologia.loc[0, "profundidad_final_m"] = 0
        issues = validar_datos(data, ["P"])
        self.assertTrue(any(issue.tabla == "Litologia" and issue.severidad == Severidad.ERROR for issue in issues))


if __name__ == "__main__":
    unittest.main()

