import io
import json
import unittest
from unittest.mock import Mock, patch

import server


class FixedForecastRouteTest(unittest.TestCase):
    def setUp(self):
        self.company = next(iter(server.COMPANY_META))
        self.row = server.FORECAST_CATALOG.get(self.company)
        self.handler = server.Handler.__new__(server.Handler)
        self.handler.saved_row = Mock(return_value=(json.dumps({
            'version': 3, 'revision': 0, 'currency': 'CNY',
            'investor_id': next(iter(server.RECOMMENDER.subjects)), 'founder_custom': {
                'profile': {'name': 'Test'}, 'events': [{'type': 1}],
            },
        }),))
        self.handler.respond = Mock(side_effect=lambda code, body: (code, body))

    def test_fixed_company_reads_catalog_without_worker(self):
        self.handler.path = '/api/model-forecast?id=' + self.company
        with patch.object(server.MODEL_FORECAST, 'get', side_effect=AssertionError('unexpected inference')):
            code, result = self.handler.handle_get()
        self.assertEqual(code, 200)
        self.assertEqual(result['events'], self.row['events'])

    def test_missing_catalog_row_returns_503_without_worker(self):
        self.handler.path = '/api/model-forecast?id=' + self.company
        with patch.object(server.FORECAST_CATALOG, 'get', return_value=None), \
             patch.object(server.MODEL_FORECAST, 'get', side_effect=AssertionError('unexpected inference')):
            code, result = self.handler.handle_get()
        self.assertEqual(code, 503)
        self.assertIn('预计算预测暂不可用', result['error'])

    def test_unknown_company_returns_404(self):
        self.handler.path = '/api/model-forecast?id=unknown'
        self.assertEqual(self.handler.handle_get()[0], 404)

    def test_custom_path_still_uses_user_input(self):
        self.handler.path = '/api/custom-forecast'
        with patch.object(server.MODEL_FORECAST, 'get_custom', return_value={'similar': []}) as compute:
            code, result = self.handler.handle_get()
        self.assertEqual(code, 200)
        self.assertEqual(result['profile']['name'], 'Test')
        self.assertEqual(compute.call_args.args[0], [{'type': 1}])

    def test_financing_scenario_uses_fixed_baseline_and_dynamic_forecast(self):
        self.handler.path = '/api/financing-scenario-forecast?id=' + self.company
        scenario = {'ready': True, 'events': [{'type': 1}], 'as_of': '2026-03-31'}
        with patch('financing_scenario.build', return_value=scenario), \
             patch.object(server.MODEL_FORECAST, 'get', side_effect=AssertionError('unexpected baseline inference')), \
             patch.object(server.MODEL_FORECAST, 'get_scenario', return_value={'available': True}) as compute:
            code, result = self.handler.handle_get()
        self.assertEqual(code, 200)
        self.assertEqual(result['baseline'], self.row)
        compute.assert_called_once_with(self.company, scenario['events'], scenario['as_of'])

    def test_offer_with_missing_catalog_does_not_run_model(self):
        body = json.dumps({'type': 'offer', 'company': self.company, 'revision': 0}).encode()
        self.handler.path = '/api/action'
        self.handler.headers = {'Content-Length': str(len(body))}
        self.handler.rfile = io.BytesIO(body)
        with patch.object(server.FORECAST_CATALOG, 'get', return_value=None), \
             patch.object(server.MODEL_FORECAST, 'get', side_effect=AssertionError('unexpected inference')):
            code, result = self.handler.do_POST()
        self.assertEqual(code, 503)
        self.assertIn('预计算预测暂不可用', result['error'])


if __name__ == '__main__':
    unittest.main()
