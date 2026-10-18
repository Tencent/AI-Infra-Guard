import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '../components/ui/button';
import PluginOutput from './outputs';
import ScanTimeline, { type TimelineEvent } from './ScanTimeline';
import StatusPill from './status';
import { loadScan, watchScan, type EngineReport, type ScenePayload } from './startTask';

const storedReport = (): EngineReport | null => {
  try {
    const raw = sessionStorage.getItem('aig-engine-report');
    return raw ? JSON.parse(raw) as EngineReport : null;
  } catch {
    return null;
  }
};

const pendingPayload = (): { nonce: string; payload: ScenePayload } | null => {
  try {
    const raw = sessionStorage.getItem('aig-engine-pending');
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { nonce?: string; payload?: ScenePayload };
    if (!parsed.nonce || !parsed.payload) return null;
    return { nonce: parsed.nonce, payload: parsed.payload };
  } catch {
    return null;
  }
};

const ScanResult: React.FC = () => {
  const { t } = useTranslation();
  const { id } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const running = location.pathname === '/scan/run';
  const cached = storedReport();
  const initial = !running && (!id || cached?.id === id) ? cached : null;
  const [report, setReport] = useState<EngineReport | null>(initial);
  const [events, setEvents] = useState<TimelineEvent[]>(Array.isArray(initial?.timeline) ? initial.timeline : []);
  const [shown, setShown] = useState(Array.isArray(initial?.timeline) ? initial!.timeline!.length : 0);
  const [error, setError] = useState('');
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!running) return undefined;
    const payload = pendingPayload();
    if (!payload) {
      setError(t('desk.noResult'));
      return undefined;
    }
    return watchScan(payload.nonce, payload.payload, message => {
      if (message.type === 'event') setEvents(prev => [...prev, message.event]);
      if (message.type === 'report') {
        setReport(message.report);
        sessionStorage.setItem('aig-engine-report', JSON.stringify(message.report));
      }
      if (message.type === 'error') setError(message.message || t('desk.startFailed'));
    });
  }, [running, t]);

  useEffect(() => {
    if (running || !id) return undefined;
    let cancelled = false;
    loadScan(id)
      .then(item => {
        if (cancelled) return;
        setReport(item);
        setEvents(Array.isArray(item.timeline) ? item.timeline : []);
        setShown(Array.isArray(item.timeline) ? item.timeline.length : 0);
      })
      .catch(reason => { if (!cancelled) setError(reason?.message || t('desk.noResult')); });
    return () => { cancelled = true; };
  }, [id, running, t]);

  useEffect(() => {
    if (!running || shown >= events.length) return undefined;
    const timer = window.setTimeout(() => setShown(value => value + 1), shown === 0 ? 0 : 280);
    return () => window.clearTimeout(timer);
  }, [running, events.length, shown]);

  useEffect(() => {
    if (!running || !report?.id || shown < events.length) return;
    sessionStorage.removeItem('aig-engine-pending');
    navigate(`/scan/result/${report.id}`, { replace: true });
  }, [running, report, shown, events.length, navigate]);

  useEffect(() => {
    bottom.current?.scrollIntoView({ block: 'end' });
  }, [shown, events.length]);

  const visible = running ? events.slice(0, shown) : events;
  const waiting = running && shown >= events.length && !error && !report;
  const finished = !running && report && Array.isArray(report.plugins);
  const status = typeof report?.status === 'string' ? report.status : '';

  if (!running && !finished) {
    return <p className="px-6 py-10 text-sm text-zinc-500">{error || (id ? t('common.loading') : t('desk.noResult'))}</p>;
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mb-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          {status && !running && <StatusPill status={status} label={t(`desk.verdict.${status}`, { defaultValue: status })} />}
        </div>
        <Button variant="outline" className="border-blue-200 text-blue-700 hover:bg-blue-50" asChild>
          <Link to="/">{t('desk.nav.new')}</Link>
        </Button>
      </div>
      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      <ScanTimeline events={visible} waiting={waiting} />
      {finished && (
        <div className="mt-6 space-y-4">
          {report.plugins.map((item, index) => <PluginOutput key={index} data={item} />)}
        </div>
      )}
      <div ref={bottom} />
    </div>
  );
};

export default ScanResult;
