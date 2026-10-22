"""Smoke test lógico de la interfaz con Streamlit simulado (sin navegador)."""
from __future__ import annotations

import runpy
import sys
import types
from pathlib import Path
import unittest


class FakeStreamlit(types.ModuleType):
    def __init__(self):
        super().__init__('streamlit')
        self.sidebar=self
        self.column_config=self
        self.selection=types.SimpleNamespace(points=[])
        self.metrics=[]

    def __enter__(self): return self
    def __exit__(self,*args): return False
    def __getattr__(self,name):
        if name in {'NumberColumn','TextColumn'}:
            return lambda *a, **kw: None
        if name=='stop':
            raise AssertionError('La aplicación ejecutó st.stop() por entradas inválidas')
        return lambda *a,**kw: None

    def columns(self,especificacion,**kwargs):
        return [self for _ in range(especificacion if isinstance(especificacion,int) else len(especificacion))]
    def tabs(self,labels): return [self for _ in labels]
    def text_input(self,label,**kw): return kw.get('value','')
    def number_input(self,label,*args,**kw): return kw.get('value',0.0)
    def selectbox(self,label,options,*args,**kw): return options[kw.get('index',0)]
    def radio(self,label,options,*args,**kw): return options[kw.get('index',0)]
    def toggle(self,label,**kw): return kw.get('value',False)
    def data_editor(self,data,**kw): return data
    def plotly_chart(self,fig,**kw):
        return types.SimpleNamespace(selection=types.SimpleNamespace(points=[]))
    def metric(self,label,value,**kw): self.metrics.append((label,value))
    def download_button(self,*args,**kw): return False
    def expander(self,*args,**kw): return self


class InterfazSmokeTest(unittest.TestCase):
    def test_render_lógico_por_defecto(self):
        fake=FakeStreamlit()
        real=sys.modules.get('streamlit')
        sys.modules['streamlit']=fake
        try:
            runpy.run_path(str(Path(__file__).resolve().parents[1]/'app.py'),run_name='__main__')
            self.assertTrue(any('Combinaciones' in k and v=='26' for k,v in fake.metrics))
            self.assertTrue(any('Presión de servicio neta' in k for k,v in fake.metrics))
        finally:
            if real is None: sys.modules.pop('streamlit',None)
            else: sys.modules['streamlit']=real


if __name__=='__main__': unittest.main()
