import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronRight, CircleCheck, Clock, Loader2 } from 'lucide-react';

export interface TimelineEvent {
  type: 'step' | 'text' | 'tool' | 'conclusion';
  plugin: string;
  title?: string;
  status?: 'doing' | 'done' | 'error';
  text?: string;
  action?: string;
  param?: string;
  result?: string;
  detail?: string;
  verdict?: string;
  reason?: string;
}

interface Line {
  kind: 'text' | 'tool' | 'conclusion';
  text?: string;
  action?: string;
  param?: string;
  result?: string;
  detail?: string;
  verdict?: string;
  reason?: string;
}

interface StepView {
  plugin: string;
  title: string;
  status: 'doing' | 'done' | 'error';
  lines: Line[];
}

export function stepsFrom(events: TimelineEvent[]): StepView[] {
  const steps: StepView[] = [];
  events.forEach(event => {
    if (event.type === 'step') {
      const existing = steps.find(item => item.plugin === event.plugin);
      if (!existing) {
        steps.push({ plugin: event.plugin, title: event.title || event.plugin, status: event.status || 'doing', lines: [] });
      } else if (event.status) {
        existing.status = event.status;
        if (event.title) existing.title = event.title;
      }
      return;
    }
    const step = steps.find(item => item.plugin === event.plugin) ?? (() => {
      const created = { plugin: event.plugin, title: event.plugin, status: 'doing' as const, lines: [] };
      steps.push(created);
      return created;
    })();
    if (event.type === 'text') step.lines.push({ kind: 'text', text: event.text });
    if (event.type === 'tool') step.lines.push({ kind: 'tool', action: event.action, param: event.param, result: event.result, detail: event.detail });
    if (event.type === 'conclusion') step.lines.push({ kind: 'conclusion', verdict: event.verdict, reason: event.reason });
  });
  return steps;
}

const ToolLine: React.FC<{ line: Line }> = ({ line }) => {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-1">
      <div className="flex items-center gap-2">
        <button
          type="button"
          className={`my-1 w-fit rounded-lg bg-gray-100 p-2 text-left text-sm text-gray-700 ${line.detail ? 'cursor-pointer border-l-4 border-blue-500 hover:bg-gray-200' : ''}`}
          onClick={() => line.detail && setOpen(value => !value)}
        >
          {line.action} {line.param}
        </button>
        {line.result && <span className="text-sm text-gray-600">{line.result}</span>}
      </div>
      {open && line.detail && <pre className="mt-1 whitespace-pre-wrap rounded-md bg-gray-50 p-2 text-xs text-gray-600">{line.detail}</pre>}
    </div>
  );
};

const ScanTimeline: React.FC<{ events: TimelineEvent[]; waiting?: boolean }> = ({ events, waiting }) => {
  const { t } = useTranslation();
  const steps = stepsFrom(events);
  return (
    <div>
      {steps.map((step, index) => (
        <div key={step.plugin} className="relative flex">
          <div className="mr-4 flex flex-col items-center">
            <div className="flex h-8 w-8 items-center justify-center">
              {step.status === 'doing' && <Loader2 className="h-4 w-4 animate-spin text-blue-500" />}
              {step.status === 'done' && <CircleCheck className="h-4 w-4 text-green-500" />}
              {step.status === 'error' && <Clock className="h-4 w-4 text-red-500" />}
            </div>
            {index < steps.length - 1 && <div className="mt-2 min-h-10 w-0.5 flex-1 bg-gray-200" />}
          </div>
          <div className="flex-1 pb-4">
            <div className="flex items-center gap-2 pt-1">
              <span className="font-medium text-gray-900">{step.title}</span>
              {step.lines.length > 0 ? <ChevronDown className="h-4 w-4 text-gray-400" /> : <ChevronRight className="h-4 w-4 text-gray-400" />}
            </div>
            <div className="ml-2 mt-2 space-y-2">
              {step.lines.map((line, lineIndex) => {
                if (line.kind === 'text') return <p key={lineIndex} className="text-sm text-gray-700">{line.text}</p>;
                if (line.kind === 'tool') return <ToolLine key={lineIndex} line={line} />;
                const tone = line.verdict === 'fail' ? 'text-red-600' : line.verdict === 'pass' ? 'text-green-600' : 'text-amber-600';
                const label = t(`desk.verdict.${line.verdict || 'insufficient'}`, { defaultValue: line.verdict || '' });
                return <p key={lineIndex} className={`text-sm ${tone}`}>{label}。{line.reason}</p>;
              })}
            </div>
          </div>
        </div>
      ))}
      {waiting && (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
        </div>
      )}
    </div>
  );
};

export default ScanTimeline;
