import React, { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import Joyride, { CallBackProps, STATUS, Step, ACTIONS } from 'react-joyride';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../ui/alert-dialog';
import { 
  Plus, 
  Edit, 
  Trash2, 
  Settings,
  Check, 
  LoaderCircle 
} from 'lucide-react';
import { Button, buttonVariants } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { modelApi } from '../../lib/modelApi';
import { ModelItem, Model } from '../../types/model';
import { protectDefaultModel } from '../../config/privateModules';
import { maskToken } from '../../utils/tokenUtils';
import { joyrideStyles, getJoyrideLocale } from '../../config/joyrideConfig';

const ModelManagementSettings: React.FC = () => {
  const { t } = useTranslation();
  const [models, setModels] = useState<ModelItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingModel, setEditingModel] = useState<ModelItem | null>(null);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [formData, setFormData] = useState({
    model_id: '',
    model: {
      model: '',
      token: '',
      base_url: '',
      note: '',
      limit: 10 as number | string,
    },
  });
  const [errors, setErrors] = useState({
    model: '',
    general: '',
  });
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [modelsToDelete, setModelsToDelete] = useState<string[]>([]);
  const [runModelManagementTour, setRunModelManagementTour] = useState(false);

  // Function that generates a unique ID
  const generateUniqueId = () => {
    return `model_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  };

  useEffect(() => {
    loadModels();
  }, []);

  useEffect(() => {
    console.log('deleteConfirmOpen状态变化:', deleteConfirmOpen);
  }, [deleteConfirmOpen]);

  const loadModels = async () => {
    setLoading(true);
    try {
      const response = await modelApi.getModels();
      if (response.status === 0) {
        // Filter out data without a 'model' property to ensure data integrity
        const validModels = (response.data || []).filter(
          (model) => model && model.model_id && model.model
        );
        setModels(validModels);
        return validModels;
      } else {
        console.error('API返回错误状态:', response.message);
        return [];
      }
    } catch (error) {
      console.error('加载模型列表失败:', error);
      return [];
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    // Clear the previous error
    setErrors({
      model: '',
      general: '',
    });
    
    // Validate the form data
    const newErrors = {
      model: '',
      general: '',
    };
    
    if (!formData.model.model) {
      newErrors.model = t('modelManagement.enterModelName');
    }
    
    if (newErrors.model) {
      setErrors(newErrors);
      return;
    }
    
    setLoading(true);
    try {
      // Prepare the payload and make sure 'limit' is a number
      const submitData = {
        ...formData.model,
        limit: (() => {
          const limitValue = formData.model.limit;
          // Check whether 'limit' is empty
          if (limitValue === '' || limitValue === null || limitValue === undefined) {
            return 10; // Default values
          }
          const numValue = Number(limitValue);
          return isNaN(numValue) ? 10 : numValue;
        })(),
      };
      
      let response;
      if (editingModel) {
        response = await modelApi.updateModel(editingModel.model_id, {
          model: submitData,
        });
      } else {
        // Automatically generate a unique ID when creating
        const newModelData = {
          model_id: generateUniqueId(),
          model: submitData,
        };
        response = await modelApi.createModel(newModelData);
      }
      
      // Check the API response
      if (response.status === 0) {
        await loadModels();
        resetForm();
      } else {
        setErrors({
          ...newErrors,
          general: response.message || t('modelManagement.operationFailed'),
        });
      }
    } catch (error) {
      console.error('保存模型失败:', error);
      setErrors({
        ...newErrors,
        general: error instanceof Error ? error.message : t('modelManagement.networkError'),
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    console.log('删除按钮被点击，当前选中的模型:', selectedModels);
    
    if (selectedModels.length === 0) {
      console.log('没有选中的模型，无法删除');
      toast.error(t('modelManagement.noModelSelected'));
      return;
    }
    
    // Whether the default model is protected is controlled by the private overlay (no such restriction in the open-source build)
    if (protectDefaultModel) {
      const firstModel = models[0];
      const isFirstModelProtected = firstModel && 
        (!firstModel.model?.token || firstModel.model.token === '');
      const hasProtectedModel = isFirstModelProtected && 
        selectedModels.includes(firstModel.model_id);
      
      if (hasProtectedModel) {
        toast.error(t('modelManagement.defaultModelNotAllowed'));
        return;
      }
    }
    
    console.log('准备删除模型:', selectedModels);
    setModelsToDelete(selectedModels);
    setDeleteConfirmOpen(true);
    console.log('确认框状态已设置为打开');
  };

  const confirmDelete = async () => {
    if (modelsToDelete.length === 0) return;
    
    setLoading(true);
    try {
      const response = await modelApi.deleteModels({ model_ids: modelsToDelete });
      
      if (response.status === 0) {
        const newModels = await loadModels();
        setSelectedModels([]);
        toast.success(t('modelManagement.modelDeleteSuccess'));
      } else {
        console.error('删除失败:', response.message);
        toast.error(response.message || t('modelManagement.deleteFailed'));
      }
    } catch (error) {
      console.error('删除模型失败:', error);
      toast.error(t('modelManagement.modelDeleteFailed'));
    } finally {
      setLoading(false);
      setDeleteConfirmOpen(false);
      setModelsToDelete([]);
    }
  };

  const resetForm = () => {
    setFormData({
      model_id: '',
      model: {
        model: '',
        token: '',
        base_url: '',
        note: '',
        limit: 10,
      },
    });
    setErrors({
      model: '',
      general: '',
    });
    setEditingModel(null);
    setShowForm(false);
  };

  const handleEdit = (model: ModelItem) => {
    setEditingModel(model);
    setFormData({
      model_id: model.model_id,
      model: { 
        model: model.model?.model || '',
        token: model.model?.token || '',
        base_url: model.model?.base_url || '',
        note: model.model?.note || '',
        limit: model.model?.limit || 10,
      },
    });
    setShowForm(true);
  };

  const handleAdd = () => {
    resetForm();
    setShowForm(true);
    // Delay starting the tour to ensure the form has rendered
    const hasSeenModelManagementTour = localStorage.getItem('hasSeenModelManagementTour');
    if (!hasSeenModelManagementTour) {
      setTimeout(() => {
        let attemptCount = 0;
        const maxAttempts = 100;
        const checkAndStartTour = () => {
          attemptCount = attemptCount + 1;
          const addButton = document.querySelector('[data-joyride="model-management-add-button"]');
          const modelNameInput = document.querySelector('[data-joyride="model-management-model-name"]');
          const apiKeyInput = document.querySelector('[data-joyride="model-management-api-key"]');
          const baseUrlInput = document.querySelector('[data-joyride="model-management-base-url"]');
          const limitInput = document.querySelector('[data-joyride="model-management-limit"]');
          const noteInput = document.querySelector('[data-joyride="model-management-note"]');
          const saveButton = document.querySelector('[data-joyride="model-management-save-button"]');
          const hasAllElements = addButton && modelNameInput && apiKeyInput && baseUrlInput && limitInput && noteInput && saveButton;
          if (hasAllElements || attemptCount >= maxAttempts) {
            if (hasAllElements) {
              setRunModelManagementTour(true);
            }
          } else {
            requestAnimationFrame(checkAndStartTour);
          }
        };
        requestAnimationFrame(checkAndStartTour);
      }, 500);
    }
  };

  const toggleModelSelection = (modelId: string) => {
    setSelectedModels(prev => 
      prev.includes(modelId) 
        ? prev.filter(id => id !== modelId)
        : [...prev, modelId]
    );
  };

  // Configure the model-management onboarding tour steps
  const getModelManagementTourSteps = (): Step[] => {
    const steps: Step[] = [];
    steps.push({
      target: '[data-joyride="model-management-add-button"]',
      content: t('modelManagement.tour.addButton'),
      placement: 'top',
      disableBeacon: true,
    });
    steps.push({
      target: '[data-joyride="model-management-model-name"]',
      content: t('modelManagement.modelNamePlaceholder'),
      placement: 'top',
      disableBeacon: true,
    });
    steps.push({
      target: '[data-joyride="model-management-api-key"]',
      content: t('modelManagement.apiKeyPlaceholder'),
      placement: 'top',
      disableBeacon: true,
    });
    steps.push({
      target: '[data-joyride="model-management-base-url"]',
      content: t('modelManagement.baseUrlPlaceholder'),
      placement: 'top',
      disableBeacon: true,
    });
    steps.push({
      target: '[data-joyride="model-management-limit"]',
      content: t('modelManagement.tour.concurrencyLimit'),
      placement: 'top',
      disableBeacon: true,
    });
    steps.push({
      target: '[data-joyride="model-management-note"]',
      content: t('modelManagement.tour.note'),
      placement: 'top',
      disableBeacon: true,
    });
    steps.push({
      target: '[data-joyride="model-management-save-button"]',
      content: t('modelManagement.tour.saveButton'),
      placement: 'top',
      disableBeacon: true,
    });
    return steps;
  };

  // Handle the model-management onboarding tour callback
  const handleModelManagementJoyrideCallback = (data: CallBackProps) => {
    const { status, action } = data;
    if (
      status === STATUS.FINISHED || 
      status === STATUS.SKIPPED || 
      action === ACTIONS.CLOSE ||
      action === ACTIONS.SKIP
    ) {
      setRunModelManagementTour(false);
      localStorage.setItem('hasSeenModelManagementTour', 'true');
    }
  };

  return (
    <div className="w-full h-full flex flex-col relative">
      {/* Model-management onboarding tour */}
      <Joyride
        steps={getModelManagementTourSteps()}
        run={runModelManagementTour}
        continuous={true}
        showProgress={true}
        showSkipButton={true}
        callback={handleModelManagementJoyrideCallback}
        styles={{
          ...joyrideStyles,
          options: {
            ...joyrideStyles.options,
            zIndex: 10000000,
          },
        }}
        locale={getJoyrideLocale(t)}
      />
      <div className="flex-1 flex overflow-hidden">
        {/* Left-hand model list */}
        <div className="w-1/2 border-r border-gray-200 p-4 flex flex-col">
          <div className="flex items-center justify-between mb-4 flex-shrink-0">
            <h3 className="font-medium">
              {t('modelManagement.modelList')} 
              {selectedModels.length > 0 && (
                <span className="text-sm text-blue-600 ml-2">
                  ({t('modelManagement.selectedCount', { count: selectedModels.length })})
                </span>
              )}
            </h3>
            <div className="flex space-x-1">
              <Button 
                size="sm" 
                className="gap-0"
                onClick={handleAdd}
                disabled={loading}
                data-joyride="model-management-add-button"
              >
                <Plus className="w-4 h-4" />
                {t('modelManagement.add')}
              </Button>
              {selectedModels.length > 0 && (
                <Button 
                  size="sm" 
                  className="gap-0"
                  variant="destructive"
                  onClick={handleDelete}
                  disabled={loading}
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  {t('modelManagement.delete')}
                </Button>
              )}
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <LoaderCircle className="w-6 h-6 animate-spin" />
            </div>
          ) : (
            <div className="space-y-2 overflow-y-auto scrollbar-hover flex-1">

              {models.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  <p>{t('modelManagement.noModelData')}</p>
                </div>
              ) : (
                  models.map((model, index) => {
                    const isFirstModel = index === 0;
                    const isTokenEmpty = !model.model?.token || model.model.token === '';
                    const shouldDisable = protectDefaultModel && isFirstModel && isTokenEmpty;
                    
                    return (
                    <div
                      key={model.model_id}
                      className={`p-3 border rounded-lg transition-colors ${
                        shouldDisable
                          ? 'border-gray-200 bg-gray-50 cursor-not-allowed'
                          : selectedModels.includes(model.model_id)
                          ? 'border-blue-500 bg-blue-50 cursor-pointer'
                          : 'border-gray-200 hover:border-gray-300 cursor-pointer'
                      }`}
                      onClick={(e) => {
                        // In non-open-source environments, do not allow selecting the first model when its token is empty
                        if (shouldDisable) return;
                        // Do not toggle selection when the click target is a checkbox or its parent
                        if (e.target instanceof HTMLInputElement && e.target.type === 'checkbox') {
                          return;
                        }
                        // Do not toggle selection when the click target is the edit button
                        if ((e.target as HTMLElement).closest('button')) {
                          return;
                        }
                        console.log('点击模型项，切换选择状态:', model.model_id);
                        toggleModelSelection(model.model_id);
                      }}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center">
                            <input
                              type="checkbox"
                              checked={selectedModels.includes(model.model_id)}
                              onChange={(e) => {
                                e.stopPropagation();
                                // In non-open-source environments, do not allow selecting the first model when its token is empty
                                if (shouldDisable) return;
                                console.log('checkbox状态改变，切换选择状态:', model.model_id);
                                toggleModelSelection(model.model_id);
                              }}
                              disabled={shouldDisable}
                              className="mr-2"
                            />
                            <h4 className="font-medium text-sm">
                              {model.model?.model || t('modelManagement.unknownModel')}
                            </h4>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            {model.model?.base_url || t('modelManagement.noBaseUrl')}
                          </p>
                          {model.model?.token && (
                            <p className="text-xs text-gray-500 mt-1">
                              Token: {maskToken(model.model.token)}
                            </p>
                          )}
                          {model.model?.note && (
                            <p className="text-xs text-gray-400 mt-1">
                              {model.model.note}
                            </p>
                          )}
                        </div>
                        {shouldDisable ? (
                          <div className="text-xs text-gray-400 px-2 py-1 bg-gray-100 rounded">
                            {t('modelManagement.defaultModel')}
                          </div>
                        ) : (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleEdit(model);
                            }}
                          >
                            <Edit className="w-4 h-4" />
                          </Button>
                        )}
                      </div>
                    </div>
                    );
                  })
                )}
              </div>
            )}
          </div>

          {/* Right-hand form */}
          <div
            className='w-1/2 p-4 h-full overflow-y-auto scrollbar-hover'
          >
            {showForm ? (
              <div>
                <h3 className="font-medium mb-4">
                  {editingModel ? t('modelManagement.editModel') : t('modelManagement.addModel')}
                </h3>
                <div className="space-y-4">
                  {errors.general && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                      <p className="text-red-600 text-sm">{errors.general}</p>
                    </div>
                  )}
                  
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      {t('modelManagement.modelNameRequired')}
                    </label>
                    <Input
                      value={formData.model?.model || ''}
                      onChange={(e) => {
                        setFormData(prev => ({
                          ...prev,
                          model: {
                            ...prev.model,
                            model: e.target.value,
                          },
                        }));
                        if (errors.model) {
                          setErrors(prev => ({ ...prev, model: '' }));
                        }
                      }}
                      placeholder={t('modelManagement.modelNamePlaceholder')}
                      required
                      className={errors.model ? 'border-red-500' : ''}
                      data-joyride="model-management-model-name"
                    />
                    {errors.model && (
                      <p className="text-red-500 text-xs mt-1">{errors.model}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      {t('modelManagement.apiKeyRequired')}
                    </label>
                    <Input
                      type="password"
                      value={formData.model?.token || ''}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        model: {
                          ...prev.model,
                          token: e.target.value,
                        },
                      }))}
                      placeholder={t('modelManagement.apiKeyPlaceholder')}
                      data-joyride="model-management-api-key"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      {t('modelManagement.baseUrlRequired')}
                    </label>
                    <Input
                      value={formData.model?.base_url || ''}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        model: {
                          ...prev.model,
                          base_url: e.target.value,
                        },
                      }))}
                      placeholder={t('modelManagement.baseUrlPlaceholder')}
                      data-joyride="model-management-base-url"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      {t('modelManagement.concurrencyLimit')}
                    </label>
                    <Input
                      type="number"
                      value={formData.model?.limit || ''}
                      onChange={(e) => {
                        const value = e.target.value;
                        setFormData(prev => ({
                          ...prev,
                          model: {
                            ...prev.model,
                            limit: value === '' ? '' : parseInt(value) || '',
                          },
                        }));
                      }}
                      placeholder={t('modelManagement.concurrencyLimitPlaceholder')}
                      data-joyride="model-management-limit"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium mb-1">
                      {t('modelManagement.note')}
                    </label>
                    <Textarea
                      value={formData.model?.note || ''}
                      onChange={(e) => setFormData(prev => ({
                        ...prev,
                        model: {
                          ...prev.model,
                          note: e.target.value,
                        },
                      }))}
                      placeholder={t('modelManagement.notePlaceholder')}
                      rows={3}
                      data-joyride="model-management-note"
                    />
                  </div>

                  <div className="flex space-x-2 pt-4">
                    <Button
                      onClick={handleSubmit}
                      disabled={loading}
                      className="flex-1"
                      data-joyride="model-management-save-button"
                    >
                      {loading ? (
                        <LoaderCircle className="w-4 h-4 mr-2 animate-spin" />
                      ) : (
                        <Check className="w-4 h-4 mr-2" />
                      )}
                      {t('modelManagement.save')}
                    </Button>
                    <Button
                      variant="outline"
                      onClick={resetForm}
                      disabled={loading}
                    >
                      {t('modelManagement.cancel')}
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <Settings className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>{t('modelManagement.selectModelToEdit')}</p>
                </div>
              </div>
            )}
          </div>
        </div>
      {/* Delete confirmation dialog */}
      <AlertDialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('modelManagement.confirmDelete')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('modelManagement.confirmDeleteMessage', { count: modelsToDelete.length })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={loading}>{t('modelManagement.cancel')}</AlertDialogCancel>
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
                t('modelManagement.delete')
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default ModelManagementSettings; 