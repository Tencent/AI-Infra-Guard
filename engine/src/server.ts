import { createReadStream, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { basename, extname, join, relative } from 'node:path';
import { catalogPayload, findRepoRoot } from './catalog.js';
import { dbPath, deleteModels, listModels, listTasks, readModel, saveModel } from './db.js';
import { runScan } from './engine.js';
import {
  libraryQuery,
  listAgentNames,
  listEvaluations,
  listFingerprints,
  listVulnerabilities,
  readAgent,
  readEvaluation,
  readJailbreak,
  removeAgent,
  writeAgent,
} from './library.js';
import { listReports, readReport, saveReport } from './store.js';
import { EngineError, type ScanConfig, type TimelineEvent } from './types.js';

const types: Record<string, string> = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2',
};

export interface ServerOptions {
  root?: string;
  dbPath?: string;
  staticDir?: string;
}

function ok(data: unknown) {
  return { status: 0, message: 'ok', data };
}

function fail(message: string) {
  return { status: 1, message, data: null };
}

function send(res: ServerResponse, status: number, body: unknown) {
  const payload = JSON.stringify(body);
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Content-Length': Buffer.byteLength(payload) });
  res.end(payload);
}

function readBuffer(req: IncomingMessage, limit: number): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const chunks: Buffer[] = [];
    let size = 0;
    req.on('data', (chunk: Buffer) => {
      size += chunk.length;
      if (size > limit) {
        reject(new EngineError('请求体过大'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolve(Buffer.concat(chunks)));
    req.on('error', reject);
  });
}

async function readJson(req: IncomingMessage): Promise<Record<string, unknown>> {
  const raw = (await readBuffer(req, 1_000_000)).toString('utf8');
  if (!raw) return {};
  const parsed = JSON.parse(raw) as unknown;
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new EngineError('配置格式不正确');
  return parsed as Record<string, unknown>;
}

function inside(root: string, file: string): boolean {
  const rel = relative(root, file);
  return rel !== '' && !rel.startsWith('..') && !rel.startsWith('/');
}

function pipeFile(res: ServerResponse, file: string) {
  res.writeHead(200, { 'Content-Type': types[extname(file)] || 'application/octet-stream' });
  createReadStream(file).pipe(res);
}

function serveStatic(res: ServerResponse, root: string, urlPath: string) {
  const decoded = decodeURIComponent((urlPath.split('?')[0] || '/')).replace(/^\/+/, '') || 'index.html';
  const file = join(root, decoded);
  if (inside(root, file) && existsSync(file) && statSync(file).isFile()) {
    pipeFile(res, file);
    return;
  }
  const index = join(root, 'index.html');
  if (!extname(decoded) && existsSync(index)) {
    pipeFile(res, index);
    return;
  }
  send(res, 404, fail('页面不存在'));
}

function partsOf(body: Buffer, contentType: string) {
  const found = /boundary=(?:"([^"]+)"|([^;]+))/i.exec(contentType);
  const boundary = (found?.[1] || found?.[2] || '').trim();
  if (!boundary) throw new EngineError('上传格式不正确');
  const marker = Buffer.from(`--${boundary}`);
  const fields: Record<string, string> = {};
  const files: Record<string, { filename: string; data: Buffer }> = {};
  let start = body.indexOf(marker);
  while (start !== -1) {
    const next = body.indexOf(marker, start + marker.length);
    if (next === -1) break;
    let chunk = body.subarray(start + marker.length, next);
    if (chunk.subarray(0, 2).toString() === '\r\n') chunk = chunk.subarray(2);
    if (chunk.subarray(-2).toString() === '\r\n') chunk = chunk.subarray(0, chunk.length - 2);
    const split = chunk.indexOf('\r\n\r\n');
    if (split !== -1) {
      const header = chunk.subarray(0, split).toString('utf8');
      const data = chunk.subarray(split + 4);
      const name = /name="([^"]+)"/.exec(header)?.[1] || '';
      const filename = /filename="([^"]*)"/.exec(header)?.[1];
      if (name && filename !== undefined) files[name] = { filename: basename(filename), data };
      else if (name) fields[name] = data.toString('utf8');
    }
    start = next;
  }
  return { fields, files };
}

function safeId(value: string): string {
  if (!/^[a-zA-Z0-9_-]{1,80}$/.test(value)) throw new EngineError('文件编号不正确');
  return value;
}

function uploadRoot(root: string): string {
  const dir = join(root, 'uploads');
  mkdirSync(dir, { recursive: true });
  return dir;
}

