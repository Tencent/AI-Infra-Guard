import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse } from 'yaml';
import { EngineError, type InputField, type OutputField, type PluginManifest, type PresetManifest } from './types.js';

const fieldTypes = new Set(['text', 'textarea', 'model', 'files', 'headers', 'agent', 'multi']);
const outputTypes = new Set(['status', 'findings', 'json']);

export function findRepoRoot(start = process.cwd()): string {
  const seeds = [start, dirname(fileURLToPath(import.meta.url))];
  for (const seed of seeds) {
    let dir = seed;
    for (let i = 0; i < 6; i += 1) {
      if (existsSync(join(dir, 'data', 'catalog', 'plugins'))) return dir;
      const parent = dirname(dir);
      if (parent === dir) break;
      dir = parent;
    }
  }
  throw new EngineError('找不到 data/catalog');
}

function asField(raw: unknown): InputField | null {
  if (!raw || typeof raw !== 'object') return null;
  const item = raw as Record<string, unknown>;
  if (typeof item.id !== 'string' || !fieldTypes.has(String(item.type))) return null;
  const source = item.source === 'evals' || item.source === 'mutations' ? item.source : undefined;
  const rawAny = typeof item.any_of === 'string' ? item.any_of : item.anyOf;
  const anyOf = typeof rawAny === 'string' && rawAny ? rawAny : undefined;
  return { id: item.id, type: item.type as InputField['type'], required: !!item.required, source, anyOf };
}

function asOutput(raw: unknown): OutputField | null {
  if (!raw || typeof raw !== 'object') return null;
  const item = raw as Record<string, unknown>;
  if (typeof item.id !== 'string' || !outputTypes.has(String(item.type))) return null;
  return { id: item.id, type: item.type as OutputField['type'] };
}

function readYamlDir(dir: string): unknown[] {
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter(name => name.endsWith('.yaml') || name.endsWith('.yml'))
    .sort()
    .map(name => parse(readFileSync(join(dir, name), 'utf8')));
}

export function loadCatalog(root = findRepoRoot()): { plugins: PluginManifest[]; presets: PresetManifest[] } {
  const plugins = readYamlDir(join(root, 'data', 'catalog', 'plugins')).flatMap((raw): PluginManifest[] => {
    if (!raw || typeof raw !== 'object') return [];
    const item = raw as Record<string, unknown>;
    if (item.enabled === false || typeof item.id !== 'string' || typeof item.task_type !== 'string') return [];
    const inputs = (Array.isArray(item.inputs) ? item.inputs : []).map(asField).filter((field): field is InputField => !!field);
    const outputs = (Array.isArray(item.outputs) ? item.outputs : []).map(asOutput).filter((field): field is OutputField => !!field);
    if (inputs.length === 0) return [];
    return [{
      id: item.id,
      taskType: item.task_type,
      name: typeof item.name === 'string' ? item.name : item.id,
      inputs,
      outputs,
    }];
  });
  const presets = readYamlDir(join(root, 'data', 'catalog', 'presets')).flatMap((raw): PresetManifest[] => {
    if (!raw || typeof raw !== 'object') return [];
    const item = raw as Record<string, unknown>;
    if (typeof item.id !== 'string' || !Array.isArray(item.plugins)) return [];
    const ids = item.plugins.filter((id): id is string => typeof id === 'string');
    if (ids.length === 0) return [];
    const inputs = (Array.isArray(item.inputs) ? item.inputs : []).map(asField).filter((field): field is InputField => !!field);
    const require = item.require && typeof item.require === 'object' ? item.require as Record<string, boolean> : undefined;
    return [{
      id: item.id,
      name: typeof item.name === 'string' ? item.name : item.id,
      plugins: ids,
      inputs,
      require,
      ui: !!item.ui,
    }];
  });
  if (plugins.length === 0) throw new EngineError('目录里没有可用插件');
  return { plugins, presets };
}

export function listPlugins(root?: string): PluginManifest[] {
  return loadCatalog(root).plugins;
}

export function listPresets(root?: string, uiOnly = false): PresetManifest[] {
  const presets = loadCatalog(root).presets;
  return uiOnly ? presets.filter(item => item.ui) : presets;
}

function textOf(item: Record<string, unknown>, key: string, fallback = ''): string {
  return typeof item[key] === 'string' && item[key] ? item[key] as string : fallback;
}

function byOrder(left: { order?: number; id?: string }, right: { order?: number; id?: string }): number {
  const order = (left.order || 0) - (right.order || 0);
  if (order !== 0) return order;
  return String(left.id).localeCompare(String(right.id));
}

export function catalogPayload(root = findRepoRoot()) {
  const plugins = readYamlDir(join(root, 'data', 'catalog', 'plugins')).flatMap(raw => {
    if (!raw || typeof raw !== 'object') return [];
    const item = raw as Record<string, unknown>;
    const kind = textOf(item, 'kind', 'builtin');
    if (item.enabled === false || kind !== 'builtin' || typeof item.id !== 'string' || typeof item.task_type !== 'string') return [];
    const inputs = (Array.isArray(item.inputs) ? item.inputs : []).map(asField).filter((field): field is InputField => !!field);
    const outputs = (Array.isArray(item.outputs) ? item.outputs : []).map(asOutput).filter((field): field is OutputField => !!field);
    if (inputs.length === 0) return [];
    return [{
      id: item.id,
      task_type: item.task_type,
      name: textOf(item, 'name', item.id),
      name_en: textOf(item, 'name_en'),
      description: textOf(item, 'description'),
      description_en: textOf(item, 'description_en'),
      inputs,
      outputs,
      order: Number(item.order) || 0,
    }];
  }).sort(byOrder);
  const known = new Set(plugins.map(item => item.id));
  const presets = readYamlDir(join(root, 'data', 'catalog', 'presets')).flatMap(raw => {
    if (!raw || typeof raw !== 'object') return [];
    const item = raw as Record<string, unknown>;
    if (typeof item.id !== 'string' || !Array.isArray(item.plugins)) return [];
    const ids = item.plugins.filter((id): id is string => typeof id === 'string' && known.has(id));
    if (ids.length === 0) return [];
    const inputs = (Array.isArray(item.inputs) ? item.inputs : []).map(asField).filter((field): field is InputField => !!field);
    const require = item.require && typeof item.require === 'object' ? item.require as Record<string, boolean> : undefined;
    return [{
      id: item.id,
      name: textOf(item, 'name', item.id),
      name_en: textOf(item, 'name_en'),
      description: textOf(item, 'description'),
      description_en: textOf(item, 'description_en'),
      plugins: ids,
      inputs,
      require,
      ui: !!item.ui,
      order: Number(item.order) || 0,
    }];
  }).sort(byOrder);
  return { plugins, presets };
}
