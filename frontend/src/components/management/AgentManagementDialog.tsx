import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Plus, 
  Edit, 
  Trash2, 
  Bot,
  LoaderCircle,
  Settings,
  Maximize2,
  Download,
  Upload
} from 'lucide-react';
import { toast } from 'sonner';
import yaml from 'js-yaml';
import { agentApi } from '../../lib/agentApi';
import { Button, buttonVariants } from '../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../ui/alert-dialog';
import AgentConfigForm, { AgentTemplates } from './AgentConfigForm';


interface Agent {
  id: string;
  name: string;
  type?: string;
  baseUrl?: string;
  [key: string]: any;
}

const AgentManagementDialog: React.FC = () => {
  const { t, i18n } = useTranslation();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [showImportDialog, setShowImportDialog] = useState(false);
  const [currentFormData, setCurrentFormData] = useState<any>(null);
  const [formVersion, setFormVersion] = useState(0);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [agentToDelete, setAgentToDelete] = useState<Agent | null>(null);
  
  const [templates, setTemplates] = useState<AgentTemplates | null>(null);
  const [templatesLoading, setTemplatesLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadAgents();
    loadTemplates();
  }, []);

  const loadTemplates = async () => {
    setTemplatesLoading(true);
    try {
      const lang = i18n.language || 'en';
      const response = await agentApi.getTemplates(lang);
      
      // Handle multiple response formats:
      // 1. Standard format: { status: 0, data: ... }
      // 2. Alternative standard format: { code: 0, data: ... }
      if ((response.status === 0 || response.code === 0) && response.data) {
        setTemplates(response.data);
      } 
      // 3. Raw data format (containing keywords like http, common, etc.)
      else if (response && ((response as any).http || (response as any).common || (response as any).dify)) {
        setTemplates(response as any);
      }
      else {
        console.error('Failed to load agent templates:', response);
        const msg = response.message || response.msg || 'Unknown error';
        toast.error(t('agentManagement.loadTemplatesFailed') || 'Failed to load templates');
      }
    } catch (error) {
      console.error('Failed to load agent templates:', error);
      toast.error(t('agentManagement.loadTemplatesFailed') || 'Failed to load templates');
    } finally {
      setTemplatesLoading(false);
    }
  };

  const loadAgents = async () => {
    setLoading(true);
    try {
      const response = await agentApi.getAgentNames();
      if (response.status === 0) {
        const names = response.data || [];
        
        // Fetch details for each agent
        const agentPromises = names.map(async (name: string) => {
          try {
            const detailRes = await agentApi.getAgent(name);
            let type = '';
            let baseUrl = '';
            let config: any = {};
            
            if (detailRes.status === 0 && detailRes.data) {
              const yamlContent = detailRes.data;
              try {
                let parsed = yaml.load(yamlContent as unknown as string) as any;
                if (parsed && !Array.isArray(parsed) && parsed.targets && Array.isArray(parsed.targets)) {
                  parsed = parsed.targets;
                }
                
                if (Array.isArray(parsed) && parsed.length > 0) {
                  const first = parsed[0];
                  type = first.id || '';
                  config = first.config || {};
                  
                  if (type === 'http') {
                    baseUrl = config.url || '';
                  } else if (type === 'dify') {
                    baseUrl = config.apiBaseUrl || '';
                  } else if (type === 'coze') {
                    baseUrl = config.apiBaseUrl || '';
                  }
                }
              } catch (e) {
                console.error(`Failed to parse config for ${name}`, e);
              }
            }
            
            return {
              id: name,
              name: name,
              type,
              baseUrl,
              ...config
            };
          } catch (e) {
            console.error(`Failed to fetch details for ${name}`, e);
            return { id: name, name: name };
          }
        });
        
        const agentList = await Promise.all(agentPromises);
        setAgents(agentList);
      } else {
        console.error('API返回错误状态:', response.message);
        setAgents([]);
      }
    } catch (error) {
      console.error('加载Agent列表失败:', error);
      setAgents([]);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = () => {
    setEditingAgent({ id: 'new', name: '' }); // Use a temporary object for new agent
    setCurrentFormData(null);
    setFormVersion(0);
    setIsFullScreen(true);
  };

  const handleEdit = (agent: Agent) => {
    // We might need to fetch full agent details here if 'agent' only has name/id
    // For now assuming we can edit based on name or need to fetch config
    // TODO: fetch agent config if needed
    setEditingAgent(agent);
    setCurrentFormData(null);
    setFormVersion(0);
    setIsFullScreen(false);
  };

  const handleDelete = (agent: Agent) => {
    setAgentToDelete(agent);
    setDeleteConfirmOpen(true);
  };

  const confirmDelete = async () => {
    if (!agentToDelete) return;

    // Use a separate loading state or reuse loading? 
    // If we reuse loading, the list will show skeleton/spinner. 
    // Let's reuse loading for now as ModelManagementDialog does.
    setLoading(true);

    try {
      const response = await agentApi.deleteAgent(agentToDelete.name);
      if (response.status === 0) {
        toast.success(t('agentManagement.deleteSuccess') || 'Deleted successfully');
        if (editingAgent?.name === agentToDelete.name) {
            setEditingAgent(null);
            setCurrentFormData(null);
            setIsFullScreen(false);
        }
        await loadAgents();
      } else {
        toast.error(response.message || t('agentManagement.deleteFailed') || 'Delete failed');
      }
    } catch (error) {
      console.error('Delete agent failed:', error);
      toast.error(t('agentManagement.deleteFailed') || 'Delete failed');
    } finally {
        setLoading(false);
        setDeleteConfirmOpen(false);
        setAgentToDelete(null);
    }
  };
  
  const validateAndGenerateYaml = (data: any): string | null => {
    // Validate name
    if (!data.name) {
      toast.error(t('agentManagement.nameRequired') || 'Agent name is required');
      return null;
    }

    const { name, type, ...rest } = data;

    let allFields: any[] = [];

    // Validate required fields
    if (templates && type && templates[type]) {
      const currentTemplate = templates[type];
      const commonTemplate = templates.common;
      
      allFields = [
        ...currentTemplate.fields,
        ...(commonTemplate ? commonTemplate.fields : [])
      ];
      
      for (const field of allFields) {
        if (field.required) {
          // Check for values, handling 0 as valid but checking for undefined/null/empty string
          const value = data[field.field];
          if (value === undefined || value === null || value === '') {
            toast.error(t('agentManagement.fieldRequired', { field: field.label }) || `${field.label} is required`);
            return null;
          }
        }
      }
    }

    // Construct config object
    const config: any = {};

    // Helper to set nested value
    const setNested = (obj: any, path: string, value: any) => {
      const keys = path.split('.');
      let current = obj;
      for (let i = 0; i < keys.length - 1; i++) {
        const key = keys[i];
        current[key] = current[key] || {};
        current = current[key];
      }
      current[keys[keys.length - 1]] = value;
    };

    if (allFields.length > 0) {
      allFields.forEach((fieldDef: any) => {
        const key = fieldDef.field;
        let value = data[key];

        if (value === undefined) return;

        if (fieldDef.idSuffix && value) {
          value = fieldDef.idSuffix.replace('{value}', String(value));
        }
        
        setNested(config, key, value);
      });
    } else {
      Object.keys(rest).forEach(key => {
        // Skip internal fields
        if (['id', 'baseUrl', 'isEdit'].includes(key)) return;
        
        setNested(config, key, rest[key]);
      });
    }

    const yamlObj = {
      targets: [
        {
          id: type,
          config: config
        }
      ]
    };

    try {
      return yaml.dump(yamlObj);
    } catch (e) {
      console.error('YAML dump failed', e);
      return null;
    }
  };

  const handleTestConnection = async (data: any) => {
    const yamlContent = validateAndGenerateYaml(data);
    if (!yamlContent) return;

    const loadingToast = toast.loading(t('agentManagement.connectionTestWait') || 'The connection test may take some time, please wait patiently.');
    try {
       const response = await agentApi.testConnection(yamlContent);
       toast.dismiss(loadingToast);
       
       if (response.status === 0) {
         toast.success(t('agentManagement.testConnectionSuccess') || 'Connection successful');
       } else {
         toast.error(response.message || t('agentManagement.testConnectionFailed') || 'Connection failed');
       }
    } catch (error) {
       toast.dismiss(loadingToast);
       console.error('Test connection failed:', error);
       toast.error(t('agentManagement.testConnectionFailed') || 'Connection failed');
    }
  };
  
  const handlePromptTest = async (data: any, prompt: string): Promise<string | null> => {
    const yamlContent = validateAndGenerateYaml(data);
    if (!yamlContent) return null;

    try {
       const response = await agentApi.promptTest(yamlContent, prompt);
       
       if (response.status === 0) {
         return response.message || '';
       } else {
         toast.error(response.message || t('agentManagement.testFailed') || 'Test failed');
         return null;
       }
    } catch (error) {
       console.error('Test prompt failed:', error);
       toast.error(t('agentManagement.testFailed') || 'Test failed');
       return null;
    }
  };
  
  const handleSaveAgent = async (data: any) => {
    const yamlContent = validateAndGenerateYaml(data);
    if (!yamlContent) return;
    
    const { name } = data;

    try {
      const response = await agentApi.saveAgent(name, yamlContent);

      if (response.status === 0) {
        toast.success(t('agentManagement.saveSuccess') || 'Saved successfully');
        setEditingAgent(null);
        setCurrentFormData(null);
        setIsFullScreen(false);
        loadAgents(); // Refresh list
      } else {
        toast.error(response.message || t('agentManagement.saveFailed') || 'Save failed');
      }
    } catch (error) {
      console.error('Save failed:', error);
      toast.error(t('agentManagement.saveFailed') || 'Save failed');
    }
  };

  const handleCloseEdit = () => {
    setEditingAgent(null);
    setCurrentFormData(null);
    setIsFullScreen(false);
  };

  const generateYamlFromTemplate = (type: string, templateData: any) => {
    if (!templateData) return '';
    const config: any = {};
    const fields = templateData.fields || [];
    
    fields.forEach((f: any) => {
         config[f.field] = f.defaultValue !== undefined ? f.defaultValue : '';
    });

    if (templates?.common?.fields) {
        templates.common.fields.forEach((f: any) => {
             config[f.field] = f.defaultValue !== undefined ? f.defaultValue : '';
        });
    }
    
    const finalConfig: any = {};
    const setNested = (obj: any, path: string, value: any) => {
      const keys = path.split('.');
      let current = obj;
      for (let i = 0; i < keys.length - 1; i++) {
        const key = keys[i];
        current[key] = current[key] || {};
        current = current[key];
      }
      current[keys[keys.length - 1]] = value;
    };

    Object.keys(config).forEach(key => {
        setNested(finalConfig, key, config[key]);
    });

    const yamlObj = {
      targets: [
        {
          id: type,
          config: finalConfig
        }
      ]
    };
    return yaml.dump(yamlObj);
  };

  const handleDownloadTemplate = (targetType?: string) => {
    // Determine type: from argument, current form data, or from editing agent if exists
    const type = targetType || currentFormData?.type || editingAgent?.type;
    
    if (!type || !templates || !templates[type]) {
         toast.error(t('agentManagement.selectTypeFirst') || 'Please select an agent type first');
         return;
    }
    
    try {
      const yamlContent = generateYamlFromTemplate(type, templates[type]);
      const blob = new Blob([yamlContent], { type: 'text/yaml' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${type}-template.yaml`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to generate template YAML:', error);
      toast.error(t('agentManagement.generateTemplateFailed') || 'Failed to generate template');
    }
  };

  const handleUploadClick = () => {
    // Keep import dialog open until upload is complete
    fileInputRef.current?.click();
  };

  const handleUploadYaml = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Use filename (without extension) as agent name
    const fileName = file.name;
    const agentName = fileName.replace(/\.(yaml|yml)$/i, '');

    if (!agentName) {
        toast.error(t('agentManagement.invalidFilename') || 'Invalid filename');
        if (fileInputRef.current) fileInputRef.current.value = '';
        return;
    }

    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        let content = event.target?.result as string;
        let parsed: any;
        try {
            parsed = yaml.load(content);
        } catch (e) {
            console.error('YAML parse error:', e);
            toast.error(t('agentManagement.parseError') || 'Failed to parse YAML file');
            if (fileInputRef.current) fileInputRef.current.value = '';
            return;
        }
        let targets: any[] = [];
        if (Array.isArray(parsed)) {
          targets = parsed;
        } else if (parsed && typeof parsed === 'object' && Array.isArray(parsed.targets)) {
          targets = parsed.targets;
        }

        if (targets.length === 0 || !targets[0].id) {
          toast.error(t('agentManagement.invalidYaml') || 'Invalid YAML format: must be an array with id');
          if (fileInputRef.current) fileInputRef.current.value = '';
          return;
        }

        let finalAgentName = agentName;
        if (targets[0].config && targets[0].config.label) {
            const label = String(targets[0].config.label).trim();
            if (label) {
                finalAgentName = label;
            }
        }

        const finalObj = { targets: targets };
        try {
            content = yaml.dump(finalObj);
        } catch (e) {
            console.error('YAML dump error:', e);
            toast.error(t('agentManagement.parseError') || 'Failed to process YAML');
            return;
        }

        // Upload to backend
        const loadingToast = toast.loading(t('agentManagement.uploading') || 'Uploading...');
        try {
            const response = await agentApi.saveAgent(finalAgentName, content);
            toast.dismiss(loadingToast);
            
            if (response.status === 0) {
                toast.success(t('agentManagement.uploadSuccess') || 'Agent created successfully');
                setShowImportDialog(false);
                loadAgents();
            } else {
                toast.error(response.message || t('agentManagement.saveFailed') || 'Save failed');
            }
        } catch (error) {
            toast.dismiss(loadingToast);
            console.error('Save failed:', error);
            toast.error(t('agentManagement.saveFailed') || 'Save failed');
        }

        // Reset file input
        if (fileInputRef.current) fileInputRef.current.value = '';
        
      } catch (error) {
        console.error('Error processing file:', error);
        toast.error(t('agentManagement.parseError') || 'Error processing file');
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="w-full h-full flex flex-col relative">
      <input 
        type="file" 
        ref={fileInputRef} 
        className="hidden" 
        accept=".yaml,.yml" 
        onChange={handleUploadYaml} 
      />
      <div className="flex-1 flex overflow-hidden">
        {/* Left-hand Agent list */}
        <div className="w-1/2 border-r border-gray-200 p-4 flex flex-col">
          <div className="flex items-center justify-between mb-4 flex-shrink-0">
            <h3 className="font-medium">{t('agentManagement.agentList')}</h3>
            <div className="flex gap-2">
              <Button 
                size="sm" 
                variant="outline"
                className="gap-2"
                onClick={() => setShowImportDialog(true)}
              >
                <Upload className="w-4 h-4" />
                {t('agentManagement.importExport') || "Upload YAML"}
              </Button>
            <Button 
              size="sm" 
              className="gap-0"
              onClick={handleAdd}
              disabled={loading}
            >
              <Plus className="w-4 h-4" />
              {t('agentManagement.add')}
            </Button>
            </div>
          </div>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <LoaderCircle className="w-6 h-6 animate-spin" />
            </div>
          ) : (
            <div className="space-y-2 overflow-y-auto scrollbar-hover flex-1">
              {agents.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>{t('agentManagement.noAgentData')}</p>
                </div>
              ) : (
                agents.map((agent) => (
                  <div
                    key={agent.id}
                    className={`p-3 border rounded-lg transition-colors ${
                      editingAgent?.id === agent.id
                        ? 'border-blue-500 bg-blue-50 cursor-pointer'
                        : 'border-gray-200 hover:border-gray-300 cursor-pointer'
                    }`}
                    onClick={(e) => {
                      if ((e.target as HTMLElement).closest('button')) {
                        return;
                      }
                      handleEdit(agent);
                    }}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1 overflow-hidden mr-2">
                        <div className="flex items-center gap-2 mb-1">
                          {agent.type && templates && templates[agent.type] && (
                             (() => {
                               // @ts-ignore
                               const iconPath = templates[agent.type].icon;
                               return iconPath ? (
                                  <img src={iconPath} alt={agent.type} className="w-5 h-5 object-contain flex-shrink-0" />
                               ) : (
                                  <div className="w-5 h-5 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
                                    <Bot className="w-3 h-3 text-gray-500" />
                                  </div>
                               );
                             })()
                          )}
                          {!agent.type && (
                              <div className="w-5 h-5 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
                                <Bot className="w-3 h-3 text-gray-500" />
                              </div>
                          )}
                          <h4 className="font-medium text-sm break-words" title={agent.name}>{agent.name}</h4>
                        </div>
                        <div className="text-xs text-gray-500 flex flex-col gap-0.5">
                          {agent.baseUrl && (
                            <span className="truncate text-gray-400" title={agent.baseUrl}>{agent.baseUrl}</span>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-2 flex-shrink-0 self-start">
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleEdit(agent);
                          }}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(agent);
                          }}
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
        {/* Right-hand edit area */}
        <div className="w-1/2 p-4 h-full overflow-y-auto scrollbar-hover">
          {editingAgent ? (
            !isFullScreen && (
            <div>
              <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium">{editingAgent.id === 'new' ? t('agentManagement.addAgent') : t('agentManagement.editAgent')}</h3>
                  <div className="flex items-center gap-1">
                  <Button variant="ghost" size="icon" onClick={() => setIsFullScreen(true)}>
                    <Maximize2 className="w-4 h-4" />
                  </Button>
                  </div>
              </div>
              {templatesLoading ? (
                 <div className="flex justify-center p-4"><LoaderCircle className="animate-spin" /></div>
              ) : templates ? (
                 <AgentConfigForm 
                    key={`${editingAgent.id}-${formVersion}`}
                    templates={templates} 
                    initialData={editingAgent.id === 'new' ? undefined : editingAgent} 
                    onSave={handleSaveAgent} 
                    onCancel={handleCloseEdit} 
                    onChange={setCurrentFormData}
                    onTestConnection={handleTestConnection}
                    onPromptTest={handlePromptTest}
                    isEdit={editingAgent.id !== 'new'}
                 />
              ) : (
                 <p className="text-red-500">Failed to load templates</p>
              )}
            </div>
            )
          ) : (
            <div className="flex items-center justify-center h-full text-gray-500">
              <div className="text-center">
                <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>{t('agentManagement.selectAgentToEdit')}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      <Dialog open={isFullScreen} onOpenChange={setIsFullScreen}>
        <DialogContent className="max-w-4xl h-[90vh] flex flex-col">
          <DialogHeader className="flex flex-row items-center justify-between pr-8">
             <DialogTitle>{editingAgent?.id === 'new' ? t('agentManagement.addAgent') : t('agentManagement.editAgent')}</DialogTitle>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto p-4">
              {templates && editingAgent && (
                 <AgentConfigForm 
                    key={`${editingAgent.id}-${formVersion}`}
                    templates={templates} 
                    initialData={editingAgent.id === 'new' ? undefined : editingAgent} 
                    onSave={handleSaveAgent} 
                    onCancel={handleCloseEdit} 
                    onChange={setCurrentFormData}
                    onTestConnection={handleTestConnection}
                    onPromptTest={handlePromptTest}
                    isEdit={editingAgent.id !== 'new'}
                 />
              )}
          </div>
        </DialogContent>
      </Dialog>
      <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('agentManagement.uploadYaml') || 'Upload Agent YAML'}</DialogTitle>
          </DialogHeader>
          <div className="py-4">
             <p className="text-sm text-gray-500 mb-4">
               {t('agentManagement.uploadInstructions') || 'Please prepare a YAML file in the following format, then upload it to create an agent.'}
             </p>
             
             {templates && (
               <div className="mb-6">
                 <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                   {Object.keys(templates)
                     .filter(key => key !== 'common')
                     .map(key => {
                       const tpl = templates[key];
                       // @ts-ignore
                       const iconPath = tpl.icon;
                       return (
                         <div 
                           key={key}
                           className="border rounded-lg p-3 hover:border-blue-500 hover:bg-blue-50 cursor-pointer transition-all group relative"
                           onClick={() => handleDownloadTemplate(key)}
                           title={tpl.description}
                         >
                            <div className="flex items-center gap-3">
                              {iconPath ? (
                                <img src={iconPath} alt={key} className="w-6 h-6 object-contain" />
                              ) : (
                                <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                                  <Bot className="w-4 h-4 text-gray-500" />
                                </div>
                              )}
                              <div className="flex-1 min-w-0">
                                <h5 className="font-medium text-sm break-words">{tpl.name}</h5>
                              </div>
                              <Download className="w-4 h-4 text-gray-400 group-hover:text-blue-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                            </div>
                         </div>
                       );
                     })}
                 </div>
               </div>
             )}

             <Button 
               className="w-full h-12 text-base" 
               onClick={handleUploadClick}
             >
               <Upload className="w-5 h-5 mr-2" />
               {t('agentManagement.uploadYamlFile') || 'Upload YAML File'}
             </Button>
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('agentManagement.confirmDeleteTitle') || 'Confirm Delete'}</AlertDialogTitle>
            <AlertDialogDescription>
              {agentToDelete && (t('agentManagement.confirmDelete', { name: agentToDelete.name }) || `Are you sure you want to delete ${agentToDelete.name}?`)}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={loading}>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={(e) => {
                e.preventDefault();
                confirmDelete();
              }}
              disabled={loading}
              className={buttonVariants({ variant: 'destructive' })}
            >
              {loading ? (
                <LoaderCircle className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                t('common.delete')
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
export default AgentManagementDialog;
