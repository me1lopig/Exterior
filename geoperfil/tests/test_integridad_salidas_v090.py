"""Regresiones del contrato de exportacion sin perdida de GeoPerfil 2D v0.9.0."""
from __future__ import annotations

from io import BytesIO
import json
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import matplotlib.axes
import pandas as pd

from perfil_geologico.calculos.proyeccion import proyectar_puntos
from perfil_geologico.modelos.dominio import Contacto, Proyecto, VerticeContacto
from perfil_geologico.servicios.datos_demo import crear_datos_demo
from perfil_geologico.servicios.exportacion import (
    contactos_a_csv, figura_html_autocontenida, figura_perfil_imagen,
    vertices_zonas_a_csv, zonas_a_csv,
)
from perfil_geologico.servicios.importar_excel import datos_a_excel
from perfil_geologico.servicios.paquete_salida import crear_paquete_entrega, verificar_paquete
from perfil_geologico.servicios.persistencia import huella_proyecto, proyecto_a_json


def proyecto_interpretado() -> tuple[Proyecto, dict[str, pd.DataFrame]]:
    datos = crear_datos_demo()
    contacto = Contacto(
        "C-01", "Techo GA", "AL", "GA", color="#123456",
        evidencia="proyectado", incertidumbre_m=0.35,
        vertices=[
            VerticeContacto(15.0, 105.0, "observado", "S-01", "S-01:I002"),
            VerticeContacto(195.0, 103.0, "interpretado"),
        ],
    )
    zona = {
        "zona_id": "Z01", "etiqueta": "Z01", "unidad_id": "AL",
        "trama": "horizontal", "color": "#89A96B", "area_m2": 10.0,
        "centro_s_m": 50.0, "centro_z_m": 105.0,
        "coordenadas": [[0.0, 110.0], [100.0, 110.0], [100.0, 100.0], [0.0, 100.0]],
        "huecos": [[[40.0, 106.0], [60.0, 106.0], [60.0, 104.0], [40.0, 104.0]]],
    }
    proyecto = Proyecto(
        nombre="Perfil auditado", localizacion="Caso sintetico", autor="GeoPerfil",
        contactos=[contacto], zonas=[zona],
        hipotesis=[{"nombre": "H1", "creada": "2026-01-01T00:00:00+00:00",
                    "contactos": [], "zonas": []}],
    )
    return proyecto, datos


class IntegridadSalidasV090Tests(unittest.TestCase):
    def test_huella_canonica_es_estable_y_figura_en_json(self) -> None:
        proyecto, datos = proyecto_interpretado()
        primera = huella_proyecto(proyecto, datos)
        segunda = huella_proyecto(proyecto, datos)
        self.assertEqual(primera, segunda)
        contenido = json.loads(proyecto_a_json(proyecto, datos))
        self.assertEqual(contenido["meta"]["sha256_estado_canonico"], primera)

    def test_xlsx_contiene_datos_e_interpretacion(self) -> None:
        proyecto, datos = proyecto_interpretado()
        bruto = datos_a_excel(datos, proyecto=proyecto, manifest={"sha256": huella_proyecto(proyecto, datos)})
        libro = pd.ExcelFile(BytesIO(bruto))
        esperadas = {
            "Proyecto", "Contactos", "Vertices_Contactos", "Zonas", "Anillos_Zonas",
            "Hipotesis", "Configuracion", "Esquema", "Manifest",
        }
        self.assertTrue(esperadas.issubset(libro.sheet_names))
        contactos = pd.read_excel(libro, sheet_name="Contactos")
        self.assertEqual(contactos.loc[0, "incertidumbre_m"], 0.35)
        self.assertEqual(contactos.loc[0, "unidad_inferior"], "GA")
        anillos = pd.read_excel(libro, sheet_name="Anillos_Zonas")
        self.assertEqual(set(anillos["tipo_anillo"]), {"exterior", "hueco"})

    def test_csv_conservan_atributos_y_cabeceras_vacias(self) -> None:
        proyecto, datos = proyecto_interpretado()
        huella = huella_proyecto(proyecto, datos)
        contacto = contactos_a_csv(proyecto.contactos, huella).decode("utf-8-sig")
        self.assertIn("unidad_superior", contacto.splitlines()[0])
        self.assertIn("incertidumbre_m", contacto.splitlines()[0])
        self.assertIn(huella, contacto)
        self.assertIn("contacto_id", contactos_a_csv([]).decode("utf-8-sig").splitlines()[0])
        self.assertIn("zona_id", zonas_a_csv([]).decode("utf-8-sig").splitlines()[0])
        self.assertIn("tipo_anillo", vertices_zonas_a_csv([]).decode("utf-8-sig").splitlines()[0])

    def test_html_es_autonomo_e_incluye_estado_maestro(self) -> None:
        class FiguraFalsa:
            def to_html(self, *, include_plotlyjs, full_html):
                assert include_plotlyjs is True and full_html is True
                return "<html><body><div>perfil</div></body></html>"
        bruto = figura_html_autocontenida(
            FiguraFalsa(), b'{"proyecto":{"nombre":"P"}}', {"sha256": "abc"}
        ).decode("utf-8")
        self.assertIn('id="geoperfil-proyecto"', bruto)
        self.assertIn('id="geoperfil-manifest"', bruto)
        self.assertIn('"nombre":"P"', bruto)

    def test_paquete_maestro_supera_verificacion(self) -> None:
        proyecto, datos = proyecto_interpretado()
        archivos = {
            "perfil_geologico.json": proyecto_a_json(proyecto, datos),
            "contactos.csv": contactos_a_csv(proyecto.contactos),
        }
        paquete, manifest = crear_paquete_entrega(proyecto, datos, archivos)
        self.assertEqual(verificar_paquete(paquete), [])
        with ZipFile(BytesIO(paquete)) as contenido:
            self.assertEqual(set(contenido.namelist()), {*archivos, "manifest.json"})
            guardado = json.loads(contenido.read("manifest.json"))
        self.assertEqual(guardado["archivos"], manifest["archivos"])

    def test_rellenos_desactivados_no_llaman_fill_between(self) -> None:
        proyecto, datos = proyecto_interpretado()
        proyecto.capas["rellenos"] = False
        proyecto.contactos[0].incertidumbre_m = 0.0
        sondeos = proyectar_puntos(datos["Sondeos"], datos["Eje"])
        dpsh = proyectar_puntos(datos["Ensayos_DPSH"], datos["Eje"])
        original = matplotlib.axes.Axes.fill_between
        llamadas = []
        def vigilar(eje, *args, **kwargs):
            llamadas.append((args, kwargs))
            return original(eje, *args, **kwargs)
        with patch.object(matplotlib.axes.Axes, "fill_between", new=vigilar):
            figura_perfil_imagen(
                proyecto, sondeos, datos["Intervalos"], datos["Unidades"],
                proyecto.contactos, dpsh, datos["Lecturas_DPSH"], 0.12,
                zonas=proyecto.zonas, formato="svg",
            )
        self.assertEqual(llamadas, [])


if __name__ == "__main__":
    unittest.main()
