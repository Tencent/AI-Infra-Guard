import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import { LanguageStorage } from '../utils/languageStorage';

import en from './locales/en.json';
import zh from './locales/zh.json';

/**
 * Deep merge (shallow structure + inner object merge). `override` takes
 * precedence over `base`.
 */
const deepMerge = <T extends Record<string, any>>(base: T, override: Record<string, any>): T => {
  const result: any = { ...base };
  for (const key of Object.keys(override)) {
    const b = result[key];
    const o = override[key];
    if (
      b &&
      typeof b === 'object' &&
      !Array.isArray(b) &&
      o &&
      typeof o === 'object' &&
      !Array.isArray(o)
    ) {
      result[key] = deepMerge(b, o);
    } else {
      result[key] = o;
    }
  }
  return result;
};

/**
 * Private locale overrides: when private/locales/{lang}.overrides.json
 * exists at the repository root, it is collected statically by vite's
 * import.meta.glob and deep-merged into the main locale.
 * In the open-source build this directory does not exist, so the glob
 * returns an empty object.
 */
type LocaleModule = { default: Record<string, any> };
const overrideModules = import.meta.glob<LocaleModule>(
  '/private/locales/*.overrides.json',
  { eager: true },
);
const getOverride = (lang: string): Record<string, any> => {
  for (const [p, mod] of Object.entries(overrideModules)) {
    if (p.endsWith(`/${lang}.overrides.json`)) {
      return mod.default || {};
    }
  }
  return {};
};

const mergedZh = deepMerge(zh as Record<string, any>, getOverride('zh'));
const mergedEn = deepMerge(en as Record<string, any>, getOverride('en'));

const SUPPORTED_LANGUAGES = ['zh', 'en'];

const getLanguageFromUrl = () => {
  if (typeof window === 'undefined') {
    return null;
  }
  const urlLang = new URLSearchParams(window.location.search).get('lang');
  if (urlLang && SUPPORTED_LANGUAGES.includes(urlLang)) {
    return urlLang;
  }
  return null;
};

// Get the initial language setting
const getInitialLanguage = () => {
  const urlLang = getLanguageFromUrl();
  if (urlLang) {
    LanguageStorage.setLanguage(urlLang);
    return urlLang;
  }
  const sessionLang = sessionStorage.getItem('i18nextLng');
  if (sessionLang) return sessionLang;
  const localLang = localStorage.getItem('i18nextLng');
  if (localLang) return localLang;

  const browserLang = navigator.language;
  if (browserLang.startsWith('zh')) return 'zh';
  if (browserLang.startsWith('en')) return 'en';
  return 'zh';
};

const resources = {
  en: { translation: mergedEn },
  zh: { translation: mergedZh },
};

// Initialize i18n
const initPromise = i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'zh',
    lng: getInitialLanguage(),
    debug: false,
    interpolation: {
      escapeValue: false,
      prefix: '{{',
      suffix: '}}',
    },
    detection: {
      order: ['localStorage', 'sessionStorage', 'navigator'],
      caches: ['localStorage', 'sessionStorage'],
      lookupLocalStorage: 'i18nextLng',
      lookupSessionStorage: 'i18nextLng',
    },
  });

initPromise
  .then(() => {
    // i18n initialization completed
  })
  .catch(error => {
    console.error('i18n 初始化失败:', error);
  });

// Listen for language changes
i18n.on('languageChanged', (lng: string) => {
  sessionStorage.setItem('i18nextLng', lng);
  localStorage.setItem('i18nextLng', lng);
});

export { initPromise };
export default i18n;
