import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from save_store import SQLiteSaveStore, DurableSaveStore, SaveConflict, StorageUnavailable


class SaveStoreTests(unittest.TestCase):
    def test_persistence_and_simultaneous_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'saves.sqlite3'
            store = SQLiteSaveStore(path)
            store.initialize()
            store.create('account', {'revision': 1, 'cash': 100})
            store = SQLiteSaveStore(path)
            self.assertEqual(store.get('account')['cash'], 100)
            gate = threading.Barrier(2)
            def update(cash):
                gate.wait()
                try:
                    store.update('account', 1, {'revision': 2, 'cash': cash})
                    return 'saved'
                except SaveConflict:
                    return 'conflict'
            with ThreadPoolExecutor(2) as pool:
                results = list(pool.map(update, [80, 90]))
            self.assertCountEqual(results, ['saved', 'conflict'])
            self.assertEqual(store.get('account')['revision'], 2)

    def test_remote_protocol_and_failure_do_not_fall_back(self):
        calls = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                calls.append(body)
                result = {'ok':True, 'state':{'revision':2}}
                if body['operation'] == 'update':
                    result = {'ok':False, 'conflict':True, 'state':{'revision':3}}
                raw = json.dumps(result).encode()
                self.send_response(200); self.end_headers(); self.wfile.write(raw)
        server = ThreadingHTTPServer(('127.0.0.1',0), Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        store = DurableSaveStore(f'http://127.0.0.1:{server.server_port}/')
        try:
            self.assertEqual(store.get('account')['revision'],2)
            with self.assertRaises(SaveConflict) as conflict:
                store.update('account',2,{'revision':3})
            self.assertEqual(conflict.exception.current['revision'],3)
            self.assertEqual(calls[-1]['expected_revision'],2)
        finally:
            server.shutdown();server.server_close();thread.join()
        with self.assertRaises(StorageUnavailable):
            store.get('account')


if __name__ == '__main__': unittest.main()
