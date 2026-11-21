"""Casos sinteticos: encabezados PERFIL1 y rechazo SPT sin inventar golpes."""
from __future__ import annotations

from io import BytesIO

import openpyxl
import pandas as pd
import pytest

from perfil_geologico.modelos.dominio import Proyecto
from perfil_geologico.calculos.proyeccion import proyectar_puntos
from perfil_geologico.calculos.terreno import terreno_de_campana
from perfil_geologico.visualizacion.perfil_plotly import crear_figura_perfil
from perfil_geologico.servicios.exportacion import contactos_a_dxf
from perfil_geologico.servicios.importar_campana import importar_campana
from perfil_geologico.servicios.importar_excel import datos_a_excel
from perfil_geologico.servicios.persistencia import proyecto_a_json, proyecto_desde_json
from perfil_geologico.tests.test_campana_multifichero_v08 import _libros, _xlsx


def _archivos_con_rechazos():
    libros = _libros()
    libros['foo.xlsx'] = _xlsx([
        ['Estación', 'Distancia', 'Cota'],
        ['STA', 0, 100], ['S-01', 5, 120.75], ['P-01', 8, 118.2],
    ])
    libros['bee.xlsx'] = _xlsx([
        ['Descripción Muestra', 'Profundidad inicial', 'ISPT_SEAT',
         'Espesor en milímetros', 'SPT (valores centrales)', 'Valores ensayos',
         'ISPT_INC1', 'ISPT_INC2', 'ISPT_INC3', 'ISPT_INC4',
         'ISPT_PEN1', 'ISPT_PEN2', 'ISPT_PEN3', 'ISPT_PEN4'],
        ['S-01', 2.45, 29, 400, ' RECHAZO ', '29-41-R',
         29, 41, 'R', None, 150, 150, 100, None],
        ['S-01', 6.4, 'R', 50, 'r', 'R',
         '  Rechazo  ', None, None, None, 50, None, None, None],
        ['S-01', 8.9, 6, 600, 18, '6-8-10-14',
         6, 8, 10, 14, 150, 150, 150, 150],
    ])
    libros['lab.xlsx'] = _xlsx([
        ['Unidad geotécnica', 'Descripción Muestra', 'Ensayo geotecnia',
         'Profundidad inicial', 'ISPT_INC1', 'ISPT_INC2', 'ISPT_INC3',
         'ISPT_INC4', 'SPT (valores centrales)'],
        ['UG-01', 'S-01', 'SPT', 2.45, 29, 41, 'rechazo', '', 'r'],
        ['UG-01', 'S-01', 'SPT', 6.4, 'R', '', '', '', 'RECHAZO'],
    ])
    return libros


@pytest.mark.parametrize('encabezado', ['Estación', 'Estaciones', 'ESTACION', 'ESTACIONES'])
def test_cabecera_perfil_singular_y_plural(encabezado):
    libros = _libros()
    libros['foo.xlsx'] = _xlsx([
        [encabezado, 'Distancia', 'Cota'], ['STA', 0, 0],
        ['S-01', 5, 120.75], ['P-01', 8, 118.2],
    ])
    datos, _ = importar_campana(libros)
    assert len(datos['Estaciones']) == 3


def test_rechazos_conservan_penetracion_y_su_texto_original():
    datos, avisos = importar_campana(_archivos_con_rechazos())
    spt = datos['SPT'].sort_values('profundidad_m').reset_index(drop=True)
    assert len(spt) == 3
    a, b, c = (spt.iloc[i] for i in range(3))
    assert a['estado'] == 'rechazo' and bool(a['rechazo'])
    assert a['secuencia'] == '29/41/R' and a['secuencia_original'] == '29-41-R'
    assert a['n_central_estado'] == 'rechazo' and a['n_central_original'] == ' RECHAZO '
    assert pd.isna(a['n_central']) and pd.isna(a['inc3'])
    assert a['inc3_estado'] == 'rechazo' and a['inc3_original'] == 'R'
    assert a['inc2'] == 41 and a['pen3_mm'] == 100
    assert a['archivo_origen'] == 'bee.xlsx' and a['fila'] == 2
    assert b['secuencia'] == 'R' and b['inc1_estado'] == 'rechazo'
    assert b['inc1_original'] == '  Rechazo  ' and b['pen1_mm'] == 50
    assert b['ispt_seat_original'] == 'R'
    assert c['secuencia'] == '6/8/10/14' and c['n_central'] == 18
    assert c['estado'] == 'registrado' and not bool(c['rechazo'])
    assert not any('duplicado con golpes distintos' in a for a in avisos)


def test_rechazos_en_listadolab_sin_ispt():
    libros = _archivos_con_rechazos()
    del libros['bee.xlsx']
    datos, avisos = importar_campana(libros)
    assert len(datos['SPT']) == 2
    assert datos['SPT']['rechazo'].tolist() == [True, True]
    assert datos['SPT'].iloc[0]['secuencia'] == '29/41/R'
    assert datos['SPT'].iloc[0]['n_central_original'] == 'r'
    assert pd.isna(datos['SPT'].iloc[0]['pen3_mm'])
    assert any('ISPT no incluido' in a for a in avisos)


