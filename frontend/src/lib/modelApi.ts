import { 
  ModelItem, 
  CreateModelRequest, 
  UpdateModelRequest, 
  DeleteModelRequest, 
  ApiResponse 
} from '../types/model';

const API_BASE_URL = '/api/v1/app';

export const modelApi = {
  // Get the model list
  async getModels(): Promise<ApiResponse<ModelItem[]>> {
    const response = await fetch(`${API_BASE_URL}/models`);
    return response.json();
  },

  // Get model details
  async getModel(modelId: string): Promise<ApiResponse<ModelItem>> {
    const response = await fetch(`${API_BASE_URL}/models/${modelId}`);
    return response.json();
  },

  // Create a model
  async createModel(data: CreateModelRequest): Promise<ApiResponse<null>> {
    const response = await fetch(`${API_BASE_URL}/models`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return response.json();
  },

  // Update a model
  async updateModel(modelId: string, data: UpdateModelRequest): Promise<ApiResponse<null>> {
    const response = await fetch(`${API_BASE_URL}/models/${modelId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return response.json();
  },

  // Delete models
  async deleteModels(data: DeleteModelRequest): Promise<ApiResponse<null>> {
    const response = await fetch(`${API_BASE_URL}/models`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });
    return response.json();
  },
}; 