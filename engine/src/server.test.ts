import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';
import { DatabaseSync } from 'node:sqlite';
import { findRepoRoot } from './catalog.js';
import { startServer } from './server.js';
import { runsDir } from './store.js';

const root = findRepoRoot();

async function withServer(run: (base: string) => Promise<void>, dbPath?: string) {
  const started = await startServer(0, '127.0.0.1', { root, dbPath });
  try {
    await run(`http://127.0.0.1:${started.port}`);
  } finally {
    await new Promise<void>((resolve, reject) => started.server.close(error => error ? reject(error) : resolve()));
  }
}

test('the typescript server returns the desk catalog', async () => {
  await withServer(async base => {
    const body = await (await fetch(`${base}/api/v1/app/catalog`)).json() as { status: number; data: { presets: Array<{ id: string; description: string; ui: boolean }>; plugins: Array<{ id: string; inputs: Array<{ id: string; anyOf?: string }> }> } };
    assert.equal(body.status, 0);
    const gov = body.data.presets.find(item => item.id === 'gov');
    assert.equal(gov?.ui, true);
    assert.match(gov?.description || '', /用途/);
    const mcp = body.data.plugins.find(item => item.id === 'mcp-scan');
    assert.equal(mcp?.inputs.find(item => item.id === 'code')?.anyOf, 'material');
  });
});

test('evaluation lists omit prompt text and a scan streams events', async () => {
  await withServer(async base => {
    const listed = await (await fetch(`${base}/api/v1/knowledge/evaluations?page=1&size=5`)).json() as { status: number; data: { items: Array<Record<string, unknown>> } };
    assert.equal(listed.status, 0);
    assert.ok(listed.data.items.length > 0);
    assert.equal(listed.data.items.some(item => 'data' in item), false);
    const response = await fetch(`${base}/api/v1/app/engine/scans?stream=1`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plugins: ['infra-scan'], inputs: { target: '10.6.0.0/24' } }),
    });
    const text = await response.text();
    assert.match(text, /登记目标/);
    assert.match(text, /"type":"report"/);
    assert.equal(text.includes('token'), false);
    const id = text.match(/"id":"([0-9a-f-]{36})"/i)?.[1];
    if (id) rmSync(join(runsDir(root), `${id}.json`), { force: true });
  });
});

test('model responses mask stored secrets', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'aig-db-'));
  const path = join(dir, 'tasks.db');
  const db = new DatabaseSync(path);
  db.prepare(`CREATE TABLE models (
    model_id TEXT PRIMARY KEY, username TEXT, model_name TEXT, token TEXT, base_url TEXT, note TEXT,
    "limit" INTEGER, created_at INTEGER, updated_at INTEGER, extra_headers TEXT, extra_body TEXT
  )`).run();
  db.prepare('INSERT INTO models (model_id, username, model_name, token, base_url, note, "limit", created_at, updated_at, extra_headers, extra_body) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)')
    .run('local-1', 'public_user', 'desk-model', 'secret-token', 'http://127.0.0.1:9', '', 0, 1, 1, '{"Authorization":"secret-header"}', '{}');
  db.close();
  try {
    await withServer(async base => {
      const body = await (await fetch(`${base}/api/v1/app/models`)).json() as { status: number; data: Array<{ model: { token: string; extra_headers?: Record<string, string> } }> };
      assert.equal(body.status, 0);
      assert.equal(body.data[0]?.model.token, '********');
      assert.equal(body.data[0]?.model.extra_headers?.Authorization, '********');
      assert.equal(JSON.stringify(body).includes('secret-token'), false);
      assert.equal(JSON.stringify(body).includes('secret-header'), false);
    }, path);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
