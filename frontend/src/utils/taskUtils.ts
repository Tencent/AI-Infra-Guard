// Task types that should show the model selection button
const MODEL_SELECTION_TASK_TYPES = ['Mcp-Scan', 'Skill-Scan', 'Model-Redteam-Report', 'Model-Jailbreak', 'AI-Infra-Scan', 'Agent-Scan'] as const;

// Task types that should show the evalModel selection button
const EVAL_MODEL_SELECTION_TASK_TYPES = ['Model-Redteam-Report', 'Model-Jailbreak'] as const;

/**
 * Determine whether the given task type should show the model selection button
 * @param taskType Task type
 * @returns Whether to show the model selection button
 */
export const shouldShowModelButton = (taskType?: string): boolean => {
  if (!taskType) return false;
  return MODEL_SELECTION_TASK_TYPES.includes(taskType as any);
};

/**
 * Determine whether the given task type should show the evalModel selection button
 * @param taskType Task type
 * @returns Whether to show the evalModel selection button
 */
export const shouldShowEvalModelButton = (taskType?: string): boolean => {
  if (!taskType) return false;
  return EVAL_MODEL_SELECTION_TASK_TYPES.includes(taskType as any);
};

/**
 * Get the list of task types that need to show the model selection button
 * @returns Array of task types
 */
export const getModelSelectionTaskTypes = (): readonly string[] => {
  return MODEL_SELECTION_TASK_TYPES;
};

/**
 * Get the list of task types that need to show the evalModel selection button
 * @returns Array of task types
 */
export const getEvalModelSelectionTaskTypes = (): readonly string[] => {
  return EVAL_MODEL_SELECTION_TASK_TYPES;
};
