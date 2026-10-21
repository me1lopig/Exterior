"""Smoke de rutas Python de app.py con API Streamlit simulada.
NO equivale a prueba visual con Streamlit real.
"""
import importlib
import os
import sys
import types
import unittest

class FakeStreamlit(types.ModuleType):
    def __init__(self, radio_index=0, enable_arc=False, enable_dap=False):
        super().__init__('streamlit')
        self.radio_index=radio_index
        self.enable_arc=enable_arc
        self.enable_dap=enable_dap
        self.tables=[]
        self.sidebar=self
        self.session_state={}
        self.column_config=self
    def __enter__(self):return self
    def __exit__(self, *args):return False
    def __getattr__(self,n):
        def run(*a,**k):
            if n in ('tabs','columns'):
                ncols = a[0] if isinstance(a[0],int) else len(a[0]);return [self]*ncols
            if n=='expander':return self
            if n=='checkbox':
                if k.get('key')=='arc_ap':return self.enable_arc
                if k.get('key')=='dap_tengo_n':return self.enable_dap
                return k.get('value',False)
            if n=='radio':
                val=a[1][min(self.radio_index,len(a[1])-1)]
                if 'key' in k: self.session_state[k['key']]=val
                return val
            if n=='selectbox':
                val=a[1][1 if (self.enable_dap and k.get('key') in ('dap_estado','arena_familia')) else k.get('index',0)]
                if 'key' in k:self.session_state[k['key']]=val
                return val
            if n=='number_input':
                val=k.get('value',a[3] if len(a)>3 else 0.0)
                if 'key' in k:self.session_state[k['key']]=val
                return val
            if n=='text_input':return k.get('value','')
            if n=='dataframe':self.tables.append(a[0]);return None
            return self if n.endswith('Column') else None
        return run

class Smoke(unittest.TestCase):
    def test_app_no_name_errors_in_default_path(self):
        fake=FakeStreamlit()
        prior=sys.modules.get('streamlit')
        sys.modules['streamlit']=fake
        try:
            path=os.path.dirname(os.path.dirname(__file__))
            if path not in sys.path:sys.path.insert(0,path)
            spec=importlib.util.spec_from_file_location('_geocorrelaciones_app_smoke',os.path.join(path,'app.py'))
            module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(fake.session_state['phi_modo'],'Partir de N de campo')
            self.assertEqual(fake.session_state['egran_modo'],'Partir de N de campo')
        finally:
            if prior is None:sys.modules.pop('streamlit',None)
            else:sys.modules['streamlit']=prior

    def test_app_alternate_input_paths(self):
        fake=FakeStreamlit(radio_index=1,enable_arc=True)
        prior=sys.modules.get('streamlit')
        sys.modules['streamlit']=fake
        try:
            path=os.path.dirname(os.path.dirname(__file__))
            if path not in sys.path:sys.path.insert(0,path)
            spec=importlib.util.spec_from_file_location('_geocorrelaciones_alt_app_smoke',os.path.join(path,'app.py'))
            module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(fake.session_state['phi_modo'],'Introducir N60 conocido')
            self.assertEqual(fake.session_state['egran_modo'],'Introducir N60 conocido')
        finally:
            if prior is None:sys.modules.pop('streamlit',None)
            else:sys.modules['streamlit']=prior

    def test_dappolonia_ui_path_with_averaged_raw_n(self):
        fake=FakeStreamlit(enable_dap=True)
        import calculos.dappolonia as dp
        original=dp.calcular_m_dappolonia
        llamadas=[]
        def contar(*args,**kwargs):
            llamadas.append(args)
            return original(*args,**kwargs)
        dp.calcular_m_dappolonia=contar
        prior=sys.modules.get('streamlit')
        sys.modules['streamlit']=fake
        try:
            path=os.path.dirname(os.path.dirname(__file__))
            if path not in sys.path:sys.path.insert(0,path)
            spec=importlib.util.spec_from_file_location('_geocorrelaciones_dap_app_smoke',os.path.join(path,'app.py'))
            module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.assertEqual(fake.session_state['dap_estado'],'Normalmente cargada')
            self.assertEqual(len(llamadas),1)
            self.assertEqual(llamadas[0][2], 'Normalmente cargada')
            self.assertEqual(llamadas[0][3], 'Arena limpia NC')
        finally:
            dp.calcular_m_dappolonia=original
            if prior is None:sys.modules.pop('streamlit',None)
            else:sys.modules['streamlit']=prior

if __name__=='__main__':unittest.main()
