"""Pruebas de interaccion SVG: autosincronizacion y relleno sin guardado manual."""
from __future__ import annotations

import os
from pathlib import Path
import pytest
playwright = pytest.importorskip('playwright.sync_api')

HTML = Path(__file__).resolve().parents[1] / 'componentes' / 'minicad_frontend' / 'index.html'
BASE = {
    'bounds': {'xmin': 0, 'xmax': 100, 'ymin': 0, 'ymax': 100},
    'terreno': [{'s_m':0,'z_m':90},{'s_m':100,'z_m':90}],
    'contactos': [], 'zonas': [], 'sondeos': [], 'dpsh': [],
    'contactos_referencia': [], 'observados': [],
    'unidades': [{'unidad_id':'A','nombre':'Arcilla','color':'#88AA77'}]
}

def launch():
    from playwright.sync_api import sync_playwright
    return sync_playwright()

def coords(page, s, z):
    return page.evaluate('''({s,z})=>{
      const svg=document.querySelector('#cad'),p=svg.createSVGPoint(),v=svg.viewBox.baseVal;
      const left=58,right=22,top=24,bottom=46;
      p.x=left+s/100*(1200-left-right);p.y=top+(100-z)/100*(v.height-top-bottom);
      const q=p.matrixTransform(svg.getScreenCTM());return {x:q.x,y:q.y};
    }''',{'s':s,'z':z})

@pytest.mark.parametrize('ev', [None, 1, 5, 10])
def test_captura_geometria_autoguardado_relleno(ev):
    with launch() as pw:
        try:
            browser=pw.chromium.launch(headless=True, args=['--no-sandbox'], executable_path='/usr/bin/chromium' if Path('/usr/bin/chromium').exists() else None)
        except Exception as exc:
            pytest.skip('Chromium no disponible: '+str(exc)[:180])
        try:
            page=browser.new_page(viewport={'width':920,'height':900})
            page.set_content(HTML.read_text(), wait_until='load')
            page.evaluate('''()=>{
                window.__saves=[];
                window.postMessage=(m)=>{
                    if(m.type==='streamlit:setComponentValue')window.__saves.push(m.value);
                };
            }''')
            model=dict(BASE)
            if ev is not None:model['exageracion_vertical']=ev
            page.evaluate('''m=>window.dispatchEvent(new MessageEvent('message',{
                data:{type:'streamlit:render',args:{model:m}}}))''', model)
            page.locator('#drawBtn').click()
            for s,z in [(20,80),(80,80)]:
                p=coords(page,s,z)
                page.mouse.click(p['x'],p['y'])
            page.locator('#finishBtn').click()
            saves=page.evaluate('window.__saves')
            assert len(saves)==1, 'Finalizar debe guardar geometria automaticamente'
            assert len(saves[-1]['contactos']) == 1
            assert abs(saves[-1]['contactos'][0]['vertices'][0]['s_m']-20)<1e-4
            model['contactos']=saves[-1]['contactos']
            model['zonas']=[{'zona_id':'Z01','etiqueta':'Z01','unidad_id':'',
                             'color':'#D9DDE2','trama':'sin_trama','area_m2':10000,
                             'coordenadas':[[0,0],[100,0],[100,100],[0,100]],
                             'huecos':[], 'centro_s_m':50, 'centro_z_m':50}]
            page.evaluate('''m=>window.dispatchEvent(new MessageEvent('message',{
                data:{type:'streamlit:render',args:{model:m}}}))''',model)
            page.locator('#paintBtn').click()
            p=coords(page,50,50)
            page.mouse.click(p['x'],p['y'])
            saves=page.evaluate('window.__saves')
            assert len(saves)==2, 'Rellenar debe funcionar sin otro guardado manual'
            assert saves[-1]['zonas'][0]['unidad_id']=='A'
        finally:
            browser.close()
