"""Comprobaciones de captura y confinamiento MiniCAD en Chromium."""
from copy import deepcopy
from pathlib import Path

import pytest

pwmod=pytest.importorskip('playwright.sync_api')

HTML=(Path(__file__).resolve().parents[1]/'componentes/minicad_frontend/index.html').read_text('utf-8')
MODEL={
 'bounds':{'xmin':-5,'xmax':105,'ymin':-25,'ymax':110},
 'dominio':{'xmin':0,'xmax':100,'base':-20,'terreno':[
     {'s_m':0,'z_m':95},{'s_m':50,'z_m':90},{'s_m':100,'z_m':100}]},
 'terreno':[{'s_m':0,'z_m':95},{'s_m':50,'z_m':90},{'s_m':100,'z_m':100}],
 'contactos':[],'contactos_referencia':[],'zonas':[],'dpsh':[],'sondeos':[],
 'unidades':[{'unidad_id':'U1','nombre':'Unidad 1','color':'#AABBCC'}],
 'observados':[{'s_m':30,'z_m':50,'referencia':'S-01','interfaz_id':'S-01:I001',
      'profundidad_m':45,'unidad_superior':'U1','unidad_inferior':'U2'}],
}


def open_page(browser):
 page=browser.new_page(viewport={'width':1180,'height':940})
 page.set_content(HTML)
 page.evaluate('''() => {window.__saved=null; const original=window.postMessage.bind(window);
    window.postMessage=(msg,target)=>{if(msg.type==='streamlit:setComponentValue')window.__saved=msg.value;return original(msg,target);}}
 ''')
 page.evaluate("m=>window.dispatchEvent(new MessageEvent('message',{data:{type:'streamlit:render',args:{model:m}}}))",MODEL)
 return page


def coord(page,s,z):
 return page.evaluate('''p=>{const svg=document.querySelector('#cad'),m=svg.getScreenCTM(),v=svg.createSVGPoint();
   const X=58+(p.s+5)/110*1120,Y=24+(110-p.z)/135*(610-24-46);
   v.x=X;v.y=Y;const q=v.matrixTransform(m);return{x:q.x,y:q.y};}''',{'s':s,'z':z})


def click(page,s,z):
 p=coord(page,s,z);page.mouse.click(p['x'],p['y'])


def browser(pw):
 if Path('/usr/bin/chromium').exists():
  return pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 try:return pw.chromium.launch(headless=True,args=['--no-sandbox'])
 except Exception as exc:pytest.skip('Sin Chromium: '+str(exc)[:200])


def test_contacto_arranca_y_termina_en_bordes_verticales():
 with pwmod.sync_playwright() as pw:
  b=browser(pw)
  try:
   p=open_page(b)
   issues=[];p.on('pageerror',lambda e:issues.append(str(e)))
   p.locator('#drawBtn').click()
   click(p,0,40)
   click(p,50,40)
   click(p,100,40)
   p.locator('#finishBtn').click()
   v=p.evaluate('window.__saved.contactos[0].vertices')
   assert [x['s_m'] for x in v]==pytest.approx([0,50,100],abs=1e-7)
   assert all(abs(x['z_m']-40)<1e-7 for x in v)
   assert not issues,issues
  finally:b.close()


def test_suelo_y_base_capturables_incluso_con_alt_y_clamp():
 with pwmod.sync_playwright() as pw:
  b=browser(pw)
  try:
   p=open_page(b)
   p.locator('#drawBtn').click()
   click(p,50,90.4) # 0,4 m por encima del terreno real en este PK
   click(p,80,-19.6) # 0,4 m de la base: captura exacta a la base
   p.locator('#finishBtn').click()
   v=p.evaluate('window.__saved.contactos[0].vertices')
   assert v[0]['s_m']==pytest.approx(50,abs=1e-6)
   assert v[0]['z_m']==pytest.approx(90,abs=1e-6)
   assert v[1]['z_m']==pytest.approx(-20,abs=1e-6)
   assert v[1]['origen']=='interpretado'
  finally:b.close()


def test_clic_fuera_de_terreno_no_genera_vertice_y_mantiene_observados():
 with pwmod.sync_playwright() as pw:
  b=browser(pw)
  try:
   p=open_page(b)
   p.locator('#drawBtn').click()
   click(p,60,104) # El terreno en PK60 esta a cota 92: fuera del dominio.
   click(p,30,50)  # Interfaz observada.
   click(p,70,45)
   p.locator('#finishBtn').click()
   v=p.evaluate('window.__saved.contactos[0].vertices')
   assert len(v)==2,v
   assert v[0]['interfaz_id']=='S-01:I001'
  finally:b.close()


def test_zoom_no_rompe_captura_del_borde_topografico():
 with pwmod.sync_playwright() as pw:
  b=browser(pw)
  try:
   p=open_page(b)
   mid=coord(p,50,90)
   p.mouse.move(mid['x'],mid['y']);p.mouse.wheel(0,-400)
   p.wait_for_timeout(100)
   p.locator('#drawBtn').click()
   # Coordenadas de pantalla del vertice topografico de PK50 tras zoom,
   # leyendo la polilinea renderizada y transformando por la matriz SVG.
   target=p.evaluate('''() => {const svg=document.querySelector('#cad');
     const terrain=[...svg.querySelectorAll('polyline')].find(x=>x.getAttribute('stroke')==='#0a2239');
     const [x,y]=terrain.getAttribute('points').trim().split(/\\s+/)[1].split(',').map(Number);
     const v=svg.createSVGPoint();v.x=x;v.y=y;const t=v.matrixTransform(svg.getScreenCTM());return{x:t.x,y:t.y};}''')
   p.mouse.click(target['x']+3,target['y']-3)
   # Segundo punto con coordenadas auxiliares via lineas de guia para PK0 z40
   guide=p.evaluate('''()=>{const svg=document.querySelector('#cad');const all=[...svg.querySelectorAll('line')];
     const g=all.find(n=>n.getAttribute('stroke')==='#2686c5' && n.getAttribute('x1')!==n.getAttribute('x2'));
     return g?.getAttribute('x1');}''')
   assert guide is not None
   # Un segundo clic cercano a PK50 dentro del dominio.
   p.mouse.click(target['x']+10,target['y']+40)
   p.locator('#finishBtn').click()
   v=p.evaluate('window.__saved.contactos[0].vertices')
   assert v[0]['s_m']==pytest.approx(50,abs=1e-8)
   assert v[0]['z_m']==pytest.approx(90,abs=1e-8)
  finally:b.close()
