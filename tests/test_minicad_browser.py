"""Optional real-Chromium regression tests for MiniCAD pointer coordinate mapping.

Install playwright and Chromium to run these tests. They skip gracefully when unavailable.
"""
import os
from pathlib import Path

import pytest

playwright = pytest.importorskip('playwright.sync_api')

HTML = Path(__file__).resolve().parents[1] / 'componentes' / 'minicad_frontend' / 'index.html'

MODEL = {
    'bounds': {'xmin': 0, 'xmax': 100, 'ymin': 0, 'ymax': 100},
    'terreno': [{'s_m': 0, 'z_m': 90}, {'s_m': 100, 'z_m': 90}],
    'sondeos': [],
    'dpsh': [],
    'zonas': [],
    'contactos': [],
    'contactos_referencia': [],
    'unidades': [{'unidad_id': 'A', 'nombre': 'Arcilla', 'color': '#88AA77'}],
    'observados': [
        {
            's_m': 30.0,
            'z_m': 70.0,
            'referencia': 'S-03',
            'interfaz_id': 'S-03:I001',
            'profundidad_m': 7.8,
            'unidad_superior': 'A',
            'unidad_inferior': 'B',
        }
    ],
}


def open_cad(browser, width, model=None):
    page = browser.new_page(viewport={'width': width, 'height': 900}, device_scale_factor=1)
    page.set_content(HTML.read_text(encoding="utf-8"), wait_until="load")
    page.evaluate("""() => {
        window.__saved = null;
        const original = window.postMessage.bind(window);
        window.postMessage = (msg, target) => {
            if (msg.type === 'streamlit:setComponentValue') window.__saved = msg.value;
            return original(msg, target);
        };
    }""")
    page.evaluate("""(model) => window.dispatchEvent(new MessageEvent('message',
        {data:{type:'streamlit:render',args:{model}}}))""", model or MODEL)
    return page


def client_coords(page, s, z):
    return page.evaluate("""({s,z})=>{
        const svg=document.querySelector('#cad'), pt=svg.createSVGPoint();
        pt.x=58+s/100*(1200-58-22);
        pt.y=24+(100-z)/100*(610-24-46);
        const p=pt.matrixTransform(svg.getScreenCTM());
        return {x:p.x,y:p.y};
    }""", {'s': s, 'z': z})


def chromium_browser(playwright_instance):
    path = os.environ.get('CHROMIUM_PATH')
    try:
        if path:
            return playwright_instance.chromium.launch(headless=True, executable_path=path, args=['--no-sandbox'])
        if Path('/usr/bin/chromium').exists():
            return playwright_instance.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        return playwright_instance.chromium.launch(headless=True)
    except Exception as exc:
        pytest.skip('Chromium not available for optional browser regression: ' + str(exc)[:300])


@pytest.mark.parametrize('width', [760, 920, 1360])
def test_exact_svg_coordinates_and_snapping_at_different_widths(width):
    with playwright.sync_playwright() as pw:
        browser=chromium_browser(pw)
        try:
            page=open_cad(browser,width)
            page.locator('#drawBtn').click()
            point=client_coords(page,30,70)
            page.mouse.move(point['x']+7,point['y']-7)
            assert page.locator('#tooltip').evaluate('(el) => getComputedStyle(el).display') != 'none'
            page.mouse.click(point['x']+7,point['y']-7)
            # turn off snapping to validate a freehand coordinate (not snapping to a line)
            page.locator('#snapBtn').click()
            second=client_coords(page,72.25,43.75)
            page.mouse.click(second['x'],second['y'])
            page.locator('#finishBtn').click()
            page.locator('#saveBtn').click()
            saved=page.evaluate('window.__saved')
            assert saved is not None
            verts=saved['contactos'][0]['vertices']
            assert verts[0]['interfaz_id']=='S-03:I001'
            assert verts[0]['origen']=='observado'
            assert abs(verts[0]['s_m']-30)<1e-10
            assert abs(verts[0]['z_m']-70)<1e-10
            assert abs(verts[1]['s_m']-72.25)<1e-4
            assert abs(verts[1]['z_m']-43.75)<1e-4
            page.close()
        finally:
            browser.close()


def test_zoom_keeps_cursor_target_fixed_and_observed_point_capturable():
    with playwright.sync_playwright() as pw:
        browser=chromium_browser(pw)
        try:
            page=open_cad(browser,800)
            point=client_coords(page,30,70)
            page.mouse.move(point['x'],point['y'])
            page.mouse.wheel(0,-340)
            page.wait_for_timeout(120)
            page.locator('#drawBtn').click()
            page.mouse.click(point['x'],point['y'])
            # after zoom, add a second vertex with snapping disabled
            page.locator('#snapBtn').click()
            next_point=client_coords(page,60,60)
            page.mouse.click(next_point['x'],next_point['y'])
            page.locator('#finishBtn').click()
            page.locator('#saveBtn').click()
            verts=page.evaluate('window.__saved.contactos[0].vertices')
            assert verts[0]['interfaz_id']=='S-03:I001'
            assert abs(verts[0]['s_m']-30)<1e-9
            assert abs(verts[0]['z_m']-70)<1e-9
        finally:
            browser.close()


def test_resize_after_render_keeps_data_coordinates():
    with playwright.sync_playwright() as pw:
        browser=chromium_browser(pw)
        try:
            page=open_cad(browser,1300)
            page.set_viewport_size({'width':760,'height':900})
            page.locator('#drawBtn').click()
            point=client_coords(page,30,70)
            page.mouse.click(point['x'],point['y'])
            page.locator('#snapBtn').click()
            second=client_coords(page,55,55)
            page.mouse.click(second['x'],second['y'])
            page.locator('#finishBtn').click()
            page.locator('#saveBtn').click()
            verts=page.evaluate('window.__saved.contactos[0].vertices')
            assert verts[0]['interfaz_id']=='S-03:I001'
            assert abs(verts[1]['s_m']-55)<1e-4
            assert abs(verts[1]['z_m']-55)<1e-4
        finally:
            browser.close()


def test_observed_boundary_wins_over_nearer_interpreted_line():
    from copy import deepcopy
    model=deepcopy(MODEL)
    model['contactos']=[{
        'contacto_id':'c1','nombre':'Interpretado','color':'#444444',
        'visible':True,'bloqueado':False,'vertices':[
            {'s_m':31,'z_m':60,'origen':'interpretado'},
            {'s_m':31,'z_m':80,'origen':'interpretado'},
        ],
    }]
    with playwright.sync_playwright() as pw:
        browser=chromium_browser(pw)
        try:
            page=open_cad(browser,800,model)
            page.locator('#drawBtn').click()
            pos=client_coords(page,31,70)
            page.mouse.click(pos['x'],pos['y'])
            page.locator('#snapBtn').click()
            second=client_coords(page,55,45)
            page.mouse.click(second['x'],second['y'])
            page.locator('#finishBtn').click()
            page.locator('#saveBtn').click()
            verts=page.evaluate('window.__saved.contactos[1].vertices')
            assert verts[0]['interfaz_id']=='S-03:I001'
            assert verts[0]['s_m']==30
            assert verts[0]['z_m']==70
        finally:
            browser.close()
