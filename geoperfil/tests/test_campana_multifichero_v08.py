"""Regresiones de la nueva entrada multifichero. Todo fixture es sintetico."""
from __future__ import annotations
from io import BytesIO
import pytest
import pandas as pd
import openpyxl

from perfil_geologico.servicios.importar_campana import importar_campana
from perfil_geologico.servicios.persistencia import proyecto_a_json, proyecto_desde_json
from perfil_geologico.calculos.terreno import terreno_de_campana
from perfil_geologico.calculos.proyeccion import proyectar_puntos
from perfil_geologico.modelos.dominio import Proyecto
from perfil_geologico.visualizacion.perfil_plotly import crear_figura_perfil
from perfil_geologico.servicios.exportacion import contactos_a_dxf, figura_perfil_imagen


def _xlsx(rows):
    wb=openpyxl.Workbook()
    ws=wb.active
    for row in rows: ws.append(row)
    out=BytesIO();wb.save(out);return out.getvalue()


def _libros():
    perfil=_xlsx([['ESTACIONES','Distancia','Cota'],['STA',0,0],['S-01',5,120.75],['P-01',8,118.2]])
    bkfl=_xlsx([['Descripción Muestra','Fecha de inicio real','Profundidad inicial','Profundidad final','Estrato','Descripción','Descripción'],
       ['S-01',None,0,3,1,'Arcilla','Arcilla marron'],['S-01',None,3,7,2,'Marga','Marga gris']])
    dprg=_xlsx([['Descripción Muestra','Nº Albarán','Fecha Entrada','Clase Hormigón','Observaciones','Profundidad nivel freático','Profundidad','Número de Golpes','Observaciones'],
       ['P-01',1,None,'PENETRÓMETRO','',0,.2,4,''],['P-01',1,None,'PENETRÓMETRO','',0,.4,5,'']])
    ispt=_xlsx([['Descripción Muestra','Profundidad inicial','ISPT_SEAT','Espesor en milímetros','SPT (valores centrales)','Valores ensayos','Profundidad nivel freático',
                'ISPT_INC1','ISPT_INC2','ISPT_INC3','ISPT_INC4','ISPT_PEN1','ISPT_PEN2','ISPT_PEN3','ISPT_PEN4'],
       ['S-01',1.5,2,600,5,'2-3-2-4',0,2,3,2,4,150,150,150,150]])
    lab=_xlsx([['Unidad geotécnica','Descripción Muestra','Ensayo geotecnia','Profundidad inicial',
                'ISPT_INC1','ISPT_INC2','ISPT_INC3','ISPT_INC4','SPT (valores centrales)',
                'Tamiz Finos','LL','LP','IP','Clasificación USCS','Sulfatos (mg/kg de suelo) Media.'],
       ['UG-01','S-01','SPT',1.5,2,3,2,4,5,None,None,None,None,None,None],
       ['UG-01','S-01','MI',2.5,1,1,2,2,None,'12,5','40,2','25,0','15,2','CL','100,0']])
    return {'foo.xlsx':perfil,'bar.xlsx':bkfl,'baz.xlsx':dprg,'bee.xlsx':ispt,'lab.xlsx':lab}


def test_importa_cinco_por_cabecera_y_conserva_cota():
    datos,avisos=importar_campana(_libros())
    assert (len(datos['Sondeos']),len(datos['Intervalos']),len(datos['Ensayos_DPSH']),len(datos['SPT']),len(datos['Muestras'])) ==(1,2,1,1,1)
    assert datos['Sondeos'].iloc[0]['cota_boca_m']==120.75
    assert datos['SPT'].iloc[0]['cota_m']==119.25
    assert datos['SPT'].iloc[0]['secuencia']=='2/3/2/4'
    assert datos['Muestras'].iloc[0]['finos_pct']==12.5
    assert datos['Muestras'].iloc[0]['sulfatos_mg_kg']==100.0
    assert len(datos['Laboratorio'])==2
    assert len(datos['Fuentes'])==5
    assert any('subtipo' in a for a in avisos)


def test_terreno_incluye_sta_sin_crear_prospeccion():
    datos,_=importar_campana(_libros())
    son=proyectar_puntos(datos['Sondeos'],datos['Eje'])
    t=terreno_de_campana(datos,son)
    assert t['s_m'].tolist()==[0.0,5.0,8.0]
    assert t['cota_boca_m'].tolist()==[0.0,120.75,118.2]
    assert son['s_m'].tolist()==[5.0]
    assert len(datos['Ensayos_DPSH'])==1
    assert datos['Estaciones'].set_index('reconocimiento').loc['STA','tipo_punto']=='terreno'
    assert datos['Eje']['x_m'].tolist()==[0.0,8.0]


def test_spt_sin_duplicados_laboratorio():
    datos,_=importar_campana(_libros())
    assert len(datos['SPT'])==1
    assert datos['SPT'].iloc[0]['archivo']=='ISPT'


