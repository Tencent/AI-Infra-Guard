import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { modelApi } from '../lib/modelApi';
import { agentApi } from '../lib/agentApi';
import { evaluationApi } from '../lib/evaluationApi';
import FieldControl, { FieldCatalog, OptionItem } from './fields';
import {
  HeaderRow,
  InputField,
  PresetDef,
  Values,
  emptyValue,
  fieldFilled,
  inputsReady,
  pluginById,
  plugins,
  presets,
  resolveInputs,
} from './plugins';
import { startScene } from './startTask';

type Tab =
  | { key: string; kind: 'scene' | 'plugins' | 'review'; field?: undefined }
  | { key: string; kind: 'field'; field: InputField };

const NewScan: React.FC = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [preset, setPreset] = useState<PresetDef | null>(null);
  const [pluginIds, setPluginIds] = useState<string[]>([]);
  const [step, setStep] = useState(0);
  const [values, setValues] = useState<Values>({});
  const [catalog, setCatalog] = useState<FieldCatalog>({ models: [], agents: [], evals: [], mutations: [] });
  const [starting, setStarting] = useState(false);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    const en = i18n.language?.startsWith('en');
    modelApi.getModels().then(res => {
      if (res.status === 0 && res.data) {
        setCatalog(prev => ({
          ...prev,
          models: res.data.filter(item => item?.model_id && item.model).map(item => ({ id: item.model_id, label: item.model.model })),
        }));
      }
    }).catch(() => {});
    agentApi.getAgentNames().then(res => {
      if (res.status === 0 && res.data) {
        setCatalog(prev => ({ ...prev, agents: res.data.map(name => ({ id: name, label: name })) }));
      }
    }).catch(() => {});
    evaluationApi.getEvaluations({ page: 1, size: 100 }).then(res => {
      if (res.status === 0) {
        setCatalog(prev => ({
          ...prev,
          evals: (res.data?.items || []).map(item => ({
            id: item.name,
            label: en ? item.name : (item.description_zh || item.name),
          })),
        }));
      }
    }).catch(() => {});
    fetch('/api/v1/knowledge/jailbreak').then(res => res.json()).then(body => {
      const methods = (body?.data?.configSchema?.strategies || []).flatMap((group: { methods?: { id: string; type?: string; typeCn?: string }[] }) => group.methods || []);
      const mutations: OptionItem[] = methods
        .filter((item: { id?: string }) => item?.id)
        .map((item: { id: string; type?: string; typeCn?: string }) => ({ id: item.id, label: en ? (item.type || item.id) : (item.typeCn || item.type || item.id) }));
      setCatalog(prev => ({ ...prev, mutations }));
    }).catch(() => {});
  }, [i18n.language]);

  const fields = useMemo(() => resolveInputs(preset, pluginIds), [preset, pluginIds]);

  useEffect(() => {
    setValues(prev => {
      const next = { ...prev };
      fields.forEach(field => {
        if (next[field.id] === undefined) next[field.id] = emptyValue(field);
      });
      return next;
    });
  }, [fields]);

  const tabs: Tab[] = useMemo(() => {
    const head: Tab[] = [{ key: 'scene', kind: 'scene' }, { key: 'plugins', kind: 'plugins' }];
    return [...head, ...fields.map(field => ({ key: field.id, kind: 'field' as const, field })), { key: 'review', kind: 'review' }];
  }, [fields]);

  const index = Math.min(step, tabs.length - 1);
  const current = tabs[index];
  const ready = pluginIds.length > 0 && inputsReady(fields, values);

  const choosePreset = (next: PresetDef) => {
    setPreset(next);
    setPluginIds(next.plugins);
    setNotice('');
    setStep(1);
  };

  const togglePlugin = (id: string) => {
    setPluginIds(prev => prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]);
    setNotice('');
  };

  const go = (next: number) => {
    if (!preset && next > 0) return;
    setNotice('');
    setStep(next);
  };

  const forward = () => {
    if (current.kind === 'scene' && !preset) {
      setNotice(t('desk.needScene'));
      return;
    }
    if (current.kind === 'plugins' && pluginIds.length === 0) {
      setNotice(t('desk.needPlugins'));
      return;
    }
    if (current.kind === 'field' && current.field.required && !current.field.anyOf && !fieldFilled(current.field, values)) {
      setNotice(t('desk.needRequired'));
      return;
    }
    setNotice('');
    setStep(value => Math.min(tabs.length - 1, value + 1));
  };

  const begin = async () => {
    if (!ready) {
      setNotice(pluginIds.length === 0 ? t('desk.needPlugins') : t('desk.needRequired'));
      return;
    }
    setStarting(true);
    try {
      const { ids, errors } = await startScene(pluginIds, values, i18n.language);
      if (errors.length > 0) toast.error(errors[0] || t('desk.startFailed'));
      navigate(ids.length === 1 ? `/records/${ids[0]}` : '/records');
    } catch (error: any) {
      toast.error(error?.message || t('desk.startFailed'));
      setStarting(false);
    }
  };

  const tabLabel = (tab: Tab) => {
    if (tab.kind === 'field') return t(`desk.fields.${tab.field.id}`);
    return t(`desk.steps.${tab.kind}`);
  };

  const tabOn = (tab: Tab) => {
    if (tab.kind === 'scene') return preset != null;
    if (tab.kind === 'plugins') return pluginIds.length > 0;
    if (tab.kind === 'review') return ready;
    return tab.field ? fieldFilled(tab.field, values) : false;
  };

  return (
    <div className="flex h-full">
      <nav className="flex w-52 shrink-0 flex-col border-r border-gray-200 bg-white px-4 py-6">
        {tabs.map((tab, tabIndex) => {
          const locked = !preset && tabIndex > 0;
          const active = tabIndex === index;
          return (
            <button
              key={tab.key}
              type="button"
              disabled={locked}
              onClick={() => go(tabIndex)}
              className={`flex items-center gap-3 rounded-md px-3 py-2 text-left text-sm disabled:cursor-default ${active ? 'bg-blue-50 text-blue-600' : locked ? 'text-gray-300' : 'text-gray-600 hover:bg-gray-50'}`}
            >
              <span className="w-4 tabular-nums">{tabIndex + 1}</span>
              <span className="min-w-0 flex-1 truncate">{tabLabel(tab)}</span>
              {tabOn(tab) && <span className="text-xs text-blue-600">●</span>}
            </button>
          );
        })}
      </nav>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-xl px-8 py-10">
            {current.kind === 'scene' && (
              <div>
                <h1 className="text-2xl font-medium">{t('desk.pick')}</h1>
                <p className="mt-2 text-sm text-gray-500">{t('desk.pickHelp')}</p>
                <div className="mt-6 space-y-2">
                  {presets.map(item => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => choosePreset(item)}
                      className={`block w-full rounded-lg border px-4 py-4 text-left ${preset?.id === item.id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white hover:border-blue-400'}`}
                    >
                      <div className="text-sm font-medium">{t(`desk.presets.${item.id}.name`)}</div>
                      <div className="mt-1 text-sm text-gray-500">{t(`desk.presets.${item.id}.blurb`)}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}
            {current.kind === 'plugins' && (
              <div>
                <h1 className="text-2xl font-medium">{t('desk.steps.plugins')}</h1>
                <p className="mt-2 text-sm text-gray-500">{t('desk.pluginsHelp')}</p>
                <div className="mt-6">
                  {plugins.map(item => {
                    const on = pluginIds.includes(item.id);
                    return (
                      <button key={item.id} type="button" onClick={() => togglePlugin(item.id)} className="flex w-full items-start gap-3 border-b border-gray-100 py-4 text-left">
                        <span className={on ? 'text-blue-600' : 'text-gray-300'}>{on ? '●' : '○'}</span>
                        <span>
                          <span className="block text-sm">{t(`desk.plugins.${item.id}.name`)}</span>
                          <span className="mt-1 block text-xs text-gray-400">
                            {item.inputs.map(field => t(`desk.fields.${field.id}`)).join('、')}
                            {' → '}
                            {item.outputs.map(field => t(`desk.outputs.${field.type}`)).join('、')}
                          </span>
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}
            {current.kind === 'field' && (
              <div>
                <h1 className="text-2xl font-medium">{t(`desk.fields.${current.field.id}`)}</h1>
                <p className="mt-2 text-sm text-gray-500">{t(`desk.fieldHelp.${current.field.id}`)}</p>
                {!current.field.required && !current.field.anyOf && <p className="mt-1 text-xs text-gray-400">{t('desk.optional')}</p>}
                {current.field.anyOf && <p className="mt-1 text-xs text-gray-400">{t('desk.anyOf')}</p>}
                <div className="mt-6">
                  <FieldControl field={current.field} values={values} setValues={setValues} catalog={catalog} />
                </div>
              </div>
            )}
            {current.kind === 'review' && (
              <div>
                <h1 className="text-2xl font-medium">{t('desk.steps.review')}</h1>
                <p className="mt-2 text-sm text-gray-500">{t('desk.help.ready')}</p>
                <dl className="mt-6 space-y-4 text-sm">
                  <div>
                    <dt className="text-gray-400">{t('desk.steps.plugins')}</dt>
                    <dd className="mt-1">{pluginIds.map(id => t(`desk.plugins.${id}.name`)).join('、') || t('desk.empty')}</dd>
                  </div>
                  {fields.map(field => (
                    <div key={field.id}>
                      <dt className="text-gray-400">{t(`desk.fields.${field.id}`)}</dt>
                      <dd className="mt-1 whitespace-pre-wrap">{displayValue(field, values, catalog, t) || t('desk.empty')}</dd>
                    </div>
                  ))}
                </dl>
                <div className="mt-8">
                  <h2 className="text-xs uppercase tracking-wide text-gray-400">{t('desk.outputsTitle')}</h2>
                  {pluginIds.map(id => {
                    const plugin = pluginById(id);
                    if (!plugin) return null;
                    return (
                      <p key={id} className="mt-3 text-sm">
                        {t(`desk.plugins.${id}.name`)}
                        <span className="ml-2 text-gray-400">{plugin.outputs.map(field => t(`desk.outputs.${field.type}`)).join('、')}</span>
                      </p>
                    );
                  })}
                </div>
              </div>
            )}
            {notice && <p className="mt-6 text-sm text-red-600">{notice}</p>}
          </div>
        </div>
        <footer className="flex items-center justify-between border-t border-gray-200 bg-white px-8 py-4">
          <button type="button" className="text-sm text-gray-400 hover:text-gray-900 disabled:invisible" disabled={index === 0} onClick={() => go(Math.max(0, index - 1))}>
            {t('desk.back')}
          </button>
          {current.kind === 'review' ? (
            <Button onClick={begin} disabled={starting || !ready}>{starting ? t('desk.starting') : t('desk.start')}</Button>
          ) : (
            <Button onClick={forward}>{t('desk.next')}</Button>
          )}
        </footer>
      </div>
    </div>
  );
};

const displayValue = (field: InputField, values: Values, catalog: FieldCatalog, t: (key: string, opts?: Record<string, unknown>) => string) => {
  const value = values[field.id];
  if (field.type === 'headers') {
    const count = Array.isArray(value) ? (value as HeaderRow[]).filter(row => row.key.trim() && row.value.trim()).length : 0;
    return count > 0 ? t('desk.headerCount', { count }) : '';
  }
  if (field.type === 'files') return Array.isArray(value) ? (value as File[]).map(file => file.name).join('、') : '';
  if (field.type === 'multi') {
    const ids = Array.isArray(value) ? value as string[] : [];
    const options = field.source === 'mutations' ? catalog.mutations : catalog.evals;
    return ids.map(id => options.find(item => item.id === id)?.label || id).join('、');
  }
  if (field.type === 'model') {
    const id = typeof value === 'string' ? value : '';
    return catalog.models.find(item => item.id === id)?.label || id;
  }
  return typeof value === 'string' ? value.trim() : '';
};

export default NewScan;
