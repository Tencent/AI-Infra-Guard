export type Verdict = 'pass' | 'fail' | 'insufficient';

export type FieldType = 'text' | 'textarea' | 'model' | 'files' | 'headers' | 'agent' | 'multi';

export interface InputField {
  id: string;
  type: FieldType;
  required: boolean;
  source?: 'evals' | 'mutations';
  anyOf?: string;
}

export interface OutputField {
  id: string;
  type: 'status' | 'findings' | 'json';
}

export interface PluginManifest {
  id: string;
  taskType: string;
  name: string;
  inputs: InputField[];
  outputs: OutputField[];
}

export interface PresetManifest {
  id: string;
  name: string;
  plugins: string[];
  inputs: InputField[];
  require?: Record<string, boolean>;
  ui: boolean;
}

export interface ModelConfig {
  name?: string;
  baseUrl?: string;
  token?: string;
}

export type InputValue = string | string[] | Record<string, string> | ModelConfig;

export interface ScanConfig {
  plugins?: string[];
  preset?: string;
  inputs?: Record<string, InputValue>;
  strategies?: string[];
}

export interface Finding {
  title: string;
  severity: 'info' | 'low' | 'medium' | 'high';
  verdict: Verdict;
  strategy?: string;
  prompt?: string;
  response?: string;
  reason: string;
}

export interface PluginRun {
  plugin: string;
  status: 'ok' | 'error';
  findings: Finding[];
}

export interface TimelineEvent {
  type: 'step' | 'text' | 'tool' | 'conclusion';
  plugin: string;
  title?: string;
  status?: 'doing' | 'done' | 'error';
  text?: string;
  action?: string;
  param?: string;
  result?: string;
  detail?: string;
  verdict?: Verdict;
  reason?: string;
}

export interface ScanReport {
  id: string;
  preset?: string;
  status: Verdict | 'error';
  plugins: PluginRun[];
  timeline?: TimelineEvent[];
  createdAt?: string;
}

export interface Runtime {
  root?: string;
  id?: () => string;
  fetch?: typeof fetch;
  complete?: (input: { prompt: string; model: string }) => Promise<string>;
  grade?: (input: { plugin: string; prompt: string; response: string }) => Promise<{ verdict: Verdict; reason: string }>;
  onEvent?: (event: TimelineEvent) => void;
}

export class EngineError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'EngineError';
  }
}
