"""Regresiones de la interfaz v0.8.2 y separacion de STA/interpretacion."""
from pathlib import Path

from perfil_geologico.servicios.importar_campana import importar_campana
from perfil_geologico.calculos.terreno import terreno_de_campana
from perfil_geologico.calculos.proyeccion import proyectar_puntos
from perfil_geologico.calculos.presentacion import preparar_guitarra
from perfil_geologico.modelos.dominio import Proyecto
from perfil_geologico.tests.test_campana_multifichero_v08 import _libros

BASE = Path(__file__).resolve().parents[1]


def test_sidebar_capa_y_navegacion_no_duplicadas():
    codigo = (BASE / 'paginas/vistas.py').read_text(encoding='utf-8')
    assert '"Datos", "Trazado", "Perfil", "Unidades", "Interpretación", "Exportar"' in codigo
    assert 'def _estado_sidebar(pagina: str)' in codigo
    assert 'CAPAS_PERFIL' in codigo
    assert 'with st.expander("Capas de representacion y textos"' not in codigo
    assert 'st.popover("＋ Nuevo"' in codigo
    assert 'st.popover("▣ Abrir"' in codigo
    assert 'st.download_button("▣ Guardar"' in codigo
    assert 'topograficos[\'reconocimiento\']' not in codigo
    assert 'fig.add_trace(go.Scatter(x=topograficos' not in codigo


def test_sta_topografia_sin_capa_reconocimiento():
    datos, _ = importar_campana(_libros())
    sondeos = proyectar_puntos(datos['Sondeos'], datos['Eje'])
    dpsh = proyectar_puntos(datos['Ensayos_DPSH'], datos['Eje'])
    terreno = terreno_de_campana(datos, sondeos)
    assert terreno['s_m'].iloc[0] == 0.0  # STA influye en el terreno
    guitarra = preparar_guitarra(sondeos, dpsh, (0.0, 8.0), 2.0, terreno)
    assert all(rec['nombre'] != 'STA' for rec in guitarra['reconocimientos'])
    minipy = (BASE / 'componentes/minicad.py').read_text(encoding='utf-8')
    assert '"terreno": [{"s_m": float(s)' in minipy
    assert '"sondeos": rectangulos' in minipy
    assert '"texto_general_pt": int(texto_general_pt)' in minipy



def test_toolbar_es_horiz_y_controles_reales():
    html = (BASE / 'componentes/minicad_frontend/index.html').read_text(encoding='utf-8')
    for button in ('selectBtn', 'drawBtn', 'lensBtn', 'deleteContactBtn',
                   'deleteLensBtn', 'paintBtn', 'clearFillBtn', 'clearBtn',
                   'panBtn', 'fitBtn', 'snapBtn', 'undoBtn', 'redoBtn', 'saveBtn'):
        assert f'id="{button}"' in html
    assert 'e.shiftKey||mode===\'pan\'' in html
    assert 'applyPresentation(m)' in html
    assert 'if(layers.terreno)drawTerrain()' in html
