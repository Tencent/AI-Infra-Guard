import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ExecutionStep } from '../../types';
import { toast } from 'sonner';
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
  Shield,
  ShieldCheck,
  Maximize,
  Minimize,
  Copy,
  MessageSquare,
  Share2
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Separator } from '../ui/separator';
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '../ui/tooltip';
import { useApp } from '../../context/AppContext';
import CodeHighlight from './CodeHighlight';

interface BaseDetailPanelProps {
  step: ExecutionStep | null;
  stepIndex?: number;
  selectedTool?: {
    step: ExecutionStep;
    subStepIndex: number;
    toolIndex: number;
  } | null;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
  title?: string;
  titleIcon?: React.ReactNode;
  children?: React.ReactNode;
  emptyMessage?: string;
  hideFullscreenButton?: boolean;
}

const BaseDetailPanel: React.FC<BaseDetailPanelProps> = ({ 
  step, 
  stepIndex, 
  selectedTool,
  isFullscreen = false, 
  onToggleFullscreen,
  title,
  titleIcon,
  children,
  emptyMessage = '选择执行步骤',
  hideFullscreenButton = false
}) => {
  const { t } = useTranslation();
  const { state } = useApp();
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const currentTask = state.tasks.find(
    task => task.id === state.currentTaskId,
  );
  const sessionId = currentTask?.id;

  const handleShare = () => {
    if (sessionId) {
      const shareUrl = `${window.location.origin}/report/${sessionId}`;
      window.open(shareUrl, '_blank');
    }
  };

  // Copy-feature related state
  const [copied, setCopied] = useState<string>('');
  
  const handleCopy = async (text: string, key: string) => {
    if (!text) {
      toast.error(t('detailPanel.ui.contentEmpty'));
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(''), 1200);
    } catch (e) {
      try {
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        setCopied(key);
        setTimeout(() => setCopied(''), 1200);
      } catch (err) {
        toast.error(t('detailPanel.ui.copyFailed'));
      }
    }
  };

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
      todo: t('detailPanel.status.todo'),
      doing: t('detailPanel.status.doing'),
      done: t('detailPanel.status.done'),
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
    const locale = t('language.locale', { defaultValue: 'zh-CN' });
    return new Intl.DateTimeFormat(locale, {
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
    
    if (duration < 60) return `${duration}${t('detailPanel.timeUnits.seconds')}`;
    if (duration < 3600) return `${Math.round(duration / 60)}${t('detailPanel.timeUnits.minutes')}`;
    return `${Math.round(duration / 3600)}${t('detailPanel.timeUnits.hours')}`;
  };

  if (!step) {
    return (
      <TooltipProvider>
        <div className="w-full min-w-[320px] bg-white border-l border-gray-200 flex items-center justify-center h-full">
          <div className="text-center text-gray-500 p-6">
            <Info className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <h3 className="font-medium mb-2">{emptyMessage}</h3>
            <p className="text-sm">{t('detailPanel.clickStepCard')}</p>
          </div>
        </div>
      </TooltipProvider>
    );
  }

  return (
    <TooltipProvider>
      <div className="bg-white border-l border-gray-200 flex flex-col w-full h-full transition-all duration-300 ease-in-out">
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
              {sessionId && !hideFullscreenButton && (
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
                    <p>{t('detailPanel.ui.shareReport')}</p>
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
                    <p>{isFullscreen ? t('detailPanel.ui.exitFullscreen') : t('detailPanel.ui.fullscreen')}</p>
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
            className="p-4 border-b border-gray-200 flex-1 overflow-y-auto min-h-0 scrollbar-hover"
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
                      <div className="flex items-center space-x-2 min-w-0">
                        <span className="text-sm font-medium text-gray-900 truncate" title={subStep.brief}>{subStep.brief}</span>
                        <Badge variant={subStep.status === 'done' ? 'default' : 'secondary'} className="text-xs flex-shrink-0">
                          {subStep.status === 'done' ? t('detailPanel.status.done') : subStep.status === 'doing' ? t('detailPanel.status.doing') : t('detailPanel.status.todo')}
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

                            // Check whether the current task type is Agent-Scan
                            const isAgentScan = currentTask?.type === 'Agent-Scan';
                            
                            return (
                              <div key={toolIndex} className="border rounded-lg p-5 bg-white">
                                <div className="flex items-center justify-between mb-2">
                                  <div className="flex items-center space-x-2 min-w-0">
                                    {!isAgentScan && (
                                      <div className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-medium truncate">
                                        {tool.tool || tool.brief}
                                      </div>
                                    )}
                                    <span className={`text-sm text-gray-600 truncate ${isAgentScan ? 'max-w-xs' : ''}`} title={`${tool.message.action} ${tool.message.param}`}>
                                      {tool.message.action} {tool.message.param}
                                    </span>
                                    {tool.result && (
                                      <div className="text-sm text-green-600 truncate max-w-xs" title={tool.result}>
                                        {tool.result}
                                      </div>
                                    )}
                                  </div>
                                  <Badge 
                                    variant={tool.status === 'done' ? 'default' : 'secondary'} 
                                    className={`text-xs ml-2 flex-shrink-0 ${
                                      tool.status === 'done' 
                                        ? 'bg-green-100 text-green-800 border-green-200' 
                                        : tool.status === 'doing' 
                                        ? 'bg-blue-100 text-blue-800 border-blue-200' 
                                        : 'bg-gray-100 text-gray-800 border-gray-200'
                                    }`}
                                  >
                                    {tool.status === 'done' ? t('detailPanel.status.success') : tool.status === 'doing' ? t('detailPanel.status.doing') : t('detailPanel.status.todo')}
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

        {/* Custom content area */}
        {children && (
          <div className={`flex-1 overflow-y-auto min-h-0 transition-all duration-300 ease-in-out scrollbar-hover ${
            isFullscreen
              ? 'max-w-[1200px] w-full mx-auto'
              : 'w-full'
          }`}>
            {children}
          </div>
        )}

        {/* Execution details */}
        {step.details && (
          <div className="p-4 border-b border-gray-200 flex-shrink-0">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center">
                  <Info className="w-4 h-4 mr-2" />
                  {t('detailPanel.ui.executionDetails')}
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
      </div>
    </TooltipProvider>
  );
};

export default BaseDetailPanel; 