export async function handleRequest(req: IncomingMessage, res: ServerResponse, options: ServerOptions = {}) {
  const root = options.root || findRepoRoot();
  const database = options.dbPath || dbPath(root);
  const staticDir = options.staticDir || join(root, 'common', 'websocket', 'static');
  const url = new URL(req.url || '/', 'http://127.0.0.1');
  const user = req.headers.username;
  const username = Array.isArray(user) ? user[0] : user;
  const path = url.pathname;

  if (req.method === 'GET' && path === '/api/v1/app/catalog') return send(res, 200, ok(catalogPayload(root)));
  if (req.method === 'GET' && path === '/api/v1/app/engine/scans') return send(res, 200, ok(listReports(root)));
  if (req.method === 'GET' && path.startsWith('/api/v1/app/engine/scans/')) return send(res, 200, ok(readReport(decodeURIComponent(path.slice('/api/v1/app/engine/scans/'.length)), root)));
  if (req.method === 'POST' && path === '/api/v1/app/engine/scans') return scan(req, res, url, root);
  if (req.method === 'GET' && path === '/api/v1/app/models') return send(res, 200, ok(listModels(username, database)));
  if (req.method === 'GET' && path.startsWith('/api/v1/app/models/')) {
    const model = readModel(decodeURIComponent(path.slice('/api/v1/app/models/'.length)), username, database);
    return send(res, 200, model ? ok(model) : fail('模型不存在'));
  }
  if (req.method === 'POST' && path === '/api/v1/app/models') {
    const body = await readJson(req);
    const model = body.model && typeof body.model === 'object' ? body.model as Record<string, unknown> : {};
    saveModel(String(body.model_id || ''), model, username, database, false);
    return send(res, 200, ok(null));
  }
  if (req.method === 'PUT' && path.startsWith('/api/v1/app/models/')) {
    const body = await readJson(req);
    const model = body.model && typeof body.model === 'object' ? body.model as Record<string, unknown> : {};
    saveModel(decodeURIComponent(path.slice('/api/v1/app/models/'.length)), model, username, database, true);
    return send(res, 200, ok(null));
  }
  if (req.method === 'DELETE' && path === '/api/v1/app/models') {
    const body = await readJson(req);
    deleteModels(Array.isArray(body.model_ids) ? body.model_ids.map(String) : [], username, database);
    return send(res, 200, ok(null));
  }
  if (req.method === 'GET' && path === '/api/v1/app/tasks') return send(res, 200, ok({ tasks: listTasks(username, url.searchParams.get('taskType') || '', database) }));
  if (req.method === 'POST' && (path === '/api/v1/app/tasks/uploadFile' || path === '/api/v1/app/tasks/uploadChunk' || path === '/api/v1/app/tasks/mergeChunks')) {
    return upload(req, res, path, root);
  }
  if (req.method === 'GET' && path === '/api/v1/knowledge/fingerprints') {
    const query = libraryQuery(url);
    return send(res, 200, ok(listFingerprints(root, query.page, query.size, query.q)));
  }
  if (req.method === 'GET' && path === '/api/v1/knowledge/vulnerabilities') {
    const query = libraryQuery(url);
    return send(res, 200, ok(listVulnerabilities(root, query.page, query.size, query.q, query.lang)));
  }
  if (req.method === 'GET' && path === '/api/v1/knowledge/evaluations') {
    const query = libraryQuery(url);
    return send(res, 200, ok(listEvaluations(root, query.page, query.size, query.q)));
  }
  if (req.method === 'GET' && path.startsWith('/api/v1/knowledge/evaluations/')) return send(res, 200, ok(readEvaluation(root, decodeURIComponent(path.slice('/api/v1/knowledge/evaluations/'.length)))));
  if (req.method === 'GET' && path === '/api/v1/knowledge/jailbreak') return send(res, 200, ok(readJailbreak(root)));
  if (req.method === 'GET' && path === '/api/v1/knowledge/agent/names') return send(res, 200, ok(listAgentNames(root, username)));
  if (req.method === 'GET' && path.startsWith('/api/v1/knowledge/agent/') && path !== '/api/v1/knowledge/agent/names') {
    return send(res, 200, ok(readAgent(root, decodeURIComponent(path.slice('/api/v1/knowledge/agent/'.length)), username)));
  }
  if (req.method === 'POST' && path.startsWith('/api/v1/knowledge/agent/') && path !== '/api/v1/knowledge/agent/connect') {
    const body = await readJson(req);
    writeAgent(root, decodeURIComponent(path.slice('/api/v1/knowledge/agent/'.length)), String(body.content || ''), username);
    return send(res, 200, ok(null));
  }
  if (req.method === 'DELETE' && path.startsWith('/api/v1/knowledge/agent/')) {
    removeAgent(root, decodeURIComponent(path.slice('/api/v1/knowledge/agent/'.length)), username);
    return send(res, 200, ok(null));
  }
  if (req.method === 'GET' && (path === '/api/v1/system/version' || path === '/api/v1/version')) {
    return send(res, 200, ok({ current_version: 'v5', latest_version: 'v5', update_available: false, update_required: false }));
  }
  if (req.method === 'GET' && path === '/plugins') return send(res, 200, catalogPayload(root).plugins);
  if (req.method === 'GET' && path === '/presets') return send(res, 200, catalogPayload(root).presets.filter(item => item.ui));
  if (req.method === 'GET' && !path.startsWith('/api/')) return serveStatic(res, staticDir, path);
  send(res, 404, fail('未知接口'));
}

