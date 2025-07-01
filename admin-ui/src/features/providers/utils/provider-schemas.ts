import { z } from 'zod'

// Custom URL validator that only allows http/https
const httpUrlSchema = z.string().url().refine(
  (url) => url.startsWith('http://') || url.startsWith('https://'),
  { message: 'URL must start with http:// or https://' }
)

// Base schema for common fields
const baseConfigSchema = z.object({
  timeout: z.number().min(1).max(300).optional(),
  maxRetries: z.number().min(0).max(10).optional()
})

// Provider-specific schemas
const providerSchemas = {
  // Local providers
  ollama: z.object({
    baseUrl: httpUrlSchema.default('http://localhost:11434/api')
  }).merge(baseConfigSchema),
  
  lmstudio: z.object({
    baseUrl: httpUrlSchema.default('http://localhost:1234')
  }).merge(baseConfigSchema),
  
  // Cloud providers
  openai: z.object({
    apiKey: z.string().min(1, 'API key is required'),
    organizationId: z.string().optional(),
    baseUrl: httpUrlSchema.optional()
  }).merge(baseConfigSchema),
  
  anthropic: z.object({
    apiKey: z.string().min(1, 'API key is required'),
    baseUrl: httpUrlSchema.optional()
  }).merge(baseConfigSchema),
  
  groq: z.object({
    apiKey: z.string().min(1, 'API key is required'),
    baseUrl: httpUrlSchema.optional()
  }).merge(baseConfigSchema),
  
  mistral: z.object({
    apiKey: z.string().min(1, 'API key is required'),
    baseUrl: httpUrlSchema.optional()
  }).merge(baseConfigSchema),
  
  deepseek: z.object({
    apiKey: z.string().min(1, 'API key is required'),
    baseUrl: httpUrlSchema.optional()
  }).merge(baseConfigSchema),
  
  openrouter: z.object({
    apiKey: z.string().min(1, 'API key is required'),
    baseUrl: httpUrlSchema.optional(),
    siteUrl: z.string().url().optional(),
    siteName: z.string().optional()
  }).merge(baseConfigSchema),
  
  xai: z.object({
    apiKey: z.string().min(1, 'API key is required'),
    baseUrl: httpUrlSchema.optional()
  }).merge(baseConfigSchema),
  
  // Enterprise providers
  vertex: z.object({
    projectId: z.string().min(1, 'Project ID is required'),
    region: z.string().min(1, 'Region is required'),
    serviceAccountKey: z.string().optional()
  }).merge(baseConfigSchema),
  
  bedrock: z.object({
    region: z.string().min(1, 'Region is required'),
    accessKeyId: z.string().optional(),
    secretAccessKey: z.string().optional()
  }).merge(baseConfigSchema),
  
  gemini: z.object({
    apiKey: z.string().min(1, 'API key is required'),
    baseUrl: httpUrlSchema.optional()
  }).merge(baseConfigSchema)
} as const

// Get schema for a specific provider
export function getProviderSchema(providerId: string) {
  return providerSchemas[providerId as keyof typeof providerSchemas] || baseConfigSchema
}

// Get default values for a provider
export function getProviderDefaults(providerId: string): Record<string, any> {
  const defaults: Record<string, any> = {
    timeout: 30,
    maxRetries: 3
  }
  
  // Provider-specific defaults
  switch (providerId) {
    case 'ollama':
      defaults.baseUrl = 'http://localhost:11434/api'
      break
    case 'lmstudio':
      defaults.baseUrl = 'http://localhost:1234'
      break
    case 'openrouter':
      defaults.baseUrl = 'https://openrouter.ai/api/v1'
      break
    case 'vertex':
      defaults.region = 'us-central1'
      break
    case 'bedrock':
      defaults.region = 'us-east-1'
      break
  }
  
  return defaults
}

