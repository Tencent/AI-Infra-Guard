import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { test } from 'node:test';
import { rmSync } from 'node:fs';
import { join } from 'node:path';
import { listPlugins, listPresets } from './catalog.js';
import { runScan } from './engine.js';
import { compareVersion, matchExpression } from './infra.js';
import { isScanTarget } from './target.js';
import { listReports, readReport, runsDir, saveReport } from './store.js';
import { EngineError } from './types.js';

test('catalog lists the five scan plugins and the government preset', () => {
  const plugins = listPlugins();
  assert.deepEqual(plugins.map(item => item.id).sort(), ['agent-scan', 'infra-scan', 'mcp-scan', 'model-redteam', 'skill-scan']);
  const gov = listPresets(undefined, true).find(item => item.id === 'gov');
  assert.ok(gov);
  assert.deepEqual(gov?.plugins, ['infra-scan', 'model-redteam']);
  assert.equal(gov?.require?.model, false);
});

test('government preset requires a purpose and does not require a model', async () => {
  await assert.rejects(() => runScan({ preset: 'gov', inputs: { target: '10.0.0.0/24' } }), EngineError);
  const report = await runScan({ preset: 'gov', inputs: { target: '10.0.0.0/24', purpose: '只读问答' } });
  assert.equal(report.status, 'insufficient');
  assert.deepEqual(report.plugins.map(item => item.plugin), ['infra-scan', 'model-redteam']);
  assert.equal(report.plugins[1]?.findings[0]?.prompt, '只读问答');
});

test('infrastructure scan rejects a target before scanning when the format is wrong', async () => {
  assert.equal(isScanTarget('example.com'), true);
  assert.equal(isScanTarget('10.0.0.0/24'), true);
  assert.equal(isScanTarget('https://example.test/health'), true);
  assert.equal(isScanTarget('2'), false);
  await assert.rejects(() => runScan({ plugins: ['infra-scan'], inputs: { target: '2' } }), /请填写域名、IP、IP 段，或 http\(s\) 地址/);
});

test('infrastructure scan records a range without requesting it', async () => {
  let called = false;
  const report = await runScan({
    plugins: ['infra-scan'],
    inputs: { target: '10.0.0.0/24' },
  }, {
    fetch: async () => {
      called = true;
      return new Response('');
    },
  });
  assert.equal(called, false);
  assert.equal(report.plugins[0]?.findings[0]?.reason, '已记录目标，未发起请求');
});

test('infrastructure scan records one http response and skips metadata addresses', async () => {
  const seen: string[] = [];
  const runtime = {
    fetch: async (input: RequestInfo | URL) => {
      seen.push(String(input));
      return new Response('<html></html>', { status: 200, headers: { server: 'demo' } });
    },
  };
  const report = await runScan({ plugins: ['infra-scan'], inputs: { target: 'https://example.test/health' } }, runtime);
  assert.deepEqual(seen, ['https://example.test/health']);
  assert.equal(report.plugins[0]?.findings[0]?.response, 'HTTP 200，Server demo');
  seen.length = 0;
  const blocked = await runScan({ plugins: ['infra-scan'], inputs: { target: 'http://169.254.169.254/' } }, runtime);
  assert.deepEqual(seen, []);
  assert.equal(blocked.plugins[0]?.findings[0]?.reason, '该地址不会被请求');
});

test('model cases keep the original prompt for unknown mutations and prefix the polite strategy', async () => {
  const report = await runScan({
    plugins: ['model-redteam'],
    strategies: ['direct', 'polite', 'not-a-strategy'],
    inputs: { model: 'local', purpose: '只读问答' },
  });
  const findings = report.plugins[0]?.findings ?? [];
  assert.equal(findings[0]?.prompt, '只读问答');
  assert.equal(findings[1]?.prompt, '请按既定用途回答：只读问答');
  assert.equal(findings[2]?.prompt, '只读问答');
  assert.equal(findings[2]?.reason, '该变异尚未执行');
});

test('model replies stay insufficient until a grader is configured, and secrets stay out of the report', async () => {
  const token = 'super-secret-token';
  const report = await runScan({
    plugins: ['model-redteam'],
    inputs: { model: { name: 'local', baseUrl: 'http://127.0.0.1:9/v1', token }, purpose: '只读问答' },
  }, {
    fetch: async () => new Response(JSON.stringify({ choices: [{ message: { content: '可以' } }] }), { status: 200 }),
  });
  assert.equal(report.plugins[0]?.findings[0]?.verdict, 'insufficient');
  assert.equal(report.plugins[0]?.findings[0]?.response, '可以');
  assert.equal(JSON.stringify(report).includes(token), false);
});

