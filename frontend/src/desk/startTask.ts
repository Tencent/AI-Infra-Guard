import { v4 as uuidv4 } from 'uuid';
import { HeaderRow, Values } from './plugins';

async function uploadChunked(file: File) {
  const chunkSize = 1024 * 1024;
  const totalChunks = Math.ceil(file.size / chunkSize);
  const fileId = uuidv4();
  for (let index = 0; index < totalChunks; index++) {
    const start = index * chunkSize;
    const form = new FormData();
    form.append('fileId', fileId);
    form.append('filename', file.name);
    form.append('chunkIndex', String(index));
    form.append('totalChunks', String(totalChunks));
    form.append('chunk', file.slice(start, Math.min(start + chunkSize, file.size)));
    const response = await fetch('/api/v1/app/tasks/uploadChunk', { method: 'POST', body: form });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || result.status !== 0) throw new Error(result.message || '');
  }
  const merge = await fetch('/api/v1/app/tasks/mergeChunks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fileId, filename: file.name, totalChunks, fileSize: file.size }),
  });
  const merged = await merge.json().catch(() => ({}));
  if (!merge.ok || merged.status !== 0 || !merged.data?.fileUrl) throw new Error(merged.message || '');
  return merged.data.fileUrl as string;
}

async function uploadOne(file: File) {
  if (file.size > 1024 * 1024) return uploadChunked(file);
  const form = new FormData();
  form.append('file', file);
  const response = await fetch('/api/v1/app/tasks/uploadFile', { method: 'POST', body: form });
  const result = await response.json().catch(() => ({}));
  if (!response.ok || result.status !== 0 || !result.data?.fileUrl) throw new Error(result.message || '');
  return result.data.fileUrl as string;
}

const text = (values: Values, id: string) => (typeof values[id] === 'string' ? (values[id] as string).trim() : '');

export interface ScenePayload {
  plugins: string[];
  preset?: string;
  inputs: Record<string, unknown>;
}

export async function prepareScene(pluginIds: string[], values: Values, presetId?: string): Promise<ScenePayload> {
  const files = Array.isArray(values.code) ? values.code as File[] : [];
  const code: string[] = [];
  for (const file of files) code.push(await uploadOne(file));

  const headers: Record<string, string> = {};
  if (Array.isArray(values.headers)) {
    (values.headers as HeaderRow[]).forEach(row => {
      if (row.key.trim() && row.value.trim()) headers[row.key.trim()] = row.value.trim();
    });
  }
  const inputs: Record<string, unknown> = {};
  (['target', 'purpose', 'endpoint', 'model', 'agent'] as const).forEach(id => {
    const value = text(values, id);
    if (value) inputs[id] = value;
  });
  if (code.length > 0) inputs.code = code;
  if (Array.isArray(values.evals) && values.evals.length > 0) inputs.evals = values.evals;
  if (Array.isArray(values.mutations) && values.mutations.length > 0) inputs.mutations = values.mutations;
  if (Object.keys(headers).length > 0) inputs.headers = headers;

  return { plugins: pluginIds, preset: presetId || undefined, inputs };
}

export interface EngineReport {
  id: string;
  status: string;
  plugins: unknown[];
  timeline?: import('./ScanTimeline').TimelineEvent[];
  createdAt?: string;
}

type StreamMessage =
  | { type: 'event'; event: import('./ScanTimeline').TimelineEvent }
  | { type: 'report'; report: EngineReport }
  | { type: 'error'; message: string };

interface ScanJob {
  key: string;
  listeners: Set<(message: StreamMessage) => void>;
  events: import('./ScanTimeline').TimelineEvent[];
  report?: EngineReport;
  error?: string;
  abort: () => void;
}

let scanJob: ScanJob | null = null;

function publish(job: ScanJob, message: StreamMessage) {
  job.listeners.forEach(listener => listener(message));
}

async function readStream(payload: ScenePayload, job: ScanJob, signal: AbortSignal) {
  try {
    const response = await fetch('/api/v1/app/engine/scans?stream=1', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    });
    if (!response.ok || !response.body) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.message || '');
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    const take = (frame: string) => {
      const data = frame.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trim()).join('\n');
      if (!data) return;
      const message = JSON.parse(data);
      if (message.error) {
        job.error = message.error;
        publish(job, { type: 'error', message: message.error });
        return;
      }
      if (message.type === 'event' && message.event) {
        job.events.push(message.event);
        publish(job, { type: 'event', event: message.event });
      }
      if (message.type === 'report' && message.report) {
        job.report = message.report;
        publish(job, { type: 'report', report: message.report });
      }
    };
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      buffer = frames.pop() || '';
      frames.forEach(take);
    }
    if (buffer.trim()) take(buffer);
    if (!job.report && !job.error) {
      job.error = '扫描失败';
      publish(job, { type: 'error', message: job.error });
    }
  } catch (error: any) {
    if (error?.name === 'AbortError') return;
    job.error = error?.message || '';
    publish(job, { type: 'error', message: job.error || '' });
  }
}

export function watchScan(nonce: string, payload: ScenePayload, listener: (message: StreamMessage) => void) {
  if (!scanJob || scanJob.key !== nonce) {
    if (scanJob) scanJob.abort();
    const controller = new AbortController();
    scanJob = { key: nonce, listeners: new Set(), events: [], abort: () => controller.abort() };
    void readStream(payload, scanJob, controller.signal);
  }
  const job = scanJob;
  job.listeners.add(listener);
  job.events.forEach(event => listener({ type: 'event', event }));
  if (job.report) listener({ type: 'report', report: job.report });
  if (job.error) listener({ type: 'error', message: job.error });
  return () => { job.listeners.delete(listener); };
}

export interface ScanRow {
  id: string;
  status: string;
  plugins: string[];
  createdAt?: string;
}

export async function listScans(): Promise<ScanRow[]> {
  const response = await fetch('/api/v1/app/engine/scans');
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.status !== 0 || !Array.isArray(body.data)) throw new Error(body.message || '');
  return body.data as ScanRow[];
}

export async function loadScan(id: string) {
  const response = await fetch(`/api/v1/app/engine/scans/${id}`);
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.status !== 0 || !body.data) throw new Error(body.message || '');
  return body.data as EngineReport;
}

export interface TaskRow {
  id: string;
  title: string;
  taskType: string;
  status: string;
  createdAt: string;
}

export async function listTasks(): Promise<TaskRow[]> {
  const response = await fetch('/api/v1/app/tasks');
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.status !== 0) throw new Error(body.message || '');
  return ((body.data?.tasks || []) as any[]).map(task => ({
    id: task.sessionId,
    title: task.title || task.sessionId,
    taskType: task.taskType || '',
    status: task.status || '',
    createdAt: task.createdAt || '',
  }));
}
