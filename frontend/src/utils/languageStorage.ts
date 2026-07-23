const LANGUAGE_STORAGE_KEY = 'i18nextLng';

/**
 * Language storage management utility
 */
export class LanguageStorage {
  /**
   * Get the saved language setting
   * @returns Language code, defaults to 'zh'
   */
  static getLanguage(): string {
    // Prefer sessionStorage
    const sessionLang = sessionStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (sessionLang) {
      return sessionLang;
    }

    // Fall back to localStorage
    const localLang = localStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (localLang) {
      return localLang;
    }

    // Default to Chinese
    return 'zh';
  }

  /**
   * Save the language setting
   * @param language Language code
   */
  static setLanguage(language: string): void {
    // Persist to both sessionStorage and localStorage
    sessionStorage.setItem(LANGUAGE_STORAGE_KEY, language);
    localStorage.setItem(LANGUAGE_STORAGE_KEY, language);
  }

  /**
   * Clear the language setting
   */
  static clearLanguage(): void {
    sessionStorage.removeItem(LANGUAGE_STORAGE_KEY);
    localStorage.removeItem(LANGUAGE_STORAGE_KEY);
  }

  /**
   * Check whether a language setting has been saved
   * @returns Whether a language setting exists
   */
  static hasLanguage(): boolean {
    return !!(sessionStorage.getItem(LANGUAGE_STORAGE_KEY) || localStorage.getItem(LANGUAGE_STORAGE_KEY));
  }

  /**
   * Get the browser default language
   * @returns Browser language code
   */
  static getBrowserLanguage(): string {
    const browserLang = navigator.language;
    if (browserLang.startsWith('zh')) {
      return 'zh';
    }
    if (browserLang.startsWith('en')) {
      return 'en';
    }
    return 'zh'; // Default to Chinese
  }

  /**
   * Get the recommended language setting
   * @returns Recommended language code
   */
  static getRecommendedLanguage(): string {
    // If a saved setting exists, use it
    if (this.hasLanguage()) {
      return this.getLanguage();
    }

    // Otherwise, use the browser language
    return this.getBrowserLanguage();
  }
} 