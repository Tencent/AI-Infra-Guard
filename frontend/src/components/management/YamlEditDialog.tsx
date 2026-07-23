import React from 'react';
import { useTranslation } from 'react-i18next';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Button } from '../ui/button';
import { Minimize, Maximize } from 'lucide-react';

interface YamlEditDialogProps {
  open: boolean;
  onClose: (open: boolean) => void;
  onSave: () => void;
  loading: boolean;
  error: string;
  yamlContent: string;
  onYamlChange: (v: string) => void;
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
  title: string;
}

const YamlEditDialog: React.FC<YamlEditDialogProps> = ({
  open,
  onClose,
  onSave,
  loading,
  error,
  yamlContent,
  onYamlChange,
  isFullscreen,
  onToggleFullscreen,
  title,
}) => {
  const { t } = useTranslation();
  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent
        className={
          isFullscreen
            ? 'fixed inset-0 w-screen h-screen max-w-none max-h-none z-50 p-0 pt-2 m-0 rounded-none shadow-none bg-white'
            : 'pt-4 max-w-2xl'
        }
        style={isFullscreen ? {transform: 'none'} : {}}
      >
        <DialogHeader>
          <div className='flex items-center'>
            <DialogTitle className='flex items-center gap-2 flex-1'>
              {title}
              <Button
                type='button'
                variant='ghost'
                className='p-2'
                onClick={onToggleFullscreen}
                style={{zIndex: 100}}
              >
                <span className='relative group'>
                  {isFullscreen ?
                    <>
                      <Minimize className='w-5 h-5' />
                      <span className='absolute left-full top-1/2 -translate-y-1/2 ml-2 px-2 py-1 text-xs text-white bg-black rounded opacity-0 group-hover:opacity-100 whitespace-nowrap'>{t('common.exitFullscreen')}</span>
                    </>
                    :
                    <>
                      <Maximize className='w-5 h-5' />
                      <span className='absolute left-full top-1/2 -translate-y-1/2 ml-2 px-2 py-1 text-xs text-white bg-black rounded opacity-0 group-hover:opacity-100 whitespace-nowrap'>{t('common.fullscreen')}</span>
                    </>
                  }
                </span>
              </Button>
            </DialogTitle>
          </div>
        </DialogHeader>
        <form
          onSubmit={e => {
            e.preventDefault();
            onSave();
          }}
          className='space-y-4'
          style={isFullscreen ? {height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column'} : {}}
        >
          <textarea
            className='w-full border rounded p-2 font-mono text-sm'
            style={isFullscreen ? {flex: 1, minHeight: 0, resize: 'none'} : {height: '18rem', resize: 'vertical'}}
            value={yamlContent}
            onChange={e => onYamlChange(e.target.value)}
            disabled={loading}
          />
          {error && <div className='text-red-500 text-sm'>{error}</div>}
          <div className='flex gap-2'>
            <Button type='submit' disabled={loading}>
              {t('common.save')}
            </Button>
            <Button
              variant='outline'
              type='button'
              onClick={() => onClose(false)}
              disabled={loading}
            >
              {t('common.cancel')}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export default YamlEditDialog; 