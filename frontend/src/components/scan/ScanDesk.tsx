import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { useApp } from '../../context/AppContext';
import { modelApi } from '../../lib/modelApi';
import { agentApi } from '../../lib/agentApi';
import { ModelItem } from '../../types/model';
import { Task } from '../../types';
import GuidedReport from '../report/GuidedReport';

export interface GuidedScanDraft {
  scenario: string;
  purpose: string;
  targetUrl: string;
  modelId?: string;
  agentId?: string;
  headers: { key: string; value: string }[];
  files: File[];
  plugins: string[];
  strategies: string[];
}

interface ScenarioNeeds {
  model?: boolean;
  purpose?: boolean;
  url?: boolean;
  code?: boolean;
  agent?: boolean;
  any?: string[];
}

interface CatalogScenario {
  id: string;
  name: string;
  name_en: string;
  description: string;
  description_en: string;
  needs: ScenarioNeeds;
  plugins?: string[];
  strategies?: string[];
}

interface CatalogCheck {
  id: string;
  name: string;
  name_en: string;
  severity: string;
  kind: string;
}

interface CatalogStrategy {
  id: string;
  name: string;
  name_en: string;
}

interface ScanDeskProps {
  onClose: () => void;
  onAgain: () => void;
  onStart: (draft: GuidedScanDraft) => Promise<void>;
}

const ScanDesk: React.FC<ScanDeskProps> = ({ onClose, onAgain, onStart }) => {
  const { state } = useApp();
  const task = state.tasks.find(item => item.id === state.currentTaskId);
  if (task?.type === 'Guided-Scan') {
    return <ScanRun task={task} onAgain={onAgain} />;
  }
  return <ScanSetup onClose={onClose} onStart={onStart} />;
};

