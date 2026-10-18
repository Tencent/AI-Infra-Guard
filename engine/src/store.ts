import { mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { findRepoRoot } from './catalog.js';
import { EngineError, type ScanReport } from './types.js';

const idPattern = /^[0-9a-f-]{36}$/i;

export function runsDir(root = findRepoRoot()): string {
  return join(root, 'engine', 'runs');
}

export function saveReport(report: ScanReport, root?: string): ScanReport {
  if (!idPattern.test(report.id)) throw new EngineError('扫描编号不正确');
  const dir = runsDir(root);
  mkdirSync(dir, { recursive: true });
  const stamped: ScanReport = { ...report, createdAt: report.createdAt || new Date().toISOString() };
  writeFileSync(join(dir, `${stamped.id}.json`), JSON.stringify(stamped));
  return stamped;
}

export interface ScanSummary {
  id: string;
  status: ScanReport['status'];
  preset?: string;
  plugins: string[];
  createdAt?: string;
}

export function listReports(root?: string): ScanSummary[] {
  const dir = runsDir(root);
  let names: string[] = [];
  try {
    names = readdirSync(dir).filter(name => name.endsWith('.json'));
  } catch {
    return [];
  }
  const rows = names.flatMap((name): ScanSummary[] => {
    try {
      const report = JSON.parse(readFileSync(join(dir, name), 'utf8')) as ScanReport;
      if (!report?.id || !idPattern.test(report.id)) return [];
      return [{
        id: report.id,
        status: report.status,
        preset: report.preset,
        plugins: (report.plugins || []).map(item => item.plugin),
        createdAt: report.createdAt,
      }];
    } catch {
      return [];
    }
  });
  return rows.sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''));
}

export function readReport(id: string, root?: string): ScanReport {
  if (!idPattern.test(id)) throw new EngineError('扫描编号不正确');
  try {
    const report = JSON.parse(readFileSync(join(runsDir(root), `${id}.json`), 'utf8')) as ScanReport;
    if (!report?.id) throw new Error('empty');
    return report;
  } catch (error) {
    if (error instanceof EngineError) throw error;
    throw new EngineError('没有这次扫描');
  }
}
