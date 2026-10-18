import React from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { HeaderRow, InputField, Values } from './plugins';

export interface OptionItem {
  id: string;
  label: string;
}

export interface FieldCatalog {
  models: OptionItem[];
  agents: OptionItem[];
  evals: OptionItem[];
  mutations: OptionItem[];
}

const line = 'mt-2 w-full rounded-md border border-gray-200 bg-white px-3 py-2 text-sm outline-none focus:border-blue-500';

const acceptFile = (file: File) => {
  const name = file.name.toLowerCase();
  return name.endsWith('.zip') || name.endsWith('.tar.gz') || name.endsWith('.tgz') || name.endsWith('.whl') || name.endsWith('.txt') || name.endsWith('.md');
};

const FieldControl: React.FC<{
  field: InputField;
  values: Values;
  setValues: React.Dispatch<React.SetStateAction<Values>>;
  catalog: FieldCatalog;
}> = ({ field, values, setValues, catalog }) => {
  const { t } = useTranslation();
  const set = (value: Values[string]) => setValues(prev => ({ ...prev, [field.id]: value }));

  if (field.type === 'model' || field.type === 'agent') {
    const options = field.type === 'model' ? catalog.models : catalog.agents;
    const current = typeof values[field.id] === 'string' ? values[field.id] as string : '';
    return (
      <select className={line} value={current} onChange={event => set(event.target.value)}>
        <option value="">{field.type === 'model' ? t('desk.chooseModel') : t('desk.chooseAgent')}</option>
        {options.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
      </select>
    );
  }

  if (field.type === 'textarea') {
    const current = typeof values[field.id] === 'string' ? values[field.id] as string : '';
    return <textarea className={`${line} min-h-40`} value={current} onChange={event => set(event.target.value)} placeholder={t('scanWizard.purposePlaceholder')} />;
  }

  if (field.type === 'text') {
    const current = typeof values[field.id] === 'string' ? values[field.id] as string : '';
    const placeholder = field.id === 'endpoint' ? t('desk.endpointPlaceholder') : t('desk.targetPlaceholder');
    return <input className={line} value={current} onChange={event => set(event.target.value)} placeholder={placeholder} />;
  }

  if (field.type === 'files') {
    const files = Array.isArray(values[field.id]) ? values[field.id] as File[] : [];
    const add = (list: FileList | null) => {
      if (!list) return;
      const accepted = Array.from(list).filter(acceptFile);
      if (accepted.length !== list.length) toast.error(t('scanWizard.fileType'));
      set([...files, ...accepted]);
    };
    return (
      <div>
        <label className="inline-block cursor-pointer text-sm text-blue-600">
          {t('scanWizard.chooseFile')}
          <input type="file" multiple className="hidden" onChange={event => add(event.target.files)} />
        </label>
        {files.map(file => (
          <div key={file.name} className="mt-2 flex justify-between text-sm">
            <span>{file.name}</span>
            <button type="button" className="text-gray-400" onClick={() => set(files.filter(item => item !== file))}>×</button>
          </div>
        ))}
      </div>
    );
  }

  if (field.type === 'headers') {
    const rows = Array.isArray(values[field.id]) ? values[field.id] as HeaderRow[] : [];
    const edit = (index: number, key: 'key' | 'value', next: string) => {
      set(rows.map((row, i) => i === index ? { ...row, [key]: next } : row));
    };
    return (
      <div>
        {rows.map((row, index) => (
          <div key={index} className="mt-2 flex gap-2">
            <input className="w-36 rounded-md border border-gray-200 px-3 py-2 text-sm" placeholder="Header" value={row.key} onChange={event => edit(index, 'key', event.target.value)} />
            <input className="flex-1 rounded-md border border-gray-200 px-3 py-2 text-sm" placeholder="Value" value={row.value} onChange={event => edit(index, 'value', event.target.value)} />
          </div>
        ))}
        <button type="button" className="mt-2 text-sm text-blue-600" onClick={() => set([...rows, { key: '', value: '' }])}>{t('scanWizard.addHeader')}</button>
      </div>
    );
  }

  const options = field.source === 'mutations' ? catalog.mutations : catalog.evals;
  const selected = Array.isArray(values[field.id]) ? values[field.id] as string[] : [];
  return (
    <div className="mt-2 flex max-h-40 flex-wrap gap-1.5 overflow-y-auto rounded-md border border-zinc-200 bg-zinc-50 p-2">
      {options.map(item => {
        const on = selected.includes(item.id);
        return (
          <button
            key={item.id}
            type="button"
            title={item.label}
            className={`rounded-md border px-2 py-1 text-xs ${on ? 'border-transparent bg-gradient-to-r from-blue-600 to-purple-600 text-white' : 'border-zinc-200 bg-white text-zinc-600 hover:border-blue-300 hover:text-blue-700'}`}
            onClick={() => set(on ? selected.filter(id => id !== item.id) : [...selected, item.id])}
          >
            {item.label}
          </button>
        );
      })}
      {options.length === 0 && <p className="text-sm text-gray-400">{field.source === 'mutations' ? t('desk.noMutations') : t('desk.noEvals')}</p>}
    </div>
  );
};

export default FieldControl;
