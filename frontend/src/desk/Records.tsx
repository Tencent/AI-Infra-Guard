import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { TaskRow, listTasks } from './startTask';

const statusKey = (status: string) => {
  if (status === 'done') return 'done';
  if (status === 'error') return 'error';
  if (status === 'terminated') return 'terminated';
  return 'running';
};

const Records: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [rows, setRows] = useState<TaskRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    listTasks()
      .then(items => { if (!cancelled) setRows(items); })
      .catch(reason => { if (!cancelled) setError(reason?.message || t('common.error')); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [t]);

  const when = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString(i18n.language?.startsWith('en') ? 'en' : 'zh-CN', { hour12: false });
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-8 py-12">
        <h1 className="text-2xl font-medium">{t('desk.nav.records')}</h1>
        {loading && <p className="mt-8 text-sm text-gray-400">{t('common.loading')}</p>}
        {!loading && error && <p className="mt-8 text-sm text-red-600">{error}</p>}
        {!loading && !error && rows.length === 0 && <p className="mt-8 text-sm text-gray-500">{t('desk.noRecords')}</p>}
        <div className="mt-6 overflow-hidden rounded-lg border border-gray-200 bg-white">
          {rows.map(row => (
            <Link key={row.id} to={`/records/${row.id}`} className="flex items-baseline justify-between gap-4 border-b border-gray-100 px-4 py-3 last:border-0 hover:bg-gray-50">
              <span className="min-w-0">
                <span className="block truncate text-sm">{row.title}</span>
                <span className="text-xs text-gray-400">{t(`desk.taskType.${row.taskType}`, { defaultValue: row.taskType })}</span>
              </span>
              <span className="shrink-0 text-xs text-gray-400">
                {t(`studio.status.${statusKey(row.status)}`)}
                {row.createdAt ? ` · ${when(row.createdAt)}` : ''}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Records;
