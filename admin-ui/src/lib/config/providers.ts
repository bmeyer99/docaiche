/**
 * AI Provider Definitions for Docaiche Admin Interface
 * 
 * This file contains all supported AI/LLM provider configurations
 * based on the Roo_api providers analysis.
 */

import { designTokens } from '../design-system/tokens';

// Provider Categories
export type ProviderCategory = 'local' | 'cloud' | 'enterprise';

// Provider Configuration Interface
export interface ProviderDefinition {
  id: string;
  name: string;
  displayName: string;
  category: ProviderCategory;
  icon: string;
  color: string;
  description: string;
  defaultBaseUrl: string;
  requiresApiKey: boolean;
  supportsEmbedding: boolean;
  supportsChat: boolean;
  configFields: ProviderConfigField[];
  modelTypes: ('text' | 'embedding')[];
  documentation?: string;
}

export interface ProviderConfigField {
  key: string;
  label: string;
  type: 'text' | 'password' | 'url' | 'number' | 'select' | 'textarea';
  required: boolean;
  placeholder?: string;
  description?: string;
  options?: { value: string; label: string }[];
  validation?: {
    min?: number;
    max?: number;
    pattern?: string;
  };
}

// AI Provider Definitions
export const AI_PROVIDERS: Record<string, ProviderDefinition> = {
  ollama: {
    id: 'ollama',
    name: 'ollama',
    displayName: 'Ollama',
    category: 'local',
    icon: '🦙',
    color: designTokens.colors.provider.ollama,
    description: 'Local LLM inference server with support for multiple models',
    defaultBaseUrl: 'http://localhost:11434/api',
    requiresApiKey: false,
    supportsEmbedding: true,
    supportsChat: true,
    modelTypes: ['text', 'embedding'],
    configFields: [
      {
        key: 'base_url',
        label: 'Base URL',
        type: 'url',
        required: true,
        placeholder: 'http://localhost:11434/api',
        description: 'Ollama server API endpoint'
      },
      {
        key: 'timeout',
        label: 'Timeout (seconds)',
        type: 'number',
        required: false,
        placeholder: '30',
        description: 'Request timeout in seconds',
        validation: { min: 5, max: 300 }
      },
      {
        key: 'max_retries',
        label: 'Max Retries',
        type: 'number',
        required: false,
        placeholder: '3',
        description: 'Maximum retry attempts',
        validation: { min: 0, max: 10 }
      }
    ],
    documentation: 'https://ollama.ai/docs'
  },

  openai: {
    id: 'openai',
    name: 'openai',
    displayName: 'OpenAI',
    category: 'cloud',
    icon: '🤖',
    color: designTokens.colors.provider.openai,
    description: 'OpenAI GPT models and embeddings',
    defaultBaseUrl: 'https://api.openai.com/v1',
    requiresApiKey: true,
    supportsEmbedding: true,
    supportsChat: true,
    modelTypes: ['text', 'embedding'],
    configFields: [
      {
        key: 'api_key',
        label: 'API Key',
        type: 'password',
        required: true,
        placeholder: 'sk-...',
        description: 'OpenAI API key from platform.openai.com'
      },
      {
        key: 'base_url',
        label: 'Base URL',
        type: 'url',
        required: false,
        placeholder: 'https://api.openai.com/v1',
        description: 'API endpoint (default: https://api.openai.com/v1)'
      },
      {
        key: 'organization',
        label: 'Organization ID',
        type: 'text',
        required: false,
        placeholder: 'org-...',
        description: 'OpenAI organization ID (optional)'
      },
      {
        key: 'max_tokens',
        label: 'Max Tokens',
        type: 'number',
        required: false,
        placeholder: '4096',
        description: 'Maximum tokens in response',
        validation: { min: 1, max: 32000 }
      },
      {
        key: 'temperature',
        label: 'Temperature',
        type: 'number',
        required: false,
        placeholder: '0.7',
        description: 'Response creativity (0.0 - 2.0)',
        validation: { min: 0, max: 2 }
      }
    ],
    documentation: 'https://platform.openai.com/docs'
  },

  openrouter: {
    id: 'openrouter',
    name: 'openrouter',
    displayName: 'OpenRouter',
    category: 'cloud',
    icon: '🔗',
    color: designTokens.colors.provider.openrouter,
    description: 'Access to multiple LLM providers through one API',
    defaultBaseUrl: 'https://openrouter.ai/api/v1',
    requiresApiKey: true,
    supportsEmbedding: false,
    supportsChat: true,
    modelTypes: ['text'],
    configFields: [
      {
        key: 'api_key',
        label: 'API Key',
        type: 'password',
        required: true,
        placeholder: 'sk-or-...',
        description: 'OpenRouter API key from openrouter.ai'
      },
      {
        key: 'base_url',
        label: 'Base URL',
        type: 'url',
        required: false,
        placeholder: 'https://openrouter.ai/api/v1',
        description: 'API endpoint (default: https://openrouter.ai/api/v1)'
      },
      {
        key: 'site_url',
        label: 'Site URL',
        type: 'url',
        required: false,
        placeholder: 'https://yoursite.com',
        description: 'Your site URL for analytics'
      },
      {
        key: 'app_name',
        label: 'App Name',
        type: 'text',
        required: false,
        placeholder: 'Docaiche Admin',
        description: 'Application name for analytics'
      }
    ],
    documentation: 'https://openrouter.ai/docs'
  },

  anthropic: {
    id: 'anthropic',
    name: 'anthropic',
    displayName: 'Anthropic Claude',
    category: 'cloud',
    icon: '🧠',
    color: designTokens.colors.provider.anthropic,
    description: 'Anthropic Claude models for advanced reasoning',
    defaultBaseUrl: 'https://api.anthropic.com',
    requiresApiKey: true,
    supportsEmbedding: false,
    supportsChat: true,
    modelTypes: ['text'],
    configFields: [
      {
        key: 'api_key',
        label: 'API Key',
        type: 'password',
        required: true,
        placeholder: 'sk-ant-...',
        description: 'Anthropic API key from console.anthropic.com'
      },
      {
        key: 'base_url',
        label: 'Base URL',
        type: 'url',
        required: false,
        placeholder: 'https://api.anthropic.com',
        description: 'API endpoint (default: https://api.anthropic.com)'
      },
      {
        key: 'max_tokens',
        label: 'Max Tokens',
        type: 'number',
        required: false,
        placeholder: '4096',
        description: 'Maximum tokens in response',
        validation: { min: 1, max: 200000 }
      },
      {
        key: 'temperature',
        label: 'Temperature',
        type: 'number',
        required: false,
        placeholder: '0.7',
        description: 'Response creativity (0.0 - 1.0)',
        validation: { min: 0, max: 1 }
      }
    ],
    documentation: 'https://docs.anthropic.com'
  },

  groq: {
    id: 'groq',
    name: 'groq',
    displayName: 'Groq',
    category: 'cloud',
    icon: '⚡',
    color: '#f97316',
    description: 'Ultra-fast LLM inference with Groq chips',
    defaultBaseUrl: 'https://api.groq.com/openai/v1',
    requiresApiKey: true,
    supportsEmbedding: false,
    supportsChat: true,
    modelTypes: ['text'],
    configFields: [
      {
        key: 'api_key',
        label: 'API Key',
        type: 'password',
        required: true,
        placeholder: 'gsk_...',
        description: 'Groq API key from console.groq.com'
      },
      {
        key: 'base_url',
        label: 'Base URL',
        type: 'url',
        required: false,
        placeholder: 'https://api.groq.com/openai/v1',
        description: 'API endpoint (default: https://api.groq.com/openai/v1)'
      }
    ],
    documentation: 'https://console.groq.com/docs'
  },

  lmstudio: {
    id: 'lmstudio',
    name: 'lmstudio',
    displayName: 'LM Studio',
    category: 'local',
    icon: '🖥️',
    color: '#8b5cf6',
    description: 'Local LLM inference with LM Studio',
    defaultBaseUrl: 'http://localhost:1234/v1',
    requiresApiKey: false,
    supportsEmbedding: true,
    supportsChat: true,
    modelTypes: ['text', 'embedding'],
    configFields: [
      {
        key: 'base_url',
        label: 'Base URL',
        type: 'url',
        required: true,
        placeholder: 'http://localhost:1234/v1',
        description: 'LM Studio server API endpoint'
      },
      {
        key: 'timeout',
        label: 'Timeout (seconds)',
        type: 'number',
        required: false,
        placeholder: '60',
        description: 'Request timeout in seconds',
        validation: { min: 5, max: 300 }
      }
    ],
    documentation: 'https://lmstudio.ai/docs'
  },

  mistral: {
    id: 'mistral',
    name: 'mistral',
    displayName: 'Mistral AI',
    category: 'cloud',
    icon: '🌪️',
    color: '#ef4444',
    description: 'Mistral AI models for efficient inference',
    defaultBaseUrl: 'https://api.mistral.ai/v1',
    requiresApiKey: true,
    supportsEmbedding: true,
    supportsChat: true,
    modelTypes: ['text', 'embedding'],
    configFields: [
      {
        key: 'api_key',
        label: 'API Key',
        type: 'password',
        required: true,
        placeholder: 'mr-...',
        description: 'Mistral API key from console.mistral.ai'
      },
      {
        key: 'base_url',
        label: 'Base URL',
        type: 'url',
        required: false,
        placeholder: 'https://api.mistral.ai/v1',
        description: 'API endpoint (default: https://api.mistral.ai/v1)'
      }
    ],
    documentation: 'https://docs.mistral.ai'
  }
};

