/**
 * AI Provider Definitions for Docaiche Admin Interface
 * 
 * This file contains all supported AI/LLM provider configurations
 * based on the Roo_api providers analysis.
 */

import { designTokens } from '../design-system/tokens';

// Provider Categories
export type ProviderCategory = 'local' | 'cloud' | 'enterprise';

// Provider Configuration (runtime state)
export interface ProviderConfiguration {
  id: string;
  providerId: string;
  name: string;
  enabled: boolean;
  config: Record<string, any>;
  status: 'connected' | 'disconnected' | 'error' | 'available';
  lastTested?: string | null;
  models?: string[];
}

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
        required: false,
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
        required: false,
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
  },

  deepseek: {
    id: 'deepseek',
    name: 'deepseek',
    displayName: 'DeepSeek',
    category: 'cloud',
    icon: '🔍',
    color: '#1e40af',
    description: 'DeepSeek AI models for code and reasoning',
    defaultBaseUrl: 'https://api.deepseek.com/v1',
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
        placeholder: 'sk-...',
        description: 'DeepSeek API key from platform.deepseek.com'
      },
      {
        key: 'base_url',
        label: 'Base URL',
        type: 'url',
        required: false,
        placeholder: 'https://api.deepseek.com/v1',
        description: 'API endpoint (default: https://api.deepseek.com/v1)'
      }
    ],
    documentation: 'https://platform.deepseek.com/docs'
  },

  vertex: {
    id: 'vertex',
    name: 'vertex',
    displayName: 'Google Vertex AI',
    category: 'enterprise',
    icon: '🔺',
    color: '#4285f4',
    description: 'Google Cloud Vertex AI with enterprise security',
    defaultBaseUrl: '',
    requiresApiKey: false,
    supportsEmbedding: true,
    supportsChat: true,
    modelTypes: ['text', 'embedding'],
    configFields: [
      {
        key: 'vertex_json_credentials',
        label: 'JSON Credentials',
        type: 'textarea',
        required: false,
        placeholder: '{"type": "service_account", ...}',
        description: 'Google Cloud service account JSON credentials'
      },
      {
        key: 'vertex_key_file',
        label: 'Key File Path',
        type: 'text',
        required: false,
        placeholder: '/path/to/service-account-key.json',
        description: 'Path to Google Cloud service account key file'
      },
      {
        key: 'vertex_project_id',
        label: 'Project ID',
        type: 'text',
        required: true,
        placeholder: 'my-gcp-project',
        description: 'Google Cloud project ID'
      },
      {
        key: 'vertex_region',
        label: 'Region',
        type: 'select',
        required: true,
        placeholder: 'us-central1',
        description: 'Google Cloud region for Vertex AI',
        options: [
          { value: 'us-central1', label: 'US Central 1' },
          { value: 'us-east1', label: 'US East 1' },
          { value: 'us-west1', label: 'US West 1' },
          { value: 'europe-west1', label: 'Europe West 1' },
          { value: 'asia-northeast1', label: 'Asia Northeast 1' }
        ]
      }
    ],
    documentation: 'https://cloud.google.com/vertex-ai/docs'
  },

  gemini: {
    id: 'gemini',
    name: 'gemini',
    displayName: 'Google Gemini',
    category: 'enterprise',
    icon: '💎',
    color: '#34a853',
    description: 'Google Gemini models for multimodal AI',
    defaultBaseUrl: 'https://generativelanguage.googleapis.com/v1beta',
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
        placeholder: 'AI...',
        description: 'Google Gemini API key from ai.google.dev'
      },
      {
        key: 'base_url',
        label: 'Base URL',
        type: 'url',
        required: false,
        placeholder: 'https://generativelanguage.googleapis.com/v1beta',
        description: 'API endpoint (leave empty for default)'
      }
    ],
    documentation: 'https://ai.google.dev/docs'
  },

  bedrock: {
    id: 'bedrock',
    name: 'bedrock',
    displayName: 'AWS Bedrock',
    category: 'enterprise',
    icon: '🪨',
    color: '#ff9900',
    description: 'AWS Bedrock with enterprise-grade AI models',
    defaultBaseUrl: '',
    requiresApiKey: false,
    supportsEmbedding: true,
    supportsChat: true,
    modelTypes: ['text', 'embedding'],
    configFields: [
      {
        key: 'aws_access_key',
        label: 'AWS Access Key',
        type: 'password',
        required: true,
        placeholder: 'AKIA...',
        description: 'AWS access key ID'
      },
      {
        key: 'aws_secret_key',
        label: 'AWS Secret Key',
        type: 'password',
        required: true,
        placeholder: 'Your AWS secret access key',
        description: 'AWS secret access key'
      },
      {
        key: 'aws_session_token',
        label: 'AWS Session Token',
        type: 'password',
        required: false,
        placeholder: 'Optional session token',
        description: 'AWS session token (optional, for temporary credentials)'
      },
      {
        key: 'aws_region',
        label: 'AWS Region',
        type: 'select',
        required: true,
        placeholder: 'us-east-1',
        description: 'AWS region where Bedrock is available',
        options: [
          { value: 'us-east-1', label: 'US East (N. Virginia)' },
          { value: 'us-west-2', label: 'US West (Oregon)' },
          { value: 'eu-west-1', label: 'Europe (Ireland)' },
          { value: 'ap-southeast-2', label: 'Asia Pacific (Sydney)' },
          { value: 'ap-northeast-1', label: 'Asia Pacific (Tokyo)' }
        ]
      },
      {
        key: 'aws_profile',
        label: 'AWS Profile',
        type: 'text',
        required: false,
        placeholder: 'default',
        description: 'AWS profile name (alternative to access keys)'
      }
    ],
    documentation: 'https://docs.aws.amazon.com/bedrock/'
  },

  // claudecode: {
  //   id: 'claudecode',
  //   name: 'claudecode',
  //   displayName: 'Claude Code',
  //   category: 'local',
  //   icon: '💻',
  //   color: '#ff6b35',
  //   description: 'Local Claude Code CLI for development assistance',
  //   defaultBaseUrl: '',
  //   requiresApiKey: false,
  //   supportsEmbedding: false,
  //   supportsChat: true,
  //   modelTypes: ['text'],
  //   configFields: [
  //     {
  //       key: 'claude_code_path',
  //       label: 'Claude Code Path',
  //       type: 'text',
  //       required: true,
  //       placeholder: '/usr/local/bin/claude',
  //       description: 'Path to Claude Code CLI executable'
  //     },
  //     {
  //       key: 'timeout',
  //       label: 'Timeout (seconds)',
  //       type: 'number',
  //       required: false,
  //       placeholder: '30',
  //       description: 'Request timeout in seconds',
  //       validation: { min: 5, max: 300 }
  //     }
  //   ],
  //   documentation: 'https://docs.anthropic.com/en/docs/claude-code'
  // },

  // geminicli: {
  //   id: 'geminicli',
  //   name: 'geminicli',
  //   displayName: 'Gemini CLI',
  //   category: 'local',
  //   icon: '⚡',
  //   color: '#4285f4',
  //   description: 'Local Gemini CLI for terminal-based AI assistance',
  //   defaultBaseUrl: '',
  //   requiresApiKey: true,
  //   supportsEmbedding: false,
  //   supportsChat: true,
  //   modelTypes: ['text'],
  //   configFields: [
  //     {
  //       key: 'api_key',
  //       label: 'Gemini API Key',
  //       type: 'password',
  //       required: true,
  //       placeholder: 'AI...',
  //       description: 'Google Gemini API key from ai.google.dev'
  //     },
  //     {
  //       key: 'gemini_cli_path',
  //       label: 'Gemini CLI Path',
  //       type: 'text',
  //       required: false,
  //       placeholder: '/usr/local/bin/gemini',
  //       description: 'Path to Gemini CLI executable (auto-detected if empty)'
  //     },
  //     {
  //       key: 'max_requests_per_minute',
  //       label: 'Max Requests/Minute',
  //       type: 'number',
  //       required: false,
  //       placeholder: '60',
  //       description: 'Rate limit for API requests (free tier: 60/min)',
  //       validation: { min: 1, max: 1000 }
  //     },
  //     {
  //       key: 'timeout',
  //       label: 'Timeout (seconds)',
  //       type: 'number',
  //       required: false,
  //       placeholder: '30',
  //       description: 'Request timeout in seconds',
  //       validation: { min: 5, max: 300 }
  //     }
  //   ],
  //   documentation: 'https://developers.google.com/gemini-code-assist/docs/gemini-cli'
  // }
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