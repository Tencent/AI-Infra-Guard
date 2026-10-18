import type { InputValue } from './types.js';

export interface GeneratedCase {
  title: string;
  prompt: string;
  fromDataset?: boolean;
}

export function text(value: InputValue | undefined): string {
  return typeof value === 'string' ? value.trim() : '';
}

export function list(value: InputValue | undefined): string[] {
  if (Array.isArray(value)) return value.map(item => item.trim()).filter(Boolean);
  const single = text(value);
  return single ? [single] : [];
}

export function headerKeys(value: InputValue | undefined): string[] {
  if (Array.isArray(value)) return [];
  if (!value || typeof value !== 'object' || 'name' in value || 'baseUrl' in value) return [];
  const record = value as Record<string, string>;
  return Object.keys(record).filter(key => key.trim() && String(record[key] ?? '').trim());
}

function clip(value: string): string {
  return [...value].slice(0, 800).join('');
}

function fileLabel(value: string): string {
  if (value.startsWith('http://') || value.startsWith('https://')) {
    try {
      return new URL(value).pathname.split('/').pop() || 'file';
    } catch {
      return 'file';
    }
  }
  return value.split(/[/\\]/).pop() || 'file';
}

export function casesFor(pluginId: string, inputs: Record<string, InputValue>): GeneratedCase[] {
  if (pluginId === 'model-redteam') return [];
  if (pluginId === 'infra-scan') {
    return [{ title: '目标', prompt: clip(text(inputs.target)) }];
  }
  if (pluginId === 'mcp-scan') {
    const endpoint = text(inputs.endpoint);
    const files = list(inputs.code).map(fileLabel);
    const title = endpoint || files[0] || 'MCP';
    const prompt = [endpoint, ...files].filter(Boolean).join('\n');
    return [{ title: clip(title), prompt: clip(prompt) }];
  }
  if (pluginId === 'skill-scan') {
    const files = list(inputs.code).map(fileLabel);
    return [{ title: files[0] || '代码包', prompt: clip(files.join('\n')) }];
  }
  if (pluginId === 'agent-scan') {
    const agent = text(inputs.agent);
    const files = list(inputs.code).map(fileLabel);
    return [{ title: clip(agent || 'Agent'), prompt: clip([agent, ...files].filter(Boolean).join('\n')) }];
  }
  return [{ title: pluginId, prompt: pluginId }];
}
