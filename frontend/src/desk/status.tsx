import React from 'react';

const toneOf = (status: string) => {
  if (status === 'pass' || status === 'ok' || status === 'done') return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  if (status === 'fail' || status === 'error' || status === 'failed' || status === 'terminated') return 'border-red-200 bg-red-50 text-red-700';
  if (status === 'running') return 'border-blue-200 bg-blue-50 text-blue-700';
  return 'border-amber-200 bg-amber-50 text-amber-700';
};

const dotOf = (status: string) => {
  if (status === 'pass' || status === 'ok' || status === 'done') return 'bg-emerald-500';
  if (status === 'fail' || status === 'error' || status === 'failed' || status === 'terminated') return 'bg-red-500';
  if (status === 'running') return 'bg-blue-500';
  return 'bg-amber-500';
};

const StatusPill: React.FC<{ status: string; label: string }> = ({ status, label }) => (
  <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium whitespace-nowrap ${toneOf(status)}`}>
    <span className={`size-1.5 rounded-full ${dotOf(status)}`} />
    {label}
  </span>
);

export default StatusPill;
