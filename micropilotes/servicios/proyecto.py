"""Esquema versionado para recuperar entradas, nunca resultados de terceros."""
import json
from math import isfinite

from modelos.inyecciones import COLS, LEGACY

SCHEMA=2
def _check(v, depth=0):
    if depth>12: raise ValueError('JSON demasiado anidado.')
    if v is None or isinstance(v,(bool,str)): 
        if isinstance(v,str) and len(v)>10000: raise ValueError('Texto demasiado largo.')
        return
    if isinstance(v,(int,float)):
        if not isfinite(v) or abs(v)>1e12: raise ValueError('Número no válido.')
        return
    if isinstance(v,list):
        if len(v)>10000: raise ValueError('Lista demasiado extensa.')
        for x in v: _check(x,depth+1)
        return
    if isinstance(v,dict):
        if len(v)>10000: raise ValueError('Demasiados campos.')
        for k,x in v.items():
            if not isinstance(k,str) or len(k)>10000: raise ValueError('Clave no válida.')
            _check(x,depth+1)
        return
    raise ValueError('Tipo JSON no válido.')

def serializar(widgets,estratos,version):
    esquema=1 if estratos and all(set(f)==LEGACY for f in estratos) else SCHEMA
    p=dict(esquema=esquema,version=version,widgets=widgets,estratos=estratos)
    return json.dumps(p,ensure_ascii=False,indent=2,allow_nan=False)

def cargar(data):
    if len(data)>2_000_000: raise ValueError('Máximo 2 MB para archivo de proyecto.')
    p=json.loads(data)
    if not isinstance(p,dict) or p.get('esquema') not in (1,SCHEMA):
        raise ValueError('Formato no compatible: seleccione Proyecto JSON de v0.5.0 o posterior (esquemas 1 o 2), no el informe de resultados.')
    w=p.get('widgets'); e=p.get('estratos')
    if not isinstance(w,dict) or not isinstance(e,list) or not 1<=len(e)<=1000:
        raise ValueError('Faltan entradas o estratos.')
    _check(w); _check(e)
    cols=LEGACY if p['esquema']==1 else set(COLS)
    if any(not isinstance(f,dict) or set(f)!=cols for f in e):
        raise ValueError('Columnas de estratos incompatibles.')
    return dict(widgets=w,estratos=e)
