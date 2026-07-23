import { EvaluationListResponse } from '../types';

const API_BASE_URL = '/api/v1/knowledge';

export const evaluationApi = {
  // Get the evaluation set list
  async getEvaluations(params?: {
    page?: number;
    size?: number;
    q?: string;
  }): Promise<EvaluationListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.append('page', params.page.toString());
    if (params?.size) searchParams.append('size', params.size.toString());
    if (params?.q) searchParams.append('q', params.q);
    
    const url = `${API_BASE_URL}/evaluations${searchParams.toString() ? `?${searchParams.toString()}` : ''}`;
    const response = await fetch(url);
    return response.json();
  },

}; 