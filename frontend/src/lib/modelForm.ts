import type { ApiResponse, CreateModelRequest, Model, UpdateModelRequest } from '../types/model';

interface ModelFormApi {
  createModel(data: CreateModelRequest): Promise<ApiResponse<null>>;
  updateModel(modelId: string, data: UpdateModelRequest): Promise<ApiResponse<null>>;
}

interface ModelFormInput {
  mode: 'create' | 'update';
  modelId: string;
  model: Omit<Model, 'limit' | 'extra_headers' | 'extra_body'> & { limit?: number | string };
  extraHeadersText: string;
  extraBodyText: string;
}

interface ModelFormMessages {
  invalidJson: string;
  invalidHeaderValue: (key: string) => string;
}

export class ModelFormValidationError extends Error {}

// Blank text explicitly clears the option; nonblank text must be a JSON object.
function parseJsonObject(text: string, errorMessage: string): Record<string, unknown> {
  if (!text.trim()) return {};
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch {
    // Do not include potentially sensitive JSON contents in errors.
    throw new ModelFormValidationError(errorMessage);
  }
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new ModelFormValidationError(errorMessage);
  }
  return parsed as Record<string, unknown>;
}

// Both create and update must validate before reaching the API.
export async function saveModelForm(
  api: ModelFormApi,
  input: ModelFormInput,
  messages: ModelFormMessages,
): Promise<ApiResponse<null>> {
  const parsedHeaders = parseJsonObject(input.extraHeadersText, messages.invalidJson);
  const headerEntries: [string, string][] = [];
  for (const [key, value] of Object.entries(parsedHeaders)) {
    if (typeof value !== 'string') {
      throw new ModelFormValidationError(messages.invalidHeaderValue(key));
    }
    headerEntries.push([key, value]);
  }

  const extraBody = parseJsonObject(input.extraBodyText, messages.invalidJson);
  const limit = input.model.limit;
  const model: Model = {
    ...input.model,
    extra_headers: Object.fromEntries(headerEntries),
    extra_body: extraBody,
    limit: limit === '' || limit == null || isNaN(Number(limit)) ? 10 : Number(limit),
  };

  return input.mode === 'update'
    ? api.updateModel(input.modelId, { model })
    : api.createModel({ model_id: input.modelId, model });
}
