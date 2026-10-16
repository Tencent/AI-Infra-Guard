import { v4 as uuidv4 } from 'uuid';
import { GuidedReportData } from '../types';
import { GuidedScanDraft, RunStatus } from './types';

export interface LiveRun {
  id: string;
  title: string;
  status: RunStatus;
  lines: string[];
  report: GuidedReportData | null;
  output: unknown;
  fallback: string;
  error: string;
}

export interface EvalRow {
  id: string;
  title: string;
  status: RunStatus;
  createdAt: string;
}

const runs = new Map<string, LiveRun>();
const listeners = new Map<string, Set<() => void>>();
const sources = new Map<string, EventSource>();

function publish(id: string) {
  listeners.get(id)?.forEach(listener => listener());
}

export function getRun(id: string): LiveRun | undefined {
  return runs.get(id);
}

export function markFailed(id: string, message: string) {
  const current = runs.get(id);
  if (current?.status === 'done') return;
  put(id, {
    id,
    title: current?.title || '',
    status: 'error',
    lines: current?.lines || [],
    report: current?.report || null,
    output: current?.output || null,
    fallback: current?.fallback || '',
    error: message || current?.error || '',
  });
}

export function subscribeRun(id: string, listener: () => void) {
  let set = listeners.get(id);
  if (!set) {
    set = new Set();
    listeners.set(id, set);
  }
  set.add(listener);
  return () => {
    set?.delete(listener);
  };
}

function put(id: string, next: LiveRun) {
  runs.set(id, next);
  publish(id);
}

function terminal(status: RunStatus) {
  return status === 'done' || status === 'error' || status === 'terminated';
}

function merge(existing: LiveRun | undefined, incoming: LiveRun): LiveRun {
  if (!existing) return incoming;
  const status = !terminal(incoming.status) && terminal(existing.status) ? existing.status : incoming.status;
  return {
    ...incoming,
    title: incoming.title || existing.title,
    status,
    lines: existing.lines.length > incoming.lines.length ? existing.lines : incoming.lines,
    report: incoming.report || existing.report,
    output: incoming.output || existing.output,
    fallback: incoming.fallback || existing.fallback,
    error: incoming.error || existing.error,
  };
}

function mapStatus(status: string): RunStatus {
  if (status === 'done' || status === 'completed') return 'done';
  if (status === 'error' || status === 'failed') return 'error';
  if (status === 'terminated') return 'terminated';
  return 'running';
}

function readResult(event: any) {
  return event?.result || event?.event?.result;
}

function applyMessage(state: { lines: string[]; report: GuidedReportData | null; output: unknown; fallback: string; error: string }, message: any) {
  if (message?.type === 'statusUpdate') {
    const brief = message.event?.brief || message.event?.description;
    if (brief && state.lines[state.lines.length - 1] !== brief) state.lines.push(brief);
  }
  if (message?.type === 'resultUpdate') {
    const result = readResult(message.event);
    if (result?.report) state.report = result.report;
    if (result && typeof result === 'object' && (result.plugin || Array.isArray(result.findings))) state.output = result;
    state.fallback = result?.content || result?.report?.summary || state.fallback;
  }
  if (message?.type === 'error') {
    state.error = message.event?.message || state.error;
  }
}

function attach(id: string) {
  if (sources.has(id)) return;
  const source = new EventSource(`/api/v1/app/tasks/sse/${id}`);
  sources.set(id, source);

  const listen = (type: string, handle: (data: any) => void) => {
    source.addEventListener(type, (event: Event) => {
      const raw = (event as MessageEvent).data;
      if (!raw) return;
      try {
        handle(JSON.parse(raw));
      } catch {
        // Connection errors share this event name and carry no JSON payload.
      }
    });
  };

  listen('statusUpdate', data => {
    const current = runs.get(id);
    if (!current) return;
    const next = { ...current, lines: [...current.lines] };
    applyMessage(next, { type: 'statusUpdate', event: data.event });
    put(id, next);
  });

  listen('resultUpdate', data => {
    const current = runs.get(id);
    if (!current) return;
    const next = { ...current, lines: [...current.lines], status: 'done' as RunStatus };
    applyMessage(next, { type: 'resultUpdate', event: data.event });
    put(id, next);
    source.close();
    sources.delete(id);
  });

  listen('error', data => {
    const message = data?.event?.message;
    if (!message) return;
    const current = runs.get(id);
    if (!current) return;
    put(id, { ...current, status: 'error', error: message });
    source.close();
    sources.delete(id);
  });
}

