export interface GuidedScanDraft {
  scenario: string;
  purpose: string;
  targetUrl: string;
  modelId?: string;
  agentId?: string;
  headers: { key: string; value: string }[];
  files: File[];
  plugins: string[];
  strategies: string[];
}

export interface ScenarioNeeds {
  model?: boolean;
  purpose?: boolean;
  url?: boolean;
  code?: boolean;
  agent?: boolean;
  any?: string[];
}

export interface CatalogScenario {
  id: string;
  name: string;
  name_en: string;
  description: string;
  description_en: string;
  needs: ScenarioNeeds;
  plugins?: string[];
  strategies?: string[];
}

export interface CatalogCheck {
  id: string;
  name: string;
  name_en: string;
  severity: string;
  kind: string;
}

export interface CatalogStrategy {
  id: string;
  name: string;
  name_en: string;
}

export type RunStatus = 'running' | 'done' | 'error' | 'terminated';