// Get field metadata for dynamic form rendering
export function getProviderFields(providerId: string) {
  const commonFields = [
    {
      name: 'timeout',
      label: 'Timeout (seconds)',
      type: 'number',
      placeholder: '30',
      description: 'Maximum time to wait for a response'
    },
    {
      name: 'maxRetries',
      label: 'Max Retries',
      type: 'number',
      placeholder: '3',
      description: 'Number of retry attempts on failure'
    }
  ]
  
  const providerFields: Record<string, any[]> = {
    // Local providers
    ollama: [
      {
        name: 'baseUrl',
        label: 'Base URL',
        type: 'text',
        placeholder: 'http://localhost:11434/api',
        description: 'Ollama server URL'
      }
    ],
    lmstudio: [
      {
        name: 'baseUrl',
        label: 'Base URL',
        type: 'text',
        placeholder: 'http://localhost:1234',
        description: 'LM Studio server URL'
      }
    ],
    
    // Cloud providers
    openai: [
      {
        name: 'apiKey',
        label: 'API Key',
        type: 'password',
        placeholder: 'sk-...',
        description: 'Your OpenAI API key',
        required: true
      },
      {
        name: 'organizationId',
        label: 'Organization ID',
        type: 'text',
        placeholder: 'org-...',
        description: 'Optional organization ID'
      },
      {
        name: 'baseUrl',
        label: 'Base URL (Optional)',
        type: 'text',
        placeholder: 'https://api.openai.com/v1',
        description: 'Custom API endpoint'
      }
    ],
    
    anthropic: [
      {
        name: 'apiKey',
        label: 'API Key',
        type: 'password',
        placeholder: 'sk-ant-...',
        description: 'Your Anthropic API key',
        required: true
      },
      {
        name: 'baseUrl',
        label: 'Base URL (Optional)',
        type: 'text',
        placeholder: 'https://api.anthropic.com',
        description: 'Custom API endpoint'
      }
    ],
    
    groq: [
      {
        name: 'apiKey',
        label: 'API Key',
        type: 'password',
        placeholder: 'gsk_...',
        description: 'Your Groq API key',
        required: true
      }
    ],
    
    mistral: [
      {
        name: 'apiKey',
        label: 'API Key',
        type: 'password',
        placeholder: 'API key',
        description: 'Your Mistral API key',
        required: true
      }
    ],
    
    deepseek: [
      {
        name: 'apiKey',
        label: 'API Key',
        type: 'password',
        placeholder: 'API key',
        description: 'Your Deepseek API key',
        required: true
      }
    ],
    
    openrouter: [
      {
        name: 'apiKey',
        label: 'API Key',
        type: 'password',
        placeholder: 'sk-or-...',
        description: 'Your OpenRouter API key',
        required: true
      },
      {
        name: 'siteUrl',
        label: 'Site URL',
        type: 'text',
        placeholder: 'https://myapp.com',
        description: 'Your application URL for OpenRouter'
      },
      {
        name: 'siteName',
        label: 'Site Name',
        type: 'text',
        placeholder: 'My App',
        description: 'Your application name for OpenRouter'
      }
    ],
    
    xai: [
      {
        name: 'apiKey',
        label: 'API Key',
        type: 'password',
        placeholder: 'API key',
        description: 'Your xAI API key',
        required: true
      }
    ],
    
    // Enterprise providers
    vertex: [
      {
        name: 'projectId',
        label: 'Project ID',
        type: 'text',
        placeholder: 'my-project-id',
        description: 'Google Cloud project ID',
        required: true
      },
      {
        name: 'region',
        label: 'Region',
        type: 'text',
        placeholder: 'us-central1',
        description: 'Google Cloud region',
        required: true
      },
      {
        name: 'serviceAccountKey',
        label: 'Service Account Key (Optional)',
        type: 'textarea',
        placeholder: 'Paste JSON key here',
        description: 'Service account JSON key for authentication'
      }
    ],
    
    bedrock: [
      {
        name: 'region',
        label: 'AWS Region',
        type: 'text',
        placeholder: 'us-east-1',
        description: 'AWS region for Bedrock',
        required: true
      },
      {
        name: 'accessKeyId',
        label: 'Access Key ID (Optional)',
        type: 'text',
        placeholder: 'AKIA...',
        description: 'AWS access key ID'
      },
      {
        name: 'secretAccessKey',
        label: 'Secret Access Key (Optional)',
        type: 'password',
        placeholder: 'Secret key',
        description: 'AWS secret access key'
      }
    ],
    
    gemini: [
      {
        name: 'apiKey',
        label: 'API Key',
        type: 'password',
        placeholder: 'API key',
        description: 'Your Google Gemini API key',
        required: true
      }
    ]
  }
  
  const fields = providerFields[providerId] || []
  return [...fields, ...commonFields]
}