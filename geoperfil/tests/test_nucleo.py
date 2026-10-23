from __future__ import annotations

import json
import unittest

import numpy as np
import pandas as pd

from perfil_geologico.calculos.contactos import (
    actualizar_vinculos_observados,
    contactos_observados,
    detectar_cruces,
    generar_borrador_geologico,
    interfaces_observadas,
    interpolar_contacto,
    vinculos_observados_desactualizados,
)
from perfil_geologico.calculos.dpsh import separar_tramos_contiguos
from perfil_geologico.calculos.proyeccion import longitud_eje, proyectar_puntos
from perfil_geologico.calculos.zonas import asignar_lentes_del_borrador, construir_zonas
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

    def test_tramos_dpsh_conservan_columnas_dataframe(self) -> None:
        lecturas = pd.DataFrame(
            {
                "profundidad_m": [0.2, 0.4, 0.6, 1.4, 1.6],
                "n20": [4, 6, 8, 13, 15],
            }
        )
        tramos = separar_tramos_contiguos(lecturas)
        self.assertEqual([len(tramo) for tramo in tramos], [3, 2])
        self.assertTrue(all(isinstance(tramo, pd.DataFrame) for tramo in tramos))
        np.testing.assert_array_equal(tramos[1]["n20"].to_numpy(float), [13.0, 15.0])

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
    @staticmethod
    def _caso_lente(profundidad_vecinos: float = 20.0) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        sondeos = pd.DataFrame(
            [
                ["S-01", 0.0, 100.0, profundidad_vecinos],
                ["S-02", 10.0, 100.0, 20.0],
                ["S-03", 20.0, 100.0, profundidad_vecinos],
            ],
            columns=["sondeo_id", "s_m", "cota_boca_m", "profundidad_m"],
        )
        intervalos = pd.DataFrame(
            [
                ["S-01", 0.0, profundidad_vecinos, "A"],
                ["S-02", 0.0, 5.0, "A"], ["S-02", 5.0, 8.0, "B"],
                ["S-02", 8.0, 20.0, "A"],
                ["S-03", 0.0, profundidad_vecinos, "A"],
            ],
            columns=["sondeo_id", "desde_m", "hasta_m", "unidad_id"],
        )
        unidades = pd.DataFrame(
            [["A", "Encajante", 1, "#aaaaaa"], ["B", "Lente local", 2, "#bbbbbb"]],
            columns=["unidad_id", "nombre", "orden", "color"],
        )
        return sondeos, intervalos, unidades

    def test_borrador_crea_lente_solo_con_control_lateral(self) -> None:
        sondeos, intervalos, unidades = self._caso_lente()
        contactos, avisos = generar_borrador_geologico(sondeos, intervalos, unidades)
        self.assertEqual(len(contactos), 1)
        lente = contactos[0]
        self.assertEqual(lente.contacto_id, "lente_B_S-02")
        self.assertEqual((lente.vertices[0].s_m, lente.vertices[2].s_m), (5.0, 15.0))
        self.assertEqual((lente.vertices[1].z_m, lente.vertices[3].z_m), (95.0, 92.0))
        self.assertEqual(lente.vertices[0].origen, "inferido_acunamiento")
        self.assertEqual(lente.vertices[1].origen, "observado")
        self.assertEqual(lente.vertices[0].s_m, lente.vertices[-1].s_m)
        self.assertTrue(any("Lente provisional" in aviso for aviso in avisos))

    def test_borrador_no_cierra_lente_sin_cobertura_vertical(self) -> None:
        sondeos, intervalos, unidades = self._caso_lente(profundidad_vecinos=4.0)
        contactos, avisos = generar_borrador_geologico(sondeos, intervalos, unidades)
        self.assertEqual(contactos, [])
        self.assertTrue(any("profundidad insuficiente" in aviso for aviso in avisos))

    def test_unidad_alternante_genera_lentes_con_id_unico(self) -> None:
        sondeos, _, unidades = self._caso_lente()
        intervalos = pd.DataFrame(
            [
                ["S-01", 0.0, 20.0, "A"],
                ["S-02", 0.0, 4.0, "A"], ["S-02", 4.0, 6.0, "B"],
                ["S-02", 6.0, 9.0, "A"], ["S-02", 9.0, 11.0, "B"],
                ["S-02", 11.0, 20.0, "A"],
                ["S-03", 0.0, 20.0, "A"],
            ],
            columns=["sondeo_id", "desde_m", "hasta_m", "unidad_id"],
        )
        contactos, _ = generar_borrador_geologico(sondeos, intervalos, unidades)
        ids = [contacto.contacto_id for contacto in contactos]
        self.assertEqual(ids, ["lente_B_S-02", "lente_B_S-02_02"])
        self.assertEqual(len(ids), len(set(ids)))

    def test_asignacion_provisional_de_unidad_a_lente(self) -> None:
        sondeos, intervalos, unidades = self._caso_lente()
        contactos, _ = generar_borrador_geologico(sondeos, intervalos, unidades)
        zonas = [{"zona_id": "Z1", "centro_s_m": 10.0, "centro_z_m": 93.5}]
        asignadas = asignar_lentes_del_borrador(zonas, contactos, unidades)
        self.assertEqual(asignadas[0]["unidad_id"], "B")
        self.assertEqual(asignadas[0]["color"], "#bbbbbb")

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

    def test_control_explicito_de_vinculos_observados(self) -> None:
        datos = crear_datos_demo()
        sondeos = proyectar_puntos(datos["Sondeos"], datos["Eje"])
        interfaces = interfaces_observadas(sondeos, datos["Intervalos"])
        interfaz_id = next(iter(interfaces))
        s_m, z_m = interfaces[interfaz_id]
        contacto = Contacto(
            "c-vinculado", "Contacto vinculado", "A", "B",
            vertices=[VerticeContacto(s_m, z_m + 0.5, "observado", "S-01", interfaz_id)],
        )
        desactualizados = vinculos_observados_desactualizados([contacto], interfaces)
        self.assertEqual(len(desactualizados), 1)
        self.assertEqual(actualizar_vinculos_observados([contacto], interfaces), 1)
        self.assertEqual(vinculos_observados_desactualizados([contacto], interfaces), [])


