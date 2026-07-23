import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { 
  LoaderCircle,
  HelpCircle,
  Check,
  Bot,
  Wifi,
  AlertCircle,
  Settings2,
  Sparkles
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../ui/accordion';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';

interface AgentTemplateField {
  field: string;
  label: string;
  type: 'text' | 'select' | 'textarea' | 'number' | 'password' | 'json';
  required: boolean;
  placeholder?: string;
  description?: string;
  defaultValue?: any;
  options?: { label: string; value: string }[];
  min?: number;
  max?: number;
  step?: number;
  rows?: number;
  idSuffix?: string;
}

interface AgentTemplateType {
  name: string;
  description: string;
  icon?: string;
  fields: AgentTemplateField[];
}

export interface AgentTemplates {
  [key: string]: AgentTemplateType;
}

interface AgentConfigFormProps {
  templates: AgentTemplates;
  initialData?: any;
  onSave: (data: any) => Promise<void>;
  onCancel: () => void;
  onChange?: (data: any) => void;
  onTestConnection?: (data: any) => Promise<void>;
  onPromptTest?: (data: any, prompt: string) => Promise<string | null>;
  isEdit?: boolean;
}

interface AgentConfigFieldProps {
  fieldConfig: AgentTemplateField;
  formData: any;
  onChange: (field: string, value: any) => void;
  disabled?: boolean;
}

const AgentConfigField: React.FC<AgentConfigFieldProps> = ({ fieldConfig, formData, onChange, disabled }) => {
  const { field, label, type, required, placeholder, description, options, min, max, step, rows } = fieldConfig;
  const value = formData[field] !== undefined ? formData[field] : (required && type === 'select' && options && options.length > 0 ? options[0].value : '');
  const [jsonError, setJsonError] = useState<string | null>(null);

  // Ensure the Select component receives the correct value; when value is empty and a default exists, use the default value
  // The default-value logic has already been handled when computing value.
  // The issue is that after handleChange updates state and the component re-renders, value should be read from formData.
  
  // Special case: for a required select, when there is no initial value, auto-select the first option and trigger change
  useEffect(() => {
      if (!disabled && type === 'select' && required && options && options.length > 0 && formData[field] === undefined) {
           onChange(field, options[0].value);
      }
  }, [type, required, options, field, disabled]); // Remove formData[field] from dependency array to avoid infinite loop

  const handleJsonChange = (val: string) => {
    onChange(field, val);
    try {
      if (val.trim()) {
        JSON.parse(val);
      }
      setJsonError(null);
    } catch (e) {
      setJsonError((e as Error).message);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
          <Label htmlFor={field} className="text-sm font-medium">
          {label} {required && <span className="text-red-500">*</span>}
          </Label>
          {description && (
              <TooltipProvider delayDuration={0}>
                  <Tooltip>
                      <TooltipTrigger asChild>
                          <div className="cursor-help inline-flex">
                            <HelpCircle className="h-4 w-4 text-gray-400" />
                          </div>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-xs z-[9999]">
                          <p>{description}</p>
                      </TooltipContent>
                  </Tooltip>
              </TooltipProvider>
          )}
      </div>
      
      {type === 'select' ? (
        <Select value={value} onValueChange={(val) => onChange(field, val)} disabled={disabled}>
          <SelectTrigger>
            <SelectValue placeholder={placeholder || label} />
          </SelectTrigger>
          <SelectContent>
            {options?.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : type === 'textarea' ? (
        <Textarea
          id={field}
          value={value}
          onChange={(e) => onChange(field, e.target.value)}
          placeholder={placeholder}
          rows={rows || 3}
          className="w-full"
          disabled={disabled}
        />
      ) : type === 'json' ? (
        <div className="relative">
          <Textarea
            id={field}
            value={value}
            onChange={(e) => handleJsonChange(e.target.value)}
            placeholder={placeholder || '{\n  "key": "value"\n}'}
            rows={rows || 5}
            className={`w-full font-mono text-sm ${jsonError ? 'border-red-500 focus-visible:ring-red-500' : ''}`}
            disabled={disabled}
          />
          {jsonError && (
            <div className="text-xs text-red-500 mt-1 flex items-center">
              <AlertCircle className="w-3 h-3 mr-1" />
              {jsonError}
            </div>
          )}
        </div>
      ) : (
        <Input
          id={field}
          type={type === 'number' ? 'number' : type === 'password' ? 'password' : 'text'}
          value={value}
          onChange={(e) => onChange(field, type === 'number' ? Number(e.target.value) : e.target.value)}
          placeholder={placeholder}
          min={min}
          max={max}
          step={step}
          className="w-full"
          disabled={disabled}
        />
      )}
    </div>
  );
};

const AgentConfigForm: React.FC<AgentConfigFormProps> = ({ templates, initialData, onSave, onCancel, onChange, onTestConnection, onPromptTest, isEdit = false }) => {
  const { t } = useTranslation();
  // Exclude 'common' from provider options
  const providerOptions = Object.keys(templates).filter(key => key !== 'common');
  
  const [provider, setProvider] = useState<string>(initialData?.type || (providerOptions.length > 0 ? providerOptions[0] : ''));
  const [formData, setFormData] = useState<any>(initialData || {});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testPrompt, setTestPrompt] = useState('');
  const [testResponse, setTestResponse] = useState<string | null>(null);
  const [isPromptTesting, setIsPromptTesting] = useState(false);
  const [hasTestedPrompt, setHasTestedPrompt] = useState(false);

  useEffect(() => {
    if (onChange) {
      onChange(formData);
    }
  }, [formData, onChange]);

  useEffect(() => {
    // If adding new agent (no initialData), populate default values when provider changes
    if (!initialData && provider && templates[provider]) {
      const defaults: any = { 
        type: provider,
        name: templates[provider].name // Auto set name from template
      };
      
      const processFields = (fields: AgentTemplateField[]) => {
          fields.forEach(f => {
            if (f.defaultValue !== undefined) {
                 defaults[f.field] = f.type === 'json' && typeof f.defaultValue === 'object' 
                    ? JSON.stringify(f.defaultValue, null, 2) 
                    : f.defaultValue;
            } else if (f.required && f.type === 'select' && f.options && f.options.length > 0) {
                 defaults[f.field] = f.options[0].value;
            }
          });
      };

      // Provider specific defaults
      processFields(templates[provider].fields);
      
      // Common defaults
      if (templates.common) {
        processFields(templates.common.fields);
      }
      
      setFormData((prev: any) => ({ ...prev, ...defaults }));
    } else if (initialData) {
       // If editing, ensure we keep the type
       setProvider(initialData.type || provider);
       
       // Handle JSON fields conversion from object to string for display
       // Also flatten nested fields (dot notation) from initialData to flat formData keys
       const processedData: any = { ...initialData };
       
       // Helper to get nested value from object using dot notation
       const getNestedValue = (obj: any, path: string) => {
         if (!path || !obj) return undefined;
         const keys = path.split('.');
         let current = obj;
         for (const key of keys) {
           if (current === undefined || current === null) return undefined;
           current = current[key];
         }
         return current;
       };

       if (provider && templates[provider]) {
           const allFields = [
               ...templates[provider].fields,
               ...(templates.common ? templates.common.fields : [])
           ];
           
           allFields.forEach(f => {
               // Try to get value from initialData using field path
               // This handles cases where field is "some.nested.prop" and initialData is { some: { nested: { prop: val } } }
               let val = getNestedValue(initialData, f.field);
               
               // If value was found (and not already set in processedData as a flat key), set it
               if (val !== undefined) {
                   // Special handling for idSuffix: extract original value from template pattern
                   if (f.idSuffix && typeof val === 'string' && f.idSuffix.includes('{value}')) {
                       // Create regex pattern by escaping special characters in idSuffix
                       // and replacing {value} with capture group
                       const pattern = f.idSuffix.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace('\\{value\\}', '(.+)');
                       const regex = new RegExp(`^${pattern}$`);
                       const match = val.match(regex);
                       if (match && match[1]) {
                           val = match[1];
                       }
                   }

                   processedData[f.field] = val;
               } else {
                   // Fallback: check if the flat key already exists in initialData (maybe flattened by backend or other logic)
                   val = processedData[f.field];
               }

               if (f.type === 'json' && val && typeof val === 'object') {
                   try {
                       processedData[f.field] = JSON.stringify(val, null, 2);
                   } catch (e) {
                       console.error('Failed to stringify JSON field', f.field, e);
                   }
               }
           });
       }
       
       // Only set name from template if it's not set in initialData (or if we want to ensure it matches template name in some cases, but for edit we usually want to keep original name)
       // actually, user asked to not allow editing name in edit mode, and usually id/name is fixed.
       // But we should NOT overwrite existing name with template name if they differ.
       if (!processedData.name && provider && templates[provider]) {
           processedData.name = templates[provider].name;
       }

       setFormData(processedData);
    }
  }, [provider, templates, initialData]);

  const handleChange = (field: string, value: any) => {
    setFormData((prev: any) => ({ ...prev, [field]: value }));
  };
  
  const processDataForSubmit = (data: any): { isValid: boolean, data: any } => {
      if (!provider || !templates[provider]) return { isValid: true, data };
      
      const processed = { ...data };
      const allFields = [
           ...templates[provider].fields,
           ...(templates.common ? templates.common.fields : [])
      ];
      
      // Check if there is a 'label' field in the form data and use it as name if present
      const labelField = allFields.find(f => f.field === 'label');
      if (labelField && processed.label) {
          processed.name = processed.label;
      }
      
      for (const f of allFields) {
          if (f.type === 'json' && processed[f.field]) {
              if (typeof processed[f.field] === 'string') {
                  try {
                      processed[f.field] = JSON.parse(processed[f.field]);
                  } catch (e) {
                      // If required and invalid, we should probably return invalid
                      // But maybe we just keep it as string and let the backend fail?
                      // Better to fail early.
                      return { isValid: false, data: null };
                  }
              }
          }
      }
      return { isValid: true, data: processed };
  };

  const handleProviderChange = (value: string) => {
    if (isEdit) return;
    setProvider(value);
    setFormData({
      type: value,
      name: templates[value]?.name || ''
    });
  };

  if (!provider || !templates[provider]) return null;

  const currentTemplate = templates[provider];
  const commonTemplate = templates.common;

  const allFields = [
    ...currentTemplate.fields,
    ...(commonTemplate ? commonTemplate.fields : [])
  ];

  const requiredFields = allFields.filter(f => f.required);
  const optionalFields = allFields.filter(f => !f.required);

  return (
    <div className="space-y-6">
      <div className="space-y-2 px-1">
        <Label>{t('agentManagement.agentType')}</Label>
        {isEdit ? (
          <div className="flex items-center gap-3 p-3 border rounded-lg bg-gray-50 text-gray-500">
             {templates[provider]?.icon ? (
                <img src={templates[provider].icon} alt={templates[provider].name} className="w-6 h-6 object-contain" />
             ) : (
                <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center">
                  <Bot className="w-4 h-4 text-gray-500" />
                </div>
             )}
             <span className="font-medium">{templates[provider]?.name}</span>
          </div>
        ) : (
          <div className="flex flex-wrap gap-3">
            {providerOptions.map((key) => {
              const tpl = templates[key];
              const isSelected = provider === key;
              return (
                <div 
                  key={key}
                  className={`border rounded-lg p-3 cursor-pointer transition-all relative flex items-center gap-3 min-w-[200px] flex-1 ${
                    isSelected 
                      ? 'border-blue-500 bg-blue-50 ring-1 ring-blue-500' 
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                  }`}
                  onClick={() => handleProviderChange(key)}
                  style={{ pointerEvents: isSubmitting || isTesting ? 'none' : 'auto', opacity: isSubmitting || isTesting ? 0.7 : 1 }}
                >
                   {tpl.icon ? (
                      <img src={tpl.icon} alt={tpl.name} className="w-6 h-6 object-contain" />
                   ) : (
                      <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
                        <Bot className="w-4 h-4 text-gray-500" />
                      </div>
                   )}
                   <span className="font-medium text-sm break-words flex-1">{tpl.name}</span>
                   {isSelected && (
                      <Check className="w-4 h-4 text-blue-500 flex-shrink-0" />
                   )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="space-y-4 px-1">
        {requiredFields.map((field) => (
          <AgentConfigField
            key={field.field}
            fieldConfig={field}
            formData={formData}
            onChange={handleChange}
            disabled={isSubmitting || isTesting || (isEdit && field.field === 'label')}
          />
        ))}
      </div>

      {optionalFields.length > 0 && (
        <Accordion type="single" collapsible className="w-full">
          <AccordionItem value="advanced" className="border-b-0">
            <AccordionTrigger className="px-1 hover:no-underline" disabled={isSubmitting || isTesting}>
              <div className="flex items-center gap-2">
                <Settings2 className="w-4 h-4" />
                {t('agentManagement.advancedSettings')}
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4 pt-4 px-1">
                {optionalFields.map((field) => (
                  <AgentConfigField
                    key={field.field}
                    fieldConfig={field}
                    formData={formData}
                    onChange={handleChange}
                    disabled={isSubmitting || isTesting || (isEdit && field.field === 'label')}
                  />
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      )}

      {onPromptTest && (
        <Accordion type="single" collapsible defaultValue="prompt-test" className="w-full">
          <AccordionItem value="prompt-test" className="border-b-0">
            <AccordionTrigger className="px-1 hover:no-underline" disabled={isSubmitting || isTesting}>
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                {t('agentManagement.promptTest') || 'Prompt Test'}
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4 pt-4 px-1">
                <div className="space-y-2">
                    <Textarea 
                        id="test-prompt" 
                        value={testPrompt} 
                        onChange={(e) => setTestPrompt(e.target.value)} 
                        placeholder={t('agentManagement.enterPrompt') || 'Enter prompt here...'}
                        rows={3}
                        disabled={isPromptTesting}
                    />
                </div>
                <Button 
                    variant="secondary" 
                    size="sm"
                    disabled={isPromptTesting || !testPrompt.trim()}
                    onClick={async () => {
                         const { isValid, data } = processDataForSubmit(formData);
                         if (!isValid) {
                             toast.error(t('agentManagement.invalidJson') || 'Please fix JSON errors first');
                             return;
                         }
                         setIsPromptTesting(true);
                         setTestResponse(null);
                         try {
                             const res = await onPromptTest(data, testPrompt);
                             if (res) {
                                 setTestResponse(res);
                                 setHasTestedPrompt(true);
                             }
                         } finally {
                             setIsPromptTesting(false);
                         }
                    }}
                >
                    {isPromptTesting ? <LoaderCircle className="w-4 h-4 animate-spin mr-2" /> : <Bot className="w-4 h-4 mr-2" />}
                    {t('agentManagement.runTest') || 'Run Test'}
                </Button>
                {testResponse && (
                    <div className="mt-4">
                        <Label className="text-xs text-gray-500 mb-1 block">{t('agentManagement.testResult') || 'Test Result'}</Label>
                        <div className="p-3 bg-gray-50 rounded-md border text-sm whitespace-pre-wrap max-h-60 overflow-y-auto">
                            {testResponse}
                        </div>
                    </div>
                )}
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      )}

      <div className="flex flex-col gap-2 pt-4 px-1">
        {onPromptTest && !hasTestedPrompt && (
          <p className="text-xs text-amber-600 flex items-center gap-1">
            <AlertCircle className="w-3 h-3" />
            {t('agentManagement.runTestRequired') || 'Please run the access verification test before saving.'}
          </p>
        )}
        <div className="flex space-x-2">
        <Button 
          onClick={async () => {
              const { isValid, data } = processDataForSubmit(formData);
              if (isValid) {
                  setIsSubmitting(true);
                  toast.info(t('agentManagement.saveWait'));
                  try {
                      await onSave(data);
                  } finally {
                      setIsSubmitting(false);
                  }
              } else {
                  toast.error(t('agentManagement.invalidJson') || 'Please fix JSON errors before saving');
              }
          }} 
          className="flex-1"
          disabled={isSubmitting || isTesting || (!!onPromptTest && !hasTestedPrompt)}
        >
          {isSubmitting ? <LoaderCircle className="w-4 h-4 mr-0 animate-spin" /> : <Check className="w-4 h-4 mr-0" />}
          {t('common.save')}
        </Button>
        {onTestConnection && (
          <Button 
            variant="secondary"
            onClick={async () => {
                const { isValid, data } = processDataForSubmit(formData);
                if (isValid) {
                    setIsTesting(true);
                    try {
                        await onTestConnection(data);
                    } finally {
                        setIsTesting(false);
                    }
                } else {
                    toast.error(t('agentManagement.invalidJson') || 'Please fix JSON errors before testing');
                }
            }}
            disabled={isSubmitting || isTesting}
          >
            {isTesting ? <LoaderCircle className="w-4 h-4 mr-0 animate-spin" /> : <Wifi className="w-4 h-4 mr-0" />}
            {t('agentManagement.testConnection') || 'Test Connection'}
          </Button>
        )}
        <Button variant="outline" onClick={onCancel} disabled={isSubmitting || isTesting}>{t('common.cancel')}</Button>
        </div>
      </div>
    </div>
  );
};

export default AgentConfigForm;