def test_spot_fecha_y_fila_trazables():
    datos,_=importar_campana(_libros())
    assert datos['Intervalos']['fila'].tolist()==[2,3]
    assert datos['SPT']['fila'].tolist()==[2]
    assert all(len(v)==64 for v in datos['Fuentes']['sha256'])


def test_sin_perfil_errores():
    libros=_libros()
    libros.pop('foo.xlsx')
    with pytest.raises(ValueError,match='Falta PERFIL1'):
        importar_campana(libros)


def test_cota_vacia_no_equivale_a_cero():
    libros=_libros()
    libros['foo.xlsx']=_xlsx([['ESTACIONES','Distancia','Cota'],['STA',0,0],['S-01',5,None],['P-01',8,118.2]])
    with pytest.raises(ValueError, match='Cota vacio'):
        importar_campana(libros)


def test_cota_cero_aceptada():
    libros=_libros()
    libros['foo.xlsx']=_xlsx([['ESTACIONES','Distancia','Cota'],['STA',0,0],['S-01',5,0],['P-01',8,0]])
    d,_=importar_campana(libros)
    assert (d['Estaciones']['cota_m']==0).all()


def test_reconocimiento_no_listado_invalida():
    libros=_libros()
    libros['foo.xlsx']=_xlsx([['ESTACIONES','Distancia','Cota'],['STA',0,0],['S-99',5,0],['P-01',8,0]])
    with pytest.raises(ValueError,match='no figura en PERFIL1'):
        importar_campana(libros)


def test_spt_discrepante_conserva_ispt_y_advierte():
    libros=_libros()
    libros['lab.xlsx']=_xlsx([['Unidad geotécnica','Descripción Muestra','Ensayo geotecnia','Profundidad inicial',
                'ISPT_INC1','ISPT_INC2','ISPT_INC3','ISPT_INC4','SPT (valores centrales)'],
                ['UG-01','S-01','SPT',1.5,90,90,90,90,180]])
    d,a=importar_campana(libros)
    assert d['SPT'].iloc[0]['secuencia']=='2/3/2/4'
    assert any('duplicado con golpes distintos' in v for v in a)


def test_roundtrip_tablas_y_capas():
    datos,_=importar_campana(_libros())
    proyecto=Proyecto()
    proyecto.capas['muestras']=True
    proyecto.texto_ensayos_pt=14
    paquete=proyecto_a_json(proyecto,datos)
    p2,d2=proyecto_desde_json(paquete)
    assert p2.capas['muestras'] and p2.texto_ensayos_pt==14
    assert set(datos)==set(d2)
    assert len(d2['Laboratorio_original'])==2
    assert d2['SPT'].iloc[0]['secuencia']=='2/3/2/4'


def test_spt_en_perfil_y_apagable():
    datos,_=importar_campana(_libros())
    pr=Proyecto()
    s=proyectar_puntos(datos['Sondeos'],datos['Eje'])
    d=proyectar_puntos(datos['Ensayos_DPSH'],datos['Eje'])
    kwargs=dict(terreno_puntos=terreno_de_campana(datos,s),spt=datos['SPT'],muestras=datos['Muestras'],laboratorio=datos['Laboratorio'])
    fig=crear_figura_perfil(pr,s,datos['Intervalos'],datos['Unidades'],[],d,datos['Lecturas_DPSH'],rango_pk=(0,8),**kwargs)
    assert any(t.name=='SPT (golpes)' for t in fig.data)
    pr.capas['spt']=False
    fig2=crear_figura_perfil(pr,s,datos['Intervalos'],datos['Unidades'],[],d,datos['Lecturas_DPSH'],rango_pk=(0,8),**kwargs)
    assert not any(t.name=='SPT (golpes)' for t in fig2.data)


def test_dxf_spt_editable_y_apagable():
    import ezdxf
    datos,_=importar_campana(_libros())
    pr=Proyecto()
    s=proyectar_puntos(datos['Sondeos'],datos['Eje'])
    d=proyectar_puntos(datos['Ensayos_DPSH'],datos['Eje'])
    kwargs=dict(terreno_puntos=terreno_de_campana(datos,s),spt=datos['SPT'],muestras=datos['Muestras'],laboratorio=datos['Laboratorio'])
    def export():
        raw=contactos_a_dxf([],[],proyecto=pr,sondeos=s,dpsh=d,lecturas_dpsh=datos['Lecturas_DPSH'],rango_pk=(0,8),**kwargs)
        return list(ezdxf.read(__import__('io').StringIO(raw.decode('utf-8'))).modelspace())
    items=export()
    assert any(e.dxf.layer=='SPT' and 'SPT 2/3/2/4' in e.dxf.text for e in items)
    pr.capas['spt']=False
    assert not any(e.dxf.layer=='SPT' for e in export())