async function uploadChunked(file: File) {
  const chunkSize = 1024 * 1024;
  const totalChunks = Math.ceil(file.size / chunkSize);
  const fileId = uuidv4();
  for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
    const start = chunkIndex * chunkSize;
    const chunk = file.slice(start, Math.min(start + chunkSize, file.size));
    const form = new FormData();
    form.append('fileId', fileId);
    form.append('filename', file.name);
    form.append('chunkIndex', String(chunkIndex));
    form.append('totalChunks', String(totalChunks));
    form.append('chunk', chunk);
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

export async function startScan(draft: GuidedScanDraft, language: string) {
  const attachments: string[] = [];
  for (const file of draft.files) attachments.push(await uploadOne(file));

  const id = `${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
  const title = (draft.purpose || draft.targetUrl || draft.scenario).trim() || draft.scenario;
  const headers: Record<string, string> = {};
  draft.headers.forEach(header => {
    if (header.key.trim() && header.value.trim()) headers[header.key.trim()] = header.value.trim();
  });

  put(id, { id, title, status: 'running', lines: [], report: null, output: null, fallback: '', error: '' });
  attach(id);

  const response = await fetch('/api/v1/app/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      id,
      sessionId: id,
      taskType: 'Guided-Scan',
      timestamp: Date.now(),
      content: title,
      params: {
        scenario: draft.scenario,
        purpose: draft.purpose,
        target_url: draft.targetUrl,
        model_id: draft.modelId,
        eval_model_id: draft.modelId,
        agent_id: draft.agentId,
        plugins: draft.plugins,
        strategies: draft.strategies,
        headers: Object.keys(headers).length > 0 ? headers : undefined,
      },
      attachments,
      countryIsoCode: language,
    }),
  });
  const result = await response.json().catch(() => ({}));
  if (!response.ok || result.status !== 0) {
    sources.get(id)?.close();
    sources.delete(id);
    const current = runs.get(id);
    if (current) put(id, { ...current, status: 'error', error: result.message || '' });
    throw new Error(result.message || '');
  }
  return id;
}

export async function hydrate(id: string) {
  const response = await fetch(`/api/v1/app/tasks/${id}`);
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.status !== 0) throw new Error(body.message || '');
  const data = body.data || {};
  const parsed = { lines: [] as string[], report: null as GuidedReportData | null, output: null as unknown, fallback: '', error: '' };
  for (const message of data.messages || []) applyMessage(parsed, message);
  const incoming: LiveRun = {
    id,
    title: data.title || data.content || '',
    status: parsed.error && mapStatus(data.status) === 'running' ? 'error' : mapStatus(data.status),
    lines: parsed.lines,
    report: parsed.report,
    output: parsed.output,
    fallback: parsed.fallback,
    error: parsed.error,
  };
  const next = merge(runs.get(id), incoming);
  put(id, next);
  if (next.status === 'running') attach(id);
  return next;
}

export async function listEvals(): Promise<EvalRow[]> {
  const response = await fetch('/api/v1/app/tasks?taskType=Guided-Scan');
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.status !== 0) throw new Error(body.message || '');
  const tasks = (body.data?.tasks || []) as any[];
  return tasks
    .filter(task => !task.taskType || String(task.taskType).includes('Guided-Scan'))
    .map(task => ({
      id: task.sessionId,
      title: task.title || task.content || task.sessionId,
      status: mapStatus(task.status),
      createdAt: task.createdAt,
    }));
}
