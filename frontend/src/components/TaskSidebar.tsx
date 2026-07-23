import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useApp } from '../context/AppContext';
import { Task, TaskType, getAvailableTaskTypes } from '../types';
import { 
  Shield,
  ShieldQuestion, 
  AlertTriangle, 
  Key, 
  Plus,
  Bug,
  ShieldCheck,
  LoaderCircle,
  Settings,
  Database,
  Blocks,
  X,
  Search,
  Filter,
  Bot,
  Pause,
  Trash2,
  Sparkles,
} from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import SettingsDialog from './SettingsDialog';
import DeleteConfirmDialog from './DeleteConfirmDialog';
import { useMcpServices } from '../config/mcpServices';
import { toast } from 'sonner';

type TaskListProps = {
  tasks: Task[],
  currentTaskId?: string,
  onTaskClick: (id: string) => void,
  onTaskContextMenu: (event: React.MouseEvent<HTMLDivElement>, task: Task) => void,
  getTaskIcon: (type: TaskType, status?: string) => React.ReactNode,
  formatDate: (date: Date) => string,
};

const TaskList = ({
  tasks,
  currentTaskId,
  onTaskClick,
  onTaskContextMenu,
  getTaskIcon,
  formatDate
}: TaskListProps) => {
  const { t } = useTranslation();
  
  return (
  <div className='p-2'>
    {tasks.length === 0 ? (
      <div className='text-center text-gray-500 py-8'>
        <ShieldCheck className='w-12 h-12 mx-auto mb-4 opacity-50' />
        <p>{t('task.noTasks')}</p>
        <p className='text-sm mt-1'>{t('task.clickNewToCreate')}</p>
      </div>
    ) : (
      tasks.map(task => (
        <div
          key={task.id}
          className={`mb-2 py-1 rounded-lg cursor-pointer transition-colors ${
            currentTaskId === task.id
              ? 'bg-white shadow-sm'
              : 'hover:bg-gray-200 border border-transparent'
          }`}
          onClick={() => onTaskClick(task.id)}
          onContextMenu={(event) => onTaskContextMenu(event, task)}
        >
          <div className='flex items-center'>
            <div className='flex items-center space-x-2 mr-1'>
              <div className='relative flex items-center justify-center w-8 h-8'>
                {task.status === 'running' && (
                  <LoaderCircle className='w-8 h-8 absolute inset-0 m-auto animate-spin text-blue-600' />
                )}
                <span className='relative z-10'>
                  {getTaskIcon(task.type, task.status)}
                </span>
              </div>
            </div>
            <h3 className={`flex-1 min-w-0 font-medium text-sm line-clamp-1 truncate ${
              task.status === 'error'
                ? 'text-red-600'
                : task.status === 'terminated'
                  ? 'text-gray-400'
                  : 'text-gray-900'
            }`}>
              {task.title}
            </h3>
            <span className={`flex-shrink-0 text-xs mx-2 ${
              task.status === 'error'
                ? 'text-red-400'
                : task.status === 'terminated'
                  ? 'text-gray-300'
                  : 'text-gray-400'
            }`}>
              {formatDate(task.createdAt)}
            </span>
          </div>
        </div>
      ))
    )}
  </div>
  );
};

