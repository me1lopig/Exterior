"""Regresiones v0.8.3: el terreno de PERFIL1 es la referencia comun de todas las salidas."""
from __future__ import annotations

from io import StringIO
import numpy as np
import pandas as pd
import ezdxf
import matplotlib.axes
import pytest

from perfil_geologico.servicios.importar_campana import importar_campana
from perfil_geologico.calculos.proyeccion import proyectar_puntos
from perfil_geologico.calculos.terreno import terreno_de_campana, incidencias_cota_inicio
from perfil_geologico.calculos.dpsh import curvas_dpsh
from perfil_geologico.visualizacion.perfil_plotly import crear_figura_perfil
from perfil_geologico.servicios.exportacion import figura_perfil_imagen, contactos_a_dxf
from perfil_geologico.modelos.dominio import Proyecto
from perfil_geologico.tests.test_campana_multifichero_v08 import _libros, _xlsx


def escenario():
    """Topo quebrada y tres PK, incluyendo STA; trabajo y terreno con cotas coherentes."""
    libros = _libros()
    libros['foo.xlsx'] = _xlsx([['ESTACIONES','Distancia','Cota'],
                               ['STA',0,119.0],['S-01',5,120.75],['P-01',8,118.2]])
    datos, _ = importar_campana(libros)
    sondeos = proyectar_puntos(datos['Sondeos'], datos['Eje'])
    dpsh = proyectar_puntos(datos['Ensayos_DPSH'], datos['Eje'])
    terreno = terreno_de_campana(datos, sondeos)
    return datos, sondeos, dpsh, terreno


def test_cotas_inicios_y_primera_lectura_separadas():
    d, s, p, t = escenario()
    assert incidencias_cota_inicio(t,s,p) == []
    np.testing.assert_allclose(t['cota_boca_m'], [119.,120.75,118.2])
    np.testing.assert_allclose(t['s_m'], [0.,5.,8.])
    assert s.iloc[0]['cota_boca_m'] == 120.75
    assert p.iloc[0]['cota_inicio_m'] == 118.2
    curvas = curvas_dpsh(p, d['Lecturas_DPSH'], .12)
    assert curvas[0]['s_m'] == 8.
    assert curvas[0]['cota_inicio_m'] == 118.2
    assert curvas[0]['tramos'][0][0]['z_m'] == pytest.approx(118.0)  # 20 cm bajo terreno, correcto.


def test_desfase_se_detecta_y_no_se_corrige_silenciosamente():
    _, s, p, t = escenario()
    p.loc[p.index[0], 'cota_inicio_m'] -= .21
    errores = incidencias_cota_inicio(t,s,p)
    assert len(errores) == 1 and 'P-01' in errores[0]
    assert '118.200' in errores[0]
    assert p.iloc[0]['cota_inicio_m'] == pytest.approx(117.99)
    assert incidencias_cota_inicio(t,s,p, tolerancia_m=.25) == []


def test_fuera_del_terreno_detectado():
    _, s, p, t = escenario()
    p.loc[p.index[0], 's_m'] = 9.0
    assert 'fuera de la topografia' in incidencias_cota_inicio(t,s,p)[0]


def test_modelo_minicad_terreno_sondeo_y_penetro_coinciden():
    d,s,p,t = escenario()
    # Cargamos el componente sin arrancar Streamlit, no disponible en todos los CI.
    import importlib, sys, types
    from unittest.mock import patch
    v1=types.ModuleType('streamlit.components.v1')
    v1.declare_component=lambda *a,**k: lambda **kwargs: None
    comp=types.ModuleType('streamlit.components');comp.v1=v1
    st=types.ModuleType('streamlit');st.components=comp
    with patch.dict(sys.modules,{'streamlit':st,'streamlit.components':comp,'streamlit.components.v1':v1}):
        mod=importlib.import_module('perfil_geologico.componentes.minicad')
        modelo = mod.modelo_minicad(s,d['Intervalos'],d['Unidades'],[],[],p,d['Lecturas_DPSH'],terreno_puntos=t)
    assert modelo['terreno'] == [{'s_m':0.,'z_m':119.},{'s_m':5.,'z_m':120.75},{'s_m':8.,'z_m':118.2}]
    assert modelo['bounds']['ymax'] > 120.75
    assert max(r['z1'] for r in modelo['sondeos']) == pytest.approx(120.75)
    assert modelo['dpsh'][0]['s_m'] == 8.
    assert modelo['dpsh'][0]['cota_inicio_m'] == 118.2


