from __future__ import annotations

import json
import unittest

import numpy as np
import pandas as pd

from perfil_geologico.calculos.contactos import contactos_observados, detectar_cruces, interpolar_contacto
from perfil_geologico.calculos.proyeccion import longitud_eje, proyectar_puntos
from perfil_geologico.calculos.zonas import construir_zonas
from perfil_geologico.modelos.dominio import Contacto, Proyecto, VerticeContacto
from perfil_geologico.servicios.datos_demo import crear_datos_demo
from perfil_geologico.servicios.exportacion import contactos_a_dxf
from perfil_geologico.servicios.importar_excel import crear_plantilla_excel, leer_excel
from perfil_geologico.servicios.persistencia import proyecto_a_json, proyecto_desde_json
from perfil_geologico.utiles.validacion import validar_datos


class ProyeccionTests(unittest.TestCase):
    def test_proyeccion_sobre_eje_recto(self) -> None:
        eje = pd.DataFrame({"x_m": [0.0, 100.0], "y_m": [0.0, 0.0]})
        puntos = pd.DataFrame({"id": ["A", "B"], "x_m": [25.0, 75.0], "y_m": [4.0, -3.0]})
        resultado = proyectar_puntos(puntos, eje)
        np.testing.assert_allclose(resultado["s_m"], [25.0, 75.0])
        np.testing.assert_allclose(resultado["distancia_eje_m"], [4.0, -3.0])
        self.assertAlmostEqual(longitud_eje(eje), 100.0)

    def test_proyeccion_sobre_eje_quebrado(self) -> None:
        eje = pd.DataFrame({"x_m": [0.0, 10.0, 10.0], "y_m": [0.0, 0.0, 10.0]})
        puntos = pd.DataFrame({"x_m": [12.0], "y_m": [6.0]})
        resultado = proyectar_puntos(puntos, eje)
        self.assertAlmostEqual(resultado.loc[0, "s_m"], 16.0)
        self.assertAlmostEqual(abs(resultado.loc[0, "distancia_eje_m"]), 2.0)


class DatosTests(unittest.TestCase):
    def setUp(self) -> None:
        self.datos = crear_datos_demo()

    def test_demo_es_valida(self) -> None:
        errores, _ = validar_datos(
            self.datos["Sondeos"], self.datos["Intervalos"], self.datos["Unidades"],
            self.datos["Ensayos_DPSH"], self.datos["Lecturas_DPSH"],
        )
        self.assertEqual(errores, [])

    def test_plantilla_es_reimportable(self) -> None:
        contenido = crear_plantilla_excel(True)
        import io
        importado = leer_excel(io.BytesIO(contenido))
        self.assertEqual(set(importado), set(self.datos))
        self.assertEqual(len(importado["Sondeos"]), 4)

    def test_contactos_en_cota_absoluta(self) -> None:
        sondeos = proyectar_puntos(self.datos["Sondeos"], self.datos["Eje"])
        contactos = contactos_observados(sondeos, self.datos["Intervalos"], self.datos["Unidades"])
        self.assertEqual(len(contactos), 3)
        primer_contacto = next(c for c in contactos if c.contacto_id == "techo_AL")
        punto_s1 = next(p for p in primer_contacto.vertices if p.referencia == "S-01")
        self.assertAlmostEqual(punto_s1.z_m, 112.4 - 1.4)

    def test_polygonizacion_del_borrador(self) -> None:
        try:
            import shapely  # noqa: F401
        except ImportError:
            self.skipTest("Shapely no esta disponible en el entorno de pruebas.")
        sondeos = proyectar_puntos(self.datos["Sondeos"], self.datos["Eje"])
        contactos = contactos_observados(sondeos, self.datos["Intervalos"], self.datos["Unidades"])
        zonas, avisos = construir_zonas(sondeos, contactos)
        self.assertEqual(len(zonas), 4)
        self.assertTrue(any("sin unidad" in aviso for aviso in avisos))


class ContactosTests(unittest.TestCase):
    def test_contacto_cerrado_conserva_orden_topologico(self) -> None:
        vertices = [
            VerticeContacto(0.0, 10.0), VerticeContacto(5.0, 8.0),
            VerticeContacto(0.0, 6.0), VerticeContacto(0.0, 10.0),
        ]
        contacto = Contacto("lente", "Lente", "A", "B", vertices=vertices.copy())
        contacto.ordenar()
        self.assertEqual([(p.s_m, p.z_m) for p in contacto.vertices], [(p.s_m, p.z_m) for p in vertices])

    def test_interpolacion_sin_extrapolacion(self) -> None:
        contacto = Contacto(
            "c1", "C1", "A", "B", vertices=[VerticeContacto(0.0, 10.0), VerticeContacto(10.0, 5.0)]
        )
        valores = interpolar_contacto(contacto, np.array([-1.0, 0.0, 5.0, 10.0, 11.0]))
        self.assertTrue(np.isnan(valores[0]))
        self.assertAlmostEqual(valores[2], 7.5)
        self.assertTrue(np.isnan(valores[-1]))

    def test_deteccion_de_cruce(self) -> None:
        superior = Contacto(
            "sup", "Superior", "A", "B", vertices=[VerticeContacto(0.0, 10.0), VerticeContacto(10.0, 5.0)]
        )
        inferior = Contacto(
            "inf", "Inferior", "B", "C", vertices=[VerticeContacto(0.0, 8.0), VerticeContacto(10.0, 7.0)]
        )
        self.assertEqual(len(detectar_cruces([superior, inferior])), 1)

    def test_dxf_contiene_polilinea(self) -> None:
        contacto = Contacto(
            "c1", "C1", "A", "B", vertices=[VerticeContacto(0.0, 10.0), VerticeContacto(10.0, 5.0)]
        )
        zona = {
            "unidad_id": "B", "coordenadas": [[0, 10], [10, 10], [10, 5], [0, 5]],
            "huecos": [],
        }
        contenido = contactos_a_dxf([contacto], [zona]).decode("ascii")
        self.assertIn("POLYLINE", contenido)
        self.assertIn("10.000000", contenido)
        self.assertIn("ZONA_B", contenido)


class PersistenciaTests(unittest.TestCase):
    def test_ida_y_vuelta_json(self) -> None:
        datos = crear_datos_demo()
        contacto = Contacto(
            "c1", "Contacto 1", "A", "B", vertices=[VerticeContacto(1.0, 2.0, "observado", "S-01")]
        )
        zona = {
            "zona_id": "Z01-prueba", "coordenadas": [[0, 0], [1, 0], [1, 1]],
            "unidad_id": "A", "trama": "puntos", "color": "#aaaaaa",
        }
        proyecto = Proyecto(nombre="Prueba", contactos=[contacto], zonas=[zona])
        contenido = proyecto_a_json(proyecto, datos)
        json.loads(contenido.decode("utf-8"))
        recuperado, tablas = proyecto_desde_json(contenido)
        self.assertEqual(recuperado.nombre, "Prueba")
        self.assertEqual(recuperado.contactos[0].vertices[0].referencia, "S-01")
        self.assertEqual(recuperado.zonas[0]["trama"], "puntos")
        self.assertEqual(len(tablas["Sondeos"]), 4)


if __name__ == "__main__":
    unittest.main()
