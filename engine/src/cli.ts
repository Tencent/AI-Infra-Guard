#!/usr/bin/env node
import { readFileSync, writeSync } from 'node:fs';
import { parseArgs } from 'node:util';
import { parse } from 'yaml';
import { listPlugins, listPresets } from './catalog.js';
import { runScan } from './engine.js';
import { startServer } from './server.js';
import { listReports, readReport, saveReport } from './store.js';
import { EngineError, type InputValue, type ScanConfig, type TimelineEvent } from './types.js';

function emitLine(value: unknown) {
  writeSync(1, `${JSON.stringify(value)}\n`);
}

function fail(error: unknown): never {
  const message = error instanceof EngineError ? error.message : '扫描失败';
  emitLine({ error: message });
  process.exitCode = 1;
  return process.exit(1);
}

function readConfig(path: string | undefined): ScanConfig {
  if (!path) return {};
  const raw = path === '-' ? readFileSync(0, 'utf8') : readFileSync(path, 'utf8');
  const parsed = path.endsWith('.json') || path === '-' ? JSON.parse(raw) : parse(raw);
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new EngineError('配置格式不正确');
  return parsed as ScanConfig;
}

function applySet(config: ScanConfig, items: string[]) {
  config.inputs = config.inputs ?? {};
  for (const item of items) {
    const eq = item.indexOf('=');
    if (eq <= 0) throw new EngineError('--set 需要 key=value');
    const key = item.slice(0, eq);
    const value = item.slice(eq + 1);
    if (key === 'headers') throw new EngineError('请求头请写在配置文件里');
    if (key === 'evals' || key === 'mutations' || key === 'code') {
      config.inputs[key] = value.split(',').map(part => part.trim()).filter(Boolean);
    } else {
      config.inputs[key] = value as InputValue;
    }
  }
}

async function serve(port: number) {
  const { port: bound } = await startServer(port);
  process.stdout.write(`listening ${bound}\n`);
}

async function main() {
  const args = parseArgs({
    allowPositionals: true,
    options: {
      config: { type: 'string' },
      plugins: { type: 'string' },
      preset: { type: 'string' },
      set: { type: 'string', multiple: true },
      json: { type: 'boolean', default: false },
      stream: { type: 'boolean', default: false },
      port: { type: 'string', default: '8088' },
    },
  });
  const command = args.positionals[0] || 'run';
  if (command === 'plugins') {
    process.stdout.write(`${JSON.stringify(listPlugins(), null, args.values.json ? undefined : 2)}\n`);
    return;
  }
  if (command === 'presets') {
    process.stdout.write(`${JSON.stringify(listPresets(undefined, true), null, args.values.json ? undefined : 2)}\n`);
    return;
  }
  if (command === 'runs') {
    process.stdout.write(`${JSON.stringify(listReports(), null, args.values.json ? undefined : 2)}\n`);
    return;
  }
  if (command === 'show') {
    const report = readReport(args.positionals[1] || '');
    process.stdout.write(`${JSON.stringify(report, null, args.values.json ? undefined : 2)}\n`);
    return;
  }
  if (command === 'serve') {
    await serve(Number(args.values.port) || 8090);
    return;
  }
  if (command !== 'run') throw new EngineError('未知命令');
  const config = readConfig(args.values.config);
  if (args.values.plugins) config.plugins = args.values.plugins.split(',').map(item => item.trim()).filter(Boolean);
  if (args.values.preset) config.preset = args.values.preset;
  if (args.values.set?.length) applySet(config, args.values.set);
  if (args.values.stream) {
    const report = saveReport(await runScan(config, {
      onEvent: (event: TimelineEvent) => emitLine({ type: 'event', event }),
    }));
    emitLine({ type: 'report', report });
    return;
  }
  const report = saveReport(await runScan(config));
  process.stdout.write(`${JSON.stringify(report, null, args.values.json ? undefined : 2)}\n`);
}

main().catch(fail);
