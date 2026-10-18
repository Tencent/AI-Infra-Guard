import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Card } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import StatusPill from './status';
import { ScanRow, TaskRow, listScans, listTasks } from './startTask';

const statusKey = (status: string) => {
  if (status === 'done') return 'done';
  if (status === 'error') return 'error';
  if (status === 'terminated') return 'terminated';
  return 'running';
};

const Records: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [scans, setScans] = useState<ScanRow[]>([]);
  const [rows, setRows] = useState<TaskRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');

  useEffect(() => {
    let cancelled = false;
    Promise.allSettled([listScans(), listTasks()])
      .then(([scanResult, taskResult]) => {
        if (cancelled) return;
        if (scanResult.status === 'fulfilled') setScans(scanResult.value);
        if (taskResult.status === 'fulfilled') setRows(taskResult.value);
        if (scanResult.status === 'rejected' && taskResult.status === 'rejected') {
          setError(scanResult.reason?.message || t('common.error'));
        }
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [t]);

  const when = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString(i18n.language?.startsWith('en') ? 'en' : 'zh-CN', { hour12: false });
  };

  const items = useMemo(() => {
    const q = query.trim().toLowerCase();
    const engine = scans.map(scan => ({
      id: scan.id,
      href: `/scan/result/${scan.id}`,
      title: scan.plugins.map(id => t(`desk.plugins.${id}.name`, { defaultValue: id })).join('、'),
      kind: t('desk.nav.scan'),
      status: scan.status,
      label: t(`desk.verdict.${scan.status}`, { defaultValue: scan.status }),
      time: scan.createdAt || '',
    }));
    const tasks = rows.map(row => ({
      id: row.id,
      href: `/records/${row.id}`,
      title: row.title,
      kind: t(`desk.taskType.${row.taskType}`, { defaultValue: row.taskType }),
      status: statusKey(row.status),
      label: t(`studio.status.${statusKey(row.status)}`),
      time: row.createdAt,
    }));
    return [...engine, ...tasks].filter(item => !q || item.title.toLowerCase().includes(q) || item.kind.toLowerCase().includes(q));
  }, [scans, rows, query, t]);

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-4 flex items-center justify-end gap-3">
        <Input value={query} onChange={event => setQuery(event.target.value)} placeholder={t('common.search')} className="h-8 w-56" />
      </div>
      {loading && <p className="text-sm text-zinc-400">{t('common.loading')}</p>}
      {!loading && error && <p className="text-sm text-red-600">{error}</p>}
      {!loading && !error && (
        <Card className="overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('desk.nav.records')}</TableHead>
                <TableHead>{t('desk.kind')}</TableHead>
                <TableHead>{t('desk.outputs.status')}</TableHead>
                <TableHead className="text-right">{t('desk.time')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map(item => (
                <TableRow key={`${item.href}-${item.id}`}>
                  <TableCell className="max-w-md font-medium">
                    <Link to={item.href} className="block truncate hover:underline">{item.title}</Link>
                  </TableCell>
                  <TableCell className="text-zinc-500">{item.kind}</TableCell>
                  <TableCell><StatusPill status={item.status} label={item.label} /></TableCell>
                  <TableCell className="text-right text-xs text-zinc-400">{when(item.time)}</TableCell>
                </TableRow>
              ))}
              {items.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="py-10 text-center text-sm text-zinc-400">{t('desk.noRecords')}</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
};

export default Records;