test('mcp accepts either code or an endpoint and only records header names', async () => {
  await assert.rejects(() => runScan({ plugins: ['mcp-scan'], inputs: {} }), EngineError);
  const secret = 'header-secret-value';
  const report = await runScan({
    plugins: ['mcp-scan'],
    inputs: { endpoint: 'https://mcp.example.test', headers: { Authorization: secret } },
  });
  assert.match(report.plugins[0]?.findings[0]?.reason ?? '', /Authorization/);
  assert.equal(JSON.stringify(report).includes(secret), false);
});

test('case generation stops at 24', async () => {
  const evals = Array.from({ length: 30 }, (_, index) => `set-${index}`);
  const report = await runScan({
    plugins: ['model-redteam'],
    inputs: { model: 'local', evals, mutations: ['direct', 'polite'] },
  });
  assert.equal(report.plugins[0]?.findings.length, 24);
});

test('a scan emits the chat timeline for each plugin', async () => {
  const seen: string[] = [];
  const report = await runScan({
    preset: 'gov',
    inputs: { target: '10.4.0.0/24', purpose: '只读问答' },
  }, { onEvent: event => { if (event.action) seen.push(event.action); } });
  assert.deepEqual(seen, ['登记目标', '生成用例', '套用策略', '判分']);
  assert.equal(report.timeline?.some(event => event.type === 'conclusion' && event.verdict === 'insufficient'), true);
});

test('a saved report can be listed and read back', async () => {
  const report = await runScan({ plugins: ['infra-scan'], inputs: { target: '10.3.0.0/24' } });
  const saved = saveReport(report);
  assert.equal(listReports().some(item => item.id === saved.id && item.plugins[0] === 'infra-scan'), true);
  assert.equal(readReport(saved.id).plugins[0]?.findings[0]?.prompt, '10.3.0.0/24');
  assert.throws(() => readReport('../secret'), EngineError);
  rmSync(join(runsDir(), `${saved.id}.json`));
});

test('version rules include a build inside the range and exclude one outside it', () => {
  const rule = 'version >= "0.5.2" && version <= "0.8.5.post1"';
  assert.equal(compareVersion('0.6.0', '0.5.2') > 0, true);
  assert.equal(matchExpression(rule, { version: '0.6.0' }), true);
  assert.equal(matchExpression(rule, { version: '0.9.0' }), false);
});

test('infrastructure scan matches the fingerprint and advisory on one response', async () => {
  const report = await runScan({
    plugins: ['infra-scan'],
    inputs: { target: 'https://example.test/version' },
  }, {
    fetch: async () => new Response('{"version":"0.6.0"}', { status: 200, headers: { server: 'uvicorn' } }),
  });
  const findings = report.plugins[0]?.findings ?? [];
  assert.equal(findings[0]?.response, 'HTTP 200，Server uvicorn');
  assert.equal(findings.some(item => item.strategy === 'fingerprint' && item.title === 'vllm'), true);
  assert.equal(findings.some(item => item.strategy === 'advisory' && item.verdict === 'fail'), true);
  assert.equal(report.status, 'fail');
});

test('model evaluation reads a dataset and grades a refusal without sending a purpose-only case', async () => {
  const report = await runScan({
    plugins: ['model-redteam'],
    inputs: { model: 'local', purpose: '只读问答', evals: ['CBRN-weapon'] },
  }, {
    complete: async () => '抱歉，我不能回答。',
  });
  const finding = report.plugins[0]?.findings[0];
  assert.equal(finding?.title, 'CBRN-weapon #1');
  assert.equal((finding?.prompt?.length ?? 0) > 20, true);
  assert.equal(finding?.verdict, 'pass');
  assert.equal(finding?.reason, '模型拒绝了该用例');
  assert.equal(finding?.prompt === '只读问答', false);
});

test('mcp keeps the evidence result when the code directory is missing', async () => {
  let called = false;
  const token = 'secret-token';
  const report = await runScan({
    plugins: ['mcp-scan'],
    inputs: { model: { name: 'local', baseUrl: 'http://127.0.0.1:9/v1', token }, code: ['/tmp/aig-missing-code-dir'] },
  }, {
    fetch: async () => {
      called = true;
      return new Response('');
    },
  });
  assert.equal(called, false);
  assert.equal(report.status, 'insufficient');
  assert.equal(JSON.stringify(report).includes(token), false);
});

test('cli prints a json report', () => {
  const result = spawnSync(process.execPath, ['dist/cli.js', 'run', '--plugins', 'infra-scan', '--set', 'target=10.1.0.0/24', '--json'], {
    cwd: new URL('..', import.meta.url),
    encoding: 'utf8',
  });
  assert.equal(result.status, 0, result.stderr);
  const report = JSON.parse(result.stdout);
  assert.equal(report.plugins[0].plugin, 'infra-scan');
  assert.equal(report.plugins[0].findings[0].prompt, '10.1.0.0/24');
  rmSync(join(runsDir(), `${report.id}.json`), { force: true });
});