def test_cero_es_distinto_de_rechazo_y_vacio():
    libros = _archivos_con_rechazos()
    d, _ = importar_campana(libros)
    assert d['SPT'].iloc[0]['inc4_estado'] == 'sin_dato'
    assert d['SPT'].iloc[0]['inc3_estado'] == 'rechazo'
    libros['bee.xlsx'] = _xlsx([
        ['Descripción Muestra', 'Profundidad inicial', 'ISPT_INC1',
         'ISPT_INC2', 'ISPT_INC3', 'ISPT_INC4', 'ISPT_PEN1',
         'ISPT_PEN2', 'ISPT_PEN3', 'ISPT_PEN4',
         'SPT (valores centrales)'],
        ['S-01', 2.45, 0, 'R', '', '', 0, '', '', '', 'Rechazo'],
    ])
    d, _ = importar_campana(libros)
    spt = d['SPT'].iloc[0]
    assert spt['inc1_estado'] == 'registrado' and spt['inc1'] == 0
    assert spt['inc2_estado'] == 'rechazo' and pd.isna(spt['inc2'])
    assert spt['inc3_estado'] == 'sin_dato' and pd.isna(spt['inc3'])
    assert spt['pen1_mm'] == 0


def test_texto_no_reconocido_no_se_convierte_en_rechazo():
    libros = _archivos_con_rechazos()
    libros['bee.xlsx'] = _xlsx([
        ['Descripción Muestra', 'Profundidad inicial', 'ISPT_INC1',
         'ISPT_INC2', 'ISPT_INC3', 'ISPT_INC4', 'ISPT_PEN1',
         'SPT (valores centrales)'],
        ['S-01', 2.45, 29, 41, 'R60', '', 100, 'R'],
    ])
    with pytest.raises(ValueError, match='ISPT_INC3 no numerico'):
        importar_campana(libros)


def test_json_y_excel_exportan_atributos_de_rechazo():
    datos, _ = importar_campana(_archivos_con_rechazos())
    proyecto = Proyecto(nombre='Rechazos sinteticos')
    _, reabiertos = proyecto_desde_json(proyecto_a_json(proyecto, datos))
    pd.testing.assert_frame_equal(datos['SPT'], reabiertos['SPT'])
    xlsx = datos_a_excel(datos, proyecto=proyecto)
    libro = openpyxl.load_workbook(BytesIO(xlsx), read_only=True, data_only=True)
    try:
        hoja = libro['SPT']
        hoja.reset_dimensions()
        filas = list(hoja.values)
        indices = {col: i for i, col in enumerate(filas[0])}
        fila_rechazo = filas[1]
        assert fila_rechazo[indices['estado']] == 'rechazo'
        assert fila_rechazo[indices['inc3_estado']] == 'rechazo'
        assert fila_rechazo[indices['inc3_original']] == 'R'
        assert fila_rechazo[indices['pen3_mm']] == 100
        assert fila_rechazo[indices['n_central_original']] == ' RECHAZO '
    finally:
        libro.close()


def test_rechazo_se_representa_y_llega_al_dxf_con_penetracion():
    import ezdxf

    datos, _ = importar_campana(_archivos_con_rechazos())
    proyecto = Proyecto()
    sondeos = proyectar_puntos(datos['Sondeos'], datos['Eje'])
    dpsh = proyectar_puntos(datos['Ensayos_DPSH'], datos['Eje'])
    extras = {
        'terreno_puntos': terreno_de_campana(datos, sondeos),
        'spt': datos['SPT'],
    }
    figura = crear_figura_perfil(
        proyecto, sondeos, datos['Intervalos'], datos['Unidades'], [],
        dpsh, datos['Lecturas_DPSH'], **extras,
    )
    etiquetas = next(t.text for t in figura.data if t.name == 'SPT (golpes)')
    assert 'SPT 29/41/R' in etiquetas
    assert 'SPT R' in etiquetas

    dxf_raw = contactos_a_dxf(
        [], proyecto=proyecto, sondeos=sondeos, dpsh=dpsh,
        lecturas_dpsh=datos['Lecturas_DPSH'], **extras,
    )
    from io import StringIO
    dxf = ezdxf.read(StringIO(dxf_raw.decode('utf-8')))
    entidades = [e for e in dxf.modelspace() if e.dxf.layer == 'SPT']
    assert len(entidades) == 3
    xdata = next(e.get_xdata('GEOPERFIL') for e in entidades if e.dxf.text == 'SPT 29/41/R')
    atributos = {str(tag.value) for tag in xdata}
    assert 'estado=rechazo' in atributos
    assert 'inc3_estado=rechazo' in atributos
    assert 'pen3_mm=100.0' in atributos
