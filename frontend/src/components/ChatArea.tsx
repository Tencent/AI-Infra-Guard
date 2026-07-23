import React, { useState, useRef, useEffect, useCallback, Suspense } from 'react';
import { useTranslation } from 'react-i18next';
import { useApp } from '../context/AppContext';
import { Message, MCPService, ExecutionStep, useTaskServiceInfo, MCPScanResult, InfraScanResult, RedteamReportResult, JailbreakResult, AgentScanResult, TaskType, EvaluationItem } from '../types';
import { v4 as uuidv4 } from 'uuid';
import { toast } from 'sonner';
import { ModelItem } from '../types/model';
import HttpHeaderDialog from './HttpHeaderDialog';
import ReactDOM from 'react-dom';
import TaskConfirmationMessage from './TaskConfirmationMessage';
import TaskExecutionTimeline from './TaskExecutionTimeline';
import EditTitleDialog from './EditTitleDialog';
import DeleteConfirmDialog from './DeleteConfirmDialog';
import CollapsibleTaskPlan from './CollapsibleTaskPlan';
import FloatingInputArea from './floatingInputArea/FloatingInputArea';
import StarPrompt from './StarPrompt';
import { shouldShowModelButton } from '../utils/taskUtils';
import { uploadFile } from '../utils/uploadUtils';
import { businessPartners, showBusinessPartners, PracticeShowcase } from '../config/privateModules';
import { useMcpServices } from '../config/mcpServices';
import { 
  Paperclip, 
  Shield, 
  AlertTriangle,
  AlertCircle,
  Bug,
  ShieldCheck,
  Key,
  Bot,
  User,
  Share,
  Edit,
  CheckCircle,
  FileText,
  Trash2,
  Pause,
  SearchCode,
  Sparkles
} from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './ui/tooltip';
import { useDropzone } from 'react-dropzone';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';

// Status mapping function
const mapStatusToStepStatus = (status: string): 'todo' | 'doing' | 'done' => {
  if (status === 'todo') return 'todo';
  if (status === 'doing' || status === 'running' || status === 'pending') return 'doing';
  if (status === 'done' || status === 'completed' || status === 'failed') return 'done';
  return 'todo';
};

// Message queue type definitions
interface QueueItem {
  id: string;
  type: string;
  data: any;
  timestamp: number;
}

const getPartnerPlaceholderText = (name: string) => {
  const latin = name.match(/[A-Za-z]+/g);
  if (latin && latin.length > 0) {
    const text = latin.join('').toUpperCase();
    return text.slice(0, 3);
  }
  return name.slice(0, 2);
};

const PartnerLogo: React.FC<{ name: string; logo: string }> = ({ name, logo }) => {
  const [imageError, setImageError] = useState(false);
  if (!logo || imageError) {
    return (
      <div className="w-10 h-10 rounded-lg bg-gray-100 border border-gray-200 flex items-center justify-center text-xs font-semibold text-gray-500">
        {getPartnerPlaceholderText(name)}
      </div>
    );
  }

  return (
    <img
      src={logo}
      alt={name}
      className="w-10 h-10 object-contain rounded-lg bg-white p-1"
      onError={() => setImageError(true)}
    />
  );
};


interface ChatAreaProps {
  selectedStep: ExecutionStep | null;
  onStepSelect: (step: ExecutionStep | null) => void;
  onMcpResultSelect: (result: MCPScanResult | InfraScanResult | RedteamReportResult | JailbreakResult | AgentScanResult) => void;
  onToolSelect?: (step: ExecutionStep, subStepIndex: number, toolIndex: number) => void;
  welcomeAnimationCompleted?: boolean;
}

