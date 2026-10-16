import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { EvalRow, listEvals } from './run';

const Evals: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [rows, setRows] = useState<EvalRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    listEvals()
      .then(items => {
        if (!cancelled) setRows(items);
      })
      .catch(reason => {
        if (!cancelled) setError(reason?.message || t('common.error'));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [t]);

  const when = (value: string) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString(i18n.language?.startsWith('en') ? 'en' : 'zh-CN', { hour12: false });
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-3xl px-8 py-12">
        <h1 className="text-3xl font-medium tracking-tight">{t('studio.evals')}</h1>
        {loading && <p className="mt-8 text-sm text-neutral-400">{t('common.loading')}</p>}
        {!loading && error && <p className="mt-8 text-sm text-red-700">{error}</p>}
        {!loading && !error && rows.length === 0 && (
          <div className="mt-8">
            <p className="text-sm text-neutral-500">{t('studio.empty')}</p>
            <Link to="/" className="mt-4 inline-block text-sm underline">
              {t('studio.newScan')}
            </Link>
          </div>
        )}
        {!loading && !error && rows.length > 0 && (
          <div className="mt-8">
            {rows.map(row => (
              <Link key={row.id} to={`/eval/${row.id}`} className="flex items-baseline justify-between gap-6 border-b border-neutral-200 py-4">
                <span className="min-w-0 truncate text-base">{row.title}</span>
                <span className="shrink-0 text-sm text-neutral-400">
                  {t(`studio.status.${row.status}`)}
                  {row.createdAt ? ` · ${when(row.createdAt)}` : ''}
                </span>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Evals;
