import unittest
from founder import save_plan, save_contact, remove_contact, budget_issues
from engine import RuleError

class FounderTests(unittest.TestCase):
    def test_budget_checks(self):
        p={'budget':{'research':100},'target':100,'cash':100,'burn':10}
        self.assertEqual(budget_issues(p),[])
        self.assertTrue(budget_issues(dict(p,target=200)))
        self.assertTrue(budget_issues(dict(p,cash=243242,burn=33)))
        self.assertEqual(budget_issues(dict(p,burn=0)),[])
    def setUp(self):
        self.state={'revision':3,'cash':100,'positions':{'x':{'cost':20}}}
        self.universe={'companies':[{'id':'x'}]}
        self.action={'company':'x','plan':{'currency':'CNY','cash':600,'burn':100,'target':1000,'materials':['team'],'purpose':'研发'}}
    def test_separate_plan(self):
        out=save_plan(self.state,self.action,self.universe)
        self.assertEqual(out['cash'],100)
        self.assertEqual(out['positions'],self.state['positions'])
        self.assertNotIn('founder_plans',self.state)
        self.assertEqual(out['revision'],4)
        self.assertEqual(out['founder_plans']['x']['cash'],600)
    def test_structured_purposes_are_used_and_budget_is_automatic(self):
        action={'company':'x','plan':{'currency':'CNY','cash':600,'burn':100,'target':1000,
            'pre_money':4000,'purpose_categories':['research','hiring'],'purpose_detail':'完成商业化'}}
        plan=save_plan(self.state,action,self.universe)['founder_plans']['x']
        self.assertEqual(plan['purpose'],'产品研发、团队招聘；完成商业化')
        self.assertEqual(plan['budget'],{'research':500,'hiring':500,'marketing':0,'other':0})
        self.assertEqual(budget_issues(plan),[])
    def test_invalid(self):
        for key,value in [('cash',-1),('burn',float('nan')),('target',True),('materials',['unknown']),('purpose',12),('currency','EUR')]:
            with self.subTest(key=key):
                action={'company':'x','plan':dict(self.action['plan'],**{key:value})}
                with self.assertRaises(RuleError):save_plan(self.state,action,self.universe)
    def test_contacts_isolated_and_idempotent(self):
        index={'i':{'name':'测试机构'}}
        action={'company':'x','institution':'i','stage':'补材料','note':'预算'}
        s=save_contact(self.state,action,self.universe,index)
        s=save_contact(s,action,self.universe,index)
        self.assertEqual(len(s['founder_contacts']['x']),1)
        self.assertEqual(s['cash'],self.state['cash'])
        self.assertNotIn('founder_contacts',self.state)
        with self.assertRaises(RuleError):save_contact(s,dict(action,institution='missing'),self.universe,index)
        removed=remove_contact(s,dict(action,institution='i'),self.universe,index)
        self.assertEqual(removed['founder_contacts']['x'],{})
