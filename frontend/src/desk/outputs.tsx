import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { pluginById } from './plugins';
import StatusPill from './status';

const textOf = (item: Record<string, unknown>) => {
  const title = item.title || item.name || item.id || item.summary;
  const detail = item.detail || item.reason || item.description;
  return {
    title: typeof title === 'string' ? title : '',
    detail: typeof detail === 'string' ? detail : '',
    severity: typeof item.severity === 'string' ? item.severity : '',
    prompt: typeof item.prompt === 'string' ? item.prompt : '',
    response: typeof item.response === 'string' ? item.response : '',
  };
};

const FindingRow: React.FC<{ item: Record<string, unknown>; index: number }> = ({ item, index }) => {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const row = textOf(item);
  const verdict = typeof item.verdict === 'string' ? item.verdict : '';
  return (
    <div className="border-b border-zinc-100 last:border-b-0">
      <button type="button" onClick={() => setOpen(value => !value)} className="flex w-full items-center gap-3 px-4 py-3 text-left text-sm hover:bg-zinc-50">
        <ChevronRight className={`size-4 shrink-0 text-zinc-400 transition-transform ${open ? 'rotate-90' : ''}`} />
        {verdict && <StatusPill status={verdict} label={t(`desk.verdict.${verdict}`, { defaultValue: verdict })} />}
        <span className="min-w-0 flex-1 truncate">{row.title || t('desk.outputs.item', { index: index + 1 })}</span>
        <span className="hidden shrink-0 text-xs text-zinc-400 sm:block">{row.detail}</span>
      </button>
      {open && (
        <div className="space-y-3 bg-zinc-50 px-4 py-3 pl-11 text-xs">
          {row.detail && <p className="whitespace-pre-wrap text-zinc-600">{row.detail}</p>}
          {row.prompt && (
            <pre className="overflow-auto rounded-md border border-zinc-200 bg-white p-3 whitespace-pre-wrap">{row.prompt}</pre>
          )}
          {row.response && (
            <pre className="overflow-auto rounded-md border border-zinc-200 bg-white p-3 whitespace-pre-wrap text-zinc-600">{row.response}</pre>
          )}
        </div>
      )}
    </div>
  );
};

const PluginOutput: React.FC<{ data: unknown }> = ({ data }) => {
  const { t } = useTranslation();
  const record = data && typeof data === 'object' ? data as Record<string, unknown> : {};
  const pluginId = typeof record.plugin === 'string' ? record.plugin : '';
  const plugin = pluginById(pluginId);
  const fields = plugin?.outputs || [{ id: 'json', type: 'json' as const }];
  const status = typeof record.status === 'string' ? record.status : '';

  return (
    <Card className="overflow-hidden">
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <CardTitle className="text-base">{plugin ? t(`desk.plugins.${plugin.id}.name`) : t('desk.outputsTitle')}</CardTitle>
        {status && <StatusPill status={status} label={status} />}
      </CardHeader>
      <CardContent className="px-0 pb-0">
        {fields.map(field => {
          if (field.type === 'status') return null;
          if (field.type === 'findings') {
            const findings = Array.isArray(record.findings) ? record.findings : [];
            if (findings.length === 0) return <p key={field.id} className="px-6 pb-6 text-sm text-zinc-500">{t('desk.outputs.none')}</p>;
            return (
              <div key={field.id}>
                {findings.map((item, index) => (
                  item && typeof item === 'object'
                    ? <FindingRow key={index} item={item as Record<string, unknown>} index={index} />
                    : <p key={index} className="border-b px-6 py-3 text-sm">{String(item)}</p>
                ))}
              </div>
            );
          }
          return (
            <pre key={field.id} className="overflow-x-auto px-6 pb-6 text-xs whitespace-pre-wrap text-zinc-700">{JSON.stringify(record, null, 2)}</pre>
          );
        })}
      </CardContent>
    </Card>
  );
};

export default PluginOutput;
