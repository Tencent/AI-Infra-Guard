// User related APIs
export interface UserInfo {
  username: string;
  isWhitelisted: boolean;
}

// Get the value of the given field from cookies
const getCookieValue = (name: string): string | null => {
  try {
    // Method 1: parse document.cookie directly
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      const cookieValue = parts.pop()?.split(';').shift();
      if (cookieValue) {
        return decodeURIComponent(cookieValue);
      }
    }

    // Method 2: fall back to a looser match if method 1 failed
    const allCookies = document.cookie.split(';');
    for (let cookie of allCookies) {
      const [cookieName, cookieValue] = cookie.trim().split('=');
      if (cookieName === name && cookieValue) {
        return decodeURIComponent(cookieValue);
      }
    }

    return null;
  } catch (error) {
    console.error(`获取cookie ${name} 时出错:`, error);
    return null;
  }
};

// Get the current user info (read from cookies)
export const getUserInfo = (): UserInfo => {
  try {
    // Read the t_user field from cookies
    const username = getCookieValue('t_user');

    // Temporary forced test: when the username is not available, force it to 'zonashi' for testing
    const testUsername = username || 'zonashi';

    if (!testUsername) {
      // Return default values when the t_user cookie is not found
      return {
        username: 'unknown',
        isWhitelisted: false,
      };
    }

    // Anyone can try the product
    const shouldFillPrompt = true;

    return {
      username: testUsername,
      isWhitelisted: shouldFillPrompt,
    };
  } catch (error) {
    console.error('获取用户信息失败:', error);
    // Return default values indicating the user is not on the whitelist
    return {
      username: 'unknown',
      isWhitelisted: false,
    };
  }
};
