// Data structure definitions
// Dynamically obtain task types from config/mcpServices.ts
import { useMcpServices } from '../config/mcpServices';

// Dynamically generated task types
export type TaskType = 'AI-Infra-Scan' | 'Mcp-Scan' | 'Skill-Scan' | 'Model-Redteam-Report' | 'Model-Jailbreak' | 'Agent-Scan';

// Get all available task types - static version
export const getAvailableTaskTypes = (): TaskType[] => {
  return ['AI-Infra-Scan', 'Mcp-Scan', 'Skill-Scan', 'Model-Redteam-Report', 'Model-Jailbreak', 'Agent-Scan'];
};

// Get the service info corresponding to a task type - must be used inside a component
export const useTaskServiceInfo = (taskType: TaskType) => {
  const mcpServices = useMcpServices();
  return mcpServices.find(service => service.id === taskType);
};

// Task status type
export type TaskStatus = 'pending' | 'running' | 'completed' | 'error' | 'done' | 'terminated';

export interface Task {
  id: string;
  title: string;
  type: TaskType;
  status: TaskStatus;
  createdAt: Date;
  updatedAt: Date;
  completedAt?: Date;
  attachments: any[]; // Task related files
  plan: ExecutionStep[];
  result?: string; // MD file path
  messages: Message[];
  isSubmitted: boolean; // Whether the task has been submitted
}

export interface SubStep {
  id: string;
  description: string;
  status: 'todo' | 'doing' |  'done';
  timestamp?: Date;
  message: any;
  tool: string;
  toolId: string;
  brief: string;
  result?: string;
  toolUsed?: any[];
}

export interface ExecutionStep {
  id: string;
  title: string;
  status: 'todo' | 'doing' | 'done';
  progress: number;
  details?: string;
  startTime?: Date;
  endTime?: Date;
  subSteps?: SubStep[];
  mcpResult?: MCPScanResult; // MCP scan result
  infraScanResult?: InfraScanResult; // AI infrastructure scan result
  redteamReportResult?: RedteamReportResult; // Model red-team evaluation result
  jailbreakResult?: JailbreakResult; // Model one-click jailbreak result
  agentScanResult?: AgentScanResult; // Agent scan result
}

export interface Message {
  id: string;
  type: 'user' | 'assistant' | 'system' | 'task_confirmation' | 'task_plan' | 'task_execution' | 'result' | 'error';
  brief?: string;
  content: string;
  timestamp: Date;
  attachments?: FileAttachment[];
  executionPlan?: ExecutionStep[];
  currentStep?: string; // ID of the currently executing step
  result?: {
    total: number;
    results: any[];
  };
  mcpResult?: MCPScanResult; // MCP scan result
  infraScanResult?: InfraScanResult; // AI infrastructure scan result
  redteamReportResult?: RedteamReportResult; // Model red-team evaluation result
  jailbreakResult?: JailbreakResult; // Model one-click jailbreak result
  agentScanResult?: AgentScanResult; // Agent scan result
}

export interface FileAttachment {
  filename: string;
  fileUrl: string;
}

export interface MCPService {
  id: string;
  name: string;
  description: string;
  triggerWord: string;
  icon: string;
  placeholderPrefix?: string;
  placeholder?: string[] | any;
  attachmentTypes?: string[];
  model?: string;
  modelTips?: string;
  evalModel?: string;
  evalModelTips?: string;
  needPlugin?: boolean;
}

export interface AppState {
  tasks: Task[];
  currentTaskId: string | null;
  isLoading: boolean;
  error: string | null;
  triggerWelcomeAnimation: boolean;
  clearInputTrigger: number;
}

export type AppAction = 
  | { type: 'SET_TASKS'; payload: Task[] }
  | { type: 'ADD_TASK'; payload: Task }
  | { type: 'UPDATE_TASK'; payload: { id: string; updates: Partial<Task> } }
  | { type: 'DELETE_TASK'; payload: string }
  | { type: 'SET_CURRENT_TASK'; payload: string | null }
  | { type: 'ADD_MESSAGE'; payload: { taskId: string; message: Message } }
  | { type: 'UPDATE_EXECUTION_STEP'; payload: { taskId: string; stepId: string; updates: Partial<ExecutionStep> } }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_TRIGGER_WELCOME_ANIMATION'; payload: boolean }
  | { type: 'CLEAR_INPUT_CONTENT'; payload: number };

