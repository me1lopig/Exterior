"""Regresiones v0.8.4: curvas confinadas, PK y cotas invariantes, bordes reales."""
import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from perfil_geologico.calculos.dpsh import distribucion_curvas, curvas_dpsh
from perfil_geologico.calculos.proyeccion import proyectar_puntos
from perfil_geologico.calculos.terreno import terreno_de_campana
from perfil_geologico.calculos.zonas import construir_zonas, validar_contactos_dominio, base_dominio
from perfil_geologico.modelos.dominio import Proyecto, Contacto, VerticeContacto
from perfil_geologico.servicios.importar_campana import importar_campana
from perfil_geologico.servicios.exportacion import contactos_a_dxf
from perfil_geologico.visualizacion.perfil_plotly import crear_figura_perfil

BASE = Path(__file__).resolve().parents[1] / 'ejemplos/campana_multifichero_sintetica'


def caso():
    books = {p.name:p.read_bytes() for p in BASE.iterdir() if p.suffix.lower()=='.xlsx'}
    datos, _ = importar_campana(books)
    sondeos = proyectar_puntos(datos['Sondeos'],datos['Eje'])
    penetraciones = proyectar_puntos(datos['Ensayos_DPSH'],datos['Eje'])
    return datos,sondeos,penetraciones,terreno_de_campana(datos,sondeos)


def test_curvas_limitadas_sin_modificar_n20_ni_cotas():
    datos,s,d,t=caso()
    pk=(float(t['s_m'].min()),float(t['s_m'].max()))
    n20=datos['Lecturas_DPSH']
    escala,sentidos=distribucion_curvas(d,n20,.12,s,pk)
    assert 0 < escala <= .12
    all_stations=sorted(set(s['s_m'].tolist()+d['s_m'].tolist()))
    curves=curvas_dpsh(d,n20,escala,sentidos)
    for c in curves:
        station=float(c['s_m'])
        assert station >= pk[0] and station <= pk[1]
        q=next(r for r in d.itertuples(index=False) if r.ensayo_id==c['ensayo_id'])
        original=n20[n20['ensayo_id']==c['ensayo_id']].sort_values('profundidad_m')
        px=[p for tramo in c['tramos'] for p in tramo]
        assert [p['n20'] for p in px]==pytest.approx(original['n20'].tolist())
        assert [p['z_m'] for p in px]==pytest.approx((q.cota_inicio_m-original['profundidad_m']).tolist())
        assert all(pk[0]-1e-9 <= p['s_m'] <= pk[1]+1e-9 for p in px)
        sorted_others=[v for v in all_stations if v!=station]
        for p in px:
            if p['s_m']>=station:
                right=min((v for v in sorted_others if v>station),default=pk[1])
                assert p['s_m'] <= (station+right)/2+1e-7
            else:
                left=max((v for v in sorted_others if v<station),default=pk[0])
                assert p['s_m'] >= (station+left)/2-1e-7


def test_ultimo_penetro_se_representa_hacia_dentro():
    s=pd.DataFrame([{'s_m':3.0}])
    d=pd.DataFrame([{'s_m':10.,'ensayo_id':'P-final', 'cota_inicio_m':130.,'profundidad_m':10.}])
    l=pd.DataFrame([{'ensayo_id':'P-final','profundidad_m':.2,'n20':100.}])
    escala,sentidos=distribucion_curvas(d,l,.12,s,(0,10))
    assert sentidos['P-final']==-1
    p=curvas_dpsh(d,l,escala,sentidos)[0]['tramos'][0][0]
    assert 0 < p['s_m'] < 10
    assert p['z_m']==pytest.approx(129.8)
    assert p['n20']==100


def test_trazado_conextremos_en_ambos_bordes_cierra_dos_zonas():
    datos,s,d,t=caso()
    xmin,xmax=float(t['s_m'].min()),float(t['s_m'].max())
    base=base_dominio(s,d,terreno_puntos=t)
    z=float(t['cota_boca_m'].min())-1.0
    assert base < z
    c=Contacto(contacto_id='c-bordes',nombre='Contacto entre lados',unidad_superior='',unidad_inferior='',vertices=[
        VerticeContacto(s_m=xmin,z_m=z),VerticeContacto(s_m=xmax,z_m=z)
    ])
    validar_contactos_dominio(s,[c],t,d)
    zonas,avisos=construir_zonas(s,[c],terreno_puntos=t,dpsh=d)
    assert len(zonas)==2,avisos
    assert not any('extremos libres' in x for x in avisos)
    # El borde inferior visible y el usado para cerrar polígonos deben coincidir.
    assert min(min(y for x,y in zona['coordenadas']) for zona in zonas)==pytest.approx(base)


def test_servidor_rechaza_contacto_fuera_del_dominio():
    datos,s,d,t=caso()
    xmin,xmax=float(t['s_m'].min()),float(t['s_m'].max())
    z=float(t['cota_boca_m'].max())+5
    c=Contacto(contacto_id='c-fuera',nombre='Fuera',unidad_superior='',unidad_inferior='',vertices=[
        VerticeContacto(s_m=xmin,z_m=z), VerticeContacto(s_m=xmax,z_m=z)
    ])
    with pytest.raises(ValueError,match='limites geologicos'):
        validar_contactos_dominio(s,[c],t,d)


def test_plotly_y_dxf_no_desbordan_y_conservan_bocas():
    import ezdxf
    datos,s,d,t=caso()
    xmin,xmax=float(t['s_m'].min()),float(t['s_m'].max())
    project=Proyecto()
    fig=crear_figura_perfil(project,s,datos['Intervalos'],datos['Unidades'],[],d,
              datos['Lecturas_DPSH'],escala_dpsh=.12,terreno_puntos=t,rango_pk=(xmin,xmax))
    keys=set(d['ensayo_id'])
    for trace in fig.data:
        if trace.name in keys:
            assert all(xmin-1e-9<=float(x)<=xmax+1e-9 for x in trace.x)
    raw=contactos_a_dxf([],proyecto=project,sondeos=s,dpsh=d,
                 lecturas_dpsh=datos['Lecturas_DPSH'],intervalos=datos['Intervalos'],
                 unidades=datos['Unidades'],escala_dpsh=.12,rango_pk=(xmin,xmax),terreno_puntos=t)
    doc=ezdxf.read(io.StringIO(raw.decode('utf-8')))
    lines=[line for line in doc.modelspace() if line.dxf.layer=='DPSH' and line.dxftype()=='LWPOLYLINE']
    assert len(lines)>=len(d)
    for line in lines:
        for xy in line.get_points('xy'):
            assert xmin-1e-7<=xy[0]<=xmax+1e-7
    heads=[entity for entity in doc.modelspace() if entity.dxf.layer=='DPSH' and entity.dxftype()=='CIRCLE']
    for row in d.itertuples(index=False):
        assert any(abs(x.dxf.center.x-row.s_m)<1e-8 and abs(x.dxf.center.y-row.cota_inicio_m)<1e-8 for x in heads)
