import React, { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { LanguageStorage } from '../utils/languageStorage';
const SUPPORTED_LANGUAGES = ['zh', 'en'];
const LanguageQuerySync: React.FC = () => {
  const location = useLocation();
  const { i18n } = useTranslation();
  useEffect(() => {
    const queryLang = new URLSearchParams(location.search).get('lang');
    if (!queryLang || !SUPPORTED_LANGUAGES.includes(queryLang)) {
      return;
    }
    if (i18n.language === queryLang) {
      return;
    }
    LanguageStorage.setLanguage(queryLang);
    i18n.changeLanguage(queryLang);
  }, [i18n, location.search]);
  return null;
};
export default LanguageQuerySync;
