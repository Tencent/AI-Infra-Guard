import React from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from './ui/button';
import { Globe } from 'lucide-react';
import { useLanguage } from '../hooks/useLanguage';

const LanguageSwitcher: React.FC = () => {
  const { t } = useTranslation();
  const { currentLanguage, changeLanguage } = useLanguage();

  const handleLanguageToggle = () => {
    const newLanguage = currentLanguage === 'zh' ? 'en' : 'zh';
    changeLanguage(newLanguage);
  };

  return (
    <Button 
      variant="ghost" 
      size="sm" 
      className="flex items-center gap-1 text-blue-600 hover:text-blue-900 hover:bg-transparent border-none shadow-none px-3 focus:outline-none focus-visible:ring-0"
      onClick={handleLanguageToggle}
    >
      <Globe className="h-4 w-4" />
      {currentLanguage === 'zh' ? t('language.chinese') : t('language.english')}
    </Button>
  );
};

export default LanguageSwitcher; 