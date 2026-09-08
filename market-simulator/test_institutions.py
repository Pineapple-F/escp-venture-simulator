import unittest
from institutions import pool

class PoolTests(unittest.TestCase):
    def test_filters_and_pages(self):
        r=dict(company='other',name='案例企业',industry='软件',stage='A轮',available='2020-01-01',source_ids=['source'])
        index={str(i):dict(id=str(i),name='机构'+str(i),rounds=[r]) for i in range(25)}
        result=pool(index,'selected',{'industry':'软件','stage':'A轮'},'2026-03-31')
        self.assertEqual(result['total'],25)
        self.assertEqual(len(result['items']),12)
        self.assertEqual(len(pool(index,'selected',{},'2026-03-31',page=3)['items']),1)
        self.assertEqual(pool(index,'selected',{},'2026-03-31',scope='industry')['total'],0)
        self.assertEqual(pool(index,'selected',{},'2026-03-31',query='机构24')['total'],1)
        self.assertEqual(pool(index,'selected',{},'2019-01-01')['total'],0)
        self.assertEqual(pool(index,'selected',{},'2026-03-31',page=999)['page'],3)