// MCP scan result type definitions
export interface MCPVulnerabilityResult {
  pluginId: string;
  title: string;
  description: string; // Description in markdown format
  level: string; // Vulnerability severity
  suggestion: string; // Remediation suggestion
}

export interface MCPReportItem {
  title: string;
  description: string;
}

export interface MCPScanResult {
  target?: string; // Scan target
  plugins?: string[]; // Plugin list
  score?: number; // Score
  language?: string; // Language
  llm?: string; // Model name used
  start_time?: number; // Start time
  end_time?: number; // End time
  readme?: string; // README content
  results: MCPVulnerabilityResult[]; // Scan results
  report: MCPReportItem[]; // Explanations for vulnerabilities that were not detected
}

// AI infrastructure scan result type definitions
export interface InfraScanVulnerability {
  cve: string;
  severity: string;
  details: string;
  summary: string;
  security_advise: string;
  references: string[];
}

export interface InfraScanTarget {
  target_url: string;
  status_code: number;
  title?: string;
  fingerprint?: string;
  reason?: string;
  screenshot?: string;
  vulnerabilities: InfraScanVulnerability[];
}

export interface InfraScanResult {
  total: number; // Total number of vulnerabilities
  score: number; // Score
  results: InfraScanTarget[];
}

// Model red-team evaluation result type definitions
export interface RedteamReportResult {
  msgType: 'markdown' | 'text' | 'json'; // Specifies the type of content
  content: string | RedteamReportJsonContent; // Text or JSON depending on msgType
}

export interface RedteamReportJsonContent {
  total: number;
  score: number;
  results: Array<{
    status: 'safe' | 'warning' | 'jailbreak';
    vulnerability: string;
    attackMethod: string;
    input?: string;
    output?: string;
    reason?: string;
  }>;
  attachment?: string;
}

// Model one-click jailbreak result type definitions
export interface JailbreakResult {
  msgType: 'markdown' | 'text'; // Specifies the type of content
  content: string; // Text content when msgType is text
  status: boolean; // Whether the jailbreak succeeded
}

export interface AgentScanVulnerability {
  id: string;
  type: string;
  title: string;
  description: string;
  level: 'High' | 'Medium' | 'Low';
  owasp: string[];
  suggestion: string;
  conversation?: Array<{
    prompt: string;
    response: string;
  }>;
}

export interface OwaspAgenticRisk {
  id: string;
  name: string;
  total: number;
  high_or_above: number;
  max_level: string;
  findings: string[];
}

export interface AgentScanResult {
  schema_version: string;
  agent_name: string;
  agent_type: string;
  model_name: string;
  start_time: number;
  end_time: number;
  plugins: string[];
  score: number;
  risk_type: 'high' | 'medium' | 'low';
  total_tests: number;
  vulnerable_tests: number;
  results: AgentScanVulnerability[];
  owasp_agentic_2026_top10: OwaspAgenticRisk[];
  report_description: string;
}

// Evaluation set related type definitions
export interface EvaluationItem {
  name: string;
  description: string;
  description_zh: string;
  source: string[];
  author: string;
  count: number;
  tags: string[];
  recommendation: number;
  language: string;
  default?: boolean; // Whether this is the default evaluation set
  official?: boolean; // Whether this is an official evaluation set
  data: Array<{
    prompt: string;
  }>;
  // Custom evaluation set related fields
  isCustom?: boolean; // Whether this is a custom evaluation set
  promptColumn?: string; // Name of the prompt column
  originalFile?: string; // Original file name
}

export interface EvaluationListResponse {
  status: number;
  message: string;
  data: {
    total: number;
    page: number;
    size: number;
    items: EvaluationItem[];
  };
}