def test_png_y_etiquetas_stored():
    datos,_=importar_campana(_libros())
    pr=Proyecto()
    s=proyectar_puntos(datos['Sondeos'],datos['Eje'])
    d=proyectar_puntos(datos['Ensayos_DPSH'],datos['Eje'])
    raw=figura_perfil_imagen(pr,s,datos['Intervalos'],datos['Unidades'],[],d,datos['Lecturas_DPSH'],.018,
        rango_pk=(0,8),terreno_puntos=terreno_de_campana(datos,s),spt=datos['SPT'],formato='svg')
    assert b'SPT 2/3/2/4' in raw


def test_los_nombres_no_importan_pero_columnas_si():
    d,_=importar_campana(_libros())
    assert len(d['Sondeos'])==1
    with pytest.raises(ValueError,match='no se identifica'):
        importar_campana({'foo.xlsx':_xlsx([['nada'],[42]])})


def test_solo_perfil_y_bkfl_permitido():
    libros=_libros()
    datos,_=importar_campana({k:v for k,v in libros.items() if k in ('foo.xlsx','bar.xlsx')})
    assert len(datos['Sondeos'])==1 and datos['Lecturas_DPSH'].empty
    assert datos['SPT'].empty


def test_lab_no_spt_sin_ispt():
    libros=_libros()
    del libros['bee.xlsx']
    d,a=importar_campana(libros)
    assert len(d['SPT'])==1
    assert d['SPT'].iloc[0]['secuencia']=='2/3/2/4'
    assert any('ISPT no incluido' in v for v in a)


def test_sta_tiene_cota_real_propia_y_no_se_extrapola():
    libros = _libros()
    libros['foo.xlsx']=_xlsx([['ESTACIONES','Distancia','Cota'],['STA',0,135.25],['S-01',5,120.75],['P-01',8,118.2]])
    d,_=importar_campana(libros)
    s=proyectar_puntos(d['Sondeos'],d['Eje'])
    terreno=terreno_de_campana(d,s)
    assert terreno.iloc[0].to_dict()=={'s_m':0.0,'cota_boca_m':135.25}
    assert s['sondeo_id'].tolist()==['S-01']
    assert d['Ensayos_DPSH']['ensayo_id'].tolist()==['P-01']
    from perfil_geologico.calculos.presentacion import preparar_guitarra
    gr=preparar_guitarra(s,proyectar_puntos(d['Ensayos_DPSH'],d['Eje']), (0,8), paso_m=5, terreno_puntos=terreno)
    assert gr['marcas'][0] == {'pk_m':0.0,'terreno_m':135.25}
    assert all(r['nombre']!='STA' for r in gr['reconocimientos'])


@pytest.mark.parametrize('tipo', ['BKFL', 'DPRG', 'ISPT', 'ListadoLab'])
def test_sta_no_puede_ser_prospeccion_en_libros_de_campo(tipo):
    libros = _libros()
    tipo_archivo={'BKFL':'bar.xlsx','DPRG':'baz.xlsx','ISPT':'bee.xlsx','ListadoLab':'lab.xlsx'}[tipo]
    wb=openpyxl.load_workbook(BytesIO(libros[tipo_archivo]))
    # Descripcion Muestra es siempre el identificador de reconocimiento en los cuatro formatos.
    ws=wb.active
    idx=next(i for i,c in enumerate(ws[1],1) if c.value=='Descripción Muestra')
    ws.cell(2,idx,'STA')
    out=BytesIO();wb.save(out)
    libros[tipo_archivo]=out.getvalue()
    with pytest.raises(ValueError,match='punto topografico'):
        importar_campana(libros)


def test_nueva_aplicacion_arranca_sin_datos_demostrativos():
    from perfil_geologico.servicios.datos_demo import crear_datos_vacios
    d=crear_datos_vacios()
    assert d['Eje'].empty and d['Sondeos'].empty and d['Ensayos_DPSH'].empty
    assert {'Sondeos','Intervalos','Unidades','Eje','Lecturas_DPSH'}.issubset(d)


def test_vista_importacion_solo_multifichero():
    from pathlib import Path
    ruta=Path(__file__).resolve().parents[1] / 'paginas' / 'vistas.py'
    codigo=ruta.read_text(encoding='utf-8')
    assert 'crear_plantilla_excel' not in codigo
    assert 'leer_excel(' not in codigo
    assert 'Plantilla GeoPerfil clasica' not in codigo
    assert 'Tabla editable' not in codigo
    assert 'Seleccionar archivos de campana' in codigo


def test_proyecto_guardado_v08_migra_sta_como_punto_terreno():
    datos,_=importar_campana(_libros())
    legacy=datos['Estaciones'].drop(columns=['tipo_punto']).copy()
    legacy['es_origen']=legacy['reconocimiento'].eq('STA')
    datos['Estaciones']=legacy
    raw=proyecto_a_json(Proyecto(),datos)
    _,restaurado=proyecto_desde_json(raw)
    puntos=restaurado['Estaciones']
    assert 'es_origen' not in puntos.columns
    assert puntos.set_index('reconocimiento').loc['STA','tipo_punto']=='terreno'
    assert terreno_de_campana(restaurado,proyectar_puntos(restaurado['Sondeos'],restaurado['Eje']))['s_m'].tolist()[0]==0.0
