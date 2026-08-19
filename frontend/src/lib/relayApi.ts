export interface RelayModel {
  id: string;
  name: string;
  provider: string;
}

export interface RelayModelsResponse {
  status: number;
  message: string;
  data: {
    models: RelayModel[];
    total: number;
    algorithms: {
      full: string;
      quick: string;
    };
  };
}

const API_BASE_URL = '/api/v1/relay';

export const relayApi = {
  // Get the built-in detectable models (from GET /api/v1/relay/models)
  async getModels(): Promise<RelayModelsResponse> {
    const response = await fetch(`${API_BASE_URL}/models`);
    return response.json();
  },
};
