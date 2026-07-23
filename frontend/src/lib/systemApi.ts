// AIG platform version-check related APIs

// Project Release page, used as the default fallback link
export const AIG_RELEASE_URL = 'https://github.com/Tencent/AI-Infra-Guard/releases';

export interface VersionCheckData {
  // Currently deployed version number
  current_version?: string;
  // Latest remote version number
  latest_version?: string;
  // Whether an update is available
  update_available?: boolean;
  // Release link of the latest version (fallback to AIG_RELEASE_URL when not returned)
  release_url?: string;
}

export interface SystemVersionResponse {
  status: number;
  message?: string;
  data?: VersionCheckData;
}

export const systemApi = {
  // Query whether a new platform version is available
  async checkVersion(): Promise<SystemVersionResponse> {
    const response = await fetch('/api/v1/system/version');
    if (!response.ok) {
      throw new Error(`Failed to check version: ${response.status}`);
    }
    return response.json();
  },
};
