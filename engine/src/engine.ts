import { randomUUID } from 'node:crypto';
import { loadCatalog } from './catalog.js';
import { lookupModel } from './db.js';
import { matchProbe, type Probe } from './infra.js';
import { auditDirectory } from './piAudit.js';
import { casesFor, headerKeys, list, text } from './plugins.js';
import { generateModelCases, gradeModelReply } from './redteam.js';
import { applyStrategy } from './strategies.js';
import { isScanTarget } from './target.js';
import {
  EngineError,
  type Finding,
  type InputField,
  type InputValue,
  type ModelConfig,
  type PluginManifest,
  type PresetManifest,
  type Runtime,
  type ScanConfig,
  type ScanReport,
  type TimelineEvent,
  type Verdict,
} from './types.js';

const maxCases = 24;

function filled(field: InputField, inputs: Record<string, InputValue>): boolean {
  const value = inputs[field.id];
  if (field.type === 'files' || field.type === 'multi') return list(value).length > 0;
  if (field.type === 'headers') return headerKeys(value).length > 0;
  if (field.type === 'model') return text(value).length > 0 || modelConfig(value) !== null;
  return text(value).length > 0;
}

function resolveFields(preset: PresetManifest | undefined, pluginIds: string[], plugins: PluginManifest[]): InputField[] {
  const fields: InputField[] = [];
  const push = (field: InputField) => {
    if (fields.some(item => item.id === field.id)) return;
    const required = preset?.require && Object.prototype.hasOwnProperty.call(preset.require, field.id)
      ? !!preset.require[field.id]
      : field.required;
    fields.push({ ...field, required });
  };
  preset?.inputs.forEach(push);
  pluginIds.forEach(id => plugins.find(item => item.id === id)?.inputs.forEach(push));
  return fields;
}

function assertReady(fields: InputField[], inputs: Record<string, InputValue>) {
  const groups = new Set(fields.map(field => field.anyOf).filter((item): item is string => !!item));
  for (const group of groups) {
    const members = fields.filter(field => field.anyOf === group);
    if (!members.some(field => filled(field, inputs))) throw new EngineError('还有必填项没有填写');
  }
  if (fields.some(field => !field.anyOf && field.required && !filled(field, inputs))) {
    throw new EngineError('还有必填项没有填写');
  }
}

function modelConfig(value: InputValue | undefined): ModelConfig | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  const item = value as ModelConfig;
  if (!item.baseUrl && !item.token && !item.name) return null;
  return { name: item.name, baseUrl: item.baseUrl, token: item.token };
}

function strategyIds(config: ScanConfig, inputs: Record<string, InputValue>): string[] {
  const picked = (config.strategies?.length ? config.strategies : list(inputs.mutations)).slice(0, 3);
  return picked.length > 0 ? picked : ['direct'];
}

function blockedHost(hostname: string): boolean {
  const host = hostname.replace(/^\[|\]$/g, '').toLowerCase();
  return host === 'metadata.google.internal' || host === '169.254.169.254';
}

function credentials(inputs: Record<string, InputValue>): ModelConfig | null {
  const direct = modelConfig(inputs.model);
  if (direct?.baseUrl && direct.token && direct.name) return direct;
  const id = text(inputs.model);
  return id ? lookupModel(id) : null;
}

