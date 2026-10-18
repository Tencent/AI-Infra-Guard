import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { parse } from 'yaml';
import { findRepoRoot } from './catalog.js';
import type { Finding } from './types.js';

export interface Probe {
  path: string;
  status: number;
  header: string;
  body: string;
}

interface HttpRule {
  path: string;
  matchers: string[];
  extractor?: { part?: string; group?: number; regex?: string };
}

interface Fingerprint {
  name: string;
  http: HttpRule[];
  version: HttpRule[];
}

interface Advisory {
  name: string;
  cve: string;
  summary: string;
  rule: string;
}

let fingerprintCache: Fingerprint[] | null = null;
let advisoryCache: Advisory[] | null = null;

function files(dir: string): string[] {
  try {
    return readdirSync(dir, { recursive: true }).flatMap(entry => {
      const name = String(entry);
      return name.endsWith('.yaml') || name.endsWith('.yml') ? [join(dir, name)] : [];
    });
  } catch {
    return [];
  }
}

function asRules(value: unknown): HttpRule[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap(item => {
    if (!item || typeof item !== 'object') return [];
    const rule = item as Record<string, unknown>;
    const extractor = rule.extractor && typeof rule.extractor === 'object' ? rule.extractor as Record<string, unknown> : undefined;
    return [{
      path: typeof rule.path === 'string' ? rule.path : '/',
      matchers: Array.isArray(rule.matchers) ? rule.matchers.filter((entry): entry is string => typeof entry === 'string') : [],
      extractor: extractor ? {
        part: typeof extractor.part === 'string' ? extractor.part : undefined,
        group: Number(extractor.group) || 0,
        regex: typeof extractor.regex === 'string' ? extractor.regex : undefined,
      } : undefined,
    }];
  });
}

function fingerprints(root: string): Fingerprint[] {
  if (fingerprintCache) return fingerprintCache;
  fingerprintCache = files(join(root, 'data', 'fingerprints')).flatMap(file => {
    try {
      const raw = parse(readFileSync(file, 'utf8')) as { info?: { name?: string }; http?: unknown; version?: unknown };
      const name = raw?.info?.name;
      if (!name) return [];
      return [{ name, http: asRules(raw.http), version: asRules(raw.version) }];
    } catch {
      return [];
    }
  });
  return fingerprintCache;
}

function advisories(root: string): Advisory[] {
  if (advisoryCache) return advisoryCache;
  advisoryCache = files(join(root, 'data', 'vuln')).flatMap(file => {
    try {
      const raw = parse(readFileSync(file, 'utf8')) as { info?: { name?: string; cve?: string; summary?: string }; rule?: string };
      if (!raw?.info?.name || !raw.info.cve || !raw.rule) return [];
      return [{ name: raw.info.name, cve: raw.info.cve, summary: raw.info.summary || raw.info.cve, rule: raw.rule }];
    } catch {
      return [];
    }
  });
  return advisoryCache;
}

function splitTop(input: string, op: '||' | '&&'): string[] {
  const parts: string[] = [];
  let quote = '';
  let start = 0;
  for (let index = 0; index < input.length; index += 1) {
    const char = input[index];
    if (quote) {
      if (char === '\\') { index += 1; continue; }
      if (char === quote) quote = '';
      continue;
    }
    if (char === '"' || char === '\'') { quote = char; continue; }
    if (input.startsWith(op, index)) {
      parts.push(input.slice(start, index));
      start = index + op.length;
      index += op.length - 1;
    }
  }
  parts.push(input.slice(start));
  return parts.map(part => part.trim()).filter(Boolean);
}

function readQuoted(input: string): string | null {
  const match = input.match(/=\s*(~|=)?\s*(?:"((?:\\.|[^"])*)"|'((?:\\.|[^'])*)')/);
  if (!match) return null;
  return (match[2] ?? match[3] ?? '').replace(/\\"/g, '"').replace(/\\'/g, '\'');
}

