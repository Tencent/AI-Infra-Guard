import React from 'react';
import { ExecutionStep } from '../types';
import TimelineStep from './TimelineStep';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Clock, ListChecks } from 'lucide-react';

interface TaskExecutionTimelineProps {
  steps: ExecutionStep[];
  taskTitle: string;
  messages: any[];
  onStepSelect?: (step: ExecutionStep) => void;
  onToolSelect?: (step: ExecutionStep, subStepIndex: number, toolIndex: number) => void;
}

const TaskExecutionTimeline: React.FC<TaskExecutionTimelineProps> = ({ 
  steps, 
  taskTitle,
  onStepSelect,
  onToolSelect
}) => {
  const completedSteps = steps.filter(step => step.status === 'done').length;
  const runningStep = steps.find(step => step.status === 'doing');
  

  
  return (
    <div>
      <Card className="w-full border-none shadow-none bg-transparent">
        <CardContent className="pt-0">
          {steps.length > 0 && (
            <div className="space-y-0">
              {steps
                .filter(step => step.subSteps && step.subSteps.length > 0)
                .map((step, index) => (
                <TimelineStep
                  key={step.id}
                  step={step}
                  index={index}
                  isLast={index === steps.filter(s => s.subSteps && s.subSteps.length > 0).length - 1}
                  onSelect={onStepSelect}
                  onToolSelect={onToolSelect}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default TaskExecutionTimeline;
