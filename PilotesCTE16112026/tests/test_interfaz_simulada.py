"""Prueba de recorrido con Streamlit simulado; NO reemplaza prueba en navegador."""
import importlib.util
import pathlib
import sys
import types


class Estado(dict):
    def __getattr__(self,k):return self[k]
    def __setattr__(self,k,v):self[k]=v


class FakeStreamlit:
    def __init__(self):
        self.session_state=Estado()
        self.sidebar=self
        self.column_config=types.SimpleNamespace(SelectboxColumn=lambda *a,**kw:None)
        self.events=[]

    def __enter__(self):return self
    def __exit__(self,*a):return False
    def __getattr__(self,name):
        if name in ('set_page_config','title','caption','warning','info','header','subheader','markdown',
                    'success','error','metric','write','dataframe','plotly_chart','download_button'):
            def meth(*a,**kw):
                self.events.append(name)
            return meth
        raise AttributeError(name)

    def columns(self,n):return [self]*n
    def tabs(self,labels):return [self]*len(labels)
    def checkbox(self,*a,**kw):return kw.get('value',False)
    def number_input(self,*a,**kw):return kw.get('value',kw.get('min_value',0.))
    def selectbox(self,*a,**kw):return list(kw.get('options',a[1] if len(a)>1 else []))[0]
    def radio(self,*a,**kw):return list(kw.get('options',a[1] if len(a)>1 else []))[0]
    def text_input(self,*a,**kw):return kw.get('value','')
    def text_area(self,*a,**kw):return kw.get('value','')
    def data_editor(self,value,**kw):return value.copy()
    def button(self,label,*a,**kw):return label in ('⚙️ Calcular matriz','📄 Generar memoria Word')
    def spinner(self,*a,**kw):return self


def test_recorrido_default_y_generacion_word(monkeypatch):
    fake=FakeStreamlit()
    monkeypatch.setitem(sys.modules,'streamlit',fake)
    modpath=pathlib.Path(__file__).parents[1]/'app.py'
    spec=importlib.util.spec_from_file_location('app_test_sim',modpath)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()
    assert 'datos_resultados_v3' in fake.session_state
    res,errores=fake.session_state.datos_resultados_v3
    assert res and 'word_buffer_v3' in fake.session_state
    assert fake.session_state.word_buffer_v3[:2]==b'PK'
    assert 'plotly_chart' in fake.events
    assert 'download_button' in fake.events


def test_rechazo_de_celda_NaN():
    import pandas as pd
    fake=FakeStreamlit()
    sys.modules['streamlit']=fake
    modpath=pathlib.Path(__file__).parents[1]/'app.py'
    spec=importlib.util.spec_from_file_location('app_test_null',modpath)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    df=mod.df_ejemplo()
    df.loc[1,'Estrato']=float('nan')
    import pytest
    with pytest.raises(mod.ErrorDatos,match='NaN'):
        mod.desde_tabla(df)
