import { v4 as uuidv4 } from 'uuid';
import { HeaderRow, Values, pluginById } from './plugins';

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

const uses = (pluginId: string, fieldId: string) => !!pluginById(pluginId)?.inputs.some(field => field.id === fieldId);

export async function startScene(pluginIds: string[], values: Values, language: string) {
  const files = Array.isArray(values.code) ? values.code as File[] : [];
  const attachments: string[] = [];
  for (const file of files) attachments.push(await uploadOne(file));

  const headers: Record<string, string> = {};
  if (Array.isArray(values.headers)) {
    (values.headers as HeaderRow[]).forEach(row => {
      if (row.key.trim() && row.value.trim()) headers[row.key.trim()] = row.value.trim();
    });
  }
  const evals = Array.isArray(values.evals) ? values.evals as string[] : [];
  const mutations = Array.isArray(values.mutations) ? values.mutations as string[] : [];

  const ids: string[] = [];
  const errors: string[] = [];
  for (const pluginId of pluginIds) {
    const plugin = pluginById(pluginId);
    if (!plugin) continue;
    const content = (uses(pluginId, 'target') && text(values, 'target'))
      || (uses(pluginId, 'endpoint') && text(values, 'endpoint'))
      || text(values, 'purpose')
      || plugin.id;
    const params: Record<string, unknown> = {};
    if (uses(pluginId, 'model') && text(values, 'model')) {
      params.model_id = text(values, 'model');
      params.eval_model_id = text(values, 'model');
    }
    if (uses(pluginId, 'agent') && text(values, 'agent')) params.agent_id = text(values, 'agent');
    if (uses(pluginId, 'headers') && Object.keys(headers).length > 0) params.headers = headers;
    if (uses(pluginId, 'evals') && evals.length > 0) params.dataset = { dataFile: evals };
    if (uses(pluginId, 'mutations') && mutations.length > 0) params.techniques = mutations;

    const id = `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
    try {
      const response = await fetch('/api/v1/app/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id,
          sessionId: id,
          taskType: plugin.taskType,
          timestamp: Date.now(),
          content,
          params,
          attachments: uses(pluginId, 'code') ? attachments : [],
          countryIsoCode: language,
        }),
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok || result.status !== 0) throw new Error(result.message || '');
      ids.push(id);
    } catch (error: any) {
      errors.push(error?.message || pluginId);
    }
  }
  if (ids.length === 0) throw new Error(errors[0] || '');
  return { ids, errors };
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
