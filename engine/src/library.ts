import { existsSync, readdirSync, readFileSync, rmSync, writeFileSync, mkdirSync } from 'node:fs';
import { basename, join, relative } from 'node:path';
import { parse } from 'yaml';
import { findRepoRoot } from './catalog.js';
import { EngineError } from './types.js';

const namePattern = /^[a-zA-Z0-9._-]{1,80}$/;

function walk(dir: string, suffix: string): string[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir, { recursive: true }).flatMap(entry => {
    const name = String(entry);
    return name.endsWith(suffix) ? [join(dir, name)] : [];
  });
}

function pageOf<T>(items: T[], page: number, size: number) {
  const start = (page - 1) * size;
  return { total: items.length, page, size, items: items.slice(start, start + size) };
}

function queryNumber(value: string | null, fallback: number): number {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : fallback;
}

let fingerprints: Array<{ info?: { name?: string; desc?: string; author?: string; recommendation?: number } }> | null = null;
let vulnerabilities = new Map<string, Array<{ info?: Record<string, unknown>; references?: string[] }>>();
let evaluations: Array<Record<string, unknown>> | null = null;

export function listFingerprints(root: string, page: number, size: number, query: string) {
  if (!fingerprints) {
    fingerprints = walk(join(root, 'data', 'fingerprints'), '.yaml').flatMap(file => {
      try {
        const parsed = parse(readFileSync(file, 'utf8'));
        return parsed && typeof parsed === 'object' ? [parsed as { info?: { name?: string; desc?: string; author?: string; recommendation?: number } }] : [];
      } catch {
        return [];
      }
    });
  }
  const q = query.toLowerCase();
  const matched = fingerprints.filter(item => {
    if (!q) return true;
    const info = item.info || {};
    return [info.name, info.desc, info.author].some(value => String(value || '').toLowerCase().includes(q));
  }).sort((left, right) => (right.info?.recommendation || 0) - (left.info?.recommendation || 0) || String(left.info?.name).localeCompare(String(right.info?.name)));
  return pageOf(matched, page, size);
}

export function listVulnerabilities(root: string, page: number, size: number, query: string, lang: string) {
  const dir = lang === 'en' ? 'vuln_en' : 'vuln';
  if (!vulnerabilities.has(dir)) {
    vulnerabilities.set(dir, walk(join(root, 'data', dir), '.yaml').flatMap(file => {
      try {
        const parsed = parse(readFileSync(file, 'utf8'));
        return parsed && typeof parsed === 'object' ? [parsed as { info?: Record<string, unknown>; references?: string[] }] : [];
      } catch {
        return [];
      }
    }));
  }
  const q = query.toLowerCase();
  const matched = (vulnerabilities.get(dir) || []).filter(item => {
    if (!q) return true;
    const info = item.info || {};
    const values = [info.cve, info.summary, info.name, info.details, ...(item.references || [])];
    return values.some(value => String(value || '').toLowerCase().includes(q));
  });
  return pageOf(matched, page, size);
}

function loadEvaluations(root: string): Array<Record<string, unknown>> {
  if (evaluations) return evaluations;
  evaluations = walk(join(root, 'data', 'eval'), '.json').flatMap(file => {
    try {
      const parsed = JSON.parse(readFileSync(file, 'utf8')) as Record<string, unknown>;
      if (!parsed || typeof parsed.name !== 'string') return [];
      const { data: _data, ...summary } = parsed;
      return [summary];
    } catch {
      return [];
    }
  }).sort((left, right) => Number(right.recommendation || 0) - Number(left.recommendation || 0));
  return evaluations;
}

export function listEvaluations(root: string, page: number, size: number, query: string) {
  const q = query.toLowerCase();
  const matched = loadEvaluations(root).filter(item => {
    if (!q) return true;
    const tags = Array.isArray(item.tags) ? item.tags.map(tag => String(tag)) : [];
    return [item.name, item.description, item.author, ...tags].some(value => String(value || '').toLowerCase().includes(q));
  });
  return pageOf(matched, page, size);
}

export function readEvaluation(root: string, name: string) {
  if (!namePattern.test(name)) throw new EngineError('评测集名称不正确');
  const file = walk(join(root, 'data', 'eval'), '.json').find(path => basename(path) === `${name}.json`);
  if (!file) throw new EngineError('评测集不存在');
  return JSON.parse(readFileSync(file, 'utf8')) as unknown;
}

export function readJailbreak(root: string) {
  const file = join(root, 'AIG-PromptSecurity', 'utils', 'strategy_map.json');
  if (!existsSync(file)) throw new EngineError('算子列表不存在');
  return JSON.parse(readFileSync(file, 'utf8')) as unknown;
}

function agentRoot(root: string, userHeader?: string): string {
  const name = (userHeader || '').trim();
  const user = namePattern.test(name) ? name : 'public_user';
  return join(root, 'data', 'agents', user);
}

export function listAgentNames(root: string, userHeader?: string): string[] {
  const dir = agentRoot(root, userHeader);
  if (!existsSync(dir)) return [];
  return readdirSync(dir).filter(name => name.endsWith('.yaml') || name.endsWith('.yml')).map(name => name.replace(/\.ya?ml$/, '')).sort();
}

export function readAgent(root: string, name: string, userHeader?: string): string {
  if (!namePattern.test(name)) throw new EngineError('接入配置名称不正确');
  const file = join(agentRoot(root, userHeader), `${name}.yaml`);
  if (!existsSync(file)) throw new EngineError('接入配置不存在');
  return readFileSync(file, 'utf8');
}

export function writeAgent(root: string, name: string, content: string, userHeader?: string) {
  if (!namePattern.test(name)) throw new EngineError('接入配置名称不正确');
  if (!content.trim()) throw new EngineError('接入配置不能为空');
  const dir = agentRoot(root, userHeader);
  mkdirSync(dir, { recursive: true });
  const file = join(dir, `${name}.yaml`);
  if (relative(dir, file).startsWith('..')) throw new EngineError('接入配置名称不正确');
  writeFileSync(file, content);
}

export function removeAgent(root: string, name: string, userHeader?: string) {
  if (!namePattern.test(name)) throw new EngineError('接入配置名称不正确');
  const file = join(agentRoot(root, userHeader), `${name}.yaml`);
  if (existsSync(file)) rmSync(file);
}

export function libraryQuery(url: URL) {
  return {
    page: queryNumber(url.searchParams.get('page'), 1),
    size: queryNumber(url.searchParams.get('size'), 20),
    q: url.searchParams.get('q') || '',
    lang: url.searchParams.get('lang') || 'zh',
  };
}

export function repoRoot(): string {
  return findRepoRoot();
}
