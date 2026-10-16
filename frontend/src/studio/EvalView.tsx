import React, { useEffect, useSyncExternalStore } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import GuidedReport from '../components/report/GuidedReport';
import PluginOutput from '../desk/outputs';
import { getRun, hydrate, markFailed, subscribeRun } from './run';

const EvalView: React.FC = () => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { t } = useTranslation();
  const run = useSyncExternalStore(
    listener => (sessionId ? subscribeRun(sessionId, listener) : () => {}),
    () => (sessionId ? getRun(sessionId) : undefined),
    () => (sessionId ? getRun(sessionId) : undefined),
  );

  useEffect(() => {
    if (!sessionId) return;
    hydrate(sessionId).catch(reason => markFailed(sessionId, reason?.message || ''));
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId || run?.status !== 'running') return;
    const timer = window.setInterval(() => {
      hydrate(sessionId).catch(() => {});
    }, 2000);
    return () => window.clearInterval(timer);
  }, [sessionId, run?.status]);

  if (!run) {
    return <p className="px-8 py-12 text-sm text-neutral-400">{t('common.loading')}</p>;
  }

  if (run.report || run.status === 'done') {
    return (
      <div className="h-full overflow-y-auto">
        <div className="mx-auto max-w-3xl px-8 py-10">
          <Link to="/" className="text-sm text-neutral-400 hover:text-neutral-900">
            {t('scanWizard.again')}
          </Link>
          <div className="mt-8">
            {run.output ? <PluginOutput data={run.output} /> : <GuidedReport report={run.report} title={run.title} fallback={run.fallback || run.error} />}
          </div>
        </div>
      </div>
    );
  }

  const current = run.status === 'error'
    ? (run.error || t('common.error'))
    : (run.lines[run.lines.length - 1] || t('scanWizard.running'));
  return (
    <div className="flex h-full flex-col">
      <div className="mx-auto flex w-full max-w-xl flex-1 flex-col justify-center px-8">
        <p className="text-sm text-neutral-400">{run.title}</p>
        <h1 className="mt-3 text-3xl font-medium tracking-tight">{current}</h1>
        <ol className="mt-10 space-y-2 text-sm text-neutral-500">
          {run.lines.map((line, index) => (
            <li key={`${line}-${index}`}>{line}</li>
          ))}
        </ol>
      </div>
    </div>
  );
};

export default EvalView;
