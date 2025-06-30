/**
 * Zod schemas for provider configuration validation
 */

import { z } from 'zod';

// URL validation pattern (currently unused but kept for future validation needs)
// const urlPattern = /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$/;

// API key patterns for different providers
const apiKeyPatterns = {
  openai: /^sk-[a-zA-Z0-9]{48}$/,
  anthropic: /^sk-ant-[a-zA-Z0-9]{90,}$/,
  openrouter: /^sk-or-[a-zA-Z0-9]{40,}$/,
  groq: /^gsk_[a-zA-Z0-9]{52}$/,
  mistral: /^mr-[a-zA-Z0-9]{32}$/,
  deepseek: /^sk-[a-zA-Z0-9]{40,}$/,
  gemini: /^AI[a-zA-Z0-9]{37}$/,
  aws: /^AKIA[a-zA-Z0-9]{16}$/,
};

// Common field validators
export const urlValidator = z.string()
  .min(1, 'URL is required')
  .refine((url) => {
    if (!url) return true; // Allow empty for optional fields
    try {
      new URL(url);
      return true;
    } catch {
      return false;
    }
  }, 'Invalid URL format')
  .refine((url) => {
    if (!url) return true;
    return url.startsWith('http://') || url.startsWith('https://');
  }, 'URL must start with http:// or https://');

export const apiKeyValidator = (provider: string) => {
  const pattern = apiKeyPatterns[provider as keyof typeof apiKeyPatterns];
  
  return z.string()
    .min(1, 'API key is required')
    .refine((key) => {
      if (!key) return true; // Allow empty for optional fields
      if (!pattern) return true; // No specific pattern for this provider
      return pattern.test(key);
    }, `Invalid ${provider} API key format`);
};

export const numberValidator = (min?: number, max?: number) => {
  let schema = z.number();
  
  if (min !== undefined) {
    schema = schema.min(min, `Value must be at least ${min}`);
  }
  
  if (max !== undefined) {
    schema = schema.max(max, `Value must be at most ${max}`);
  }
  
  return schema;
};

export const stringNumberValidator = (min?: number, max?: number) => {
  return z.string().transform((val, ctx) => {
    if (!val) return undefined;
    const parsed = Number(val);
    if (isNaN(parsed)) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Must be a valid number',
      });
      return z.NEVER;
    }
    return parsed;
  }).pipe(z.number().optional())
    .or(z.number())
    .refine((val) => {
      if (val === undefined) return true;
      if (min !== undefined && val < min) return false;
      if (max !== undefined && val > max) return false;
      return true;
    }, {
      message: min !== undefined && max !== undefined 
        ? `Value must be between ${min} and ${max}`
        : min !== undefined 
        ? `Value must be at least ${min}`
        : `Value must be at most ${max}`
    });
};

// Sanitize text input to prevent XSS
export const sanitizeText = (text: string): string => {
  return text
    .replace(/[<>]/g, '') // Remove angle brackets
    .replace(/javascript:/gi, '') // Remove javascript: protocol
    .replace(/on\w+\s*=/gi, '') // Remove event handlers
    .trim();
};