class PersistenciaTests(unittest.TestCase):
    def test_ida_y_vuelta_json(self) -> None:
        datos = crear_datos_demo()
        contacto = Contacto(
            "c1", "Contacto 1", "A", "B",
            vertices=[VerticeContacto(1.0, 2.0, "observado", "S-01", "S-01:1.000000")],
            visible=False, bloqueado=True, evidencia="proyectado", incertidumbre_m=0.4,
        )
        zona = {
            "zona_id": "Z01-prueba", "coordenadas": [[0, 0], [1, 0], [1, 1]],
            "unidad_id": "A", "trama": "puntos", "color": "#aaaaaa",
        }
        proyecto = Proyecto(
            nombre="Prueba", contactos=[contacto], zonas=[zona],
            hipotesis=[{"nombre": "Alternativa", "contactos": [], "zonas": []}],
        )
        contenido = proyecto_a_json(proyecto, datos)
        json.loads(contenido.decode("utf-8"))
        recuperado, tablas = proyecto_desde_json(contenido)
        self.assertEqual(recuperado.nombre, "Prueba")
        self.assertEqual(recuperado.contactos[0].vertices[0].referencia, "S-01")
        self.assertEqual(recuperado.contactos[0].vertices[0].interfaz_id, "S-01:1.000000")
        self.assertTrue(recuperado.contactos[0].bloqueado)
        self.assertFalse(recuperado.contactos[0].visible)
        self.assertEqual(recuperado.contactos[0].evidencia, "proyectado")
        self.assertAlmostEqual(recuperado.contactos[0].incertidumbre_m, 0.4)
        self.assertEqual(recuperado.hipotesis[0]["nombre"], "Alternativa")
        self.assertEqual(recuperado.zonas[0]["trama"], "puntos")
        self.assertEqual(len(tablas["Sondeos"]), 4)


if __name__ == "__main__":
    unittest.main()
