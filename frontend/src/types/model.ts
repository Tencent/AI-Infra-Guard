export interface Model {
  model: string;
  token: string;
  base_url: string;
  note: string;
  limit?: number;
}

export interface ModelItem {
  model_id: string;
  model: Model;
  default?: string[] | string;
}

export interface CreateModelRequest {
  model_id: string;
  model: Model;
}

export interface UpdateModelRequest {
  model: Model;
}

export interface DeleteModelRequest {
  model_ids: string[];
}

export interface ApiResponse<T = any> {
  status?: number;
  code?: number;
  message?: string;
  msg?: string;
  data: T;
} 