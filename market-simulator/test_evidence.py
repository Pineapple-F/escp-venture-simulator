import copy
import json
from pathlib import Path
import unittest
from evidence_engine import new_game,apply,public_state,RuleError
from engine import terms

class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.u=json.loads(Path('runtime/universe-v3.json').read_text())
    def test_missing_is_unknown(self):
        t=terms({'currency':'USD'},[])
        self.assertIsNone(t['target']);self.assertIsNone(t['pre_money']);self.assertIsNone(t['reference'])
    def test_currency_not_changed(self):
        r=dict(amount=123456,currency='CNY',conflict=False,date='2020-01-01',available='2020-01-02',stage='A轮')
        self.assertEqual(terms({'currency':'USD'},[r])['reference']['currency'],'CNY')
    def test_allocation_and_advance(self):
        s=new_game(self.u);cid=next(c['id'] for c in self.u['companies'] if not c.get('closed'))
        n=apply(s,dict(type='offer',company=cid,amount=12345),self.u)
        self.assertEqual(n['cash'],s['cash']-12345)
        self.assertEqual(n['positions'][cid]['cost'],12345)
        self.assertEqual(n['opening_point']['cash'],s['cash'])
        self.assertEqual(n['last_result']['amount'],12345)
        self.assertEqual(len(n['transaction_points']),1)
        public=public_state(n,self.u)
        self.assertFalse(public['positions'][cid]['legacy_assumption'])
        self.assertIsNone(public['transaction_points'][0]['sim_assets'])
        after=apply(n,dict(type='advance'),self.u)
        self.assertEqual(after['cash'],n['cash']);self.assertFalse(after['notifications'])
        self.assertEqual(len(after['market_path']),len(s['market_path']))
    def test_old_records_preserved_but_not_presented_as_verified(self):
        s=new_game(self.u);cid=self.u['companies'][0]['id']
        s['positions'][cid]=dict(cost=100,lots=[],scenario=True,ownership=.2,sim_value=150)
        original=copy.deepcopy(s);public=public_state(s,self.u)
        self.assertEqual(original,s)
        self.assertIsNone(public['positions'][cid]['ownership'])
        self.assertTrue(public['positions'][cid]['legacy_assumption'])
        self.assertIsNone(public['curve'][-1]['unrealized'])
        self.assertEqual(public['positions'][cid]['cost'],100)
    def test_cannot_bypass_with_legacy_invest(self):
        with self.assertRaises(RuleError):apply(new_game(self.u),dict(type='invest'),self.u)

if __name__=='__main__':unittest.main()