async function scan(req: IncomingMessage, res: ServerResponse, url: URL, root: string) {
  const config = await readJson(req) as ScanConfig;
  if (url.searchParams.get('stream') === '1') {
    res.writeHead(200, {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
    });
    const report = saveReport(await runScan(config, {
      root,
      onEvent: (event: TimelineEvent) => {
        res.write(`data: ${JSON.stringify({ type: 'event', event })}\n\n`);
      },
    }), root);
    res.write(`data: ${JSON.stringify({ type: 'report', report })}\n\n`);
    res.end();
    return;
  }
  send(res, 200, ok(saveReport(await runScan(config, { root }), root)));
}

async function upload(req: IncomingMessage, res: ServerResponse, path: string, root: string) {
  if (path === '/api/v1/app/tasks/mergeChunks') {
    const body = await readJson(req);
    const fileId = safeId(String(body.fileId || ''));
    const filename = basename(String(body.filename || 'file'));
    const total = Number(body.totalChunks);
    if (!filename || !Number.isInteger(total) || total < 1) throw new EngineError('分片参数不正确');
    const chunks = Array.from({ length: total }, (_, index) => readFileSync(join(uploadRoot(root), '.chunks', fileId, String(index))));
    const file = join(uploadRoot(root), fileId, filename);
    mkdirSync(join(uploadRoot(root), fileId), { recursive: true });
    writeFileSync(file, Buffer.concat(chunks));
    return send(res, 200, ok({ filename, fileUrl: file, fileSize: statSync(file).size }));
  }
  const form = partsOf(await readBuffer(req, 32_000_000), String(req.headers['content-type'] || ''));
  if (path === '/api/v1/app/tasks/uploadFile') {
    const file = form.files.file;
    if (!file?.filename) throw new EngineError('没有收到文件');
    const fileId = safeId(`${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}`);
    const saved = join(uploadRoot(root), fileId, file.filename);
    mkdirSync(join(uploadRoot(root), fileId), { recursive: true });
    writeFileSync(saved, file.data);
    return send(res, 200, ok({ fileUrl: saved, filename: file.filename, size: file.data.length }));
  }
  const fileId = safeId(form.fields.fileId || '');
  const index = Number(form.fields.chunkIndex);
  const total = Number(form.fields.totalChunks);
  const chunk = form.files.chunk;
  if (!chunk || !Number.isInteger(index) || index < 0 || !Number.isInteger(total) || index >= total) throw new EngineError('分片参数不正确');
  const dir = join(uploadRoot(root), '.chunks', fileId);
  mkdirSync(dir, { recursive: true });
  writeFileSync(join(dir, String(index)), chunk.data);
  send(res, 200, ok({ chunkIndex: index, totalChunks: total, message: '分片已保存' }));
}

export function startServer(port = 8088, host = '127.0.0.1', options: ServerOptions = {}) {
  const server = createServer((req, res) => {
    handleRequest(req, res, options).catch(error => {
      const message = error instanceof EngineError ? error.message : error instanceof SyntaxError ? '配置格式不正确' : '请求失败';
      if (res.headersSent) {
        res.write(`data: ${JSON.stringify({ error: message })}\n\n`);
        res.end();
        return;
      }
      send(res, 200, fail(message));
    });
  });
  return new Promise<{ server: typeof server; port: number }>((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, host, () => {
      const address = server.address();
      resolve({ server, port: typeof address === 'object' && address ? address.port : port });
    });
  });
}
