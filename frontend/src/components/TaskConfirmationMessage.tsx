import React from 'react';
import { useTranslation } from 'react-i18next';
import { ExecutionStep, TaskType } from '../types';
import { useMcpServices } from '../config/mcpServices';
import { CheckCircle, Clock, Shield, AlertTriangle, Key, Bug, ShieldCheck, Bot } from 'lucide-react';
import { Card, CardContent } from './ui/card';

interface TaskConfirmationMessageProps {
  taskType: TaskType;
  executionPlan: ExecutionStep[];
  confirmationText: string;
}

const TaskConfirmationMessage: React.FC<TaskConfirmationMessageProps> = ({ 
  taskType, 
  executionPlan, 
  confirmationText 
}) => {
  const { t } = useTranslation();
  const mcpServices = useMcpServices();
  
  const getTaskIcon = (type: TaskType) => {
    const service = mcpServices.find(service => service.id === type);
    if (!service) {
      return <Shield className="w-5 h-5 text-blue-600" />;
    }
    
    switch (service.icon) {
      case 'Bug':
        return <Bug className="w-5 h-5 text-blue-600" />;
      case 'ShieldCheck':
        return <ShieldCheck className="w-5 h-5 text-blue-600" />;
      case 'AlertTriangle':
        return <AlertTriangle className="w-5 h-5 text-orange-600" />;
      case 'Key':
        return <Key className="w-5 h-5 text-red-600" />;
      case 'Bot':
        return <Bot className="w-5 h-5 text-blue-600" />;

      default:
        return <Shield className="w-5 h-5 text-blue-600" />;
    }
  };

  const getTaskTitle = (type: TaskType) => {
    const service = mcpServices.find(service => service.id === type);
    return service ? service.name : t('taskConfirmation.aiSecurityDetection');
  };

  return (
    <Card className="border-none bg-transparent shadow-none">
      <CardContent className="py-2">
        {/* Task confirmation */}
        <div className="flex items-center space-x-3 mb-3">
          <div>
            <div className="text-gray-900 flex items-center">
              {t('taskConfirmation.taskReceived', { taskTitle: getTaskTitle(taskType) })}
            </div>
            <p className="text-gray-700 leading-relaxed">
              {confirmationText}
            </p>
          </div>
        </div>

        {/* Execution plan list - only shown when a plan exists */}
        {executionPlan.length > 0 && (
          <ol className="space-y-2">
            {executionPlan.map((step, index) => (
              <li key={step.id} className="flex items-center space-x-3">
                <span className="flex items-center justify-center w-5 h-5 bg-blue-100 text-blue-700 text-sm font-medium rounded-full flex-shrink-0 mt-0.5">
                  {index + 1}
                </span>
                <span className="text-gray-700">{step.title}</span>
              </li>
            ))}
          </ol>
        )}
        
        {/* <div className="mt-4 text-sm text-blue-800 flex items-center">
          {t('taskConfirmation.workProcessNotice')}
        </div> */}
      </CardContent>
    </Card>
  );
};

export default TaskConfirmationMessage;
