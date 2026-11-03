"""Regresiones de guitarra, extensiones, imagen y DXF editables."""
from __future__ import annotations

from io import BytesIO, StringIO

import ezdxf
import pandas as pd
import pytest

from perfil_geologico.calculos.presentacion import limites_perfil, preparar_guitarra
from perfil_geologico.calculos.proyeccion import proyectar_puntos, longitud_eje
from perfil_geologico.modelos.dominio import Proyecto
from perfil_geologico.servicios.datos_demo import crear_datos_demo
from perfil_geologico.servicios.exportacion import figura_perfil_imagen, figura_perfil_pdf, contactos_a_dxf
from perfil_geologico.servicios.persistencia import proyecto_a_json, proyecto_desde_json
from perfil_geologico.visualizacion.perfil_plotly import crear_figura_perfil


@pytest.fixture
def caso():
    d=crear_datos_demo()
    s=proyectar_puntos(d['Sondeos'],d['Eje'])
    p=proyectar_puntos(d['Ensayos_DPSH'],d['Eje'])
    return d,s,p


def test_tres_modos_extension(caso):
    d,s,p=caso
    long=longitud_eje(d['Eje'])
    pr=Proyecto()
    assert limites_perfil(pr,d['Eje'],s,p)==(0,long)
    pr.extension_modo='reconocimientos'; pr.margen_pk_m=5
    a,b=limites_perfil(pr,d['Eje'],s,p)
    assert 0<=a<b<=long
    pr.extension_modo='manual'; pr.pk_inicio_m=10; pr.pk_fin_m=min(long,20)
    assert limites_perfil(pr,d['Eje'],s,p)==(10,min(long,20))
    pr.pk_fin_m=long+5
    with pytest.raises(ValueError): limites_perfil(pr,d['Eje'],s,p)


def test_guitarra_fuera_de_sondeos_no_inventa_cotas(caso):
    d,s,p=caso
    largo=longitud_eje(d['Eje'])
    g=preparar_guitarra(s,p,(0,largo),50)
    assert g['marcas']
    sx=s['s_m']
    for marca in g['marcas']:
        if marca['pk_m']<sx.min()-1e-7 or marca['pk_m']>sx.max()+1e-7:
            assert marca['terreno_m'] is None


def test_persistencia_nuevos_campos(caso):
    d,_,_=caso
    p=Proyecto(extension_modo='manual',pk_inicio_m=4,pk_fin_m=25,guitarra_paso_m=25,margen_pk_m=20)
    p2,_=proyecto_desde_json(proyecto_a_json(p,d))
    assert (p2.extension_modo,p2.pk_inicio_m,p2.pk_fin_m,p2.guitarra_paso_m)==('manual',4,25,25)


def test_figure_guitarra_pk(caso):
    d,s,p=caso
    largo=longitud_eje(d['Eje'])
    fig=crear_figura_perfil(Proyecto(),s,d['Intervalos'],d['Unidades'],[],p,d['Lecturas_DPSH'],rango_pk=(0,largo))
    fig.to_json()  # valida todos los atributos Plotly
    assert fig.layout.xaxis2.matches=='x'
    assert list(fig.layout.xaxis.range)==[0,largo]
    assert len([t for t in fig.data if t.xaxis=='x2'])>0


def test_documentos_comparten_guitarra(caso):
    d,s,p=caso
    q=Proyecto()
    rango=(0,longitud_eje(d['Eje']))
    args=(q,s,d['Intervalos'],d['Unidades'],[],p,d['Lecturas_DPSH'],.12)
    pdf=figura_perfil_pdf(*args,rango_pk=rango)
    png=figura_perfil_imagen(*args,rango_pk=rango,formato='png')
    svg=figura_perfil_imagen(*args,rango_pk=rango,formato='svg')
    assert pdf[:4]==b'%PDF'
    assert png[:8]==b'\x89PNG\r\n\x1a\n'
    assert b'<svg' in svg[:3000]
    assert b'PK (m)' in svg


def test_dxf_hatch_y_guitarra(caso):
    d,s,p=caso
    zona={'zona_id':'Z1','unidad_id':'A','trama':'diagonal_45','color':'#AAAAAA',
          'coordenadas':[[10,100],[35,100],[35,95],[10,95]],
          'huecos':[[[15,99],[20,99],[20,97],[15,97]]]}
    g=contactos_a_dxf([], [zona],proyecto=Proyecto(), sondeos=s, dpsh=p,
            lecturas_dpsh=d['Lecturas_DPSH'],rango_pk=(0,longitud_eje(d['Eje'])))
    doc=ezdxf.read(StringIO(g.decode('utf-8')))
    m=doc.modelspace()
    h=list(m.query('HATCH'))
    assert len(h)==1 and len(h[0].paths)==2
    assert len(m.query('TEXT[layer=="GUITARRA"]'))>3
    assert len(m.query('LWPOLYLINE[layer=="GUITARRA"]'))>3


def test_dxf_sin_unidad_no_trama(caso):
    d,s,p=caso
    zona={'coordenadas':[[10,100],[35,100],[35,95],[10,95]],'unidad_id':''}
    a=contactos_a_dxf([], [zona],proyecto=Proyecto(), sondeos=s, dpsh=p, rango_pk=(0,longitud_eje(d['Eje'])))
    doc=ezdxf.read(StringIO(a.decode('utf-8')))
    assert len(doc.modelspace().query('HATCH'))==0
