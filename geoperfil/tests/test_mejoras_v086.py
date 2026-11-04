"""Regresiones de persistencia, escalas y estados de contactos de v0.8.6."""
from __future__ import annotations

import json
import unittest

import pandas as pd

from perfil_geologico import __version__
from perfil_geologico.calculos.contactos import actualizar_vertices
from perfil_geologico.calculos.estilos_unidades import aplicar_edicion_unidades
from perfil_geologico.modelos.dominio import Contacto, Proyecto, VerticeContacto
from perfil_geologico.servicios.datos_demo import crear_datos_demo
from perfil_geologico.servicios.exportacion import contactos_a_csv, contactos_a_dxf
from perfil_geologico.servicios.persistencia import proyecto_a_json, proyecto_desde_json


class MejorasV086Tests(unittest.TestCase):
    def test_json_es_estandar_y_contiene_metadatos(self) -> None:
        datos = crear_datos_demo()
        datos["Ensayos_DPSH"].loc[0, "cota_inicio_m"] = float("nan")
        bruto = proyecto_a_json(Proyecto(), datos)
        contenido = json.loads(
            bruto,
            parse_constant=lambda valor: (_ for _ in ()).throw(
                ValueError(f"Constante no estándar: {valor}")
            ),
        )
        self.assertIsNone(contenido["datos"]["Ensayos_DPSH"][0]["cota_inicio_m"])
        self.assertEqual(contenido["meta"]["version_aplicacion"], __version__)

    def test_proyecto_antiguo_conserva_exageracion_exacta(self) -> None:
        proyecto = Proyecto.from_dict({"exageracion_vertical": 2.5})
        self.assertEqual(proyecto.escala_horizontal, 1000.0)
        self.assertEqual(proyecto.escala_vertical, 400.0)
        self.assertEqual(proyecto.exageracion_vertical, 2.5)

    def test_escalas_persisten_en_ida_y_vuelta(self) -> None:
        original = Proyecto(escala_horizontal=500.0, escala_vertical=200.0,
                            exageracion_vertical=2.5)
        recuperado, _ = proyecto_desde_json(
            proyecto_a_json(original, crear_datos_demo())
        )
        self.assertEqual(
            (recuperado.escala_horizontal, recuperado.escala_vertical,
             recuperado.exageracion_vertical),
            (500.0, 200.0, 2.5),
        )

    def test_contacto_bloqueado_no_admite_edicion_numerica(self) -> None:
        contacto = Contacto(
            "C1", "Contacto", "R", "AL", bloqueado=True,
            vertices=[VerticeContacto(0.0, 10.0), VerticeContacto(5.0, 8.0)],
        )
        tabla = pd.DataFrame([
            {"s_m": 0.0, "z_m": 9.0, "origen": "interpretado",
             "referencia": "", "interfaz_id": ""},
            {"s_m": 5.0, "z_m": 8.0, "origen": "interpretado",
             "referencia": "", "interfaz_id": ""},
        ])
        with self.assertRaisesRegex(ValueError, "bloqueado"):
            actualizar_vertices(contacto, tabla)

    def test_ordenes_de_unidad_deben_ser_unicos(self) -> None:
        unidades = crear_datos_demo()["Unidades"].iloc[:2].copy()
        cambios = {
            str(fila.unidad_id): {
                "nombre": fila.nombre, "color": fila.color, "orden": 1,
            }
            for fila in unidades.itertuples(index=False)
        }
        with self.assertRaisesRegex(ValueError, "duplicados"):
            aplicar_edicion_unidades(unidades, [], cambios)

    def test_contacto_oculto_no_se_exporta_como_geometria(self) -> None:
        contacto = Contacto(
            "C1", "Oculto", "R", "AL", visible=False,
            vertices=[VerticeContacto(0.0, 10.0), VerticeContacto(5.0, 8.0)],
        )
        dxf = contactos_a_dxf([contacto]).decode("ascii")
        self.assertNotIn("VERTEX", dxf)
        csv = contactos_a_csv([contacto]).decode("utf-8-sig")
        self.assertIn("visible", csv.splitlines()[0])
        self.assertIn("False", csv)


if __name__ == "__main__":
    unittest.main()
