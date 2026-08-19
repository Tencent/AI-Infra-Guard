import React, { useState, useEffect, useRef } from 'react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import {
  Cable,
  Zap,
  RotateCcw,
  Eye,
  EyeOff,
  CheckCircle2,
  Download,
  AlertTriangle,
  BadgeCheck,
  Server,
  Cpu,
  Calendar,
  ShieldCheck,
  ShieldAlert,
  Fingerprint,
  Radar,
  Sigma,
  KeyRound,
  Layers,
  Sparkles,
  FileCheck2,
  Lock,
} from 'lucide-react';
import Header from '../components/Header';
import LanguageSwitcher from '../components/LanguageSwitcher';
import { useReportPrint } from '../components/detailPanel/useReportPrint';
import { modelApi } from '../lib/modelApi';
import { relayApi, RelayModel } from '../lib/relayApi';
import { ModelItem } from '../types/model';
import { useLanguage } from '../hooks/useLanguage';

// Detection endpoint (Server-Sent Events stream)
const CHECK_STREAM_URL = '/api/v1/relay/check/stream';

interface FingerprintDetail {
  posterior?: number;
  runner_up_model?: string;
  runner_up_posterior?: number;
  evidence_level?: string;
  forgery_status?: string;
  sample_size?: number;
  candidate_count?: number;
  range?: [number, number];
  observed_distribution?: number[];
  reference_distribution?: number[];
  distribution_overlap?: number;
  largest_deviation?: {
    range?: [number, number];
    observed?: number;
    reference?: number;
    difference?: number;
  };
}

interface CheckResult {
  algorithm?: string;
  score?: number;
  overall_verdict?: string;
  risk_level?: string;
  summary?: string;
  detail?: {
 findings?: { probe?: string; severity: string; title: string }[];
    best_model?: string;
    fingerprint?: FingerprintDetail;
    test_info?: {
   latency_ms?: number | null;
  tokens_per_second?: number | null;
      input_tokens?: number | null;
      output_tokens?: number | null;
      cache_read_tokens?: number | null;
  };
};
  partial_errors?: Record<string, unknown> | null;
}

interface FindingItem {
  title: string;
  meaning: string;
  severity: string;
}

