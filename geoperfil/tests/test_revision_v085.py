"""Regresion v0.8.5: guitarra completa, paleta editable y TypeError MiniCAD."""
from __future__ import annotations
import ast
import json
from pathlib import Path
from io import StringIO

import ezdxf
import pytest
from perfil_geologico.calculos.estilos_unidades import aplicar_edicion_unidades
from perfil_geologico.calculos.presentacion import preparar_guitarra
from perfil_geologico.calculos.proyeccion import proyectar_puntos
from perfil_geologico.calculos.terreno import terreno_de_campana
from perfil_geologico.modelos.dominio import Proyecto
from perfil_geologico.servicios.importar_campana import importar_campana
from perfil_geologico.servicios.persistencia import proyecto_a_json, proyecto_desde_json
from perfil_geologico.servicios.exportacion import contactos_a_dxf, figura_perfil_imagen
from perfil_geologico.tests.test_campana_multifichero_v08 import _libros
from perfil_geologico.visualizacion.perfil_plotly import crear_figura_perfil

BASE = Path(__file__).resolve().parents[1]


def caso():
    datos, _ = importar_campana(_libros())
    s = proyectar_puntos(datos['Sondeos'], datos['Eje'])
    d = proyectar_puntos(datos['Ensayos_DPSH'], datos['Eje'])
    terreno = terreno_de_campana(datos, s)
    return datos, s, d, terreno


def test_guitarra_incluye_ambos_trabajos_sin_sta():
    datos, s, d, t = caso()
    resultado = preparar_guitarra(s,d,(0,8),2,terreno_puntos=t)
    assert [(r['nombre'], r['pk_m'], r['tipo']) for r in resultado['reconocimientos']] == [
        ('S-01',5.0,'Sondeo'),('P-01',8.0,'DPSH')]
    assert not any(r['nombre']=='STA' for r in resultado['reconocimientos'])


def test_plotly_guitarra_filas_distintas_y_pk_exactos():
    datos,s,d,t = caso()
    fig = crear_figura_perfil(Proyecto(),s,datos['Intervalos'],datos['Unidades'],[],d,
        datos['Lecturas_DPSH'],rango_pk=(0,8),terreno_puntos=t)
    items = {(str(tx),float(tr.y[0]),float(tr.x[0])) for tr in fig.data
             if tr.xaxis == 'x2' and getattr(tr,'text',None)
             for tx in tr.text if tx in ('S-01','P-01')}
    assert ('S-01',1.5,5.0) in items
    assert ('P-01',0.5,8.0) in items
    assert fig.layout.yaxis2.range == (-0.05,4.05)
    annots = [a.text for a in fig.layout.annotations]
    assert 'Sondeos' in annots and 'Penetrómetros' in annots


def test_dxf_guitarra_separa_sondeos_penetraciones():
    datos,s,d,t = caso()
    dxf=contactos_a_dxf([],[],proyecto=Proyecto(),sondeos=s,dpsh=d,
        lecturas_dpsh=datos['Lecturas_DPSH'],rango_pk=(0,8),terreno_puntos=t)
    doc=ezdxf.read(StringIO(dxf.decode('utf-8')))
    txt=[e.dxf.text for e in doc.modelspace().query('TEXT[layer=="GUITARRA"]')]
    for label in ('Sondeos','Penetrómetros','S-01','P-01'):
        assert label in txt
    assert 'STA' not in txt


def test_editar_unidades_recolorea_zonas_preserva_ids_y_fuente():
    datos, *_ = caso()
    originales=datos['Unidades'].copy(deep=True)
    code=str(originales.iloc[0]['unidad_id'])
    zonas=[{'zona_id':'Z1','unidad_id':code,'color':'#AAAAAA','trama':'puntos'},
           {'zona_id':'Z2','unidad_id':'','color':'#EEEEEE'}]
    nueva, nuevas_zonas = aplicar_edicion_unidades(originales,zonas,{code:{'nombre':'Mi material','color':'#04fba1'}})
    assert nueva.set_index('unidad_id').loc[code,'nombre']=='Mi material'
    assert nueva.set_index('unidad_id').loc[code,'color']=='#04FBA1'
    assert nueva['unidad_id'].tolist()==originales['unidad_id'].tolist()
    assert nuevas_zonas[0]['color']=='#04FBA1'
    assert nuevas_zonas[0]['trama']=='puntos'
    assert nuevas_zonas[1]['color']=='#EEEEEE'
    assert originales.set_index('unidad_id').loc[code,'nombre']!='Mi material'
    datos['Unidades']=nueva
    proyecto=Proyecto(zonas=nuevas_zonas)
    p2,d2=proyecto_desde_json(proyecto_a_json(proyecto, datos))
    assert d2['Unidades'].set_index('unidad_id').loc[code,'color']=='#04FBA1'
    assert p2.zonas[0]['color']=='#04FBA1'
    assert nueva.loc[nueva['unidad_id']==code, 'color'].iloc[0] == nuevas_zonas[0]['color']


