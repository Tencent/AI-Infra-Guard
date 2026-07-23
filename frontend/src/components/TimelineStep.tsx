import React, { useState } from 'react';
import { ExecutionStep } from '../types';
import { 
  Clock, 
  CircleCheck, 
  XCircle, 
  Play,
  ChevronDown,
  ChevronRight,
  Link,
  Loader2
} from 'lucide-react';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from './ui/collapsible';

interface TimelineStepProps {
  step: ExecutionStep;
  index: number;
  isLast: boolean;
  onSelect?: (step: ExecutionStep) => void;
  onToolSelect?: (step: ExecutionStep, subStepIndex: number, toolIndex: number) => void;
}

const TimelineStep: React.FC<TimelineStepProps> = ({ step, index, isLast, onSelect, onToolSelect }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  const getStatusIcon = (status: ExecutionStep['status']) => {
    switch (status) {
      case 'todo':
        return <Clock className="w-4 h-4 text-gray-400" />;
      case 'doing':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'done':
        return <CircleCheck className="w-4 h-4 text-green-500" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status: ExecutionStep['status']) => {
    switch (status) {
      case 'todo':
        return 'border-gray-300';
      case 'doing':
        return 'border-blue-300';
      case 'done':
        return 'border-green-300';
      default:
        return 'border-gray-300';
    }
  };

  const formatTime = (date?: Date) => {
    if (!date) return '';
    return new Intl.DateTimeFormat('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(date);
  };

  const handleStepClick = () => {
    if (onSelect) {
      onSelect(step);
    }
  };

  const handleToolClick = (subStepIndex: number, toolIndex: number) => {
    if (onToolSelect) {
      onToolSelect(step, subStepIndex, toolIndex);
    }
  };

  return (
    <div className="relative flex">
      {/* Timeline line */}
      <div className="flex flex-col items-center mr-4">
        {/* Status node */}
        <div 
          className={`
            flex items-center justify-center w-8 h-8
            ${getStatusColor(step.status)}
            ${onSelect ? 'cursor-pointer hover:scale-110 transition-transform' : ''}
          `}
          onClick={handleStepClick}
        >
          {getStatusIcon(step.status)}
        </div>
        
        {/* Connector line */}
        {!isLast && (
          <div className="w-0.5 bg-gray-200 flex-1 mt-2 min-h-[40px]"></div>
        )}
      </div>

      {/* Step content */}
      <div className="flex-1 pb-3">
        <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
          <CollapsibleTrigger asChild>
            <div 
              className="flex items-center cursor-pointer hover:bg-gray-50 pt-1 rounded-lg -ml-2 gap-2"
              onClick={handleStepClick}
            >
              <div className="flex items-center space-x-3">
                <span className="font-medium text-gray-900">
                  {step.title}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                {isExpanded ? (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                )}
              </div>
            </div>
          </CollapsibleTrigger>

          <CollapsibleContent>
            <div className="mt-2 ml-2">
              {/* Main status description */}
              {step.details && (
                <div className="mb-3">
                  <p className="text-sm text-gray-700">{step.details}</p>
                </div>
              )}

              {/* Sub-step display */}
              {step.subSteps && step.subSteps.length > 0 && (
                <div className='space-y-2'>
                  {step.subSteps.map((subStep, subIndex) => (
                    <div key={subStep.id || subIndex} className='flex items-start space-x-3'>
                      <div className='flex items-center space-x-2 mt-2'>
                        {subStep.status === 'doing' && (
                          <Loader2 className='w-3 h-3 text-blue-500 animate-spin' />
                        )}
                        {subStep.status === 'done' && (
                          <CircleCheck className='w-3 h-3 text-green-500' />
                        )}
                        {subStep.status === 'todo' && (
                          <Clock className='w-3 h-3 text-gray-400' />
                        )}
                      </div>
                      <div className='flex-1'>
                        {/* Display of brief + action + param */}
                        <span className='text-sm text-gray-700 font-medium'>{subStep.brief}{subStep.description ? ` - ${subStep.description}` : ''}</span>
                        {(subStep.toolUsed && subStep.toolUsed.length > 0) && (
                          <div className='text-sm text-gray-500 mt-1'>
                            {subStep.toolUsed.map((tool, toolIndex) => (
                              <div key={`${subStep.id || subIndex}-${tool.toolId || toolIndex}`} className='flex items-center gap-1'>
                                <div 
                                  className={`bg-gray-100 rounded-lg my-1 w-fit p-2 transition-colors ${
                                    tool.actionLog 
                                      ? 'border-l-4 border-blue-500 cursor-pointer hover:bg-gray-200' 
                                      : 'cursor-default'
                                  }`}
                                  title={tool.actionLog ? '点击查看操作日志' : ''}
                                  onClick={tool.actionLog ? () => handleToolClick(subIndex, toolIndex) : undefined}
                                >
                                  {tool.message.action} {tool.message.param}
                                </div>
                                <div className='text-gray-600 ml-2'>{tool.result}</div>
                              </div>  
                            ))}
                          </div>
                        )}
                        {/* Result display */}
                        {subStep.result && (
                          <div className='text-xs text-green-600 mt-1'>
                            {subStep.result}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Progress bar */}
              {step.status === 'doing' && step.progress > 0 && (
                <div className="mt-3">
                  <div className="flex justify-between text-xs text-gray-600 mb-1">
                    <span>执行进度</span>
                    <span>{Math.round(step.progress)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${step.progress}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          </CollapsibleContent>
        </Collapsible>
      </div>
    </div>
  );
};

export default TimelineStep;