// Format a timestamp as YYYY/M/D HH:mm
const formatDateTime = (ts: number): string => {
  const d = new Date(ts);
  const pad = (n: number) => (n < 10 ? `0${n}` : `${n}`);
  return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

// ============ Fingerprint distribution matching card (only shown in full mode) ============
interface FingerprintCardProps {
  fingerprint: FingerprintDetail;
  bestModel?: string;
}

const FingerprintCard: React.FC<FingerprintCardProps> = ({ fingerprint, bestModel }) => {
  const { t } = useTranslation();

  const observed = fingerprint.observed_distribution ?? [];
  const reference = fingerprint.reference_distribution ?? [];
  const sampleSize = fingerprint.sample_size ?? 0;
  const candidateCount = fingerprint.candidate_count ?? 0;
  const [rangeStart, rangeEnd] = fingerprint.range ?? [1, Math.max(observed.length, reference.length)];
  const overlap = fingerprint.distribution_overlap ?? 0;
  const posterior = fingerprint.posterior ?? 0;
  const runnerUp = fingerprint.runner_up_model ?? '';
  const runnerUpPosterior = fingerprint.runner_up_posterior ?? 0;
  const dev = fingerprint.largest_deviation;

  // ---- Chart geometry ----
  const width = 640; // viewBox width
  const height = 220;
  const padLeft = 8;
  const padRight = 8;
  const padTop = 12;
  const padBottom = 24;
  const innerW = width - padLeft - padRight;
  const innerH = height - padTop - padBottom;

  const buckets = Math.max(observed.length, reference.length, 1);
  const maxY = Math.max(
    ...observed.map((v) => v || 0),
    ...reference.map((v) => v || 0),
    0.01
  );

  const xAt = (i: number) => padLeft + (i / (buckets - 1 || 1)) * innerW;
  const yAt = (v: number) => padTop + innerH - (v / maxY) * innerH;

  const buildPath = (arr: number[]): string => {
    if (!arr.length) return '';
    return arr.map((v, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i).toFixed(2)} ${yAt(v || 0).toFixed(2)}`).join(' ');
  };
  const buildArea = (arr: number[]): string => {
    if (!arr.length) return '';
    const line = arr.map((v, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i).toFixed(2)} ${yAt(v || 0).toFixed(2)}`).join(' ');
    return `${line} L ${xAt(arr.length - 1).toFixed(2)} ${(padTop + innerH).toFixed(2)} L ${xAt(0).toFixed(2)} ${(padTop + innerH).toFixed(2)} Z`;
  };

  // Peak point: index of the max value in observed, used for the right-side guide line
  const peakIdx = observed.reduce(
    (best, v, i, arr) => (v > arr[best] ? i : best),
    0
  );
  const peakX = xAt(peakIdx);
  const peakY = yAt(observed[peakIdx] || 0);

  const confidencePct = (posterior * 100).toFixed(1);
  const overlapPct = (overlap * 100).toFixed(1);
  const runnerUpPct = (runnerUpPosterior * 100).toFixed(1);
  const devDiffPP = dev?.difference != null ? (dev.difference * 100).toFixed(1) : '--';
  const devObservedPct = dev?.observed != null ? (dev.observed * 100).toFixed(1) : '--';
  const devReferencePct = dev?.reference != null ? (dev.reference * 100).toFixed(1) : '--';
  const devStart = dev?.range?.[0] ?? '--';
  const devEnd = dev?.range?.[1] ?? '--';

  const forgeryStatus = (fingerprint.forgery_status ?? '').toLowerCase();
  // Three verdicts: stable (green) / identity mismatch (red) / insufficient evidence (yellow)
  const verdictKind: 'stable' | 'mismatch' | 'insufficient' =
  forgeryStatus === 'supported'
      ? 'stable'
    : forgeryStatus === 'suspected_known' || forgeryStatus === 'unknown_anomaly'
      ? 'mismatch'
      : 'insufficient';
  const verdictClasses = {
    stable: {
    wrap: 'text-emerald-700',
      badge: 'bg-emerald-100',
      icon: 'text-emerald-600',
    Icon: CheckCircle2,
 key: 'llmProxyDetect.report.fingerprint.verdictStable',
   // Chart primary color (for the current observed curve)
  chartStroke: '#22c55e', // emerald-500
      legendBg: 'bg-emerald-500',
      accentText: 'text-emerald-600',
    },
    mismatch: {
      wrap: 'text-rose-700',
      badge: 'bg-rose-100',
  icon: 'text-rose-600',
  Icon: AlertTriangle,
      key: 'llmProxyDetect.report.fingerprint.verdictMismatch',
    chartStroke: '#f43f5e', // rose-500
      legendBg: 'bg-rose-500',
      accentText: 'text-rose-600',
    },
    insufficient: {
   wrap: 'text-amber-700',
      badge: 'bg-amber-100',
   icon: 'text-amber-600',
      Icon: AlertTriangle,
      key: 'llmProxyDetect.report.fingerprint.verdictInsufficient',
      chartStroke: '#f59e0b', // amber-500
      legendBg: 'bg-amber-500',
      accentText: 'text-amber-600',
    },
  }[verdictKind];
  const VerdictIcon = verdictClasses.Icon;
  const observedColor = verdictClasses.chartStroke;

  return (
    <Card className="rounded-3xl bg-white/70 backdrop-blur-md border border-gray-100 shadow-[0_10px_30px_-10px_rgba(11,28,48,0.05),0_4px_12px_-5px_rgba(11,28,48,0.02)] overflow-hidden p-6 sm:p-8">
      {/* Title area */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="inline-flex items-center gap-1.5 text-emerald-600 text-xs font-semibold mb-2">
            <Fingerprint size={14} />
      <span>{t('llmProxyDetect.report.fingerprint.badge')}</span>
          </div>
          <h3 className="text-xl sm:text-2xl font-bold text-gray-900">
       {t('llmProxyDetect.report.fingerprint.title')}
          </h3>
        </div>
<div className="flex items-center gap-4 text-xs text-gray-500">
     <span className="inline-flex items-center gap-1.5">
      <span className={`w-3 h-[2px] ${verdictClasses.legendBg} rounded-full`} />
    {t('llmProxyDetect.report.fingerprint.legendObserved')}
     </span>
    <span className="inline-flex items-center gap-1.5">
  <span className="w-3 h-[2px] bg-[#7B72F0] rounded-full" />
    {t('llmProxyDetect.report.fingerprint.legendReference')}
  </span>
        </div>
  </div>

      {/* Three-step flow: generate observed distribution -> overlay reference fingerprint -> output inferred result */}
      <div className="mt-6 relative">
        <div className="hidden sm:flex items-center gap-3">
          {[
            t('llmProxyDetect.report.fingerprint.stepGenerate'),
            t('llmProxyDetect.report.fingerprint.stepOverlay'),
            t('llmProxyDetect.report.fingerprint.stepOutput'),
          ].map((label, i, arr) => (
  <React.Fragment key={i}>
       <div className="flex items-center gap-2 shrink-0">
     <span className="w-6 h-6 rounded-full bg-white border border-emerald-300 text-emerald-600 text-[11px] font-bold flex items-center justify-center">
         {i + 1}
 </span>
     <span className="text-xs text-gray-600 whitespace-nowrap">{label}</span>
              </div>
    {i < arr.length - 1 && (
    <span
      aria-hidden
        className="flex-1 h-px bg-emerald-300 pointer-events-none"
      />
    )}
      </React.Fragment>
 ))}
   </div>
        {/* Mobile: vertical stack */}
        <div className="flex flex-col gap-2 sm:hidden">
          {[
            t('llmProxyDetect.report.fingerprint.stepGenerate'),
            t('llmProxyDetect.report.fingerprint.stepOverlay'),
            t('llmProxyDetect.report.fingerprint.stepOutput'),
          ].map((label, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-white border border-emerald-300 text-emerald-600 text-[11px] font-bold flex items-center justify-center shrink-0">
                {i + 1}
              </span>
              <span className="text-xs text-gray-600">{label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Body: chart on the left + result card on the right */}
      <div className="mt-6 grid grid-cols-1 lg:grid-cols-[1fr_260px] gap-6">
        {/* Chart area */}
   <div className="relative">
          <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
   <span className="font-semibold text-gray-700">
   {t('llmProxyDetect.report.fingerprint.sampleSize', { count: sampleSize })}
            </span>
            <span>{t('llmProxyDetect.report.fingerprint.candidateHint', { count: candidateCount })}</span>
          </div>

        <div className="relative rounded-lg bg-gradient-to-b from-gray-50 to-white border border-gray-100 p-2">
  <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-[220px]" preserveAspectRatio="none">
     <defs>
        <linearGradient id="obsFill" x1="0" y1="0" x2="0" y2="1">
 <stop offset="0%" stopColor={observedColor} stopOpacity="0.25" />
       <stop offset="100%" stopColor={observedColor} stopOpacity="0" />
     </linearGradient>
    <linearGradient id="refFill" x1="0" y1="0" x2="0" y2="1">
           <stop offset="0%" stopColor="#7B72F0" stopOpacity="0.18" />
   <stop offset="100%" stopColor="#7B72F0" stopOpacity="0" />
       </linearGradient>
    </defs>

              {/* Grid lines (4 horizontal) */}
     {[0.25, 0.5, 0.75, 1].map((r) => (
   <line
       key={r}
             x1={padLeft}
               x2={width - padRight}
      y1={padTop + innerH * r}
           y2={padTop + innerH * r}
       stroke="#eef2f7"
      strokeWidth={1}
       />
    ))}

    {/* Reference area + line */}
<path d={buildArea(reference)} fill="url(#refFill)" />
       <path d={buildPath(reference)} fill="none" stroke="#7B72F0" strokeWidth={1.75} strokeLinejoin="round" strokeLinecap="round" />

    {/* Observed area + line */}
     <path d={buildArea(observed)} fill="url(#obsFill)" />
     <path d={buildPath(observed)} fill="none" stroke={observedColor} strokeWidth={1.75} strokeLinejoin="round" strokeLinecap="round" />

   {/* Peak highlight */}
  {observed.length > 0 && (
    <>
       <circle cx={peakX} cy={peakY} r={5} fill={observedColor} opacity="0.25" />
      <circle cx={peakX} cy={peakY} r={3} fill={observedColor} />
  <line x1={peakX} y1={peakY} x2={width - padRight} y2={peakY} stroke={observedColor} strokeWidth={1} strokeDasharray="3 3" opacity="0.5" />
    </>
 )}

      {/* X axis ticks: start, end */}
           <text x={padLeft} y={height - 6} fontSize="10" fill="#94a3b8">{rangeStart}</text>
   <text x={width - padRight} y={height - 6} fontSize="10" fill="#94a3b8" textAnchor="end">{rangeEnd}</text>
       </svg>
  </div>
        </div>

        {/* Right-side result card */}
        <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-5 flex flex-col justify-between">
      <div>
   <div className="w-9 h-9 rounded-lg bg-gray-900 text-white flex items-center justify-center font-serif italic text-lg mb-4">
        f
         </div>
            <p className="text-xs text-gray-500">
  {t('llmProxyDetect.report.fingerprint.finalModel')}
            </p>
 <p className="mt-1 text-2xl font-bold text-gray-900 break-all">
      {bestModel || t('llmProxyDetect.report.notIdentified')}
            </p>
          </div>
          <div className="mt-5 pt-4 border-t border-gray-100">
  <div className="flex items-center justify-between">
          <span className="text-xs text-gray-500">
       {t('llmProxyDetect.report.fingerprint.confidence')}
              </span>
               <span className={`text-lg font-bold ${verdictClasses.accentText}`}>{confidencePct}%</span>
            </div>
        <p className="text-[11px] text-gray-400 mt-2 leading-relaxed">
    {t('llmProxyDetect.report.fingerprint.confidenceDesc')}
       </p>
          </div>
  </div>
  </div>

      {/* Three metric cards */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
   <p className="text-xs text-gray-500">
  {t('llmProxyDetect.report.fingerprint.overlapTitle')}
   </p>
   <p className="mt-2 text-2xl font-bold text-gray-900">{overlapPct}%</p>
          <p className="text-[11px] text-gray-400 mt-2">
         {t(
          overlap >= 0.9
     ? 'llmProxyDetect.report.fingerprint.overlapDescHigh'
     : overlap >= 0.75
        ? 'llmProxyDetect.report.fingerprint.overlapDescMid'
   : 'llmProxyDetect.report.fingerprint.overlapDescLow'
            )}
   </p>
</div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
      <p className="text-xs text-gray-500">
    {t('llmProxyDetect.report.fingerprint.deviationTitle')}
          </p>
          <p className="mt-2 text-2xl font-bold text-gray-900">
     {t('llmProxyDetect.report.fingerprint.deviationValue', { diff: devDiffPP })}
          </p>
        <p className="text-[11px] text-gray-400 mt-2">
  {t('llmProxyDetect.report.fingerprint.deviationDesc', {
       start: devStart,
      end: devEnd,
   observed: devObservedPct,
            reference: devReferencePct,
            })}
        </p>
 </div>
   <div className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-xs text-gray-500">
     {t('llmProxyDetect.report.fingerprint.runnerUpTitle')}
    </p>
    <p className="mt-2 text-2xl font-bold text-gray-900 break-all">{runnerUp || '—'}</p>
   <p className="text-[11px] text-gray-400 mt-2">
   {t('llmProxyDetect.report.fingerprint.runnerUpDesc', { percent: runnerUpPct })}
      </p>
  </div>
      </div>

      {/* Verdict */}
      <div className={`mt-5 flex items-center gap-2 text-sm ${verdictClasses.wrap}`}>
        <span className={`w-5 h-5 rounded-full ${verdictClasses.badge} flex items-center justify-center shrink-0`}>
    <VerdictIcon size={14} className={verdictClasses.icon} />
        </span>
        <span>{t(verdictClasses.key)}</span>
      </div>
    </Card>
  );
};

const LLMProxyDetectPage: React.FC = () => {
  const { t } = useTranslation();
  const [endpointUrl, setEndpointUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);
  const [model, setModel] = useState('');
  const [customModel, setCustomModel] = useState('');
  const [scanMode, setScanMode] = useState<'quick' | 'full'>('quick');
  const [isDetecting, setIsDetecting] = useState(false);
  const [platformModels, setPlatformModels] = useState<ModelItem[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [relayModels, setRelayModels] = useState<RelayModel[]>([]);
  const [loadingRelayModels, setLoadingRelayModels] = useState(false);

  // Whether a finding's severity is "passed"
  // The backend only returns "Passed" / "Failed"; compared case-insensitively here
  const isPassSeverity = (sev?: string): boolean =>
    (sev || '').toLowerCase() === 'passed';

  // Map the API severity to "Pass / Fail" (localized)
  const mapVerdict = (sev?: string): string =>
    isPassSeverity(sev)
      ? t('llmProxyDetect.report.verdictPass')
      : t('llmProxyDetect.report.verdictFail');

  // Sort built-in models: Claude & GPT series first, newer version within a series first
  const sortRelayModels = (models: RelayModel[]): RelayModel[] => {
    const seriesPriority = (provider: string) => {
      if (provider === 'anthropic') return 1;
      if (provider === 'openai_compatible') return 2;
      return 3;
    };
    const extractVersion = (s: string) => {
      const matches = s.match(/\d+(?:\.\d+)*/g);
      if (!matches) return 0;
      return parseFloat(matches[matches.length - 1]);
    };
    return [...models].sort((a, b) => {
      const pa = seriesPriority(a.provider);
      const pb = seriesPriority(b.provider);
      if (pa !== pb) return pa - pb;
      return extractVersion(b.id) - extractVersion(a.id); // newer first
    });
  };

  // Load the platform-configured models (reuse modelApi.getModels -> /api/v1/app/models)
  useEffect(() => {
    const loadModels = async () => {
      setLoadingModels(true);
      try {
        const response = await modelApi.getModels();
        if (response.status === 0 && response.data) {
          setPlatformModels(response.data);
        }
      } catch (error) {
        console.error('Failed to load platform model list:', error);
      } finally {
        setLoadingModels(false);
      }
    };
    loadModels();
  }, []);

  // Load the built-in detectable models (GET /api/v1/relay/models)
  useEffect(() => {
    const loadRelayModels = async () => {
      setLoadingRelayModels(true);
      try {
        const response = await relayApi.getModels();
        if (response.status === 0 && response.data?.models) {
          setRelayModels(sortRelayModels(response.data.models));
        }
      } catch (error) {
        console.error('Failed to load built-in detectable models:', error);
      } finally {
        setLoadingRelayModels(false);
      }
    };
    loadRelayModels();
  }, []);

  // Track user scroll to determine whether the log is stuck to the bottom
  const handleLogScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    // Within 8px of the bottom counts as "stuck to bottom"
    isLogStickBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight <= 8;
  };

  // Mask a token for display (keep prefix, hide the rest)
  const maskToken = (token?: string) =>
    token && token.length > 6 ? `${token.slice(0, 6)}••••••••` : '••••••••';

  // Currently selected platform-configured model (if any)
  const selectedPlatformModel = platformModels.find((m) => m.model_id === model);
  const isPlatformModel = !!selectedPlatformModel;

  // Currently selected built-in detectable model (from /api/v1/relay/models)
  const selectedRelayModel = relayModels.find((m) => m.id === model);
  const isBuiltInModel = !!selectedRelayModel;
  // Full audit is only supported for models in the built-in relay list
  const fullAuditSupported = isBuiltInModel;

  const { currentLanguage } = useLanguage();

  // ---- Live SSE detection state ----
  type DetectPhase = 'idle' | 'connecting' | 'running' | 'done' | 'failed';
  const [phase, setPhase] = useState<DetectPhase>('idle');
  const [stageLabel, setStageLabel] = useState('');
  const [progressRate, setProgressRate] = useState<number | null>(null);
  const [eventMessages, setEventMessages] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const resultRef = useRef<CheckResult | null>(null);
  const targetModelRef = useRef<string>('');
  const baseUrlRef = useRef<string>('');
  // Log container: used to auto-scroll to bottom (pauses auto-scroll after the user scrolls up manually)
  const logContainerRef = useRef<HTMLDivElement | null>(null);
  const isLogStickBottomRef = useRef<boolean>(true);

  // When a new log event arrives, auto-scroll to bottom unless the user scrolled up manually
  useEffect(() => {
    const el = logContainerRef.current;
    if (!el) return;
    if (isLogStickBottomRef.current) {
      el.scrollTop = el.scrollHeight;
    }
  }, [eventMessages]);

  // Reset "stuck to bottom" state when detection starts so each new run auto-follows by default
  useEffect(() => {
    if (phase === 'connecting') {
      isLogStickBottomRef.current = true;
    }
  }, [phase]);

  // Track the previous fullAuditSupported value to detect an "unsupported -> supported" transition
  const prevFullAuditSupportedRef = useRef<boolean>(fullAuditSupported);

  // Automatically adjust scan mode:
  // 1) When full scan is not supported, fall back to quick scan
  // 2) When switching from "unsupported" to "supported", automatically select full scan
  useEffect(() => {
    const prev = prevFullAuditSupportedRef.current;
    if (!fullAuditSupported && scanMode === 'full') {
      setScanMode('quick');
    } else if (!prev && fullAuditSupported) {
      setScanMode('full');
    }
    prevFullAuditSupportedRef.current = fullAuditSupported;
  }, [fullAuditSupported, scanMode]);

  // ---- View switching: detect form / report view ----
  const [view, setView] = useState<'detect' | 'report'>('detect');
  const [reportResult, setReportResult] = useState<CheckResult | null>(null);
  const [reportTargetModel, setReportTargetModel] = useState<string>('');
  const [reportBaseUrl, setReportBaseUrl] = useState<string>('');
  const [reportDetectionTime, setReportDetectionTime] = useState<string>('');
  const detectionStartRef = useRef<number>(0);

  const canStart = !model
    ? false
    : isPlatformModel
    ? true
    : model === 'custom'
    ? !!customModel.trim() && !!endpointUrl.trim() && !!apiKey.trim()
    : !!endpointUrl.trim() && !!apiKey.trim();

  // When a platform-configured model is selected, URL & API Key are not needed
  const handleModelChange = (value: string) => {
    setModel(value);
    const selected = platformModels.find((m) => m.model_id === value);
    if (selected) {
      setEndpointUrl('');
      setApiKey('');
    }
  };

  const handleStartDetection = async () => {
    // ---- Form validation: give the user clear feedback ----
    if (!model) {
      toast.error(t('llmProxyDetect.validation.selectModel'));
      return;
    }
    if (model === 'custom' && !customModel.trim()) {
      toast.error(t('llmProxyDetect.validation.fillCustomModel'));
      return;
    }
    if (!isPlatformModel) {
      if (!endpointUrl.trim()) {
        toast.error(t('llmProxyDetect.validation.fillRelayUrl'));
        return;
      }
      if (!apiKey.trim()) {
        toast.error(t('llmProxyDetect.validation.fillApiKey'));
        return;
      }
    }
    if (!canStart) return;

    // Record the target model chosen by the user, to be displayed in the report view after detection
    const targetModelName = isPlatformModel
      ? selectedPlatformModel?.model.model || model
      : model === 'custom'
      ? customModel.trim()
      : selectedRelayModel?.name || model;
    targetModelRef.current = targetModelName;

    // ---- Build request payload ----
    const payload: Record<string, unknown> = {
      algorithm: scanMode,
      language: currentLanguage === 'en' ? 'en' : 'zh',
      use_configured_model: isPlatformModel,
    };

    if (isPlatformModel) {
      payload.model_id = model;
      // Show the base_url saved on the platform in the report
      baseUrlRef.current = selectedPlatformModel?.model.base_url || '';
    } else {
      const baseUrl = endpointUrl.trim();
      payload.base_url = baseUrl;
      payload.api_key = apiKey.trim();
      payload.model = model === 'custom' ? customModel.trim() : model;
      baseUrlRef.current = baseUrl;
    }

    // Not shown in the UI, only used in full mode: default 200 samples, disable thinking
    if (scanMode === 'full') {
      payload.iterations = 200;
      payload.no_think = true;
    }

    // ---- Reset live state ----
    setPhase('connecting');
    setStageLabel(t('llmProxyDetect.overlay.stageConnecting'));
    setProgressRate(null);
    setEventMessages([]);
    setErrorMessage(null);
    resultRef.current = null;
    setIsDetecting(true);
    detectionStartRef.current = Date.now();

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const response = await fetch(CHECK_STREAM_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      // Request errors before SSE starts use a regular HTTP JSON response (400/409/422, etc.)
      if (!response.ok || !response.body) {
        let detail = t('llmProxyDetect.overlay.requestFailedHttp', { status: response.status });
        try {
          const errJson = await response.json();
          if (errJson && typeof errJson.detail === 'string') detail = errJson.detail;
        } catch {
          /* keep default detail */
        }
        throw new Error(detail);
      }

      setPhase('running');
      setStageLabel(t('llmProxyDetect.overlay.stageRunning'));
      await readSseStream(response.body, controller.signal);
    } catch (err) {
      if ((err as { name?: string })?.name === 'AbortError') {
        setPhase('idle');
        setIsDetecting(false);
        return;
      }
      const msg = err instanceof Error ? err.message : t('llmProxyDetect.overlay.requestFailedDefault');
      setPhase('failed');
      setErrorMessage(msg);
      setStageLabel(t('llmProxyDetect.overlay.stageAborted'));
      setIsDetecting(false);
    }
  };

  const cancelDetection = () => {
    abortRef.current?.abort();
  };

  // Parse the SSE event stream (text/event-stream) and handle events one by one until done / error
  const readSseStream = async (body: ReadableStream<Uint8Array>, signal: AbortSignal) => {
    const reader = body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let eventName: string | null = null;

    const appendLog = (msg: string) =>
      setEventMessages((prev) => [...prev, msg].slice(-100));

    const handleBlock = (block: string) => {
      const lines = block.split('\n');
      let dataStr = '';
      let localEvent: string | null = null;
      for (const line of lines) {
        if (!line || line.startsWith(':')) continue; // ignore comment/keep-alive lines
        if (line.startsWith('event:')) {
          localEvent = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          dataStr += (dataStr ? '\n' : '') + line.slice(5).trim();
        }
      }
      if (localEvent) eventName = localEvent;
      if (!dataStr) return;

      let envelope: { status?: number; message?: string; data?: any };
      try {
        envelope = JSON.parse(dataStr);
      } catch {
        return;
      }

      const { message, data } = envelope;

      switch (eventName) {
        case 'start':
          appendLog(`[start] ${message ?? 'started'}`);
          setStageLabel(t('llmProxyDetect.overlay.stageStarted', { mode: data?.algorithm ?? scanMode }));
          break;
        case 'progress': {
          const completed = typeof data?.completed === 'number' ? data.completed : undefined;
          const total = typeof data?.total === 'number' ? data.total : undefined;
          const success = typeof data?.success === 'number' ? data.success : undefined;
          const errorCount = typeof data?.error === 'number' ? data.error : undefined;

          if (typeof completed === 'number' && typeof total === 'number' && total > 0) {
            const rate = completed / total;
            setProgressRate(rate);
            setStageLabel(t('llmProxyDetect.overlay.stageSampling', { percent: Math.round(rate * 100) }));
          } else if (typeof data?.completed_rate === 'number') {
            // Fallback to legacy field
            setProgressRate(data.completed_rate);
            setStageLabel(t('llmProxyDetect.overlay.stageSampling', { percent: Math.round(data.completed_rate * 100) }));
          }

          const parts: string[] = [];
          if (typeof completed === 'number' && typeof total === 'number') {
            parts.push(`${completed}/${total}`);
          }
          if (typeof success === 'number') parts.push(`success=${success}`);
          if (typeof errorCount === 'number') parts.push(`error=${errorCount}`);
          const detail = parts.join(' · ');
          appendLog(`[progress] ${detail || message || ''}`);
          break;
        }
        case 'result': {
          resultRef.current = data;
          const score = data?.score ?? '?';
          appendLog(
            t('llmProxyDetect.overlay.logResultPrefix', { score, summary: data?.summary ?? '' })
          );
          if (data?.partial_errors && Object.keys(data.partial_errors).length) {
            appendLog(`[partial_errors] ${JSON.stringify(data.partial_errors)}`);
          }
          setStageLabel(t('llmProxyDetect.overlay.stageGeneratingReport'));
          break;
        }
        case 'done':
          appendLog(t('llmProxyDetect.overlay.logDoneOk'));
          setReportResult(resultRef.current);
          setReportTargetModel(targetModelRef.current);
          setReportBaseUrl(baseUrlRef.current);
          setReportDetectionTime(formatDateTime(detectionStartRef.current || Date.now()));
          setPhase('idle');
          setIsDetecting(false);
          setView('report');
          break;
        case 'error':
          appendLog(`[error] ${message ?? t('llmProxyDetect.overlay.detectFailedDefault')}`);
          setPhase('failed');
          setErrorMessage(message ?? t('llmProxyDetect.overlay.detectFailedDefault'));
          setStageLabel(t('llmProxyDetect.overlay.stageAborted'));
          setIsDetecting(false);
          break;
        default:
          if (message) appendLog(`[${eventName ?? 'event'}] ${message}`);
      }
    };

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (signal.aborted) break;
        buffer += decoder.decode(value, { stream: true });

        let sep: number;
        while ((sep = buffer.indexOf('\n\n')) !== -1) {
          const rawBlock = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          handleBlock(rawBlock);
        }
      }
      if (buffer.trim()) handleBlock(buffer);
    } finally {
      reader.releaseLock();
    }
  };

  const handleResetDefaults = () => {
    setEndpointUrl('');
    setApiKey('');
    setModel('');
    setCustomModel('');
    setScanMode('quick');
  };

  // ============ Report view derived data ============
  const rawReportScore = reportResult?.score ?? 0;
  // Support both 0~1 and 0~100 scales: only values in (0,1] are treated as a percentage
  const reportScore = rawReportScore > 0 && rawReportScore <= 1 ? rawReportScore * 100 : rawReportScore;
  // SVG ring: r=70, circumference = 2*PI*70 ≈ 440
  const circumference = 440;
  const displayScore = Math.max(0, Math.min(100, reportScore));
  const dashOffset = circumference * (1 - displayScore / 100);

  const resultFindings = reportResult?.detail?.findings ?? [];
  const displayFindings: FindingItem[] = resultFindings
    .map((f) => ({
    title: f.probe || f.title,
      meaning: f.title,
      severity: f.severity,
    }))
    // Stable sort: failed items first, passed items after; keep original API order within each group
    .sort((a, b) => Number(isPassSeverity(a.severity)) - Number(isPassSeverity(b.severity)));

  const passedCount = displayFindings.filter((f) => isPassSeverity(f.severity)).length;
  const failedCount = displayFindings.length - passedCount;

  const testInfo = reportResult?.detail?.test_info;

  // Token metrics: use a logarithmic scale so both0~tens and thousands~tens-of-thousands are visually distinguishable.
  // Empty/0 -> 0% (no more 4% floor) to avoid making "125 and 0 look the same".
  const logPct = (v: number | null | undefined, max: number) => {
    if (v == null || v <= 0) return 0;
    const p = (Math.log10(1 + v) / Math.log10(1 + max)) * 100;
    return Math.max(0, Math.min(100, p));
  };

  // TTFT (time to first token): lower is better. Inverted log-scale mapping,
  // e.g. ~100ms is near full, 1s mid-range, >=10s is near 0.
  const invertedLogPct = (v: number | null | undefined, bestMs: number, worstMs: number) => {
    if (v == null || v <= 0) return 100;
    const clamped = Math.max(bestMs, Math.min(worstMs, v));
    const ratio = (Math.log10(clamped) - Math.log10(bestMs)) / (Math.log10(worstMs) - Math.log10(bestMs));
    return Math.max(0, Math.min(100, (1 - ratio) * 100));
  };

  // Tokens/sec: larger is better; 100 tps is treated as "very fast" and near full.
  const linearPct = (v: number | null | undefined, max: number) => {
    if (v == null || v <= 0) return 0;
    return Math.max(0, Math.min(100, (v / max) * 100));
  };

  // Return progress bar color based on "good/mid/bad" rating.
  const perfColor = (rating: 'good' | 'mid' | 'bad') =>
    rating === 'good' ? 'bg-emerald-500' : rating === 'mid' ? 'bg-amber-500' : 'bg-rose-500';

  const ttftRating: 'good' | 'mid' | 'bad' =
    testInfo?.latency_ms == null
      ? 'mid'
      : testInfo.latency_ms <= 800
      ? 'good'
      : testInfo.latency_ms <= 2500
    ? 'mid'
      : 'bad';
  const tpsRating: 'good' | 'mid' | 'bad' =
    testInfo?.tokens_per_second == null
      ? 'mid'
      : testInfo.tokens_per_second >= 40
   ? 'good'
      : testInfo.tokens_per_second >= 15
      ? 'mid'
      : 'bad';

  const speedRows = [
    {
      label: t('llmProxyDetect.report.metrics.ttft'),
   value: testInfo?.latency_ms != null ? `${testInfo.latency_ms}ms` : '—',
// 100ms(near full) ~ 10000ms(near empty)
      width: `${invertedLogPct(testInfo?.latency_ms, 100, 10000)}%`,
      color: perfColor(ttftRating),
    },
    {
      label: t('llmProxyDetect.report.metrics.tokensPerSec'),
      value: testInfo?.tokens_per_second != null ? `${testInfo.tokens_per_second} tps` : '—',
      width: `${linearPct(testInfo?.tokens_per_second, 100)}%`,
      color: perfColor(tpsRating),
    },
    {
      label: t('llmProxyDetect.report.metrics.inputTokens'),
  value: testInfo?.input_tokens != null ? `${testInfo.input_tokens}` : '—',
      // Log scale, reference upper bound 128k (covers common context windows)
      width: `${logPct(testInfo?.input_tokens, 128000)}%`,
      color: 'bg-[#5D5FEF]',
    },
    {
      label: t('llmProxyDetect.report.metrics.outputTokens'),
      value: testInfo?.output_tokens != null ? `${testInfo.output_tokens}` : '—',
      // Output cap is usually smaller than input, reference 16k
   width: `${logPct(testInfo?.output_tokens, 16000)}%`,
      color: 'bg-[#5D5FEF]',
    },
    {
    label: t('llmProxyDetect.report.metrics.cacheReadTokens'),
      value: testInfo?.cache_read_tokens != null ? `${testInfo.cache_read_tokens}` : '—',
      width: `${logPct(testInfo?.cache_read_tokens, 128000)}%`,
      color: 'bg-[#5D5FEF]',
    },
  ];

  const bestModel = reportResult?.detail?.best_model || '';
  const targetIdentity = reportTargetModel || bestModel || t('llmProxyDetect.report.notIdentified');
  const confidenceLabel = (() => {
    if (reportScore < 40) return t('llmProxyDetect.report.confidenceLow');
    if (reportScore < 70) return t('llmProxyDetect.report.confidenceMid');
    return t('llmProxyDetect.report.confidenceHigh');
  })();
  const actualIdentity = bestModel || confidenceLabel;
  const isRisk = reportResult?.overall_verdict === 'risk';
  // When the backend reports risk, prefer the fine-grained risk_level (high / medium / low).
  // Fallback to the coarse "risk" wording if risk_level is missing or unrecognized.
  const riskLevel = (reportResult?.risk_level || '').toLowerCase();
  const riskLevelKey =
    riskLevel === 'high' ? 'high' : riskLevel === 'medium' ? 'medium' : riskLevel === 'low' ? 'low' : '';
  const scoreLabel = isRisk
    ? riskLevelKey
      ? t(`llmProxyDetect.report.scoreRisk${riskLevelKey.charAt(0).toUpperCase() + riskLevelKey.slice(1)}`)
      : t('llmProxyDetect.report.scoreRisk')
    : t('llmProxyDetect.report.scoreNormal');
  const riskBadgeLabel = isRisk
    ? riskLevelKey
      ? t(`llmProxyDetect.report.badgeRisk${riskLevelKey.charAt(0).toUpperCase() + riskLevelKey.slice(1)}`)
      : t('llmProxyDetect.report.badgeRisk')
    : t('llmProxyDetect.report.badgeVerified');
  // Return ring/label color based on the score range: <40 red, <70 orange, >=70 green
  const scoreColor = (() => {
    if (reportScore < 40) return { ring: '#ef4444', track: '#fee2e2', label: '#dc2626' }; // red-500 / red-100 / red-600
    if (reportScore < 70) return { ring: '#f59e0b', track: '#fef3c7', label: '#d97706' }; // amber-500 / amber-100 / amber-600
    return { ring: '#22c55e', track: '#dcfce7', label: '#16a34a' };                        // green-500 / green-100 / green-600
  })();
  // Localization mapping for detection algorithm
  const algorithmLabel = (() => {
    const algo = (reportResult?.algorithm || '').toLowerCase();
    if (algo === 'quick') return t('llmProxyDetect.report.algorithmQuick');
    if (algo === 'full') return t('llmProxyDetect.report.algorithmFull');
    return reportResult?.algorithm || '';
  })();

  const handleBackToDetect = () => {
    setView('detect');
    setReportResult(null);
    setReportTargetModel('');
    setReportBaseUrl('');
    setReportDetectionTime('');
  };

  // ---- Report export (browser print, save as PDF) ----
  const reportRef = useRef<HTMLDivElement>(null);
  const reportDocumentTitle = (() => {
    const target = reportTargetModel || bestModel || 'LLM';
    const zh = '大模型 API 投毒检测报告';
    const en = 'LLM API Poisoning Detection Report';
    const base = currentLanguage === 'en' ? en : zh;
    return `${base} - ${target}`;
  })();
  const handleDownloadPdf = useReportPrint(reportRef, reportDocumentTitle);

  // ============ Report view ============
  if (view === 'report') {
    return (
      <div className="h-screen bg-gray-50 flex flex-col overflow-hidden">
        <Header backButtonLeftSlot={<LanguageSwitcher />} />

        <main className="flex-1 overflow-y-auto">
          <div ref={reportRef} className="print-content-wrapper max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
            {/* Top actions (above the header card) */}
            <div className="flex justify-end gap-2">
              <button
                onClick={handleDownloadPdf}
                className="bg-white border border-gray-200 px-4 py-2 rounded-lg text-sm font-semibold text-gray-900 hover:bg-gray-50 transition-colors flex items-center gap-1 shadow-sm"
              >
                <Download size={18} /> {t('llmProxyDetect.report.exportReport')}
              </button>
              <button
                onClick={handleBackToDetect}
                className="bg-[#5D5FEF] text-white px-6 py-2 rounded-lg text-sm font-semibold hover:opacity-90 transition-opacity shadow-[0_4px_14px_0_rgba(93,95,239,0.25)]"
              >
                {t('llmProxyDetect.report.runNewAudit')}
              </button>
            </div>

            {/* Header Section */}
            <div className="relative bg-[#7B72F0] p-8 rounded-xl border border-[#7B72F0]/20 shadow-sm overflow-hidden">
              {/* Centered title & meta */}
              <div className="flex flex-col items-center text-center">
                <div className="flex items-center justify-center gap-2 mb-4 mt-2">
                  <img src="/images/logo-white.png" alt="A.I.G" className="w-8 h-8 mr-2 flex-shrink-0" />
                  <h1 className="text-3xl font-bold text-white flex items-center">
                    <span
                      className="mr-4 relative"
                      style={{ fontFamily: 'tencentSans', letterSpacing: '0.1em', top: '-2px', fontSize: '30px' }}
                    >
                      A.I.G
                    </span>
                    {t('llmProxyDetect.report.title')}
                  </h1>
                </div>
                {(reportResult?.algorithm || reportBaseUrl || reportDetectionTime) && (
                  <div className="flex flex-wrap justify-center gap-x-12 gap-y-4 text-xs text-[#E0DEFC] mt-6 mb-2">
                    {reportBaseUrl && (
                      <div className="flex items-center gap-2">
                        <Server className="w-4 h-4 opacity-70" />
                        <span className="opacity-70">{t('llmProxyDetect.report.relayAddress')}</span>
                        <span className="font-medium text-white text-sm font-mono break-all">{reportBaseUrl}</span>
                      </div>
                    )}
                    {reportResult?.algorithm && (
                      <div className="flex items-center gap-2">
                        <Cpu className="w-4 h-4 opacity-70" />
                        <span className="opacity-70">{t('llmProxyDetect.report.detectionAlgorithm')}</span>
                        <span className="font-medium text-white text-sm">{algorithmLabel}</span>
                      </div>
                    )}
                    {reportDetectionTime && (
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 opacity-70" />
                        <span className="opacity-70">{t('llmProxyDetect.report.detectionTime')}</span>
                        <span className="font-medium text-white text-sm">{reportDetectionTime}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Score and Authenticity Bento */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                   <Card className="rounded-3xl bg-white/70 backdrop-blur-md border border-gray-100 shadow-[0_10px_30px_-10px_rgba(11,28,48,0.05),0_4px_12px_-5px_rgba(11,28,48,0.02)] overflow-hidden p-8 flex flex-col items-center justify-center relative group">
                <div className="text-center relative z-10 w-full">
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-6">{t('llmProxyDetect.report.overallHealth')}</p>
                  <div className="relative w-40 h-40 flex items-center justify-center mx-auto">
                    <svg className="w-full h-full transform -rotate-90" viewBox="0 0 160 160">
                      <circle cx="80" cy="80" fill="transparent" r="70" stroke={scoreColor.track} strokeWidth="10" />
                      <circle
                        cx="80"
                        cy="80"
                        fill="transparent"
                        r="70"
                        stroke={scoreColor.ring}
                        strokeDasharray={circumference}
                        strokeDashoffset={dashOffset}
                        strokeLinecap="round"
                        strokeWidth="10"
                        style={{ transition: 'stroke-dashoffset 0.35s, stroke 0.35s' }}
                      />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-5xl font-bold text-gray-900">{reportScore}</span>
                      <span className="text-xs font-semibold text-gray-600">{t('llmProxyDetect.report.outOf')}</span>
                    </div>
                  </div>
                  <p className="mt-6 text-sm font-bold tracking-tight" style={{ color: scoreColor.label }}>{scoreLabel}</p>
                  {reportResult?.summary && (
                    <div className="mt-6 pt-4 border-t border-gray-100 w-full">
                      <p className="text-sm text-gray-600 font-medium leading-relaxed">{reportResult.summary}</p>
                    </div>
                  )}
                </div>
     <div
  className="absolute -bottom-4 -right-4 opacity-[0.03] group-hover:opacity-[0.06] transition-opacity pointer-events-none"
   >
      {reportScore < 40 ? (
      <ShieldAlert size={140} />
     ) : reportScore < 70 ? (
        <AlertTriangle size={140} />
     ) : (
   <BadgeCheck size={140} />
        )}
        </div>
              </Card>

            <Card className="rounded-3xl bg-white/70 backdrop-blur-md border border-gray-100 shadow-[0_10px_30px_-10px_rgba(11,28,48,0.05),0_4px_12px_-5px_rgba(11,28,48,0.02)] overflow-hidden p-8 md:col-span-2 flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-start mb-6">
                    <div>
                      <h3 className="text-2xl font-semibold text-gray-900">{t('llmProxyDetect.report.modelAuthenticity')}</h3>
                      <p className="text-sm text-gray-600 mt-1">{t('llmProxyDetect.report.modelAuthenticityDesc')}</p>
                    </div>
                    <span
                      className="text-[10px] px-2.5 py-1 rounded-full font-bold uppercase tracking-wider"
                      style={{ backgroundColor: scoreColor.track, color: scoreColor.label }}
                    >
                      {riskBadgeLabel}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                    <div className="space-y-2">
       <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest">{t('llmProxyDetect.report.targetIdentity')}</p>
    <div className="bg-[#eff4ff] p-4 rounded-lg border border-gray-200">
            <p className="font-mono text-sm font-medium break-all">{targetIdentity}</p>
                      </div>
                    </div>
                    <div className="space-y-2">
          <p className="text-[10px] font-bold text-gray-600 uppercase tracking-widest">{t('llmProxyDetect.report.actualIdentity')}</p>
              <div className="bg-[#eff4ff] p-4 rounded-lg border border-gray-200 flex items-center justify-between">
  <p className="font-mono text-sm font-medium break-all">{actualIdentity}</p>
                        {isRisk ? (
                          <AlertTriangle className="shrink-0 ml-2" size={18} style={{ color: scoreColor.label }} />
                        ) : (
                          <CheckCircle2 className="shrink-0 ml-2" size={18} style={{ color: scoreColor.label }} />
                        )}
                      </div>
                    </div>
                  </div>
                </div>
                <div className="pt-6 space-y-4">
                  {speedRows.map((row) => (
                    <div key={row.label}>
                      <div className="flex justify-between mb-2">
                        <span className="text-xs font-semibold text-gray-600">{row.label}</span>
                        <span className="text-xs font-bold text-gray-900">{row.value}</span>
                      </div>
                      <div className="h-2 w-full bg-[#dce9ff] rounded-full overflow-hidden">
                        <div className={`h-full ${row.color} rounded-full`} style={{ width: row.width }}></div>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

   {/* Fingerprint distribution matching (only in full mode) */}
         {reportResult?.algorithm === 'full' && reportResult?.detail?.fingerprint && (
      <FingerprintCard
        fingerprint={reportResult.detail.fingerprint}
      bestModel={reportResult.detail.best_model}
     />
            )}

         {/* Detailed Findings Table */}
               <Card className="rounded-3xl bg-white/70 backdrop-blur-md border border-gray-100 shadow-[0_10px_30px_-10px_rgba(11,28,48,0.05),0_4px_12px_-5px_rgba(11,28,48,0.02)] overflow-hidden">
          <div className="p-6 bg-white/50 border-b border-gray-200 flex flex-col sm:flex-row justify-between sm:items-center gap-3">
        <h2 className="text-xl font-bold text-gray-900">{t('llmProxyDetect.report.anomalyFindings')}</h2>
          <div className="flex gap-2">
           <div className="flex items-center gap-1 px-2.5 py-1 bg-white border border-gray-200 rounded-full">
        <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
             <span className="text-[11px] font-bold text-gray-600">{t('llmProxyDetect.report.passedCount', { count: passedCount })}</span>
          </div>
  <div className="flex items-center gap-1 px-2.5 py-1 bg-white border border-gray-200 rounded-full">
                    <span className="w-2 h-2 rounded-full bg-rose-400"></span>
                    <span className="text-[11px] font-bold text-gray-600">{t('llmProxyDetect.report.failedCount', { count: failedCount })}</span>
                  </div>
                </div>
              </div>
              <div className="overflow-hidden">
                <table className="w-full text-left border-collapse table-fixed">
                  <colgroup>
                    <col className="w-56" />
                    <col />
                    <col className="w-32" />
                  </colgroup>
                <thead className="bg-[#eff4ff]/50 border-b border-gray-200">
                    <tr>
                      <th className="px-6 py-4 text-[11px] font-bold text-gray-600 uppercase tracking-widest whitespace-nowrap">{t('llmProxyDetect.report.colItem')}</th>
                      <th className="px-6 py-4 text-[11px] font-bold text-gray-600 uppercase tracking-widest">{t('llmProxyDetect.report.colDescription')}</th>
                     <th className="px-6 py-4 text-[11px] font-bold text-gray-600 uppercase tracking-widest whitespace-nowrap">{t('llmProxyDetect.report.colResult')}</th>
                    </tr>
                  </thead>
                  <tbody className="text-sm">
                    {displayFindings.length === 0 ? (
                      <tr>
                        <td colSpan={3} className="px-6 py-10 text-center text-gray-600">
                          {t('llmProxyDetect.report.noFindings')}
                        </td>
                      </tr>
                    ) : (
                      displayFindings.map((item, index) => {
                        const verdict = mapVerdict(item.severity);
                        const isPass = isPassSeverity(item.severity);
                        return (
                <tr
       key={index}
   className={`border-b border-[#c7c4d7]/30 hover:bg-[#5D5FEF]/5 transition-all cursor-default hover:translate-x-1 ${
       index % 2 === 1 ? 'bg-[#eff4ff]' : ''
  }`}
         >
   <td className="px-6 py-4 font-semibold text-[#5D5FEF] whitespace-nowrap">{item.title}</td>
          <td className="px-6 py-4 text-gray-600 break-words">{item.meaning}</td>
 <td className="px-6 py-4 whitespace-nowrap">
      <span
    className={`inline-flex items-center gap-1.5 font-bold ${
  isPass ? 'text-emerald-500' : 'text-rose-500'
}`}
   >
  {isPass ? (
  <CheckCircle2 size={16} className="shrink-0" />
           ) : (
       <AlertTriangle size={16} className="shrink-0" />
        )}
           {verdict}
                   </span>
   </td>
      </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </Card>

            {/* Footer */}
            <div className="mt-12 flex justify-center items-center pb-2">
              <span className="text-sm text-gray-400 mr-4">Powered by:</span>
              <img src="/images/zhuque.png" alt="zhuque" className="h-9 w-auto" />
            </div>
          </div>
        </main>
      </div>
    );
  }

  // ============ Detection form view ============
  return (
    <div className="h-screen bg-gray-50 flex flex-col overflow-hidden">
      {/* Top Navigation Bar (shared Header, same as user manual) */}
      <Header backButtonLeftSlot={<LanguageSwitcher />} />

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
       {/* Page Header - Hero */}
     <header className="mb-12 flex flex-col items-center text-center gap-6 pt-8 pb-2">
      <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/60 border border-[#5D5FEF]/15 text-[#5D5FEF] text-sm font-medium shadow-sm backdrop-blur-md">
   <span className="w-2 h-2 rounded-full bg-[#5D5FEF] animate-pulse" />
 <span>{t('llmProxyDetect.page.heroBadge')}</span>
     </div>
     <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-gray-900 max-w-4xl leading-[1.1]">
     {t('llmProxyDetect.page.title')}
     </h1>
     <p className="text-base sm:text-lg text-gray-500 max-w-2xl leading-relaxed">
      {t('llmProxyDetect.page.subtitle')}
     </p>
          </header>

          {/* Bento Grid Layout */}
          <div className="grid grid-cols-12 gap-6">
            {/* Form Column (full width) */}
            <div className="col-span-12 space-y-6">
        {/* Target Endpoint Card */}
      <Card className="rounded-3xl bg-white/70 backdrop-blur-md border border-gray-100 shadow-[0_10px_30px_-10px_rgba(11,28,48,0.05),0_4px_12px_-5px_rgba(11,28,48,0.02)]">
                <CardHeader className="pb-6">
                  <CardTitle className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <Cable className="text-blue-600" size={24} />
                    {t('llmProxyDetect.targetEndpoint.title')}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* LLM Model & Scan Mode Row */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <Label className="text-sm font-bold text-gray-900 mb-2 uppercase tracking-wide block">
                        {t('llmProxyDetect.targetEndpoint.llmModel')}
                      </Label>
                      <Select value={model} onValueChange={handleModelChange}>
                        <SelectTrigger className="border-gray-200 bg-white focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600">
                          <SelectValue placeholder={t('llmProxyDetect.targetEndpoint.selectModelPlaceholder')} />
                        </SelectTrigger>
                        <SelectContent>
                          {loadingModels && (
                            <div className="px-2 py-2 text-sm text-gray-500">{t('llmProxyDetect.targetEndpoint.loading')}</div>
                          )}
                          {platformModels.length > 0 && (
                            <>
                              <div className="px-2 py-1.5 text-[11px] font-bold uppercase tracking-wider text-gray-500">
                                {t('llmProxyDetect.targetEndpoint.platformModelsGroup')}
                              </div>
                              {platformModels.map((m) => (
                                <SelectItem key={m.model_id} value={m.model_id}>
                                  {m.model.model}
                                </SelectItem>
                              ))}
                              <div className="my-1 h-px bg-gray-200" />
                            </>
                          )}
                          {loadingRelayModels && (
                            <div className="px-2 py-2 text-sm text-gray-500">{t('llmProxyDetect.targetEndpoint.loading')}</div>
                          )}
                          {relayModels.length > 0 && (
                            <>
                              <div className="px-2 py-1.5 text-[11px] font-bold uppercase tracking-wider text-gray-500">
                                {t('llmProxyDetect.targetEndpoint.builtInModelsGroup')}
                              </div>
                              {relayModels.map((m) => (
                                <SelectItem key={m.id} value={m.id}>
                                  {m.name}
                                </SelectItem>
                              ))}
                              <div className="my-1 h-px bg-gray-200" />
                            </>
                          )}
                          {!loadingRelayModels && relayModels.length === 0 && (
                            <div className="px-2 py-2 text-sm text-gray-500">{t('llmProxyDetect.targetEndpoint.noBuiltInModels')}</div>
                          )}
                          <SelectItem value="custom">{t('llmProxyDetect.targetEndpoint.customOption')}</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label className="text-sm font-bold text-gray-900 mb-2 uppercase tracking-wide block">
                        {t('llmProxyDetect.targetEndpoint.scanMode')}
                      </Label>
                      <div className="flex items-center gap-6 h-[42px]">
                        <label className="flex items-center gap-2 cursor-pointer group">
                          <input
                            type="radio"
                            name="scan_mode"
                            checked={scanMode === 'quick'}
                            onChange={() => setScanMode('quick')}
                            className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                          />
                          <span className="text-sm group-hover:text-blue-600 transition-colors">{t('llmProxyDetect.targetEndpoint.scanModeQuick')}</span>
                        </label>
                        {fullAuditSupported ? (
                          <label className="flex items-center gap-2 cursor-pointer group">
                            <input
                              type="radio"
                              name="scan_mode"
                              checked={scanMode === 'full'}
                              onChange={() => setScanMode('full')}
                              className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                            />
                            <span className="text-sm group-hover:text-blue-600 transition-colors">{t('llmProxyDetect.targetEndpoint.scanModeFull')}</span>
                          </label>
                        ) : (
                          <label className="flex items-center gap-2 cursor-not-allowed opacity-50">
                            <input
                              type="radio"
                              name="scan_mode"
                              checked={false}
                              disabled
                              readOnly
                              className="w-4 h-4 text-blue-600 border-gray-300 focus:ring-blue-500"
                            />
                            <span className="text-sm text-gray-500">{t('llmProxyDetect.targetEndpoint.scanModeFull')}</span>
                          </label>
                        )}
                      </div>
                    </div>
                  </div>

                  {isPlatformModel ? (
                    /* Platform-configured model: use saved Endpoint & Key, no manual input needed */
                    <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                      <div className="flex items-center gap-2 mb-1">
                        <CheckCircle2 size={16} className="text-blue-600" />
                        <span className="text-sm font-semibold text-gray-900">
                          {t('llmProxyDetect.targetEndpoint.platformSelectedTitle')}
                        </span>
                      </div>
                      <p className="text-xs text-gray-600">
                        {t('llmProxyDetect.targetEndpoint.platformSelectedDesc')}
                      </p>
                      <div className="mt-3 space-y-1 font-mono text-xs text-gray-600">
                        <div>{t('llmProxyDetect.targetEndpoint.endpointLabelPlatform')}: {selectedPlatformModel.model.base_url}</div>
                        <div>{t('llmProxyDetect.targetEndpoint.apiKeyLabelPlatform')}: {maskToken(selectedPlatformModel.model.token)}</div>
                      </div>
                    </div>
                  ) : (
                    <>
                      {/* Custom Model Name (only for manually entered, non-built-in models) */}
                      {model === 'custom' && (
                        <div>
                          <Label className="text-sm font-bold text-gray-900 mb-2 uppercase tracking-wide block">
                            {t('llmProxyDetect.targetEndpoint.customModelName')}
                          </Label>
                          <Input
                            value={customModel}
                            onChange={(e) => setCustomModel(e.target.value)}
                            placeholder={t('llmProxyDetect.targetEndpoint.customModelPlaceholder')}
                            className="border-gray-200 font-mono text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                          />
                        </div>
                      )}

                      {/* Relay API URL */}
                      <div>
                        <Label className="text-sm font-bold text-gray-900 mb-2 uppercase tracking-wide block">
                          {t('llmProxyDetect.targetEndpoint.relayApiUrl')}
                        </Label>
                        <Input
                          value={endpointUrl}
                          onChange={(e) => setEndpointUrl(e.target.value)}
                          placeholder={t('llmProxyDetect.targetEndpoint.relayApiUrlPlaceholder')}
                          className="border-gray-200 font-mono text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                        />
                      </div>

        {/* API Key */}
   <div>
               <div className="flex items-center justify-between mb-2 gap-3 flex-wrap">
           <Label className="text-sm font-bold text-gray-900 uppercase tracking-wide block">
      {t('llmProxyDetect.targetEndpoint.apiKey')}
     </Label>
          <span
     className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-[11px] font-medium"
         title={t('llmProxyDetect.targetEndpoint.apiKeySecurityHint')}
 >
         <ShieldCheck size={14} className="shrink-0" />
  {t('llmProxyDetect.targetEndpoint.apiKeySecurityHint')}
         </span>
         </div>
      <div className="relative">
                          <Input
                            type={showApiKey ? 'text' : 'password'}
                            value={apiKey}
                            onChange={(e) => setApiKey(e.target.value)}
                            placeholder={t('llmProxyDetect.targetEndpoint.apiKeyPlaceholder')}
                            className="pr-10 border-gray-200 font-mono text-sm focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600"
                          />
                          <button
                            onClick={() => setShowApiKey(!showApiKey)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-600 hover:text-blue-600 transition-colors"
                          >
                            {showApiKey ? <EyeOff size={18} /> : <Eye size={18} />}
                          </button>
                        </div>
                      </div>
                    </>
                  )}

                  {/* Action Buttons */}
                  <div className="mt-10 flex items-center justify-end gap-3">
                    <Button
                      variant="outline"
                      onClick={handleResetDefaults}
                      className="border-gray-200 text-gray-600 hover:bg-gray-50 transition-all"
                    >
                      <RotateCcw size={18} className="mr-0" />
                      {t('llmProxyDetect.targetEndpoint.resetDefaults')}
                    </Button>
                    <Button
                      onClick={handleStartDetection}
                      disabled={isDetecting || !canStart}
                      className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-10 py-3 shadow-lg shadow-blue-600/20 active:scale-95 transition-all"
                    >
                      <Zap size={18} className="mr-0" />
                      {isDetecting ? t('llmProxyDetect.targetEndpoint.detecting') : t('llmProxyDetect.targetEndpoint.startDetection')}
                    </Button>
                  </div>
                </CardContent>
              </Card>

            </div>

     {/* Detection Principle & Advantages (full width, below the form) */}
            <div className="col-span-12">
    {/* Section header */}
         <div className="flex flex-col items-center text-center mb-16 mt-20">
       <div className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-[#5D5FEF]/5 border border-[#5D5FEF]/10 text-[#5D5FEF] text-[11px] font-semibold uppercase tracking-[0.2em] mb-6">
   <Sparkles size={13} />
 <span>{t('llmProxyDetect.principle.badge')}</span>
         </div>
       <h2 className="text-2xl sm:text-3xl md:text-[34px] font-bold tracking-tight max-w-3xl leading-[1.25] bg-gradient-to-br from-gray-900 to-[#5D5FEF] bg-clip-text text-transparent">
 {t('llmProxyDetect.principle.heroTitle')}
      </h2>
<p className="mt-6 text-sm sm:text-base text-gray-500 leading-relaxed max-w-2xl">
{t('llmProxyDetect.principle.heroSubtitle')}
     </p>
          </div>

     {/* Three-principle cards */}
     <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
      {[
      {
  key: 'card1',
           num: '01',
  Icon: Radar,
     accent: '#3B82F6',
       accentSoft: 'rgba(59,130,246,0.10)',
   accentSoft2: 'rgba(59,130,246,0.04)',
        chipBg: 'bg-blue-50',
      chipText: 'text-blue-700',
            chipBorder: 'border-blue-100/80',
     iconGradient: 'from-blue-50 to-blue-100/50',
   iconBorder: 'border-blue-200/50',
     iconText: 'text-blue-600',
        checkBg: 'bg-blue-50',
     checkText: 'text-blue-500',
    },
   {
      key: 'card2',
  num: '02',
     Icon: Sigma,
  accent: '#10B981',
    accentSoft: 'rgba(16,185,129,0.10)',
      accentSoft2: 'rgba(16,185,129,0.04)',
      chipBg: 'bg-emerald-50',
   chipText: 'text-emerald-700',
       chipBorder: 'border-emerald-100/80',
   iconGradient: 'from-emerald-50 to-emerald-100/50',
     iconBorder: 'border-emerald-200/50',
   iconText: 'text-emerald-600',
     checkBg: 'bg-emerald-50',
         checkText: 'text-emerald-500',
   },
    {
key: 'card3',
   num: '03',
  Icon: KeyRound,
         accent: '#8B5CF6',
    accentSoft: 'rgba(139,92,246,0.10)',
       accentSoft2: 'rgba(139,92,246,0.04)',
         chipBg: 'bg-purple-50',
    chipText: 'text-purple-700',
 chipBorder: 'border-purple-100/80',
     iconGradient: 'from-purple-50 to-purple-100/50',
iconBorder: 'border-purple-200/50',
iconText: 'text-purple-600',
     checkBg: 'bg-purple-50',
     checkText: 'text-purple-500',
      },
    ].map(({ key, num, Icon, accent, accentSoft, accentSoft2, chipBg, chipText, chipBorder, iconGradient, iconBorder, iconText, checkBg, checkText }) => (
      <div
     key={key}
   className={`group relative rounded-3xl bg-white/70 backdrop-blur-md border border-gray-100 shadow-[0_10px_30px_-10px_rgba(11,28,48,0.05),0_4px_12px_-5px_rgba(11,28,48,0.02)] hover:-translate-y-1 hover:shadow-[0_20px_40px_-10px_rgba(40,36,190,0.08)] transition-all duration-500 overflow-hidden`}
    >
         {/* soft radial glow at top */}
        <div
      className="absolute inset-x-0 top-0 h-40 pointer-events-none opacity-70 group-hover:opacity-100 transition-opacity"
            style={{
         background: `radial-gradient(120% 100% at 50% 0%, ${accentSoft} 0%, ${accentSoft2} 40%, transparent 70%)`,
    }}
      aria-hidden
/>
   {/* watermark number */}
             <span
       className="pointer-events-none absolute -right-3 -top-6 font-black text-[180px] leading-none select-none tracking-tighter transition-colors duration-500"
           style={{ color: accent, opacity: 0.05 }}
           aria-hidden
        >
         {num}
       </span>

         <div className="relative p-8 sm:p-10 flex flex-col h-full">
   {/* icon + tag */}
 <div className="flex items-start justify-between mb-6">
 <div
      className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${iconGradient} border ${iconBorder} ${iconText} flex items-center justify-center shadow-sm`}
    >
         <Icon size={30} strokeWidth={2} />
     </div>
        <span className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-[10px] font-bold uppercase tracking-widest border ${chipBg} ${chipText} ${chipBorder} shadow-sm`}>
     {t(`llmProxyDetect.principle.${key}.tag`)}
      </span>
          </div>

  <h4 className="text-xl font-bold text-gray-900 leading-snug tracking-tight mb-3">
 {t(`llmProxyDetect.principle.${key}.title`)}
        </h4>
   <p className="text-sm text-gray-500 leading-relaxed mb-6 font-medium">
 {t(`llmProxyDetect.principle.${key}.desc`)}
 </p>

   <ul className="space-y-4 mt-auto">
      {(t(`llmProxyDetect.principle.${key}.points`, { returnObjects: true }) as string[]).map((point, i) => (
         <li key={i} className="flex items-start gap-3">
    <span
     className={`shrink-0 mt-0.5 w-6 h-6 rounded-full ${checkBg} flex items-center justify-center`}
    aria-hidden
     >
  <CheckCircle2 size={14} strokeWidth={2.5} className={checkText} />
         </span>
  <span className="text-[13px] text-gray-600 leading-relaxed">{point}</span>
        </li>
          ))}
     </ul>
     </div>
  </div>
  ))}
 </div>

   {/* Four Platform Advantages */}
 <div className="mt-20 relative py-8">
  <div className="relative z-10 flex flex-col gap-14">
        <div className="flex flex-col items-center gap-4 text-center">
          <h3 className="text-2xl sm:text-3xl font-bold text-gray-900 tracking-tight">
       {t('llmProxyDetect.principle.advantagesTitle')}
  </h3>
      <div className="w-16 h-1 bg-gradient-to-r from-[#5D5FEF] to-transparent rounded-full" />
     </div>

   <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
          {[
        { key: 'blackbox', Icon: Lock },
        { key: 'evidence', Icon: Layers },
       { key: 'fingerprint', Icon: Fingerprint },
     { key: 'report', Icon: FileCheck2 },
  ].map(({ key, Icon }) => (
           <div
        key={key}
        className="group bg-white/80 backdrop-blur-md border border-white p-8 rounded-3xl shadow-sm hover:shadow-xl hover:shadow-[#5D5FEF]/5 transition-all duration-300 flex flex-col items-center text-center"
          >
      <div className="w-16 h-16 rounded-2xl bg-slate-50 text-slate-700 flex items-center justify-center mb-6 group-hover:scale-110 group-hover:bg-[#5D5FEF]/10 group-hover:text-[#5D5FEF] transition-all duration-300">
  <Icon size={30} strokeWidth={1.5} />
     </div>
    <h4 className="text-base font-bold text-gray-900 mb-3">
     {t(`llmProxyDetect.principle.advantages.${key}.title`)}
          </h4>
     <p className="text-sm text-gray-500 leading-relaxed">
      {t(`llmProxyDetect.principle.advantages.${key}.desc`)}
    </p>
   </div>
     ))}
   </div>

          <div className="text-center">
    <p className="inline-block px-4 py-2 text-xs text-gray-500/80 leading-relaxed max-w-3xl">
      {t('llmProxyDetect.principle.footnote')}
       </p>
  </div>
        </div>
   </div>
  </div>

          </div>

          {/* Footer */}
          <div className="mt-12 flex justify-center items-center pb-2">
            <span className="text-sm text-gray-400 mr-4">Powered by:</span>
            <img
              src="/images/zhuque.png"
              alt="zhuque"
              className="h-9 w-auto"
            />
          </div>
        </div>
      </main>

      {/* Live detection overlay (SSE progress) */}
      {phase !== 'idle' && (
        <div className="fixed inset-0 z-[100] bg-black/30 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-lg p-6">
            <div className="flex items-center gap-3 mb-2">
              <span
                className={`w-3 h-3 rounded-full ${
                  phase === 'failed' ? 'bg-red-500' : 'bg-blue-600 animate-pulse'
                }`}
              />
              <h3 className="text-lg font-bold text-gray-900">
                {phase === 'connecting'
                  ? t('llmProxyDetect.overlay.connecting')
                  : phase === 'running'
                  ? t('llmProxyDetect.overlay.running')
                  : phase === 'failed'
                  ? t('llmProxyDetect.overlay.failed')
                  : t('llmProxyDetect.overlay.completed')}
              </h3>
            </div>

            <p className="text-sm text-gray-600 mb-3">{stageLabel}</p>

            {phase === 'failed' && errorMessage ? (
              <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3 mb-3 whitespace-pre-wrap break-words">
                {errorMessage}
              </div>
            ) : (
              <>
                {progressRate !== null ? (
                  <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden mb-1">
                    <div
                      className="h-full bg-blue-600 rounded-full transition-all duration-300"
                      style={{ width: `${Math.round(progressRate * 100)}%` }}
                    />
                  </div>
                ) : (
                  phase === 'running' && (
                    <div className="w-full h-2 rounded-full bg-gray-100 overflow-hidden mb-1">
                      <div
                        className="h-full bg-blue-600 rounded-full animate-pulse"
                        style={{ width: '40%' }}
                      />
                    </div>
                  )
                )}
                <p className="text-xs text-gray-400 mb-3">
                  {t('llmProxyDetect.overlay.hint')}
                </p>
              </>
            )}

            {/* SSE event log */}
            <div
              ref={logContainerRef}
              onScroll={handleLogScroll}
              className="bg-gray-900 rounded-lg p-3 h-40 overflow-y-auto font-mono text-[11px] text-green-300 space-y-1"
            >
              {eventMessages.length === 0 ? (
                <div className="text-gray-500">{t('llmProxyDetect.overlay.waitingEvents')}</div>
              ) : (
                eventMessages.map((m, i) => (
                  <div key={i} className="whitespace-pre-wrap break-all">
                    {m}
                  </div>
                ))
              )}
            </div>

            {/* Actions */}
            <div className="mt-4 flex justify-end gap-2">
              {(phase === 'connecting' || phase === 'running') && (
                <Button variant="outline" onClick={cancelDetection}>
                  {t('llmProxyDetect.overlay.cancel')}
                </Button>
              )}
              {phase === 'failed' && (
                <>
                  <Button variant="outline" onClick={() => setPhase('idle')}>
                    {t('llmProxyDetect.overlay.close')}
                  </Button>
                  <Button
                    onClick={handleStartDetection}
                    className="bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    {t('llmProxyDetect.overlay.retry')}
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LLMProxyDetectPage;