const ScanRun: React.FC<{ task: Task; onAgain: () => void }> = ({ task, onAgain }) => {
  const { t } = useTranslation();
  const report = task.messages.find(item => item.guidedReport)?.guidedReport;
  const error = [...task.messages].reverse().find(item => item.type === 'error');
  const lines = task.plan.flatMap(step => (step.subSteps || []).map(item => item.brief || item.description).filter(Boolean));
  const current = lines[lines.length - 1] || task.plan.find(step => step.status === 'doing')?.title || t('scanWizard.running');

  if (report || (task.status === 'completed' && !lines.length && task.messages.some(item => item.type === 'result'))) {
    const fallback = task.messages.find(item => item.type === 'result')?.content || '';
    return (
      <div className="h-full overflow-y-auto bg-white">
        <div className="mx-auto max-w-3xl px-8 py-10">
          <button type="button" className="mb-8 text-sm text-neutral-400 hover:text-neutral-900" onClick={onAgain}>
            {t('scanWizard.again')}
          </button>
          <GuidedReport report={report} title={task.title} fallback={fallback} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-white">
      <div className="mx-auto flex w-full max-w-xl flex-1 flex-col justify-center px-8">
        <p className="text-sm text-neutral-400">{task.title}</p>
        <h1 className="mt-3 text-3xl font-medium tracking-tight text-neutral-900">
          {error ? error.content : current}
        </h1>
        <ol className="mt-10 space-y-2 text-sm text-neutral-500">
          {lines.map((line, index) => (
            <li key={`${line}-${index}`}>{line}</li>
          ))}
        </ol>
      </div>
    </div>
  );
};

const ScanSetup: React.FC<Omit<ScanDeskProps, 'onAgain'>> = ({ onClose, onStart }) => {
  const { t, i18n } = useTranslation();
  const isEn = i18n.language?.startsWith('en');
  const fileRef = useRef<HTMLInputElement>(null);
  const purposeRef = useRef<HTMLTextAreaElement>(null);
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [scenarios, setScenarios] = useState<CatalogScenario[]>([]);
  const [checks, setChecks] = useState<CatalogCheck[]>([]);
  const [strategies, setStrategies] = useState<CatalogStrategy[]>([]);
  const [scenarioId, setScenarioId] = useState('');
  const [pluginIds, setPluginIds] = useState<string[]>([]);
  const [strategyIds, setStrategyIds] = useState<string[]>([]);
  const [models, setModels] = useState<ModelItem[]>([]);
  const [agents, setAgents] = useState<string[]>([]);
  const [purpose, setPurpose] = useState('');
  const [targetUrl, setTargetUrl] = useState('');
  const [modelId, setModelId] = useState('');
  const [agentId, setAgentId] = useState('');
  const [headers, setHeaders] = useState<{ key: string; value: string }[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const [starting, setStarting] = useState(false);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const [catalogRes, modelRes, agentRes] = await Promise.all([
          fetch('/api/v1/app/catalog').then(res => res.json()),
          modelApi.getModels(),
          agentApi.getAgentNames().catch(() => ({ status: 1, data: [] as string[] })),
        ]);
        if (cancelled) return;
        if (catalogRes.status !== 0) {
          setLoadError(catalogRes.message || t('scanWizard.loadFailed'));
        } else {
          const items = (catalogRes.data?.scenarios || []) as CatalogScenario[];
          setScenarios(items);
          setChecks((catalogRes.data?.checks || []) as CatalogCheck[]);
          setStrategies((catalogRes.data?.strategies || []) as CatalogStrategy[]);
          if (items[0]) setScenarioId(items[0].id);
        }
        if (modelRes.status === 0 && modelRes.data?.[0]) {
          setModels(modelRes.data);
          setModelId(modelRes.data[0].model_id);
        }
        if (agentRes.status === 0 && agentRes.data) setAgents(agentRes.data);
      } catch {
        if (!cancelled) setLoadError(t('scanWizard.loadFailed'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [t]);

  useEffect(() => {
    const item = scenarios.find(entry => entry.id === scenarioId);
    if (!item) return;
    setPluginIds(item.plugins || []);
    setStrategyIds(item.strategies?.length ? item.strategies : ['direct']);
  }, [scenarioId, scenarios]);

  useEffect(() => {
    if (step === 2) purposeRef.current?.focus();
  }, [step]);

  const scenario = scenarios.find(item => item.id === scenarioId);
  const needs = scenario?.needs || {};
  const labelOf = (item: { name: string; name_en?: string }) => (isEn && item.name_en ? item.name_en : item.name);
  const wants = (key: string) => {
    if (key === 'model') return !!needs.model;
    if (key === 'url') return !!needs.url || !!needs.any?.includes('url');
    if (key === 'code') return !!needs.code || !!needs.any?.includes('code');
    if (key === 'agent') return !!needs.agent || !!needs.any?.includes('agent');
    return false;
  };
  const hasCode = files.length > 0 || /github\.com/i.test(targetUrl) || /github\.com/i.test(purpose);
  const hasURL = targetUrl.trim() !== '' && !/github\.com/i.test(targetUrl);
  const blockers: string[] = [];
  if (wants('model') && !modelId) blockers.push(t('scanWizard.missing.model'));
  if (needs.purpose && !purpose.trim()) blockers.push(t('scanWizard.missing.purpose'));
  if (needs.url && !hasURL) blockers.push(t('scanWizard.missing.url'));
  if (needs.code && !hasCode) blockers.push(t('scanWizard.missing.code'));
  if (needs.agent && !agentId) blockers.push(t('scanWizard.missing.agent'));
  if (needs.any?.length) {
    const ok = needs.any.some(key => (key === 'url' && hasURL) || (key === 'code' && hasCode) || (key === 'agent' && !!agentId));
    if (!ok) blockers.push(t('scanWizard.missing.any'));
  }
  if (pluginIds.length === 0) blockers.push(t('scanWizard.missing.plugins'));
  if (strategyIds.length === 0) blockers.push(t('scanWizard.missing.strategies'));

  const steps = [
    t('scanWizard.steps.scene'),
    t('scanWizard.steps.target'),
    t('scanWizard.steps.purpose'),
    t('scanWizard.steps.plugins'),
    t('scanWizard.steps.strategies'),
    t('scanWizard.steps.review'),
  ];

  const toggle = (list: string[], id: string, setList: (next: string[]) => void) => {
    setList(list.includes(id) ? list.filter(item => item !== id) : [...list, id]);
  };

  const stepBlocker = () => {
    if (step === 1 && wants('model') && !modelId) return t('scanWizard.missing.model');
    if (step === 2 && needs.purpose && !purpose.trim()) return t('scanWizard.missing.purpose');
    if (step === 3 && pluginIds.length === 0) return t('scanWizard.missing.plugins');
    if (step === 4 && strategyIds.length === 0) return t('scanWizard.missing.strategies');
    return '';
  };

  const forward = () => {
    const reason = stepBlocker();
    if (reason) {
      setNotice(reason);
      return;
    }
    setNotice('');
    setStep(value => Math.min(steps.length - 1, value + 1));
  };

  const addFiles = (list: FileList | null) => {
    if (!list) return;
    const accepted = Array.from(list).filter(file => {
      const name = file.name.toLowerCase();
      return name.endsWith('.zip') || name.endsWith('.tar.gz') || name.endsWith('.tgz') || name.endsWith('.whl') || name.endsWith('.txt') || name.endsWith('.md');
    });
    if (accepted.length !== list.length) toast.error(t('scanWizard.fileType'));
    setFiles(prev => [...prev, ...accepted]);
  };

  const start = async () => {
    if (!scenario || blockers.length > 0) {
      setNotice(blockers[0] || t('scanWizard.needScene'));
      return;
    }
    setStarting(true);
    try {
      await onStart({
        scenario: scenario.id,
        purpose: purpose.trim(),
        targetUrl: targetUrl.trim(),
        modelId: modelId || undefined,
        agentId: agentId || undefined,
        headers: headers.filter(item => item.key.trim() && item.value.trim()),
        files,
        plugins: pluginIds,
        strategies: strategyIds,
      });
    } catch (error: any) {
      toast.error(error?.message || t('scanWizard.startFailed'));
      setStarting(false);
    }
  };

  const chooseScene = (id: string) => {
    setScenarioId(id);
    setNotice('');
    setStep(1);
  };

  const modelName = models.find(item => item.model_id === modelId)?.model.model || modelId;
  const line = 'w-full border-0 border-b border-neutral-300 bg-transparent py-3 text-lg outline-none focus:border-neutral-900';

  return (
    <div className="flex h-full flex-col bg-white text-neutral-900">
      <header className="flex items-center justify-between px-8 pt-6">
        <div className="text-sm">{t('scanWizard.title')}</div>
        <button type="button" className="text-sm text-neutral-400 hover:text-neutral-900" onClick={onClose}>
          {t('common.cancel')}
        </button>
      </header>
      <nav className="flex gap-5 px-8 pb-2 pt-4 text-sm">
        {steps.map((label, index) => (
          <button
            key={label}
            type="button"
            onClick={() => { setNotice(''); setStep(index); }}
            className={index === step ? 'text-neutral-900' : 'text-neutral-300 hover:text-neutral-500'}
          >
            {index + 1} {label}
            {index === 3 && pluginIds.length > 0 ? ` ${pluginIds.length}` : ''}
            {index === 4 && strategyIds.length > 0 ? ` ${strategyIds.length}` : ''}
          </button>
        ))}
      </nav>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-xl px-8 py-12">
          {loading && <p className="text-sm text-neutral-400">{t('common.loading')}</p>}
          {!loading && loadError && <p className="text-sm text-red-700">{loadError}</p>}
          {!loading && !loadError && step === 0 && (
            <div>
              <h1 className="text-3xl font-medium tracking-tight">{t('scanWizard.sceneTitle')}</h1>
              <p className="mt-3 text-sm text-neutral-500">{t('scanWizard.sceneHelp')}</p>
              <div className="mt-8">
                {scenarios.map(item => (
                  <button key={item.id} type="button" onClick={() => chooseScene(item.id)} className="block w-full border-b border-neutral-200 py-5 text-left">
                    <div className="text-xl">{labelOf(item)}</div>
                    <div className="mt-1 text-sm text-neutral-400">{isEn && item.description_en ? item.description_en : item.description}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
          {!loading && !loadError && step === 1 && (
            <div>
              <h1 className="text-3xl font-medium tracking-tight">{t('scanWizard.targetTitle')}</h1>
              <p className="mt-3 text-sm text-neutral-500">{t('scanWizard.targetHelp')}</p>
              <div className="mt-8 space-y-6">
                {wants('model') && (
                  <label className="block text-sm text-neutral-500">
                    {t('scanWizard.model')}
                    <select value={modelId} onChange={event => setModelId(event.target.value)} className={line}>
                      <option value="">{t('scanWizard.modelEmpty')}</option>
                      {models.map(item => (
                        <option key={item.model_id} value={item.model_id}>{item.model.model}</option>
                      ))}
                    </select>
                  </label>
                )}
                {wants('url') && (
                  <label className="block text-sm text-neutral-500">
                    {t('scanWizard.url')}
                    <input value={targetUrl} onChange={event => setTargetUrl(event.target.value)} placeholder={t('scanWizard.urlPlaceholder')} className={line} onKeyDown={event => { if (event.key === 'Enter') forward(); }} />
                  </label>
                )}
                {wants('agent') && (
                  <label className="block text-sm text-neutral-500">
                    {t('scanWizard.agent')}
                    <select value={agentId} onChange={event => setAgentId(event.target.value)} className={line}>
                      <option value="">{t('scanWizard.agentEmpty')}</option>
                      {agents.map(item => <option key={item} value={item}>{item}</option>)}
                    </select>
                  </label>
                )}
                {wants('code') && (
                  <div>
                    <button type="button" className="text-sm underline" onClick={() => fileRef.current?.click()}>{t('scanWizard.chooseFile')}</button>
                    <p className="mt-1 text-xs text-neutral-400">{t('scanWizard.uploadHint')}</p>
                    <input ref={fileRef} type="file" multiple className="hidden" onChange={event => addFiles(event.target.files)} />
                    {files.map(file => (
                      <div key={file.name} className="mt-2 flex justify-between text-sm">
                        <span>{file.name}</span>
                        <button type="button" className="text-neutral-400" onClick={() => setFiles(prev => prev.filter(item => item !== file))}>×</button>
                      </div>
                    ))}
                  </div>
                )}
                {wants('url') && (
                  <div>
                    <button type="button" className="text-sm text-neutral-400 underline" onClick={() => setHeaders(prev => [...prev, { key: '', value: '' }])}>{t('scanWizard.addHeader')}</button>
                    {headers.map((header, index) => (
                      <div key={index} className="mt-2 flex gap-3">
                        <input value={header.key} onChange={event => setHeaders(prev => prev.map((item, i) => i === index ? { ...item, key: event.target.value } : item))} placeholder="Header" className="w-32 border-b border-neutral-300 py-2 text-sm outline-none" />
                        <input value={header.value} onChange={event => setHeaders(prev => prev.map((item, i) => i === index ? { ...item, value: event.target.value } : item))} placeholder="Value" className="flex-1 border-b border-neutral-300 py-2 text-sm outline-none" />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
          {!loading && !loadError && step === 2 && (
            <div>
              <h1 className="text-3xl font-medium tracking-tight">{t('scanWizard.purposeTitle')}</h1>
              <p className="mt-3 text-sm text-neutral-500">{t('scanWizard.purposeHelp')}</p>
              <textarea
                ref={purposeRef}
                value={purpose}
                onChange={event => setPurpose(event.target.value)}
                onKeyDown={event => { if (event.key === 'Enter' && (event.metaKey || event.ctrlKey)) forward(); }}
                placeholder={t('scanWizard.purposePlaceholder')}
                className="mt-8 min-h-48 w-full resize-none border-0 border-b border-neutral-300 bg-transparent text-lg outline-none focus:border-neutral-900"
              />
            </div>
          )}
          {!loading && !loadError && step === 3 && (
            <div>
              <h1 className="text-3xl font-medium tracking-tight">{t('scanWizard.pluginsTitle')}</h1>
              <p className="mt-3 text-sm text-neutral-500">{t('scanWizard.pluginsHelp')}</p>
              <div className="mt-6">
                {checks.map(item => {
                  const on = pluginIds.includes(item.id);
                  return (
                    <button key={item.id} type="button" onClick={() => toggle(pluginIds, item.id, setPluginIds)} className="flex w-full items-baseline justify-between border-b border-neutral-200 py-4 text-left">
                      <span className={on ? 'text-lg' : 'text-lg text-neutral-400'}>
                        <span className="mr-3">{on ? '●' : '○'}</span>
                        {labelOf(item)}
                      </span>
                      <span className="text-sm text-neutral-400">{t(`guidedReport.kind.${item.kind}`, { defaultValue: item.kind })}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          {!loading && !loadError && step === 4 && (
            <div>
              <h1 className="text-3xl font-medium tracking-tight">{t('scanWizard.strategiesTitle')}</h1>
              <p className="mt-3 text-sm text-neutral-500">{t('scanWizard.strategiesHelp')}</p>
              <div className="mt-6">
                {strategies.map(item => {
                  const on = strategyIds.includes(item.id);
                  return (
                    <button key={item.id} type="button" onClick={() => toggle(strategyIds, item.id, setStrategyIds)} className="flex w-full items-baseline border-b border-neutral-200 py-4 text-left text-lg">
                      <span className="mr-3">{on ? '●' : '○'}</span>
                      <span className={on ? '' : 'text-neutral-400'}>{labelOf(item)}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}
          {!loading && !loadError && step === 5 && scenario && (
            <div>
              <h1 className="text-3xl font-medium tracking-tight">{t('scanWizard.reviewTitle')}</h1>
              <p className="mt-3 text-sm text-neutral-500">{t('scanWizard.reviewHelp')}</p>
              <dl className="mt-8 space-y-4 text-sm">
                <div><dt className="text-neutral-400">{t('scanWizard.steps.scene')}</dt><dd className="mt-1 text-base">{labelOf(scenario)}</dd></div>
                <div><dt className="text-neutral-400">{t('scanWizard.model')}</dt><dd className="mt-1 text-base">{modelName || t('scanWizard.empty')}</dd></div>
                <div><dt className="text-neutral-400">{t('scanWizard.purpose')}</dt><dd className="mt-1 whitespace-pre-wrap text-base">{purpose || t('scanWizard.empty')}</dd></div>
                <div><dt className="text-neutral-400">{t('scanWizard.steps.plugins')}</dt><dd className="mt-1 text-base">{pluginIds.map(id => labelOf(checks.find(item => item.id === id) || { name: id })).join('、')}</dd></div>
                <div><dt className="text-neutral-400">{t('scanWizard.steps.strategies')}</dt><dd className="mt-1 text-base">{strategyIds.map(id => labelOf(strategies.find(item => item.id === id) || { name: id })).join('、')}</dd></div>
              </dl>
            </div>
          )}
          {notice && <p className="mt-6 text-sm text-red-700">{notice}</p>}
        </div>
      </div>
      {step > 0 && (
        <footer className="flex items-center justify-between px-8 py-5">
          <button type="button" className="text-sm text-neutral-400 hover:text-neutral-900" onClick={() => { setNotice(''); setStep(value => value - 1); }}>
            {t('common.back')}
          </button>
          {step < 5 ? (
            <button type="button" className="bg-neutral-900 px-5 py-2 text-sm text-white" onClick={forward}>
              {t('scanWizard.continue')}
            </button>
          ) : (
            <button type="button" className="bg-neutral-900 px-5 py-2 text-sm text-white disabled:bg-neutral-300" onClick={start} disabled={starting || blockers.length > 0}>
              {starting ? t('scanWizard.starting') : t('scanWizard.start')}
            </button>
          )}
        </footer>
      )}
    </div>
  );
};

export default ScanDesk;
