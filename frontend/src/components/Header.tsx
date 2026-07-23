import React from 'react';
import { ArrowLeft } from 'lucide-react';
import { Button } from './ui/button';
import { useTranslation } from  'react-i18next';

interface HeaderProps {
  showBackButton?: boolean;
  backButtonText?: string;
  onBackClick?: () => void;
  backButtonLeftSlot?: React.ReactNode;
}

const Header: React.FC<HeaderProps> = ({
  showBackButton = true,
  backButtonText,
  onBackClick,
  backButtonLeftSlot,
}) => {
  const { t } = useTranslation();
  const baseUrl = import.meta.env.BASE_URL || '/';
  const logoSrc = `${baseUrl.replace(/\/$/, '')}/images/logo.png`;
  const defaultBackButtonText = t('help.backToHome');
  const handleBackClick = () => {
    if (onBackClick) {
      onBackClick();
    } else {
      window.location.href = '/';
    }
  };

  return (
    <div className="bg-white border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <button
            type='button'
            className='flex items-center focus:outline-none'
            style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
            onClick={() => { window.location.href = '/'; }}
          >
            <img src={logoSrc} alt='A.I.G' className='w-7 h-7 mr-3 relative' style={{ top: '2px' }} />
            <h1 className='text-lg font-semibold text-gray-900'>
              <span
                className='font-[tencentSans] text-2xl text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-purple-600'
                style={{ fontFamily: 'tencentSans', letterSpacing: '0.1em' }}
              >A.I.G</span>
            </h1>
          </button>
          <div className='flex items-center gap-2'>
            {backButtonLeftSlot}
            {showBackButton && (
              <Button
                variant='outline'
                size='sm'
                onClick={handleBackClick}
                className='text-gray-600 hover:text-gray-900 gap-1'
              >
                <ArrowLeft className='w-4 h-4' />
                {backButtonText || defaultBackButtonText}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Header; 