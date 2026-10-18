import { mkdtempSync, realpathSync, rmSync, statSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import type { ModelConfig, Verdict } from './types.js';

const toolLabel: Record<string, string> = {
  read: '读取文件',
  grep: '搜索代码',
  find: '查找文件',
  ls: '列出目录',
};

function auditRoot(path: string): string | null {
  try {
    const stat = statSync(path);
    const dir = stat.isDirectory() ? path : dirname(path);
    const resolved = realpathSync(dir);
    if (resolved === '/' || resolved.split('/').filter(Boolean).length < 2) return null;
    return resolved;
  } catch {
    return null;
  }
}

function readVerdict(text: string): { verdict: Verdict; reason: string } {
  const match = text.match(/\{[\s\S]*\}/);
  if (!match) return { verdict: 'insufficient', reason: '审计没有返回可解析的结论' };
  try {
    const parsed = JSON.parse(match[0]) as { verdict?: string; reason?: string };
    const verdict = parsed.verdict === 'pass' || parsed.verdict === 'fail' || parsed.verdict === 'insufficient' ? parsed.verdict : 'insufficient';
    return { verdict, reason: String(parsed.reason || '审计已完成').slice(0, 400) };
  } catch {
    return { verdict: 'insufficient', reason: '审计没有返回可解析的结论' };
  }
}

export async function auditDirectory(options: {
  kind: 'mcp' | 'agent';
  cwd: string;
  model: ModelConfig;
  onTool?: (action: string, param: string) => void;
}): Promise<{ verdict: Verdict; reason: string; response: string } | null> {
  const cwd = auditRoot(options.cwd);
  const baseUrl = options.model.baseUrl;
  const token = options.model.token;
  const name = options.model.name || 'audit-model';
  if (!cwd || !baseUrl || !token) return null;
  const agentDir = mkdtempSync(join(tmpdir(), 'aig-pi-'));
  try {
    const pi = await import('@earendil-works/pi-coding-agent');
    const modelRuntime = await pi.ModelRuntime.create({ refreshOnCreate: false, modelsPath: null, authPath: join(agentDir, 'auth.json') });
    modelRuntime.registerProvider('aig', {
      name: 'AIG',
      baseUrl,
      apiKey: token,
      api: 'openai-completions',
      models: [{
        id: name,
        name,
        reasoning: false,
        input: ['text'],
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
        contextWindow: 128000,
        maxTokens: 4096,
      }],
    });
    await modelRuntime.setRuntimeApiKey('aig', token);
    const model = modelRuntime.getModel('aig', name);
    if (!model) return { verdict: 'insufficient', reason: '审计模型没有就绪', response: '' };
    const loader = new pi.DefaultResourceLoader({
      cwd,
      agentDir,
      noExtensions: true,
      noSkills: true,
      noPromptTemplates: true,
      noContextFiles: true,
      systemPrompt: options.kind === 'mcp'
        ? '你是 MCP 服务的安全审计员。只使用只读工具查看代码。寻找命令执行、路径穿越、密钥硬编码和不受限制的工具权限。不要编写或演示利用方法。最后只输出 JSON：{"verdict":"pass|fail|insufficient","reason":"一句话"}。发现密钥时只写文件名，不写密钥内容。'
        : '你是 Agent 接入配置和代码的安全审计员。只使用只读工具。寻找提示词注入、工具滥用、密钥硬编码和不受信任的外部内容。不要编写或演示利用方法。最后只输出 JSON：{"verdict":"pass|fail|insufficient","reason":"一句话"}。发现密钥时只写文件名，不写密钥内容。',
    });
    await loader.reload();
    const { session } = await pi.createAgentSession({
      cwd,
      agentDir,
      model,
      modelRuntime,
      resourceLoader: loader,
      sessionManager: pi.SessionManager.inMemory(cwd),
      tools: ['read', 'grep', 'find', 'ls'],
      thinkingLevel: 'off',
    });
    let tools = 0;
    session.subscribe(event => {
      if (event.type !== 'tool_execution_start') return;
      tools += 1;
      const name = 'toolName' in event ? String(event.toolName) : '';
      const args = 'args' in event ? event.args : undefined;
      const param = args && typeof args === 'object' && 'path' in args ? String(args.path) : name;
      options.onTool?.(toolLabel[name] || '检查代码', param.split('/').pop() || param);
      if (tools >= 8) void session.abort();
    });
    await session.prompt('审计当前目录，并按约定输出 JSON 结论。');
    const messages = session.messages || [];
    const last = [...messages].reverse().find(item => item && typeof item === 'object' && 'role' in item && item.role === 'assistant');
    const content = last && 'content' in last ? last.content : '';
    const text = typeof content === 'string'
      ? content
      : Array.isArray(content) ? content.map(part => part && typeof part === 'object' && 'text' in part ? String(part.text) : '').join('') : '';
    session.dispose();
    const graded = readVerdict(text);
    return { ...graded, response: text.slice(0, 800) };
  } catch {
    return { verdict: 'insufficient', reason: '代码审计没有完成', response: '' };
  } finally {
    rmSync(agentDir, { recursive: true, force: true });
  }
}
