import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { modelApi } from '../lib/modelApi';
import { agentApi } from '../lib/agentApi';
import { evaluationApi } from '../lib/evaluationApi';
import FieldControl, { FieldCatalog, OptionItem } from './fields';
import {
  HeaderRow,
  InputField,
  PluginDef,
  PresetDef,
  Values,
  catalogFromApi,
  emptyValue,
  inputsReady,
  pluginById,
  plugins as fallbackPlugins,
  presets as fallbackPresets,
  resolveInputs,
} from './plugins';
import { v4 as uuidv4 } from 'uuid';
import { prepareScene } from './startTask';
import { isScanTarget } from './target';

type Tab = { key: string; kind: 'plugins' | 'inputs' | 'review' };

function inputGroups(preset: PresetDef | null, pluginIds: string[], fields: InputField[], catalog: PluginDef[]) {
  const seen = new Set<string>();
  const take = (inputs: InputField[]) => inputs.flatMap(input => {
    const field = fields.find(item => item.id === input.id);
    if (!field || seen.has(field.id)) return [];
    seen.add(field.id);
    return [field];
  });
  const groups: { id: string; fields: InputField[] }[] = [];
  const presetFields = take(preset?.inputs || []);
  if (presetFields.length > 0) groups.push({ id: 'preset', fields: presetFields });
  pluginIds.forEach(id => {
    groups.push({ id, fields: take(pluginById(id, catalog)?.inputs || []) });
  });
  return groups;
}

function labelOf(item: { name?: string; nameEn?: string } | undefined, language?: string, fallback = '') {
  if (!item) return fallback;
  if (language?.startsWith('en') && item.nameEn) return item.nameEn;
  return item.name || fallback;
}

