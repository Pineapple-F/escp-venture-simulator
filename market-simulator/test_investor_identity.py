"""HTTP identity gate and persistent investor binding, with isolated account storage."""
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
import unittest
import urllib.error
import urllib.request


class InvestorIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='escp-identity-test-')
        names = ('SAVE_DB_PATH', 'MODEL_WARM_ON_START', 'SAVE_STORE_URL', 'COOKIE_SECURE')
        cls.environment = {name: os.environ.get(name) for name in names}
        os.environ.update(SAVE_DB_PATH=str(Path(cls.temp.name) / 'saves.sqlite3'),
                          MODEL_WARM_ON_START='0', COOKIE_SECURE='0')
        os.environ.pop('SAVE_STORE_URL', None)
        import server
        cls.server = server
        cls.original_db, cls.original_remote = server.DB, server.REMOTE_SAVES
        server.DB, server.REMOTE_SAVES = Path(cls.temp.name) / 'saves.sqlite3', None
        server.SQLiteSaveStore(server.DB).initialize()
        cls.known = next(r for r in server.RECOMMENDER.investor_rows if r['trained'])
        cls.unseen = next(r for r in server.RECOMMENDER.investor_rows if not r['trained'])

        class Quiet(server.Handler):
            def log_message(self, *args):
                pass

        cls.httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = 'http://127.0.0.1:' + str(cls.httpd.server_address[1])

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join()
        cls.server.DB, cls.server.REMOTE_SAVES = cls.original_db, cls.original_remote
        for name, value in cls.environment.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        cls.temp.cleanup()

    def setUp(self):
        self.client = urllib.request.build_opener(urllib.request.ProxyHandler({}),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, path, body=None, cookie=None):
        headers = {'Origin': self.base, 'Content-Type': 'application/json'}
        if cookie:
            headers['Cookie'] = 'market_save=' + cookie
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data, headers)
        try:
            response = self.client.open(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def create(self, subject=None):
        subject = subject or self.known
        status, data = self.request('/api/new', {'name': 'Identity test', 'investor_id': subject['id']})
        self.assertEqual(status, 200, data)
        return data['game']

    def test_catalog_is_searchable_before_entry_but_identity_is_required(self):
        status, data = self.request('/api/recommendation-investors?q=' + self.known['id'])
        self.assertEqual(status, 200)
        self.assertEqual([r['id'] for r in data['items']], [self.known['id']])
        for body in ({}, {'investor_id': 'visitor'}, {'investor_id': self.known['name']}, {'investor_id': []}):
            status, _ = self.request('/api/new', body)
            self.assertEqual(status, 400, body)
        self.assertIsNone(self.request('/api/game')[1]['game'])
        self.assertEqual(self.request('/api/recommendations')[0], 401)
        self.assertEqual(self.request('/api/investor-graph')[0], 401)

    def test_preview_is_public_evidenced_and_does_not_select_identity(self):
        for subject in (self.known, self.unseen):
            status, data = self.request('/api/investor-preview?investor_id=' + subject['id'])
            self.assertEqual(status, 200, data)
            self.assertEqual(data['investor']['id'], subject['id'])
            self.assertEqual(data['profile']['name'], subject['name'])
            self.assertEqual(data['profile']['company_count'], subject['company_count'])
            self.assertEqual(data['graph']['root_id'], 'institution:' + subject['id'])
            events = self.server.RECOMMENDER.subjects[subject['id']]['events']
            self.assertEqual(data['profile']['event_count'], len(events))
            self.assertTrue(all(edge['evidence'] for edge in data['graph']['edges']))
        self.assertIsNone(self.request('/api/game')[1]['game'])
        self.assertEqual(self.request('/api/recommendations')[0], 401)
        self.assertEqual(self.request('/api/investor-preview')[0], 400)
        self.assertEqual(self.request('/api/investor-preview?investor_id=visitor')[0], 404)
        self.create(self.known)
        before = self.request('/api/legacy-export')[1]
        self.assertEqual(self.request('/api/investor-preview?investor_id=' + self.unseen['id'])[0], 200)
        self.assertEqual(self.request('/api/legacy-export')[1], before)
        self.assertEqual(self.request('/api/game')[1]['game']['investor_id'], self.known['id'])

    def test_recommendation_and_graph_use_saved_identity(self):
        game = self.create()
        self.assertEqual(game['investor_id'], self.known['id'])
        self.assertEqual(game['investor']['name'], self.known['name'])
        self.assertEqual(self.request('/api/game')[1]['game']['investor']['id'], self.known['id'])
        before = self.request('/api/legacy-export')[1]
        status, data = self.request('/api/recommendations')
        self.assertEqual(status, 200)
        self.assertEqual(data['investor']['id'], self.known['id'])
        self.assertEqual(data['method'], 'sgl')
        self.assertEqual(data['count'], 10)
        self.assertFalse(set(r['id'] for r in data['items']) & self.server.RECOMMENDER.history[self.known['id']])
        company_id = data['items'][0]['id']
        status, detail = self.request('/api/company?id=' + company_id)
        self.assertEqual(status, 200, detail)
        self.assertEqual(detail['company']['id'], company_id)
        self.assertIn('history', detail['company'])
        status, graph = self.request('/api/investor-graph')
        self.assertEqual(status, 200, graph)
        self.assertEqual(graph['root_id'], 'institution:' + self.known['id'])
        node_ids = {n['id'] for n in graph['nodes']}
        self.assertIn(graph['root_id'], node_ids)
        self.assertTrue(all(e['source'] in node_ids and e['target'] in node_ids for e in graph['edges']))
        self.assertEqual(self.request('/api/recommendations?investor_id=' + self.unseen['id'])[0], 403)
        self.assertEqual(self.request('/api/legacy-export')[1], before)

    def test_switch_is_validated_persisted_and_revision_protected(self):
        game = self.create()
        status, _ = self.request('/api/investor', {'investor_id': 'visitor', 'revision': game['revision']})
        self.assertEqual(status, 400)
        before = self.request('/api/legacy-export')[1]
        status, data = self.request('/api/investor', {'investor_id': self.unseen['id'], 'revision': game['revision']})
        self.assertEqual(status, 200, data)
        self.assertEqual(data['game']['investor_id'], self.unseen['id'])
        self.assertEqual(data['game']['revision'], game['revision'] + 1)
        after = self.request('/api/legacy-export')[1]
        for key in ('cash', 'positions', 'curve', 'log', 'month', 'initial'):
            self.assertEqual(before[key], after[key], key)
        self.assertEqual(self.request('/api/recommendations')[1]['method'], 'mostpop')
        self.assertEqual(self.request('/api/investor-graph')[1]['root_id'], 'institution:' + self.unseen['id'])
        status, _ = self.request('/api/investor', {'investor_id': self.known['id'], 'revision': game['revision']})
        self.assertEqual(status, 409)
        self.assertEqual(self.request('/api/game')[1]['game']['investor_id'], self.unseen['id'])

    def test_existing_unbound_save_can_bind_without_reset(self):
        sid = secrets.token_urlsafe(32)
        state = self.server.new_game(self.server.UNIVERSE, 'Existing account', initial=123456)
        self.server.saves().create(sid, state)
        self.assertEqual(self.request('/api/recommendations', cookie=sid)[0], 403)
        self.assertEqual(self.request('/api/investor-graph', cookie=sid)[0], 403)
        self.assertEqual(self.request('/api/action', {'type': 'advance', 'revision': 0}, cookie=sid)[0], 403)
        status, data = self.request('/api/investor', {'investor_id': self.known['id'], 'revision': 0}, cookie=sid)
        self.assertEqual(status, 200, data)
        self.assertEqual(data['game']['cash'], 123456)
        self.assertEqual(data['game']['investor_id'], self.known['id'])
        self.assertEqual(self.request('/api/recommendations', cookie=sid)[0], 200)

    def test_founder_workspace_still_works_but_cannot_bypass_investor_gate(self):
        status, data = self.request('/api/new', {'workspace': 'founder', 'name': 'Founder test'})
        self.assertEqual(status, 200, data)
        self.assertFalse(data['game'].get('investor_id'))
        self.assertEqual(self.request('/api/recommendations')[0], 403)
        self.assertEqual(self.request('/api/investor-graph')[0], 403)


if __name__ == '__main__':
    unittest.main()
