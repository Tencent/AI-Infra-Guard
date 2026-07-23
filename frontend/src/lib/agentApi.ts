import { ApiResponse } from '../types/model';

const KNOWLEDGE_API_BASE_URL = '/api/v1/knowledge';

export interface SaveAgentRequest {
  content: string;
}

export const agentApi = {
  // Get the Agent list
  async getAgentNames(): Promise<ApiResponse<string[]>> {
    const response = await fetch(`${KNOWLEDGE_API_BASE_URL}/agent/names`);
    return response.json();
  },

  // Get Agent details
  async getAgent(name: string): Promise<ApiResponse<string>> {
    const response = await fetch(`${KNOWLEDGE_API_BASE_URL}/agent/${name}`);
    return response.json();
  },

  // Save an Agent
  async saveAgent(name: string, content: string): Promise<ApiResponse<void>> {
    const response = await fetch(`${KNOWLEDGE_API_BASE_URL}/agent/${name}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content }),
    });
    return response.json();
  },

  // Test connection
  async testConnection(content: string): Promise<ApiResponse<void>> {
    const response = await fetch(`${KNOWLEDGE_API_BASE_URL}/agent/connect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content }),
    });
    return response.json();
  },

  // Delete an Agent
  async deleteAgent(name: string): Promise<ApiResponse<void>> {
    const response = await fetch(`${KNOWLEDGE_API_BASE_URL}/agent/${name}`, {
      method: 'DELETE',
    });
    return response.json();
  },

  // Prompt test
  async promptTest(content: string, prompt: string): Promise<ApiResponse<string>> {
    const response = await fetch(`${KNOWLEDGE_API_BASE_URL}/agent/prompt_test`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ content, prompt }),
    });
    return response.json();
  },

  // Get Agent templates
  async getTemplates(language: string = 'en'): Promise<ApiResponse<any>> {
    const response = await fetch(`${KNOWLEDGE_API_BASE_URL}/agent/template?language=${language}`);
    return response.json();
  },
};
