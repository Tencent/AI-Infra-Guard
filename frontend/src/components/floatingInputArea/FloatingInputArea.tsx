import React, { useRef, useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import Joyride, { CallBackProps, STATUS, Step } from 'react-joyride';
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import { Send, Paperclip, AtSign, X, Database, Settings, Check, BookOpen, Upload, ShieldQuestion, Clock, Star, Bot, Loader2, Sparkles, ShieldAlert, Grid, RefreshCw } from 'lucide-react';
import AttackMethodSelector from './AttackMethodSelector';
import { MCPService, EvaluationItem } from '../../types';
import { modelApi } from '../../lib/modelApi';
import { agentApi } from '../../lib/agentApi';
import { evaluationApi } from '../../lib/evaluationApi';
import { ModelItem } from '../../types/model';
import { shouldShowModelButton, shouldShowEvalModelButton } from '../../utils/taskUtils';
import { isOpenSource } from '../../config/env';
import { hasMoreFeaturesMenu, maxAttackMethods, extraMoreFeatures } from '../../config/privateModules';
import { joyrideStyles, getJoyrideLocale as getJoyrideLocaleConfig } from '../../config/joyrideConfig';
import { getTaskTypeDefaultIdentifier } from '../../config/mcpServices';
import HttpHeaderDialog from '../HttpHeaderDialog';
import SettingsDialog from '../SettingsDialog';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../ui/dialog';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../ui/dropdown-menu';
import { Input } from '../ui/input';
import { Label } from '../ui/label';

interface FloatingInputAreaProps {
  input: string;
  setInput: (value: string) => void;
  attachments: File[];
  setAttachments: React.Dispatch<React.SetStateAction<File[]>>;
  showMcpMenu: boolean;
  setShowMcpMenu: (show: boolean) => void;
  mcpServices: MCPService[];
  handleSend: () => void;
  handleInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  handleInputBlur: () => void;
  removeAttachment: (index: number) => void;
  getServiceIcon: (iconName: string) => React.ReactElement;
  mode: 'center' | 'bottom';
  inputRef?: React.RefObject<HTMLTextAreaElement>;
  inputAreaRef?: React.RefObject<HTMLDivElement>;
  showButtonMcpMenu: boolean;
  setShowButtonMcpMenu: (show: boolean) => void;
  taskType?: string;
  selectedModel?: ModelItem;
  onModelSelect?: (model: ModelItem | undefined) => void;
  selectedModels?: ModelItem[];
  onModelsSelect?: (models: ModelItem[]) => void;
  selectedEvalModel?: ModelItem;
  onEvalModelSelect?: (model: ModelItem) => void;
  onTaskTypeChange?: (taskType: string) => void;
  currentTaskId?: string | null;
  currentTaskStatus?: 'pending' | 'running' | 'completed' | 'error' | 'done' | 'terminated';
  currentTask?: any; // Add the currentTask prop
  httpHeaders?: { key: string; value: string }[];
  onHttpHeadersChange?: (headers: { key: string; value: string }[]) => void;
  selectedMcpService?: MCPService | null;
  onMcpServiceSelect?: (service: MCPService) => void;
  onClearMcpService?: () => void;
  selectedEvaluations?: EvaluationItem[];
  onEvaluationsSelect?: (evaluations: EvaluationItem[]) => void;
  selectedAgent?: string;
  onAgentSelect?: (agent: string) => void;
  selectedAttackMethods?: string[];
  onAttackMethodsSelect?: (methods: string[]) => void;
  triggerWelcomeAnimation?: boolean;
  maxEvaluationCount?: number;
  onMaxEvaluationCountChange?: (count: number) => void;
  welcomeAnimationCompleted?: boolean;
  isSending?: boolean;
}

const JOYRIDE_SCROLL_OFFSET = 120;
// Custom placeholder component
const AnimatedPlaceholder: React.FC<{ selectedMcpService?: MCPService | null }> = ({ selectedMcpService }) => {
  const { t } = useTranslation();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  
  // Default placeholderPrefix and placeholder
  const defaultPlaceholderPrefix = t('floatingInputArea.placeholder.prefix');
  const defaultPlaceholders = t('floatingInputArea.placeholder.options', { returnObjects: true });

  useEffect(() => {
    const placeholders = selectedMcpService?.placeholder || defaultPlaceholders;
    
    const interval = setInterval(() => {
      setIsAnimating(true);
      setTimeout(() => {
        setCurrentIndex(prevIndex => (prevIndex + 1) % placeholders.length);
        setIsAnimating(false);
      }, 1000); // Animation duration
    }, 3000); // Switch every 3 seconds

    return () => clearInterval(interval);
  }, [selectedMcpService?.placeholder, defaultPlaceholders]);

  const getPlaceholderText = () => {
    const placeholders = selectedMcpService?.placeholder || defaultPlaceholders;
    const currentPlaceholder = placeholders[currentIndex] || placeholders[0];
    return currentPlaceholder;
  };

  // Use the effective placeholder and prefix
  const effectivePlaceholders = selectedMcpService?.placeholder || defaultPlaceholders;
  const effectivePrefix = selectedMcpService?.placeholderPrefix || defaultPlaceholderPrefix;
  
  const prefix = effectivePrefix;

  return (
    <div
      className="absolute top-0 left-0 px-4 py-3 text-gray-500 pointer-events-none select-none w-full"
      style={{ display: 'flex', alignItems: 'center', height: '24px' }}
    >
      {prefix && (
        <span style={{ whiteSpace: 'pre' }}>{prefix}</span>
      )}
      <div
        className="overflow-hidden"
        style={{ display: 'flex', alignItems: 'center' }}
      >
        <span
          className={`transition-all duration-1000 ease-in-out ${isAnimating ? 'opacity-0 -translate-y-2' : 'opacity-100 translate-y-0'}`}
          style={{
            display: 'inline-block',
            whiteSpace: 'pre',
            marginLeft: prefix ? 0 : undefined,
          }}
        >
          {getPlaceholderText()}
        </span>
      </div>
    </div>
  );
};

const FloatingInputArea: React.FC<FloatingInputAreaProps> = ({
  input,
  setInput,
  attachments,
  setAttachments,
  showMcpMenu,
  setShowMcpMenu,
  mcpServices,
  handleSend,
  handleInputChange,
  handleInputBlur,
  removeAttachment,
  getServiceIcon,
  mode,
  inputRef,
  inputAreaRef,
  showButtonMcpMenu,
  setShowButtonMcpMenu,
  taskType,
  selectedModel,
  onModelSelect,
  selectedModels = [],
  onModelsSelect,
  selectedEvalModel,
  onEvalModelSelect,
  onTaskTypeChange,
  currentTaskId,
  currentTaskStatus,
  currentTask,
  httpHeaders = [],
  onHttpHeadersChange,
  selectedMcpService,
  onMcpServiceSelect,
  onClearMcpService,
  selectedEvaluations = [],
  onEvaluationsSelect,
  selectedAgent,
  onAgentSelect,
  selectedAttackMethods = [],
  onAttackMethodsSelect,
  triggerWelcomeAnimation = false,
  maxEvaluationCount: propMaxEvaluationCount = -1,
  onMaxEvaluationCountChange,
  welcomeAnimationCompleted = false,
  isSending = false,
}) => {
  const { t, i18n } = useTranslation();
  
  // Joyride common locale configuration
  const getJoyrideLocale = () => getJoyrideLocaleConfig(t);
  
  // Handle send button clicks and add task-type validation
  const handleSendWithValidation = () => {
    // Check whether a task type has been selected (detected via @-mentions)
    if (!taskType) {
      toast.error(t('floatingInputArea.buttons.selectTaskTypeFirst'));
      return;
    }
    handleSend();
  };
  const localInputRef = useRef<HTMLTextAreaElement>(null);
  const localInputAreaRef = useRef<HTMLDivElement>(null);
  
  const finalInputRef = inputRef || localInputRef;
  const finalInputAreaRef = inputAreaRef || localInputAreaRef;

  // State related to model selection
  const [showModelMenu, setShowModelMenu] = useState(false);
  const [models, setModels] = useState<ModelItem[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [modelMenuPosition, setModelMenuPosition] = useState<'top' | 'bottom'>('top');
  
  // State related to evalModel selection
  const [showEvalModelMenu, setShowEvalModelMenu] = useState(false);
  const [evalModelMenuPosition, setEvalModelMenuPosition] = useState<'top' | 'bottom'>('top');
  
  // State related to HTTP Header configuration
  const [showHttpHeaderDialog, setShowHttpHeaderDialog] = useState(false);
  
  // State related to the model-management dialog
  const [showModelManagementDialog, setShowModelManagementDialog] = useState(false);
  
  // State related to the plugin-management dialog
  const [showKnowledgeBaseDialog, setShowKnowledgeBaseDialog] = useState(false);

  // State related to evaluation-set selection
  const [showEvaluationMenu, setShowEvaluationMenu] = useState(false);
  const [evaluations, setEvaluations] = useState<EvaluationItem[]>([]);
  const [loadingEvaluations, setLoadingEvaluations] = useState(false);
  const [evaluationMenuPosition, setEvaluationMenuPosition] = useState<'top' | 'bottom'>('top');

  // State related to Agent selection
  const [agents, setAgents] = useState<string[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [showAgentMenu, setShowAgentMenu] = useState(false);
  const [agentMenuPosition, setAgentMenuPosition] = useState<'top' | 'bottom'>('top');
  const [showAgentManagementDialog, setShowAgentManagementDialog] = useState(false);

  // State related to the custom evaluation-set dialog
  const [showCustomEvaluationDialog, setShowCustomEvaluationDialog] = useState(false);
  
  // State related to the max evaluation total
  const maxEvaluationCount = propMaxEvaluationCount;
  const setMaxEvaluationCount = onMaxEvaluationCountChange || (() => {});
  const [customEvaluationFile, setCustomEvaluationFile] = useState<File | null>(null);
  const [promptColumn, setPromptColumn] = useState('prompt');
  const [customEvaluationFileInputRef] = useState(React.createRef<HTMLInputElement>());

  // State related to the welcome-text animation
  const [welcomeAnimationActive, setWelcomeAnimationActive] = useState(false);
  
  // State related to the onboarding tour
  const [runTour, setRunTour] = useState(false);
  // "AI Security Skill Market" NEW badge visibility: hidden once the user has clicked the button
  const [showSkillMarketBadge, setShowSkillMarketBadge] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem('hasSeenSkillMarket') !== 'true';
  });
  const dismissSkillMarketBadge = () => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('hasSeenSkillMarket', 'true');
    }
    setShowSkillMarketBadge(false);
  };
  // State related to the task-type onboarding tour
  const [runTaskTour, setRunTaskTour] = useState(false);
  // State related to the MCP security-scan onboarding tour
  const [runMcpScanTour, setRunMcpScanTour] = useState(false);
  // State related to the Skill-scan onboarding tour
  const [runSkillScanTour, setRunSkillScanTour] = useState(false);
  // State related to the AI infrastructure-scan onboarding tour
  const [runAiInfraScanTour, setRunAiInfraScanTour] = useState(false);
  // State related to the model one-click jailbreak onboarding tour
  const [runModelJailbreakTour, setRunModelJailbreakTour] = useState(false);
  // State related to the Agent-scan onboarding tour
  const [runAgentScanTour, setRunAgentScanTour] = useState(false);

  // Warning dialog state
  const [showLimitWarning, setShowLimitWarning] = useState(false);
  const [pendingSelection, setPendingSelection] = useState<{ type: 'evaluation' | 'attackMethod'; data: any } | null>(null);

  // Get the MCP service config that matches the current task type
  const getCurrentMcpService = () => {
    return mcpServices.find(service => service.id === taskType);
  };

  // Choose the default model based on the task type and the 'default' field
  const getDefaultModelForTaskType = (models: ModelItem[], taskType: string | undefined): ModelItem | null => {
    if (!taskType || models.length === 0) {
      return null;
    }
    const defaultIdentifier = getTaskTypeDefaultIdentifier(taskType);
    if (!defaultIdentifier) {
      return null;
    }
    // Find models whose 'default' field contains the current task-type identifier
    const defaultModel = models.find((model) => {
      // Skip when the 'default' field is missing
      if (model.default === undefined || model.default === null) {
        return false;
      }
      // Skip when 'default' is an empty string
      if (model.default === '') {
        return false;
      }
      // Normalize 'default' to an array
      const defaultArray = Array.isArray(model.default) ? model.default : [model.default];
      // Skip when the array is empty
      if (defaultArray.length === 0) {
        return false;
      }
      // Check whether the array contains the identifier of the current task type
      return defaultArray.includes(defaultIdentifier);
    });
    return defaultModel || null;
  };

  // Determine whether multi-select is supported
  const isMultiSelect = () => {
    const currentService = getCurrentMcpService();
    return currentService?.model === 'multi';
  };

  // AI-Infra-Scan explicitly allows choosing "no model", so it must not be overwritten by the default model backfill
  const supportsNoModelSelection = taskType === 'AI-Infra-Scan';

  // Close the button MCP menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showButtonMcpMenu) {
        const target = event.target as Element;
        const buttonContainer = target.closest('.relative.group');
        if (!buttonContainer) {
          setShowButtonMcpMenu(false);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showButtonMcpMenu, setShowButtonMcpMenu]);

  // Close the model selection menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showModelMenu) {
        const target = event.target as Element;
        const modelMenuContainer = target.closest('.model-menu-container');
        if (!modelMenuContainer) {
          setShowModelMenu(false);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showModelMenu]);

  // Close the evalModel selection menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showEvalModelMenu) {
        const target = event.target as Element;
        const evalModelMenuContainer = target.closest('.eval-model-menu-container');
        if (!evalModelMenuContainer) {
          setShowEvalModelMenu(false);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showEvalModelMenu]);

  // Close the evaluation-set selection menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showEvaluationMenu) {
        const target = event.target as Element;
        const evaluationMenuContainer = target.closest('.evaluation-menu-container');
        if (!evaluationMenuContainer) {
          setShowEvaluationMenu(false);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showEvaluationMenu]);

  // Close the Agent selection menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showAgentMenu) {
        const target = event.target as Element;
        const agentMenuContainer = target.closest('.agent-menu-container');
        if (!agentMenuContainer) {
          setShowAgentMenu(false);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showAgentMenu]);

  // Recalculate the evaluation-set menu position on window resize
  useEffect(() => {
    const handleResize = () => {
      if (showEvaluationMenu) {
        // Recompute the menu position
        const buttonElement = document.querySelector('.evaluation-menu-container button');
        if (buttonElement) {
          const buttonRect = buttonElement.getBoundingClientRect();
          const viewportHeight = window.innerHeight;
          const menuMaxHeight = Math.min(400, viewportHeight * 0.5);
          
          const spaceAbove = buttonRect.top;
          const spaceBelow = viewportHeight - buttonRect.bottom;
          
          if (spaceAbove >= menuMaxHeight && spaceAbove > spaceBelow) {
            setEvaluationMenuPosition('top');
          } else {
            setEvaluationMenuPosition('bottom');
          }
        }
      }
    };

    window.addEventListener('resize', handleResize);
    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [showEvaluationMenu]);

  // Load the model list
  const loadModels = async (forceReload = false) => {
    if (models.length > 0 && !forceReload) return; // Skip if it has already been loaded and this is not a forced reload
    
    setLoadingModels(true);
    try {
      const response = await modelApi.getModels();
      if (response.status === 0 && response.data) {
        setModels(response.data);
        
        // On forced reload, verify that the currently selected model still exists
        if (forceReload && response.data.length > 0) {
          // Check whether the single-select model still exists
          if (selectedModel && !response.data.find(m => m.model_id === selectedModel.model_id)) {
            // If the currently selected model no longer exists, prefer a model whose 'default' field contains the current task type
            if (onModelSelect && taskType) {
              const defaultModel = getDefaultModelForTaskType(response.data, taskType);
              if (defaultModel) {
                onModelSelect(defaultModel);
              } else {
                onModelSelect(response.data[0]);
              }
            } else if (onModelSelect) {
              onModelSelect(response.data[0]);
            }
          }
          
          // Check whether the multi-select models still exist
          if (isMultiSelect() && selectedModels.length > 0) {
            const validSelectedModels = selectedModels.filter(selectedModel => 
              response.data.find(m => m.model_id === selectedModel.model_id)
            );
            if (validSelectedModels.length !== selectedModels.length) {
              // If some models were deleted, update the selected model list
              if (onModelsSelect) {
                if (validSelectedModels.length > 0) {
                  onModelsSelect(validSelectedModels);
                } else {
                  // If all selected models were deleted, prefer a model whose 'default' field contains the current task type
                  if (taskType) {
                    const defaultModel = getDefaultModelForTaskType(response.data, taskType);
                    if (defaultModel) {
                      onModelsSelect([defaultModel]);
                    } else {
                      onModelsSelect([response.data[0]]);
                    }
                  } else {
                    onModelsSelect([response.data[0]]);
                  }
                }
              }
            }
          }
          
          // Check whether the evalModel still exists
          if (selectedEvalModel && !response.data.find(m => m.model_id === selectedEvalModel.model_id)) {
            // If the currently selected evalModel no longer exists, choose the first available model
            if (onEvalModelSelect && shouldShowEvalModelButton(taskType) && isOpenSource) {
              onEvalModelSelect(response.data[0]);
            }
          }
        } else {
          // Default selection logic for a normal load
          // If no model is selected and the model list is not empty, prefer a model whose 'default' field contains the current task type
          if (!supportsNoModelSelection && !selectedModel && response.data.length > 0 && onModelSelect && taskType) {
            const defaultModel = getDefaultModelForTaskType(response.data, taskType);
            if (defaultModel) {
              onModelSelect(defaultModel);
            } else {
              onModelSelect(response.data[0]);
            }
          }
          // If no multi-select models are chosen and the model list is not empty, prefer models whose 'default' field contains the current task type
          if (isMultiSelect() && selectedModels.length === 0 && response.data.length > 0 && onModelsSelect && taskType) {
            const defaultModel = getDefaultModelForTaskType(response.data, taskType);
            if (defaultModel) {
              onModelsSelect([defaultModel]);
            } else {
              onModelsSelect([response.data[0]]);
            }
          }
          // If no evalModel is selected, the model list is not empty and the evalModel button should be shown, select the first one by default
          if (!selectedEvalModel && response.data.length > 0 && onEvalModelSelect && shouldShowEvalModelButton(taskType) && isOpenSource) {
            onEvalModelSelect(response.data[0]);
          }
        }
      }
    } catch (error) {
      console.error('加载模型列表失败:', error);
    } finally {
      setLoadingModels(false);
    }
  };

  // Load the evaluation-set list
  const loadEvaluations = async (forceReload = false) => {
    if (evaluations.length > 0 && !forceReload) return; // Skip when already loaded
    
    setLoadingEvaluations(true);
    try {
      const response = await evaluationApi.getEvaluations({ size: 100000 });
      if (response.status === 0 && response.data && response.data.items) {
        setEvaluations(response.data.items);
        // When no evaluation set is selected and there is no attachment, default to sets whose official is true
        if (selectedEvaluations.length === 0 && attachments.length === 0 && response.data.items && response.data.items.length > 0 && onEvaluationsSelect) {
          const officialEvaluation = response.data.items.find(item => item.official === true);
          if (officialEvaluation) {
            onEvaluationsSelect([officialEvaluation]);
          } else {
            // If none has official=true, select the first one
            onEvaluationsSelect([response.data.items[0]]);
          }
        }
      }
    } catch (error) {
      console.error('加载评测集列表失败:', error);
    } finally {
      setLoadingEvaluations(false);
    }
  };

  // Load the Agent list
  const loadAgents = async (forceReload = false) => {
    if (agents.length > 0 && !forceReload) return;
    setLoadingAgents(true);
    try {
      const response = await agentApi.getAgentNames();
      if (response.status === 0 && response.data) {
        setAgents(response.data);
        // Select the first one by default
        if (response.data.length > 0 && !selectedAgent && onAgentSelect) {
          onAgentSelect(response.data[0]);
        }
      }
    } catch (error) {
      console.error('Failed to load agents:', error);
      toast.error(t('common.loadFailed'));
    } finally {
      setLoadingAgents(false);
    }
  };

  // Load Agents when taskType is Agent-Scan
  useEffect(() => {
    if (taskType === 'Agent-Scan') {
      loadAgents();
    }
  }, [taskType]);

  // Load the model list on component initialization
  useEffect(() => {
    loadModels();
  }, []); // Empty dependency array; runs only on mount
  

  // Load the evaluation-set list on component initialization
  useEffect(() => {
    loadEvaluations();
  }, []); // Empty dependency array; runs only on mount

  // When the evaluation-set list updates, check whether a default set needs to be selected
  useEffect(() => {
    // When no evaluation set is selected but sets are available, prefer sets whose official is true
    if (selectedEvaluations.length === 0 && evaluations.length > 0 && onEvaluationsSelect) {
      const officialEvaluation = evaluations.find(item => item.official === true);
      if (officialEvaluation) {
        onEvaluationsSelect([officialEvaluation]);
      } else {
        // If none has official=true, select the first one
        onEvaluationsSelect([evaluations[0]]);
      }
    }
  }, [evaluations, selectedEvaluations, onEvaluationsSelect]);

  // When taskType changes, check whether the default model needs to be set
  useEffect(() => {
    if (models.length > 0 && taskType) {
      // For multi-select mode without any selected model, prefer models whose 'default' contains the current task type
      if (isMultiSelect() && selectedModels.length === 0 && onModelsSelect) {
        const defaultModel = getDefaultModelForTaskType(models, taskType);
        if (defaultModel) {
          onModelsSelect([defaultModel]);
        } else {
          onModelsSelect([models[0]]);
        }
      }
      // For single-select mode without any selected model, prefer a model whose 'default' contains the current task type
      else if (!isMultiSelect() && !supportsNoModelSelection && !selectedModel && onModelSelect && taskType) {
        const defaultModel = getDefaultModelForTaskType(models, taskType);
        if (defaultModel) {
          onModelSelect(defaultModel);
        } else {
          onModelSelect(models[0]);
        }
      }
      // If the evalModel button should be shown and no evalModel is selected, select the first one by default
      if (shouldShowEvalModelButton(taskType) && isOpenSource && !selectedEvalModel && onEvalModelSelect) {
        onEvalModelSelect(models[0]);
      }
    }
  }, [taskType, models, selectedModel, selectedModels, selectedEvalModel, onModelSelect, onModelsSelect, onEvalModelSelect]);
  
  // When currentTaskId is not empty, read the user message from currentTask.messages and set it into the input
  useEffect(() => {
    if (currentTaskId && currentTask?.messages) {
      // Find the content of the first user message
      const userMessage = currentTask.messages.find(msg => msg.type === 'user');
      if (userMessage?.content) {
        setInput(userMessage.content);
      }
    }
  }, [currentTaskId, currentTask?.messages, setInput]);
  
  // Watch textarea input changes and control the evaluation-set selection (only for one-click model checkup)
  useEffect(() => {
    if (taskType === 'Model-Redteam-Report' && onEvaluationsSelect) {
      const hasInput = input.trim().length > 0;
      
      if (hasInput) {
        // Clear the evaluation-set selection when there is input content
        if (selectedEvaluations.length > 0) {
          onEvaluationsSelect([]);
        }
      } else {
        // When there is no input content, restore the default evaluation-set selection
        if (selectedEvaluations.length === 0 && evaluations.length > 0) {
          const officialEvaluation = evaluations.find(item => item.official === true);
          if (officialEvaluation) {
            onEvaluationsSelect([officialEvaluation]);
          } else {
            // If none has official=true, select the first one
            onEvaluationsSelect([evaluations[0]]);
          }
        }
      }
    }
  }, [input, taskType, selectedEvaluations, evaluations, onEvaluationsSelect]);



  // Handle model selection
  const handleModelSelect = (model: ModelItem) => {
    if (isMultiSelect()) {
      // Multi-select mode
      if (onModelsSelect) {
        const isSelected = selectedModels.some(m => m.model_id === model.model_id);
        if (isSelected) {
          // Remove if already selected
          const newSelectedModels = selectedModels.filter(m => m.model_id !== model.model_id);
          onModelsSelect(newSelectedModels);
        } else {
          // Add if not selected
          const newSelectedModels = [...selectedModels, model];
          onModelsSelect(newSelectedModels);
        }
      }
    } else {
      // Single-select mode
      if (onModelSelect) {
        onModelSelect(model);
      }
      setShowModelMenu(false);
    }
  };

  // Toggle the Agent selection menu
  const toggleAgentMenu = () => {
    if (!showAgentMenu) {
      // Compute the menu position
      const buttonElement = document.querySelector('.agent-menu-container button');
      if (buttonElement) {
        const buttonRect = buttonElement.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const menuMaxHeight = Math.min(400, viewportHeight * 0.5);
        
        const spaceAbove = buttonRect.top;
        const spaceBelow = viewportHeight - buttonRect.bottom;
        
        if (spaceAbove >= menuMaxHeight && spaceAbove > spaceBelow) {
          setAgentMenuPosition('top');
        } else {
          setAgentMenuPosition('bottom');
        }
      }
      setShowAgentMenu(true);
    } else {
      setShowAgentMenu(false);
    }
  };

  // Handle Agent selection
  const handleAgentSelect = (agent: string) => {
    if (onAgentSelect) {
      onAgentSelect(agent);
    }
    setShowAgentMenu(false);
  };

  // Toggle the model selection menu
  const toggleModelMenu = () => {
    if (!showModelMenu) {
      // Compute the menu position
      const buttonElement = document.querySelector('.model-menu-container button');
      if (buttonElement) {
        const buttonRect = buttonElement.getBoundingClientRect();
        const menuHeight = 400; // Estimate the menu height
        
        // If there is not enough space above the button, show it below
        if (buttonRect.top < menuHeight) {
          setModelMenuPosition('bottom');
        } else {
          setModelMenuPosition('top');
        }
      }
    }
    setShowModelMenu(!showModelMenu);
  };

  // Handle evalModel selection
  const handleEvalModelSelect = (model: ModelItem) => {
    if (onEvalModelSelect) {
      onEvalModelSelect(model);
    }
    setShowEvalModelMenu(false);
  };

  // Toggle the evalModel selection menu
  const toggleEvalModelMenu = () => {
    if (!showEvalModelMenu) {
      // Compute the menu position
      const buttonElement = document.querySelector('.eval-model-menu-container button');
      if (buttonElement) {
        const buttonRect = buttonElement.getBoundingClientRect();
        const menuHeight = 400; // Estimate the menu height
        
        // If there is not enough space above the button, show it below
        if (buttonRect.top < menuHeight) {
          setEvalModelMenuPosition('bottom');
        } else {
          setEvalModelMenuPosition('top');
        }
      }
    }
    setShowEvalModelMenu(!showEvalModelMenu);
  };

  // Handle warning confirmation
  const handleConfirmLimitWarning = () => {
    if (pendingSelection) {
      if (pendingSelection.type === 'evaluation') {
        const newSelectedEvaluations = pendingSelection.data as EvaluationItem[];
        onEvaluationsSelect?.(newSelectedEvaluations);
        
        // Get the newly added evaluation set (the last one)
        const addedEvaluation = newSelectedEvaluations[newSelectedEvaluations.length - 1];
        if (addedEvaluation && addedEvaluation.official === false && onAttackMethodsSelect) {
            onAttackMethodsSelect([]);
        }
      } else if (pendingSelection.type === 'attackMethod') {
        onAttackMethodsSelect?.(pendingSelection.data as string[]);
      }
    }
    setShowLimitWarning(false);
    setPendingSelection(null);
  };

  // Handle attack-method selection (with a warning)
  const handleAttackMethodsSelect = (methods: string[]) => {
    if (
      maxAttackMethods !== null &&
      methods.length > maxAttackMethods &&
      methods.length > selectedAttackMethods.length
    ) {
      setPendingSelection({ type: 'attackMethod', data: methods });
      setShowLimitWarning(true);
    } else {
      onAttackMethodsSelect?.(methods);
    }
  };

  // Handle evaluation-set selection
  const handleEvaluationSelect = (evaluation: EvaluationItem) => {
    if (onEvaluationsSelect) {
      const isSelected = selectedEvaluations.some(e => e.name === evaluation.name);
      if (isSelected) {
        // Remove if already selected
        const newSelectedEvaluations = selectedEvaluations.filter(e => e.name !== evaluation.name);
        onEvaluationsSelect(newSelectedEvaluations);
      } else {
        // Add if not selected
        const newSelectedEvaluations = [...selectedEvaluations, evaluation];
        
        // Check whether the limit is exceeded (controlled by the private overlay; maxAttackMethods=null means no limit)
        if (maxAttackMethods !== null && newSelectedEvaluations.length > maxAttackMethods) {
          setPendingSelection({ type: 'evaluation', data: newSelectedEvaluations });
          setShowLimitWarning(true);
          return;
        }

        onEvaluationsSelect(newSelectedEvaluations);
        
        // Clear attack methods when the selected evaluation set's official is false
        if (evaluation.official === false && onAttackMethodsSelect) {
          onAttackMethodsSelect([]);
        }
      }
    }
  };

  // Clear all selected evaluation sets
  const handleClearAllEvaluations = () => {
    if (onEvaluationsSelect) {
      onEvaluationsSelect([]);
    }
  };

  // Handle temporary evaluation-set upload
  const handleTemporaryEvaluationUpload = () => {
    setShowCustomEvaluationDialog(true);
    setShowEvaluationMenu(false);
  };

  // Toggle the evaluation-set selection menu
  const toggleEvaluationMenu = () => {
    if (!showEvaluationMenu) {
      // Compute the menu position
      const buttonElement = document.querySelector('.evaluation-menu-container button');
      if (buttonElement) {
        const buttonRect = buttonElement.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const menuMaxHeight = Math.min(400, viewportHeight * 0.5); // Maximum menu height, not exceeding 50% of the viewport height
        
        // Compute the available space above and below the button
        const spaceAbove = buttonRect.top;
        const spaceBelow = viewportHeight - buttonRect.bottom;
        
        // If the space above is sufficient and larger than the space below, place it above
        // Otherwise, show it below
        if (spaceAbove >= menuMaxHeight && spaceAbove > spaceBelow) {
          setEvaluationMenuPosition('top');
        } else {
          setEvaluationMenuPosition('bottom');
        }
      }
    }
    setShowEvaluationMenu(!showEvaluationMenu);
  };

  // Handle MCP service selection
  const handleMcpServiceSelect = (service: MCPService) => {
    if (onMcpServiceSelect) {
      onMcpServiceSelect(service);
    }
    if (onTaskTypeChange) {
      onTaskTypeChange(service.id);
    }
    setShowMcpMenu(false);
    setShowButtonMcpMenu(false);
    // When selecting the model security checkup, start the task tour after a delay
    if (service.id === 'Model-Redteam-Report') {
      const hasSeenJailbreakEvaluationTour = localStorage.getItem('hasSeenJailbreakEvaluationTour');
      if (!hasSeenJailbreakEvaluationTour) {
        let attemptCount = 0;
        const maxAttempts = 100;
        const checkAndStartTaskTour = () => {
          attemptCount = attemptCount + 1;
          const evalModelButton = document.querySelector('[data-joyride="eval-model-button"]');
          const evaluationTargetButton = document.querySelector('[data-joyride="evaluation-target-button"]');
          const evaluationSetButton = document.querySelector('[data-joyride="evaluation-set-button"]');
          const submitButton = document.querySelector('[data-joyride="submit-button"]');
          const hasAllButtons = evaluationTargetButton && evaluationSetButton && submitButton && (isOpenSource ? evalModelButton : true);
          if (hasAllButtons || attemptCount >= maxAttempts) {
            if (hasAllButtons) {
              setRunTaskTour(true);
            }
          } else {
            requestAnimationFrame(checkAndStartTaskTour);
          }
        };
        setTimeout(() => {
          requestAnimationFrame(checkAndStartTaskTour);
        }, 500);
      }
    }
    // When selecting MCP security scan, start the MCP-scan tour after a delay
    if (service.id === 'Mcp-Scan') {
      const hasSeenMcpScanTour = localStorage.getItem('hasSeenMcpScanTour');
      if (!hasSeenMcpScanTour) {
        let attemptCount = 0;
        const maxAttempts = 100;
        const checkAndStartMcpScanTour = () => {
          attemptCount = attemptCount + 1;
          const attachmentButton = document.querySelector('[data-joyride="mcp-scan-attachment-button"]');
          const textarea = document.querySelector('[data-joyride="mcp-scan-textarea"]');
          const modelButton = document.querySelector('[data-joyride="mcp-scan-model-button"]');
          const submitButton = document.querySelector('[data-joyride="mcp-scan-submit-button"]');
          const hasAllButtons = attachmentButton && textarea && modelButton && submitButton;
          if (hasAllButtons || attemptCount >= maxAttempts) {
            if (hasAllButtons) {
              setRunMcpScanTour(true);
            }
          } else {
            requestAnimationFrame(checkAndStartMcpScanTour);
          }
        };
        setTimeout(() => {
          requestAnimationFrame(checkAndStartMcpScanTour);
        }, 500);
      }
    }
    // When selecting Skill scan, start the Skill-scan tour after a delay
    if (service.id === 'Skill-Scan') {
      const hasSeenSkillScanTour = localStorage.getItem('hasSeenSkillScanTour');
      if (!hasSeenSkillScanTour) {
        let attemptCount = 0;
        const maxAttempts = 100;
        const checkAndStartSkillScanTour = () => {
          attemptCount = attemptCount + 1;
          const attachmentButton = document.querySelector('[data-joyride="skill-scan-attachment-button"]');
          const textarea = document.querySelector('[data-joyride="skill-scan-textarea"]');
          const modelButton = document.querySelector('[data-joyride="skill-scan-model-button"]');
          const submitButton = document.querySelector('[data-joyride="skill-scan-submit-button"]');
          const hasAllButtons = attachmentButton && textarea && modelButton && submitButton;
          if (hasAllButtons || attemptCount >= maxAttempts) {
            if (hasAllButtons) {
              setRunSkillScanTour(true);
            }
          } else {
            requestAnimationFrame(checkAndStartSkillScanTour);
          }
        };
        setTimeout(() => {
          requestAnimationFrame(checkAndStartSkillScanTour);
        }, 500);
      }
    }
    // When selecting AI infrastructure scan, start the infra-scan tour after a delay
    if (service.id === 'AI-Infra-Scan') {
      const hasSeenAiInfraScanTour = localStorage.getItem('hasSeenAiInfraScanTour');
      if (!hasSeenAiInfraScanTour) {
        let attemptCount = 0;
        const maxAttempts = 100;
        const checkAndStartAiInfraScanTour = () => {
          attemptCount = attemptCount + 1;
          const textarea = document.querySelector('[data-joyride="ai-infra-scan-textarea"]');
          const attachmentButton = document.querySelector('[data-joyride="ai-infra-scan-attachment-button"]');
          const modelButton = document.querySelector('[data-joyride="ai-infra-scan-model-button"]');
          const configButton = document.querySelector('[data-joyride="ai-infra-scan-config-button"]');
          const submitButton = document.querySelector('[data-joyride="ai-infra-scan-submit-button"]');
          const hasAllButtons = textarea && attachmentButton && modelButton && configButton && submitButton;
          if (hasAllButtons || attemptCount >= maxAttempts) {
            if (hasAllButtons) {
              setRunAiInfraScanTour(true);
            }
          } else {
            requestAnimationFrame(checkAndStartAiInfraScanTour);
          }
        };
        setTimeout(() => {
          requestAnimationFrame(checkAndStartAiInfraScanTour);
        }, 500);
      }
    }
    // When selecting one-click model jailbreak, start the jailbreak tour after a delay
    if (service.id === 'Model-Jailbreak') {
      const hasSeenModelJailbreakTour = localStorage.getItem('hasSeenModelJailbreakTour');
      if (!hasSeenModelJailbreakTour) {
        let attemptCount = 0;
        const maxAttempts = 100;
        const checkAndStartModelJailbreakTour = () => {
          attemptCount = attemptCount + 1;
          const textarea = document.querySelector('[data-joyride="model-jailbreak-textarea"]');
          const evaluationTargetButton = document.querySelector('[data-joyride="evaluation-target-button"]');
          const submitButton = document.querySelector('[data-joyride="model-jailbreak-submit-button"]');
          const hasAllButtons = textarea && evaluationTargetButton && submitButton;
          if (hasAllButtons || attemptCount >= maxAttempts) {
            if (hasAllButtons) {
              setRunModelJailbreakTour(true);
            }
          } else {
            requestAnimationFrame(checkAndStartModelJailbreakTour);
          }
        };
        setTimeout(() => {
          requestAnimationFrame(checkAndStartModelJailbreakTour);
        }, 500);
      }
    }
    // When selecting Agent scan, start the Agent-scan tour after a delay
    if (service.id === 'Agent-Scan') {
      const hasSeenAgentScanTour = localStorage.getItem('hasSeenAgentScanTour');
      if (!hasSeenAgentScanTour) {
        let attemptCount = 0;
        const maxAttempts = 100;
        const checkAndStartAgentScanTour = () => {
          attemptCount = attemptCount + 1;
          const agentButton = document.querySelector('[data-joyride="agent-select-button"]');
          const modelButton = document.querySelector('[data-joyride="agent-scan-model-button"]');
          const submitButton = document.querySelector('[data-joyride="agent-scan-submit-button"]');
          const hasAllButtons = agentButton && modelButton && submitButton;
          if (hasAllButtons || attemptCount >= maxAttempts) {
            if (hasAllButtons) {
              setRunAgentScanTour(true);
            }
          } else {
            requestAnimationFrame(checkAndStartAgentScanTour);
          }
        };
        setTimeout(() => {
          requestAnimationFrame(checkAndStartAgentScanTour);
        }, 500);
      }
    }
  };

  // Clear the selected MCP service
  const clearSelectedMcpService = () => {
    if (onClearMcpService) {
      onClearMcpService();
    }
    if (onTaskTypeChange) {
      onTaskTypeChange('');
    }
  };

  const isCenterMode = mode === 'center';
  const borderRadius = isCenterMode ? 'rounded-[40px]' : 'rounded-[20px]';
  const containerStyle = isCenterMode ? {
    height: 'calc(100vh - 160px)',
    minHeight: '400px',
    width: '100%',
    maxWidth: '1200px',
  } : {
    position: 'absolute' as const,
    bottom: 0,
    left: 0,
    right: 0,
  };

  // Decide whether the model selection button should be shown
  const shouldShowModelButtonLocal = shouldShowModelButton(taskType);
  const getModelButtonLabel = () => {
    const placeholder = taskType === 'Model-Redteam-Report'
      ? t('floatingInputArea.buttons.selectEvaluationTarget')
      : taskType === 'AI-Infra-Scan'
        ? t('floatingInputArea.buttons.selectMultimodalModel')
        : taskType === 'Agent-Scan'
        ? t('floatingInputArea.buttons.selectModel')
        : t('floatingInputArea.buttons.selectModel');
    const currentService = getCurrentMcpService();
    const template = currentService?.modelTips;
    if (isMultiSelect()) {
      if (selectedModels.length === 0) {
        return { label: placeholder, hasSelection: false };
      }
      const length = selectedModels.length;
      const baseName = selectedModels[0].model.model;
      const countText = length === 1
        ? ''
        : t(
          'floatingInputArea.evaluation.modelCount',
          {
            count: i18n.language.startsWith('zh') ? length : length - 1,
          },
        );
      const combinedName = `${baseName}${countText}`;
      const finalLabel = template
        ? template.replace('{model}', combinedName)
        : combinedName;
      return { label: finalLabel, hasSelection: true };
    }
    if (!selectedModel) {
      if (supportsNoModelSelection) {
        return { label: t('floatingInputArea.buttons.useNoModel'), hasSelection: true };
      }
      return { label: placeholder, hasSelection: false };
    }
    const modelName = selectedModel.model.model;
    const formatted = template ? template.replace('{model}', modelName) : modelName;
    return { label: formatted, hasSelection: true };
  };

  // Decide whether the evalModel selection button should be shown
  const shouldShowEvalModelButtonLocal = shouldShowEvalModelButton(taskType) && isOpenSource;
  const { label: modelButtonLabel, hasSelection: hasModelSelection } = getModelButtonLabel();

  // Decide whether the HTTP Header configuration button should be shown
  // Note: SKILL scan does not show the HTTP Header configuration button
  const shouldShowHttpHeaderButton = taskType === 'AI-Infra-Scan' || taskType === 'Mcp-Scan';

  // Decide whether the evaluation-set selection button should be shown
  const shouldShowEvaluationButton = taskType === 'Model-Redteam-Report';

  // Decide whether the add-attachment button should be shown
  const shouldShowAttachmentButton = taskType === 'AI-Infra-Scan' || taskType === 'Mcp-Scan' || taskType === 'Skill-Scan';

  const scrollJoyrideTargetIntoView = useCallback((selector?: Step['target']) => {
    if (typeof window === 'undefined' || typeof document === 'undefined') {
      return;
    }
    if (!selector || typeof selector !== 'string') {
      return;
    }
    const element = document.querySelector(selector) as HTMLElement | null;
    if (!element) {
      return;
    }
    const rect = element.getBoundingClientRect();
    const absoluteTop = rect.top + window.scrollY;
    const scrollHeight = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
    const maxScrollableTop = scrollHeight - window.innerHeight;
    const targetTop = Math.max(absoluteTop - JOYRIDE_SCROLL_OFFSET, 0);
    const finalTop = maxScrollableTop > 0 ? Math.min(targetTop, maxScrollableTop) : targetTop;
    window.scrollTo({ top: finalTop, behavior: 'smooth' });
  }, []);
  const handleJoyrideStepScroll = useCallback((data: CallBackProps) => {
    if (data.type === 'step:before') {
      scrollJoyrideTargetIntoView(data.step?.target);
    }
  }, [scrollJoyrideTargetIntoView]);
  


  // Handle HTTP Header configuration
  const handleHttpHeadersChange = (headers: { key: string; value: string }[]) => {
    if (onHttpHeadersChange) {
      onHttpHeadersChange(headers);
    }
    setShowHttpHeaderDialog(false);
  };

  // Manage the animation timer with useRef
  const animationTimers = useRef<{ start?: NodeJS.Timeout; end?: NodeJS.Timeout }>({});

  // Function that plays the welcome animation
  const playWelcomeAnimation = useCallback(() => {
    // Only play the animation in CenterMode when there is no task id
    if (!isCenterMode || currentTaskId) {
      return;
    }

    // Clear existing timers
    if (animationTimers.current.start) clearTimeout(animationTimers.current.start);
    if (animationTimers.current.end) clearTimeout(animationTimers.current.end);
    
    // Reset the state so the animation can restart
    setWelcomeAnimationActive(false);
    
    // Start a new animation sequence
    // Start the animation after a 200ms delay so page switching feels more natural
    animationTimers.current.start = setTimeout(() => {
      setWelcomeAnimationActive(true);
    }, 200);
    
    // Reset the state after the animation finishes; extend the duration to support two zoom-in-and-out cycles
    animationTimers.current.end = setTimeout(() => {
      setWelcomeAnimationActive(false);
    }, 1800); // 200ms delay + 1600ms animation duration
  }, [isCenterMode, currentTaskId]);

  // Clean up timers when the component unmounts
  useEffect(() => {
    return () => {
      if (animationTimers.current.start) clearTimeout(animationTimers.current.start);
      if (animationTimers.current.end) clearTimeout(animationTimers.current.end);
    };
  }, []);

  // Trigger the animation when entering CenterMode without a task id (e.g. page refresh or switching back from a task)
  useEffect(() => {
    if (isCenterMode && !currentTaskId) {
      playWelcomeAnimation();
    }
  }, [isCenterMode, currentTaskId, playWelcomeAnimation]);

  // Watch changes to triggerWelcomeAnimation (e.g. clicking the New Task button)
  useEffect(() => {
    if (triggerWelcomeAnimation) {
      playWelcomeAnimation();
    }
  }, [triggerWelcomeAnimation, playWelcomeAnimation]);
  // Initialize the onboarding tour
  useEffect(() => {
    if (isCenterMode && !currentTaskId && welcomeAnimationCompleted) {
      // v2: added the "AI Security Skill Market" onboarding step; existing users are re-onboarded once
      const hasSeenTour = localStorage.getItem('hasSeenTour_v2');
      if (!hasSeenTour) {
        let attemptCount = 0;
        const maxAttempts = 100; // Retry at most 100 times (~5 seconds, assuming ~50ms per attempt)
        // Use requestAnimationFrame and DOM checks to ensure the buttons have rendered
        const checkAndStartTour = () => {
          attemptCount = attemptCount + 1;
          const buttons = document.querySelectorAll('[data-joyride]');
          // Wait until all required buttons have rendered (at least 3) or the retry limit is reached
          if (buttons.length >= 3 || attemptCount >= maxAttempts) {
            if (buttons.length >= 3) {
              // All buttons have rendered; start the tour immediately
              setRunTour(true);
            }
          } else {
            // If the buttons have not finished rendering, keep waiting
            requestAnimationFrame(checkAndStartTour);
          }
        };
        // Wait a short while before checking to ensure the DOM has rendered
        setTimeout(() => {
          requestAnimationFrame(checkAndStartTour);
        }, 300);
      }
    }
  }, [isCenterMode, currentTaskId, mcpServices.length, welcomeAnimationCompleted]);
  // Configure the onboarding tour steps
  const getTourSteps = (): Step[] => {
    const steps: Step[] = [];
    // Find the corresponding service
    const modelRedteamReportService = mcpServices.find(s => s.id === 'Model-Redteam-Report');
    const agentScanService = mcpServices.find(s => s.id === 'Agent-Scan');
    const skillScanService = mcpServices.find(s => s.id === 'Skill-Scan');
    const mcpScanService = mcpServices.find(s => s.id === 'Mcp-Scan');
    const aiInfraScanService = mcpServices.find(s => s.id === 'AI-Infra-Scan');
    // Follow the left-to-right order on the page:
    // 1. AI Security Skill Market -> 2. Agent scan -> 3. Skill scan -> 4. MCP scan -> 5. Model security checkup -> 6. AI infrastructure scan
    if (agentScanService) {
      // New feature: AI Security Skill Market
      steps.push({
        target: '[data-joyride="skill-market"]',
        content: t('floatingInputArea.tour.skillMarketDescription'),
        placement: 'top',
        disableBeacon: true,
      });
      steps.push({
        target: '[data-joyride="agent-scan"]',
        content: agentScanService.description,
        placement: 'top',
        disableBeacon: true,
      });
    }
    if (skillScanService) {
      steps.push({
        target: '[data-joyride="skill-scan"]',
        content: skillScanService.description,
        placement: 'top',
        disableBeacon: true,
      });
    }
    if (mcpScanService) {
      steps.push({
        target: '[data-joyride="mcp-scan"]',
        content: mcpScanService.description,
        placement: 'top',
        disableBeacon: true,
      });
    }
    if (modelRedteamReportService) {
      steps.push({
        target: '[data-joyride="model-redteam-report"]',
        content: modelRedteamReportService.description,
        placement: 'top',
        disableBeacon: true,
      });
    }
    if (aiInfraScanService) {
      steps.push({
        target: '[data-joyride="ai-infra-scan"]',
        content: aiInfraScanService.description,
        placement: 'top',
        disableBeacon: true,
      });
    }
    // Closing CTA: guide the user to click the Agent-scan button to start
    if (agentScanService) {
      steps.push({
        target: '[data-joyride="agent-scan"]',
        content: t('floatingInputArea.tour.step4Content'),
        placement: 'top',
        disableBeacon: true,
      });
    }
    return steps;
  };
  // Handle the onboarding tour callback
  const handleJoyrideCallback = (data: CallBackProps) => {
    const { status, action } = data;
    if (action === 'close') {
      setRunTour(false);
      localStorage.setItem('hasSeenTour_v2', 'true');
      return;
    }
    handleJoyrideStepScroll(data);
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setRunTour(false);
      localStorage.setItem('hasSeenTour_v2', 'true');
    }
  };
  // Configure the task onboarding tour steps
  const getTaskTourSteps = (): Step[] => {
    const steps: Step[] = [];
    // Step 1: scoring-model button (shown only in the openSource build)
    if (isOpenSource && shouldShowEvalModelButtonLocal) {
      steps.push({
        target: '[data-joyride="eval-model-button"]',
        content: t('floatingInputArea.jailbreakEvaluationTour.evalModel'),
        placement: 'top',
        disableBeacon: true,
      });
    }
    // Step 2: evaluation-target button
    if (shouldShowModelButtonLocal) {
      steps.push({
        target: '[data-joyride="evaluation-target-button"]',
        content: t('floatingInputArea.jailbreakEvaluationTour.evaluationTarget'),
        placement: 'top',
        disableBeacon: true,
      });
    }
    // Step 3: evaluation-set button
    if (shouldShowEvaluationButton) {
      steps.push({
        target: '[data-joyride="evaluation-set-button"]',
        content: t('floatingInputArea.jailbreakEvaluationTour.evaluationSet'),
        placement: 'top',
        disableBeacon: true,
      });
    }
    // Step 4: submit button
    steps.push({
      target: '[data-joyride="submit-button"]',
      content: t('floatingInputArea.jailbreakEvaluationTour.submit'),
      placement: 'top',
      disableBeacon: true,
    });
    return steps;
  };
  // Configure the one-click model-jailbreak onboarding tour steps
  const getModelJailbreakTourSteps = (): Step[] => {
    const steps: Step[] = [];
    // Step 1: textarea
    steps.push({
      target: '[data-joyride="model-jailbreak-textarea"]',
      content: t('mcpServices.modelJailbreak.placeholderPrefix'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 2: evaluation-target button
    steps.push({
      target: '[data-joyride="evaluation-target-button"]',
      content: t('floatingInputArea.modelJailbreakTour.evaluationTarget'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 3: submit button
    steps.push({
      target: '[data-joyride="model-jailbreak-submit-button"]',
      content: t('floatingInputArea.modelJailbreakTour.submit'),
      placement: 'top',
      disableBeacon: true,
    });
    return steps;
  };
  // Handle the task onboarding tour callback
  const handleTaskJoyrideCallback = (data: CallBackProps) => {
    const { status, action } = data;
    if (action === 'close') {
      setRunTaskTour(false);
      localStorage.setItem('hasSeenJailbreakEvaluationTour', 'true');
      return;
    }
    handleJoyrideStepScroll(data);
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setRunTaskTour(false);
      localStorage.setItem('hasSeenJailbreakEvaluationTour', 'true');
    }
  };
  // Handle the one-click model-jailbreak onboarding tour callback
  const handleModelJailbreakJoyrideCallback = (data: CallBackProps) => {
    const { status, action } = data;
    if (action === 'close') {
      setRunModelJailbreakTour(false);
      localStorage.setItem('hasSeenModelJailbreakTour', 'true');
      return;
    }
    handleJoyrideStepScroll(data);
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setRunModelJailbreakTour(false);
      localStorage.setItem('hasSeenModelJailbreakTour', 'true');
    }
  };
  // Configure the MCP security-scan onboarding tour steps
  const getMcpScanTourSteps = (): Step[] => {
    const steps: Step[] = [];
    // Step 1: attachment button
    steps.push({
      target: '[data-joyride="mcp-scan-attachment-button"]',
      content: t('floatingInputArea.mcpScanTour.attachment'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 2: textarea
    steps.push({
      target: '[data-joyride="mcp-scan-textarea"]',
      content: t('floatingInputArea.mcpScanTour.textarea'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 3: model selection button
    steps.push({
      target: '[data-joyride="mcp-scan-model-button"]',
      content: t('floatingInputArea.mcpScanTour.model'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 4: submit button
    steps.push({
      target: '[data-joyride="mcp-scan-submit-button"]',
      content: t('floatingInputArea.mcpScanTour.submit'),
      placement: 'top',
      disableBeacon: true,
    });
    return steps;
  };
  // Handle the MCP security-scan onboarding tour callback
  const handleMcpScanJoyrideCallback = (data: CallBackProps) => {
    const { status, action } = data;
    if (action === 'close') {
      setRunMcpScanTour(false);
      localStorage.setItem('hasSeenMcpScanTour', 'true');
      return;
    }
    handleJoyrideStepScroll(data);
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setRunMcpScanTour(false);
      localStorage.setItem('hasSeenMcpScanTour', 'true');
    }
  };
  // Configure the Skill-scan onboarding tour steps
  const getSkillScanTourSteps = (): Step[] => {
    const steps: Step[] = [];
    // Step 1: attachment button
    steps.push({
      target: '[data-joyride="skill-scan-attachment-button"]',
      content: t('floatingInputArea.skillScanTour.attachment'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 2: textarea
    steps.push({
      target: '[data-joyride="skill-scan-textarea"]',
      content: t('floatingInputArea.skillScanTour.textarea'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 3: model selection button
    steps.push({
      target: '[data-joyride="skill-scan-model-button"]',
      content: t('floatingInputArea.skillScanTour.model'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 4: submit button
    steps.push({
      target: '[data-joyride="skill-scan-submit-button"]',
      content: t('floatingInputArea.skillScanTour.submit'),
      placement: 'top',
      disableBeacon: true,
    });
    return steps;
  };
  // Handle the Skill-scan onboarding tour callback
  const handleSkillScanJoyrideCallback = (data: CallBackProps) => {
    const { status, action } = data;
    if (action === 'close') {
      setRunSkillScanTour(false);
      localStorage.setItem('hasSeenSkillScanTour', 'true');
      return;
    }
    handleJoyrideStepScroll(data);
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setRunSkillScanTour(false);
      localStorage.setItem('hasSeenSkillScanTour', 'true');
    }
  };
  // Configure the AI infrastructure-scan onboarding tour steps
  const getAiInfraScanTourSteps = (): Step[] => {
    const steps: Step[] = [];
    // Step 1: textarea
    steps.push({
      target: '[data-joyride="ai-infra-scan-textarea"]',
      content: t('floatingInputArea.aiInfraScanTour.textarea'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 2: attachment button
    steps.push({
      target: '[data-joyride="ai-infra-scan-attachment-button"]',
      content: t('floatingInputArea.aiInfraScanTour.attachment'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 3: model selection button
    steps.push({
      target: '[data-joyride="ai-infra-scan-model-button"]',
      content: t('floatingInputArea.tooltips.aiInfraModelHint'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 4: configure button
    steps.push({
      target: '[data-joyride="ai-infra-scan-config-button"]',
      content: t('floatingInputArea.aiInfraScanTour.config'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 5: submit button
    steps.push({
      target: '[data-joyride="ai-infra-scan-submit-button"]',
      content: t('floatingInputArea.aiInfraScanTour.submit'),
      placement: 'top',
      disableBeacon: true,
    });
    return steps;
  };
  // Handle the AI infrastructure-scan onboarding tour callback
  const handleAiInfraScanJoyrideCallback = (data: CallBackProps) => {
    const { status, action } = data;
    if (action === 'close') {
      setRunAiInfraScanTour(false);
      localStorage.setItem('hasSeenAiInfraScanTour', 'true');
      return;
    }
    handleJoyrideStepScroll(data);
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setRunAiInfraScanTour(false);
      localStorage.setItem('hasSeenAiInfraScanTour', 'true');
    }
  };

  // Configure the Agent-scan onboarding tour steps
  const getAgentScanTourSteps = (): Step[] => {
    const steps: Step[] = [];
    // Step 1: select-agent button
    steps.push({
      target: '[data-joyride="agent-select-button"]',
      content: t('floatingInputArea.agentScanTour.selectAgent'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 2: model selection button
    steps.push({
      target: '[data-joyride="agent-scan-model-button"]',
      content: t('floatingInputArea.agentScanTour.selectModel'),
      placement: 'top',
      disableBeacon: true,
    });
    // Step 3: submit button
    steps.push({
      target: '[data-joyride="agent-scan-submit-button"]',
      content: t('floatingInputArea.agentScanTour.submit'),
      placement: 'top',
      disableBeacon: true,
    });
    return steps;
  };

  // Handle the Agent-scan onboarding tour callback
  const handleAgentScanJoyrideCallback = (data: CallBackProps) => {
    const { status, action } = data;
    if (action === 'close') {
      setRunAgentScanTour(false);
      localStorage.setItem('hasSeenAgentScanTour', 'true');
      return;
    }
    handleJoyrideStepScroll(data);
    if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
      setRunAgentScanTour(false);
      localStorage.setItem('hasSeenAgentScanTour', 'true');
    }
  };

  // Do not render FloatingInputArea when a task id is set
  if (currentTaskId) {
    return null;
  }

  return (
    <div
      ref={finalInputAreaRef}
      className={isCenterMode ? "p-4 backdrop-blur-sm flex flex-col items-center justify-center" : "p-4 border-gray-200 shadow-lg"}
      style={containerStyle}
    >
      {/* Onboarding tour */}
      <Joyride
        steps={getTourSteps()}
        run={runTour}
        continuous={true}
        showProgress={true}
        showSkipButton={true}
        callback={handleJoyrideCallback}
        styles={joyrideStyles}
        locale={getJoyrideLocale()}
        disableScrolling={true}
      />
      {/* Task onboarding tour - shown only for the Model-Redteam-Report task type */}
      {taskType === 'Model-Redteam-Report' && (
        <Joyride
          steps={getTaskTourSteps()}
          run={runTaskTour}
          continuous={true}
          showProgress={true}
          showSkipButton={true}
          callback={handleTaskJoyrideCallback}
          styles={joyrideStyles}
          locale={getJoyrideLocale()}
          disableScrolling={true}
        />
      )}
      {/* MCP security-scan onboarding tour - shown only for the Mcp-Scan task type */}
      {taskType === 'Mcp-Scan' && (
        <Joyride
          steps={getMcpScanTourSteps()}
          run={runMcpScanTour}
          continuous={true}
          showProgress={true}
          showSkipButton={true}
          callback={handleMcpScanJoyrideCallback}
          styles={joyrideStyles}
          locale={getJoyrideLocale()}
          disableScrolling={true}
        />
      )}
      {/* Skill-scan onboarding tour - shown only for the Skill-Scan task type */}
      {taskType === 'Skill-Scan' && (
        <Joyride
          steps={getSkillScanTourSteps()}
          run={runSkillScanTour}
          continuous={true}
          showProgress={true}
          showSkipButton={true}
          callback={handleSkillScanJoyrideCallback}
          styles={joyrideStyles}
          locale={getJoyrideLocale()}
          disableScrolling={true}
        />
      )}
      {/* AI infrastructure-scan onboarding tour - shown only for the AI-Infra-Scan task type */}
      {taskType === 'AI-Infra-Scan' && (
        <Joyride
          steps={getAiInfraScanTourSteps()}
          run={runAiInfraScanTour}
          continuous={true}
          showProgress={true}
          showSkipButton={true}
          callback={handleAiInfraScanJoyrideCallback}
          styles={joyrideStyles}
          locale={getJoyrideLocale()}
          disableScrolling={true}
        />
      )}
      {/* One-click model jailbreak onboarding tour - shown only for the Model-Jailbreak task type */}
      {taskType === 'Model-Jailbreak' && (
        <Joyride
          steps={getModelJailbreakTourSteps()}
          run={runModelJailbreakTour}
          continuous={true}
          showProgress={true}
          showSkipButton={true}
          callback={handleModelJailbreakJoyrideCallback}
          styles={joyrideStyles}
          locale={getJoyrideLocale()}
          disableScrolling={true}
        />
      )}
      {/* Agent-scan onboarding tour - shown only for the Agent-Scan task type */}
      {taskType === 'Agent-Scan' && (
        <Joyride
          steps={getAgentScanTourSteps()}
          run={runAgentScanTour}
          continuous={true}
          showProgress={true}
          showSkipButton={true}
          callback={handleAgentScanJoyrideCallback}
          styles={joyrideStyles}
          locale={getJoyrideLocale()}
          disableScrolling={true}
        />
      )}
      <div className="w-full">
        {/* Greeting */}
        {isCenterMode && !currentTaskId && (
          <div className="flex items-center justify-center text-center text-gray-500 mb-8 overflow-hidden">
            <h3 className='text-lg font-medium'>{t('floatingInputArea.welcome.greeting')}
              <span
                className='mx-1 font-[tencentSans] text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600 pl-1'
                style={{ fontFamily: 'tencentSans', letterSpacing: '0.1em' }}
              >A.I.G</span>
              {t('floatingInputArea.welcome.assistant')}
            </h3>
          </div>
        )}
        <div className={`relative flex-1 border border-gray-200 text-gray-900 placeholder-gray-500 py-4 pb-20 ${borderRadius} bg-white w-full ${isCenterMode ? 'max-w-[1200px] mx-auto' : ''} ${welcomeAnimationActive ? 'animate-pulse-twice' : ''}`} style={{boxShadow: 'rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.06) 0px 2px 5px 0px, rgba(0, 0, 0, 0.01) 0px 4px 4px 0px',}}>
          
          <div className='flex'>
            {/* MCP service label */}
            {selectedMcpService && (
              <div className="mb-3 flex items-center px-4">
                <div className="flex items-center bg-gray-100 rounded-[8px] px-1 py-1 text-sm">
                  <span className="text-gray-700 ml-2 font-medium">@{selectedMcpService.name}</span>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-auto p-1 ml-1"
                        onClick={clearSelectedMcpService}
                      >
                        <X className="w-3 h-3 text-gray-600" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{t('floatingInputArea.buttons.clearService')}</p>
                    </TooltipContent>
                  </Tooltip>
                </div>
              </div>
            )}
            {/* Attachment display */}
            {attachments.length > 0 && taskType !== 'Model-Redteam-Report' && (
              <div className="mb-3 flex flex-wrap gap-2">
                {attachments.map((file, index) => (
                  <div key={index} className="flex items-center bg-gray-100 rounded-[8px] px-2 py-1 text-sm">
                    <Paperclip className="w-4 h-4 mr-1" />
                    <span className="text-gray-700">{file.name}</span>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-auto p-1 ml-1"
                          onClick={() => removeAttachment(index)}
                        >
                          <X className="w-3 h-3 text-gray-600" />
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>{t('floatingInputArea.buttons.deleteAttachment')}</p>
                      </TooltipContent>
                    </Tooltip>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="relative" data-joyride={taskType === 'Mcp-Scan' ? 'mcp-scan-textarea' : taskType === 'Skill-Scan' ? 'skill-scan-textarea' : taskType === 'AI-Infra-Scan' ? 'ai-infra-scan-textarea' : taskType === 'Model-Jailbreak' ? 'model-jailbreak-textarea' : undefined}>
            <textarea
              ref={finalInputRef}
              value={input}
              onChange={handleInputChange}
              onBlur={handleInputBlur}
              onKeyDown={e => {
                if (e.key === '@') {
                  e.preventDefault();
                  setShowMcpMenu(true);
                }
              }}
              placeholder=""
              disabled={!!currentTaskId || isSending}
              className={`text-gray-900 placeholder-gray-500 border-0 shadow-none px-4 resize-none overflow-hidden hover:border-0 w-full focus:border-0 focus:shadow-none focus:ring-0 focus:outline-none ${isCenterMode ? 'rounded-[40px]' : ''} ${!!currentTaskId || isSending ? 'cursor-not-allowed bg-transparent' : ''}`}
              style={{ 
                minHeight: '48px',
                maxHeight: '120px',
                lineHeight: '1.5',
              }}
              onKeyPress={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  // For Model-Redteam-Report tasks, do not check the input content
                  // For Agent-Scan tasks with an Agent and a model selected, also skip the input-content check
                  if (
                    taskType === 'Model-Redteam-Report' ||
                    (taskType === 'Agent-Scan' && selectedAgent && (isMultiSelect() ? selectedModels.length > 0 : selectedModel)) ||
                    input.trim() ||
                    attachments.length > 0
                  ) {
                    handleSend();
                  }
                }
              }}
              rows={1}
            />
            {!input && <AnimatedPlaceholder selectedMcpService={selectedMcpService} />}
          </div>
          
          {/* Textarea MCP menu */}
          {showMcpMenu && mcpServices.length > 0 && (
            <div className='absolute top-full left-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto scrollbar-hover' style={{zIndex: 10}}>
              <div className='p-2'>
                {mcpServices.map((service) => (
                  <div
                    key={service.id}
                    className='flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600'
                    onClick={() => handleMcpServiceSelect(service)}
                  >
                    {getServiceIcon(service.icon)}
                    <span className='text-sm font-medium text-gray-600'>{service.name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className='px-4 bottom-4 flex justify-between items-center space-x-2 absolute w-full'>
            {/* Bottom-left buttons */}
            <div className='flex flex-wrap gap-2 flex-1 min-w-0'>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className='relative group'>
                    <Button
                      size='sm'
                      variant='ghost'
                      className='p-1 h-8 w-8 border rounded-[10px]'
                      onClick={() => {
                        if (!showButtonMcpMenu) {
                          // Compute the menu position
                          const buttonElement = document.querySelector('.relative.group button');
                          if (buttonElement) {
                            const buttonRect = buttonElement.getBoundingClientRect();
                            const menuHeight = 200; // Estimate the menu height
                            
                            // If there is not enough space above the button, show it below
                            if (buttonRect.top < menuHeight) {
                              // We cannot directly mutate the position state here, but CSS classes can handle it
                              const menuElement = buttonElement.parentElement?.querySelector('.absolute');
                              if (menuElement) {
                                menuElement.classList.remove('bottom-full', 'mb-2');
                                menuElement.classList.add('top-full', 'mt-2');
                              }
                            } else {
                              const menuElement = buttonElement.parentElement?.querySelector('.absolute');
                              if (menuElement) {
                                menuElement.classList.remove('top-full', 'mt-2');
                                menuElement.classList.add('bottom-full', 'mb-2');
                              }
                            }
                          }
                        }
                        setShowButtonMcpMenu(!showButtonMcpMenu);
                      }}
                    >
                      <AtSign className='w-4 h-4' />
                    </Button>
                    {/* Button MCP menu */}
                    <div className={`absolute left-0 bg-white border border-gray-200 rounded-lg shadow-lg max-h-48 overflow-y-auto min-w-[200px] transition-all duration-200 scrollbar-hover ${showButtonMcpMenu ? 'opacity-100 visible' : 'opacity-0 invisible'} bottom-full mb-2`} style={{zIndex: 20}}>
                      <div className='p-2'>
                        {mcpServices.map((service) => (
                          <div
                            key={service.id}
                            className='flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600'
                            onClick={() => handleMcpServiceSelect(service)}
                          >
                            {getServiceIcon(service.icon)}
                            <span className='text-sm font-medium text-gray-600'>{service.name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{t('floatingInputArea.buttons.callService')}</p>
                </TooltipContent>
              </Tooltip>
              
              {/* Add-attachment button - shown only for AI-Infra-Scan or Mcp-Scan task types */}
              {shouldShowAttachmentButton && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size='sm'
                      variant='ghost'
                      className='p-1 h-8 w-8 border rounded-[10px]'
                      data-joyride={taskType === 'Mcp-Scan' ? 'mcp-scan-attachment-button' : taskType === 'Skill-Scan' ? 'skill-scan-attachment-button' : taskType === 'AI-Infra-Scan' ? 'ai-infra-scan-attachment-button' : undefined}
                      disabled={isSending}
                      onClick={() => {
                        // Get the allowed file types based on taskType
                        const currentService = mcpServices.find(service => service.id === taskType);
                        const allowedTypes = currentService?.attachmentTypes || [];
                        const acceptValue = allowedTypes.join(',');
                        
                        const input = document.createElement('input');
                        input.type = 'file';
                        input.multiple = false;
                        input.accept = acceptValue;
                        input.onchange = (e) => {
                          const files = (e.target as HTMLInputElement).files;
                          if (files && files.length > 0) {
                            const file = files[0];
                            // Validate the file type
                            let valid = true;
                            if (allowedTypes.length > 0) {
                              valid = allowedTypes.some(type => {
                                if (type.startsWith('.')) {
                                  return file.name.toLowerCase().endsWith(type.toLowerCase());
                                }
                                return file.type.includes(type.replace('.', ''));
                              });
                            }
                            if (!valid) {
                              toast.error(`只允许上传以下文件类型: ${allowedTypes.join(', ')}`);
                              return;
                            }
                            setAttachments([file]);
                          }
                        };
                        input.click();
                      }}
                    >
                      <Paperclip className='w-4 h-4' />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t('floatingInputArea.buttons.addAttachment')}</p>
                  </TooltipContent>
                </Tooltip>
              )}

             {/* evalModel selection button - shown only for specific task types */}
             {shouldShowEvalModelButtonLocal && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className='relative group eval-model-menu-container'>
                      <Button
                        size='sm'
                        variant='ghost'
                        className='p-1 h-8 w-auto border rounded-[10px] gap-1'
                        onClick={toggleEvalModelMenu}
                        disabled={loadingModels || isSending}
                        data-joyride="eval-model-button"
                      >
                        <Database className='w-4 h-4' />
                        {taskType && (() => {
                          // Get the MCP service config that matches the current task type
                          const currentService = mcpServices.find(service => service.id === taskType);
                          if (currentService?.evalModelTips) {
                            if (selectedEvalModel) {
                              // Replace the {evalModel} placeholder in evalModelTips
                              const evalModelTipsText = currentService.evalModelTips.replace('{evalModel}', selectedEvalModel.model.model);
                              return (
                                <span className='text-xs text-gray-600'>
                                  {evalModelTipsText}
                                </span>
                              );
                            } else {
                              return (
                                <span className='text-xs text-red-500'>
                                  {t('floatingInputArea.evaluation.selectEvaluationTarget')}
                                </span>
                              );
                            }
                          }
                          return null;
                        })()}
                      </Button>
                      {/* evalModel selection menu */}
                      <div className={`absolute left-0 bg-white border border-gray-200 rounded-lg shadow-lg w-auto whitespace-nowrap transition-all duration-200 ${showEvalModelMenu ? 'opacity-100 visible' : 'opacity-0 invisible'} ${evalModelMenuPosition === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'}`} style={{zIndex: 30, maxHeight: '50vh'}}>
                        <div className='flex flex-col' style={{maxHeight: '50vh'}}>
                          {loadingModels ? (
                            <div className='flex items-center justify-center p-4 text-gray-500'>
                              <div className='animate-spin rounded-full h-4 w-4 border-b-2 border-gray-500'></div>
                              <span className='ml-2 text-sm'>{t('floatingInputArea.buttons.loading')}</span>
                            </div>
                          ) : (
                            <>
                              {/* Model list - scrollable area */}
                              <div className='flex-1 overflow-y-auto p-2 scrollbar-hover' style={{maxHeight: 'calc(50vh - 60px)'}}>
                                {models.length > 0 ? (
                                  models.map((model) => (
                                    <div
                                      key={model.model_id}
                                      className={`flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600 ${selectedEvalModel?.model_id === model.model_id ? 'bg-blue-50 border border-blue-200' : ''}`}
                                      onClick={() => handleEvalModelSelect(model)}
                                    >
                                      <Database className='w-4 h-4' />
                                      <span className='text-sm font-medium text-gray-600'>{model.model.model}</span>
                                    </div>
                                  ))
                                ) : (
                                  <div className='p-4 text-gray-500 text-sm text-center'>
                                    {t('floatingInputArea.buttons.noAvailableModels')}
                                  </div>
                                )}
                              </div>
                              {/* Manage-models button - pinned at the bottom */}
                              <div className='border-t border-gray-200 p-2 flex-shrink-0 flex items-center justify-between'>
                                <div
                                  className='flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600 flex-1'
                                  onClick={() => {
                                    setShowModelManagementDialog(true);
                                    setShowEvalModelMenu(false);
                                  }}
                                >
                                  <Settings className='w-4 h-4' />
                                  <span className='text-sm font-medium text-gray-600'>{t('floatingInputArea.buttons.manageModel')}</span>
                                </div>
                                <div
                                  className='flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600'
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    loadModels(true);
                                  }}
                                >
                                  <RefreshCw className={`w-4 h-4 ${loadingModels ? 'animate-spin' : ''}`} />
                                  <span className='text-sm font-medium text-gray-600'>{t('common.refresh')}</span>
                                </div>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t('floatingInputArea.buttons.selectScoringModel')}</p>
                  </TooltipContent>
                </Tooltip>
              )}

              {/* Agent selection button - shown only for the Agent-Scan task type */}
              {taskType === 'Agent-Scan' && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className='relative group agent-menu-container'>
                      <Button
                        size='sm'
                        variant='ghost'
                        className='p-1 h-8 w-auto border rounded-[10px] gap-1'
                        onClick={toggleAgentMenu}
                        disabled={loadingAgents}
                        data-joyride="agent-select-button"
                      >
                        <Bot className='w-4 h-4' />
                        <span className={`text-xs ${selectedAgent ? 'text-gray-600' : 'text-red-500'}`}>
                          {selectedAgent || t('floatingInputArea.buttons.selectAgent')}
                        </span>
                      </Button>
                      {/* Agent selection menu */}
                      <div className={`absolute left-0 bg-white border border-gray-200 rounded-lg shadow-lg w-auto whitespace-nowrap transition-all duration-200 ${showAgentMenu ? 'opacity-100 visible' : 'opacity-0 invisible'} ${agentMenuPosition === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'}`} style={{zIndex: 30, maxHeight: '50vh'}}>
                        <div className='flex flex-col' style={{maxHeight: '50vh'}}>
                          {loadingAgents ? (
                            <div className='flex items-center justify-center p-4 text-gray-500'>
                              <div className='animate-spin rounded-full h-4 w-4 border-b-2 border-gray-500'></div>
                              <span className='ml-2 text-sm'>{t('floatingInputArea.buttons.loading')}</span>
                            </div>
                          ) : (
                            <>
                              <div className='flex-1 overflow-y-auto p-2 scrollbar-hover' style={{maxHeight: 'calc(50vh - 60px)'}}>
                                {agents.length > 0 ? (
                                  agents.map((agent) => (
                                    <div
                                      key={agent}
                                      className={`flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600 ${selectedAgent === agent ? 'bg-blue-50 border border-blue-200' : ''}`}
                                      onClick={() => handleAgentSelect(agent)}
                                    >
                                      <Bot className='w-4 h-4' />
                                      <span className='text-sm font-medium text-gray-600'>{agent}</span>
                                    </div>
                                  ))
                                ) : (
                                  <div className='p-4 text-gray-500 text-sm text-center'>
                                    {t('floatingInputArea.buttons.noAgentAvailable')}
                                  </div>
                                )}
                              </div>
                              {/* Manage-Agents button - pinned at the bottom */}
                              <div className='border-t border-gray-200 p-2 flex-shrink-0 flex items-center justify-between'>
                                <div
                                  className='flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600 flex-1'
                                  onClick={() => {
                                    setShowAgentManagementDialog(true);
                                    setShowAgentMenu(false);
                                  }}
                                >
                                  <Settings className='w-4 h-4' />
                                  <span className='text-sm font-medium text-gray-600'>{t('floatingInputArea.buttons.manageAgent')}</span>
                                </div>
                                <div
                                  className='flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600'
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    loadAgents(true);
                                  }}
                                >
                                  <RefreshCw className={`w-4 h-4 ${loadingAgents ? 'animate-spin' : ''}`} />
                                  <span className='text-sm font-medium text-gray-600'>{t('common.refresh')}</span>
                                </div>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t('floatingInputArea.buttons.selectAgent')}</p>
                  </TooltipContent>
                </Tooltip>
              )}

              {/* Model selection button - shown only for specific task types */}
              {shouldShowModelButtonLocal && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className='relative group model-menu-container'>
                      <Button
                        size='sm'
                        variant='ghost'
                        className='p-1 h-8 w-auto border rounded-[10px] gap-1'
                        onClick={toggleModelMenu}
                        disabled={loadingModels || isSending}
                        data-joyride={taskType === 'Mcp-Scan' ? 'mcp-scan-model-button' : taskType === 'Skill-Scan' ? 'skill-scan-model-button' : taskType === 'Model-Redteam-Report' ? 'evaluation-target-button' : taskType === 'Model-Jailbreak' ? 'evaluation-target-button' : taskType === 'AI-Infra-Scan' ? 'ai-infra-scan-model-button' : taskType === 'Agent-Scan' ? 'agent-scan-model-button' : undefined}
                      >
                        <Database className='w-4 h-4' />
                        <span className={`text-xs ${hasModelSelection ? 'text-gray-600' : taskType === 'AI-Infra-Scan' ? 'text-gray-600' : 'text-red-500'}`}>
                          {modelButtonLabel}
                        </span>
                      </Button>
                      {/* Model selection menu */}
                      <div className={`absolute left-0 bg-white border border-gray-200 rounded-lg shadow-lg w-auto whitespace-nowrap transition-all duration-200 ${showModelMenu ? 'opacity-100 visible' : 'opacity-0 invisible'} ${modelMenuPosition === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'}`} style={{zIndex: 30, maxHeight: '50vh'}}>
                        <div className='flex flex-col' style={{maxHeight: '50vh'}}>
                          {loadingModels ? (
                            <div className='flex items-center justify-center p-4 text-gray-500'>
                              <div className='animate-spin rounded-full h-4 w-4 border-b-2 border-gray-500'></div>
                              <span className='ml-2 text-sm'>{t('floatingInputArea.buttons.loading')}</span>
                            </div>
                          ) : (
                            <>
                              {/* Model list - scrollable area */}
                              <div className='flex-1 overflow-y-auto p-2 scrollbar-hover' style={{maxHeight: 'calc(50vh - 60px)'}}>
                                {/* AI-Infra-Scan 'no model' option */}
                                {taskType === 'AI-Infra-Scan' && (
                                  <div
                                    className={`flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600 ${!selectedModel ? 'bg-blue-50 border border-blue-200' : ''}`}
                                    onClick={() => {
                                      if (onModelSelect) {
                                        onModelSelect(undefined);
                                      }
                                      setShowModelMenu(false);
                                    }}
                                  >
                                    <Database className='w-4 h-4' />
                                    <span className='text-sm font-medium text-gray-600'>{t('floatingInputArea.buttons.useNoModel')}</span>
                                  </div>
                                )}
                                {models.length > 0 ? (
                                  models.map((model) => {
                                    const isSelected = isMultiSelect() 
                                      ? selectedModels.some(m => m.model_id === model.model_id)
                                      : selectedModel?.model_id === model.model_id;
                                    
                                    return (
                                      <div
                                        key={model.model_id}
                                        className={`flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600 ${isSelected ? 'bg-blue-50 border border-blue-200' : ''}`}
                                        onClick={() => handleModelSelect(model)}
                                      >
                                        {isMultiSelect() && (
                                          <div className={`w-4 h-4 border rounded flex items-center justify-center ${isSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-300'}`}>
                                            {isSelected && <Check className='w-3 h-3 text-white' />}
                                          </div>
                                        )}
                                        <Database className='w-4 h-4' />
                                        <span className='text-sm font-medium text-gray-600'>{model.model.model}</span>
                                      </div>
                                    );
                                  })
                                ) : (
                                  <div className='p-4 text-gray-500 text-sm text-center'>
                                    {t('floatingInputArea.buttons.noAvailableModels')}
                                  </div>
                                )}
                              </div>
                              {/* AI-Infra-Scan hint */}
                              {taskType === 'AI-Infra-Scan' && (
                                <div className='border-b border-gray-200 p-2'>
                                  <p className='text-xs text-gray-400'>{t('floatingInputArea.tooltips.aiInfraModelHint')}</p>
                                </div>
                              )}
                              {/* Manage-models button - pinned at the bottom */}
                              <div className='border-t border-gray-200 p-2 flex-shrink-0 flex items-center justify-between'>
                                <div
                                  className='flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600 flex-1'
                                  onClick={() => {
                                    setShowModelManagementDialog(true);
                                    setShowModelMenu(false);
                                  }}
                                >
                                  <Settings className='w-4 h-4' />
                                  <span className='text-sm font-medium text-gray-600'>{t('floatingInputArea.buttons.manageModel')}</span>
                                </div>
                                <div
                                  className='flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600'
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    loadModels(true);
                                  }}
                                >
                                  <RefreshCw className={`w-4 h-4 ${loadingModels ? 'animate-spin' : ''}`} />
                                  <span className='text-sm font-medium text-gray-600'>{t('common.refresh')}</span>
                                </div>
                              </div>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>
                      {taskType === 'AI-Infra-Scan'
                        ? t('floatingInputArea.tooltips.aiInfraModelHint')
                        : taskType === 'Model-Redteam-Report'
                          ? t('floatingInputArea.buttons.selectEvaluationTarget')
                          : taskType === 'Agent-Scan'
                            ? t('floatingInputArea.buttons.selectModelSimple')
                            : t('floatingInputArea.buttons.selectModel')}
                    </p>
                  </TooltipContent>
                </Tooltip>
              )}

              

              {/* HTTP Header configuration button - shown only for the AI-Infra-Scan task type */}
              {shouldShowHttpHeaderButton && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size='sm'
                      variant={httpHeaders.length > 0 ? 'default' : 'ghost'}
                      className={`p-1 h-8 w-8 border rounded-[10px] ${httpHeaders.length > 0 ? 'bg-blue-600 text-white border-blue-600' : ''}`}
                      onClick={() => setShowHttpHeaderDialog(true)}
                      data-joyride="ai-infra-scan-config-button"
                    >
                      <Settings className='w-4 h-4' />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{t('floatingInputArea.buttons.configureHttpHeaders')}</p>
                  </TooltipContent>
                </Tooltip>
              )}

              {/* Evaluation-set selection button - shown only for the Model-Redteam-Report task type */}
              {shouldShowEvaluationButton && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className='relative group evaluation-menu-container'>
                      <Button
                        size='sm'
                        variant='ghost'
                        className={`p-1 h-8 w-auto border rounded-[10px] gap-1 ${input.trim().length > 0 || isSending ? 'opacity-50 cursor-not-allowed' : ''}`}
                        onClick={input.trim().length > 0 || isSending ? undefined : toggleEvaluationMenu}
                        disabled={loadingEvaluations || input.trim().length > 0 || isSending}
                        data-joyride="evaluation-set-button"
                      >
                        <BookOpen className='w-4 h-4' />
                        {(() => {
                          // Show a disabled state when the textarea has content
                          if (input.trim().length > 0) {
                            return (
                              <span className='text-xs text-gray-400'>
                                {t('floatingInputArea.buttons.evaluationDisabled')}
                              </span>
                            );
                          }
                          
                          if (selectedEvaluations.length > 0) {
                            // Only count the actually selected evaluation sets
                            const totalCount = selectedEvaluations.length;
                            
                            let showName = '';
                            if (selectedEvaluations.length > 0) {
                              showName = selectedEvaluations[0].isCustom ? selectedEvaluations[0].originalFile : selectedEvaluations[0].name;
                            }
                            
                            const evaluationNames = totalCount === 1 ? showName : `${showName}${t('floatingInputArea.evaluation.evaluationCount', { count: i18n.language === 'en' ? totalCount - 1 : totalCount })}`;
                            return (
                              <span className='text-xs text-gray-600'>
                                {`${t('floatingInputArea.evaluation.evaluationSet')} ${evaluationNames}`}
                              </span>
                            );
                          } else {
                            return (
                              <span className='text-xs text-red-500'>
                                {t('floatingInputArea.buttons.selectEvaluationSet')}
                              </span>
                            );
                          }
                        })()}
                      </Button>
                      {/* Evaluation-set selection menu */}
                      <div className={`absolute left-0 bg-white border border-gray-200 rounded-lg shadow-lg w-auto whitespace-nowrap transition-all duration-200 ${showEvaluationMenu ? 'opacity-100 visible' : 'opacity-0 invisible'} ${evaluationMenuPosition === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'}`} style={{zIndex: 30, maxHeight: '50vh'}}>
                        <div className='flex flex-col' style={{maxHeight: 'inherit'}}>
                          {/* Scrollable content area */}
                          <div className='flex-1 overflow-y-auto p-2 scrollbar-hover'>
                            {loadingEvaluations ? (
                              <div className='flex items-center justify-center p-4 text-gray-500'>
                                <div className='animate-spin rounded-full h-4 w-4 border-b-2 border-gray-500'></div>
                                <span className='ml-2 text-sm'>{t('floatingInputArea.buttons.loading')}</span>
                              </div>
                            ) : (
                              <>
                                {/* Display custom evaluation sets */}
                                {(() => {
                                  // Get all custom evaluation sets (both selected ones and those in attachments)
                                  const customEvaluations = selectedEvaluations.filter(evaluation => evaluation.isCustom);
                                  const attachmentFiles = attachments.filter(file => 
                                    !customEvaluations.some(e => e.originalFile === file.name)
                                  );
                                  
                                  // Merge and display all custom evaluation sets
                                  return [...customEvaluations, ...attachmentFiles.map(file => ({
                                    name: `custom_${file.name}`,
                                    originalFile: file.name,
                                    description: `${t('floatingInputArea.evaluation.custom')}${t('floatingInputArea.evaluation.evaluationSet')} - ${file.name}`,
                                    description_zh: `${t('floatingInputArea.evaluation.custom')}${t('floatingInputArea.evaluation.evaluationSet')} - ${file.name}`,
                                    source: [t('floatingInputArea.customEvaluation.source')],
                                    author: t('floatingInputArea.customEvaluation.author'),
                                    count: 0,
                                    tags: ['自定义'],
                                    recommendation: 3,
                                    language: i18n.language.startsWith('zh') ? 'zh' : 'en',
                                    default: false,
                                    data: [],
                                    isCustom: true,
                                    promptColumn: 'prompt'
                                  }))].map((evaluation) => {
                                    const isSelected = selectedEvaluations.some(e => e.name === evaluation.name);
                                    
                                    return (
                                      <Tooltip key={evaluation.name}>
                                        <TooltipTrigger asChild>
                                          <div
                                            className={`flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600 ${isSelected ? 'bg-blue-50 border border-blue-200' : ''}`}
                                            onClick={() => handleEvaluationSelect(evaluation)}
                                          >
                                            <div className={`w-4 h-4 border rounded flex items-center justify-center ${isSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-300'}`}>
                                              {isSelected && <Check className='w-3 h-3 text-white' />}
                                            </div>
                                            <span className='text-sm font-medium text-gray-600' title={evaluation.originalFile || evaluation.name}>
                                              {evaluation.originalFile || evaluation.name}
                                            </span>
                                            <span className='text-xs text-green-600 bg-green-50 px-1 rounded'>{t('floatingInputArea.evaluation.custom')}</span>
                                          </div>
                                        </TooltipTrigger>
                                        <TooltipContent side="right" className="max-w-xs">
                                          <p className="whitespace-normal">
                                            {i18n.language.startsWith('zh') ? evaluation.description_zh : evaluation.description}
                                            {evaluation.promptColumn && (
                                              <span className="block mt-1 text-xs text-gray-500">
                                                {t('floatingInputArea.evaluation.promptField')} {evaluation.promptColumn}
                                              </span>
                                            )}
                                          </p>
                                        </TooltipContent>
                                      </Tooltip>
                                    );
                                  });
                                })()}
                                
                                {/* Show a divider when both custom and system evaluation sets exist */}
                                {(() => {
                                  const customEvaluations = selectedEvaluations.filter(evaluation => evaluation.isCustom);
                                  const attachmentFiles = attachments.filter(file => 
                                    !customEvaluations.some(e => e.originalFile === file.name)
                                  );
                                  return (customEvaluations.length > 0 || attachmentFiles.length > 0) && evaluations.length > 0;
                                })() && (
                                  <div className='border-t border-gray-200 my-2'></div>
                                )}
                                
                                {/* Display system evaluation sets */}
                                {evaluations.length > 0 ? (
                                  evaluations.map((evaluation) => {
                                    const isSelected = selectedEvaluations.some(e => e.name === evaluation.name);
                                    
                                    return (
                                      <Tooltip key={evaluation.name}>
                                        <TooltipTrigger asChild>
                                          <div
                                            className={`flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600 ${isSelected ? 'bg-blue-50 border border-blue-200' : ''}`}
                                            onClick={() => handleEvaluationSelect(evaluation)}
                                          >
                                            <div className={`w-4 h-4 border rounded flex items-center justify-center ${isSelected ? 'bg-blue-600 border-blue-600' : 'border-gray-300'}`}>
                                              {isSelected && <Check className='w-3 h-3 text-white' />}
                                            </div>
                                            <span className='text-sm font-medium text-gray-600'>{evaluation.name}</span>
                                            {evaluation.official && (
                                              <span className='text-xs text-blue-600 bg-blue-50 px-1 rounded'>{t('floatingInputArea.evaluation.official')}</span>
                                            )}
                                            <span className='text-xs text-gray-500 bg-black text-white px-1 rounded mr-2'>{evaluation.language}</span>
                                            {/* Recommendation stars */}
                                            <span className='text-xs text-yellow-600 flex items-center gap-0.5'>
                                              {Array.from({
                                                length: evaluation.recommendation || 0,
                                              }).map((_, i) => (
                                                <Star key={i} className='inline w-3 h-3 fill-yellow-400 stroke-yellow-600' />
                                              ))}
                                            </span>
                                            <span className='text-xs text-gray-400 flex items-center'>
                                              <Clock className='w-3 h-3 inline mr-1' />
                                              {t('floatingInputArea.evaluation.approximately')}{(() => {
                                                const count = evaluation.count || 0;
                                                const estimatedSeconds = Math.max(count + 10, 30);
                                                
                                                if (estimatedSeconds < 60) {
                                                  return `1${t('floatingInputArea.evaluation.minute')}`;
                                                } else if (estimatedSeconds < 3600) {
                                                  const minutes = Math.floor(estimatedSeconds / 60);
                                                  const seconds = estimatedSeconds % 60;
                                                  const adjustedMinutes = seconds > 0 ? minutes + 1 : minutes;
                                                  return `${adjustedMinutes}${t('floatingInputArea.evaluation.minutes')}`;
                                                } else {
                                                  const hours = Math.floor(estimatedSeconds / 3600);
                                                  const minutes = Math.floor((estimatedSeconds % 3600) / 60);
                                                  const seconds = estimatedSeconds % 60;
                                                  
                                                  let result = `${hours}${t('floatingInputArea.evaluation.hours')}`;
                                                  const adjustedMinutes = seconds > 0 ? minutes + 1 : minutes;
                                                  if (adjustedMinutes > 0) {
                                                    result += `${adjustedMinutes}${t('floatingInputArea.evaluation.minutes')}`;
                                                  }
                                                  return result;
                                                }
                                              })()}
                                            </span>
                                          </div>
                                        </TooltipTrigger>
                                        <TooltipContent side="right" className="max-w-xs">
                                          <p className="whitespace-normal">{i18n.language.startsWith('zh') ? evaluation.description_zh : evaluation.description}</p>
                                        </TooltipContent>
                                      </Tooltip>
                                    );
                                  })
                                ) : selectedEvaluations.filter(evaluation => evaluation.isCustom).length === 0 ? (
                                  <div className='p-4 text-gray-500 text-sm text-center'>
                                    {t('floatingInputArea.buttons.noAvailableEvaluations')}
                                  </div>
                                ) : null}
                              </>
                            )}
                          </div>
                          {/* Pinned footer button area */}
                          <div className='p-2'>
                            {/* {selectedEvaluations.length > 0 && (
                              <div
                                className='flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600'
                                onClick={handleClearAllEvaluations}
                              >
                                <X className='w-4 h-4' />
                                <span className='text-sm font-medium text-gray-600'>{t('floatingInputArea.evaluationSet.clearAll')}</span>
                              </div>
                            )} */}
                            {/* Max evaluation total input */}
                            <div className='p-2 border-b border-gray-200 pb-4'>
                              <div className='flex items-center space-x-2'>
                                <Label className='text-sm font-medium text-gray-600 whitespace-nowrap'>{t('floatingInputArea.evaluationSet.maxEvaluationCount')}</Label>
                                <Input
                                  type='number'
                                  value={maxEvaluationCount === -1 ? '' : maxEvaluationCount}
                                  onChange={(e) => {
                                    const value = e.target.value;
                                    if (value === '') {
                                      setMaxEvaluationCount(-1);
                                    } else {
                                      const numValue = parseInt(value);
                                      if (!isNaN(numValue) && numValue >= -1) {
                                        setMaxEvaluationCount(numValue);
                                      }
                                    }
                                  }}
                                  placeholder={t('floatingInputArea.evaluationSet.maxEvaluationCountPlaceholder')}
                                  className='h-8 text-sm'
                                  min='-1'
                                />
                              </div>
                            </div>
                            <div className='flex items-center justify-between'>
                              <div
                                className='flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600 flex-1'
                                onClick={() => {
                                  setShowKnowledgeBaseDialog(true);
                                  setShowEvaluationMenu(false);
                                }}
                              >
                                <Settings className='w-4 h-4' />
                                <span className='text-sm font-medium text-gray-600'>{t('floatingInputArea.buttons.manageEvaluationSet')}</span>
                              </div>
                              <div
                                className='flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600'
                                onClick={(e) => {
                                  e.stopPropagation();
                                  loadEvaluations(true);
                                }}
                              >
                                <RefreshCw className={`w-4 h-4 ${loadingEvaluations ? 'animate-spin' : ''}`} />
                                <span className='text-sm font-medium text-gray-600'>{t('common.refresh')}</span>
                              </div>
                            </div>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <div
                                  className='flex items-center space-x-2 p-2 hover:bg-gray-100 rounded cursor-pointer text-gray-600'
                                  onClick={() => setShowCustomEvaluationDialog(true)}
                                >
                                  <Upload className='w-4 h-4' />
                                  <span className='text-sm font-medium text-gray-600'>{t('floatingInputArea.buttons.useCustomEvaluationSet')}</span>
                                </div>
                              </TooltipTrigger>
                              <TooltipContent side="right" className="max-w-xs">
                                <p>{t('floatingInputArea.buttons.uploadCustomEvaluationSet')}</p>
                                <p className="text-xs text-gray-300 mt-1">
                                  {t('floatingInputArea.evaluation.requirements')}{(() => {
                                    const currentService = mcpServices.find(service => service.id === taskType);
                                    const allowedTypes = currentService?.attachmentTypes || [];
                                    return allowedTypes.length > 0 
                                      ? `${t('floatingInputArea.evaluationSet.supportedFileTypes')} ${allowedTypes.join(', ')}`
                                      : t('floatingInputArea.evaluationSet.allFileTypes');
                                  })()}，{t('floatingInputArea.evaluation.fileSizeLimit')}
                                </p>
                              </TooltipContent>
                            </Tooltip>
                          </div>
                        </div>
                      </div>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{input.trim().length > 0 ? t('floatingInputArea.buttons.evaluationDisabledTooltip') : t('floatingInputArea.buttons.selectEvaluationSet')}</p>
                  </TooltipContent>
                </Tooltip>
              )}

              {/* Attack-method selection button - shown only for the Model-Redteam-Report task type */}
              {shouldShowEvaluationButton && (
                <AttackMethodSelector
                  selectedMethods={selectedAttackMethods}
                  onMethodsSelect={handleAttackMethodsSelect}
                  taskType={taskType}
                  selectedEvaluations={selectedEvaluations}
                />
              )}
            </div>
            {/* Bottom-right send button */}
            <div className='right-2 flex-shrink-0'>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    onClick={handleSendWithValidation}
                    disabled={
                      !!currentTaskId ||
                      isSending ||
                      (taskType === 'Agent-Scan'
                        ? !selectedAgent || (isMultiSelect() ? selectedModels.length === 0 : !selectedModel)
                        : taskType !== 'Model-Redteam-Report' && !input.trim() && attachments.length === 0)
                    }
                    className='bg-blue-600 hover:bg-blue-700 h-7 px-4'
                    size='sm'
                    data-joyride={taskType === 'Mcp-Scan' ? 'mcp-scan-submit-button' : taskType === 'Skill-Scan' ? 'skill-scan-submit-button' : taskType === 'Model-Redteam-Report' ? 'submit-button' : taskType === 'AI-Infra-Scan' ? 'ai-infra-scan-submit-button' : taskType === 'Model-Jailbreak' ? 'model-jailbreak-submit-button' : taskType === 'Agent-Scan' ? 'agent-scan-submit-button' : undefined}
                  >
                    {isSending ? <Loader2 className='w-4 h-4 animate-spin' /> : <Send className='w-4 h-4' />}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{t('floatingInputArea.buttons.sendMessage')}</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </div>
        </div>
        {currentTaskId === null && (
          <div>
            <div className='flex flex-wrap justify-center gap-4 mt-8 px-4'>
              {mcpServices.map(service => {
                // Add the data-joyride attribute to the three main buttons
                let dataJoyride = '';
                if (service.id === 'Model-Redteam-Report') {
                  dataJoyride = 'model-redteam-report';
                } else if (service.id === 'Mcp-Scan') {
                  dataJoyride = 'mcp-scan';
                } else if (service.id === 'Skill-Scan') {
                  dataJoyride = 'skill-scan';
                } else if (service.id === 'AI-Infra-Scan') {
                  dataJoyride = 'ai-infra-scan';
                } else if (service.id === 'Model-Jailbreak') {
                  dataJoyride = 'model-jailbreak';
                } else if (service.id === 'Agent-Scan') {
                  dataJoyride = 'agent-scan';
                }
                // Determine the icon color and background color based on the service type
                const getServiceColor = (serviceId: string) => {
                  switch (serviceId) {
                    case 'Model-Redteam-Report':
                      return {
                        iconColor: 'text-yellow-600',
                        bgColor: 'bg-yellow-50',
                      };
                    case 'Mcp-Scan':
                      return {
                        iconColor: 'text-green-600',
                        bgColor: 'bg-green-50',
                      };
                    case 'Skill-Scan':
                      return {
                        iconColor: 'text-teal-600',
                        bgColor: 'bg-teal-50',
                      };
                    case 'AI-Infra-Scan':
                      return {
                        iconColor: 'text-blue-600',
                        bgColor: 'bg-blue-50',
                      };
                    case 'Model-Jailbreak':
                      return {
                        iconColor: 'text-purple-600',
                        bgColor: 'bg-purple-50',
                      };
                    case 'Agent-Scan':
                      return {
                        iconColor: 'text-orange-500',
                        bgColor: 'bg-orange-50',
                      };
                    default:
                      return {
                        iconColor: 'text-gray-600',
                        bgColor: 'bg-gray-50',
                      };
                  }
                };
                const colors = getServiceColor(service.id);
                // Clone the icon and apply the color
                const originalIcon = getServiceIcon(service.icon);
                const originalClassName = originalIcon.props?.className || '';
                const coloredIcon = React.cloneElement(originalIcon, {
                  className: `w-5 h-5 ${colors.iconColor} ${originalClassName}`.trim(),
                });
                return (
                  <React.Fragment key={service.id}>
                    {service.id === 'Agent-Scan' && (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <button
                            type='button'
                            className="relative flex flex-row items-center gap-1.5 px-5 py-2 transition-all duration-150 focus:outline-none focus:ring-0 active:outline-none hover:bg-rose-50 cursor-pointer outline-none bg-white rounded-full border border-rose-100 shadow-sm"
                            data-joyride="skill-market"
                            onClick={() => {
                              dismissSkillMarketBadge();
                              window.open('https://matrix.tencent.com/skill-market', '_blank');
                            }}
                          >
                            <Sparkles className="w-4 h-4 text-rose-500" />
                            <span className="text-xs font-medium text-rose-400" style={{ fontSize: '12px' }}>{t('floatingInputArea.buttons.skillMarket')}</span>
                            {showSkillMarketBadge && (
                              <span
                                aria-label="new feature"
                                className="absolute -top-2 -right-2 flex items-center justify-center select-none pointer-events-none"
                              >
                                {/* Outer breathing glow */}
                                <span className="absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-60 animate-ping" />
                                {/* Badge body + subtle scale-breathing */}
                                <span className="relative inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-bold leading-none text-white bg-gradient-to-r from-rose-500 to-pink-500 rounded-full shadow-md animate-skill-market-breath">
                                  {t('floatingInputArea.buttons.skillMarketNewBadge')}
                                </span>
                              </span>
                            )}
                          </button>
                        </TooltipTrigger>
                        <TooltipContent>
                          <p>{t('floatingInputArea.tooltips.skillMarketDescription')}</p>
                        </TooltipContent>
                      </Tooltip>
                    )}
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          type='button'
                          className="relative flex flex-row items-center gap-1.5 px-5 py-2 transition-all duration-150 focus:outline-none focus:ring-0 active:outline-none hover:bg-gray-100 cursor-pointer outline-none bg-white rounded-full border border-gray-100 shadow-sm"
                          data-joyride={dataJoyride || undefined}
                          onClick={() => {
                            handleMcpServiceSelect(service);
                            if (finalInputRef.current) {
                              finalInputRef.current.focus();
                            }
                          }}
                        >
                          {coloredIcon}
                          <span className="text-xs font-medium text-gray-500" style={{ fontSize: '12px' }}>{service.name}</span>
                        </button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>{service.description}</p>
                      </TooltipContent>
                    </Tooltip>
                  </React.Fragment>
                );
              })}
              {hasMoreFeaturesMenu && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      type='button'
                      className="relative flex flex-row items-center gap-1.5 px-5 py-2 transition-all duration-150 focus:outline-none focus:ring-0 active:outline-none hover:bg-gray-100 cursor-pointer outline-none bg-white rounded-full border border-gray-100 shadow-sm"
                    >
                      <Grid className='w-5 h-5 text-gray-600' />
                      <span className="text-xs font-medium text-gray-500" style={{ fontSize: '12px' }}>{t('floatingInputArea.buttons.moreFeatures')}</span>
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="center" className="w-48">
                    {extraMoreFeatures.map(item => {
                      const Icon = item.icon;
                      return (
                        <DropdownMenuItem
                          key={item.href}
                          onClick={() => window.open(item.href, '_blank')}
                          className="cursor-pointer"
                        >
                          <Icon className="mr-2 h-4 w-4" />
                          <span>{t(item.labelI18nKey)}</span>
                        </DropdownMenuItem>
                      );
                    })}
                    <DropdownMenuItem onClick={() => window.open('/help', '_blank')} className="cursor-pointer">
                      <ShieldQuestion className="mr-2 h-4 w-4" />
                      <span>{t('floatingInputArea.buttons.helpDocument')}</span>
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>
        )}
        
        {/* HTTP Header configuration dialog */}
        <HttpHeaderDialog
          open={showHttpHeaderDialog}
          headers={httpHeaders}
          onConfirm={handleHttpHeadersChange}
          onCancel={() => setShowHttpHeaderDialog(false)}
        />
        
        {/* Model management dialog */}
        <SettingsDialog
          isOpen={showModelManagementDialog}
          initialTab="models"
          onClose={async () => {
            setShowModelManagementDialog(false);
            // After closing the dialog, force-reload the model list so the menu shows the latest data
            await loadModels(true);
          }}
        />
        
        {/* Agent management dialog */}
        <SettingsDialog
          isOpen={showAgentManagementDialog}
          initialTab="agents"
          onClose={async () => {
            setShowAgentManagementDialog(false);
            await loadAgents();
          }}
        />
        
        {/* Plugin management dialog */}
        <SettingsDialog
          isOpen={showKnowledgeBaseDialog}
          initialTab="plugins"
          onClose={() => setShowKnowledgeBaseDialog(false)}
        />

        {/* Custom evaluation-set dialog */}
        <Dialog open={showCustomEvaluationDialog} onOpenChange={(open) => {
          setShowCustomEvaluationDialog(open);
          if (!open) {
            // Reset the state when closing the dialog
            setCustomEvaluationFile(null);
            setPromptColumn('prompt');
          }
        }}>
          <DialogContent className='max-w-md'>
            <DialogHeader>
              <DialogTitle>{t('floatingInputArea.buttons.useCustomEvaluationSet')}</DialogTitle>
            </DialogHeader>
            <div className='space-y-4'>
              <div className='space-y-3'>
                <div className='space-y-2'>
                  <Label htmlFor="promptColumn" className='text-sm font-medium text-gray-700'>
                  {t('floatingInputArea.evaluationSet.promptFieldName')}
                  </Label>
                  <Input
                    id="promptColumn"
                    value={promptColumn}
                    onChange={(e) => setPromptColumn(e.target.value)}
                    placeholder={t('floatingInputArea.evaluationSet.promptFieldNamePlaceholder')}
                    className='w-full'
                  />
                </div>
                <div className='relative'>
                  <input
                    ref={customEvaluationFileInputRef}
                    type='file'
                    accept={(() => {
                      const currentService = mcpServices.find(service => service.id === taskType);
                      const allowedTypes = currentService?.attachmentTypes || [];
                      return allowedTypes.length > 0 ? allowedTypes.join(',') : '';
                    })()}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file && onEvaluationsSelect) {
                        setCustomEvaluationFile(file);
                        // Create the custom evaluation-set object, including promptColumn info
                        const customEvaluation = {
                          name: `custom_${Date.now()}`,
                          description: `${t('floatingInputArea.evaluation.custom')}${t('floatingInputArea.evaluation.evaluationSet')} - ${file.name}`,
                          description_zh: `${t('floatingInputArea.evaluation.custom')}${t('floatingInputArea.evaluation.evaluationSet')} - ${file.name}`,
                          source: [t('floatingInputArea.customEvaluation.source')],
                          author: t('floatingInputArea.customEvaluation.author'),
                          count: 0,
                          tags: [t('floatingInputArea.evaluation.custom')],
                          recommendation: 3,
                          language: i18n.language.startsWith('zh') ? 'zh' : 'en',
                          default: false,
                          data: [],
                          // Add custom fields to mark this as a custom evaluation set
                          isCustom: true,
                          promptColumn: promptColumn,
                          originalFile: file.name,
                        };
                        onEvaluationsSelect([customEvaluation]);
                        // Add the file to attachments
                        setAttachments([file]);
                        setShowCustomEvaluationDialog(false);
                        setCustomEvaluationFile(null);
                        setPromptColumn('prompt');
                      }
                    }}
                    className='hidden'
                  />
                  <Button
                    onClick={() => customEvaluationFileInputRef.current?.click()}
                    className='w-full gap-1'
                  >
                    <Upload className='w-4 h-4' />
                    {t('floatingInputArea.buttons.selectFile')}
                  </Button>
                </div>
              </div>
              <div className='text-xs text-gray-500'>
                <p className='mt-1'>
                  {(() => {
                    const currentService = mcpServices.find(service => service.id === taskType);
                    const allowedTypes = currentService?.attachmentTypes || [];
                    return allowedTypes.length > 0 
                      ? `${t('floatingInputArea.evaluationSet.supportedFileTypes')} ${allowedTypes.join(', ')}`
                      : t('floatingInputArea.evaluationSet.allFileTypes');
                  })()}
                </p>
                <p className='mt-2'>{t('floatingInputArea.evaluationSet.fileSizeLimit')}</p>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* High-cost warning dialog */}
        <Dialog open={showLimitWarning} onOpenChange={setShowLimitWarning}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t('floatingInputArea.limitWarning.title')}</DialogTitle>
              <DialogDescription className='py-4'>
                {t('floatingInputArea.limitWarning.content')}
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="ghost" onClick={handleConfirmLimitWarning}>
                {t('floatingInputArea.limitWarning.confirm')}
              </Button>
              <Button className="bg-black text-white hover:bg-gray-800" onClick={() => setShowLimitWarning(false)}>
                {t('floatingInputArea.limitWarning.cancel')}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
};

export default FloatingInputArea; 