def test_plotly_terreno_sin_puntos_sta_y_inicio_penetro_en_cota():
    d,s,p,t = escenario()
    fig = crear_figura_perfil(Proyecto(),s,d['Intervalos'],d['Unidades'],[],p,d['Lecturas_DPSH'],
                               terreno_puntos=t, rango_pk=(0,8))
    linea = next(tr for tr in fig.data if tr.name == 'Terreno (puntos PERFIL1)')
    assert linea.mode == 'lines'  # STA contribuye a la geometria; sin marca individual.
    np.testing.assert_allclose(linea.x, [0,5,8])
    np.testing.assert_allclose(linea.y, [119,120.75,118.2])
    cabeza = next(tr for tr in fig.data if tr.name == 'Inicio penetrómetro')
    assert list(cabeza.x) == [8.]
    assert list(cabeza.y) == [118.2]
    cota_columna = [sh for sh in fig.layout.shapes if sh.type == 'line' and sh.x0 == 5. and sh.x1 == 5.]  # no shape expected for cap; cap has width
    assert len(cota_columna) == 0
    assert any(sh.type == 'line' and sh.y0 == 120.75 and sh.y1 == 120.75 for sh in fig.layout.shapes)
    curva = next(tr for tr in fig.data if tr.name == 'P-01')
    assert curva.y[0] == pytest.approx(118.0)


def test_pdf_svg_usa_todos_los_puntos_perfil1(monkeypatch):
    d,s,p,t = escenario()
    trazos=[]
    original = matplotlib.axes.Axes.plot
    def guardar(self, *args, **kwargs):
        if len(args)>=2:
            try:
                xs=list(map(float,args[0])); ys=list(map(float,args[1]))
                trazos.append((xs,ys))
            except (TypeError,ValueError):
                pass
        return original(self,*args,**kwargs)
    monkeypatch.setattr(matplotlib.axes.Axes,'plot',guardar)
    raw=figura_perfil_imagen(Proyecto(),s,d['Intervalos'],d['Unidades'],[],p,d['Lecturas_DPSH'],.02,
                                rango_pk=(0,8),terreno_puntos=t,formato='svg')
    assert raw.startswith(b'<?xml')
    assert any(x==[0.,5.,8.] and y==[119.,120.75,118.2] for x,y in trazos)
    assert any(x==[8.] and y==[118.2] for x,y in trazos)  # marca de la boca


def test_dxf_editable_preserva_cota_inicio_y_puntos_terreno():
    d,s,p,t = escenario()
    raw=contactos_a_dxf([],[],proyecto=Proyecto(),sondeos=s,dpsh=p,
                          lecturas_dpsh=d['Lecturas_DPSH'],terreno_puntos=t,rango_pk=(0,8))
    cad=ezdxf.read(StringIO(raw.decode('utf-8')))
    elementos=list(cad.modelspace())
    terreno=next(e for e in elementos if e.dxf.layer=='TERRENO' and e.dxftype()=='LWPOLYLINE')
    assert list(terreno.get_points('xy')) == [(0.,119.),(5.,120.75),(8.,118.2)]
    inicios=[e for e in elementos if e.dxftype()=='CIRCLE']
    assert any(e.dxf.layer=='DPSH' and e.dxf.center.x==8. and e.dxf.center.y==118.2 for e in inicios)
    assert any(e.dxf.layer=='SONDEOS' and e.dxf.center.x==5. and e.dxf.center.y==120.75 for e in inicios)
    assert any(e.dxf.layer=='DPSH' and e.dxftype()=='LWPOLYLINE' and
               list(e.get_points('xy'))[0]==(8.,118.2) for e in elementos)
