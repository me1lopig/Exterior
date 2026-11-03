"""Adaptador de libros de campana a GeoPerfil.

No ejecuta formulas ni macros; conserva trazabilidad por archivo/hoja/fila.
Las estaciones se expresan como PK acumulado (m) y cota real (m).
Los golpes del penetrometro se conservan sin atribuirles norma DPSH.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from io import BytesIO
import math
import re
import unicodedata
from typing import Mapping

import pandas as pd
import openpyxl

from perfil_geologico.servicios.datos_demo import crear_datos_demo
from perfil_geologico.utiles.validacion import validar_datos

PALETA = ('#D1A979','#9DAF93','#C7B68C','#929CA9','#BE9D81','#9CA7B4','#DDC799','#9EB4AE')
LIBROS = ('PERFIL1','BKFL','DPRG','ISPT','ListadoLab')


def _norm(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(s).strip().lower()) if not unicodedata.combining(c))


def _numero(v, campo, fila, archivo, *, permitir_vacio=False):
    if v is None or (isinstance(v, str) and not v.strip()):
        if permitir_vacio:
            return None
        raise ValueError(f'{archivo}, fila {fila}: {campo} vacio (el cero es un valor valido).')
    try:
        result = float(v.strip().replace(' ', '').replace(',', '.') if isinstance(v,str) else v)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{archivo}, fila {fila}: {campo} no numerico ({v!r}).') from exc
    if not math.isfinite(result):
        raise ValueError(f'{archivo}, fila {fila}: {campo} no finito.')
    return result


def _cabecera_columnas(row):
    used = Counter()
    cols=[]
    for j, val in enumerate(row):
        key=str(val).strip() if val is not None and str(val).strip() else f'Columna_{j+1}'
        used[key] += 1
        cols.append(key if used[key]==1 else f'{key}__{used[key]}')
    return cols


def _filas(contenido: bytes, nombre: str):
    if len(contenido) > 15*1024*1024:
        raise ValueError(f'{nombre}: libro demasiado grande (limite 15 MB).')
    if len(contenido)<4 or contenido[:2]!=b'PK':
        raise ValueError(f'{nombre}: no es un libro XLSX valido.')
    wb=openpyxl.load_workbook(BytesIO(contenido), read_only=True, data_only=False, keep_links=False)
    try:
        ws=wb.worksheets[0]
        ws.reset_dimensions()
        data=ws.iter_rows(values_only=True)
        header=next(data, None)
        if not header:
            raise ValueError(f'{nombre}: no tiene encabezados.')
        encabezados=_cabecera_columnas(header)
        registros=[]
        for nro, values in enumerate(data,start=2):
            if nro>150001:
                raise ValueError(f'{nombre}: limite de 150000 filas superado.')
            if not any(v is not None and str(v).strip() for v in values):
                continue
            if any(isinstance(v,str) and v.startswith('=') for v in values):
                raise ValueError(f'{nombre}, fila {nro}: contiene formula; exporte valores antes de importar.')
            valores = list(values) + [None] * max(0, len(encabezados)-len(values))
            registros.append((nro,dict(zip(encabezados,valores))))
        return ws.title, encabezados, registros
    finally:
        wb.close()


def _v(registro, nombre, archivo):
    wanted=_norm(nombre)
    for k,v in registro.items():
        if _norm(k)==wanted:
            return v
    raise ValueError(f'{archivo}: falta la columna {nombre!r}.')


def _id(v, nombre, fila):
    s=str(v).strip().upper() if v is not None else ''
    if not s:
        raise ValueError(f'{nombre}, fila {fila}: identificador vacio.')
    return s


def _fecha(value):
    if value is None: return ''
    return value.isoformat() if hasattr(value,'isoformat') else str(value)


def importar_campana(archivos: Mapping[str,bytes]) -> tuple[dict[str,pd.DataFrame],list[str]]:
    """Admite los archivos independientemente del orden; exige PERFIL1.

    Retorna tablas del motor v0.7 + estaciones, SPT, muestras, laboratorio y fuentes.
    """
    registros={}
    fuentes=[]
    avisos=[]
    for nombre, contenido in archivos.items():
        hoja,columnas,items=_filas(bytes(contenido),nombre)
        cab={_norm(c) for c in columnas}
        if {'estaciones','distancia','cota'}.issubset(cab): clave='PERFIL1'
        elif {'profundidad inicial','profundidad final','estrato'}.issubset(cab): clave='BKFL'
        elif {'numero de golpes','profundidad','descripcion muestra'}.issubset(cab): clave='DPRG'
        elif {'ispt_inc1','ispt_pen1','spt (valores centrales)'}.issubset(cab): clave='ISPT'
        elif {'unidad geotecnica','ensayo geotecnia'}.issubset(cab): clave='ListadoLab'
        else:
            raise ValueError(f'{nombre}: no se identifica ninguno de los cinco formatos por sus encabezados.')
        if clave in registros:
            raise ValueError(f'Hay dos archivos de tipo {clave}; seleccione solo uno.')
        registros[clave]=items
        fuentes.append({'archivo':nombre,'tipo':clave,'hoja':hoja,'filas':len(items),
                        'sha256':sha256(contenido).hexdigest()})
    if 'PERFIL1' not in registros:
        raise ValueError('Falta PERFIL1.xlsx, obligatorio para posiciones y cotas.')
    estaciones=[]
    ids=set()
    for n, row in registros['PERFIL1']:
        idrec=_id(_v(row,'ESTACIONES','PERFIL1'), 'PERFIL1',n)
        if idrec in ids:
            raise ValueError(f'PERFIL1: identificador repetido {idrec}.')
        ids.add(idrec)
        pk=_numero(_v(row,'Distancia','PERFIL1'),'Distancia',n,'PERFIL1')
        z=_numero(_v(row,'Cota','PERFIL1'),'Cota',n,'PERFIL1')
        if pk<0: raise ValueError(f'PERFIL1, fila {n}: PK negativo.')
        estaciones.append({'reconocimiento':idrec,'pk_m':pk,'cota_m':z,
                           'tipo_punto':'terreno' if idrec=='STA' else 'reconocimiento','archivo':'PERFIL1','fila':n})
    if not estaciones: raise ValueError('PERFIL1 no contiene estaciones.')
    distancias=[x['pk_m'] for x in estaciones]
    if any(b < a for a,b in zip(distancias,distancias[1:])):
        avisos.append('PERFIL1: las estaciones se ordenaron por PK acumulado.')
    estaciones.sort(key=lambda x:x['pk_m'])
    if len(set(distancias))<len(distancias):
        avisos.append('PERFIL1: existen estaciones en el mismo PK; revise si es intencionado.')
    if max(distancias)<=min(distancias):
        raise ValueError('PERFIL1: la longitud del perfil debe ser positiva.')
    ubicaciones={p['reconocimiento']:p for p in estaciones}
    sondeos_info={}
    def validar_reconocimiento(idrec, fuente, n):
        if idrec not in ubicaciones:
            raise ValueError(f'{fuente}, fila {n}: {idrec} no figura en PERFIL1.')
        if ubicaciones[idrec]['tipo_punto']=='terreno':
            raise ValueError(f'{fuente}, fila {n}: {idrec} es un punto topografico, no un reconocimiento de campo.')
    intervalos=[]
    unidad_detalles={}
    for n,row in registros.get('BKFL',[]):
        idrec=_id(_v(row,'Descripción Muestra','BKFL'),'BKFL',n)
        validar_reconocimiento(idrec,'BKFL',n)
        desde=_numero(_v(row,'Profundidad inicial','BKFL'),'Profundidad inicial',n,'BKFL')
        hasta=_numero(_v(row,'Profundidad final','BKFL'),'Profundidad final',n,'BKFL')
        if desde<0 or hasta<=desde: raise ValueError(f'BKFL, fila {n}: intervalo de profundidad incorrecto.')
        estrato=_v(row,'Estrato','BKFL')
        codigo=f'EST_{str(estrato).strip()}' if estrato is not None else ''
        if not codigo: raise ValueError(f'BKFL, fila {n}: codigo de estrato vacio.')
        nombre=str(_v(row,'Descripción','BKFL') or codigo).strip()
        descripcion=str(row.get('Descripción__2') or nombre).strip()
        if codigo not in unidad_detalles:
            unidad_detalles[codigo]=nombre
        elif unidad_detalles[codigo]!=nombre:
            avisos.append(f'BKFL: el estrato {codigo} tiene descripciones diferentes; revise correspondencia.')
        intervalos.append({'sondeo_id':idrec,'desde_m':desde,'hasta_m':hasta,'unidad_id':codigo,
                           'descripcion':descripcion,'archivo':'BKFL','fila':n})
        sondeos_info[idrec]=max(sondeos_info.get(idrec,0.0),hasta)
    sondeos=[]
    for idrec,prof in sondeos_info.items():
        p=ubicaciones[idrec]
        sondeos.append({'sondeo_id':idrec,'x_m':p['pk_m'],'y_m':0.0,
                        'cota_boca_m':p['cota_m'],'profundidad_m':prof,'descripcion':'Sondeo - BKFL'})
    if not sondeos: avisos.append('No se han importado intervalos BKFL; el perfil no tendra columnas litologicas.')
    unidades=[{'unidad_id':codigo,'nombre':nombre,'orden':i,'color':PALETA[(i-1)%len(PALETA)]}
             for i,(codigo,nombre) in enumerate(unidad_detalles.items(),start=1)]
    penetraciones={}
    lecturas=[]
    for n,row in registros.get('DPRG',[]):
        idrec=_id(_v(row,'Descripción Muestra','DPRG'),'DPRG',n)
        validar_reconocimiento(idrec,'DPRG',n)
        prof=_numero(_v(row,'Profundidad','DPRG'),'Profundidad',n,'DPRG')
        golpe=_numero(_v(row,'Número de Golpes','DPRG'),'Numero de Golpes',n,'DPRG')
        if prof<0 or golpe<0: raise ValueError(f'DPRG, fila {n}: profundidades y golpes deben ser >= 0.')
        if idrec not in penetraciones:
            p=ubicaciones[idrec]
            penetraciones[idrec]={'ensayo_id':idrec,'x_m':p['pk_m'],'y_m':0.,
                         'cota_inicio_m':p['cota_m'],'profundidad_m':prof,
                         'fecha':_fecha(_v(row,'Fecha Entrada','DPRG')),
                         'tipo_ensayo':'PENETROMETRO (subtipo no confirmado)'}
        penetraciones[idrec]['profundidad_m']=max(penetraciones[idrec]['profundidad_m'],prof)
        lecturas.append({'ensayo_id':idrec,'profundidad_m':prof,'n20':golpe,
                         'estado':'registrado','observaciones':'Golpes originales DPRG; subtipo por confirmar',
                         'archivo':'DPRG','fila':n})
    if penetraciones:
        avisos.append('DPRG: el subtipo de penetracion no esta documentado. Se muestran golpes/20 cm sin asumir norma DPSH ni rechazo.')
    sptraw={}
    def _spt(n,row,fuente,overwrite=False):
        idrec=_id(_v(row,'Descripción Muestra',fuente),fuente,n)
        validar_reconocimiento(idrec,fuente,n)
        profundidad=_numero(_v(row,'Profundidad inicial',fuente),'Profundidad inicial',n,fuente)
        if profundidad<0: raise ValueError(f'{fuente}, fila {n}: profundidad negativa.')
        golpes=[]
        for i in range(1,5):
            golpes.append(_numero(_v(row,f'ISPT_INC{i}',fuente),f'ISPT_INC{i}',n,fuente, permitir_vacio=True))
        llave=(idrec,round(profundidad,5))
        central=_numero(_v(row,'SPT (valores centrales)',fuente),'SPT central',n,fuente,permitir_vacio=True)
        if llave in sptraw and not overwrite:
            anterior=sptraw[llave]
            if tuple(golpes)!=tuple(anterior['golpes']):
                avisos.append(f'{fuente}, fila {n}: SPT duplicado con golpes distintos ({idrec}, {profundidad:g} m). Se mantiene ISPT.')
            return
        if all(v is None for v in golpes):
            avisos.append(f'{fuente}, fila {n}: SPT sin secuencia de golpes completa.')
        if central is not None and golpes[1] is not None and golpes[2] is not None and abs(central-(golpes[1]+golpes[2]))>.01:
            avisos.append(f'{fuente}, fila {n}: N central no coincide con incrementos 2+3; se conservan ambos.')
        sptraw[llave]={'id':idrec,'prof':profundidad,'golpes':golpes,'central':central,'origen':fuente,'fila':n,
                       'pen':[(_numero(_v(row,f'ISPT_PEN{i}',fuente),f'ISPT_PEN{i}',n,fuente,permitir_vacio=True)
                               if fuente=='ISPT' else None) for i in range(1,5)]}
    for n,row in registros.get('ISPT',[]): _spt(n,row,'ISPT',True)
    laboratorio=[]
    muestras=[]
    labs_raw=[]
    for n,row in registros.get('ListadoLab',[]):
        idrec=_id(_v(row,'Descripción Muestra','ListadoLab'),'ListadoLab',n)
        validar_reconocimiento(idrec,'ListadoLab',n)
        tipo=str(_v(row,'Ensayo geotecnia','ListadoLab') or '').strip().upper()
        prof=_numero(_v(row,'Profundidad inicial','ListadoLab'),'Profundidad inicial',n,'ListadoLab')
        if prof<0: raise ValueError(f'ListadoLab, fila {n}: profundidad negativa.')
        if tipo=='SPT': _spt(n,row,'ListadoLab')
        ug=str(_v(row,'Unidad geotécnica','ListadoLab') or '').strip()
        out={'reconocimiento':idrec,'profundidad_m':prof,'tipo':tipo,'unidad_geotecnica':ug,
             'uscs':str(row.get('Clasificación USCS') or '').strip(),
             'finos_pct':_numero(row.get('Tamiz Finos'),'Finos',n,'ListadoLab',permitir_vacio=True),
             'll_pct':_numero(row.get('LL'),'LL',n,'ListadoLab',permitir_vacio=True),
             'lp_pct':_numero(row.get('LP'),'LP',n,'ListadoLab',permitir_vacio=True),
             'ip_pct':_numero(row.get('IP'),'IP',n,'ListadoLab',permitir_vacio=True),
             'sulfatos_mg_kg':_numero(row.get('Sulfatos (mg/kg de suelo) Media.'),'Sulfatos',n,'ListadoLab',permitir_vacio=True),
             'rcs_kpa':_numero(row.get('RCS (kpa)'),'RCS (kPa)',n,'ListadoLab',permitir_vacio=True),
             'densidad_seca_kn_m3':_numero(row.get('Densidad Seca Kn/m3'),'Densidad seca',n,'ListadoLab',permitir_vacio=True),
             'densidad_humeda_kn_m3':_numero(row.get('Densidad Húmeda KN/m3'),'Densidad humeda',n,'ListadoLab',permitir_vacio=True),
             'humedad_pct':_numero(row.get('Humedad'),'Humedad',n,'ListadoLab',permitir_vacio=True),
             'phi_cd_grados':_numero(row.get('Ángulo de Rozamiento con denaje'),'Angulo rozamiento',n,'ListadoLab',permitir_vacio=True),
             'cohesion_cd_kpa':_numero(row.get('Cohesión KPa con drenaje'),'Cohesion',n,'ListadoLab',permitir_vacio=True),
             'archivo':'ListadoLab','fila':n}
        laboratorio.append(out)
        labs_raw.append({'archivo':'ListadoLab','fila':n, **{k:_fecha(v) for k,v in row.items()}})
        if tipo!='SPT': muestras.append(out.copy())
    if not registros.get('ISPT') and any(r['tipo']=='SPT' for r in laboratorio):
        avisos.append('ISPT no incluido: los SPT proceden de ListadoLab, sin incrementos de penetracion documentados.')
    spt=[]
    for _,it in sorted(sptraw.items()):
        p=ubicaciones[it['id']]
        secuencia='/'.join(str(int(v)) if v is not None and v.is_integer() else (f'{v:g}' if v is not None else '?') for v in it['golpes'])
        spt.append({'sondeo_id':it['id'],'profundidad_m':it['prof'],'pk_m':p['pk_m'],
                    'cota_m':p['cota_m']-it['prof'],'secuencia':secuencia,'n_central':it['central'],
                    **{f'inc{i}':it['golpes'][i-1] for i in range(1,5)},
                    **{f'pen{i}_mm':it['pen'][i-1] for i in range(1,5)},
                    'archivo':it['origen'],'fila':it['fila']})
    # Tablas de v0.7 con su esquema original para compatibilidad.
    base=crear_datos_demo()
    def tabla(nombre,rows):
        columnas=list(base[nombre].columns)
        extra=[c for r in rows for c in r if c not in columnas]
        return pd.DataFrame(rows,columns=columnas+list(dict.fromkeys(extra)))
    datos={
        'Sondeos':tabla('Sondeos',sondeos),
        'Intervalos':tabla('Intervalos',intervalos),
        'Unidades':tabla('Unidades',unidades),
        'Ensayos_DPSH':tabla('Ensayos_DPSH',list(penetraciones.values())),
        'Lecturas_DPSH':tabla('Lecturas_DPSH',lecturas),
        'Eje':pd.DataFrame([{'orden':1,'x_m':0.0,'y_m':0.},
                           {'orden':2,'x_m':max(distancias),'y_m':0.}]),
        'Estaciones':pd.DataFrame(estaciones,columns=['reconocimiento','pk_m','cota_m','tipo_punto','archivo','fila']),
        'SPT':pd.DataFrame(spt,columns=['sondeo_id','profundidad_m','pk_m','cota_m','secuencia','n_central',
                 'inc1','inc2','inc3','inc4','pen1_mm','pen2_mm','pen3_mm','pen4_mm','archivo','fila']),
        'Muestras':pd.DataFrame(muestras,columns=list(laboratorio[0]) if laboratorio else [
            'reconocimiento','profundidad_m','tipo','unidad_geotecnica','uscs','finos_pct',
            'll_pct','lp_pct','ip_pct','sulfatos_mg_kg','rcs_kpa','densidad_seca_kn_m3','densidad_humeda_kn_m3','humedad_pct','phi_cd_grados','cohesion_cd_kpa','archivo','fila']),
        'Laboratorio':pd.DataFrame(laboratorio,columns=list(laboratorio[0]) if laboratorio else [
            'reconocimiento','profundidad_m','tipo','unidad_geotecnica','uscs','finos_pct','ll_pct',
            'lp_pct','ip_pct','sulfatos_mg_kg','rcs_kpa','densidad_seca_kn_m3','densidad_humeda_kn_m3','humedad_pct','phi_cd_grados','cohesion_cd_kpa','archivo','fila']),
        'Laboratorio_original':pd.DataFrame(labs_raw),
        'Fuentes':pd.DataFrame(fuentes,columns=['archivo','tipo','hoja','filas','sha256']),
    }
    errores, warnings=validar_datos(*(datos[x] for x in ('Sondeos','Intervalos','Unidades','Ensayos_DPSH','Lecturas_DPSH')))
    if errores: raise ValueError('Datos importados incompatibles: '+'; '.join(errores))
    return datos,avisos+warnings