// Helper functions
export const getProvidersByCategory = (category: ProviderCategory): ProviderDefinition[] => {
  return Object.values(AI_PROVIDERS).filter(provider => provider.category === category);
};

export const getProvidersWithEmbedding = (): ProviderDefinition[] => {
  return Object.values(AI_PROVIDERS).filter(provider => provider.supportsEmbedding);
};

export const getProvidersWithChat = (): ProviderDefinition[] => {
  return Object.values(AI_PROVIDERS).filter(provider => provider.supportsChat);
};

export const getProviderById = (id: string): ProviderDefinition | undefined => {
  return AI_PROVIDERS[id];
};

// Default provider configurations
export const DEFAULT_PROVIDER_CONFIGS = {
  text_provider: 'ollama',
  embedding_provider: 'ollama',
  use_same_provider: true
} as const;

// Provider status types
export type ProviderStatus = 'connected' | 'disconnected' | 'testing' | 'error';

export interface ProviderConnectionResult {
  status: ProviderStatus;
  message: string;
  models?: string[];
  latency?: number;
  error?: string;
}

// Runtime provider configuration
export interface ProviderConfiguration {
  id: string;
  providerId: string;
  name: string;
  enabled: boolean;
  config: Record<string, string | number | boolean>;
  status: ProviderStatus;
  lastTested?: string;
  models?: string[];
}