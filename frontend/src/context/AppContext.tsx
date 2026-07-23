import React, { createContext, useContext, useReducer, useEffect, useRef, useState } from 'react';
import { AppState, AppAction, Task, TaskType, TaskStatus, Message, ExecutionStep, SubStep, getAvailableTaskTypes } from '../types';
import { v4 as uuidv4 } from 'uuid';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { env } from '../config/env';

// Initial state
const initialState: AppState = {
  tasks: [],
  currentTaskId: null,
  isLoading: false,
  error: null,
  triggerWelcomeAnimation: false,
  clearInputTrigger: 0,
};

// Reducer function
function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case 'SET_TASKS':
      return {
        ...state,
        tasks: action.payload,
      };
    
    case 'ADD_TASK':
      const newState = {
        ...state,
        tasks: [action.payload, ...state.tasks],
        currentTaskId: action.payload.id,
      };
      return newState;
    
    case 'UPDATE_TASK':
      return {
        ...state,
        tasks: state.tasks.map(task =>
          task.id === action.payload.id
            ? { ...task, ...action.payload.updates }
            : task
        ),
      };
    
    case 'DELETE_TASK':
      return {
        ...state,
        tasks: state.tasks.filter(task => task.id !== action.payload),
        currentTaskId: state.currentTaskId === action.payload ? null : state.currentTaskId,
      };
    
    case 'SET_CURRENT_TASK':
      return {
        ...state,
        currentTaskId: action.payload,
      };
    
    case 'ADD_MESSAGE':
      return {
        ...state,
        tasks: state.tasks.map(task =>
          task.id === action.payload.taskId
            ? { ...task, messages: [...task.messages, action.payload.message] }
            : task
        ),
      };
    
    case 'UPDATE_EXECUTION_STEP':
      return {
        ...state,
        tasks: state.tasks.map(task =>
          task.id === action.payload.taskId
            ? {
                ...task,
                plan: task.plan.map(step =>
                  step.id === action.payload.stepId
                    ? { ...step, ...action.payload.updates }
                    : step
                ),
              }
            : task
        ),
      };
    
    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };
    
    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
      };
    
    case 'SET_TRIGGER_WELCOME_ANIMATION':
      return {
        ...state,
        triggerWelcomeAnimation: action.payload,
      };
    
    case 'CLEAR_INPUT_CONTENT':
      return {
        ...state,
        clearInputTrigger: action.payload,
      };
    
    default:
      return state;
  }
}

// Create context
const AppContext = createContext<{
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
  actions: {
    loadTasks: () => Promise<void>;
    loadTask: (taskId: string) => Promise<void>;
    createTask: (title: string, type: TaskType, sessionId?: string) => void;
    sendMessage: (taskId: string, content: string, attachments?: any[]) => void;
    startTask: (taskId: string) => void;
    updateTaskTitle: (taskId: string, newTitle: string) => void;
    updateTaskProgress: (taskId: string, progressData: any) => void;
    updateTaskPlan: (taskId: string, planSteps: ExecutionStep[]) => void;
    addExecutionStep: (taskId: string, newStep: ExecutionStep) => void;
    updateStepTools: (taskId: string, stepId: string, statusId: string, toolUsed: any[]) => void;
    addSubStep: (taskId: string, stepId: string, newSubStep: any) => void;
    updateActionLog: (taskId: string, stepId: string, actionId: string, actionLog: string) => void;
    updateTaskResult: (taskId: string, result: any, timestamp: number) => void;
    completeTask: (taskId: string, resultData: any) => void;
    deleteTask: (taskId: string) => void;
    setTriggerWelcomeAnimation: (trigger: boolean) => void;
    clearInputContent: () => void;
    stopTaskStatusCheck: () => void;
  };
} | null>(null);

