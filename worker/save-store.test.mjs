import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { SaveStore } from './save-store.mjs';

function open(path) {
  const db = new DatabaseSync(path);
  const sql = { exec(query, ...args) {
    const stmt = db.prepare(query);
    if (/^(SELECT|UPDATE.*RETURNING)/s.test(query)) {
      const rows = stmt.all(...args);
      return { toArray: () => rows };
    }
    stmt.run(...args);
    return { toArray: () => [] };
  }};
  return { db, store: new SaveStore(sql) };
}
const id = 'test_account_01234567890123456789';

test('durable SQL survives reopening and rejects stale concurrent writes', () => {
  const dir = mkdtempSync(join(tmpdir(), 'escp-saves-'));
  const path = join(dir, 'durable.sqlite');
  let context = open(path);
  try {
    const initial = { version: 3, revision: 1, name: '持久化测试', cash: 100 };
    assert.deepEqual(context.store.operate({operation:'create',id,state:initial}), {ok:true});
    // Retrying create must not reset a save.
    assert.deepEqual(context.store.operate({operation:'create',id,state:initial}), {ok:true});
    context.db.close();
    context = open(path);
    assert.deepEqual(context.store.operate({operation:'get',id}).state, initial);
    const state = {...initial, revision:2, cash:90};
    assert.equal(context.store.operate({operation:'update',id,expected_revision:1,state}).ok,true);
    const stale = context.store.operate({operation:'update',id,expected_revision:1,state:{...state,cash:80}});
    assert.equal(stale.conflict,true);
    assert.equal(stale.state.cash,90);
    assert.equal(context.store.operate({operation:'create',id,state:initial}).conflict,true);
  } finally { context.db.close(); rmSync(dir,{recursive:true}); }
});

test('rejects invalid IDs, oversized saves and invalid revisions', () => {
  const {db,store}=open(':memory:');
  try {
    assert.equal(store.operate({operation:'get',id:"' OR 1=1"}).ok,false);
    assert.equal(store.operate({operation:'create',id,state:{revision:1,text:'x'.repeat(1048577)}}).ok,false);
    assert.equal(store.operate({operation:'update',id,expected_revision:1,state:{revision:8}}).ok,false);
    assert.equal(store.operate({operation:'get',id}).state,null);
  } finally {db.close();}
});
