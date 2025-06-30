/**
 * Validation functions for provider settings
 */

import { z } from 'zod';
import { ProviderConfiguration } from '@/lib/config/providers';
import type { ModelSelection, ProviderSettings } from '../types';
import { 
  isModelSelection 
} from '../types';
import { 
  validateProviderConfig as validateProviderConfigSchema,
  sanitizeText,
  urlValidator,
  createSafeProviderConfig
} from './schemas';

export function validateProviderConfig(
  providerId: string,
  config: ProviderConfiguration['config']
): { isValid: boolean; errors?: string[] } {
  const validation = validateProviderConfigSchema(providerId, config);
  
  if (validation.success) {
    return { isValid: true };
  }
  
  const errors = validation.errors?.errors.map(err => {
    const field = err.path.join('.');
    return field ? `${field}: ${err.message}` : err.message;
  }) || ['Invalid configuration'];
  
  return { isValid: false, errors };
}

export function validateModelSelection(selection: unknown): selection is ModelSelection {
  return isModelSelection(selection);
}

export function validateProviderSettings(settings: Partial<ProviderSettings>): string[] {
  const errors: string[] = [];
  
  try {
    // Validate model selection
    if (settings.modelSelection) {
      if (!validateModelSelection(settings.modelSelection.textGeneration)) {
        errors.push('Invalid text generation model selection');
      }
      if (!validateModelSelection(settings.modelSelection.embeddings)) {
        errors.push('Invalid embeddings model selection');
      }
    }
    
    // Validate providers
    if (settings.providers) {
      Object.entries(settings.providers).forEach(([providerId, provider]) => {
        const validation = validateProviderConfig(providerId, provider.config);
        if (!validation.isValid && validation.errors) {
          validation.errors.forEach(error => {
            errors.push(`${provider.name}: ${error}`);
          });
        }
      });
    }
  } catch (error) {
    errors.push('Validation error: ' + (error instanceof Error ? error.message : 'Unknown error'));
  }
  
  return errors;
}

export function isValidProviderId(providerId: string): boolean {
  return typeof providerId === 'string' && providerId.length > 0 && /^[a-zA-Z0-9_-]+$/.test(providerId);
}

export function isValidFieldPath(fieldPath: string): boolean {
  return typeof fieldPath === 'string' && fieldPath.length > 0 && fieldPath.includes('.') && /^[a-zA-Z0-9._-]+$/.test(fieldPath);
}

// Validation helpers for specific field types
export function validateUrl(url: string): { isValid: boolean; error?: string } {
  try {
    urlValidator.parse(url);
    return { isValid: true };
  } catch (error) {
    if (error instanceof z.ZodError) {
      return { isValid: false, error: error.errors[0]?.message || 'Invalid URL' };
    }
    return { isValid: false, error: 'Invalid URL format' };
  }
}

export function validateApiKey(provider: string, apiKey: string): { isValid: boolean; error?: string } {
  if (!apiKey) {
    return { isValid: false, error: 'API key is required' };
  }
  
  // Basic validation - ensure it's not just whitespace
  if (!apiKey.trim()) {
    return { isValid: false, error: 'API key cannot be empty' };
  }
  
  // Provider-specific validation could be added here
  return { isValid: true };
}

export function validateNumber(value: any, min?: number, max?: number): { isValid: boolean; error?: string } {
  const num = Number(value);
  
  if (isNaN(num)) {
    return { isValid: false, error: 'Must be a valid number' };
  }
  
  if (min !== undefined && num < min) {
    return { isValid: false, error: `Value must be at least ${min}` };
  }
  
  if (max !== undefined && num > max) {
    return { isValid: false, error: `Value must be at most ${max}` };
  }
  
  return { isValid: true };
}

// Sanitization functions
export function sanitizeInput(input: string): string {
  return sanitizeText(input);
}

export function sanitizeProviderConfig(
  providerId: string,
  config: unknown
): ProviderConfiguration['config'] {
  return createSafeProviderConfig(providerId, config);
}

// Check if a value contains potentially malicious content
export function containsMaliciousContent(value: string): boolean {
  const maliciousPatterns = [
    /<script[^>]*>.*?<\/script>/gi,
    /javascript:/gi,
    /on\w+\s*=/gi,
    /<iframe[^>]*>/gi,
    /<object[^>]*>/gi,
    /<embed[^>]*>/gi,
    /\beval\s*\(/gi,
    /\bexpression\s*\(/gi
  ];
  
  return maliciousPatterns.some(pattern => pattern.test(value));
}

// Validate and sanitize all text inputs in a config object
export function sanitizeConfigObject(config: Record<string, any>): Record<string, any> {
  const sanitized: Record<string, any> = {};
  
  for (const [key, value] of Object.entries(config)) {
    if (typeof value === 'string') {
      // Check for malicious content
      if (containsMaliciousContent(value)) {
        console.warn(`Potentially malicious content detected in field '${key}'`);
        sanitized[key] = ''; // Clear malicious content
      } else {
        sanitized[key] = sanitizeText(value);
      }
    } else if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      sanitized[key] = sanitizeConfigObject(value);
    } else {
      sanitized[key] = value;
    }
  }
  
  return sanitized;
}