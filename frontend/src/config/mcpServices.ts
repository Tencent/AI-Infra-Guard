import { useTranslation } from 'react-i18next';
import { enableEvalModel } from './env';

const useMcpServices = () => {
  const { t } = useTranslation();

  const baseServices = [
    {
      id: 'Agent-Scan',
      name: t('mcpServices.agentScan.name'),
      description: t('mcpServices.agentScan.description'),
      triggerWord: t('mcpServices.agentScan.triggerWord'),
      icon: 'Bot',
      placeholderPrefix: t('mcpServices.agentScan.placeholderPrefix'),
      placeholder: t('mcpServices.agentScan.placeholder', { returnObjects: true }),
      attachmentTypes: [],
      model: 'yes',
      modelTips: '{model}'
    },
    {
      id: 'Skill-Scan',
      name: t('mcpServices.skillScan.name'),
      description: t('mcpServices.skillScan.description'),
      triggerWord: t('mcpServices.skillScan.triggerWord'),
      icon: 'Sparkles',
      placeholderPrefix: t('mcpServices.skillScan.placeholderPrefix'),
      placeholder: t('mcpServices.skillScan.placeholder', { returnObjects: true }),
      attachmentTypes: ['.zip', '.tar.gz', '.tgz', '.whl'],
      model: 'yes',
      modelTips: '{model}',
      needPlugin: true
    },
    {
      id: 'Mcp-Scan',
      name: t('mcpServices.mcpScan.name'),
      description: t('mcpServices.mcpScan.description'),
      triggerWord: t('mcpServices.mcpScan.triggerWord'),
      icon: 'ShieldCheck',
      placeholderPrefix: t('mcpServices.mcpScan.placeholderPrefix'),
      placeholder: t('mcpServices.mcpScan.placeholder', { returnObjects: true }),
      attachmentTypes: ['.zip', '.tar.gz', '.tgz', '.whl'],
      model: 'yes',
      modelTips: '{model}',
      needPlugin: true
    },
    {
      id: 'Model-Redteam-Report',
      name: t('mcpServices.modelRedteamReport.name'),
      description: t('mcpServices.modelRedteamReport.description'),
      triggerWord: t('mcpServices.modelRedteamReport.triggerWord'),
      icon: 'AlertTriangle',
      placeholderPrefix: t('mcpServices.modelRedteamReport.placeholderPrefix'),
      placeholder: t('mcpServices.modelRedteamReport.placeholder', { returnObjects: true }),
      attachmentTypes: ['.csv', '.json', '.jsonl', '.txt', '.tsv', '.xlsx', '.xls', '.parquet'],
      model: 'multi',
      modelTips: t('mcpServices.modelTips')
    },
    {
      id: 'AI-Infra-Scan',
      name: t('mcpServices.aiInfraScan.name'),
      description: t('mcpServices.aiInfraScan.description'),
      triggerWord: t('mcpServices.aiInfraScan.triggerWord'),
      icon: 'Bug',
      placeholderPrefix: t('mcpServices.aiInfraScan.placeholderPrefix'),
      placeholder: t('mcpServices.aiInfraScan.placeholder', { returnObjects: true }),
      attachmentTypes: ['.txt'],
      model: 'yes',
      modelTips: '{model}'
    }
  ];

  // Attach the "eval model" field to the red-team report / jailbreak evaluation services
  // when the scoring-model capability is enabled (controlled by VITE_ENABLE_EVAL_MODEL,
  // defaults to isOpenSource when unset).
  const mcpServices = baseServices.map(service => {
    if (enableEvalModel && (service.id === 'Model-Redteam-Report' || service.id === 'Model-Jailbreak')) {
      return {
        ...service,
        evalModel: 'yes',
        evalModelTips: t('mcpServices.evalModelTips')
      };
    }
    return service;
  });

  return mcpServices;
};

// Mapping from task type to default field identifier
export const getTaskTypeDefaultIdentifier = (taskType: string): string => {
  const mapping: Record<string, string> = {
    'Model-Redteam-Report': 'model_redteam_report',
    'Mcp-Scan': 'mcp_scan',
    'Skill-Scan': 'mcp_scan',
    'AI-Infra-Scan': 'ai_infra_scan',
    'Agent-Scan': 'agent_scan',
  };
  return mapping[taskType] || '';
};

export { useMcpServices };
export type MCPService = ReturnType<typeof useMcpServices>[number];