def test_edicion_invalida_no_modifica_original():
    datos,*_=caso()
    tabla=datos['Unidades']
    id=str(tabla.iloc[0]['unidad_id'])
    for cambio in ({'nombre':'  ','color':'#AABBCC'}, {'nombre':'abc','color':'rojo'}):
        with pytest.raises(ValueError): aplicar_edicion_unidades(tabla,[],{id:cambio})
    assert tabla.iloc[0]['nombre']!='abc'


def test_catalogo_unidades_sin_observaciones_y_json_migra_antiguos():
    datos,*_=caso()
    assert 'observaciones' not in datos['Unidades'].columns
    datos['Unidades']['observaciones']='antiguo'
    paquete=proyecto_a_json(Proyecto(),datos)
    p2,d2=proyecto_desde_json(paquete)
    assert 'observaciones' not in d2['Unidades'].columns


def test_regresion_typeerror_miniCAD_no_duplicacion_dpsh():
    """Detecta keyword duplicada que causo TypeError en Streamlit Cloud."""
    source=(BASE/'paginas/vistas.py').read_text(encoding='utf-8')
    tree=ast.parse(source)
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and
           isinstance(n.func,ast.Name) and n.func.id=='modelo_minicad']
    assert len(calls)==1
    node=calls[0]
    assert len(node.args)==7
    assert all(k.arg!='dpsh' for k in node.keywords)
    assert len({k.arg for k in node.keywords})==len(node.keywords)


def test_formulario_unidades_muestra_selector_visual_y_no_observaciones():
    code=(BASE/'paginas/vistas.py').read_text(encoding='utf-8')
    code=code.split('def vista_unidades()',1)[1].split('def _contactos_desde_cad',1)[0]
    assert 'st.text_input("Nombre"' in code
    assert 'st.color_picker("Color seleccionado"' in code
    assert 'Guardar nombres y colores' in code
    assert 'observaciones' not in code.lower()


def test_modelo_minicad_ejecuta_con_firma_de_vista_sin_streamlit_instalado():
    """Smoke del constructor de datos del MiniCAD con un adaptador UI simulado."""
    import subprocess
    import sys
    snippet = '''
import sys,types
streamlit=types.ModuleType("streamlit");streamlit.__path__=[]
components=types.ModuleType("streamlit.components");components.__path__=[]
v1=types.ModuleType("streamlit.components.v1");v1.declare_component=lambda *a,**kw:lambda **kw2:None
sys.modules.update({"streamlit":streamlit,"streamlit.components":components,"streamlit.components.v1":v1})
from perfil_geologico.servicios.importar_campana import importar_campana
from perfil_geologico.tests.test_campana_multifichero_v08 import _libros
from perfil_geologico.calculos.proyeccion import proyectar_puntos
from perfil_geologico.calculos.terreno import terreno_de_campana
from perfil_geologico.componentes.minicad import modelo_minicad
datos,_=importar_campana(_libros());s=proyectar_puntos(datos["Sondeos"],datos["Eje"]);d=proyectar_puntos(datos["Ensayos_DPSH"],datos["Eje"])
modelo=modelo_minicad(s,datos["Intervalos"],datos["Unidades"],[],[],d,datos["Lecturas_DPSH"],escala_dpsh=.02,contactos_referencia=[],exageracion_vertical=5,terreno_puntos=terreno_de_campana(datos,s),capas={"terreno":True,"sondeos":True},texto_general_pt=10,texto_ensayos_pt=9)
assert len(modelo["dpsh"])==1
assert len(modelo["sondeos"])==2
'''
    proc = subprocess.run([sys.executable,"-c",snippet],cwd=BASE.parent,capture_output=True,text=True,timeout=30)
    assert proc.returncode==0,proc.stdout+proc.stderr
