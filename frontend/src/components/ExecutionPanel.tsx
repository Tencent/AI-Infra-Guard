import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { ExecutionStep, TaskStatus } from '../types';
import { 
  Clock, 
  CheckCircle, 
  XCircle, 
  Play, 
  Pause,
  Download,
  FileText,
  ChevronRight,
  ChevronDown
} from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { ScrollArea } from './ui/scroll-area';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';

// Status mapping function
const mapTaskStatusToStepStatus = (status: TaskStatus): 'todo' | 'doing' | 'done' => {
  if (status === 'pending') return 'todo';
  if (status === 'running') return 'doing';
  if (status === 'completed' || status === 'error' || status === 'done') return 'done';
  return 'todo';
};

const ExecutionPanel: React.FC = () => {
  const { state } = useApp();
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const currentTask = state.tasks.find(task => task.id === state.currentTaskId);

  if (!currentTask) {
    return (
      <div className="w-80 bg-gray-900 border-l border-gray-700 flex items-center justify-center">
        <div className="text-center text-gray-500">
          <Clock className="w-12 h-12 mx-auto mb-4 opacity-50" />
          <p>无执行计划</p>
        </div>
      </div>
    );
  }

  const getStatusIcon = (status: ExecutionStep['status']) => {
    switch (status) {
      case 'todo':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'doing':
        return <Play className="w-4 h-4 text-blue-500 animate-pulse" />;
      case 'done':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: ExecutionStep['status']) => {
    const variants = {
      todo: 'secondary',
      doing: 'default',
      done: 'default',
    } as const;

    const labels = {
      todo: '待执行',
      doing: '执行中',
      done: '已完成',
    };

    return (
      <Badge variant={variants[status]} className="text-xs">
        {labels[status]}
      </Badge>
    );
  };

  const formatDuration = (start?: Date, end?: Date) => {
    if (!start) return '';
    const startTime = start;
    const endTime = end || new Date();
    const duration = Math.round((endTime.getTime() - startTime.getTime()) / 1000);
    
    if (duration < 60) return `${duration}秒`;
    if (duration < 3600) return `${Math.round(duration / 60)}分钟`;
    return `${Math.round(duration / 3600)}小时`;
  };

  const toggleStepExpansion = (stepId: string) => {
    setExpandedSteps(prev => {
      const newSet = new Set(prev);
      if (newSet.has(stepId)) {
        newSet.delete(stepId);
      } else {
        newSet.add(stepId);
      }
      return newSet;
    });
  };

  const downloadReport = () => {
    if (currentTask.result) {
      window.open(currentTask.result, '_blank');
    }
  };

  const completedSteps = currentTask.plan.filter(step => step.status === 'done').length;
  const totalSteps = currentTask.plan.length;
  const overallProgress = totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0;

  return (
    <div className="w-80 bg-gray-900 border-l border-gray-700 flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold text-white">执行计划</h3>
          {currentTask.result && (
            <Button 
              size="sm" 
              variant="outline"
              onClick={downloadReport}
              className="text-xs"
            >
              <Download className="w-3 h-3 mr-1" />
              报告
            </Button>
          )}
        </div>

        {/* Overall progress */}
        {totalSteps > 0 && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-400">总体进度</span>
              <span className="text-white">{completedSteps} / {totalSteps}</span>
            </div>
            <Progress value={overallProgress} className="h-2" />
          </div>
        )}

        {/* Task status */}
        <div className="flex items-center justify-between mt-3">
          <span className="text-sm text-gray-400">任务状态</span>
          <div className="flex items-center space-x-2">
            {getStatusIcon(mapTaskStatusToStepStatus(currentTask.status))}
            {getStatusBadge(mapTaskStatusToStepStatus(currentTask.status))}
          </div>
        </div>
      </div>

      {/* Execution steps */}
      <ScrollArea className="flex-1">
        <div className="p-4">
          {currentTask.plan.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <Pause className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>暂无执行计划</p>
              <p className="text-sm mt-1">任务开始后将显示执行步骤</p>
            </div>
          ) : (
            <div className="space-y-3">
              {currentTask.plan.map((step, index) => (
                <Collapsible
                  key={step.id}
                  open={expandedSteps.has(step.id)}
                  onOpenChange={() => toggleStepExpansion(step.id)}
                >
                  <div className="bg-gray-800 rounded-lg border border-gray-700">
                    <CollapsibleTrigger className="w-full p-3 text-left hover:bg-gray-750 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs text-gray-400 font-mono">
                              {(index + 1).toString().padStart(2, '0')}
                            </span>
                            {getStatusIcon(step.status)}
                          </div>
                          <span className="text-sm text-white font-medium">
                            {step.title}
                          </span>
                        </div>
                        <div className="flex items-center space-x-2">
                          {getStatusBadge(step.status)}
                          {expandedSteps.has(step.id) ? (
                            <ChevronDown className="w-4 h-4 text-gray-400" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-gray-400" />
                          )}
                        </div>
                      </div>

                      {/* Progress bar */}
                      {step.status === 'doing' && (
                        <div className="mt-2">
                          <div className="flex justify-between text-xs text-gray-400 mb-1">
                            <span>进度</span>
                            <span>{Math.round(step.progress)}%</span>
                          </div>
                          <Progress value={step.progress} className="h-1" />
                        </div>
                      )}
                    </CollapsibleTrigger>

                    <CollapsibleContent>
                      <div className="px-3 pb-3 border-t border-gray-700 mt-3 pt-3">
                        {/* Execution details */}
                        {step.details && (
                          <div className="mb-3">
                            <div className="text-xs text-gray-400 mb-1">执行详情</div>
                            <div className="text-sm text-gray-300 bg-gray-900 rounded p-2">
                              {step.details}
                            </div>
                          </div>
                        )}

                        {/* Timing info */}
                        <div className="space-y-2 text-xs">
                          {step.startTime && (
                            <div className="flex justify-between">
                              <span className="text-gray-400">开始时间</span>
                              <span className="text-gray-300">
                                {new Intl.DateTimeFormat('zh-CN', {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                  second: '2-digit',
                                }).format(new Date(step.startTime))}
                              </span>
                            </div>
                          )}
                          
                          {step.endTime && (
                            <div className="flex justify-between">
                              <span className="text-gray-400">结束时间</span>
                              <span className="text-gray-300">
                                {new Intl.DateTimeFormat('zh-CN', {
                                  hour: '2-digit',
                                  minute: '2-digit',
                                  second: '2-digit',
                                }).format(new Date(step.endTime))}
                              </span>
                            </div>
                          )}
                          
                          {step.startTime && (
                            <div className="flex justify-between">
                              <span className="text-gray-400">执行时长</span>
                              <span className="text-gray-300">
                                {formatDuration(step.startTime, step.endTime)}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </CollapsibleContent>
                  </div>
                </Collapsible>
              ))}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Footer info */}
      {currentTask.result && (
        <div className="p-4 border-t border-gray-700">
          <Button 
            className="w-full bg-green-600 hover:bg-green-700" 
            onClick={downloadReport}
          >
            <FileText className="w-4 h-4 mr-2" />
            查看完整报告
          </Button>
        </div>
      )}
    </div>
  );
};

export default ExecutionPanel;
