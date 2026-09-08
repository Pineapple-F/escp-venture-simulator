import unittest
from financing import transact
from engine import RuleError
from founder import save_plan

class FinancingTests(unittest.TestCase):
    def setUp(self):
        self.u={'start':'2026-03-31','companies':[{'id':'c'}],'rounds':[{'company':'c','industry':'软件','available':'2020-01-01'}]}
        self.i={k:{'name':k,'rounds':[{'company':'other','industry':'软件','available':'2020-01-01'}]} for k in ['a','b']}
        self.s={'revision':0,'cash':999,'founder_contacts':{'c':{'a':{},'b':{}}},'founder_plans':{'c':{'target':100,'pre_money':400,'cash':50,'currency':'CNY','purpose':'研发','materials':['financials','use_of_funds','cap_table']}}}
    def act(self,kind,iid='a',amount=100):
        self.s['founder_plans']['c'].setdefault('budget',{'research':100})
        self.s['founder_plans']['c'].setdefault('burn',10)
        self.s=transact(self.s,{'company':'c','institution':iid,'type':'financing_'+kind,'amount':amount},self.u,self.i)
        return self.s['founder_rounds']['c']
    def test_close_once(self):
        self.act('submit');r=self.act('week');self.assertEqual(r['applications']['a']['status'],'terms')
        self.act('accept');r=self.act('week');self.assertEqual(r['cash'],150);self.assertEqual(r['raised'],100)
        self.assertEqual(r['original_ownership'],.8);self.assertEqual(r['applications']['a']['ownership'],.2)
        self.assertEqual(self.s['cash'],999)
        self.assertEqual(self.act('week')['cash'],150)
        with self.assertRaises(RuleError):self.act('accept')
    def test_materials_retry(self):
        self.s['founder_plans']['c']['budget']={}
        self.act('submit');self.assertEqual(self.act('week')['applications']['a']['status'],'materials')
        self.s['founder_plans']['c']['budget']={'research':100}
        self.act('submit');self.assertEqual(self.act('week')['applications']['a']['status'],'terms')
    def test_overcommit_and_dilution(self):
        self.act('submit',amount=60);self.act('submit','b',60);self.act('week');self.act('accept')
        with self.assertRaises(RuleError):self.act('accept','b')
        self.act('decline','b');self.act('submit','b',40);self.act('week');self.act('accept','b');r=self.act('week')
        self.assertEqual(r['raised'],100);self.assertAlmostEqual(r['applications']['a']['ownership'],.12)
        self.assertAlmostEqual(r['applications']['b']['ownership'],.08)
    def test_no_history_rejects_and_no_bypass(self):
        self.i['a']['rounds']=[];self.act('submit');self.assertEqual(self.act('week')['applications']['a']['status'],'rejected')
        with self.assertRaises(RuleError):self.act('accept')
    def test_plan_lock_and_rejected_revision(self):
        self.i['a']['rounds']=[];self.act('submit')
        changed=dict(self.s['founder_plans']['c'],target=200)
        with self.assertRaises(RuleError):save_plan(self.s,{'company':'c','plan':changed},self.u)
        self.act('week')
        out=save_plan(self.s,{'company':'c','plan':changed},self.u)
        self.assertNotIn('c',out['founder_rounds'])
        self.assertEqual(out['founder_round_archives']['c'][0]['target'],100)
        self.assertEqual(out['founder_plans']['c']['target'],200)
