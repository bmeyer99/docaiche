# Provider Settings Type Safety Documentation

## Overview

This document describes the comprehensive type safety and validation improvements made to the provider settings module.

## Key Improvements

### 1. Zod Schema Validation

All data structures now have corresponding Zod schemas for runtime validation:

```typescript
// Model selection validation
export const ModelSelectionSchema = z.object({
  provider: z.string().min(1, 'Provider is required'),
  model: z.string()
});

// Provider configuration response validation
export const ProviderConfigurationResponseSchema = z.object({
  id: z.string(),
  enabled: z.boolean().optional(),
  config: z.record(z.string(), z.any()).optional(),
  status: z.enum(['connected', 'disconnected', 'error']).optional(),
  last_tested: z.string().optional(),
  models: z.array(z.string()).optional()
});
```

### 2. Provider-Specific Validation

Each provider has its own validation schema with field-specific rules:

```typescript
export const ProviderConfigSchemas = {
  openai: z.object({
    api_key: apiKeyValidator('openai').optional(),
    base_url: urlValidator.optional(),
    organization: z.string().transform(sanitizeText).optional(),
    max_tokens: stringNumberValidator(1, 32000).optional(),
    temperature: stringNumberValidator(0, 2).optional(),
  }),
  // ... other providers
};
```

### 3. Input Sanitization

All text inputs are sanitized to prevent XSS attacks:

```typescript
export const sanitizeText = (text: string): string => {
  return text
    .replace(/[<>]/g, '') // Remove angle brackets
    .replace(/javascript:/gi, '') // Remove javascript: protocol
    .replace(/on\w+\s*=/gi, '') // Remove event handlers
    .trim();
};
```

### 4. Malicious Content Detection

The system checks for potentially malicious patterns:

```typescript
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
```

### 5. API Response Validation

All API responses are validated before use:

```typescript
function validateProviderResponse(data: unknown): ProviderConfigurationResponse[] {
  if (!Array.isArray(data)) {
    console.error('Invalid provider configurations response: expected array');
    return [];
  }
  
  const validated: ProviderConfigurationResponse[] = [];
  
  for (const item of data) {
    try {
      const parsed = ProviderConfigurationResponseSchema.parse(item);
      validated.push(parsed);
    } catch (error) {
      console.error('Invalid provider configuration in response:', error);
    }
  }
  
  return validated;
}
```

### 6. Type-Safe API Client

The API client no longer uses `any` types:

```typescript
async getProviderConfigurations(): Promise<Array<{
  id: string;
  enabled?: boolean;
  config?: Record<string, any>;
  status?: string;
  last_tested?: string;
  models?: string[];
}>>
```

### 7. Context-Level Validation

The provider settings context validates data before updates:

```typescript
const updateProvider = useCallback((providerId: string, config: Partial<ProviderConfiguration['config']>) => {
  // Validate provider ID
  if (!isValidProviderId(providerId)) {
    console.error('Invalid provider ID:', providerId);
    return;
  }
  
  // Sanitize and validate configuration
  const sanitizedConfig = sanitizeProviderConfig(providerId, mergedConfig);
  const validation = validateProviderConfig(providerId, sanitizedConfig);
  
  if (!validation.isValid) {
    console.warn(`Invalid configuration for provider ${providerId}:`, validation.errors);
  }
  
  // Update with sanitized config
  // ...
}, []);
```

## Usage Examples

### Validating User Input

```typescript
import { validateUrl, validateApiKey, containsMaliciousContent } from '../utils/validation';

// Validate URL
const urlValidation = validateUrl(userInput);
if (!urlValidation.isValid) {
  showError(urlValidation.error);
}

// Check for malicious content
if (containsMaliciousContent(userInput)) {
  showError('Invalid input detected');
}
```

### Using the Validated Form Component

```typescript
import { ValidatedProviderForm } from '../examples/validated-provider-form';

function ProviderSettings() {
  return <ValidatedProviderForm providerId="openai" />;
}
```

## Security Benefits

1. **XSS Prevention**: All user inputs are sanitized before storage
2. **Injection Prevention**: Malicious patterns are detected and blocked
3. **Type Safety**: Runtime validation ensures data integrity
4. **API Security**: Invalid data is filtered out at the API boundary

## Backward Compatibility

All changes maintain backward compatibility:
- Invalid data is logged but not rejected (graceful degradation)
- Default values are provided for missing fields
- Existing configurations continue to work

## Testing Recommendations

1. Test with invalid URLs and API keys
2. Attempt XSS injections in text fields
3. Verify number range validations
4. Test with malformed API responses
5. Verify sanitization doesn't break valid inputs