import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { LanguageStorage } from '../utils/languageStorage';

export const useLanguage = () => {
  const { i18n } = useTranslation();
  const [currentLanguage, setCurrentLanguage] = useState<string>(i18n.language);

  // Initialize language setting
  useEffect(() => {
    // Get the saved language setting
    const savedLanguage = LanguageStorage.getRecommendedLanguage();

    // Switch when the i18n language differs from the saved one
    if (savedLanguage !== i18n.language) {
      i18n.changeLanguage(savedLanguage);
    }

    // Update the current language state
    setCurrentLanguage(i18n.language);
  }, []); // Run only once on mount

  // Listen for i18n language changes
  useEffect(() => {
    const handleLanguageChanged = (lng: string) => {
      setCurrentLanguage(lng);
    };

    // Register the language-change listener
    i18n.on('languageChanged', handleLanguageChanged);

    return () => {
      // Clean up the listener
      i18n.off('languageChanged', handleLanguageChanged);
    };
  }, [i18n]);

  // Switch language
  const changeLanguage = useCallback((lng: string) => {
    // Persist the language setting via LanguageStorage
    LanguageStorage.setLanguage(lng);
    // Switch the language
    i18n.changeLanguage(lng);
  }, [i18n]);

  // Get the current language
  const getCurrentLanguage = useCallback(() => {
    return currentLanguage;
  }, [currentLanguage]);

  // Check whether the current language is Chinese
  const isChinese = useCallback(() => {
    return currentLanguage === 'zh';
  }, [currentLanguage]);

  // Check whether the current language is English
  const isEnglish = useCallback(() => {
    return currentLanguage === 'en';
  }, [currentLanguage]);

  // Reset the language setting
  const resetLanguage = useCallback(() => {
    LanguageStorage.clearLanguage();
    const defaultLang = 'zh';
    i18n.changeLanguage(defaultLang);
  }, [i18n]);

  return {
    currentLanguage,
    changeLanguage,
    getCurrentLanguage,
    isChinese,
    isEnglish,
    resetLanguage,
  };
}; 