const NewScan: React.FC = () => {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [pluginList, setPluginList] = useState<PluginDef[]>(fallbackPlugins);
  const [presetList, setPresetList] = useState<PresetDef[]>(fallbackPresets);
  const [preset, setPreset] = useState<PresetDef | null>(null);
  const [pluginIds, setPluginIds] = useState<string[]>([]);
  const [step, setStep] = useState(0);
  const [values, setValues] = useState<Values>({});
  const [catalog, setCatalog] = useState<FieldCatalog>({ models: [], agents: [], evals: [], mutations: [] });
  const [starting, setStarting] = useState(false);
  const [notice, setNotice] = useState('');
  const [targetTried, setTargetTried] = useState(false);

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
            label: item.name,
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
    fetch('/api/v1/app/catalog').then(res => res.json()).then(body => {
      const loaded = body?.status === 0 ? catalogFromApi(body.data) : null;
      if (loaded) {
        setPluginList(loaded.plugins);
        setPresetList(loaded.presets);
      }
    }).catch(() => {});
  }, [i18n.language]);

  const fields = useMemo(() => resolveInputs(preset, pluginIds, pluginList), [preset, pluginIds, pluginList]);

  useEffect(() => {
    setValues(prev => {
      const next = { ...prev };
      fields.forEach(field => {
        if (next[field.id] === undefined) next[field.id] = emptyValue(field);
      });
      return next;
    });
  }, [fields]);

  const tabs: Tab[] = useMemo(() => [
    { key: 'plugins', kind: 'plugins' },
    { key: 'inputs', kind: 'inputs' },
    { key: 'review', kind: 'review' },
  ], []);

  const index = Math.min(step, tabs.length - 1);
  const current = tabs[index];
  const ready = pluginIds.length > 0 && inputsReady(fields, values);
  const targetText = typeof values.target === 'string' ? values.target.trim() : '';
  const targetInvalid = pluginIds.includes('infra-scan') && targetText !== '' && !isScanTarget(targetText);

  const rejectTarget = () => {
    if (!targetInvalid) return false;
    setTargetTried(true);
    setNotice('');
    setStep(tabs.findIndex(tab => tab.kind === 'inputs'));
    return true;
  };

  const keepPreset = (ids: string[]) => {
    setPreset(current => (current && current.plugins.every(id => ids.includes(id)) ? current : null));
  };

  const choosePreset = (next: PresetDef) => {
    setPreset(next);
    setPluginIds(next.plugins);
    setNotice('');
  };

  const togglePlugin = (id: string) => {
    setPluginIds(prev => {
      const next = prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id];
      keepPreset(next);
      if (next.length === 0) setStep(0);
      return next;
    });
    setNotice('');
  };

  const go = (next: number) => {
    if (pluginIds.length === 0 && next > 0) return;
    if (next > index && rejectTarget()) return;
    setNotice('');
    setStep(next);
  };

  const forward = () => {
    if (current.kind === 'plugins' && pluginIds.length === 0) {
      setNotice(t('desk.needPlugins'));
      return;
    }
    if (current.kind === 'inputs' && !inputsReady(fields, values)) {
      setNotice(t('desk.needRequired'));
      return;
    }
    if (rejectTarget()) return;
    setNotice('');
    setStep(value => Math.min(tabs.length - 1, value + 1));
  };

  const begin = async () => {
    if (!ready) {
      setNotice(pluginIds.length === 0 ? t('desk.needPlugins') : t('desk.needRequired'));
      return;
    }
    if (rejectTarget()) return;
    setStarting(true);
    try {
      const payload = await prepareScene(pluginIds, values, preset?.id);
      sessionStorage.setItem('aig-engine-pending', JSON.stringify({ nonce: uuidv4(), payload }));
      navigate('/scan/run');
    } catch (error: any) {
      toast.error(error?.message || t('desk.startFailed'));
      setStarting(false);
    }
  };

  const tabOn = (tab: Tab) => {
    if (tab.kind === 'plugins') return pluginIds.length > 0;
    if (tab.kind === 'inputs') return ready;
    return ready;
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 bg-white px-6 py-4">
        <div>
          <h2 className="text-base font-semibold">{t(`desk.steps.${current.kind}`)}</h2>
          <p className="mt-1 text-sm text-zinc-500">
            {current.kind === 'plugins' ? t('desk.pickHelp') : current.kind === 'inputs' ? t('desk.inputsHelp') : t('desk.help.ready')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {tabs.map((tab, tabIndex) => {
            const locked = pluginIds.length === 0 && tabIndex > 0;
            const active = tabIndex === index;
            return (
              <button
                key={tab.key}
                type="button"
                disabled={locked}
                onClick={() => go(tabIndex)}
                className={`flex items-center gap-2 rounded-md border px-3 py-1.5 text-sm disabled:cursor-default ${active ? 'border-transparent bg-gradient-to-r from-blue-600 to-purple-600 text-white' : locked ? 'border-zinc-200 text-zinc-300' : 'border-zinc-200 bg-white text-zinc-600 hover:border-blue-300 hover:text-blue-700'}`}
              >
                <span className="tabular-nums">{tabIndex + 1}</span>
                {t(`desk.steps.${tab.kind}`)}
                {tabOn(tab) && !active && <span className="size-1.5 rounded-full bg-emerald-500" />}
              </button>
            );
          })}
        </div>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-6">
        {current.kind === 'plugins' && (
          <div className="mx-auto max-w-5xl space-y-6">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {presetList.map(item => {
                const on = preset?.id === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => choosePreset(item)}
                    className={`rounded-xl border p-4 text-left shadow-sm ${on ? 'border-transparent bg-gradient-to-br from-blue-600 to-purple-600 text-white' : 'border-zinc-200 bg-white hover:border-blue-300'}`}
                  >
                    <div className="text-sm font-medium">{labelOf(item, i18n.language, t(`desk.presets.${item.id}.name`))}</div>
                    <p className={`mt-2 text-xs leading-5 ${on ? 'text-zinc-300' : 'text-zinc-500'}`}>
                      {i18n.language?.startsWith('en') ? (item.blurbEn || t(`desk.presets.${item.id}.blurb`)) : (item.blurb || t(`desk.presets.${item.id}.blurb`))}
                    </p>
                  </button>
                );
              })}
            </div>
            <Card className="overflow-hidden">
              {pluginList.map(item => {
                const on = pluginIds.includes(item.id);
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => togglePlugin(item.id)}
                    className={`flex w-full items-center gap-3 border-b border-zinc-100 px-4 py-3 text-left last:border-0 ${on ? 'bg-gradient-to-r from-blue-50 to-purple-50' : 'bg-white hover:bg-blue-50/40'}`}
                  >
                    <span className={`flex size-4 shrink-0 items-center justify-center rounded border ${on ? 'border-blue-600 bg-gradient-to-br from-blue-600 to-purple-600 text-white' : 'border-zinc-300'}`}>
                      {on && <span className="text-[10px] leading-none">✓</span>}
                    </span>
                    <span className="min-w-0 flex-1 text-sm font-medium">{labelOf(item, i18n.language, t(`desk.plugins.${item.id}.name`))}</span>
                    <span className="flex flex-wrap justify-end gap-1.5">
                      {item.inputs.map(field => (
                        <Badge key={field.id} variant="secondary">{t(`desk.fields.${field.id}`)}</Badge>
                      ))}
                    </span>
                  </button>
                );
              })}
            </Card>
          </div>
        )}
        {current.kind === 'inputs' && (
          <div className="mx-auto max-w-3xl space-y-4">
            {inputGroups(preset, pluginIds, fields, pluginList).map(group => (
              <Card key={group.id}>
                <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm">
                    {group.id === 'preset' && preset ? labelOf(preset, i18n.language) : labelOf(pluginById(group.id, pluginList), i18n.language, t(`desk.plugins.${group.id}.name`))}
                  </CardTitle>
                  {group.id !== 'preset' && (
                    <button type="button" className="text-xs text-zinc-400 hover:text-blue-700" onClick={() => togglePlugin(group.id)}>{t('desk.removePlugin')}</button>
                  )}
                </CardHeader>
                <CardContent className="space-y-5">
                  {group.fields.map(field => (
                    <div key={field.id}>
                      <div className="flex items-center gap-2 text-sm font-medium">
                        {t(`desk.fields.${field.id}`)}
                        {field.required && <span className="text-red-500">*</span>}
                        {field.anyOf && <Badge variant="secondary">{t('desk.anyOf')}</Badge>}
                      </div>
                      <p className="mt-1 text-xs text-zinc-500">{t(`desk.fieldHelp.${field.id}`)}</p>
                      <FieldControl field={field} values={values} setValues={next => { setTargetTried(false); setNotice(''); setValues(next); }} catalog={catalog} />
                      {field.id === 'target' && targetTried && targetInvalid && <p className="mt-2 text-sm text-red-600">{t('desk.targetFormat')}</p>}
                    </div>
                  ))}
                </CardContent>
              </Card>
            ))}
          </div>
        )}
        {current.kind === 'review' && (
          <div className="mx-auto grid max-w-5xl gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="text-sm">{t('desk.steps.plugins')}</CardTitle></CardHeader>
              <CardContent className="space-y-3 text-sm">
                <div className="flex flex-wrap gap-1.5">
                  {pluginIds.map(id => <Badge key={id} variant="secondary">{labelOf(pluginById(id, pluginList), i18n.language, t(`desk.plugins.${id}.name`))}</Badge>)}
                </div>
                {fields.map(field => (
                  <div key={field.id} className="border-t border-zinc-100 pt-3">
                    <div className="text-xs text-zinc-400">{t(`desk.fields.${field.id}`)}</div>
                    <div className="mt-1 whitespace-pre-wrap">{displayValue(field, values, catalog, t) || t('desk.empty')}</div>
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="text-sm">{t('desk.outputsTitle')}</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                {pluginIds.map(id => {
                  const plugin = pluginById(id, pluginList);
                  if (!plugin) return null;
                  return (
                    <div key={id} className="flex items-center justify-between gap-3 border-b border-zinc-100 pb-3 last:border-0 last:pb-0">
                      <span className="text-sm">{labelOf(plugin, i18n.language, t(`desk.plugins.${id}.name`))}</span>
                      <span className="text-xs text-zinc-400">{plugin.outputs.map(field => t(`desk.outputs.${field.type}`)).join('、')}</span>
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          </div>
        )}
        {notice && <p className="mx-auto mt-4 max-w-5xl text-sm text-red-600">{notice}</p>}
      </div>
      <footer className="flex items-center justify-between border-t border-zinc-200 bg-white px-6 py-3">
        <Button variant="outline" disabled={index === 0} onClick={() => go(Math.max(0, index - 1))}>{t('desk.back')}</Button>
        {current.kind === 'review' ? (
          <Button className="border-transparent bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-500 hover:to-purple-500" onClick={begin} disabled={starting || !ready}>{starting ? t('desk.starting') : t('desk.start')}</Button>
        ) : (
          <Button className="border-transparent bg-gradient-to-r from-blue-600 to-purple-600 text-white hover:from-blue-500 hover:to-purple-500" onClick={forward}>{t('desk.next')}</Button>
        )}
      </footer>
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
