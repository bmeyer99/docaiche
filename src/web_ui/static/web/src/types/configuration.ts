export interface ModelSettings {
  temperature: number;
  maxTokens: number;
  topP?: number;
  presencePenalty?: number;
}

export interface ProviderConfig {
  provider: 'ollama' | 'openai' | 'custom';
  baseUrl: string;
  apiKey?: string;
  model: string;
  settings: ModelSettings;
}

export interface EmbeddingProviderConfig {
  use_text_generation_config: boolean;
  provider?: 'ollama' | 'openai' | 'custom';
  baseUrl?: string;
  apiKey?: string;
  model?: string;
}

export interface SystemConfiguration {
  textGeneration: ProviderConfig;
  embedding: EmbeddingProviderConfig;
  [key: string]: any;
}

export interface TestConnectionRequest {
  provider: string;
  baseUrl: string;
  apiKey?: string;
}

export interface TestConnectionResponse {
  success: boolean;
  models?: string[];
  error?: string;
}