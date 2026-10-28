"""Pruebas lógicas del flujo «Calcular» sin navegador ni ejecución de macros."""
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
        self.session_state={}
        self.selection=types.SimpleNamespace(points=[])
        self.metrics=[]
        self.warnings=[]
        self.click_calcular=False
        self.ancho_max=None

    def __enter__(self): return self
    def __exit__(self,*args): return False
    def __getattr__(self,name):
        if name in {'NumberColumn','TextColumn'}:
            return lambda *a, **kw: None
        if name=='stop':
            def _stop(): raise StopIteration('Streamlit detenido hasta Calcular')
            return _stop
        return lambda *a,**kw: None

    def columns(self,especificacion,**kwargs):
        return [self for _ in range(especificacion if isinstance(especificacion,int) else len(especificacion))]
    def tabs(self,labels): return [self for _ in labels]
    def text_input(self,label,**kw): return kw.get('value','')
    def number_input(self,label,*args,**kw):
        if label=='Bmax (m)' and self.ancho_max is not None:
            return self.ancho_max
        return kw.get('value',0.0)
    def selectbox(self,label,options,*args,**kw): return options[kw.get('index',0)]
    def radio(self,label,options,*args,**kw): return options[kw.get('index',0)]
    def toggle(self,label,**kw): return kw.get('value',False)
    def button(self,label,**kw): return self.click_calcular
    def data_editor(self,data,**kw): return data
    def plotly_chart(self,fig,**kw):
        return types.SimpleNamespace(selection=types.SimpleNamespace(points=[]))
    def metric(self,label,value,**kw): self.metrics.append((label,value))
    def warning(self,message,**kw): self.warnings.append(message)
    def download_button(self,*args,**kw): return False
    def expander(self,*args,**kw): return self


class InterfazSmokeTest(unittest.TestCase):
    def test_se_calcula_solo_al_pulsar_y_quedan_resultados_obsoletos(self):
        fake=FakeStreamlit()
        real=sys.modules.get('streamlit')
        sys.modules['streamlit']=fake
        origen=str(Path(__file__).resolve().parents[1]/'app.py')
        try:
            with self.assertRaises(StopIteration):
                runpy.run_path(origen,run_name='__main__')
            self.assertNotIn('ultimo_calculo',fake.session_state)

            fake.click_calcular=True
            runpy.run_path(origen,run_name='__main__')
            self.assertEqual(len(fake.session_state['ultimo_calculo']['resultados']),26)
            self.assertTrue(any('Presión de servicio neta' in k for k,v in fake.metrics))

            fake.click_calcular=False
            fake.ancho_max=2.0
            runpy.run_path(origen,run_name='__main__')
            self.assertEqual(len(fake.session_state['ultimo_calculo']['resultados']),26)
            self.assertTrue(any('pendientes de actualizar' in w for w in fake.warnings))
        finally:
            if real is None: sys.modules.pop('streamlit',None)
            else: sys.modules['streamlit']=real


if __name__=='__main__': unittest.main()