const TaskSidebar: React.FC = () => {
  const { state, dispatch, actions } = useApp();
  const { t, i18n } = useTranslation();
  const mcpServices = useMcpServices();
  const [showSettingsDialog, setShowSettingsDialog] = useState(false);
  const [showSearchDialog, setShowSearchDialog] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<Task[] | null>(null);
  const [selectedTaskType, setSelectedTaskType] = useState<string>('all');
  const [contextMenu, setContextMenu] = useState<{
    open: boolean;
    x: number;
    y: number;
    taskId: string | null;
  }>({ open: false, x: 0, y: 0, taskId: null });
  const [taskToDelete, setTaskToDelete] = useState<Task | null>(null);
  const [taskToTerminate, setTaskToTerminate] = useState<Task | null>(null);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | undefined>(undefined);
  const [terminateLoading, setTerminateLoading] = useState(false);
  const [terminateError, setTerminateError] = useState<string | undefined>(undefined);
  
  // Load the task list on mount and clean up the timer on unmount
  useEffect(() => {
    actions.loadTasks();
    
    // Clean up the timer when the component unmounts
    return () => {
      actions.stopTaskStatusCheck();
    };
  }, []);

  useEffect(() => {
    const handleCloseContextMenu = () => {
      setContextMenu(prev => ({ ...prev, open: false }));
    };

    window.addEventListener('click', handleCloseContextMenu);
    window.addEventListener('scroll', handleCloseContextMenu, true);

    return () => {
      window.removeEventListener('click', handleCloseContextMenu);
      window.removeEventListener('scroll', handleCloseContextMenu, true);
    };
  }, []);





  const getTaskIcon = (type: TaskType, status?: string) => {
    const iconStatusClass = status === 'error'
      ? ' text-red-500'
      : status === 'terminated'
        ? ' text-gray-400'
        : '';
    const service = mcpServices.find(service => service.id === type);
    if (!service) {
      return <Shield className={`w-4 h-4${iconStatusClass}`} />;
    }
    
    switch (service.icon) {
      case 'Bug':
        return <Bug className={`w-4 h-4${iconStatusClass}`} />;
      case 'ShieldCheck':
        return <ShieldCheck className={`w-4 h-4${iconStatusClass}`} />;
      case 'AlertTriangle':
        return <AlertTriangle className={`w-4 h-4${iconStatusClass}`} />;
      case 'Key':
        return <Key className={`w-4 h-4${iconStatusClass}`} />;
      case 'Bot':
        return <Bot className={`w-4 h-4${iconStatusClass}`} />;
      case 'Sparkles':
        return <Sparkles className={`w-4 h-4${iconStatusClass}`} />;

      default:
        return <Shield className={`w-4 h-4${iconStatusClass}`} />;
    }
  };

  const formatDate = (date: Date) => {
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    
    if (isToday) {
      // Uniformly use 24-hour format, with colon-separated hours and minutes
      const hours = date.getHours().toString().padStart(2, '0');
      const minutes = date.getMinutes().toString().padStart(2, '0');
      return `${hours}:${minutes}`;
    } else {
      // Determine the locale based on the current language
      const locale = i18n.language === 'zh' ? 'zh-CN' : 'en-US';
      return new Intl.DateTimeFormat(locale, {
        month: 'numeric',
        day: 'numeric',
      }).format(date);
    }
  };

  const handleClearCurrentTask = () => {
    dispatch({ type: 'SET_CURRENT_TASK', payload: null });
    // Clear the input content
    actions.clearInputContent();
    // Trigger the welcome-text expand animation
    actions.setTriggerWelcomeAnimation(true);
    // Reset the state after the animation completes
    setTimeout(() => {
      actions.setTriggerWelcomeAnimation(false);
    }, 1000);
    // Delay slightly so the textarea can gain focus after the page finishes rendering
    setTimeout(() => {
      const textarea = document.querySelector('textarea');
      if (textarea) {
        textarea.focus();
      }
    }, 100);
  };

  const buildStatusUpdatePayload = (task: Task) => {
    const timestamp = Date.now();
    const now = new Date();
    const formatPart = (value: number, length = 2) => value.toString().padStart(length, '0');
    const eventId = `${now.getFullYear()}${formatPart(now.getMonth() + 1)}${formatPart(now.getDate())}${formatPart(now.getHours())}${formatPart(now.getMinutes())}${formatPart(now.getSeconds())}_${timestamp}`;
    const lastPlanStepId = task.plan?.length ? task.plan[task.plan.length - 1].id : undefined;

    return {
      id: eventId,
      type: 'event',
      sessionId: task.id,
      timestamp,
      event: {
        id: eventId,
        type: 'statusUpdate',
        timestamp,
        agentStatus: 'terminated',
        // Compatible with the current frontend's reading of the agentStaus field
        agentStaus: 'terminated',
        planStepId: lastPlanStepId,
        noRender: false,
      },
    };
  };

  const handleDeleteTask = async () => {
    if (!taskToDelete) return;
    setDeleteLoading(true);
    setDeleteError(undefined);

    try {
      const response = await fetch(`/api/v1/app/tasks/${taskToDelete.id}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const result = await response.json();
      if (result.status === 0) {
        actions.deleteTask(taskToDelete.id);
        setTaskToDelete(null);
        toast.success(t('chatArea.taskDeleteSuccess'));
      } else {
        setDeleteError(result.message || t('chatArea.deleteFailed'));
      }
    } catch (error) {
      setDeleteError(t('chatArea.deleteRequestFailed'));
    } finally {
      setDeleteLoading(false);
    }
  };

  const handleTerminateTask = async () => {
    if (!taskToTerminate) return;
    setTerminateLoading(true);
    setTerminateError(undefined);

    try {
      const response = await fetch(`/api/v1/app/tasks/${taskToTerminate.id}/terminate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const result = await response.json();
      if (result.status === 0) {
        const statusUpdatePayload = buildStatusUpdatePayload(taskToTerminate);
        window.dispatchEvent(new CustomEvent('taskStatusUpdate', { detail: statusUpdatePayload }));

        dispatch({
          type: 'UPDATE_TASK',
          payload: {
            id: taskToTerminate.id,
            updates: {
              status: 'terminated',
              updatedAt: new Date(),
            },
          },
        });

        toast.success(result.message || t('taskTerminate.terminateSuccess'));
        setTaskToTerminate(null);
      } else {
        setTerminateError(result.message || t('taskTerminate.terminateFailed'));
      }
    } catch (error) {
      setTerminateError(t('taskTerminate.terminateRequestFailed'));
    } finally {
      setTerminateLoading(false);
    }
  };

  const handleTaskContextMenu = (event: React.MouseEvent<HTMLDivElement>, task: Task) => {
    event.preventDefault();
    setContextMenu({
      open: true,
      x: event.clientX,
      y: event.clientY,
      taskId: task.id,
    });
  };

  const openDeleteConfirm = () => {
    const selectedTask = state.tasks.find(task => task.id === contextMenu.taskId);
    if (!selectedTask) return;
    setTaskToDelete(selectedTask);
    setContextMenu(prev => ({ ...prev, open: false }));
  };

  const openTerminateConfirm = () => {
    const selectedTask = state.tasks.find(task => task.id === contextMenu.taskId);
    if (!selectedTask || selectedTask.status !== 'running') return;
    setTaskToTerminate(selectedTask);
    setContextMenu(prev => ({ ...prev, open: false }));
  };

  const contextTask = state.tasks.find(task => task.id === contextMenu.taskId);
  const terminateDisabled = !contextTask || contextTask.status !== 'running';

  // Search handler
  async function handleSearch() {
    setSearching(true);
    try {
      const params = new URLSearchParams();
      if (searchValue) {
        params.append('q', searchValue);
      }
      if (selectedTaskType !== 'all') {
        params.append('taskType', selectedTaskType);
      }
      
      const response = await fetch(`/api/v1/app/tasks?${params.toString()}`);
      const responseData = await response.json();
      if (responseData.status !== 0) throw new Error(responseData.message || '搜索失败');
      const tasks: Task[] = responseData.data.tasks.map((task: any) => ({
        id: task.sessionId,
        title: task.title,
        type: task.taskType,
        status: task.status === 'done'
          ? 'completed'
          : task.status === 'terminated'
            ? 'terminated'
            : task.status === 'error'
              ? 'error'
              : 'running',
        createdAt: new Date(task.createdAt),
        updatedAt: new Date(task.updatedAt),
        completedAt: task.completedAt ? new Date(task.completedAt) : undefined,
        files: task.files || [],
        plan: [],
        messages: [],
        isSubmitted: true,
      }));
      setSearchResult(tasks.filter(task => task.isSubmitted));
    } catch (e) {
      setSearchResult([]);
    } finally {
      setSearching(false);
    }
  }

  // Get the filtered task list
  const getFilteredTasks = () => {
    const tasks = searchResult !== null
      ? searchResult
      : state.tasks.filter(task => task.isSubmitted);
    
    if (selectedTaskType === 'all') {
      return tasks;
    }
    
    return tasks.filter(task => task.type === selectedTaskType);
  };

  // Task list component
  return (
    <TooltipProvider>
      <div className="w-80 bg-gray-100 flex flex-col h-full">
      {/* Header */}
      <div className="p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center">
            <img src="/images/logo.png" alt="A.I.G" className="w-5 h-5 mr-2 relative" style={{ top: '1px' }} />
            <h2
              className='text-lg font-semibold text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600'
              style={{ fontFamily: 'tencentSans', letterSpacing: '0.1em' }}
            >A.I.G</h2>
            {import.meta.env.VITE_SHOW_PRO_LOGO === 'true' && (
              <span className="ml-2 px-2 py-1 text-xs font-bold text-white bg-gradient-to-r from-blue-600 to-purple-600 rounded-full shadow-lg" style={{ fontFamily: "'tencentSans', sans-serif", letterSpacing: '0.05em' }}>
                PRO
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <Button 
              size="sm" 
              onClick={handleClearCurrentTask}
              className="bg-blue-600 hover:bg-blue-700 gap-0 h-7 px-2 text-xs"
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
            {t('task.newTask')}
            </Button>
          </div>
        </div>
      </div>
      <div className="text-xs text-gray-400 pl-3 pb-2 flex items-center justify-between">
        <span>{t('task.taskList')}</span>
        <Button
          variant='ghost'
          size='icon'
          className='text-gray-400 hover:text-gray-700 p-1'
          onClick={() => setShowSearchDialog(true)}
        >
          <svg xmlns='http://www.w3.org/2000/svg' className='w-4 h-4' fill='none' viewBox='0 0 24 24' stroke='currentColor'>
            <path strokeLinecap='round' strokeLinejoin='round' strokeWidth={2} d='M21 21l-4.35-4.35m0 0A7.5 7.5 0 104.5 4.5a7.5 7.5 0 0012.15 12.15z' />
          </svg>
        </Button>
      </div>
      
      {/* Task type filter */}
      <div className="px-3">
        <div className="flex flex-wrap gap-1">
          <button
            onClick={() => setSelectedTaskType('all')}
            className={`px-2 py-2 mb-1 text-xs rounded-xl transition-colors ${
              selectedTaskType === 'all'
                ? 'bg-gray-900 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            {t('task.all')}
          </button>
          {mcpServices.map(service => (
            <button
              key={service.id}
              onClick={() => setSelectedTaskType(service.id)}
              className={`px-2 py-2 text-xs rounded-xl transition-colors mb-1 ${
                selectedTaskType === service.id
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {service.name}
            </button>
          ))}
        </div>
      </div>
      
      {/* Task list */}
      <ScrollArea className="flex-1 custom-scrollarea">
        <TaskList
          tasks={getFilteredTasks()}
          currentTaskId={state.currentTaskId}
          onTaskClick={actions.loadTask}
          onTaskContextMenu={handleTaskContextMenu}
          getTaskIcon={getTaskIcon}
          formatDate={formatDate}
        />
      </ScrollArea>
      {contextMenu.open && (
        <div
          className="fixed z-50 min-w-[140px] rounded-md border border-zinc-200 bg-white p-1 shadow-lg"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(event) => event.stopPropagation()}
        >
          <button
            type="button"
            className={`w-full rounded-sm px-2 py-1.5 text-left text-sm flex items-center gap-2 ${
              terminateDisabled
                ? 'text-gray-400 cursor-not-allowed'
                : 'text-gray-700 hover:bg-gray-100'
            }`}
            onClick={openTerminateConfirm}
            disabled={terminateDisabled}
          >
            <Pause className="w-4 h-4" />
            {t('taskTerminate.terminateTask')}
          </button>
          <button
            type="button"
            className="w-full rounded-sm px-2 py-1.5 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
            onClick={openDeleteConfirm}
          >
            <Trash2 className="w-4 h-4" />
            {t('chatArea.deleteTask')}
          </button>
        </div>
      )}

      {/* Footer info */}
      <div className="p-4 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center text-xs text-blue-600 hover:text-blue-900">
            <ShieldQuestion className="w-4 h-4 mr-1" />
            <a 
              href="/help"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-900 transition-colors cursor-pointer"
            >
              {t('navigation.help')}
            </a>
          </div>
          <div className="flex items-center">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowSettingsDialog(true)}
                  className="text-blue-600 hover:text-blue-900 gap-1"
                >
                  <Settings className="w-4 h-4" />
                  <span className="text-xs">{t('common.settings') || '设置'}</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{t('common.settings') || '设置'}</p>
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      </div>

      {/* Settings dialog */}
      <SettingsDialog
        isOpen={showSettingsDialog}
        onClose={() => setShowSettingsDialog(false)}
      />

      {/* Search tasks dialog */}
      {showSearchDialog && (
        <div className='fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-30'>
          <div className='bg-white rounded-lg shadow-lg w-[520px] max-h-[80vh] flex flex-col'>
            <div className='p-4 border-b flex items-center gap-2'>
              <Search className='w-4 h-4 text-gray-400 mr-0' />
              <input
                className='flex-1 rounded px-0 py-1 text-sm outline-none  transition-all'
                placeholder={t('common.search')}
                value={searchValue}
                onChange={e => setSearchValue(e.target.value)}
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    handleSearch();
                  }
                }}
                maxLength={50}
              />
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size='icon'
                      variant='ghost'
                      className='text-gray-400 hover:text-gray-700 p-0 ml-2'
                      onClick={() => {
                        setShowSearchDialog(false);
                        setSearchValue('');
                        setSearchResult(null);
                      }}
                      aria-label={t('common.close')}
                    >
                      <X className='w-4 h-4' />
                    </Button>
                  </TooltipTrigger>
                <TooltipContent>
                  {t('common.close')}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            </div>
            <div className='flex-1 overflow-y-auto p-0 scrollbar-hover'>
              {searching ? (
                <div className='text-center text-gray-400 py-8'>{t('common.searching')}</div>
              ) : (
                <TaskList
                  tasks={getFilteredTasks()}
                  currentTaskId={state.currentTaskId}
                  onTaskClick={id => {
                    actions.loadTask(id);
                    setShowSearchDialog(false);
                  }}
                  onTaskContextMenu={handleTaskContextMenu}
                  getTaskIcon={getTaskIcon}
                  formatDate={formatDate}
                />
              )}
            </div>
          </div>
        </div>
      )}
      <DeleteConfirmDialog
        open={!!taskToDelete}
        loading={deleteLoading}
        error={deleteError}
        onConfirm={handleDeleteTask}
        onCancel={() => {
          setTaskToDelete(null);
          setDeleteError(undefined);
        }}
        title={t('taskDelete.confirmTitle')}
        description={t('taskDelete.confirmDescription')}
      />
      <DeleteConfirmDialog
        open={!!taskToTerminate}
        loading={terminateLoading}
        error={terminateError}
        onConfirm={handleTerminateTask}
        onCancel={() => {
          setTaskToTerminate(null);
          setTerminateError(undefined);
        }}
        title={t('taskTerminate.confirmTitle')}
        description={t('taskTerminate.confirmDescription')}
        confirmText={t('taskTerminate.confirm')}
        loadingText={t('taskTerminate.terminating')}
        cancelText={t('taskTerminate.cancel')}
      />
    </div>
    </TooltipProvider>
  );
};

export default TaskSidebar;
