// Runs only through the private container outbound handler / DO RPC.
// No public HTTP route exposes account storage.
export class SaveStore {
  constructor(sql) {
    this.sql = sql;
    sql.exec('CREATE TABLE IF NOT EXISTS account_saves (id TEXT PRIMARY KEY, state TEXT NOT NULL)');
  }

  operate({ operation, id, state, expected_revision } = {}) {
    if (typeof id !== 'string' || !/^[A-Za-z0-9_-]{20,128}$/.test(id)) {
      return { ok: false, error: 'Invalid save ID' };
    }
    const read = () => {
      const rows = this.sql.exec('SELECT state FROM account_saves WHERE id=?', id).toArray();
      return rows.length ? JSON.parse(rows[0].state) : null;
    };
    if (operation === 'get') return { ok: true, state: read() };
    if (!['create', 'update'].includes(operation)) return { ok: false, error: 'Invalid operation' };
    if (!state || typeof state !== 'object' || !Number.isSafeInteger(state.revision)) {
      return { ok: false, error: 'Invalid state' };
    }
    const encoded = JSON.stringify(state);
    if (new TextEncoder().encode(encoded).byteLength > 1024 * 1024) {
      return { ok: false, error: 'Save exceeds 1 MiB' };
    }
    if (operation === 'create') {
      this.sql.exec('INSERT INTO account_saves (id,state) VALUES (?,?) ON CONFLICT(id) DO NOTHING', id, encoded);
      const current = read();
      return JSON.stringify(current) === encoded ? { ok: true } : { ok: false, conflict: true, state: current };
    }
    if (!Number.isSafeInteger(expected_revision) || state.revision !== expected_revision + 1) {
      return { ok: false, error: 'Invalid revision' };
    }
    const updated = this.sql.exec(
      "UPDATE account_saves SET state=? WHERE id=? AND json_extract(state,'$.revision')=? RETURNING id",
      encoded, id, expected_revision,
    ).toArray();
    return updated.length ? { ok: true } : { ok: false, conflict: true, state: read() };
  }
}
