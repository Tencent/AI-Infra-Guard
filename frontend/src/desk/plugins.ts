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
  inputs: InputField[];
  outputs: OutputField[];
}

export interface PresetDef {
  id: string;
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

export const pluginById = (id: string) => plugins.find(item => item.id === id);

export function resolveInputs(preset: PresetDef | null, pluginIds: string[]): InputField[] {
  const list: InputField[] = [];
  const push = (field: InputField) => {
    if (list.some(item => item.id === field.id)) return;
    const required = preset?.require && Object.prototype.hasOwnProperty.call(preset.require, field.id)
      ? !!preset.require[field.id]
      : field.required;
    list.push({ ...field, required });
  };
  preset?.inputs?.forEach(push);
  pluginIds.forEach(id => pluginById(id)?.inputs.forEach(push));
  return list;
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
