"""Account saves: local SQLite, or the container's durable storage bridge.

Writes use revision compare-and-swap so concurrent requests cannot overwrite
each other. Never fall back to ephemeral SQLite when the remote store fails.
"""
import json
import sqlite3
from contextlib import closing
from urllib.error import HTTPError, URLError
from urllib.request import Request, ProxyHandler, build_opener


class StorageUnavailable(RuntimeError):
    pass


class SaveConflict(Exception):
    def __init__(self, current):
        self.current = current
        super().__init__('Save revision changed')


class SQLiteSaveStore:
    def __init__(self, path):
        self.path = path

    def initialize(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE IF NOT EXISTS saves (id TEXT PRIMARY KEY, state TEXT NOT NULL)')

    def get(self, sid):
        if not sid:
            return None
        with closing(sqlite3.connect(self.path, timeout=10)) as db:
            row = db.execute('SELECT state FROM saves WHERE id=?', (sid,)).fetchone()
        return json.loads(row[0]) if row else None

    def create(self, sid, state):
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            db.execute('INSERT INTO saves VALUES (?, ?)', (sid, json.dumps(state)))

    def update(self, sid, expected_revision, state):
        with closing(sqlite3.connect(self.path, timeout=10)) as db, db:
            db.execute('BEGIN IMMEDIATE')
            result = db.execute(
                "UPDATE saves SET state=? WHERE id=? AND json_extract(state,'$.revision')=?",
                (json.dumps(state), sid, expected_revision))
            if result.rowcount != 1:
                row = db.execute('SELECT state FROM saves WHERE id=?', (sid,)).fetchone()
                raise SaveConflict(json.loads(row[0]) if row else None)


class DurableSaveStore:
    def __init__(self, url):
        self.url = url
        # The virtual host must go directly to Cloudflare's outbound handler.
        self.client = build_opener(ProxyHandler({}))

    def _request(self, operation, sid, **kwargs):
        body = json.dumps(dict(operation=operation, id=sid, **kwargs)).encode()
        request = Request(self.url, body, {'Content-Type': 'application/json'}, method='POST')
        try:
            with self.client.open(request, timeout=15) as response:
                result = json.load(response)
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
            raise StorageUnavailable('Account storage is temporarily unavailable') from error
        if result.get('conflict'):
            raise SaveConflict(result.get('state'))
        if not result.get('ok'):
            raise StorageUnavailable('Account storage rejected the operation')
        return result.get('state')

    def get(self, sid):
        return self._request('get', sid) if sid else None

    def create(self, sid, state):
        self._request('create', sid, state=state)

    def update(self, sid, expected_revision, state):
        self._request('update', sid, expected_revision=expected_revision, state=state)