// Provider-specific configuration schemas
export const ProviderConfigSchemas = {
  ollama: z.object({
    base_url: urlValidator.optional(),
    endpoint: urlValidator.optional(), 
    timeout: stringNumberValidator(5, 300).optional(),
    timeout_seconds: stringNumberValidator(5, 300).optional(),
    max_retries: stringNumberValidator(0, 10).optional(),
    model: z.string().optional(),
    temperature: stringNumberValidator(0, 2).optional(),
    max_tokens: stringNumberValidator(1, 32000).optional(),
  }),
  
  openai: z.object({
    api_key: apiKeyValidator('openai').optional(),
    base_url: urlValidator.optional(),
    organization: z.string().transform(sanitizeText).optional(),
    max_tokens: stringNumberValidator(1, 32000).optional(),
    temperature: stringNumberValidator(0, 2).optional(),
  }),
  
  openrouter: z.object({
    api_key: apiKeyValidator('openrouter'),
    base_url: urlValidator.optional(),
    site_url: urlValidator.optional(),
    app_name: z.string().transform(sanitizeText).optional(),
  }),
  
  anthropic: z.object({
    api_key: apiKeyValidator('anthropic'),
    base_url: urlValidator.optional(),
    max_tokens: stringNumberValidator(1, 200000).optional(),
    temperature: stringNumberValidator(0, 1).optional(),
  }),
  
  groq: z.object({
    api_key: apiKeyValidator('groq'),
    base_url: urlValidator.optional(),
  }),
  
  lmstudio: z.object({
    base_url: urlValidator,
    timeout: stringNumberValidator(5, 300).optional(),
  }),
  
  mistral: z.object({
    api_key: apiKeyValidator('mistral'),
    base_url: urlValidator.optional(),
  }),
  
  deepseek: z.object({
    api_key: apiKeyValidator('deepseek'),
    base_url: urlValidator.optional(),
  }),
  
  vertex: z.object({
    vertex_json_credentials: z.string().optional().refine((val) => {
      if (!val) return true;
      try {
        const parsed = JSON.parse(val);
        return parsed.type === 'service_account';
      } catch {
        return false;
      }
    }, 'Invalid service account JSON'),
    vertex_key_file: z.string().transform(sanitizeText).optional(),
    vertex_project_id: z.string().min(1, 'Project ID is required').transform(sanitizeText),
    vertex_region: z.enum(['us-central1', 'us-east1', 'us-west1', 'europe-west1', 'asia-northeast1']),
  }),
  
  gemini: z.object({
    api_key: apiKeyValidator('gemini'),
    base_url: urlValidator.optional(),
  }),
  
  bedrock: z.object({
    aws_access_key: apiKeyValidator('aws'),
    aws_secret_key: z.string().min(1, 'AWS secret key is required'),
    aws_session_token: z.string().optional(),
    aws_region: z.enum(['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-2', 'ap-northeast-1']),
    aws_profile: z.string().transform(sanitizeText).optional(),
  }),
};

// Get schema for a specific provider
export function getProviderConfigSchema(providerId: string): z.ZodSchema | undefined {
  return ProviderConfigSchemas[providerId as keyof typeof ProviderConfigSchemas];
}

// Validate provider configuration
export function validateProviderConfig(
  providerId: string, 
  config: unknown
): { success: boolean; data?: any; errors?: z.ZodError } {
  const schema = getProviderConfigSchema(providerId);
  
  if (!schema) {
    // If no schema defined, just ensure it's an object
    if (typeof config === 'object' && config !== null) {
      return { success: true, data: config };
    }
    return { 
      success: false, 
      errors: new z.ZodError([{
        code: 'custom',
        message: 'Configuration must be an object',
        path: []
      }])
    };
  }
  
  try {
    const data = schema.parse(config);
    return { success: true, data };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return { success: false, errors: error };
    }
    return { 
      success: false, 
      errors: new z.ZodError([{
        code: 'custom',
        message: 'Validation failed',
        path: []
      }])
    };
  }
}

// Create a safe provider configuration with defaults
export function createSafeProviderConfig(
  providerId: string,
  config: unknown
): Record<string, any> {
  // If config is not an object, return empty
  if (!config || typeof config !== 'object') {
    return {};
  }
  
  const validation = validateProviderConfig(providerId, config);
  
  if (validation.success) {
    return validation.data;
  }
  
  // If validation fails, still return the config but sanitize text fields
  // This is more lenient and allows unknown fields to pass through
  const inputConfig = config as Record<string, any>;
  const sanitized: Record<string, any> = {};
  
  for (const [key, value] of Object.entries(inputConfig)) {
    if (typeof value === 'string') {
      sanitized[key] = sanitizeText(value);
    } else if (typeof value === 'number' || typeof value === 'boolean') {
      sanitized[key] = value;
    } else if (value === null || value === undefined) {
      sanitized[key] = value;
    }
    // Skip complex objects/arrays for safety
  }
  
  return sanitized;
}