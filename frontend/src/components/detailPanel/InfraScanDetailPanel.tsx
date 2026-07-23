import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ExecutionStep, InfraScanResult, InfraScanTarget, InfraScanVulnerability } from '../../types';
import {
  Clock, 
  CheckCircle, 
  XCircle, 
  Play,
  Calendar,
  Timer,
  Info,
  AlertTriangle,
  FileText,
  BookOpen,
  Bug,
  ShieldCheck,
  Globe,
  Server,
  BarChart3,
  Maximize,
  Minimize,
  Share2,
  Download,
  ZoomIn,
  SearchCode
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Separator } from '../ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '../ui/tooltip';
import { Dialog, DialogContent } from '../ui/dialog';
import { useApp } from '../../context/AppContext';
import CodeHighlight from './CodeHighlight';
import { useReportPrint } from './useReportPrint';

interface InfraScanDetailPanelProps {
  step: ExecutionStep | null;
  stepIndex?: number;
  infraScanResult?: InfraScanResult;
  selectedTool?: {
    step: ExecutionStep;
    subStepIndex: number;
    toolIndex: number;
  } | null;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
  hideFullscreenButton?: boolean;
  sessionId?: string;
}

const InfraScanDetailPanel: React.FC<InfraScanDetailPanelProps> = ({ 
  step, 
  stepIndex, 
  infraScanResult, 
  selectedTool,
  isFullscreen = false, 
  onToggleFullscreen,
  hideFullscreenButton = false,
  sessionId
}) => {
  const { t } = useTranslation();
  const { state } = useApp();
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [previewImage, setPreviewImage] = useState<{ image: string; reason?: string; summary?: string } | null>(null);
  const currentTask = state.tasks.find(
    task => task.id === state.currentTaskId,
  );
  const currentSessionId = sessionId || currentTask?.id;

  const handleShare = () => {
    if (currentSessionId) {
      const shareUrl = `${window.location.origin}/report/${currentSessionId}`;
      window.open(shareUrl, '_blank');
    }
  };

  const handleDownloadPdf = useReportPrint(
    panelRef,
    `A.I.G ${t('task.taskType.aiInfraScan')}`
  );

  // Handle scroll events and detect whether the user scrolled manually
  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10; // 10px tolerance
    setShouldAutoScroll(isAtBottom);
  };

  // Auto-scroll to the bottom
  const scrollToBottom = () => {
    if (scrollContainerRef.current && shouldAutoScroll) {
      scrollContainerRef.current.scrollTop = scrollContainerRef.current.scrollHeight;
    }
  };

  // Watch actionLog changes and auto-scroll
  useEffect(() => {
    if (step?.subSteps) {
      const hasActionLogChanges = step.subSteps.some(subStep => 
        subStep.toolUsed?.some(tool => tool.actionLog)
      );
      if (hasActionLogChanges) {
        // Use setTimeout to scroll only after the DOM update is complete
        setTimeout(scrollToBottom, 100);
      }
    }
  }, [step?.subSteps, shouldAutoScroll]);

  if (!step && !infraScanResult) {
    return (
      <TooltipProvider>
        <div className="w-full min-w-[320px] bg-white border-l border-gray-200 flex items-center justify-center h-full">
          <div className="text-center text-gray-500 p-6">
            <Info className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <h3 className="font-medium mb-2">{t('infraScan.selectStep')}</h3>
            <p className="text-sm">{t('infraScan.selectStepDescription')}</p>
          </div>
        </div>
        <Dialog open={!!previewImage} onOpenChange={(open) => !open && setPreviewImage(null)}>
          <DialogContent className="max-w-[90vw] max-h-[90vh] p-0 flex flex-col">
            {previewImage && (
              <>
                <img
                  src={previewImage.image}
                  alt={t('infraScan.target.screenshot')}
                  className="w-full h-auto max-h-[calc(90vh-120px)] object-contain"
                />
                {previewImage.reason && (
                  <div className="p-4 border-t border-gray-200 bg-gray-50">
                    <div className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                      <SearchCode className="w-4 h-4 mr-1 text-gray-500" />
                      {t('infraScan.target.agentEvaluation')}
                    </div>
                    <div className="text-sm text-gray-600">
                      {previewImage.reason}
                    </div>
                  </div>
                )}
              </>
            )}
          </DialogContent>
        </Dialog>
      </TooltipProvider>
    );
  }

  const getStatusIcon = (status: ExecutionStep['status']) => {
    switch (status) {
      case 'todo':
        return <Clock className="w-5 h-5 text-amber-500" />;
      case 'doing':
        return <Play className="w-5 h-5 text-blue-500 animate-pulse" />;
      case 'done':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: ExecutionStep['status']) => {
    const variants = {
      todo: 'secondary',
      doing: 'default',
      done: 'default',
    } as const;

    const labels = {
      todo: t('infraScan.status.todo'),
      doing: t('infraScan.status.doing'),
      done: t('infraScan.status.done'),
    };

    return (
      <Badge variant={variants[status]} className="text-xs">
        {labels[status]}
      </Badge>
    );
  };

  const formatTime = (date?: Date | string) => {
    if (!date) return '-';
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return new Intl.DateTimeFormat('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(dateObj);
  };

  const formatDuration = (start?: Date | string, end?: Date | string) => {
    if (!start) return '-';
    const startObj = typeof start === 'string' ? new Date(start) : start;
    const endObj = end ? (typeof end === 'string' ? new Date(end) : end) : new Date();
    const duration = Math.round((endObj.getTime() - startObj.getTime()) / 1000);
    
    if (duration < 60) return `${duration}${t('infraScan.timeUnits.seconds')}`;
    if (duration < 3600) return `${Math.round(duration / 60)}${t('infraScan.timeUnits.minutes')}`;
    return `${Math.round(duration / 3600)}${t('infraScan.timeUnits.hours')}`;
  };

  const getSeverityColor = (severity: string) => {
    switch (severity?.toLowerCase() || '') {
      case 'critical':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'high':
        return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getProgressColor = (score: number) => {
    if (score >= 80) return 'bg-green-600';
    if (score >= 60) return 'bg-yellow-600';
    return 'bg-red-600';
  };

  const renderVulnerability = (vulnerability: InfraScanVulnerability, index: number) => (
    <Card key={index} className="mb-4 shadow-lg border border-gray-100">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center min-w-0 flex-1">
            <AlertTriangle className="w-4 h-4 mr-2 text-red-500 flex-shrink-0" />
            <div className="min-w-0 flex-1">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="text-sm font-semibold leading-none tracking-tight truncate cursor-default">
                    {vulnerability.summary || t('infraScan.vulnerability.unknown')}
                    {vulnerability.cve && (
                      <span className="text-gray-500 ml-1">
                        ({vulnerability.cve})
                      </span>
                    )}
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="max-w-xs">
                    {vulnerability.summary || t('infraScan.vulnerability.unknown')}
                    {vulnerability.cve && (
                      <span className="text-gray-400 ml-1">
                        ({vulnerability.cve})
                      </span>
                    )}
                  </p>
                </TooltipContent>
              </Tooltip>
            </div>
          </div>
          <Badge className={`text-xs ${getSeverityColor(vulnerability.severity)} flex-shrink-0 ml-2`}>
            {vulnerability.severity || 'unknown'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-0 space-y-3">
        <div>
          <div className="text-sm font-medium text-gray-700 my-2 flex items-center">
            <FileText className="w-4 h-4 mr-1 text-gray-500" />
            {t('infraScan.vulnerability.details')}
          </div>
          <div className="text-sm text-gray-600 prose prose-sm max-w-none">
            <CodeHighlight>
              {vulnerability.details || ''}
            </CodeHighlight>
          </div>
        </div>
        {vulnerability.security_advise && (
          <>
            <Separator />
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                <ShieldCheck className="w-4 h-4 mr-1 text-gray-500" />
                {t('infraScan.vulnerability.securityAdvise')}
              </div>
              <div className="text-sm text-gray-600">
                {vulnerability.security_advise}
              </div>
            </div>
          </>
        )}
        {vulnerability.references && vulnerability.references.length > 0 && (
          <>
            <Separator />
            <div>
              <div className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                <BookOpen className="w-4 h-4 mr-1 text-gray-500" />
                {t('infraScan.vulnerability.references')}
              </div>
              <div className="text-sm text-gray-600 space-y-1">
                {vulnerability.references.map((ref, idx) => (
                  <div key={idx} className="text-blue-600 hover:text-blue-800">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <a 
                          href={ref} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="block truncate cursor-pointer"
                        >
                          {ref}
                        </a>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p className="max-w-xs break-all">
                          {ref}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );

  const renderTarget = (target: InfraScanTarget, index: number) => (
    <Card key={index} className="mb-4 shadow-lg border border-gray-100">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center">
            <Globe className="w-4 h-4 mr-2 text-blue-500" />
            {target.title || target.target_url || t('infraScan.target.unknown')}
          </CardTitle>
          <div className="flex items-center space-x-2">
            {target.vulnerabilities && target.vulnerabilities.length > 0 && (
              <Badge variant="destructive" className="text-xs">
                {target.vulnerabilities.length} {t('infraScan.target.vulnerabilityCount')}
              </Badge>
            )}
          </div>
        </div>
        <div className="text-xs text-gray-500 flex items-center space-x-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="truncate max-w-[180px]">
                URL: {target.target_url || t('infraScan.target.unknownUrl')}
              </div>
            </TooltipTrigger>
            <TooltipContent>
              <p>{target.target_url || t('infraScan.target.unknownUrl')}</p>
            </TooltipContent>
          </Tooltip>
          {target.fingerprint && (
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="truncate max-w-[120px]">
                  <span className="mx-1">|</span>
                  {t('infraScan.target.fingerprint')}: {target.fingerprint}
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>{target.fingerprint}</p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        {(target.screenshot || (target as any).summary) && (
          <div className="mb-4">
            {(target as any).summary && (
              <div className="text-sm text-gray-500 mb-2">
                {(target as any).summary}
              </div>
            )}
            {target.screenshot && (
              <div className="overflow-hidden flex justify-start relative">
                <img
                  src={target.screenshot}
                  alt={t('infraScan.target.screenshot')}
                  className="w-auto h-auto max-w-full object-contain cursor-pointer hover:opacity-80 transition-opacity border border-gray-200 rounded"
                  onClick={() => setPreviewImage({ image: target.screenshot, reason: target.reason, summary: (target as any).summary })}
                  onError={(e) => {
                    const imgElement = e.target as HTMLImageElement;
                    imgElement.style.display = 'none';
                  }}
                />
                <div className="absolute top-0 right-0 bg-black/50 hover:bg-black/70 rounded-bl rounded-tr p-1 cursor-pointer transition-colors" onClick={() => setPreviewImage({ image: target.screenshot, reason: target.reason, summary: (target as any).summary })}>
                  <SearchCode className="w-3 h-3 text-white" />
                </div>
              </div>
            )}
          </div>
        )}
        {target.vulnerabilities && target.vulnerabilities.length > 0 ? (
          <div className="space-y-3">
            {target.vulnerabilities.map((vulnerability, idx) => 
              renderVulnerability(vulnerability, idx)
            )}
          </div>
        ) : (
          <div className="text-center text-gray-500 py-4">
            <CheckCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">{t('infraScan.target.noVulnerabilities')}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );

  // If only infraScanResult is present, show the scan results
  if (infraScanResult && !step) {
    return (
      <TooltipProvider>
        <div className="bg-white border-l border-gray-200 flex justify-center flex-col w-full h-full transition-all duration-300 ease-in-out">
          {/* Header */}
          <div className="p-4 border-b border-gray-200 flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Bug className="w-5 h-5 text-blue-500" />
                <span className="text-sm font-medium text-gray-500">A.I.G {t('infraScan.scanResult')}</span>
              </div>
              <div className="flex items-center space-x-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={handleDownloadPdf}
                      className="p-1.5 rounded-md hover:bg-gray-100 transition-colors cursor-pointer"
                    >
                      <Download className="w-4 h-4 text-gray-500" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t('redteam.downloadDetailedReport')}</p>
                  </TooltipContent>
                </Tooltip>
                {currentSessionId && !hideFullscreenButton && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={handleShare}
                        className="p-1.5 rounded-md hover:bg-gray-100 transition-colors cursor-pointer"
                      >
                        <Share2 className="w-4 h-4 text-gray-500" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{t('infraScan.share')}</p>
                    </TooltipContent>
                  </Tooltip>
                )}
                {onToggleFullscreen && !hideFullscreenButton && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={onToggleFullscreen}
                        className="p-1.5 rounded-md hover:bg-gray-100 transition-colors cursor-pointer"
                      >
                        {isFullscreen ? (
                          <Minimize className="w-4 h-4 text-gray-500" />
                        ) : (
                          <Maximize className="w-4 h-4 text-gray-500" />
                        )}
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{isFullscreen ? t('infraScan.exitFullscreen') : t('infraScan.fullscreen')}</p>
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
            </div>
          </div>

          {/* Scan result content */}
          <div ref={panelRef} className={`flex-1 overflow-y-auto min-h-0 transition-all duration-300 ease-in-out scrollbar-hover print-content-wrapper ${
            isFullscreen ? 'mt-4' : ''
          }`}>
            <div className={`p-4 space-y-6 ${
              isFullscreen
                ? 'max-w-[1200px] w-full mx-auto'
                : 'w-full'
            }`}>
              {/* Scan statistics */}
              <Card className="shadow-lg border border-gray-100">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center">
                    <Server className="w-4 h-4 mr-2" />
                    {t('infraScan.scan.reportSummary')}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm text-gray-600">{t('infraScan.scan.securityScore')}</span>
                    <span className={`text-lg font-bold ${getScoreColor(infraScanResult.score)}`}>
                      {infraScanResult.score}/100
                    </span>
                  </div>
                  <div className="mb-4">
                    <Progress 
                      value={infraScanResult.score} 
                      className="h-2"
                      color={getProgressColor(infraScanResult.score)}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-14 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">{t('infraScan.scan.targets')}</span>
                      <span className="font-medium">{infraScanResult.results.length} {t('infraScan.target.count')}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">{t('infraScan.scan.vulnerabilities')}</span>
                      <span className={`font-medium ${infraScanResult.total === 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {infraScanResult.total} {t('infraScan.target.count')}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Scan target list */}
              {infraScanResult.results && infraScanResult.results.length > 0 && (
                <div>
                  <div className="flex items-center space-x-2 mb-4">
                    <Globe className="w-5 h-5 text-blue-500" />
                    <span className="font-medium text-gray-900">{t('infraScan.scan.details')}</span>
                  </div>
                  {infraScanResult.results.map((target, index) => 
                    renderTarget(target, index)
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
        <Dialog open={!!previewImage} onOpenChange={(open) => !open && setPreviewImage(null)}>
          <DialogContent className="max-w-[90vw] max-h-[90vh] p-0 flex flex-col">
            {previewImage && (
              <>
                <img
                  src={previewImage.image}
                  alt={t('infraScan.target.screenshot')}
                  className="w-full h-auto max-h-[calc(90vh-120px)] object-contain"
                />
                {previewImage.reason && (
                  <div className="p-4 border-t border-gray-200 bg-gray-50">
                    <div className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                      <SearchCode className="w-4 h-4 mr-1 text-gray-500" />
                      {t('infraScan.target.agentEvaluation')}
                    </div>
                    <div className="text-sm text-gray-600">
                      {previewImage.reason}
                    </div>
                  </div>
                )}
              </>
            )}
          </DialogContent>
        </Dialog>
      </TooltipProvider>
    );
  }

  // Ensure step exists
  if (!step) {
    return (
      <TooltipProvider>
        <div className="w-full min-w-[320px] bg-white border-l border-gray-200 flex items-center justify-center h-full transition-all duration-300 ease-in-out">
          <div className="text-center text-gray-500 p-6">
            <Info className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <h3 className="font-medium mb-2">{t('infraScan.selectStep')}</h3>
            <p className="text-sm">{t('infraScan.selectStepDescription')}</p>
          </div>
        </div>
        <Dialog open={!!previewImage} onOpenChange={(open) => !open && setPreviewImage(null)}>
          <DialogContent className="max-w-[90vw] max-h-[90vh] p-0 flex flex-col">
            {previewImage && (
              <>
                <img
                  src={previewImage.image}
                  alt={t('infraScan.target.screenshot')}
                  className="w-full h-auto max-h-[calc(90vh-120px)] object-contain"
                />
                {previewImage.reason && (
                  <div className="p-4 border-t border-gray-200 bg-gray-50">
                    <div className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                      <SearchCode className="w-4 h-4 mr-1 text-gray-500" />
                      {t('infraScan.target.agentEvaluation')}
                    </div>
                    <div className="text-sm text-gray-600">
                      {previewImage.reason}
                    </div>
                  </div>
                )}
              </>
            )}
          </DialogContent>
        </Dialog>
      </TooltipProvider>
    );
  }

  return (
    <TooltipProvider>
      <div className="bg-white border-l border-gray-200 border-b-0 flex flex-col w-full h-full transition-all duration-300 ease-in-out">
        {/* Header */}
        <div className="p-4 border-b border-gray-200 flex-shrink-0">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-mono text-gray-500 bg-gray-100 px-2 py-1 rounded">
                {stepIndex !== undefined ? (stepIndex + 1).toString().padStart(2, '0') : '--'}
              </span>
              <h3 className="font-semibold text-gray-900 text-lg leading-tight">
                {step.title}
              </h3>
              {getStatusIcon(step.status)}
              {getStatusBadge(step.status)}
            </div>
            <div className="flex items-center space-x-2">
              {currentSessionId && !hideFullscreenButton && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={handleShare}
                      className="p-1.5 rounded-md hover:bg-gray-100 transition-colors cursor-pointer"
                    >
                      <Share2 className="w-4 h-4 text-gray-500" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t('infraScan.share')}</p>
                  </TooltipContent>
                </Tooltip>
              )}
              {onToggleFullscreen && !hideFullscreenButton && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={onToggleFullscreen}
                      className="p-1.5 rounded-md hover:bg-gray-100 transition-colors cursor-pointer"
                    >
                      {isFullscreen ? (
                        <Minimize className="w-4 h-4 text-gray-500" />
                      ) : (
                        <Maximize className="w-4 h-4 text-gray-500" />
                      )}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{isFullscreen ? t('infraScan.exitFullscreen') : t('infraScan.fullscreen')}</p>
                  </TooltipContent>
                </Tooltip>
              )}
            </div>
          </div>
        </div>

        {/* Display tool information */}
        {step.subSteps && step.subSteps.length > 0 && (
          <div 
            ref={scrollContainerRef}
            onScroll={handleScroll}
            className="p-4 flex-1 overflow-y-auto min-h-0 scrollbar-hover print-content-wrapper"
          >
            <div className="space-y-4">
              {step.subSteps.map((subStep, subIndex) => {
                // Check whether any tool in this subStep contains actionLog
                const hasActionLogTools = subStep.toolUsed && subStep.toolUsed.some(tool => 
                  tool.actionLog && tool.actionLog.trim() !== ''
                );
                
                // Skip this subStep when none of its tools has an actionLog
                if (!hasActionLogTools) {
                  return null;
                }
                
                // When a tool is selected, only show the sub-step that owns it
                if (selectedTool && selectedTool.step.id === step.id && selectedTool.subStepIndex !== subIndex) {
                  return null;
                }
                
                return (
                  <div key={subIndex} className="border rounded-lg p-5 bg-gray-50">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center space-x-2">
                        <span className="text-sm font-medium text-gray-900">{subStep.brief}</span>
                        <Badge variant={subStep.status === 'done' ? 'default' : 'secondary'} className="text-xs">
                          {subStep.status === 'done' ? t('infraScan.status.done') : subStep.status === 'doing' ? t('infraScan.status.doing') : t('infraScan.status.todo')}
                        </Badge>
                      </div>
                    </div>
                    {subStep.description && (
                      <div className="text-xs text-gray-500 mb-3">
                        {subStep.description}
                      </div>
                    )}
                    {subStep.toolUsed && subStep.toolUsed.length > 0 && (
                      <div className="space-y-3">
                        {subStep.toolUsed
                          .filter(tool => tool.actionLog && tool.actionLog.trim() !== '') // Only show tools that have actionLog content
                          .map((tool, toolIndex) => {
                            const isSelected = selectedTool && 
                              selectedTool.step.id === step.id && 
                              selectedTool.subStepIndex === subIndex && 
                              selectedTool.toolIndex === toolIndex;
                            
                            // Only show the selected tool, or show all tools when nothing is selected
                            const shouldShow = isSelected || !selectedTool;
                            
                            if (!shouldShow) {
                              return null;
                            }
                            
                            return (
                              <div key={toolIndex} className="border rounded-lg p-5 bg-white">
                                <div className="flex items-center justify-between mb-2">
                                  <div className="flex items-center space-x-2">
                                    <div className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-medium">
                                      {tool.tool || tool.brief}
                                    </div>
                                    <span className="text-sm text-gray-600">
                                      {tool.message.action} {tool.message.param}
                                    </span>
                                    {tool.result && (
                                      <div className="text-sm text-green-600">
                                        {tool.result}
                                      </div>
                                    )}
                                  </div>
                                  <Badge 
                                    variant="outline" 
                                    className={`text-xs ${
                                      tool.status === 'done' 
                                        ? 'bg-green-50 text-green-700 border-green-200' 
                                        : tool.status === 'doing' 
                                        ? 'bg-blue-50 text-blue-700 border-blue-200' 
                                        : 'bg-gray-50 text-gray-700 border-gray-200'
                                    }`}
                                  >
                                    {tool.status === 'done' ? t('infraScan.status.success') : tool.status === 'doing' ? t('infraScan.status.doing') : t('infraScan.status.todo')}
                                  </Badge>
                                </div>
                                {tool.actionLog && (
                                  <div className="py-3 text-sm text-gray-700">
                                    <pre className="whitespace-pre-wrap font-mono text-sm">
                                      {tool.actionLog}
                                    </pre>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Scan results */}
        {step.infraScanResult && (
          <div className="flex-1 overflow-y-auto min-h-0 transition-all duration-300 ease-in-out scrollbar-hover">
            <div className={`p-4 space-y-6 ${
              isFullscreen
                ? 'max-w-[1200px] w-full mx-auto'
                : 'w-full'
            }`}>
              {/* Overall score */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center">
                    <BarChart3 className="w-4 h-4 mr-2" />
                    {t('infraScan.scan.score')}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">安全评分</span>
                    <span className={`text-lg font-bold ${getScoreColor(step.infraScanResult.score)}`}>
                      {step.infraScanResult.score}/100
                    </span>
                  </div>
                  <div className="mt-2">
                    <Progress 
                      value={step.infraScanResult.score} 
                      className="h-2"
                      color={getProgressColor(step.infraScanResult.score)}
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Scan statistics */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center">
                    <Server className="w-4 h-4 mr-2" />
                    {t('infraScan.scan.statistics')}
                  </CardTitle>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">{t('infraScan.scan.targets')}</span>
                      <span className="font-medium">{step.infraScanResult.total} {t('infraScan.target.count')}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">{t('infraScan.scan.vulnerabilities')}</span>
                      <span className={`font-medium ${step.infraScanResult.total === 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {step.infraScanResult.total} {t('infraScan.target.count')}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Scan target list */}
              {step.infraScanResult.results && step.infraScanResult.results.length > 0 && (
                <div>
                  <div className="flex items-center space-x-2 mb-4">
                    <Globe className="w-5 h-5 text-blue-500" />
                    <span className="font-medium text-gray-900">{t('infraScan.scan.details')}</span>
                  </div>
                  {step.infraScanResult.results.map((target, index) => 
                    renderTarget(target, index)
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Progress info */}
        {/*step.status === 'doing' && (
          <div className="p-4 border-b border-gray-200 flex-shrink-0">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">Execution progress</CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="flex justify-between text-sm text-gray-600 mb-2">
                  <span>Current progress</span>
                  <span className="font-medium">{Math.round(step.progress)}%</span>
                </div>
                <Progress value={step.progress} className="h-3" />
              </CardContent>
            </Card>
          </div>
        )*/}

        {/* Execution details */}
        {step.details && (
          <div className="p-4 border-b border-gray-200 flex-shrink-0">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center">
                  <Info className="w-4 h-4 mr-2" />
                  {t('infraScan.executionDetails')}
                </CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {step.details}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Timing info */}
        {/*<div className="p-4 flex-shrink-0">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center">
                <Calendar className="w-4 h-4 mr-2" />
                Timing info
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-0 space-y-3">
              {step.startTime && (
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Start time</span>
                  <span className="font-mono text-gray-900">
                    {formatTime(step.startTime)}
                  </span>
                </div>
              )}
              
              {step.endTime && (
                <>
                  <Separator />
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">End time</span>
                    <span className="font-mono text-gray-900">
                      {formatTime(step.endTime)}
                    </span>
                  </div>
                </>
              )}
              
              {step.startTime && (
                <>
                  <Separator />
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600 flex items-center">
                      <Timer className="w-3 h-3 mr-1" />
                      Elapsed time
                    </span>
                    <span className="font-medium text-gray-900">
                      {formatDuration(step.startTime, step.endTime)}
                    </span>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>*/}
      </div>
      <Dialog open={!!previewImage} onOpenChange={(open) => !open && setPreviewImage(null)}>
        <DialogContent className="max-w-[90vw] max-h-[90vh] p-0 flex flex-col">
          {previewImage && (
            <>
              <img
                src={previewImage.image}
                alt={t('infraScan.target.screenshot')}
                className="w-full h-auto max-h-[calc(90vh-120px)] object-contain"
              />
              {previewImage.reason && (
                <div className="p-4 border-t border-gray-200 bg-gray-50">
                  <div className="text-sm font-medium text-gray-700 mb-2 flex items-center">
                    <SearchCode className="w-4 h-4 mr-1 text-gray-500" />
                    {t('infraScan.target.pageAnalysis')}
                  </div>
                  <div className="text-sm text-gray-600">
                    {previewImage.reason}
                  </div>
                </div>
              )}
            </>
          )}
        </DialogContent>
      </Dialog>
    </TooltipProvider>
  );
};

export default InfraScanDetailPanel; 