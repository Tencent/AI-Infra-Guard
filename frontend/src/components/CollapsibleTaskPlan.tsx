import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, CheckCircle, Loader, Clock, ChevronDown, ChevronUp } from 'lucide-react';
import { ExecutionStep } from '../types';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';

interface CollapsibleTaskPlanProps {
  steps: ExecutionStep[];
  taskTitle: string;
  onExpandedChange?: (expanded: boolean) => void;
}

const CollapsibleTaskPlan: React.FC<CollapsibleTaskPlanProps> = ({
  steps,
  taskTitle,
  onExpandedChange,
}) => {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(() => {
    // Collapse by default when the task is completed; otherwise expand by default
    const isFinished = steps.every(step => step.status === 'done');
    return !isFinished;
  });
  const isFinished = steps.every(step => step.status === 'done');
  const lastStep = steps[steps.length - 1];
  const doingStep = steps.find(step => step.status === 'doing');
  let displayStep: ExecutionStep | undefined;
  let Icon: React.ElementType;
  if (isFinished) {
    displayStep = lastStep;
    Icon = CheckCircle;
  } else if (doingStep) {
    displayStep = doingStep;
    Icon = Loader;
  } else {
    displayStep = steps[0];
    Icon = Loader;
  }
  const completedCount = steps.filter(step => step.status === 'done').length;
  const totalCount = steps.length;
  
  // Notify the parent component about the expanded-state change
  useEffect(() => {
    if (onExpandedChange) {
      onExpandedChange(expanded);
    }
  }, [expanded, onExpandedChange]);
  return (
    <div>
      {expanded && <div className='flex items-center justify-between mb-4 mt-2'>
        <span className='font-bold'>{taskTitle}</span>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                className='text-blue-600 text-sm hover:text-blue-800 transition-colors'
                onClick={() => setExpanded(!expanded)}
              >
                {!expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{expanded ? t('task.collapse') : t('task.expand')}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>}
      {expanded ? (
        <div className='border rounded bg-gray-50 my-2 p-2'>
          <div className='flex items-center justify-between space-x-2 p-2'>
            <span className='font-bold'>{t('task.taskProgress')}</span>
            <span className='text-gray-500 text-sm'>{completedCount}/{totalCount}</span>
          </div>
          {steps.map(
            (step, idx) => {
              let StepIcon;
              if (step.status === 'done') {
                StepIcon = Check;
              } else if (step.status === 'todo') {
                StepIcon = Clock;
              } else {
                StepIcon = Loader;
              }
              return (
                <div
                  key={step.title}
                  className='flex items-center space-x-2 p-2'
                >
                  <StepIcon 
                    size={14}
                    className={
                      step.status === 'done' 
                        ? 'text-green-500' 
                        : step.status === 'todo'
                          ? 'text-gray-500'
                          : 'animate-spin text-blue-500'
                    } 
                  />
                  <span>{step.title}</span>
                </div>
              );
            },
          )}
        </div>
      ) : (
        <div className='flex items-center justify-between p-2'>
          <div className='flex items-center space-x-2'>
            <Icon 
              size={14}
              className={isFinished ? 'text-green-500' : 'animate-spin text-blue-500'} 
            />
            <span>{displayStep?.title}</span>
          </div>
          <div className='flex items-center space-x-2'>
            <span className='text-gray-500 text-sm'>{completedCount}/{totalCount}</span>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className='text-blue-600 text-sm hover:text-blue-800 transition-colors'
                    onClick={() => setExpanded(!expanded)}
                  >
                    {!expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{expanded ? t('task.collapse') : t('task.expand')}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      )}
    </div>
  );
};

export default CollapsibleTaskPlan; 