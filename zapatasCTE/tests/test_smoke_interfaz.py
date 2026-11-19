"""Simulacion de flujo Streamlit SIN navegador (solo deteccion de excepciones Python)."""
import runpy
import sys
from types import ModuleType,SimpleNamespace
from pathlib import Path
import pandas as pd

class FakeContainer:
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def __getattr__(self, key):
        return lambda *a, **kw: None

class FakeState(dict):
    pass

class FakeStreamlit(ModuleType):
    def __init__(self):
        super().__init__('streamlit')
        self.session_state=FakeState()
    def set_page_config(self,**kwargs): pass
    def tabs(self,labels): return [FakeContainer() for _ in labels]
    def columns(self,labels,**kwargs):
        n=labels if isinstance(labels,int) else len(labels)
        return [FakeContainer() for _ in range(n)]
    def expander(self,*a,**kw): return FakeContainer()
    def number_input(self,*a,**kw): return kw.get('value',0)
    def selectbox(self,label,options,**kw): return list(options)[0]
    def text_input(self,label,**kw): return kw.get('value','')
    def checkbox(self,label,**kw): return kw.get('value',False)
    def radio(self,label,options,**kw): return list(options)[0]
    def data_editor(self,df,**kw): return df
    def button(self,*a,**kw): return True
    def plotly_chart(self,*a,**kw): return SimpleNamespace(selection=SimpleNamespace(points=[]))
    def download_button(self,*a,**kw): return None
    def stop(self): raise AssertionError('No se obtuvo resultado de prueba')
    def __getattr__(self,n):
        if n in ('markdown','caption','title','subheader','info','warning','success','error',
                 'metric','write','dataframe','code','divider'):
            return lambda *a,**kw: None
        raise AttributeError(n)


def test_smoke_calcular_y_visualizar(monkeypatch):
    fake=FakeStreamlit()
    monkeypatch.setitem(sys.modules,'streamlit',fake)
    raiz=Path(__file__).resolve().parents[1]
    runpy.run_path(str(raiz/'app.py'),run_name='__main__')
    assert len(fake.session_state['ultimo_calculo']['rows'])>0
    assert fake.session_state['ultimo_calculo']['rows'][0]['q_asiento_bruta_mpa']>0