function versionParts(value: string): Array<number | string> {
  return value.split(/[^0-9A-Za-z]+/).filter(Boolean).map(part => /^\d+$/.test(part) ? Number(part) : part.toLowerCase());
}

export function compareVersion(left: string, right: string): number {
  const a = versionParts(left);
  const b = versionParts(right);
  const length = Math.max(a.length, b.length);
  for (let index = 0; index < length; index += 1) {
    const av = a[index] ?? 0;
    const bv = b[index] ?? 0;
    if (typeof av === 'number' && typeof bv === 'number') {
      if (av !== bv) return av - bv;
    } else {
      const as = String(av);
      const bs = String(bv);
      if (as !== bs) return as < bs ? -1 : 1;
    }
  }
  return 0;
}

function samePath(rulePath: string, requestPath: string): boolean {
  const left = rulePath.startsWith('/') ? rulePath : `/${rulePath}`;
  const right = requestPath || '/';
  return left === right;
}

export function matchExpression(expression: string, values: Record<string, string>): boolean {
  const orParts = splitTop(expression, '||');
  if (orParts.length > 1) return orParts.some(part => matchExpression(part, values));
  const andParts = splitTop(expression, '&&');
  if (andParts.length > 1) return andParts.every(part => matchExpression(part, values));
  const atom = expression.trim();
  if (atom.startsWith('(') && atom.endsWith(')')) return matchExpression(atom.slice(1, -1), values);
  const key = atom.split(/\s|=/)[0]?.trim() || '';
  const raw = values[key] ?? '';
  const expected = readQuoted(atom);
  if (expected === null) return false;
  if (key === 'version') {
    if (atom.includes('>=')) return compareVersion(raw, expected) >= 0;
    if (atom.includes('<=')) return compareVersion(raw, expected) <= 0;
    if (atom.includes('>')) return compareVersion(raw, expected) > 0;
    if (atom.includes('<')) return compareVersion(raw, expected) < 0;
    if (atom.includes('==')) return compareVersion(raw, expected) === 0;
    return false;
  }
  const haystack = raw.toLowerCase();
  const needle = expected.toLowerCase();
  if (atom.includes('!=')) return !haystack.includes(needle);
  if (atom.includes('==')) return haystack === needle;
  if (atom.includes('~=')) {
    try { return new RegExp(expected, 'i').test(raw); } catch { return false; }
  }
  return haystack.includes(needle);
}

function extractVersion(rule: HttpRule, probe: Probe): string {
  if (!rule.extractor?.regex || !samePath(rule.path, probe.path)) return '';
  const source = rule.extractor.part === 'header' ? probe.header : probe.body;
  try {
    const found = new RegExp(rule.extractor.regex, 'i').exec(source);
    return found?.[rule.extractor.group || 1] || found?.[0] || '';
  } catch {
    return '';
  }
}

export function matchProbe(probe: Probe, root = findRepoRoot()): Finding[] {
  const values = { body: probe.body, header: probe.header, status: String(probe.status) };
  const found: Finding[] = [];
  fingerprints(root).forEach(fingerprint => {
    const matched = fingerprint.http.some(rule => samePath(rule.path, probe.path) && rule.matchers.some(matcher => matchExpression(matcher, values)));
    if (!matched) return;
    const version = fingerprint.version.map(rule => extractVersion(rule, probe)).find(Boolean) || '';
    found.push({
      title: fingerprint.name,
      severity: 'info',
      verdict: 'insufficient',
      strategy: 'fingerprint',
      prompt: probe.path,
      response: version,
      reason: version ? `识别到 ${fingerprint.name}，版本 ${version}` : `识别到 ${fingerprint.name}，未提取到版本`,
    });
    if (!version) return;
    advisories(root).filter(item => item.name === fingerprint.name && matchExpression(item.rule, { version })).forEach(item => {
      found.push({
        title: item.cve,
        severity: 'high',
        verdict: 'fail',
        strategy: 'advisory',
        prompt: `${fingerprint.name} ${version}`,
        response: item.summary,
        reason: `${item.cve}：${item.summary}`,
      });
    });
  });
  return found;
}
