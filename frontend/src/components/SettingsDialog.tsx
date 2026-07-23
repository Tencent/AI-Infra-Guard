import React, { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Settings, 
  Blocks, 
  Database, 
  Globe,
  ScrollText,
  X,
  Bot,
  RefreshCw
} from 'lucide-react';
import { Dialog, DialogContent, DialogTitle } from './ui/dialog';
import { toast } from 'sonner';
import ModelManagementSettings from './management/ModelManagementDialog';
import KnowledgeBaseSettings, { KnowledgeBaseSettingsRef } from './management/KnowledgeBaseDialog';
import AgentManagementDialog from './management/AgentManagementDialog';
import LanguageSwitcher from './LanguageSwitcher';
import Changelog from './Changelog';
// The open-source build always shows the "Update data" button (used to sync the latest community fingerprint/vulnerability databases)
const showUpdateDataButton = true;

interface SettingsDialogProps {
  isOpen: boolean;
  onClose: () => void;
  initialTab?: 'plugins' | 'models' | 'agents' | 'language' | 'changelog';
}

const SettingsDialog = ({ isOpen, onClose, initialTab = 'plugins' }: SettingsDialogProps) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState(initialTab);
  const [changelogVersion, setChangelogVersion] = useState<string>('');
  const [updating, setUpdating] = useState(false);
  const knowledgeBaseRef = useRef<KnowledgeBaseSettingsRef>(null);

  // Update data: POST triggers async sync → poll GET for the final result, then refresh jailbreak eval sets, AI-app fingerprints, and the vulnerability database on success
  const handleUpdateData = async () => {
    if (updating) return;
    setUpdating(true);

    const POLL_INTERVAL = 2000; // Polling interval: 2 seconds
    const POLL_TIMEOUT = 5 * 60 * 1000; // Polling timeout: 5 minutes

    const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

    try {
      // 1. POST to trigger the sync
      const triggerResp = await fetch('/api/v1/system/update-data', { method: 'POST' });
      const triggerData = await triggerResp.json();
      if (triggerData.status !== 0) {
        toast.error(t('knowledgeBase.updateDataFailed'), {
          description: triggerData.message || t('knowledgeBase.updateDataFailed'),
        });
        return;
      }

      // 2. Poll GET to query sync progress
      const startTs = Date.now();
      let finalData: any = triggerData.data;
      let finalStatus = triggerData.status;
      let finalMessage = triggerData.message;

      // If the trigger already reports completion (running=false), use it directly; otherwise start polling
      while (finalData?.running) {
        if (Date.now() - startTs > POLL_TIMEOUT) {
          toast.error(t('knowledgeBase.updateDataFailed'), {
            description: t('knowledgeBase.updateDataTimeout'),
          });
          return;
        }
        await sleep(POLL_INTERVAL);
        const pollResp = await fetch('/api/v1/system/update-data');
        const pollData = await pollResp.json();
        finalStatus = pollData.status;
        finalMessage = pollData.message;
        finalData = pollData.data;
      }

      // 3. Display the final result
      const success = finalStatus === 0 && finalData?.success !== false;
      if (success) {
        const filesUpdated = finalData?.files_updated ?? 0;
        if (filesUpdated === 0) {
          toast.success(t('knowledgeBase.updateDataSuccess'), {
            description: t('knowledgeBase.dataAlreadyUpToDate'),
          });
        } else {
          toast.success(t('knowledgeBase.updateDataSuccess'), {
            description: t('knowledgeBase.filesUpdatedCount', { count: filesUpdated }),
          });
        }
        // Re-fetch jailbreak eval sets, AI-app fingerprints, and the vulnerability database
        knowledgeBaseRef.current?.refreshAll();
      } else {
        toast.error(t('knowledgeBase.updateDataFailed'), {
          description: finalData?.message || finalMessage || t('knowledgeBase.updateDataFailed'),
        });
      }
    } catch (error) {
      toast.error(t('knowledgeBase.updateDataFailed'), {
        description: t('knowledgeBase.updateDataFailed'),
      });
    } finally {
      setUpdating(false);
    }
  };

  React.useEffect(() => {
    if (isOpen) {
      setActiveTab(initialTab);
    }
  }, [isOpen, initialTab]);

  React.useEffect(() => {
    if (activeTab !== 'changelog') {
        setChangelogVersion('');
    }
  }, [activeTab]);

  const handleVersionLoaded = React.useCallback((version: string) => {
    setChangelogVersion(version);
  }, []);

  const menuItems = [
    { id: 'models', icon: Database, label: t('task.modelConfig') },
    { id: 'agents', icon: Bot, label: t('task.agentConfig') },
    { id: 'plugins', icon: Blocks, label: t('task.pluginManagement') },
    { id: 'language', icon: Globe, label: t('language.switch') || 'Language' },
    { id: 'changelog', icon: ScrollText, label: t('common.changelog') || 'Changelog' },
  ];

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-[1000px] w-[90vw] h-[80vh] p-0 flex overflow-hidden gap-0">
            {/* Sidebar */}
            <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col">
                <div className="p-4 border-b border-gray-200 flex items-center gap-2">
                    <Settings className="w-5 h-5 text-gray-500" />
                    <DialogTitle className="font-semibold text-gray-700 text-base">{t('common.settings') || 'Settings'}</DialogTitle>
                </div>
                <div className="p-2 flex-1 overflow-y-auto">
                    {menuItems.map(item => (
                        <button
                            key={item.id}
                            onClick={() => setActiveTab(item.id as any)}
                            className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors mb-1 ${
                                activeTab === item.id 
                                    ? 'bg-white text-blue-600 shadow-sm font-medium' 
                                    : 'text-gray-600 hover:bg-gray-200/50'
                            }`}
                        >
                            <item.icon className="w-4 h-4" />
                            {item.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 flex flex-col min-w-0 bg-white">
                 <div className="flex justify-between items-center p-4 border-b border-gray-200 h-[57px]">
                    <h2 className="text-lg font-medium flex items-center gap-3">
                        {menuItems.find(i => i.id === activeTab)?.label}
                        {activeTab === 'changelog' && changelogVersion && (
                            <span className="text-sm font-normal text-gray-500 bg-blue-100 px-2 py-1 rounded-full">
                                {changelogVersion}
                            </span>
                        )}
                        {activeTab === 'plugins' && showUpdateDataButton && (
                            <button
                                type="button"
                                onClick={handleUpdateData}
                                disabled={updating}
                                className="flex items-center gap-1 ml-2 text-sm font-normal text-blue-600 hover:text-blue-700 disabled:text-blue-400 disabled:cursor-not-allowed transition-colors"
                            >
                                <RefreshCw className={`w-4 h-4 ${updating ? 'animate-spin' : ''}`} />
                                {updating ? t('knowledgeBase.updatingData') : t('knowledgeBase.updateData')}
                            </button>
                        )}
                    </h2>
                </div>
                <div className="flex-1 overflow-hidden relative flex flex-col">
                    {activeTab === 'plugins' && <KnowledgeBaseSettings ref={knowledgeBaseRef} />}
                    {activeTab === 'models' && <ModelManagementSettings />}
                    {activeTab === 'agents' && <AgentManagementDialog />}
                    {activeTab === 'language' && (
                        <div className="p-6 flex flex-col items-center justify-center h-full">
                            <h3 className="text-lg font-medium text-gray-700 mb-6">{t('language.select')}</h3>
                             <div className="scale-150">
                                <LanguageSwitcher />
                             </div>
                        </div>
                    )}
                    {activeTab === 'changelog' && (
                        <Changelog 
                            onVersionLoaded={handleVersionLoaded}
                        />
                    )}
                </div>
            </div>
        </DialogContent>
    </Dialog>
  );
};

export default SettingsDialog;
