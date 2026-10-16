import React, { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { GuidedReportData } from '../../types';

interface GuidedReportProps {
  report?: GuidedReportData | null;
  title?: string;
  fallback?: string;
}

const GuidedReport: React.FC<GuidedReportProps> = ({ report, title, fallback }) => {
  const { t } = useTranslation();
  const [filter, setFilter] = useState<'fail' | 'all'>(report && report.fail > 0 ? 'fail' : 'all');
  const [open, setOpen] = useState<number | null>(null);

  useEffect(() => {
    setFilter(report && report.fail > 0 ? 'fail' : 'all');
    setOpen(null);
  }, [report]);

  if (!report) {
    return <p className="text-sm text-neutral-600 whitespace-pre-wrap">{fallback || t('guidedReport.empty')}</p>;
  }

  const cases = (report.cases || []).filter(item => filter === 'all' || item.verdict === 'fail');
  const verdict = t(`guidedReport.verdict.${report.verdict}`, { defaultValue: report.verdict || '' });

  return (
    <article className="text-neutral-900">
      <header className="border-b border-neutral-200 pb-6">
        {title && <p className="text-xs text-neutral-500">{title}</p>}
        <h1 className="mt-1 text-3xl font-medium tracking-tight">{verdict}</h1>
        <p className="mt-3 text-sm text-neutral-600">{report.summary}</p>
        <p className="mt-4 text-sm tabular-nums text-neutral-800">
          {t('guidedReport.counts', { total: report.total || 0, fail: report.fail || 0, pass: report.pass || 0, insufficient: report.insufficient || 0 })}
        </p>
      </header>

      <section className="mt-8">
        <h2 className="text-xs uppercase tracking-wide text-neutral-500">{t('guidedReport.plugins')}</h2>
        <div className="mt-2">
          {(report.plugins || []).map(item => (
            <div key={item.id} className="flex items-baseline justify-between border-b border-neutral-100 py-3 text-sm">
              <div>
                <span>{item.name}</span>
                {item.severity && <span className="ml-2 text-neutral-400">{t(`guidedReport.severity.${item.severity}`, { defaultValue: item.severity })}</span>}
              </div>
              <span className="tabular-nums text-neutral-600">{item.fail}/{item.total}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-8">
        <h2 className="text-xs uppercase tracking-wide text-neutral-500">{t('guidedReport.strategies')}</h2>
        <div className="mt-2">
          {(report.strategies || []).map(item => (
            <div key={item.id} className="flex items-baseline justify-between border-b border-neutral-100 py-3 text-sm">
              <span>{item.name}</span>
              <span className="tabular-nums text-neutral-600">{item.fail}/{item.total}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-8">
        <div className="flex items-center justify-between">
          <h2 className="text-xs uppercase tracking-wide text-neutral-500">{t('guidedReport.cases')}</h2>
          <div className="text-sm">
            <button type="button" className={filter === 'fail' ? 'text-neutral-900' : 'text-neutral-400'} onClick={() => setFilter('fail')}>{t('guidedReport.failedOnly')}</button>
            <span className="mx-2 text-neutral-300">/</span>
            <button type="button" className={filter === 'all' ? 'text-neutral-900' : 'text-neutral-400'} onClick={() => setFilter('all')}>{t('guidedReport.all')}</button>
          </div>
        </div>
        {cases.length === 0 && <p className="mt-4 text-sm text-neutral-500">{t('guidedReport.noCases')}</p>}
        <div className="mt-2">
          {cases.map((item, index) => {
            const expanded = open === index;
            return (
              <div key={`${item.pluginId}-${item.strategyId}-${index}`} className="border-b border-neutral-100">
                <button type="button" className="flex w-full items-baseline justify-between py-3 text-left text-sm" onClick={() => setOpen(expanded ? null : index)}>
                  <span>{item.pluginName}<span className="ml-2 text-neutral-400">{item.strategyName}</span></span>
                  <span>{t(`guidedReport.verdict.${item.verdict}`, { defaultValue: item.verdict })}</span>
                </button>
                {expanded && (
                  <div className="space-y-3 pb-4 text-sm leading-6 text-neutral-700">
                    {item.prompt && <p className="whitespace-pre-wrap">{item.prompt}</p>}
                    {item.response && <p className="whitespace-pre-wrap text-neutral-500">{item.response}</p>}
                    {item.reason && <p>{item.reason}</p>}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </article>
  );
};

export default GuidedReport;
