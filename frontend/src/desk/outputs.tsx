import React from 'react';
import { useTranslation } from 'react-i18next';
import { pluginById } from './plugins';

const textOf = (item: Record<string, unknown>) => {
  const title = item.title || item.name || item.id || item.summary;
  const detail = item.detail || item.reason || item.description;
  return {
    title: typeof title === 'string' ? title : '',
    detail: typeof detail === 'string' ? detail : '',
    severity: typeof item.severity === 'string' ? item.severity : '',
  };
};

const PluginOutput: React.FC<{ data: unknown }> = ({ data }) => {
  const { t } = useTranslation();
  const record = data && typeof data === 'object' ? data as Record<string, unknown> : {};
  const pluginId = typeof record.plugin === 'string' ? record.plugin : '';
  const plugin = pluginById(pluginId);
  const fields = plugin?.outputs || [{ id: 'json', type: 'json' as const }];

  return (
    <article className="text-gray-900">
      <h1 className="text-2xl font-medium">{plugin ? t(`desk.plugins.${plugin.id}.name`) : t('desk.outputsTitle')}</h1>
      <div className="mt-6 space-y-6">
        {fields.map(field => {
          if (field.type === 'status') {
            const status = typeof record.status === 'string' ? record.status : '';
            return (
              <section key={field.id}>
                <h2 className="text-xs uppercase tracking-wide text-gray-400">{t('desk.outputs.status')}</h2>
                <p className="mt-2 text-sm">{status || t('desk.empty')}</p>
              </section>
            );
          }
          if (field.type === 'findings') {
            const findings = Array.isArray(record.findings) ? record.findings : [];
            return (
              <section key={field.id}>
                <h2 className="text-xs uppercase tracking-wide text-gray-400">{t('desk.outputs.findings')}</h2>
                {findings.length === 0 && <p className="mt-2 text-sm text-gray-500">{t('desk.outputs.none')}</p>}
                <div className="mt-2">
                  {findings.map((item, index) => {
                    if (!item || typeof item !== 'object') {
                      return <p key={index} className="border-b border-gray-100 py-3 text-sm">{String(item)}</p>;
                    }
                    const row = textOf(item as Record<string, unknown>);
                    return (
                      <div key={index} className="border-b border-gray-100 py-3 text-sm">
                        <div className="flex items-baseline justify-between gap-4">
                          <span>{row.title || t('desk.outputs.item', { index: index + 1 })}</span>
                          {row.severity && <span className="text-gray-400">{row.severity}</span>}
                        </div>
                        {row.detail && <p className="mt-1 whitespace-pre-wrap text-gray-600">{row.detail}</p>}
                      </div>
                    );
                  })}
                </div>
              </section>
            );
          }
          return (
            <section key={field.id}>
              <h2 className="text-xs uppercase tracking-wide text-gray-400">{t('desk.outputs.json')}</h2>
              <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs text-gray-700">{JSON.stringify(record, null, 2)}</pre>
            </section>
          );
        })}
      </div>
    </article>
  );
};

export default PluginOutput;
