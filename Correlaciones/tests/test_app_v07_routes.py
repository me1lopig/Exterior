"""Recorridos simulados de nuevas rutas. No equivale a UI visual real."""
import importlib.util
import os
import sys
import unittest
from tests.test_app_mock_smoke import FakeStreamlit


class FakeConWebbStroud(FakeStreamlit):
    def __getattr__(self,n):
        original=super().__getattr__(n)
        def wrapper(*a,**k):
            if n=='checkbox' and k.get('key') in ('webb_hay_n','sb_confirmado'):
                return True
            return original(*a,**k)
        return wrapper


class CaminosNuevos(unittest.TestCase):
    def test_app_con_datos_webb_y_stroud(self):
        import calculos.webb_stroud as ws
        wb_orig,sb_orig=ws.calcular_webb,ws.calcular_stroud_butler
        wb_l,sb_l=[],[]
        def wb(*a,**k):
            wb_l.append((a,k))
            return wb_orig(*a,**k)
        def sb(*a,**k):
            sb_l.append((a,k))
            return sb_orig(*a,**k)
        ws.calcular_webb,ws.calcular_stroud_butler=wb,sb
        fake=FakeConWebbStroud()
        prev=sys.modules.get('streamlit')
        sys.modules['streamlit']=fake
        try:
            path=os.path.dirname(os.path.dirname(__file__))
            spec=importlib.util.spec_from_file_location('_geocorrelaciones_app_v07',os.path.join(path,'app.py'))
            mod=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertEqual(len(wb_l),1)
            self.assertEqual(len(sb_l),1)
            self.assertTrue(sb_l[0][1]['f2_confirmado'])
            self.assertEqual(wb_l[0][0][1],'Arena saturada')
            self.assertGreaterEqual(len(fake.tables),3)
        finally:
            ws.calcular_webb,ws.calcular_stroud_butler=wb_orig,sb_orig
            if prev is None:sys.modules.pop('streamlit',None)
            else:sys.modules['streamlit']=prev

if __name__=='__main__':unittest.main()
