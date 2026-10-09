export interface Model {
  model: string;
  token: string;
  base_url: string;
  note: string;
  limit?: number;
  /** 随每次模型请求发送的额外请求头，值在读取接口里是掩码 */
  extra_headers?: Record<string, string>;
  /** 合并进请求体的额外字段，支持 provider.order 这类点号路径 */
  extra_body?: Record<string, unknown>;
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