const ChatArea: React.FC<ChatAreaProps> = ({ selectedStep, onStepSelect, onMcpResultSelect, onToolSelect, welcomeAnimationCompleted }) => {
  const { state, actions, dispatch } = useApp();
  const { t, i18n } = useTranslation();
  const mcpServices = useMcpServices();
  const [input, setInput] = useState('');
  const [showMcpMenu, setShowMcpMenu] = useState(false);
  const [showButtonMcpMenu, setShowButtonMcpMenu] = useState(false);
  const [attachments, setAttachments] = useState<File[]>([]);
  const [isRenaming, setIsRenaming] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [renameLoading, setRenameLoading] = useState(false);
  const [renameError, setRenameError] = useState<string | undefined>(undefined);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState<string | undefined>(undefined);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [terminateLoading, setTerminateLoading] = useState(false);
  const [terminateError, setTerminateError] = useState<string | undefined>(undefined);
  const [showTerminateConfirm, setShowTerminateConfirm] = useState(false);
  const [selectedModel, setSelectedModel] = useState<ModelItem | undefined>(undefined);
  const [selectedModels, setSelectedModels] = useState<ModelItem[]>([]);
  const [selectedEvalModel, setSelectedEvalModel] = useState<ModelItem | undefined>(undefined);
  const [currentTaskType, setCurrentTaskType] = useState<string | undefined>(undefined);
  const [selectedMcpService, setSelectedMcpService] = useState<MCPService | null>(null);
  const [httpHeaders, setHttpHeaders] = useState<{ key: string; value: string }[]>([]);
  const [showHttpHeaderDialog, setShowHttpHeaderDialog] = useState(false);
  const [selectedEvaluations, setSelectedEvaluations] = useState<EvaluationItem[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | undefined>(undefined);
  const [selectedAttackMethods, setSelectedAttackMethods] = useState<string[]>([]);
  const [maxEvaluationCount, setMaxEvaluationCount] = useState<number>(-1);

  // Message queue related state
  const [messageQueue, setMessageQueue] = useState<QueueItem[]>([]);
  
  // Auto-scroll related state
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [isProcessingQueue, setIsProcessingQueue] = useState(false);
  
  // SSE connection management
  const [activeSSEConnections, setActiveSSEConnections] = useState<Set<string>>(new Set());

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const inputAreaRef = useRef<HTMLDivElement>(null);
  const taskPlanRef = useRef<HTMLDivElement>(null);
  const [inputAreaHeight, setInputAreaHeight] = useState(0);
  const [taskPlanHeight, setTaskPlanHeight] = useState(0);

  const currentTask = state.tasks.find(task => task.id === state.currentTaskId);

  // Use useRef to obtain the latest state
  const stateRef = useRef(state);
  
  // Update stateRef inside useEffect to avoid mutation during render
  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  // Handle a single queued item
  const processQueueItem = useCallback(async (item: QueueItem) => {
    const { type, data, timestamp } = item;
    
    switch (type) {
      case 'connected':
        // Check whether the task already exists to avoid duplicate creation
        const existingTask = stateRef.current.tasks.find(task => task.id === data.sessionId);
        
        if (!existingTask) {
          actions.createTask('', data.taskType, data.sessionId);
          // Wait briefly to ensure the state has been updated
          await new Promise(resolve => setTimeout(resolve, 10));
          actions.sendMessage(data.sessionId, data.content, data.attachmentsWithNames);
        } else {
          // Even if the task already exists, send the message (when there is not one yet)
          if (existingTask.messages.length === 0) {
            actions.sendMessage(data.sessionId, data.content, data.attachmentsWithNames);
          }
        }
        break;
        
      case 'planUpdate':
        const currentTask = stateRef.current.tasks.find(task => task.id === data.sessionId);
        const planSteps = data.event.tasks.map((task, idx) => {
          const stepId = task.stepId || `step-${idx}`;
          return {
            id: stepId,
            title: task.title,
            status: mapStatusToStepStatus(task.status),
            progress: task.progress || 0,
            startTime: task.startedAt ? new Date(task.startedAt) : undefined,
            endTime: task.completedAt ? new Date(task.completedAt) : undefined,
            details: task.details || '',
            subSteps: currentTask?.plan[idx]?.subSteps || [],
          };
        });
        actions.updateTaskPlan(data.sessionId, planSteps);
        
        // Send these two messages only on the first planUpdate
        if (currentTask?.plan.length === 0) {
          // Check whether these message types already exist to avoid duplicate additions
          const hasConfirmationMessage = currentTask?.messages?.some(msg => msg.type === 'task_confirmation');
          const hasExecutionMessage = currentTask?.messages?.some(msg => msg.type === 'task_execution');
          
          if (!hasConfirmationMessage) {
            const confirmationMessage: Message = {
              id: uuidv4(),
              type: 'task_confirmation',
              content: '',
              timestamp: new Date(),
              attachments: [],
              executionPlan: planSteps,
            };
            dispatch({ type: 'ADD_MESSAGE', payload: { taskId: data.sessionId, message: confirmationMessage } });
          }
          
          if (!hasExecutionMessage) {
            const executionMessage: Message = {
              id: uuidv4(),
              type: 'task_execution',
              content: t('chatArea.taskExecuting'),
              timestamp: new Date(),
              attachments: [],
            };
            dispatch({ type: 'ADD_MESSAGE', payload: { taskId: data.sessionId, message: executionMessage } });
          }
        }
        break;
        
      case 'newPlanStep':

        const newStep = {
          id: data.event.stepId,
          title: data.event.title,
          status: mapStatusToStepStatus('doing'),
          progress: 0,
          subSteps: [],
        };
        actions.addExecutionStep(data.sessionId, newStep);
        break;
        
      case 'statusUpdate':
        if (!data.event?.planStepId) {
          const statusMessage = data.event?.description || data.event?.brief;
          if (statusMessage) {
            const rawTimestamp = data.event.timestamp;
            const timestamp = rawTimestamp
              ? new Date(rawTimestamp > 1e12 ? rawTimestamp : rawTimestamp * 1000)
              : new Date();

            dispatch({
              type: 'ADD_MESSAGE',
              payload: {
                taskId: data.sessionId,
                message: {
                  id: data.event.id || uuidv4(),
                  type: 'system',
                  brief: data.event?.brief,
                  content: statusMessage,
                  timestamp,
                },
              },
            });
          }

          if (data.event?.agentStatus === 'terminated' || data.event?.agentStaus === 'terminated') {
            dispatch({
              type: 'UPDATE_TASK',
              payload: {
                id: data.sessionId,
                updates: {
                  status: 'terminated',
                  updatedAt: new Date(),
                },
              },
            });
          }
          break;
        }

        const status = data.event.agentStaus || data.event.agentStatus;
        const rawTimestamp = data.event.timestamp;
        const newSubStep = {
          id: data.event.id || `${data.event.planStepId}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          brief: data.event.brief,
          description: data.event.description || '',
          status: mapStatusToStepStatus(status),
          message: {},
          timestamp: rawTimestamp ? new Date(rawTimestamp > 1e12 ? rawTimestamp : rawTimestamp * 1000) : undefined,
          toolUsed: [],
        };
        actions.addSubStep(data.sessionId, data.event.planStepId, newSubStep);
        break;
        
      case 'toolUsed':
        const toolUsed = data.event.tools.map((tool) => ({
          id: tool.toolId || tool.brief || Math.random().toString(),
          brief: tool.brief,
          status: mapStatusToStepStatus(tool.status),
          message: tool.message,
          result: tool.result,
          timestamp: data.event.timestamp ? new Date(data.event.timestamp * 1000) : undefined,
          tool: tool.tool,
          toolId: tool.toolId,
          actionLog: '', // Initialize the actionLog field
        }));
        actions.updateStepTools(data.sessionId, data.event.planStepId, data.event.statusId, toolUsed);
        break;
        
      case 'actionLog':
        // Use a dedicated action to update actionLog
        actions.updateActionLog(data.sessionId, data.event.planStepId, data.event.actionId, data.event.actionLog);
        break;
        
      case 'resultUpdate':
        // Check whether a result message already exists to avoid duplicate additions
        const resultTask = stateRef.current.tasks.find(task => task.id === data.sessionId);
        const hasResultMessage = resultTask?.messages.some(msg => msg.type === 'result');
        
        if (!hasResultMessage) {
          actions.updateTaskResult(data.sessionId, data.event.result, data.event.timestamp);
          actions.completeTask(data.sessionId, data.event);
        }
        break;
        
      case 'task_progress':
        actions.updateTaskProgress(data.sessionId, data.event);
        break;
        
      case 'error':
        // Add an error message to the task
        // Check whether the same error message already exists
        const errorTask = stateRef.current.tasks.find(task => task.id === data.sessionId);
        const errorContent = data.event.message || data.event.error || t('chatArea.unknownError');
        const hasErrorMessage = errorTask?.messages.some(msg => 
          msg.type === 'error' && msg.content === errorContent
        );
        
        if (!hasErrorMessage) {
          const errorMessage: Message = {
            id: uuidv4(),
            type: 'error',
            content: errorContent,
            timestamp: data.event.timestamp ? new Date(data.event.timestamp * 1000) : new Date(),
          };
          dispatch({ type: 'ADD_MESSAGE', payload: { taskId: data.sessionId, message: errorMessage } });
        }
        break;
        
      default:
    }
  }, [actions, dispatch, stateRef]);

  // Message queue handler
  const processMessageQueue = useCallback(async () => {
    if (isProcessingQueue) return;
    
    setIsProcessingQueue(true);
    
    // Get a snapshot of the current queue
    const currentQueue = [...messageQueue];
    
    if (currentQueue.length === 0) {
      setIsProcessingQueue(false);
      return;
    }
    
    // Clear the queue immediately to avoid duplicate handling
    setMessageQueue([]);
    
    // Handle messages in the queue
    for (const item of currentQueue) {
      try {
        await processQueueItem(item);
        // Add a small delay to ensure the state update completes
        await new Promise(resolve => setTimeout(resolve, 50));
      } catch (error) {
      }
    }
    
    setIsProcessingQueue(false);
  }, [isProcessingQueue, messageQueue, processQueueItem]);

  // Add a message to the queue
  const addToMessageQueue = (type: string, data: any) => {
    
    // Check whether a message of the same type already exists to avoid duplicate handling
    const existingItem = messageQueue.find(item => {
      if (item.type !== type || item.data.sessionId !== data.sessionId) {
        return false;
      }
      
      // Deduplicate 'connected' events to avoid creating duplicate tasks
      if (type === 'connected') {
        return true; // Skip adding when a connected message with the same sessionId already exists
      }
      
      // Deduplicate 'error' events to avoid showing the same error twice
      if (type === 'error') {
        // Check whether the same error content exists
        return item.data.event?.message === data.event?.message && 
               item.data.event?.error === data.event?.error;
      }
      
      // Do not deduplicate 'statusUpdate' events; allow multiple status updates to be shown
      if (type === 'statusUpdate') {
        return false;
      }
      
      // Deduplicate 'resultUpdate' events to avoid duplicate result messages
      if (type === 'resultUpdate') {
        return true;
      }
      
      // For other types, check for the same planStepId (if present)
      /*if (data.event?.planStepId && item.data.event?.planStepId) {
        return item.data.event.planStepId === data.event.planStepId;
      }*/
      
      // If no planStepId is present, allow adding (to avoid over-deduplication)
      return false;
    });
    
    if (existingItem) {
      return;
    }
    
    
    const queueItem: QueueItem = {
      id: uuidv4(),
      type,
      data,
      timestamp: Date.now(),
    };
    
    setMessageQueue(prev => [...prev, queueItem]);
  };

  // Watch queue changes and handle them automatically
  useEffect(() => {
    if (messageQueue.length > 0 && !isProcessingQueue) {
      processMessageQueue();
    }
  }, [messageQueue.length, isProcessingQueue, processMessageQueue]);

  useEffect(() => {
    const handleTaskStatusUpdate = (event: Event) => {
      const customEvent = event as CustomEvent<any>;
      const payload = customEvent.detail;
      if (!payload?.sessionId || payload?.event?.type !== 'statusUpdate') {
        return;
      }

      if (payload.event.planStepId) {
        addToMessageQueue('statusUpdate', {
          sessionId: payload.sessionId,
          event: payload.event,
        });
        return;
      }

      if (payload.event.brief) {
        dispatch({
          type: 'ADD_MESSAGE',
          payload: {
            taskId: payload.sessionId,
            message: {
              id: payload.id || uuidv4(),
              type: 'system',
              brief: payload.event.brief,
              content: payload.event.description || payload.event.brief,
              timestamp: payload.timestamp ? new Date(payload.timestamp) : new Date(),
            },
          },
        });
      }

      if (payload.event.agentStatus === 'terminated' || payload.event.agentStaus === 'terminated') {
        dispatch({
          type: 'UPDATE_TASK',
          payload: {
            id: payload.sessionId,
            updates: {
              status: 'terminated',
              updatedAt: new Date(),
            },
          },
        });
      }
    };

    window.addEventListener('taskStatusUpdate', handleTaskStatusUpdate as EventListener);
    return () => {
      window.removeEventListener('taskStatusUpdate', handleTaskStatusUpdate as EventListener);
    };
  }, [addToMessageQueue, dispatch]);

  // Clean up the SSE connection when the component unmounts
  useEffect(() => {
    return () => {
      // Clean up all active SSE connections
      setActiveSSEConnections(new Set());
    };
  }, []);

  // Watch clearInputTrigger and clear the input content on change
  useEffect(() => {
    if (state.clearInputTrigger > 0) {
      setInput('');
      setAttachments([]);
      clearSelectedMcpService();
      setSelectedModel(undefined);
      setSelectedModels([]);
      setMaxEvaluationCount(-1);
      setSelectedAgent(undefined);
      setSelectedEvalModel(undefined);
      setSelectedEvaluations([]);
      setHttpHeaders([]);
      setShowMcpMenu(false);
      setShowButtonMcpMenu(false);
    }
  }, [state.clearInputTrigger]);

  // Watch the current task; establish an SSE connection when the current task is unfinished
  useEffect(() => {
    if (state.currentTaskId && currentTask) {
      // If the current task is unfinished and there is no SSE connection, establish one
      if (currentTask?.status === 'running' && !activeSSEConnections.has(state.currentTaskId)) {
        // Delay establishing the connection to ensure the task data is loaded
        setTimeout(() => {
          if (!activeSSEConnections.has(state.currentTaskId)) {
            establishSSEConnection(state.currentTaskId, '', [], currentTask?.type);
          }
        }, 100);
      }
    }
  }, [state.currentTaskId, currentTask?.status]);

  // Detect the scroll position
  useEffect(() => {
    const checkScrollPosition = () => {
      const scrollArea = document.querySelector('[data-radix-scroll-area-viewport]');
      if (scrollArea) {
        const { scrollTop, scrollHeight, clientHeight } = scrollArea as HTMLElement;
        const isAtBottom = scrollTop + clientHeight >= scrollHeight - 10; // 10px tolerance
        setShouldAutoScroll(isAtBottom);
      }
    };

    // Listen for scroll events
    const scrollArea = document.querySelector('[data-radix-scroll-area-viewport]');
    if (scrollArea) {
      scrollArea.addEventListener('scroll', checkScrollPosition);
      // Initial scroll-position check
      checkScrollPosition();
      return () => scrollArea.removeEventListener('scroll', checkScrollPosition);
    }
  }, []);

  // Auto-scroll to the bottom
  const scrollToBottom = () => {
    if (messagesEndRef.current && shouldAutoScroll) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Force scroll to the bottom (used when the task starts)
  const forceScrollToBottom = () => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // Auto-scroll to the bottom
  useEffect(() => {
    // Auto-scroll if the task is running and the user was previously at the bottom
    if (currentTask?.status === 'running' && shouldAutoScroll) {
      setTimeout(scrollToBottom, 100);
    } else if (currentTask?.messages && currentTask.messages.length > 0) {
      // For new messages, always scroll to the bottom
      setTimeout(scrollToBottom, 100);
    }
  }, [currentTask?.messages, currentTask?.status, shouldAutoScroll]);

  // Watch the message count and auto-scroll when new messages arrive
  useEffect(() => {
    if (currentTask?.messages && currentTask.messages.length > 0) {
      const lastMessage = currentTask?.messages?.[currentTask.messages.length - 1];
      // Auto-scroll for system, error, or result messages
      if (lastMessage.type === 'system' || lastMessage.type === 'error' || lastMessage.type === 'result') {
        setTimeout(forceScrollToBottom, 100);
      }
    }
  }, [currentTask?.messages?.length]);

  // Watch task-plan changes and auto-scroll when new execution steps appear
  useEffect(() => {
    if (currentTask?.status === 'running' && currentTask?.plan && currentTask?.plan.length > 0) {
      // Check whether there is a running step
      const hasDoingStep = currentTask?.plan?.some(step => step.status === 'doing');
      if (hasDoingStep && shouldAutoScroll) {
        setTimeout(scrollToBottom, 100);
      }
    }
  }, [currentTask?.plan, currentTask?.status, shouldAutoScroll]);

  // Watch task status changes and auto-scroll when a task starts running
  useEffect(() => {
    if (currentTask?.status === 'running') {
      // When the task starts running, auto-scroll to the bottom after a short delay
      setTimeout(() => {
        setShouldAutoScroll(true);
        setTimeout(forceScrollToBottom, 50);
      }, 200);
    }
  }, [currentTask?.status]);

  // File drag-and-drop upload
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        setAttachments([acceptedFiles[0]]);
      }
    },
    noClick: true,
  });

  // Chunked file upload
  const uploadFileChunked = async (file: File) => {
    const CHUNK_SIZE = 1 * 1024 * 1024; // 1MB
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE);
    const fileId = uuidv4();
    const filename = file.name;

    for (let chunkIndex = 0; chunkIndex < totalChunks; chunkIndex++) {
      const start = chunkIndex * CHUNK_SIZE;
      const end = Math.min(start + CHUNK_SIZE, file.size);
      const chunk = file.slice(start, end);
      
      const formData = new FormData();
      formData.append('fileId', fileId);
      formData.append('filename', filename);
      formData.append('chunkIndex', chunkIndex.toString());
      formData.append('totalChunks', totalChunks.toString());
      formData.append('chunk', chunk);
      
      const response = await fetch('/api/v1/app/tasks/uploadChunk', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Chunk ${chunkIndex + 1}/${totalChunks} upload failed`);
      }
      
      const result = await response.json();
      if (result.status !== 0) {
        throw new Error(result.message || `Chunk ${chunkIndex + 1}/${totalChunks} upload failed`);
      }
    }

    // Merge chunks
    const mergeResponse = await fetch('/api/v1/app/tasks/mergeChunks', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        fileId,
        filename,
        totalChunks,
        fileSize: file.size,
      }),
    });

    if (!mergeResponse.ok) {
      throw new Error('Merge chunks failed');
    }

    const mergeResult = await mergeResponse.json();
    if (mergeResult.status !== 0) {
      throw new Error(mergeResult.message || 'Merge chunks failed');
    }

    return mergeResult.data;
  };

  // Handle attachment upload
  const processAttachments = async (files: File[]) => {
    const attachmentUrls: string[] = [];
    const attachmentsWithNames: { filename: string, fileUrl: string }[] = [];
    
    if (files.length > 0) {
      for (const file of files) {
        let result;
        // If the file is larger than 1MB, use chunked upload
        if (file.size > 1 * 1024 * 1024) {
          result = await uploadFileChunked(file);
        } else {
          const formData = new FormData();
          formData.append('file', file);
          
          const uploadResponse = await fetch('/api/v1/app/tasks/uploadFile', {
            method: 'POST',
            body: formData,
          });
          
          if (uploadResponse.ok) {
            const uploadResult = await uploadResponse.json();
            if (uploadResult.status === 0) {
              result = uploadResult.data;
            } else {
              throw new Error(uploadResult.message || t('chatArea.uploadError'));
            }
          } else {
            throw new Error(t('chatArea.uploadError'));
          }
        }
        
        if (result) {
          attachmentUrls.push(result.fileUrl);
          attachmentsWithNames.push(result);
        }
      }
    }
    return { attachmentUrls, attachmentsWithNames };
  };

  // Send message
  const [isSending, setIsSending] = useState(false);
  
  const handleSend = async () => {
    if (isSending) {
      return;
    }
    
    const taskType = selectedMcpService.id;
    
    // For a Model-Redteam-Report task type, the input content check is unnecessary
    // For an Agent-Scan task type, the input content check is also unnecessary
    if (taskType !== 'Model-Redteam-Report' && taskType !== 'Agent-Scan' && !input.trim() && attachments.length === 0) return;
    
    setIsSending(true);

    const content = input.trim();
    
    // Upload attachments
    let attachmentUrls: string[] = [];
    let attachmentsWithNames: { filename: string, fileUrl: string }[] = [];
    
    try {
      const result = await processAttachments(attachments);
      attachmentUrls = result.attachmentUrls;
      attachmentsWithNames = result.attachmentsWithNames;
    } catch (error: any) {
      toast.error(error.message || t('chatArea.uploadError'));
      setIsSending(false);
      return;
    }

    // When no task is selected, send the request to the backend first
    if (!currentTask) {
      // Check whether an MCP service is selected
      if (!selectedMcpService) {
        toast.error(t('chatArea.selectServiceFirst'));
        setIsSending(false);
        return;
      }
      
      // Send the message to the server first
      const tempTaskId = `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      const result = sendMessageToServer(tempTaskId, content, attachmentUrls, taskType);

      // Establish the SSE connection after a 100ms delay
      setTimeout(() => {
        // Re-check whether the connection already exists
        if (!activeSSEConnections.has(tempTaskId)) {
          establishSSEConnection(tempTaskId, content, attachmentsWithNames, taskType);
        }
      }, 100);
    } else {
      const result = await sendMessageToServer(currentTask?.id, content, attachmentUrls, currentTask?.type);
      // Establish the SSE connection immediately
      setTimeout(() => {
        establishSSEConnection(currentTask?.id, content, attachmentsWithNames, currentTask?.type);
      }, 100);
      if (result.success) {
        actions.sendMessage(currentTask?.id, content, attachments);
      }
    }
    
    setInput('');
    setAttachments([]);
    // Clear selectedMcpService
    clearSelectedMcpService();
    // Clear the selected model
    setSelectedModel(undefined);
    setSelectedModels([]);
    setSelectedAgent(undefined);
    // Reset the max evaluation total
    setMaxEvaluationCount(-1);
    // Clear the selected evalModel
    setSelectedEvalModel(undefined);
    // Clear the selected evaluation set (including custom sets)
    setSelectedEvaluations([]);
    // Clear HTTP Headers
    setHttpHeaders([]);
    setShowMcpMenu(false);
    setShowButtonMcpMenu(false);
    
    // Reset the sending state
    setIsSending(false);
  };


  // Send the message to the server
  const sendMessageToServer = async (taskId: string, content: string, attachments: string[], taskType: string): Promise<{ success: boolean; title?: string }> => {
    try {
      
      // Send the task request
      const timestamp = Date.now();
      // Build the params object
      const params: any = {
        // model_id: 'model_1752130627004_r10nyjocw',
        model_id: taskType === 'Agent-Scan' ? undefined : getModelId(taskType, selectedModel, selectedModels),
        eval_model_id: taskType === 'Agent-Scan' ? getModelId(taskType, selectedModel, selectedModels) : getEvalModelId(taskType, selectedEvalModel),
      };
      
      // For an AI-Infra-Scan or Mcp-Scan task with HTTP Headers, add them to params
      // Note: Skill-Scan does not allow HTTP Header configuration
      if ((taskType === 'AI-Infra-Scan' || taskType === 'Mcp-Scan') && httpHeaders.length > 0) {
        const headersObj: { [key: string]: string } = {};
        httpHeaders.forEach(header => {
          if (header.key.trim() && header.value.trim()) {
            headersObj[header.key.trim()] = header.value.trim();
          }
        });
        if (Object.keys(headersObj).length > 0) {
          params.headers = headersObj;
        }
      }
      
      // When content has a value, set dataset to undefined
      if (content) {
        params.dataset = undefined;
      } else if (selectedEvaluations.length > 0) {
        // If an evaluation set is selected, add it to params
        params.dataset = {
          dataFile: selectedEvaluations.filter(evaluation => !evaluation.isCustom).map(evaluation => evaluation.name),
        };
        
        // For a custom evaluation set, add promptColumn info
        const customEvaluation = selectedEvaluations.find(evaluation => evaluation.isCustom);
        if (customEvaluation && customEvaluation.promptColumn) {
          params.dataset.promptColumn = customEvaluation.promptColumn;
        }
        
        // Add the max evaluation total parameter
        if (maxEvaluationCount !== -1) {
          params.dataset.numPrompts = maxEvaluationCount;
        }
      }
      
      // For a Model-Redteam-Report task with selected attack methods, add them to params
      if (taskType === 'Model-Redteam-Report' && selectedAttackMethods.length > 0) {
        params.techniques = selectedAttackMethods;
      }
      
      // For an Agent-Scan task, add the agent parameter
      if (taskType === 'Agent-Scan' && selectedAgent) {
        params.agent_id = selectedAgent;
      }

      const requestBody = {
        id: taskId,
        sessionId: taskId,
        taskType,
        timestamp: timestamp,
        content: content,
        params: params,
        attachments: attachments,
        countryIsoCode: i18n.language,
      };

     
      // Send the POST request asynchronously without waiting for a response
      fetch('/api/v1/app/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      }).then(async (response) => {
        if (response.ok) {
          const result = await response.json();
          if (result.status === 0) {
            // Add the new task to the task list, using taskId as sessionId
            // actions.createTask(result.data.title, requestBody.taskType, taskId);
            const currentTask = stateRef.current.tasks.find(task => task.id === taskId);
            // Update the task title with the returned result.data.title
            if (currentTask) {
              actions.updateTaskTitle(taskId, result.data.title);
            }
            // Send the message directly without waiting for the state update
            // actions.sendMessage(result.data.sessionId, content, attachmentsWithNames);
          } else {
            handleTaskFailure(taskId, requestBody);
            // Show the error toast
            toast.error(result.message || t('chatArea.serverError'));
          }
        } else {
          handleTaskFailure(taskId, requestBody);
          // Show the error toast
          toast.error(t('chatArea.httpError', { status: response.status }));
        }
      }).catch(error => {
        handleTaskFailure(taskId, requestBody);
        // Show the error toast
        toast.error(t('chatArea.networkError'));
      });
      // Return success immediately without waiting for the POST response
      return { success: true };
    } catch (error) {
      // Show the error toast
              toast.error(t('chatArea.messageSendError'));
      return { success: false };
    }
  };

  // Establish the SSE connection
  const establishSSEConnection = (sessionId: string, content: string, attachmentsWithNames: { filename: string, fileUrl: string }[], taskType: string) => {
    // Check whether a connection for this sessionId already exists
    if (activeSSEConnections.has(sessionId)) {
      return;
    }
    
    const eventSource = new EventSource(`/api/v1/app/tasks/sse/${sessionId}`);
    
    // Add to the active connection list
    setActiveSSEConnections(prev => new Set(prev).add(sessionId));
    
    eventSource.onopen = () => {
      // SSE connection established
    };

    eventSource.addEventListener('connected', (event) => {
      // Handle connected events via the message queue
      addToMessageQueue('connected', {
        taskType,
        sessionId,
        content,
        attachmentsWithNames,
      });
    });

    eventSource.addEventListener('planUpdate', (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'planUpdate' && data.event?.tasks) {
        // Handle planUpdate events via the message queue
        addToMessageQueue('planUpdate', {
          sessionId,
          event: data.event,
        });
      }
    });

    eventSource.addEventListener('newPlanStep', (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'newPlanStep' && data.event) {
        // Handle newPlanStep events via the message queue
        addToMessageQueue('newPlanStep', {
          sessionId,
          event: data.event,
        });
      }
    });

    eventSource.addEventListener('statusUpdate', (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'statusUpdate' && data.event) {
        // Handle statusUpdate events via the message queue
        addToMessageQueue('statusUpdate', {
          sessionId,
          event: data.event,
        });
      }
    });

    eventSource.addEventListener('toolUsed', (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'toolUsed' && data.event?.planStepId && Array.isArray(data.event.tools)) {
        // Handle toolUsed events via the message queue
        addToMessageQueue('toolUsed', {
          sessionId,
          event: data.event,
        });
      }
    });

    eventSource.addEventListener('resultUpdate', (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'resultUpdate' && data.event?.result) {
        // Handle resultUpdate events via the message queue
        addToMessageQueue('resultUpdate', {
          sessionId,
          event: data.event,
        });
        eventSource.close();
        // Remove from the active connection list
        setActiveSSEConnections(prev => {
          const newSet = new Set(prev);
          newSet.delete(sessionId);
          return newSet;
        });
      }
    });

    eventSource.addEventListener('actionLog', (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'actionLog' && data.event?.planStepId) {
        // Handle actionLog events via the message queue
        addToMessageQueue('actionLog', {
          sessionId,
          event: data.event,
        });
      }
    });

    eventSource.addEventListener('error', (event) => {
      try {
        const data = JSON.parse((event as any).data);
        if (data.type === 'error' && data.event) {
          // Handle error events via the message queue
          addToMessageQueue('error', {
            sessionId,
            event: data.event,
          });
        }
      } catch (error) {
      }
    });

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        // Handle different types of SSE messages
        if (data.type === 'connected') {
        } else if (data.type === 'task_progress') {
          // Handle task_progress events via the message queue
          addToMessageQueue('task_progress', {
            sessionId,
            event: data.event,
          });
        }
      } catch (error) {
      }
    };
    
    eventSource.onerror = (error) => {
      eventSource.close();
      // Remove from the active connection list
      setActiveSSEConnections(prev => {
        const newSet = new Set(prev);
        newSet.delete(sessionId);
        return newSet;
      });
    };
  };
  // Handle task failure
  const handleTaskFailure = (taskId: string, requestBody?: any) => {
    // Delete the corresponding task
    const taskToDelete = stateRef.current.tasks.find(task => task.id === taskId);
    if (taskToDelete) {
      actions.deleteTask(taskId);
    }
  };

  // Handle input changes
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInput(value);
    // Auto-adjust the height
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  };

  // Handle input blur
  const handleInputBlur = () => {
    // Delay closing the menu to avoid closing it immediately when clicking a menu item
    setTimeout(() => {
      setShowMcpMenu(false);
    }, 200);
  };



  // Remove an attachment
  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  // Rename the task
  const handleRenameTask = async (title: string) => {
    if (!currentTask || !title.trim()) return;
    setRenameLoading(true);
    setRenameError(undefined);
    try {
      const response = await fetch(`/api/v1/app/tasks/${currentTask?.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: title.trim(),
        }),
      });
      const result = await response.json();
      if (result.status === 0) {
        actions.updateTaskTitle(currentTask?.id, title.trim());
        setIsRenaming(false);
        setNewTitle('');
      } else {
        setRenameError(result.message || t('chatArea.renameFailed'));
      }
    } catch (error) {
      setRenameError(t('chatArea.renameRequestFailed'));
    } finally {
      setRenameLoading(false);
    }
  };

  // Delete the task
  const handleDeleteTask = async () => {
    if (!currentTask) return;
    setDeleteLoading(true);
    setDeleteError(undefined);
    try {
      const response = await fetch(`/api/v1/app/tasks/${currentTask?.id}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const result = await response.json();
      if (result.status === 0) {
        // After successful deletion, clear the current task
        actions.deleteTask(currentTask?.id);
        setShowDeleteConfirm(false);
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

  const buildTerminateStatusUpdatePayload = (taskId: string) => {
    const timestamp = Date.now();
    const now = new Date();
    const formatPart = (value: number, length = 2) => value.toString().padStart(length, '0');
    const eventId = `${now.getFullYear()}${formatPart(now.getMonth() + 1)}${formatPart(now.getDate())}${formatPart(now.getHours())}${formatPart(now.getMinutes())}${formatPart(now.getSeconds())}_${timestamp}`;
    return {
      id: eventId,
      type: 'event',
      sessionId: taskId,
      timestamp,
      event: {
        id: eventId,
        type: 'statusUpdate',
        timestamp,
        agentStatus: 'terminated',
        agentStaus: 'terminated',
      },
    };
  };

  const handleTerminateTask = async () => {
    if (!currentTask) return;
    setTerminateLoading(true);
    setTerminateError(undefined);
    try {
      const response = await fetch(`/api/v1/app/tasks/${currentTask?.id}/terminate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      const result = await response.json();
      if (result.status === 0) {
        const statusUpdatePayload = buildTerminateStatusUpdatePayload(currentTask.id);
        window.dispatchEvent(new CustomEvent('taskStatusUpdate', { detail: statusUpdatePayload }));
        setShowTerminateConfirm(false);
        toast.success(result.message || t('taskTerminate.terminateSuccess'));
      } else {
        setTerminateError(result.message || t('taskTerminate.terminateFailed'));
      }
    } catch (error) {
      setTerminateError(t('taskTerminate.terminateRequestFailed'));
    } finally {
      setTerminateLoading(false);
    }
  };

  // Get the message icon
  const getMessageIcon = (type: Message['type']) => {
    switch (type) {
      case 'user':
        return <User className="w-5 h-5" />;
      case 'assistant':
        return <Bot className="w-5 h-5" />;
      case 'system':
        return <Shield className="w-5 h-5" />;
      default:
        return <Bot className="w-5 h-5" />;
    }
  };

  // Format the time
  const formatTime = (date: Date | string) => {
    const dateObj = typeof date === 'string' ? new Date(date) : date;
    return new Intl.DateTimeFormat('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(dateObj);
  };

  // Get the icon component by name
  const getServiceIcon = (iconName: string) => {
    const iconMap: { [key: string]: React.ComponentType<any> } = {
      Bug,
      ShieldCheck,
      AlertTriangle,
      Key,
      SearchCode,
      Bot,
      Sparkles,
    };
    
    const IconComponent = iconMap[iconName];
    return IconComponent ? <IconComponent className="w-4 h-4" /> : <Bug className="w-4 h-4" />;
  };

  useEffect(() => {
    if (!inputAreaRef.current) return;
    
    const updateHeight = () => {
      if (inputAreaRef.current) {
        const taskPlanHeight = taskPlanRef.current?.offsetHeight || 0;
        setInputAreaHeight(
          inputAreaRef.current.offsetHeight + taskPlanHeight
        );
        setTaskPlanHeight(taskPlanHeight);
      }
    };
    
    const observer = new window.ResizeObserver(updateHeight);
    observer.observe(inputAreaRef.current);
    
    // Observe taskPlanRef.current only when it exists
    if (taskPlanRef.current) {
      observer.observe(taskPlanRef.current);
    }
    
    setTimeout(updateHeight, 1);
    return () => observer.disconnect();
  }, [currentTask]);

  useEffect(() => {}, [inputAreaHeight]);
  
  
  // Watch the appearance and disappearance of the task-plan area
  useEffect(() => {
    const hasTaskPlan = currentTask?.plan && currentTask?.plan.length > 0;
    if (hasTaskPlan && taskPlanRef.current) {
      // Recalculate the height when the task-plan area appears
      setTimeout(() => {
        if (taskPlanRef.current) {
          const newHeight = taskPlanRef.current.offsetHeight;
          setTaskPlanHeight(newHeight);
        }
      }, 100);
    } else {
      // Reset the height when the task-plan area disappears
      setTaskPlanHeight(0);
    }
  }, [currentTask?.plan]);
  
  // Handle changes to the expanded state of the task plan
  const handleTaskPlanExpandedChange = (expanded: boolean) => {
    // Give the DOM a moment to finish updating
    setTimeout(() => {
      if (taskPlanRef.current) {
        const newHeight = taskPlanRef.current.offsetHeight;
        setTaskPlanHeight(newHeight);
      }
    }, 50);
  };

  // Handle model selection
  const handleModelSelect = (model: ModelItem | undefined) => {
    setSelectedModel(model);
  };

  // Handle multi-select model selection
  const handleModelsSelect = (models: ModelItem[]) => {
    setSelectedModels(models);
  };

  // Handle evalModel selection
  const handleEvalModelSelect = (model: ModelItem) => {
    setSelectedEvalModel(model);
  };

  // Handle task type changes
  const handleTaskTypeChange = (taskType: string) => {
    // Clear the state only when there is already a task type and it is switched to a different one
    // If there was no previous task type (currentTaskType is empty), preserve the input state
    if (currentTaskType && taskType && currentTaskType !== taskType) {
      // Clear the selected model
      setSelectedModel(undefined);
      setSelectedModels([]);
      setSelectedAgent(undefined);
      // Clear the input
      setInput('');
    }
    setCurrentTaskType(taskType);
  };

  // Handle MCP service selection
  const handleMcpServiceSelect = (service: MCPService) => {
    setSelectedMcpService(service);
    setCurrentTaskType(service.id);
  };

  // Clear the selected MCP service
  const clearSelectedMcpService = () => {
    setSelectedMcpService(null);
    setCurrentTaskType(undefined);
  };

  // Get model ID
  const getModelId = (taskType: string, selectedModel?: ModelItem, selectedModels?: ModelItem[]) => {
    // Look up the matching MCP service config based on the task type
    const mcpService = mcpServices.find(service => service.id === taskType);
    
    // If the service config's model is 'no', return undefined
    if (mcpService && mcpService.model === 'no') {
      return undefined;
    }
    
    // If the service config's model is 'multi', return an array of model_id
    if (mcpService && mcpService.model === 'multi') {
      if (selectedModels && selectedModels.length > 0) {
        return selectedModels.map(model => model.model_id);
      }
      return undefined;
    }
    
    // Otherwise decide based on shouldShowModelButton and selectedModel (single-select mode)
    if (shouldShowModelButton(taskType) && selectedModel) {
      return selectedModel.model_id;
    }
    
    return undefined;
  };

  // Get evalModel ID
  const getEvalModelId = (taskType: string, selectedEvalModel?: ModelItem) => {
    // Look up the matching MCP service config based on the task type
    const mcpService = mcpServices.find(service => service.id === taskType);
    
    // If the service config's evalModel is 'yes' and an evalModel is selected, return its ID
    if (mcpService && (mcpService as any).evalModel === 'yes' && selectedEvalModel) {
      return selectedEvalModel.model_id;
    }
    
    return undefined;
  };

  // Handle HTTP Headers changes
  const handleHttpHeadersChange = (headers: { key: string; value: string }[]) => {
    setHttpHeaders(headers);
    setShowHttpHeaderDialog(false);
  };

  const handleEvaluationsSelect = (evaluations: EvaluationItem[]) => {
    setSelectedEvaluations(evaluations);
  };

  const handleAgentSelect = (agent: string) => {
    setSelectedAgent(agent);
  };

  if (!currentTask) {
    return (
      <TooltipProvider>
        <div className="flex-1 flex flex-col bg-gray-50 relative h-full !overflow-y-auto scrollbar-hover">
          <div className="flex flex-col items-center justify-center">
            <FloatingInputArea
              input={input}
              setInput={setInput}
              attachments={attachments}
              setAttachments={setAttachments}
              showMcpMenu={showMcpMenu}
              setShowMcpMenu={setShowMcpMenu}
              showButtonMcpMenu={showButtonMcpMenu}
              setShowButtonMcpMenu={setShowButtonMcpMenu}
              mcpServices={mcpServices}
              handleSend={handleSend}
              handleInputChange={handleInputChange}
              handleInputBlur={handleInputBlur}
              removeAttachment={removeAttachment}
              getServiceIcon={getServiceIcon}
              mode="center"
              inputRef={inputRef}
              inputAreaRef={inputAreaRef}
              taskType={currentTaskType || currentTask?.type}
              selectedModel={selectedModel}
              onModelSelect={handleModelSelect}
              selectedModels={selectedModels}
              onModelsSelect={handleModelsSelect}
              selectedEvalModel={selectedEvalModel}
              onEvalModelSelect={handleEvalModelSelect}
              onTaskTypeChange={handleTaskTypeChange}
              currentTaskId={state.currentTaskId}
              currentTask={currentTask}
              httpHeaders={httpHeaders}
              onHttpHeadersChange={handleHttpHeadersChange}
              selectedMcpService={selectedMcpService}
              onMcpServiceSelect={handleMcpServiceSelect}
              onClearMcpService={clearSelectedMcpService}
              selectedEvaluations={selectedEvaluations}
              onEvaluationsSelect={handleEvaluationsSelect}
              selectedAgent={selectedAgent}
              onAgentSelect={handleAgentSelect}
              selectedAttackMethods={selectedAttackMethods}
              onAttackMethodsSelect={setSelectedAttackMethods}
              triggerWelcomeAnimation={state.triggerWelcomeAnimation}
              maxEvaluationCount={maxEvaluationCount}
              onMaxEvaluationCountChange={setMaxEvaluationCount}
              welcomeAnimationCompleted={welcomeAnimationCompleted}
              isSending={isSending}
            />
            <HttpHeaderDialog
              open={showHttpHeaderDialog}
              headers={httpHeaders}
              onConfirm={handleHttpHeadersChange}
              onCancel={() => setShowHttpHeaderDialog(false)}
            />
          </div>
          {showBusinessPartners && businessPartners.length > 0 && (
            <section className="w-full max-w-7xl px-8 mt-8 mx-auto" style={{ marginBottom: '10rem' }}>
              <h2 className="text-4xl font-bold text-blue-800 mb-12 text-center">{t('chatArea.businessPartners', { defaultValue: '业务合作伙伴' })}</h2>
              <div className="flex flex-wrap justify-center gap-4 md:gap-6 pb-4">
                {businessPartners.map((partner) => (
                  <div
                    key={partner.name}
                    className="flex items-center gap-3 bg-white rounded-2xl px-6 py-4 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] hover:shadow-[0_8px_30px_-4px_rgba(59,130,246,0.15)] hover:-translate-y-1 hover:border-blue-100 border border-transparent transition-all duration-300 cursor-pointer"
                  >
                    <PartnerLogo name={partner.name} logo={partner.logo} />
                    <span className="text-base font-medium text-gray-700 whitespace-nowrap">{partner.name}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
          {PracticeShowcase && (
            <Suspense fallback={null}>
              <PracticeShowcase />
            </Suspense>
          )}
          <div className="flex justify-center items-center pb-2">
            <span className="text-sm text-gray-400 mr-4">Powered by:</span>
            <img
              src="/images/zhuque.png"
              alt="zhuque"
              className="h-9 w-auto"
            />
          </div>
          {/* Star prompt & sensitive-data prompt - shown when there is no currentTaskId */}
          {!state.currentTaskId && (
            <div className="fixed bottom-6 right-6 z-50 flex flex-col space-y-4 items-end">
              <StarPrompt githubUrl="https://github.com/Tencent/AI-Infra-Guard" />
            </div>
          )}
        </div>
      </TooltipProvider>
    );
  }

  return (
    <TooltipProvider>
      <div className="flex-1 flex flex-col bg-gray-50 relative min-w-0 h-full focus:outline-none" {...getRootProps()}>
        <input {...getInputProps()} />
        
        {/* Task header */}
        <div className="p-4">
          <div className='flex items-center justify-between'>
            <div className="flex items-center min-w-0 flex-1">
              <Tooltip>
                <TooltipTrigger asChild>
                  <h2 className="text-lg font-semibold text-gray-900 mr-2 truncate cursor-help">{currentTask?.title}</h2>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{currentTask?.title}</p>
                </TooltipContent>
              </Tooltip>
              <Badge variant="outline" className="text-xs text-gray-600 py-1 px-2 flex-shrink-0">
                {mcpServices.find(service => service.id === currentTask?.type)?.name || currentTask?.type}
              </Badge>
            </div>
            <div className="flex space-x-2 ml-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size='sm'
                    variant='ghost'
                    className='p-2 h-8 w-8 border rounded-[10px] hover:bg-gray-100 hover:border-gray-300'
                    onClick={() => setShowTerminateConfirm(true)}
                    disabled={currentTask?.status !== 'running'}
                  >
                    <Pause className='w-4 h-4 text-gray-600' />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{t('taskTerminate.terminateTask')}</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size='sm'
                    variant='ghost'
                    className='p-2 h-8 w-8 border rounded-[10px] hover:bg-red-50 hover:border-red-200'
                    onClick={() => setShowDeleteConfirm(true)}
                  >
                    <Trash2 className='w-4 h-4 text-red-500' />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{t('chatArea.deleteTask')}</p>
                </TooltipContent>
              </Tooltip>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size='sm'
                    variant='ghost'
                    className='p-2 h-8 w-8 border rounded-[10px]'
                    onClick={() => {
                      setIsRenaming(true);
                      setNewTitle(currentTask?.title);
                    }}
                  >
                    <Edit className='w-4 h-4' />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{t('chatArea.renameTask')}</p>
                </TooltipContent>
              </Tooltip>
          </div>
        </div>
      </div>
      <EditTitleDialog
        open={isRenaming}
        defaultValue={newTitle}
        loading={renameLoading}
        error={renameError}
        onConfirm={handleRenameTask}
        onCancel={() => {
          setIsRenaming(false);
          setRenameError(undefined);
        }}
      />

      {/* Message list */}
      <ScrollArea
        className='flex-1 p-4 custom-scrollarea'
        style={{ paddingBottom: taskPlanHeight + 48 }}
        data-task-plan-height={taskPlanHeight}
      >
        <div className="space-y-4 px-4">
          {!currentTask?.messages || currentTask.messages.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <Bot className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>{t('chatArea.startConversation')}</p>
              <p className="text-sm mt-1">{t('chatArea.conversationHint')}</p>
            </div>
          ) : (
            currentTask?.messages?.map((message, idx) => (
              <div key={idx} className="mb-6">
                {/* User message */}
                {message.type === 'user' && (
                  <div className="flex justify-end group">
                    <div className="flex items-center space-x-2 mr-4">
                      <span className="text-xs text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity">
                        {formatTime(message.timestamp)}
                      </span>
                    </div>
                    <div className="max-w-[70%]">
                      {message.attachments && message.attachments.length > 0 && (
                        <div className="mb-2 flex gap-2">
                          {message.attachments.map((attachment, index) => (
                            <div 
                              key={index} 
                              className="flex items-start space-x-2 text-sm opacity-80 border border-gray-200 rounded-lg p-2 bg-white cursor-pointer hover:bg-gray-50 transition-colors max-w-full"
                              onClick={async () => {
                                if (attachment.fileUrl && currentTask) {
                                  try {
                                    const response = await fetch(`/api/v1/app/tasks/${currentTask?.id}/downloadFile`, {
                                      method: 'POST',
                                      headers: {
                                        'Content-Type': 'application/json',
                                      },
                                      body: JSON.stringify({
                                        fileUrl: attachment.fileUrl,
                                      }),
                                    });
                                    
                                    if (response.ok) {
                                      // Get the file name from response headers
                                      const contentDisposition = response.headers.get('Content-Disposition');
                                      let filename = attachment.filename;
                                      if (contentDisposition) {
                                        const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
                                        if (filenameMatch) {
                                          filename = filenameMatch[1];
                                        }
                                      }
                                      
                                      // Create a blob and download it
                                      const blob = await response.blob();
                                      const url = window.URL.createObjectURL(blob);
                                      const link = document.createElement('a');
                                      link.href = url;
                                      link.download = filename;
                                      document.body.appendChild(link);
                                      link.click();
                                      document.body.removeChild(link);
                                      window.URL.revokeObjectURL(url);
                                    } else {
                                      const errorData = await response.json();
                                      toast.error(errorData.message || t('chatArea.downloadFileFailed'));
                                    }
                                  } catch (error) {
                                    toast.error(t('chatArea.downloadError'));
                                  }
                                }
                              }}
                            >
                              <Paperclip className="w-4 h-4 flex-shrink-0 self-center" />
                              <span className="break-words break-all">{attachment.filename}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {message.content && <div className="whitespace-pre-wrap bg-white rounded-lg p-3 border border-gray-200">{message.content}</div>}
                      
                    </div>
                  </div>
                )}

                {/* Regular assistant message */}
                {message.type === 'assistant' && (
                  <div className="flex justify-start group">
                    <div className="max-w-[80%] p-3">
                      <div className='flex items-center mb-3'>
                        <img
                          src='/images/logo.png'
                          className='w-5 h-5'
                          style={{ verticalAlign: 'middle', marginBottom: '1px' }}
                        />
                        <span
                          className='text-sm font-[tencentSans] text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 ml-2'
                          style={{ fontFamily: 'tencentSans', letterSpacing: '0.1em' }}
                        >A.I.G</span>
                        <span className='text-xs text-gray-300 ml-2'>
                          {formatTime(message.timestamp)}
                        </span>
                      </div>
                      <div className="text-gray-900 whitespace-pre-wrap">{message.content}</div>
                    </div>
                  </div>
                )}

                {/* Task confirmation message */}
                {message.type === 'task_confirmation' && message.executionPlan && (
                  <div className='flex justify-start group'>
                    <div className='max-w-[85%] w-full'>
                      <div className='flex items-baseline mb-3'>
                        <img src='/images/logo.png' className='w-5 h-5 relative' style={{ 
                        top: '5px' }} />
                        <span
                          className='text-sm font-[tencentSans] text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 ml-2'
                          style={{ fontFamily: 'tencentSans', letterSpacing: '0.1em' }}
                        >A.I.G</span>
                        <span className='text-xs text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity ml-2'>
                          {formatTime(message.timestamp)}
                        </span>
                      </div>
                      <TaskConfirmationMessage
                        taskType={currentTask?.type}
                        executionPlan={message.executionPlan}
                        confirmationText={message.content}
                      />
                    </div>
                  </div>
                )}

                {/* Task execution timeline */}
                {message.type === 'task_execution' && (
                  <div className="flex justify-start">
                    <div className="max-w-[85%] w-full">
                      <TaskExecutionTimeline
                        steps={currentTask?.plan || []}
                        messages={currentTask?.messages || []}
                        taskTitle={currentTask?.title || ''}
                        onStepSelect={onStepSelect}
                        onToolSelect={onToolSelect}
                      />
                    </div>
                  </div>
                )}

                {/* System message */}
                {message.type === 'system' && (
                  <div className="flex justify-center">
                    <div className="max-w-[70%] bg-amber-100 text-amber-800 border border-amber-200 rounded-lg p-3 text-center">
                      <div className="flex items-center justify-center space-x-2 mb-2">
                        <Shield className="w-4 h-4" />
                        <span className="text-sm font-medium">{message.brief || t('chatArea.system')}</span>
                        <span className="text-xs text-amber-600">
                          {formatTime(message.timestamp)}
                        </span>
                      </div>
                      <div>{message.content}</div>
                    </div>
                  </div>
                )}



                {/* Result message */}
                {message.type === 'result' && (
                  <div className='flex justify-start group'>
                    <div className='max-w-[85%] w-full'>
                      <div className='flex items-baseline mb-3'>
                        <img src='/images/logo.png' className='w-5 h-5 relative' style={{ 
                        top: '5px' }} />
                        <span
                          className='text-sm font-[tencentSans] text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 ml-2'
                          style={{ fontFamily: 'tencentSans', letterSpacing: '0.1em' }}
                        >A.I.G</span>
                        <span className='text-xs text-gray-300 opacity-0 group-hover:opacity-100 transition-opacity ml-2'>
                          {formatTime(message.timestamp)}
                        </span>
                      </div>
                      <div className='text-gray-900 whitespace-pre-wrap p-6 py-2'>
                        {currentTask?.type === 'Model-Redteam-Report' ? (
                          <>{t('chatArea.taskCompleted.redteamReport')}</>
                        ) : currentTask?.type === 'Model-Jailbreak' ? (
                          <>{t('chatArea.taskCompleted.jailbreak')}</>
                        ) : currentTask?.type === 'Agent-Scan' ? (
                          <>{t('chatArea.taskCompleted.default', { riskCount: (message?.result as any)?.vulnerable_tests || message?.result?.results?.length || 0 })}</>
                        ) : (
                          (() => {
                            const riskCount = message?.result?.total !== undefined ? message?.result?.total : message?.result?.results?.length;
                            console.log('riskCount 值:', riskCount);
                            return <>{t('chatArea.taskCompleted.default', { riskCount })}</>;
                          })()
                        )}
                      </div>
                      <div 
                          className='border border-gray-200 rounded-lg py-2 px-4 mt-2 w-fit bg-white text-gray-700 ml-6 flex items-center cursor-pointer hover:bg-gray-50 transition-colors'
                          onClick={() => {
                            // Choose which result type to pass based on the task type
                            if (currentTask?.type === 'AI-Infra-Scan' && message.infraScanResult) {
                              onMcpResultSelect(message.infraScanResult);
                            } else if (currentTask?.type === 'Model-Redteam-Report' && message.redteamReportResult) {
                              onMcpResultSelect(message.redteamReportResult);
                            } else if (currentTask?.type === 'Model-Jailbreak' && message.jailbreakResult) {
                              onMcpResultSelect(message.jailbreakResult);
                            } else if (currentTask?.type === 'Agent-Scan' && message.agentScanResult) {
                              onMcpResultSelect(message.agentScanResult);
                            } else if (message.mcpResult) {
                              onMcpResultSelect(message.mcpResult);
                            }
                          }}
                        >
                          <FileText className='w-4 h-4 mr-2' />
                          {currentTask?.type === 'Model-Redteam-Report' ? t('chatArea.viewReport.redteamReport') : 
                           currentTask?.type === 'Model-Jailbreak' ? t('chatArea.viewReport.jailbreak') : 
                           currentTask?.type === 'Agent-Scan' ? t('chatArea.viewReport.agentScan') :
                           t('chatArea.viewReport.riskReport')}
                        </div>
                    </div>
                  </div>
                )}
                {/* Error message */}
                {message.type === 'error' && (
                  <div className="flex justify-center">
                    <div className="max-w-[70%] bg-red-100 text-red-800 border border-red-200 rounded-lg p-3 text-center">
                      <div className="flex items-center justify-center space-x-2 mb-2">
                        <AlertCircle className="w-4 h-4" />
                        <span className="text-sm font-medium">{t('chatArea.error')}</span>
                        <span className="text-xs text-red-600">
                          {formatTime(message.timestamp)}
                        </span>
                      </div>
                      <div>{message.content}</div>
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>
      </ScrollArea>
      <FloatingInputArea
        input={input}
        setInput={setInput}
        attachments={attachments}
        setAttachments={setAttachments}
        showMcpMenu={showMcpMenu}
        setShowMcpMenu={setShowMcpMenu}
        showButtonMcpMenu={showButtonMcpMenu}
        setShowButtonMcpMenu={setShowButtonMcpMenu}
        mcpServices={mcpServices}
        handleSend={handleSend}
        handleInputChange={handleInputChange}
        handleInputBlur={handleInputBlur}

        removeAttachment={removeAttachment}
        getServiceIcon={getServiceIcon}
        mode="bottom"
        inputRef={inputRef}
        inputAreaRef={inputAreaRef}
        taskType={currentTaskType || currentTask?.type}
        selectedModel={selectedModel}
        onModelSelect={handleModelSelect}
        selectedModels={selectedModels}
        onModelsSelect={handleModelsSelect}
        selectedEvalModel={selectedEvalModel}
        onEvalModelSelect={handleEvalModelSelect}
        onTaskTypeChange={handleTaskTypeChange}
        currentTaskId={state.currentTaskId}
        currentTask={currentTask}
        currentTaskStatus={currentTask?.status}
        httpHeaders={httpHeaders}
        onHttpHeadersChange={handleHttpHeadersChange}
        selectedMcpService={selectedMcpService}
        onMcpServiceSelect={handleMcpServiceSelect}
        onClearMcpService={clearSelectedMcpService}
        selectedEvaluations={selectedEvaluations}
        onEvaluationsSelect={handleEvaluationsSelect}
        selectedAttackMethods={selectedAttackMethods}
        onAttackMethodsSelect={setSelectedAttackMethods}
        triggerWelcomeAnimation={state.triggerWelcomeAnimation}
        maxEvaluationCount={maxEvaluationCount}
        onMaxEvaluationCountChange={setMaxEvaluationCount}
        isSending={isSending}
      />
      <HttpHeaderDialog
        open={showHttpHeaderDialog}
        headers={httpHeaders}
        onConfirm={handleHttpHeadersChange}
        onCancel={() => setShowHttpHeaderDialog(false)}
      />
      <DeleteConfirmDialog
        open={showDeleteConfirm}
        loading={deleteLoading}
        error={deleteError}
        onConfirm={handleDeleteTask}
        onCancel={() => {
          setShowDeleteConfirm(false);
          setDeleteError(undefined);
        }}
        title={t('taskDelete.confirmTitle')}
        description={t('taskDelete.confirmDescription')}
      />
      <DeleteConfirmDialog
        open={showTerminateConfirm}
        loading={terminateLoading}
        error={terminateError}
        onConfirm={handleTerminateTask}
        onCancel={() => {
          setShowTerminateConfirm(false);
          setTerminateError(undefined);
        }}
        title={t('taskTerminate.confirmTitle')}
        description={t('taskTerminate.confirmDescription')}
        confirmText={t('taskTerminate.confirm')}
        loadingText={t('taskTerminate.terminating')}
        cancelText={t('taskTerminate.cancel')}
      />
      {/* Task progress floating box above the floating input area */}
      {currentTask?.plan && currentTask?.plan.length > 0 && (
        <div
          ref={taskPlanRef}
          className="m-4"
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: '0px',
            display: 'flex',
            justifyContent: 'center',
            pointerEvents: 'none',
          }}
        >
          <div
            style={{
              width: '100%',
              background: 'white',
              borderRadius: 20,
              boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
              border: '1px solid #e5e7eb',
              padding: 12,
              pointerEvents: 'auto',
            }}
          >
            <CollapsibleTaskPlan
              steps={currentTask?.plan || []}
              taskTitle={currentTask?.title || ''}
              onExpandedChange={handleTaskPlanExpandedChange}
            />
          </div>
        </div>
      )}
    </div>
    </TooltipProvider>
  );
};

export default ChatArea;
