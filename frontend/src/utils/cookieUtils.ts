import Cookies from 'js-cookie';

// Cookie configuration constants
export const COOKIE_CONFIG = {
  AUTH_TOKEN: 'g_t',
  EXPIRES_DAYS: 7,
  SECURE: window.location.protocol === 'https:',
  SAME_SITE: 'strict' as const,
} as const;

/**
 * Cookie utility class
 */
export class CookieUtils {
  /**
   * Set the authentication token
   */
  static setAuthToken(token: string): void {
    Cookies.set(COOKIE_CONFIG.AUTH_TOKEN, token, {
      expires: COOKIE_CONFIG.EXPIRES_DAYS,
      secure: COOKIE_CONFIG.SECURE,
      sameSite: COOKIE_CONFIG.SAME_SITE,
    });
  }

  /**
   * Get the authentication token
   */
  static getAuthToken(): string | undefined {
    return Cookies.get(COOKIE_CONFIG.AUTH_TOKEN);
  }

  /**
   * Clear the authentication token
   */
  static clearAuthToken(): void {
    Cookies.remove(COOKIE_CONFIG.AUTH_TOKEN);
  }

  /**
   * Check whether the user is authenticated
   */
  static isAuthenticated(): boolean {
    return !!this.getAuthToken();
  }

  /**
   * Get all cookies (used for debugging)
   */
  static getAllCookies(): Record<string, string> {
    return Cookies.get();
  }

  /**
   * Clear all authentication related cookies
   */
  static clearAllAuthCookies(): void {
    this.clearAuthToken();
    // Additional auth-related cookie cleanup can be added here
  }

  /**
   * Check whether the cookie is about to expire (1 day in advance)
   */
  static isTokenExpiringSoon(): boolean {
    const token = this.getAuthToken();
    if (!token) return false;

    // JWT token parsing logic can be added here to check expiration time
    // For now, return false to indicate it is not expiring soon
    return false;
  }

}
