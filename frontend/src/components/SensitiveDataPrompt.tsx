import React, { useState } from 'react';
import { ShieldAlert, X } from 'lucide-react';
import { useTranslation, Trans } from 'react-i18next';
import { sensitiveContact } from '@/config/privateModules';

const SensitiveDataPrompt: React.FC = () => {
  const { t } = useTranslation();
  const [isVisible, setIsVisible] = useState(true);
  if (!isVisible) {
    return null;
  }
  // The open-source build does not display sensitive-data contacts by default (sensitiveContact is null)
  if (!sensitiveContact) {
    return null;
  }
  return (
    <div className='bg-white rounded-lg shadow-lg border border-gray-200 p-4 w-96 relative'>
      <button
        onClick={() => setIsVisible(false)}
        className='absolute top-3 right-3 text-gray-400 hover:text-gray-600 transition-colors'
        aria-label={t('common.close')}
      >
        <X className='w-4 h-4' />
      </button>
      <div className='flex items-center space-x-3'>
        <div className='flex-1'>
          <p className='text-sm font-medium text-gray-900 mb-1 flex items-center'>
            <ShieldAlert className='w-4 h-4 text-yellow-500 mr-1' />
            {t('sensitivePrompt.title')}
          </p>
          <p className='text-xs text-gray-600 leading-relaxed'>
            <Trans
              i18nKey={sensitiveContact.i18nKey}
              components={[
                <a
                  key='link'
                  href={sensitiveContact.href}
                  className='text-blue-600 hover:underline cursor-pointer'
                />
              ]}
            />
          </p>
        </div>
      </div>
    </div>
  );
};
export default SensitiveDataPrompt;