async function observeTarget(target: string, runtime: Runtime): Promise<{ response: string; reason: string; probe?: Probe }> {
  let url: URL;
  try {
    url = new URL(target);
  } catch {
    return { response: '', reason: '已记录目标，未发起请求' };
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return { response: '', reason: '已记录目标，未发起请求' };
  if (url.username || url.password || blockedHost(url.hostname)) return { response: '', reason: '该地址不会被请求' };
  const fetchImpl = runtime.fetch ?? fetch;
  try {
    const response = await fetchImpl(url.toString(), { method: 'GET', redirect: 'manual', signal: AbortSignal.timeout(5000) });
    const server = response.headers.get('server');
    const note = server && server.length <= 80 ? `，Server ${server}` : '';
    const body = await response.text().catch(() => '');
    const header = [...response.headers.entries()].map(([key, value]) => `${key}: ${value}`).join('\n');
    return {
      response: `HTTP ${response.status}${note}`,
      reason: '已记录响应状态',
      probe: { path: url.pathname || '/', status: response.status, header, body: body.slice(0, 20000) },
    };
  } catch {
    return { response: '', reason: '请求失败' };
  }
}

async function completeModel(prompt: string, model: ModelConfig | null, fallback: string, runtime: Runtime): Promise<string> {
  if (runtime.complete) return runtime.complete({ prompt, model: model?.name || fallback });
  if (!model?.baseUrl || !model.token || !model.name) return '';
  const base = model.baseUrl.replace(/\/$/, '');
  const url = base.endsWith('/chat/completions') ? base : `${base}/chat/completions`;
  const fetchImpl = runtime.fetch ?? fetch;
  let response: Response;
  try {
    response = await fetchImpl(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${model.token}` },
      body: JSON.stringify({ model: model.name, temperature: 0, messages: [{ role: 'user', content: prompt }] }),
      signal: AbortSignal.timeout(20000),
    });
  } catch {
    throw new EngineError('模型请求失败');
  }
  if (!response.ok) throw new EngineError('模型请求失败');
  const data = await response.json() as { choices?: { message?: { content?: string } }[] };
  const content = data.choices?.[0]?.message?.content;
  if (typeof content !== 'string' || !content.trim()) throw new EngineError('模型没有返回内容');
  return [...content].slice(0, 2000).join('');
}

async function grade(plugin: string, prompt: string, response: string, reason: string, runtime: Runtime): Promise<{ verdict: Verdict; reason: string }> {
  if (runtime.grade) return runtime.grade({ plugin, prompt, response });
  if (!response) return { verdict: 'insufficient', reason };
  return { verdict: 'insufficient', reason: reason === '已记录响应状态' ? reason : '已收到回复，尚未配置判分规则' };
}

const verdictText: Record<Verdict, string> = { pass: '通过', fail: '不通过', insufficient: '证据不足' };

function baseName(value: string): string {
  const clean = value.split('?')[0] ?? value;
  return clean.split(/[/\\]/).pop() || 'file';
}

function emit(runtime: Runtime, timeline: TimelineEvent[], event: TimelineEvent) {
  timeline.push(event);
  runtime.onEvent?.(event);
}

async function runPlugin(plugin: PluginManifest, inputs: Record<string, InputValue>, config: ScanConfig, runtime: Runtime, timeline: TimelineEvent[]) {
  const tell = (event: TimelineEvent) => emit(runtime, timeline, event);
  const model = credentials(inputs);
  const cases = plugin.id === 'model-redteam' ? generateModelCases(inputs, runtime.root) : casesFor(plugin.id, inputs);
  const strategies = plugin.id === 'model-redteam' ? strategyIds(config, inputs) : ['evidence'];
  const findings: Finding[] = [];
  tell({ type: 'step', plugin: plugin.id, title: plugin.name, status: 'doing' });
  if (plugin.id === 'infra-scan') tell({ type: 'text', plugin: plugin.id, text: /^https?:\/\//.test(text(inputs.target)) ? '正在请求目标。' : '正在登记目标。' });
  if (plugin.id === 'model-redteam') tell({ type: 'text', plugin: plugin.id, text: '按用途生成用例。' });
  if (plugin.id === 'mcp-scan') {
    tell({ type: 'text', plugin: plugin.id, text: '正在检查代码和连接地址。' });
    list(inputs.code).forEach(file => tell({ type: 'tool', plugin: plugin.id, action: '检查代码', param: baseName(file), status: 'done' }));
    if (text(inputs.endpoint)) tell({ type: 'tool', plugin: plugin.id, action: '检查地址', param: text(inputs.endpoint), status: 'done' });
    const names = headerKeys(inputs.headers);
    if (names.length > 0) tell({ type: 'tool', plugin: plugin.id, action: '记录请求头', param: names.join('、'), status: 'done' });
  }
  if (plugin.id === 'skill-scan') {
    tell({ type: 'text', plugin: plugin.id, text: '正在检查代码包。' });
    list(inputs.code).forEach(file => tell({ type: 'tool', plugin: plugin.id, action: '检查代码包', param: baseName(file), status: 'done' }));
  }
  if (plugin.id === 'agent-scan') {
    tell({ type: 'text', plugin: plugin.id, text: '正在检查接入配置。' });
    tell({ type: 'tool', plugin: plugin.id, action: '检查接入', param: text(inputs.agent), status: 'done' });
    list(inputs.code).forEach(file => tell({ type: 'tool', plugin: plugin.id, action: '检查代码包', param: baseName(file), status: 'done' }));
  }
  for (const item of cases) {
    for (const strategyId of strategies) {
      if (findings.length >= maxCases) break;
      const rendered = strategyId === 'evidence'
        ? { id: 'evidence', prompt: item.prompt, known: true }
        : applyStrategy(strategyId, item.prompt);
      let response = '';
      let reason = '已记录输入，扫描器尚未接入';
      let observedProbe: Probe | undefined;
      if (plugin.id === 'model-redteam') {
        if (!rendered.known) reason = '该变异尚未执行';
        else if (runtime.complete || model) {
          response = await completeModel(rendered.prompt, model, text(inputs.model), runtime);
          reason = response ? '已收到回复' : '未配置模型地址，用例已生成但未发送';
        } else {
          reason = '已选择模型，未提供调用地址，用例已生成但未发送';
        }
        tell({ type: 'tool', plugin: plugin.id, action: '生成用例', param: item.title, detail: item.fromDataset ? item.title : rendered.prompt, status: 'done' });
        tell({ type: 'tool', plugin: plugin.id, action: '套用策略', param: rendered.id, status: 'done' });
        if (response) {
          tell({ type: 'tool', plugin: plugin.id, action: '请求模型', param: model?.name || text(inputs.model), result: '已收到回复', detail: response, status: 'done' });
        } else {
          tell({ type: 'text', plugin: plugin.id, text: reason });
        }
      }
      if (plugin.id === 'infra-scan') {
        const observed = await observeTarget(item.prompt, runtime);
        response = observed.response;
        reason = observed.reason;
        observedProbe = observed.probe;
        tell({
          type: 'tool',
          plugin: plugin.id,
          action: /^https?:\/\//.test(item.prompt) ? '请求目标' : '登记目标',
          param: item.prompt,
          result: response || reason,
          status: 'done',
        });
      }
      if (plugin.id === 'mcp-scan' && headerKeys(inputs.headers).length > 0) {
        reason = `${reason}。请求头：${headerKeys(inputs.headers).join('、')}`;
      }
      let graded = await grade(plugin.id, rendered.prompt, response, reason, runtime);
      if (plugin.id === 'model-redteam' && !runtime.grade) graded = gradeModelReply(!!item.fromDataset, response, graded);
      if (plugin.id === 'model-redteam') tell({ type: 'tool', plugin: plugin.id, action: '判分', param: verdictText[graded.verdict], status: 'done' });
      tell({ type: 'conclusion', plugin: plugin.id, verdict: graded.verdict, reason: graded.reason });
      findings.push({
        title: item.title,
        severity: 'info',
        verdict: graded.verdict,
        strategy: rendered.id,
        prompt: rendered.prompt,
        response,
        reason: graded.reason,
      });
      if (plugin.id === 'infra-scan' && observedProbe && findings.length < maxCases) {
        matchProbe(observedProbe, runtime.root).forEach(extra => {
          if (findings.length >= maxCases) return;
          tell({
            type: 'tool',
            plugin: plugin.id,
            action: extra.strategy === 'advisory' ? '匹配漏洞' : '匹配指纹',
            param: extra.title,
            result: extra.reason,
            status: 'done',
          });
          tell({ type: 'conclusion', plugin: plugin.id, verdict: extra.verdict, reason: extra.reason });
          findings.push(extra);
        });
      }
    }
  }
  if ((plugin.id === 'mcp-scan' || plugin.id === 'agent-scan') && model && list(inputs.code).length > 0) {
    const audited = await auditDirectory({
      kind: plugin.id === 'mcp-scan' ? 'mcp' : 'agent',
      cwd: list(inputs.code)[0] || '',
      model,
      onTool: (action, param) => tell({ type: 'tool', plugin: plugin.id, action, param, status: 'done' }),
    });
    if (audited) {
      tell({ type: 'conclusion', plugin: plugin.id, verdict: audited.verdict, reason: audited.reason });
      findings.push({
        title: '代码审计',
        severity: 'info',
        verdict: audited.verdict,
        strategy: 'pi',
        prompt: baseName(list(inputs.code)[0] || ''),
        response: audited.response,
        reason: audited.reason,
      });
    }
  }
  tell({ type: 'step', plugin: plugin.id, title: plugin.name, status: 'done' });
  return { plugin: plugin.id, status: 'ok' as const, findings };
}

function aggregate(report: ScanReport): ScanReport['status'] {
  const findings = report.plugins.flatMap(item => item.findings);
  if (report.plugins.some(item => item.status === 'error')) return 'error';
  if (findings.some(item => item.verdict === 'fail')) return 'fail';
  if (findings.length > 0 && findings.every(item => item.verdict === 'pass')) return 'pass';
  return 'insufficient';
}

export async function runScan(config: ScanConfig, runtime: Runtime = {}): Promise<ScanReport> {
  const catalog = loadCatalog(runtime.root);
  const preset = config.preset ? catalog.presets.find(item => item.id === config.preset) : undefined;
  if (config.preset && !preset) throw new EngineError('未知场景');
  const pluginIds = config.plugins?.length ? config.plugins : preset?.plugins ?? [];
  if (pluginIds.length === 0) throw new EngineError('至少选择一个插件');
  if (pluginIds.some(id => !catalog.plugins.some(item => item.id === id))) throw new EngineError('未知插件');
  const inputs = config.inputs ?? {};
  assertReady(resolveFields(preset, pluginIds, catalog.plugins), inputs);
  if (pluginIds.includes('infra-scan') && !isScanTarget(text(inputs.target))) {
    throw new EngineError('请填写域名、IP、IP 段，或 http(s) 地址');
  }
  const timeline: TimelineEvent[] = [];
  const plugins = [];
  for (const id of pluginIds) {
    const plugin = catalog.plugins.find(item => item.id === id);
    if (!plugin) continue;
    plugins.push(await runPlugin(plugin, inputs, config, runtime, timeline));
  }
  const report: ScanReport = {
    id: runtime.id?.() ?? randomUUID(),
    preset: preset?.id,
    status: 'insufficient',
    plugins,
    timeline,
  };
  report.status = aggregate(report);
  return report;
}
