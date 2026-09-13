"""Historical boundary and graph-integrity tests, independent of Parquet data."""
from copy import deepcopy
import unittest

from knowledge_graph import KnowledgeGraph


def round_record(rid, company='c1', date='2020-01-01', **extra):
    record = dict(id=rid, company=company, name='企业 ' + company,
                  industry='软件', region='北京', date=date, available=date,
                  stage='A轮', amount=1000000, currency='CNY',
                  source=['ie'], source_ids=['event-' + rid],
                  conflict=False, publication_proxy=False)
    record.update(extra)
    return record


def fixture():
    first, peer = round_record('r1'), round_record('r2', 'c2', '2021-01-01')
    future = round_record('r3', 'c3', '2028-01-01')
    universe = dict(start='2026-03-31', companies=[dict(id='c' + str(i)) for i in range(1, 5)],
                    rounds=[first, peer, future], risks=[])
    institutions = {'i1': dict(id='i1', name='共同投资机构', rounds=[first, peer, future]),
                    'i2': dict(id='i2', name='仅未来机构', rounds=[future])}
    return universe, institutions


class KnowledgeGraphTests(unittest.TestCase):
    def assert_integrity(self, graph):
        ids = [node['id'] for node in graph['nodes']]
        edge_ids = [edge['id'] for edge in graph['edges']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(edge_ids), len(set(edge_ids)))
        self.assertIn(graph['root_id'], ids)
        self.assertLessEqual(len(ids), KnowledgeGraph.MAX_NODES)
        for edge in graph['edges']:
            self.assertIn(edge['source'], ids)
            self.assertIn(edge['target'], ids)
            self.assertTrue(edge['evidence'])
            for evidence in edge['evidence']:
                self.assertTrue(evidence['source'])
                self.assertTrue(evidence['record_id'])
        # Every displayed node is connected to the selected root.
        visited = {graph['root_id']}
        while True:
            previous = set(visited)
            for edge in graph['edges']:
                if edge['source'] in visited or edge['target'] in visited:
                    visited.update([edge['source'], edge['target']])
            if previous == visited:
                break
        self.assertEqual(visited, set(ids))

    def test_company_institution_round_chain_is_evidenced(self):
        universe, institutions = fixture()
        graph = KnowledgeGraph(universe, institutions).graph('company', 'c1')
        triples = {(e['source'], e['type'], e['target']) for e in graph['edges']}
        self.assertIn(('institution:i1', 'participated', 'round:r1'), triples)
        self.assertIn(('round:r1', 'financing_of', 'company:c1'), triples)
        self.assertIn(('institution:i1', 'participated', 'round:r2'), triples)
        self.assertIn(('round:r2', 'financing_of', 'company:c2'), triples)
        self.assertFalse(any(s.startswith('company:') and t.startswith('company:')
                             for s, _, t in triples))
        evidence = next(e['evidence'] for e in graph['edges'] if e['source'] == 'round:r1')
        self.assertIn('event-r1', [item['record_id'] for item in evidence])
        money = next(n['details'] for n in graph['nodes'] if n['id'] == 'round:r1')
        self.assertEqual(money['整轮融资金额'], 1000000)
        self.assertIn('不代表', money['金额口径'])
        self.assert_integrity(graph)

    def test_participation_evidence_does_not_claim_other_investors_source_rows(self):
        row = round_record('shared', source_ids=['only-investor-a', 'only-investor-b'])
        universe = dict(start='2026-03-31', companies=[dict(id='c1')], rounds=[row], risks=[])
        institutions = {iid: dict(id=iid, name=iid, rounds=[row]) for iid in ['a', 'b']}
        graph = KnowledgeGraph(universe, institutions).graph('company', 'c1')
        for edge in graph['edges']:
            records = {item['record_id'] for item in edge['evidence']}
            if edge['type'] == 'participated':
                iid = edge['source'].split(':', 1)[1]
                self.assertEqual(records, {iid + ' / shared'})
                self.assertTrue(all('机构—融资轮次关联' in item['source'] for item in edge['evidence']))
            elif edge['type'] == 'financing_of':
                self.assertIn('only-investor-a', records)
                self.assertIn('only-investor-b', records)
        details = next(node['details'] for node in graph['nodes'] if node['type'] == 'round')
        self.assertEqual(details['来源记录'], ['only-investor-a', 'only-investor-b'])
        self.assert_integrity(graph)

    def test_future_financing_risks_and_institution_counts_are_hidden(self):
        universe, institutions = fixture()
        delayed = round_record('delayed', 'c1', '2020-01-01', available='2027-01-01')
        universe['rounds'].append(delayed)
        institutions['i1']['rounds'].append(delayed)
        universe['risks'] = [dict(company='c1', date='2024-01-01', type='abnormal_listing', records=2),
                             dict(company='c1', date='2028-01-01', type='abnormal_removed', records=999)]
        service = KnowledgeGraph(universe, institutions)
        graph = service.graph('company', 'c1')
        ids = {n['id'] for n in graph['nodes']}
        self.assertNotIn('round:r3', ids)
        self.assertNotIn('round:delayed', ids)
        self.assertNotIn('company:c3', ids)
        self.assertNotIn('institution:i2', ids)
        self.assertEqual(graph['summary']['totals']['rounds'], 1)
        self.assertEqual(graph['summary']['totals']['risks'], 1)
        institution = next(n for n in graph['nodes'] if n['type'] == 'institution')
        self.assertEqual(institution['details']['已收录融资轮次'], 2)
        self.assertEqual(institution['details']['已收录被投企业'], 2)
        with self.assertRaises(KeyError):
            service.graph('institution', 'i2')
        self.assert_integrity(graph)

    def test_institution_view_lists_actual_companies_and_rounds(self):
        universe, institutions = fixture()
        graph = KnowledgeGraph(universe, institutions).graph('institution', 'i1')
        self.assertEqual(graph['summary']['totals']['rounds'], 2)
        self.assertEqual(graph['summary']['totals']['companies'], 2)
        self.assertEqual({n['entity_id'] for n in graph['nodes'] if n['type'] == 'company'}, {'c1', 'c2'})
        self.assert_integrity(graph)

    def test_duplicate_records_are_deduplicated_and_order_is_stable(self):
        universe, institutions = fixture()
        universe['rounds'] += deepcopy(universe['rounds'])
        institutions['i1']['rounds'] += deepcopy(institutions['i1']['rounds'])
        universe['risks'] = [dict(company='c1', date='2020-01-01', type='abnormal_listing', records=2)] * 2
        before = deepcopy(universe)
        first = KnowledgeGraph(universe, institutions).graph('company', 'c1')
        universe['rounds'].reverse()
        institutions['i1']['rounds'].reverse()
        second = KnowledgeGraph(universe, institutions).graph('company', 'c1')
        self.assertEqual(first, second)
        self.assertEqual(first['summary']['totals']['rounds'], 1)
        self.assertEqual(first['summary']['totals']['risks'], 1)
        universe['rounds'].reverse()
        self.assertEqual(universe, before)
        self.assert_integrity(first)

    def test_missing_recommendation_and_noncanonical_rounds_do_not_become_edges(self):
        universe, institutions = fixture()
        not_in_universe = round_record('missing')
        wrong_company = dict(universe['rounds'][0], company='c4')
        institutions['bogus'] = dict(id='bogus', name='无可靠匹配机构', rounds=[not_in_universe, wrong_company])
        graph = KnowledgeGraph(universe, institutions).graph('company', 'c1')
        self.assertNotIn('institution:bogus', {n['id'] for n in graph['nodes']})
        self.assert_integrity(graph)

    def test_empty_company_and_invalid_entities(self):
        universe, institutions = fixture()
        service = KnowledgeGraph(universe, institutions)
        graph = service.graph('company', 'c4')
        self.assertEqual(len(graph['nodes']), 1)
        self.assertEqual(graph['edges'], [])
        self.assertFalse(graph['truncated'])
        self.assertTrue(any('不代表不存在' in note for note in graph['notes']))
        with self.assertRaises(KeyError):
            service.graph('company', 'missing')
        with self.assertRaises(ValueError):
            service.graph('person', 'anything')
        self.assert_integrity(graph)

    def test_bounded_graph_has_correct_totals_and_no_orphan_nodes(self):
        universe = dict(start='2026-03-31', companies=[dict(id='c' + str(i)) for i in range(61)], risks=[])
        own = [round_record('own-' + str(i), 'c0', f'2020-01-{i + 1:02}') for i in range(20)]
        peers = [round_record('peer-' + str(i), 'c' + str(i + 1), '2021-01-01') for i in range(60)]
        universe['rounds'] = own + peers
        institutions = {'i' + str(i): dict(id='i' + str(i), name='机构' + str(i), rounds=own + peers)
                        for i in range(20)}
        people = [dict(name='人员' + str(i), position='董事', start=None, end=None, status='时间待核验')
                  for i in range(20)]
        universe['risks'] = [dict(company='c0', date=f'2020-01-{i + 1:02}', type='abnormal_listing', records=1)
                             for i in range(20)]
        service = KnowledgeGraph(universe, institutions, lambda cid, cutoff: dict(officers=people))
        for kind, entity_id in [('company', 'c0'), ('institution', 'i0')]:
            graph = service.graph(kind, entity_id)
            self.assertTrue(graph['truncated'])
            self.assert_integrity(graph)
        totals = service.graph('company', 'c0')['summary']['totals']
        self.assertEqual(totals['rounds'], 20)
        self.assertEqual(totals['institutions'], 20)
        self.assertEqual(totals['people'], 20)
        self.assertEqual(totals['risks'], 20)

    def test_person_identity_is_company_scoped_and_future_appointments_hidden(self):
        universe, institutions = fixture()
        person = dict(name='同名人员', position='董事', start='2020-01-01', end=None, status='未记录离任')
        future = dict(person, name='未来人员', start='2028-01-01')
        calls = []

        def load(cid, cutoff):
            calls.append((cid, cutoff))
            return dict(officers=[person, person, future], note='任职记录不是员工总数。')

        service = KnowledgeGraph(universe, institutions, load)
        first, second = service.graph('company', 'c1'), service.graph('company', 'c2')
        one = [n for n in first['nodes'] if n['type'] == 'person']
        two = [n for n in second['nodes'] if n['type'] == 'person']
        self.assertEqual(len(one), 1)
        self.assertEqual(len(two), 1)
        self.assertNotEqual(one[0]['id'], two[0]['id'])
        self.assertNotIn('entity_id', one[0])
        self.assertEqual(first['summary']['totals']['people'], 1)
        self.assertEqual(calls, [('c1', universe['start']), ('c2', universe['start'])])
        self.assert_integrity(first)

    def test_profile_failure_does_not_hide_financing_relations(self):
        universe, institutions = fixture()

        def unavailable(cid, cutoff):
            raise OSError('source not available')

        graph = KnowledgeGraph(universe, institutions, unavailable).graph('company', 'c1')
        self.assertIn('round:r1', {n['id'] for n in graph['nodes']})
        self.assertTrue(any('人员资料暂不可用' in note for note in graph['notes']))
        self.assert_integrity(graph)


if __name__ == '__main__':
    unittest.main()
