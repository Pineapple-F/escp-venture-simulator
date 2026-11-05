"""SGL serving contracts: true dot products, identity routing, exclusions and failures."""
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from recommendations import InvestorRecommender, RecommendationUnavailable


class RecommendationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.assets = Path(self.temp.name)
        ids = [f'co_{i:02}' for i in range(18)]
        self.universe = dict(start='2026-03-31', companies=[dict(id=cid, name=cid) for cid in ids], rounds=[])
        self.subjects = {
            'ik_trained': dict(id='ik_trained', name='已训练投资方', companies={'co_00', 'co_01'}),
            'ik_unseen': dict(id='ik_unseen', name='新投资方', companies={'co_17'}),
            **{f'ik_other_{i}': dict(id=f'ik_other_{i}', name=f'投资方{i}', companies={f'co_{j:02}' for j in range(i, 18)}) for i in range(3)},
        }
        np.savez_compressed(self.assets / 'embeddings.npz',
                            user_embeddings=np.array([[1, 2], [0, 0]], dtype=np.float32),
                            item_embeddings=np.array([[i, i] for i in range(18)], dtype=np.float32),
                            seen_indptr=np.array([0, 2, 2]), seen_indices=np.array([0, 17]))
        self.manifest = dict(schema_version=1, model='SGL', model_version='test_sgl',
                             user_ids=['ik_trained', 'ik_other_0'], item_ids=ids,
                             embeddings_sha256=sha256((self.assets / 'embeddings.npz').read_bytes()).hexdigest())
        self.save_manifest()

    def save_manifest(self):
        (self.assets / 'manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def service(self):
        return InvestorRecommender(self.assets, self.universe, self.subjects)

    def test_trained_ranking_is_dot_product_excludes_both_histories(self):
        result = self.service().recommend('ik_trained')
        self.assertEqual(result['method'], 'sgl')
        self.assertEqual(result['count'], 10)
        self.assertEqual([r['id'] for r in result['items']], [f'co_{i:02}' for i in range(16, 6, -1)])
        self.assertEqual(result['items'][0]['score'], 48)
        self.assertTrue(all(r['id'] not in {'co_00', 'co_01', 'co_17'} for r in result['items']))

    def test_unseen_uses_distinct_investor_popularity(self):
        svc = self.service()
        result = svc.recommend('ik_unseen')
        self.assertEqual(result['method'], 'mostpop')
        self.assertEqual(result['count'], 10)
        expected = sorted((cid for cid in svc.popularity if cid != 'co_17'), key=lambda cid: (-svc.popularity[cid], cid))[:10]
        self.assertEqual([r['id'] for r in result['items']], expected)

    def test_actual_subject_required_and_training_flag_matches(self):
        svc = self.service()
        with self.assertRaises(KeyError):
            svc.recommend('visitor')
        self.assertTrue(svc.investors('已训练')['items'][0]['trained'])
        self.assertFalse(svc.investors('新投资')['items'][0]['trained'])
        with self.assertRaises(ValueError):
            svc.investors(page=0)

    def test_known_zero_scores_do_not_switch_to_popularity(self):
        # Known subject with no remaining candidates: honest empty result, no re-investments.
        result = self.service().recommend('ik_other_0')
        self.assertEqual(result['method'], 'sgl')
        self.assertEqual(result['count'], 0)

    def test_unavailable_company_cannot_be_recommended(self):
        self.universe['companies'] = [c for c in self.universe['companies'] if c['id'] != 'co_16']
        for iid in ['ik_trained', 'ik_unseen']:
            self.assertNotIn('co_16', [r['id'] for r in self.service().recommend(iid)['items']])

    def test_corrupt_or_misaligned_model_is_error_not_cold_start(self):
        self.manifest['user_ids'].append('ik_extra')
        self.save_manifest()
        with self.assertRaises(RecommendationUnavailable):
            self.service().recommend('ik_trained')
        self.manifest['embeddings_sha256'] = 'invalid'
        self.save_manifest()
        with self.assertRaises(RecommendationUnavailable):
            self.service().recommend('ik_unseen')

    def test_concurrent_read_only_and_deterministic_ties(self):
        from concurrent.futures import ThreadPoolExecutor
        svc = self.service()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(svc.recommend, ['ik_trained', 'ik_unseen'] * 20))
        self.assertTrue(all(r['items'] == results[i % 2]['items'] for i, r in enumerate(results)))
        self.assertEqual(self.subjects['ik_trained']['companies'], {'co_00', 'co_01'})

    def test_untrained_subject_has_real_graph_including_outside_catalogue(self):
        event = dict(id='ev_actual', company='co_outside', name='范围外的历史被投企业',
                     date='2024-01-02', available='2024-01-05', stage='A轮', industry='软件', region='北京')
        self.subjects['ik_unseen']['companies'].add('co_outside')
        self.subjects['ik_unseen']['events'] = {('ev_actual', 'co_outside'): event}
        graph = self.service().graph('ik_unseen')
        self.assertEqual(graph['root_id'], 'institution:ik_unseen')
        self.assertFalse(graph['investor']['trained'])
        self.assertEqual({e['type'] for e in graph['edges']}, {'participated', 'financing_of'})
        self.assertEqual(len(graph['edges']), 2)
        company = next(n for n in graph['nodes'] if n['type'] == 'company')
        self.assertEqual(company['label'], event['name'])
        self.assertFalse(company['available_in_workspace'])
        self.assertTrue(all(e['evidence'][0]['record_id'] == 'ev_actual' for e in graph['edges']))
        self.assertNotIn('co_16', [n.get('entity_id') for n in graph['nodes']])

    def test_search_accepts_multiple_keywords_and_id_disambiguation(self):
        svc = self.service()
        self.assertEqual(svc.investors('已训练 ik_trained')['items'][0]['id'], 'ik_trained')
        self.assertEqual(svc.investors('已训练 不存在')['total'], 0)


if __name__ == '__main__':
    unittest.main()
