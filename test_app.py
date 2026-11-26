"""Run with python -m unittest test_app.py."""
import unittest
from unittest.mock import patch
import json
import pandas as pd
from streamlit.testing.v1 import AppTest
from datos import BASE, normalize

class DashboardTests(unittest.TestCase):
    def test_filters_and_totals(self):
        snapshot = normalize(pd.read_csv(BASE/'data/casos.csv',dtype=str).to_dict('records'))
        totals = snapshot.groupby('ano').casos.sum()
        with patch('datos.fetch_data',return_value=(snapshot,'TEST')):
            at = AppTest.from_file(str(BASE/'app.py'),default_timeout=30).run()
            self.assertFalse(at.exception)
            self.assertEqual(at.metric[0].value,f'{int(totals.sum()):,}'.replace(',','.'))
            self.assertEqual([m.value for m in at.metric][1:],[f'{int(totals[y]):,}'.replace(',','.') for y in [2022,2023,2024]])
            at.multiselect[0].set_value([2022,2024]).run()
            self.assertEqual(at.metric[0].value,f'{int(totals[2022]+totals[2024]):,}'.replace(',','.'))
            self.assertEqual(set(at.dataframe[0].value['Año']),{2022,2024})
            at.selectbox[0].select('27').run()
            at.selectbox[1].select('27495').run()
            self.assertFalse(at.exception)
            expected = snapshot[snapshot.cod_mun_o=='27495'].groupby('ano').casos.sum()
            self.assertEqual([m.value for m in at.metric],[str(expected[2022]+expected[2024]),str(expected[2022]),str(expected[2024])])
            at.multiselect[0].set_value([2022]).run()
            self.assertTrue((at.dataframe[0].value['Año']==2022).all())
            at.selectbox[0].select('05').run()
            self.assertEqual(at.selectbox[1].value,'Todos')
            self.assertFalse(at.exception)
            at.multiselect[0].set_value([]).run()
            self.assertTrue(at.info)
            self.assertEqual(len(at.metric),0)
            at.multiselect[0].set_value([2022,2023,2024]).run()
            self.assertEqual(len(at.metric),4)
            self.assertFalse(at.exception)

    def test_snapshot_consistency(self):
        snapshot = normalize(pd.read_csv(BASE/'data/casos.csv',dtype=str).to_dict('records'))
        metadata = json.loads((BASE/'data/snapshot.json').read_text())
        self.assertEqual({str(k):int(v) for k,v in snapshot.groupby('ano').casos.sum().items()},metadata['totales'])

if __name__=='__main__':
    unittest.main()
