import unittest
from streamlit.testing.v1 import AppTest
class SmokeTests(unittest.TestCase):
    def test_arranque(self):
        at=AppTest.from_file('app.py',default_timeout=60).run()
        self.assertFalse(at.exception, str(at.exception))
        self.assertTrue(any('Geo_App' in t.value for t in at.title))
