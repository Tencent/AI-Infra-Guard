import React from 'react';
import { ExecutionStep } from '../types';
import { 
  Clock, 
  CheckCircle, 
  XCircle, 
  Play,
  ChevronRight
} from 'lucide-react';
import { Badge } from './ui/badge';
import { Progress } from './ui/progress';
import { Card, CardContent, CardHeader } from './ui/card';

interface StepCardProps {
  step: ExecutionStep;
  index: number;
  isSelected: boolean;
  onClick: () => void;
}

const StepCard: React.FC<StepCardProps> = ({ step, index, isSelected, onClick }) => {
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
      pending: 'secondary',
      running: 'default',
      completed: 'default',
      failed: 'destructive',
    } as const;

    const labels = {
      pending: '待执行',
      running: '执行中',
      completed: '已完成',
      failed: '失败',
    };

    return (
      <Badge variant={variants[status]} className="text-xs">
        {labels[status]}
      </Badge>
    );
  };

  const getStatusColor = (status: ExecutionStep['status']) => {
    switch (status) {
      case 'todo':
        return 'border-amber-200 bg-amber-50';
      case 'doing':
        return 'border-blue-200 bg-blue-50';
      case 'done':
        return 'border-green-200 bg-green-50';
      default:
        return 'border-gray-200 bg-gray-50';
    }
  };

  return (
    <Card 
      className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
        isSelected 
          ? 'ring-2 ring-blue-500 shadow-lg' 
          : 'hover:shadow-sm'
      } ${getStatusColor(step.status)}`}
      onClick={onClick}
    >
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-mono text-gray-500 bg-white px-2 py-1 rounded">
                {(index + 1).toString().padStart(2, '0')}
              </span>
              {getStatusIcon(step.status)}
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {getStatusBadge(step.status)}
            <ChevronRight className="w-4 h-4 text-gray-400" />
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <h3 className="font-medium text-gray-900 mb-2">
          {step.title}
        </h3>
        
        {step.status === 'doing' && (
          <div className="mb-2">
            <div className="flex justify-between text-xs text-gray-600 mb-1">
              <span>进度</span>
              <span>{Math.round(step.progress)}%</span>
            </div>
            <Progress value={step.progress} className="h-2" />
          </div>
        )}
        
        {step.details && (
          <p className="text-sm text-gray-600 line-clamp-2">
            {step.details}
          </p>
        )}
      </CardContent>
    </Card>
  );
};

export default StepCard;
