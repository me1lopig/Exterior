"""Prueba grafica MiniCAD: bocas y puntos de inicio alineados al terreno."""
from pathlib import Path
from unittest.mock import patch
import importlib
import sys
import types
import pytest

from perfil_geologico.tests.test_cotas_inicio_v083 import escenario


def test_miniCAD_sondeo_y_penetro_sobre_terreno_con_cota_irregular():
    from perfil_geologico.calculos.proyeccion import proyectar_puntos
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip('Playwright no instalado en este entorno.')
    datos, sondeos, dpsh, t = escenario()
    v1 = types.ModuleType('streamlit.components.v1')
    v1.declare_component = lambda *args, **kwargs: lambda **kw: None
    components = types.ModuleType('streamlit.components')
    components.v1 = v1
    st = types.ModuleType('streamlit')
    st.components = components
    with patch.dict(sys.modules, {'streamlit': st, 'streamlit.components': components,
                                 'streamlit.components.v1': v1}):
        minicad = importlib.import_module('perfil_geologico.componentes.minicad')
        model = minicad.modelo_minicad(
            sondeos, datos['Intervalos'], datos['Unidades'], [], [], dpsh,
            datos['Lecturas_DPSH'], terreno_puntos=t,
        )
    html = (Path(__file__).resolve().parents[1] / 'componentes/minicad_frontend/index.html').read_text('utf-8')
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True,
                 executable_path="/usr/bin/chromium" if Path("/usr/bin/chromium").exists() else None,
                 args=["--no-sandbox"])
        except Exception:
            pytest.skip('No hay navegador Chromium utilizable.')
        try:
            page = browser.new_page(viewport={'width': 1100, 'height': 800})
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.set_content(html)
            page.evaluate("m=>window.dispatchEvent(new MessageEvent('message',{data:{type:'streamlit:render',args:{model:m}}}))", model)
            resultado = page.evaluate('''() => {
              const svg=document.querySelector('#cad');
              const tr=Array.from(svg.querySelectorAll('polyline')).find(x=>x.getAttribute('stroke')==='#0a2239');
              const pts=tr.getAttribute('points').trim().split(/\\s+/).map(v=>v.split(',').map(Number));
              const rect=Array.from(svg.querySelectorAll('rect')).find(r=>r.getAttribute('fill')==='#D1A979');
              const head=Array.from(svg.querySelectorAll('circle')).find(c=>c.getAttribute('r')==='4'&&c.getAttribute('stroke')==='#e45658');
              if(!tr||!rect||!head)return null;
              return {terreno:pts,sondeo:{x:Number(rect.getAttribute('x'))+Number(rect.getAttribute('width'))/2,y:Number(rect.getAttribute('y'))},
                penetracion:{x:Number(head.getAttribute('cx')),y:Number(head.getAttribute('cy'))},
                texts:svg.textContent};
            }''')
            assert not errors, errors
            assert resultado is not None
            assert 'STA' not in resultado['texts']
            topo = resultado['terreno']
            x_s,y_s=resultado['sondeo'].values()
            x_p,y_p=resultado['penetracion'].values()
            assert any(abs(x-x_s)<1e-3 and abs(y-y_s)<1e-3 for x,y in topo), resultado
            assert any(abs(x-x_p)<1e-3 and abs(y-y_p)<1e-3 for x,y in topo), resultado
        finally:
            browser.close()
