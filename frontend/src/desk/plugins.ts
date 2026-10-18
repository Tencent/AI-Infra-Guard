export type FieldType = 'text' | 'textarea' | 'model' | 'files' | 'headers' | 'agent' | 'multi';
export type OutputType = 'status' | 'findings' | 'json';
export type MultiSource = 'evals' | 'mutations';

export interface InputField {
  id: string;
  type: FieldType;
  required: boolean;
  source?: MultiSource;
  anyOf?: string;
}

export interface OutputField {
  id: string;
  type: OutputType;
}

export interface PluginDef {
  id: string;
  taskType: string;
  name?: string;
  nameEn?: string;
  inputs: InputField[];
  outputs: OutputField[];
}

export interface PresetDef {
  id: string;
  name?: string;
  nameEn?: string;
  blurb?: string;
  blurbEn?: string;
  plugins: string[];
  inputs?: InputField[];
  require?: Record<string, boolean>;
}

export type HeaderRow = { key: string; value: string };
export type FieldValue = string | string[] | File[] | HeaderRow[];
export type Values = Record<string, FieldValue>;

const result: OutputField[] = [
  { id: 'status', type: 'status' },
  { id: 'findings', type: 'findings' },
];

export const plugins: PluginDef[] = [
  {
    id: 'infra-scan',
    taskType: 'AI-Infra-Scan',
    inputs: [{ id: 'target', type: 'text', required: true }],
    outputs: result,
  },
  {
    id: 'model-redteam',
    taskType: 'Model-Redteam-Report',
    inputs: [
      { id: 'model', type: 'model', required: true },
      { id: 'evals', type: 'multi', source: 'evals', required: false },
      { id: 'mutations', type: 'multi', source: 'mutations', required: false },
    ],
    outputs: result,
  },
  {
    id: 'skill-scan',
    taskType: 'Skill-Scan',
    inputs: [{ id: 'code', type: 'files', required: true }],
    outputs: result,
  },
  {
    id: 'mcp-scan',
    taskType: 'Mcp-Scan',
    inputs: [
      { id: 'code', type: 'files', required: false, anyOf: 'material' },
      { id: 'endpoint', type: 'text', required: false, anyOf: 'material' },
      { id: 'headers', type: 'headers', required: false },
    ],
    outputs: result,
  },
  {
    id: 'agent-scan',
    taskType: 'Agent-Scan',
    inputs: [
      { id: 'agent', type: 'agent', required: true },
      { id: 'code', type: 'files', required: false },
    ],
    outputs: result,
  },
];

export const presets: PresetDef[] = [
  { id: 'infra', plugins: ['infra-scan'] },
  { id: 'model', plugins: ['model-redteam'] },
  { id: 'skill', plugins: ['skill-scan'] },
  { id: 'mcp', plugins: ['mcp-scan'] },
  { id: 'agent', plugins: ['agent-scan'] },
  {
    id: 'gov',
    plugins: ['infra-scan', 'model-redteam'],
    inputs: [{ id: 'purpose', type: 'textarea', required: true }],
    require: { model: false },
  },
];

export const pluginById = (id: string, list: PluginDef[] = plugins) => list.find(item => item.id === id);

const fieldTypes = new Set(['text', 'textarea', 'model', 'files', 'headers', 'agent', 'multi']);
const outputTypes = new Set(['status', 'findings', 'json']);

function asField(raw: any): InputField | null {
  if (!raw || typeof raw.id !== 'string' || !fieldTypes.has(raw.type)) return null;
  return {
    id: raw.id,
    type: raw.type,
    required: !!raw.required,
    source: raw.source === 'evals' || raw.source === 'mutations' ? raw.source : undefined,
    anyOf: typeof raw.anyOf === 'string' && raw.anyOf ? raw.anyOf : undefined,
  };
}

function asOutput(raw: any): OutputField | null {
  if (!raw || typeof raw.id !== 'string' || !outputTypes.has(raw.type)) return null;
  return { id: raw.id, type: raw.type };
}

export function catalogFromApi(data: any): { plugins: PluginDef[]; presets: PresetDef[] } | null {
  const rawPlugins = Array.isArray(data?.plugins) ? data.plugins : [];
  const loadedPlugins = rawPlugins.flatMap((item: any): PluginDef[] => {
    const inputs = (Array.isArray(item?.inputs) ? item.inputs : []).map(asField).filter((field: InputField | null): field is InputField => !!field);
    const outputs = (Array.isArray(item?.outputs) ? item.outputs : []).map(asOutput).filter((field: OutputField | null): field is OutputField => !!field);
    const local = plugins.find(plugin => plugin.id === item?.id);
    if (!item?.id || !item?.task_type) return [];
    if (inputs.length === 0 && !local) return [];
    return [{
      id: item.id,
      taskType: item.task_type,
      name: item.name || local?.name,
      nameEn: item.name_en || local?.nameEn,
      inputs: inputs.length > 0 ? inputs : (local?.inputs || []),
      outputs: outputs.length > 0 ? outputs : (local?.outputs || []),
    }];
  });
  const rawPresets = (Array.isArray(data?.presets) ? data.presets : []).filter((item: any) => item?.ui);
  const loadedPresets = rawPresets.flatMap((item: any): PresetDef[] => {
    if (!item?.id || !Array.isArray(item.plugins) || item.plugins.length === 0) return [];
    const inputs = (Array.isArray(item.inputs) ? item.inputs : []).map(asField).filter((field: InputField | null): field is InputField => !!field);
    return [{
      id: item.id,
      name: item.name,
      nameEn: item.name_en,
      blurb: item.description,
      blurbEn: item.description_en,
      plugins: item.plugins.filter((id: unknown) => typeof id === 'string'),
      inputs,
      require: item.require && typeof item.require === 'object' ? item.require : undefined,
    }];
  });
  if (loadedPlugins.length === 0 || loadedPresets.length === 0) return null;
  return { plugins: loadedPlugins, presets: loadedPresets };
}

export function resolveInputs(preset: PresetDef | null, pluginIds: string[], catalog: PluginDef[] = plugins): InputField[] {
  const fields: InputField[] = [];
  const push = (field: InputField) => {
    if (fields.some(item => item.id === field.id)) return;
    const required = preset?.require && Object.prototype.hasOwnProperty.call(preset.require, field.id)
      ? !!preset.require[field.id]
      : field.required;
    fields.push({ ...field, required });
  };
  preset?.inputs?.forEach(push);
  pluginIds.forEach(id => pluginById(id, catalog)?.inputs.forEach(push));
  return fields;
}

export function emptyValue(field: InputField): FieldValue {
  if (field.type === 'files' || field.type === 'multi') return [];
  if (field.type === 'headers') return [];
  return '';
}

export function fieldFilled(field: InputField, values: Values) {
  const value = values[field.id];
  if (field.type === 'files') return Array.isArray(value) && value.some(item => item instanceof File);
  if (field.type === 'multi') return Array.isArray(value) && value.length > 0;
  if (field.type === 'headers') {
    return Array.isArray(value) && (value as HeaderRow[]).some(row => row?.key?.trim() && row?.value?.trim());
  }
  return typeof value === 'string' && value.trim() !== '';
}

export function inputsReady(fields: InputField[], values: Values) {
  const groups = new Set(fields.map(field => field.anyOf).filter((item): item is string => !!item));
  for (const group of groups) {
    const members = fields.filter(field => field.anyOf === group);
    if (!members.some(field => fieldFilled(field, values))) return false;
  }
  return fields.every(field => field.anyOf || !field.required || fieldFilled(field, values));
}
