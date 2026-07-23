import React from 'react';
import { useTranslation } from 'react-i18next';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Download, Upload, HelpCircle } from 'lucide-react';

interface YamlUploadDialogProps {
  open: boolean;
  onClose: (open: boolean) => void;
  onUpload: (file: File) => void;
  loading: boolean;
  error: string;
  onDownloadSample: () => void;
  title: string;
  type?: 'mcp' | 'vulnerability' | 'fingerprint';
}

const YamlUploadDialog: React.FC<YamlUploadDialogProps> = ({
  open,
  onClose,
  onUpload,
  loading,
  error,
  onDownloadSample,
  title,
  type,
}) => {
  const { t } = useTranslation();
  const [fileInputRef] = React.useState(React.createRef<HTMLInputElement>());

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.name.endsWith('.yaml') && !file.name.endsWith('.yml')) {
      return;
    }

    onUpload(file);
    
    // Clear the file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Show different instructions based on the title
  const isVulnerability = type === 'vulnerability' || (!type && title.includes('漏洞'));
  const isMCP = type === 'mcp' || (!type && (title.includes('MCP') || title.includes('插件')));
  
  const description = isMCP 
    ? t('knowledgeBase.yamlUpload.description.mcp')
    : isVulnerability 
      ? t('knowledgeBase.yamlUpload.description.vulnerability')
      : t('knowledgeBase.yamlUpload.description.fingerprint');
  
  const formatRequirements = isMCP ? [
    t('knowledgeBase.yamlUpload.requirements.mcp.info'),
    t('knowledgeBase.yamlUpload.requirements.mcp.promptTemplate'),
  ] : isVulnerability ? [
    t('knowledgeBase.yamlUpload.requirements.vulnerability.info'),
    t('knowledgeBase.yamlUpload.requirements.vulnerability.rule'),
    t('knowledgeBase.yamlUpload.requirements.vulnerability.references'),
    t('knowledgeBase.yamlUpload.requirements.vulnerability.cvss'),
    t('knowledgeBase.yamlUpload.requirements.vulnerability.securityAdvice'),
  ] : [
    t('knowledgeBase.yamlUpload.requirements.fingerprint.info'),
    t('knowledgeBase.yamlUpload.requirements.fingerprint.http'),
    t('knowledgeBase.yamlUpload.requirements.fingerprint.version'),
    t('knowledgeBase.yamlUpload.requirements.fingerprint.metadata'),
  ];

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className='max-w-md'>
        <DialogHeader>
          <div className='flex items-center gap-2'>
            <DialogTitle>{title}</DialogTitle>
            <a
              href='/help'
              target='_blank'
              rel='noopener noreferrer'
              className='text-gray-500 hover:text-gray-700 transition-colors'
              title={t('knowledgeBase.yamlUpload.viewHelp')}
            >
              <HelpCircle className='w-4 h-4' />
            </a>
          </div>
        </DialogHeader>
        <div className='space-y-4'>
          <div className='text-sm text-gray-600'>
            {description}
          </div>
          <div className='space-y-3'>
            <Button onClick={onDownloadSample} variant='outline' className='w-full'>
              <Download className='w-4 h-4 mr-2' />
              {t('knowledgeBase.yamlUpload.downloadSample')}
            </Button>
            <div className='relative'>
              <input
                ref={fileInputRef}
                type='file'
                accept='.yaml,.yml'
                onChange={handleFileUpload}
                className='hidden'
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
                className='w-full'
              >
                <Upload className='w-4 h-4 mr-2' />
                {loading ? t('knowledgeBase.yamlUpload.uploading') : t('knowledgeBase.yamlUpload.uploadButton')}
              </Button>
            </div>
          </div>
          {error && (
            <div className='text-red-500 text-sm bg-red-50 p-3 rounded-md'>{error}</div>
          )}
          <div className='text-xs text-gray-500'>
            <p>{t('knowledgeBase.yamlUpload.formatRequirements')}</p>
            <ul className='list-disc list-inside mt-1 space-y-1'>
              {formatRequirements.map((requirement, index) => (
                <li key={index}>{requirement}</li>
              ))}
            </ul>
          </div>
          <div className='flex gap-2'>
            <Button
              variant='outline'
              onClick={() => onClose(false)}
              disabled={loading}
              className='flex-1'
            >
              {t('knowledgeBase.yamlUpload.cancel')}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default YamlUploadDialog;
