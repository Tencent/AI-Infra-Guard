import { existsSync } from 'node:fs';
import { DatabaseSync } from 'node:sqlite';
import { join } from 'node:path';
import { findRepoRoot } from './catalog.js';
import { EngineError } from './types.js';

const mask = '********';
const modelIdPattern = /^[a-zA-Z0-9_-]{1,80}$/;

export function dbPath(root = findRepoRoot()): string {
  return process.env.DB_PATH || join(root, 'db', 'tasks.db');
}

function open(path: string, readOnly: boolean): DatabaseSync | null {
  if (!existsSync(path)) return null;
  return new DatabaseSync(path, { readOnly });
}

function usernameOf(header: string | undefined): string {
  const name = (header || '').trim();
  if (!name || name.includes('..') || /[/\\]/.test(name)) return 'public_user';
  return name;
}

function jsonMap(value: unknown): Record<string, unknown> | undefined {
  if (!value) return undefined;
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value) as unknown;
      return parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed as Record<string, unknown> : undefined;
    } catch {
      return undefined;
    }
  }
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : undefined;
}

function maskedMap(value: unknown): Record<string, string> | undefined {
  const map = jsonMap(value);
  if (!map) return undefined;
  return Object.fromEntries(Object.keys(map).map(key => [key, mask]));
}

function modelView(row: Record<string, unknown>) {
  return {
    model_id: String(row.model_id || ''),
    model: {
      model: String(row.model_name || ''),
      token: row.token ? mask : '',
      base_url: String(row.base_url || ''),
      note: String(row.note || ''),
      limit: Number(row.limit) || 0,
      extra_headers: maskedMap(row.extra_headers),
      extra_body: maskedMap(row.extra_body),
    },
  };
}

export function lookupModel(id: string, path = dbPath()): { name: string; baseUrl: string; token: string } | null {
  if (!/^[a-zA-Z0-9_-]{1,80}$/.test(id)) return null;
  const db = open(path, true);
  if (!db) return null;
  try {
    const row = db.prepare('SELECT model_name, token, base_url FROM models WHERE model_id = ?').get(id);
    const token = String(row?.token || '');
    const baseUrl = String(row?.base_url || '');
    if (!row || !token || !baseUrl) return null;
    return { name: String(row.model_name || id), baseUrl, token };
  } finally {
    db.close();
  }
}

export function listModels(userHeader?: string, path = dbPath()): unknown[] {
  const db = open(path, true);
  if (!db) return [];
  try {
    return db.prepare('SELECT * FROM models WHERE username = ? ORDER BY created_at DESC').all(usernameOf(userHeader)).map(modelView);
  } finally {
    db.close();
  }
}

export function readModel(id: string, userHeader?: string, path = dbPath()) {
  const db = open(path, true);
  if (!db) return null;
  try {
    const row = db.prepare('SELECT * FROM models WHERE model_id = ? AND username = ?').get(id, usernameOf(userHeader));
    return row ? modelView(row) : null;
  } finally {
    db.close();
  }
}

function columnOf(db: DatabaseSync, id: string, user: string, column: 'token' | 'extra_headers' | 'extra_body'): unknown {
  return db.prepare(`SELECT ${column} FROM models WHERE model_id = ? AND username = ?`).get(id, user)?.[column];
}

function keepMasked(next: unknown, previous: unknown): string {
  const map = jsonMap(next) || {};
  const old = jsonMap(previous) || {};
  const merged: Record<string, unknown> = {};
  Object.entries(map).forEach(([key, value]) => {
    merged[key] = value === mask ? old[key] ?? '' : value;
  });
  return JSON.stringify(merged);
}

export function saveModel(id: string, model: Record<string, unknown>, userHeader?: string, path = dbPath(), updating = false) {
  if (!modelIdPattern.test(id)) throw new EngineError('模型编号不正确');
  const name = typeof model.model === 'string' ? model.model.trim() : '';
  const baseUrl = typeof model.base_url === 'string' ? model.base_url.trim() : '';
  const token = typeof model.token === 'string' ? model.token : '';
  if (!name || !baseUrl) throw new EngineError('模型名称和地址不能为空');
  const user = usernameOf(userHeader);
  const db = open(path, false);
  if (!db) throw new EngineError('数据库不存在');
  try {
    const now = Date.now();
    const previousToken = updating ? columnOf(db, id, user, 'token') : '';
    const nextToken = !token || token === mask ? String(previousToken || '') : token;
    if (!nextToken) throw new EngineError('模型令牌不能为空');
    const headers = model.extra_headers === undefined
      ? String(updating ? columnOf(db, id, user, 'extra_headers') || '{}' : '{}')
      : keepMasked(model.extra_headers, updating ? columnOf(db, id, user, 'extra_headers') : undefined);
    const body = model.extra_body === undefined
      ? String(updating ? columnOf(db, id, user, 'extra_body') || '{}' : '{}')
      : keepMasked(model.extra_body, updating ? columnOf(db, id, user, 'extra_body') : undefined);
    const note = typeof model.note === 'string' ? model.note : '';
    const limit = Number(model.limit) || 0;
    if (updating) {
      const result = db.prepare(`UPDATE models SET model_name = ?, token = ?, base_url = ?, note = ?, "limit" = ?, extra_headers = ?, extra_body = ?, updated_at = ? WHERE model_id = ? AND username = ?`)
        .run(name, nextToken, baseUrl, note, limit, headers, body, now, id, user);
      if (!result.changes) throw new EngineError('模型不存在');
      return;
    }
    db.prepare(`INSERT INTO models (model_id, username, model_name, token, base_url, note, "limit", created_at, updated_at, extra_headers, extra_body) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
      .run(id, user, name, nextToken, baseUrl, note, limit, now, now, headers, body);
  } finally {
    db.close();
  }
}

export function deleteModels(ids: string[], userHeader?: string, path = dbPath()) {
  const clean = ids.filter(id => modelIdPattern.test(id));
  if (clean.length === 0) throw new EngineError('模型编号不正确');
  const db = open(path, false);
  if (!db) return;
  try {
    const marks = clean.map(() => '?').join(', ');
    db.prepare(`DELETE FROM models WHERE username = ? AND model_id IN (${marks})`).run(usernameOf(userHeader), ...clean);
  } finally {
    db.close();
  }
}

export function listTasks(userHeader?: string, taskType = '', path = dbPath()) {
  const db = open(path, true);
  if (!db) return [];
  try {
    const user = usernameOf(userHeader);
    const rows = taskType
      ? db.prepare('SELECT id, title, task_type, status, created_at FROM sessions WHERE username = ? AND task_type = ? ORDER BY created_at DESC').all(user, taskType)
      : db.prepare('SELECT id, title, task_type, status, created_at FROM sessions WHERE username = ? ORDER BY created_at DESC').all(user);
    return rows.map(row => ({
      sessionId: String(row.id || ''),
      title: String(row.title || ''),
      taskType: String(row.task_type || ''),
      status: String(row.status || ''),
      createdAt: Number(row.created_at) || 0,
    }));
  } finally {
    db.close();
  }
}