// Provider component
export function AppProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(appReducer, initialState);
  const { t } = useTranslation();

  // Use useRef to track the latest state
  const stateRef = useRef(state);
  stateRef.current = state;



  // Use useState to manage the local state of subSteps and keep state consistent
  const [subStepsState, setSubStepsState] = useState<Map<string, any[]>>(new Map());

  // Load task data
  const loadTasks = async () => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const response = await fetch('/api/v1/app/tasks');
      const responseData = await response.json();
      
      if (responseData.status !== 0) {
        throw new Error(responseData.message || '获取任务列表失败');
      }
      let hasUnfinishedTask = false;

      // Transform API response data into the app's internal format
      const tasks: Task[] = responseData.data.tasks.map((task: any) => {
        // Do not generate a default plan; use an empty array instead
        const plan: ExecutionStep[] = [];
        const taskType = getTaskTypeFromString(task.taskType);
        const status = task.status === 'done'
          ? 'completed'
          : task.status === 'terminated'
            ? 'terminated'
            : task.status === 'error'
              ? 'error'
              : 'running';
        if (status === 'running') {
          hasUnfinishedTask = true;
        }
        
        return {
          id: task.sessionId,
          title: task.title,
          type: taskType,
          status,
          createdAt: new Date(task.createdAt),
          updatedAt: new Date(task.updatedAt),
          completedAt: task.completedAt ? new Date(task.completedAt) : undefined,
          files: task.files || [],
          plan,
          messages: [], // The API response has no messages field; initialize to an empty array
          isSubmitted: true, // Tasks loaded from the API are already submitted
        };
      });

      dispatch({ type: 'SET_TASKS', payload: tasks });

      // Check whether there are unfinished tasks to decide whether to start the timer
      if (hasUnfinishedTask) {
        startTaskStatusCheck();
      } else {
        stopTaskStatusCheck();
      }

      // Do not auto-select the first task; let the user choose manually
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: '加载任务失败' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  // Load a single task's data
  const loadTask = async (taskId: string) => {
    try {
      dispatch({ type: 'SET_LOADING', payload: true });
      const response = await fetch(`/api/v1/app/tasks/${taskId}`);
      const responseData = await response.json();
      
      if (responseData.status !== 0) {
        throw new Error(responseData.message || '获取任务详情失败');
      }
      
      const taskData = responseData.data;

      // Parse messages and assemble plan, result and messages
      let planSteps = [];
      const stepIdMap = {};
      const stepTitleMap = {};
      let result = null;
      const parsedMessages = [];
      const statusMessages: Message[] = [];
      let planUpdate = null;
      // 1. Find planUpdate
      for (const msg of taskData.messages) {
        if (msg.type === 'planUpdate' && msg.event?.tasks) {
          planUpdate = msg;
        }
        if (msg.type === 'newPlanStep') {
          stepTitleMap[msg.event.title] = msg.event.stepId;
        }
      }
      // 2. Assemble the main steps
      // Prefer using the stepId carried by the planUpdate task as the main step id
      // to keep it consistent with subsequent planStepId values; if no stepId is
      // present, fall back to a title lookup, and finally fall back to the index.
      if (planUpdate) {
        planSteps = planUpdate.event.tasks.map((task, idx) => {
          const step = {
            id: task.stepId || stepTitleMap[task.title] || `step-${idx}`,
            title: task.title,
            status: mapStatusToStepStatus(task.status),
            progress: task.progress || 0,
            startTime: task.startedAt ? new Date(task.startedAt) : undefined,
            endTime: task.completedAt ? new Date(task.completedAt) : undefined,
            details: task.details || '',
            subSteps: [],
          };
          stepIdMap[step.id] = step;
          return step;
        });
      }
      let errorMessage = {};
      // 3. Iterate over messages and categorize them into subSteps of the main step
      for (const msg of taskData.messages) {
        // toolUsed
        if (msg.type === 'toolUsed' && msg.event?.planStepId && Array.isArray(msg.event.tools)) {
          const step = stepIdMap[msg.event.planStepId];
          if (step) {
            step.subSteps.forEach(subStep => {
              if (subStep.id === msg.event.statusId) {
                // Save the existing toolUsed data in order to preserve actionLog
                const existingToolUsed = subStep.toolUsed || [];
                const existingToolMap = {};
                existingToolUsed.forEach(tool => {
                  existingToolMap[tool.toolId] = tool;
                });
                
                subStep.toolUsed = msg.event.tools.map((tool) => {
                  const toolId = tool.toolId || tool.brief || Math.random().toString();
                  const existingTool = existingToolMap[toolId];
                  
                  return {
                    id: toolId,
                    brief: tool.brief,
                    status: mapStatusToStepStatus(tool.status),
                    message: tool.message,
                    result: tool.result,
                    timestamp: msg.event.timestamp ? new Date(msg.event.timestamp * 1000) : undefined,
                    tool: tool.tool,
                    toolId: tool.toolId,
                    actionLog: existingTool ? existingTool.actionLog || '' : '', // Preserve the existing actionLog
                  };
                });
              }
            });
          }
        }
        // statusUpdate
        if (msg.type === 'statusUpdate') {
          if (msg.event?.planStepId) {
            const step = stepIdMap[msg.event.planStepId];
            if (step) {
              const subStepId = msg.event.id || Math.random().toString();
              const existingSubStepIndex = step.subSteps.findIndex(subStep => subStep.id === subStepId);
              const stepStatus = msg.event.agentStaus || msg.event.agentStatus;
              const rawTimestamp = msg.event.timestamp;
              
              const newSubStep = {
                id: subStepId,
                brief: msg.event.brief,
                description: msg.event.description || '',
                status: mapStatusToStepStatus(stepStatus),
                message: {},
                timestamp: rawTimestamp ? new Date(rawTimestamp > 1e12 ? rawTimestamp : rawTimestamp * 1000) : undefined,
                toolUsed: [],
              };
              
              if (existingSubStepIndex !== -1) {
                // Preserve the existing toolUsed data; use deep copy to avoid reference issues
                const existingToolUsed = step.subSteps[existingSubStepIndex].toolUsed;
                step.subSteps[existingSubStepIndex] = {
                  ...newSubStep,
                  toolUsed: existingToolUsed ? existingToolUsed.map(tool => ({
                    ...tool,
                    actionLog: tool.actionLog || '', // Explicitly preserve the actionLog field
                  })) : [],
                };
              } else {
                step.subSteps.push(newSubStep);
              }
            }
          } else if (msg.event?.brief || msg.event?.description) {
            const rawTimestamp = msg.event.timestamp;
            statusMessages.push({
              id: msg.event.id || uuidv4(),
              type: 'system',
              brief: msg.event.brief,
              content: msg.event.description || msg.event.brief || '',
              timestamp: rawTimestamp ? new Date(rawTimestamp > 1e12 ? rawTimestamp : rawTimestamp * 1000) : (msg.timestamp ? new Date(msg.timestamp) : new Date()),
            });
          }
        }
        // actionLog
        if (msg.type === 'actionLog' && msg.event?.planStepId) {
          const step = stepIdMap[msg.event.planStepId];
          if (step) {
            step.subSteps.forEach(subStep => {
              if (subStep.toolUsed && Array.isArray(subStep.toolUsed)) {
                subStep.toolUsed.forEach(tool => {
                  if (tool.toolId === msg.event.actionId) {
                    tool.actionLog = (tool.actionLog || '') + (msg.event.actionLog || '');
                  }
                });
              }
            });
          }
        }
        // Parse the result
        if (msg.type === 'resultUpdate' && msg.event?.result) {
          result = {
            result: msg.event.result,
            timestamp: msg.event.timestamp ? new Date(msg.event.timestamp * 1000) : undefined,
          };
        }
        // Parse errors
        if (msg.type === 'error') {
          errorMessage = {
            id: uuidv4(),
            type: 'error',
            content: msg.event.message || '未知错误',
            timestamp: msg.timestamp ? new Date(msg.timestamp) : new Date(),
          };
        }
      }
           
      // If no plan data was returned from the API, use an empty array
      if (planSteps.length === 0) {
        planSteps = [];
      }
      // Assemble the other messages
      // 1. User message
      parsedMessages.push({
        type: 'user',
        timestamp: taskData.createdAt,
        content: taskData.content,
        attachments: taskData.attachments || [],
      })
      // 2. Task confirmation message
      parsedMessages.push({
        type: 'task_confirmation',
        timestamp: taskData.createdAt,
        executionPlan: planSteps,
        content: '',
      })
      // 3. Timeline message
      parsedMessages.push({
        type: 'task_execution',
        timestamp: taskData.createdAt,
        content: '',
      })
      // 4. Result message
      // Add the result message only when the task status is done
      if (taskData.status === 'done') {
        const taskType = getTaskTypeFromString(taskData.taskType || '');
        let resultMessage: any = {
          type: 'result',
          timestamp: result.timestamp,
          result: result.result,
        };
        
        // Set the corresponding result field based on the task type
        if (taskType === 'AI-Infra-Scan') {
          resultMessage.infraScanResult = result.result;
        } else if (taskType === 'Model-Redteam-Report') {
          resultMessage.redteamReportResult = result.result;
        } else if (taskType === 'Model-Jailbreak') {
          resultMessage.jailbreakResult = result.result;
        } else if (taskType === 'Agent-Scan') {
          resultMessage.agentScanResult = result.result;
        } else {
          resultMessage.mcpResult = result.result;
        }
        
        parsedMessages.push(resultMessage);
      }
      // 5. Error message (if any)
      if (errorMessage) {
        parsedMessages.push(errorMessage);
      }
      // 6. Non-plan-step status messages (e.g. task termination)
      if (statusMessages.length > 0) {
        parsedMessages.push(...statusMessages);
      }
      // 4. Task execution message
      const task = {
        id: taskData.sessionId,
        title: taskData.title,
        type: getTaskTypeFromString(taskData.taskType || ''), // Use the actual task type returned by the API
        status: (
          taskData.status === 'done'
            ? 'completed'
            : taskData.status === 'terminated'
              ? 'terminated'
              : taskData.status === 'error'
                ? 'error'
                : 'running'
        ) as TaskStatus, // Map status
        createdAt: new Date(taskData.createdAt),
        updatedAt: new Date(taskData.createdAt), // Use createdAt when updatedAt is absent
        completedAt: taskData.status === 'done' ? new Date(taskData.createdAt) : undefined,
        attachments: taskData.attachments || [],
        plan: planSteps,
        messages: parsedMessages,
        isSubmitted: true,
      };

      dispatch({
        type: 'UPDATE_TASK',
        payload: {
          id: taskId,
          updates: task,
        },
      });
      dispatch({ type: 'SET_CURRENT_TASK', payload: taskId });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: '获取任务详情失败' });
    } finally {
      dispatch({ type: 'SET_LOADING', payload: false });
    }
  };

  // Create a new task
  const createTask = (title: string, type: TaskType, sessionId?: string) => {
    // Check whether the task already exists to avoid duplicate creation
    const existingTask = stateRef.current.tasks.find(task => task.id === sessionId);
    if (existingTask) {
      return;
    }
    
    const newTask: Task = {
      id: sessionId || uuidv4(),
      title,
      type,
      status: 'running',
      createdAt: new Date(),
      updatedAt: new Date(),
      attachments: [],
      plan: [],
      messages: [],
      isSubmitted: true,
    };
    
    // Update stateRef immediately so subsequent checks can see the new task
    stateRef.current = {
      ...stateRef.current,
      tasks: [newTask, ...stateRef.current.tasks],
      currentTaskId: newTask.id,
    };

    dispatch({ type: 'ADD_TASK', payload: newTask });

    // Start periodic status checks immediately after creating a new task
    startTaskStatusCheck();

    // Note: dispatch is asynchronous, so state.tasks here still holds the old value.
    // To get the latest value, listen for state changes in useEffect.
  };

  // Send a message
  const sendMessage = (taskId: string, content: string, attachments: any[] = []) => {
    const message: Message = {
      id: uuidv4(),
      type: 'user',
      content,
      timestamp: new Date(),
      attachments,
    };
    
    dispatch({ type: 'ADD_MESSAGE', payload: { taskId, message } });

    // If this is the first message, mark the task as submitted
    const task = stateRef.current.tasks.find(t => t.id === taskId);
    if (task && !task.isSubmitted) {
      dispatch({
        type: 'UPDATE_TASK',
        payload: {
          id: taskId,
          updates: {
            isSubmitted: true,
          },
        },
      });
    }
    
    // For an MCP service invocation, generate the task confirmation and execution plan
    if (content.includes('@')) {
      const task = stateRef.current.tasks.find(t => t.id === taskId);
      if (task) {
        // Task confirmation message
        setTimeout(() => {
          const confirmationMessage: Message = {
            id: uuidv4(),
            type: 'task_confirmation',
            content: getTaskConfirmationText(content, task.type),
            timestamp: new Date(),
            attachments: [],
            executionPlan: [], // Do not generate a default execution plan
          };

          dispatch({ type: 'ADD_MESSAGE', payload: { taskId, message: confirmationMessage } });
        }, 800);

        // Start task execution
        setTimeout(() => {
          actions.startTask(taskId);

          // Add the execution timeline message
          const executionMessage: Message = {
            id: uuidv4(),
            type: 'task_execution',
            content: '任务执行中',
            timestamp: new Date(),
            attachments: [],
          };
          
          dispatch({ type: 'ADD_MESSAGE', payload: { taskId, message: executionMessage } });
        }, 2000);
      }
    } else {
      // Regular AI reply
      /*setTimeout(() => {
        const aiResponse: Message = {
          id: uuidv4(),
          type: 'assistant',
          content: getAIResponse(content),
          timestamp: new Date(),
          attachments: [],
        };
        
        dispatch({ type: 'ADD_MESSAGE', payload: { taskId, message: aiResponse } });
      }, 1000);*/
    }
  };

  // Start task execution
  const startTask = (taskId: string) => {
    const task = stateRef.current.tasks.find(t => t.id === taskId);
    if (!task) return;

    // Update task status
    dispatch({
      type: 'UPDATE_TASK',
      payload: {
        id: taskId,
        updates: {
          status: 'running',
          updatedAt: new Date(),
          plan: [], // Do not generate a default execution plan
        },
      },
    });
  };

  // Get the corresponding TaskType from a task type string
  const getTaskTypeFromString = (taskType: string): TaskType => {
    const availableTypes = getAvailableTaskTypes();

    // Try to match by service name
    for (const type of availableTypes) {
      if (taskType.includes(type)) {
        return type;
      }
    }

    // Fallback to the first available type
    return availableTypes[0];
  };

  // Generate the task confirmation text
  const getTaskConfirmationText = (userMessage: string, taskType: TaskType): string => {
    // Return the corresponding confirmation text based on the task type
    switch (taskType) {
      case 'AI-Infra-Scan':
        return '好的，我将为您进行AI基础设施安全扫描，请稍候。';
      case 'Mcp-Scan':
        return '好的，我将为您进行MCP安全扫描，请稍候。';
      case 'Skill-Scan':
        return '好的，我将为您进行SKILL安全扫描，请稍候。';
      case 'Model-Redteam-Report':
        return '好的，我将为您进行大模型安全体检，请稍候。';
      case 'Model-Jailbreak':
        return '好的，我将为您进行大模型一键越狱测试，请稍候。';
      default:
        return '好的，我将为您执行AI安全检测任务，请稍候。';
    }
  };

  // Mock AI reply
  const getAIResponse = (userMessage: string): string => {
    return '我是AI安全检测智能体，可以帮助您进行模型安全性检测。您可以使用 @安全扫描、@越狱评测、@一键越狱 来调用相应的MCP服务。请告诉我您需要什么帮助。';
  };


  
  // Sync local state with Redux state
  useEffect(() => {
    // Sync to local state whenever Redux state updates
    state.tasks.forEach(task => {
      task.plan.forEach(step => {
        if (step.subSteps && step.subSteps.length > 0) {
          const key = `${task.id}-${step.id}`;
          setSubStepsState(prev => {
            const newState = new Map(prev);
            newState.set(key, step.subSteps);
            return newState;
          });
        }
      });
    });
  }, [state.tasks]);

  // Clean up the timer when the component unmounts
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
        checkCountRef.current = 0;
      }
    };
  }, []);

  // Manage the timer with useRef to avoid frequent creation and destruction
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const checkCountRef = useRef<number>(0);

  // Periodically check the status of unfinished tasks
  const checkUnfinishedTasks = async () => {
    const currentTasks = stateRef.current.tasks;
    const runningTasks = currentTasks.filter(task => task.status === 'running' || task.status === 'pending');

    // If there are no running tasks, stop the timer
    if (runningTasks.length === 0) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
        checkCountRef.current = 0;
      }
      return;
    }

    try {
      const response = await fetch('/api/v1/app/tasks');
      const responseData = await response.json();
      
      if (responseData.status !== 0) {
        console.warn('获取任务状态失败:', responseData.message);
        return;
      }
      
      const apiTasks = responseData.data.tasks;
      let hasStatusChange = false;

      // Only update the status and name of running tasks
      runningTasks.forEach(task => {
        const apiTask = apiTasks.find((apiTask: any) => apiTask.sessionId === task.id);
        if (apiTask) {
          const newStatus = apiTask.status === 'done'
            ? 'completed'
            : apiTask.status === 'terminated'
              ? 'terminated'
              : apiTask.status === 'error'
                ? 'error'
                : 'running';
          const newTitle = apiTask.title;

          // Only update when the status or the name has changed
          if (task.status !== newStatus || task.title !== newTitle) {
            hasStatusChange = true;

            // Record the status change for notification purposes
            const statusChangeInfo = {
              taskId: task.id,
              taskTitle: newTitle,
              oldStatus: task.status,
              newStatus: newStatus,
              timestamp: new Date(),
            };
            
            dispatch({
              type: 'UPDATE_TASK',
              payload: {
                id: task.id,
                updates: {
                  status: newStatus,
                  title: newTitle,
                  updatedAt: new Date(),
                },
              },
            });
            
            // Emit a status-change notification event
            if (typeof window !== 'undefined' && window.dispatchEvent) {
              const event = new CustomEvent('taskStatusChanged', {
                detail: statusChangeInfo,
              });
              window.dispatchEvent(event);
            }

            // Show a toast notification
            if (newStatus === 'completed') {
              toast.success(t('task.notifications.taskCompleted', { title: newTitle }), {
                description: t('task.notifications.taskCompletedDescription'),
                duration: 5000,
              });
            } else if (newStatus === 'error') {
              toast.error(t('task.notifications.taskFailed', { title: newTitle }), {
                description: t('task.notifications.taskFailedDescription'),
                duration: 5000,
              });
            } else if (newStatus === 'running' && task.status !== 'running') {
              toast.info(t('task.notifications.taskStarted', { title: newTitle }), {
                description: t('task.notifications.taskStartedDescription'),
                duration: 3000,
              });
            }
          }
        }
      });
      
      // Increment the check count
      checkCountRef.current += 1;

      // Reset the check count when a status change occurred
      if (hasStatusChange) {
        checkCountRef.current = 0;
      }

    } catch (error) {
      console.error('检查任务状态时发生错误:', error);
      // Increment the check count for error retry logic
      checkCountRef.current += 1;
    }
  };

  // Function to start the timer
  const startTaskStatusCheck = () => {
    if (!intervalRef.current) {
      // Initial check interval is 5 seconds; adjust later as needed
      const initialInterval = 5000;
      intervalRef.current = setInterval(checkUnfinishedTasks, initialInterval);
    }
  };

  // Function to stop the timer
  const stopTaskStatusCheck = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
      checkCountRef.current = 0;
    }
  };

  const actions = {
    loadTasks,
    loadTask,
    createTask,
    sendMessage,
    startTask,
    updateTaskTitle: (taskId: string, newTitle: string) => {
      dispatch({
        type: 'UPDATE_TASK',
        payload: {
          id: taskId,
          updates: {
            title: newTitle,
            updatedAt: new Date(),
          },
        },
      });
    },
    updateTaskProgress: (taskId: string, progressData: any) => {
      // Update task progress
      dispatch({
        type: 'UPDATE_TASK',
        payload: {
          id: taskId,
          updates: {
            status: progressData.status || 'running',
            updatedAt: new Date(),
          },
        },
      });
    },
    updateTaskPlan: (taskId: string, planSteps: ExecutionStep[]) => {
      // Update the task execution plan
      dispatch({
        type: 'UPDATE_TASK',
        payload: {
          id: taskId,
          updates: {
            plan: planSteps,
            updatedAt: new Date(),
          },
        },
      });
    },
    addExecutionStep: (taskId: string, newStep: ExecutionStep) => {
      // Add an execution step
      dispatch({
        type: 'UPDATE_EXECUTION_STEP',
        payload: {
          taskId,
          stepId: newStep.id,
          updates: newStep,
        },
      });
    },
    updateStepTools: (taskId: string, stepId: string, statusId: string, toolUsed: any[]) => {
      // Update the step's used tools
      const task = stateRef.current.tasks.find(t => t.id === taskId);
      if (task) {
        const updatedPlan = task.plan.map(step => {
          if (step.id === stepId) {
            const updatedSubSteps = step.subSteps?.map(subStep => {
              if (subStep.id === statusId) {
                // Preserve the existing toolUsed data, especially actionLog
                const existingToolUsed = subStep.toolUsed || [];
                const existingToolMap = {};
                existingToolUsed.forEach(tool => {
                  existingToolMap[tool.toolId] = tool;
                });

                // Merge new toolUsed data while preserving the existing actionLog
                const mergedToolUsed = toolUsed.map(newTool => {
                  const existingTool = existingToolMap[newTool.toolId];
                  if (existingTool) {
                    return {
                      ...newTool,
                      actionLog: existingTool.actionLog || newTool.actionLog || '',
                    };
                  }
                  return newTool;
                });
                
                return { ...subStep, toolUsed: mergedToolUsed };
              }
              return subStep;
            }) || [];
            return { ...step, subSteps: updatedSubSteps };
          }
          return step;
        });
        
        dispatch({
          type: 'UPDATE_TASK',
          payload: {
            id: taskId,
            updates: {
              plan: updatedPlan,
              updatedAt: new Date(),
            },
          },
        });
      }
    },
    addSubStep: (taskId: string, stepId: string, newSubStep: any) => {
      // Add a sub-step, merging sub-steps with the same id

      // Read the current subSteps from Redux state
      const task = stateRef.current.tasks.find(t => t.id === taskId);
      if (!task) {
        return;
      }
      
      const step = task.plan.find(s => s.id === stepId);
      if (!step) {
        return;
      }
      
      const currentSubSteps = step.subSteps || [];
      
      const existingSubStepIndex = currentSubSteps.findIndex(subStep => subStep.id === newSubStep.id);
      
      let updatedSubSteps;
      if (existingSubStepIndex !== -1) {
        // If a sub-step with the same id exists, merge the data and keep the existing toolUsed
        const existingSubStep = currentSubSteps[existingSubStepIndex];
        updatedSubSteps = [...currentSubSteps];
        updatedSubSteps[existingSubStepIndex] = {
          ...newSubStep,
          toolUsed: existingSubStep.toolUsed || [],
        };
      } else {
        // If no sub-step with the same id exists, simply append it
        updatedSubSteps = [...currentSubSteps, newSubStep];
      }

      // Update Redux state
      dispatch({
        type: 'UPDATE_EXECUTION_STEP',
        payload: {
          taskId,
          stepId,
          updates: {
            subSteps: updatedSubSteps,
          },
        },
      });
    },
    updateActionLog: (taskId: string, stepId: string, actionId: string, actionLog: string) => {
      // Update a tool's action log
      const task = stateRef.current.tasks.find(t => t.id === taskId);
      if (!task) return;
      
      const step = task.plan.find(s => s.id === stepId);
      if (!step || !step.subSteps) return;
      
      const updatedSubSteps = step.subSteps.map(subStep => {
        if (subStep.toolUsed && Array.isArray(subStep.toolUsed)) {
          const updatedToolUsed = subStep.toolUsed.map(tool => {
            if (tool.toolId === actionId) {
              return { ...tool, actionLog: (tool.actionLog || '') + (actionLog || '') };
            }
            return tool;
          });
          return { ...subStep, toolUsed: updatedToolUsed };
        }
        return subStep;
      });
      
      dispatch({
        type: 'UPDATE_EXECUTION_STEP',
        payload: {
          taskId,
          stepId,
          updates: {
            subSteps: updatedSubSteps,
          },
        },
      });
    },
    updateTaskResult: (taskId: string, result: any, timestamp: number) => {
      // Update the task result
      const task = stateRef.current.tasks.find(t => t.id === taskId);
      if (!task) return;

      // Handle different result formats depending on the task type
      let resultMessage: Message;

      if (task.type === 'AI-Infra-Scan') {
        // AI infrastructure scan result
        resultMessage = {
          id: uuidv4(),
          type: 'result',
          content: '',
          timestamp: timestamp ? new Date(timestamp * 1000) : new Date(),
          result: {
            total: result.total || 0,
            results: result.results || [],
          },
          infraScanResult: result,
        };
      } else if (task.type === 'Model-Redteam-Report') {
        // Model red-team evaluation result
        resultMessage = {
          id: uuidv4(),
          type: 'result',
          content: '',
          timestamp: timestamp ? new Date(timestamp * 1000) : new Date(),
          result: {
            total: 0,
            results: [],
          },
          redteamReportResult: result,
        };
      } else if (task.type === 'Model-Jailbreak') {
        // Model one-click jailbreak result
        resultMessage = {
          id: uuidv4(),
          type: 'result',
          content: '',
          timestamp: timestamp ? new Date(timestamp * 1000) : new Date(),
          result: {
            total: 0,
            results: [],
          },
          jailbreakResult: result,
        };
      } else if (task.type === 'Agent-Scan') {
        // Agent scan result
        resultMessage = {
          id: uuidv4(),
          type: 'result',
          content: '',
          timestamp: timestamp ? new Date(timestamp * 1000) : new Date(),
          result: {
            total: result.total_tests || 0,
            results: result.results || [],
          },
          agentScanResult: result,
        };
      } else {
        // MCP scan result
        resultMessage = {
          id: uuidv4(),
          type: 'result',
          content: '',
          timestamp: timestamp ? new Date(timestamp * 1000) : new Date(),
          result: {
            total: result.total || 0,
            results: result.results || [],
          },
          mcpResult: result,
        };
      }

      // Add the result message
      dispatch({ type: 'ADD_MESSAGE', payload: { taskId, message: resultMessage } });

      // Update task status
      dispatch({
        type: 'UPDATE_TASK',
        payload: {
          id: taskId,
          updates: {
            status: 'completed',
            result,
            updatedAt: timestamp ? new Date(timestamp * 1000) : new Date(),
            completedAt: timestamp ? new Date(timestamp * 1000) : new Date(),
          },
        },
      });

      // Check whether unfinished tasks remain; if not, stop the timer
      setTimeout(() => {
        const currentTasks = stateRef.current.tasks;
        const runningTasks = currentTasks.filter(task => task.status === 'running' || task.status === 'pending');
        if (runningTasks.length === 0) {
          stopTaskStatusCheck();
        }
      }, 1000);
    },
    completeTask: (taskId: string, resultData: any) => {
      // Update task status
      dispatch({
        type: 'UPDATE_TASK',
        payload: {
          id: taskId,
          updates: {
            status: 'completed',
            updatedAt: new Date(),
            completedAt: new Date(),
            result: resultData.result || null,
          },
        },
      });

      // Check whether unfinished tasks remain; if not, stop the timer
      setTimeout(() => {
        const currentTasks = stateRef.current.tasks;
        const runningTasks = currentTasks.filter(task => task.status === 'running' || task.status === 'pending');
        if (runningTasks.length === 0) {
          stopTaskStatusCheck();
        }
      }, 1000);
    },
    deleteTask: (taskId: string) => {
      // Delete a task
      dispatch({
        type: 'DELETE_TASK',
        payload: taskId,
      });
    },
    setTriggerWelcomeAnimation: (trigger: boolean) => {
      // Skip the config-item check so the animation still shows when triggered manually
      dispatch({
        type: 'SET_TRIGGER_WELCOME_ANIMATION',
        payload: trigger,
      });
    },
    clearInputContent: () => {
      dispatch({
        type: 'CLEAR_INPUT_CONTENT',
        payload: Date.now(),
      });
    },
    stopTaskStatusCheck: () => {
      stopTaskStatusCheck();
    },
  };

  return (
    <AppContext.Provider value={{ state, dispatch, actions }}>
      {children}
    </AppContext.Provider>
  );
}

// Hook
export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within AppProvider');
  }
  return context;
}

// Status mapping function
function mapStatusToStepStatus(status: string): 'todo' | 'doing' | 'done' {
  if (status === 'todo') return 'todo';
  if (status === 'doing' || status === 'running' || status === 'pending') return 'doing';
  if (status === 'done' || status === 'completed' || status === 'failed') return 'done';
  return 'todo';
}
