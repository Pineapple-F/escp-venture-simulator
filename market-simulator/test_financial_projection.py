import unittest

from financial_projection import FinancialProjection


class FinancialProjectionTests(unittest.TestCase):
    def test_peer_amount_and_value_are_deterministic(self):
        rounds = []
        for index, amount in enumerate((100, 200, 300, 400, 500)):
            company = f'peer-{index}'
            rounds += [
                dict(id=f'a{index}', company=company, date='2020-01-01', available='2020-01-01',
                     industry='TECH', stage='A轮', amount=100, currency='CNY', valuation=500,
                     valuation_currency='CNY', conflict=False),
                dict(id=f'b{index}', company=company, date='2021-01-01', available='2021-01-01',
                     industry='TECH', stage='B轮', amount=amount, currency='CNY', valuation=amount * 6,
                     valuation_currency='CNY', conflict=False),
            ]
        rounds.append(dict(id='target', company='target', date='2022-01-01', available='2022-01-01',
                           industry='TECH', stage='A轮', amount=100, currency='CNY', valuation=500,
                           valuation_currency='CNY', conflict=False))
        estimator = FinancialProjection(dict(start='2023-01-31', rounds=rounds))
        forecast = {'events': [dict(event='融资', predicted=True, month_index=4,
                                    estimated_month='2023-05')]}
        result = estimator.project('target', forecast, 'CNY')
        self.assertTrue(result['available'])
        self.assertEqual(result['predicted_amount'], 300)
        self.assertEqual(result['entry_valuation'], 500)
        self.assertEqual(result['predicted_post_valuation'], 1800)
        self.assertEqual(result['value_multiple'], 3.6)
        self.assertEqual(result['basis'], '同行业同阶段')

    def test_rows_after_cutoff_are_not_used(self):
        universe = dict(start='2023-01-31', rounds=[
            dict(id='future', company='peer', date='2024-01-01', available='2024-01-01',
                 industry='TECH', stage='B轮', amount=999999, currency='CNY', valuation=None,
                 valuation_currency=None, conflict=False)
        ])
        estimator = FinancialProjection(universe)
        result = estimator.project('target', {'events': [dict(event='融资', predicted=True)]}, 'CNY')
        self.assertFalse(result['available'])


if __name__ == '__main__':
    unittest.main()
