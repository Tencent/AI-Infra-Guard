import React, { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { ExecutionStep, RedteamReportResult } from '../../types';
import { 
  AlertTriangle,
  Maximize,
  Minimize,
  Info,
  Share2,
  Download,
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '../ui/tooltip';
import { useApp } from '../../context/AppContext';
import BaseDetailPanel from './BaseDetailPanel';
import ResultDisplay from './PromptResultDisplay';
import { useReportPrint } from './useReportPrint';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';

interface RedteamReportDetailPanelProps {
  step: ExecutionStep | null;
  stepIndex?: number;
  redteamReportResult?: RedteamReportResult;
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

const RedteamReportDetailPanel: React.FC<RedteamReportDetailPanelProps> = ({ 
  step, 
  stepIndex, 
  redteamReportResult, 
  selectedTool,
  isFullscreen = false, 
  onToggleFullscreen,
  hideFullscreenButton = false,
  sessionId
}) => {
  const { t } = useTranslation();
  const { state } = useApp();
  const reportRef = useRef<HTMLDivElement>(null);
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

  const getAttachmentUrl = (): string | null => {
    const content: any = redteamReportResult?.content;
    if (!content) {
      return null;
    }
    const contentArray = Array.isArray(content) ? content : [content];
    const found = contentArray.find(item => item && item.attachment);
    return found?.attachment || null;
  };

  const downloadViaTaskApi = async (
    fileUrl: string,
  ): Promise<{ blob: Blob; filename: string }> => {
    const endpoint = currentSessionId
      ? `/api/v1/app/tasks/${currentSessionId}/downloadFile`
      : '/api/v1/app/tasks/downloadFile';
    const response = await fetch(
      endpoint,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fileUrl,
        }),
      },
    );
    const disposition = response.headers.get('Content-Disposition');
    let filename = `${t('redteam.evaluationResult')}`;
    if (disposition) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) {
        filename = decodeURIComponent(match[1]);
      }
    }
    const blob = await response.blob();
    return { blob, filename };
  };

  const handleDownloadCsv = async () => {
    const url = getAttachmentUrl();
    if (!url) {
      return;
    }
    try {
      const { blob, filename } = await downloadViaTaskApi(url);
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = filename.endsWith('.csv') ? filename : `${filename}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(objectUrl);
    } catch {}
  };

  const parseCsvToObjects = (text: string): Record<string, string>[] => {
    const lines = text.split(/\r?\n/).filter(line => line.trim().length > 0);
    if (lines.length === 0) {
      return [];
    }
    const parseLine = (line: string): string[] => {
      const result: string[] = [];
      let current = '';
      let inQuotes = false;
      for (let i = 0; i < line.length; i += 1) {
        const char = line[i];
        if (char === '"') {
          if (inQuotes && i + 1 < line.length && line[i + 1] === '"') {
            current += '"';
            i += 1;
          } else {
            inQuotes = !inQuotes;
          }
        } else if (char === ',' && !inQuotes) {
          result.push(current);
          current = '';
        } else {
          current += char;
        }
      }
      result.push(current);
      return result.map(cell => cell.replace(/^\s+|\s+$/g, ''));
    };
    const headers = parseLine(lines[0]);
    const rows: Record<string, string>[] = [];
    for (let idx = 1; idx < lines.length; idx += 1) {
      const cols = parseLine(lines[idx]);
      if (cols.length === 1 && cols[0] === '') {
        continue;
      }
      const row: Record<string, string> = {};
      for (let c = 0; c < headers.length; c += 1) {
        row[headers[c] || `col_${c + 1}`] = cols[c] !== undefined ? cols[c] : '';
      }
      rows.push(row);
    }
    return rows;
  };

  const handleDownloadJsonl = async () => {
    const url = getAttachmentUrl();
    if (!url) {
      return;
    }
    try {
      const { blob } = await downloadViaTaskApi(url);
      const csvText = await blob.text();
      const objects = parseCsvToObjects(csvText);
      const jsonl = objects.map(obj => JSON.stringify(obj)).join('\n');
      const outBlob = new Blob([jsonl], { type: 'application/jsonl' });
      const objectUrl = URL.createObjectURL(outBlob);
      const a = document.createElement('a');
      a.href = objectUrl;
      a.download = `${t('redteam.evaluationResult')}.jsonl`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(objectUrl);
    } catch {}
  };

  const handleDownloadPdf = useReportPrint(
    reportRef,
    `A.I.G ${t('task.taskType.modelRedteamReport')}`
  );

  // If only redteamReportResult is present, show the evaluation results
  if (redteamReportResult && !step) {
    return (
      <TooltipProvider>
        <div className="bg-white border-l border-gray-200 flex flex-col w-full h-full transition-all duration-300 ease-in-out">
          {/* Header */}
          <div className="p-4 border-b border-gray-200 flex-shrink-0">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-5 h-5 text-orange-500" />
                <span className="text-sm font-medium text-gray-500">{t('redteam.aigReportTitle')}</span>
              </div>
              <div className="flex items-center space-x-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button
                            className="p-1.5 rounded-md hover:bg-gray-100 transition-colors cursor-pointer"
                            type="button"
                            aria-label={t('redteam.downloadDetailedReport')}
                          >
                            <Download className="w-4 h-4 text-gray-500" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={handleDownloadPdf}>
                            {t('redteam.downloadReport')}
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={handleDownloadCsv}>
                            {t('redteam.downloadDataCsv')}
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={handleDownloadJsonl}>
                            {t('redteam.downloadDataJsonl')}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
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
                      <p>{t('common.share')}</p>
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
                      <p>{isFullscreen ? t('common.exitFullscreen') : t('common.fullscreen')}</p>
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>
            </div>
          </div>

          {/* Evaluation result */}
          <div ref={reportRef} className={`flex-1 overflow-y-auto min-h-0 transition-all duration-300 ease-in-out scrollbar-hover print-content-wrapper ${
            isFullscreen
              ? 'max-w-[1200px] w-full mx-auto'
              : 'w-full'
          }`}>
            <ResultDisplay
              title={t('redteam.evaluationResult')}
              titleIcon={<AlertTriangle className="w-4 h-4" />}
              content={redteamReportResult.content}
              msgType={redteamReportResult.msgType}
              sessionId={currentSessionId}
              isFullscreen={isFullscreen}
            />
          </div>
        </div>
      </TooltipProvider>
    );
  }

  return (
    <BaseDetailPanel
      step={step}
      stepIndex={stepIndex}
      selectedTool={selectedTool}
      isFullscreen={isFullscreen}
      onToggleFullscreen={onToggleFullscreen}
      emptyMessage={t('redteam.selectExecutionStep')}
    >
      {/* Model red-team evaluation result */}
      {step?.redteamReportResult && (
        <div className="p-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center">
                <AlertTriangle className="w-4 h-4 mr-2 text-blue-500" />
                {t('redteam.evaluationReport')}
              </CardTitle>
              <div className="flex items-center space-x-2">
                <Badge variant="outline" className="text-xs">
                  {step.redteamReportResult.msgType}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="pt-0">
              <ResultDisplay
                title={t('redteam.evaluationReport')}
                titleIcon={<AlertTriangle className="w-4 h-4" />}
                content={step.redteamReportResult.content}
                msgType={step.redteamReportResult.msgType}
                sessionId={currentSessionId}
                isFullscreen={isFullscreen}
              />
            </CardContent>
          </Card>
        </div>
      )}

    </BaseDetailPanel>
  );
};

export default RedteamReportDetailPanel;