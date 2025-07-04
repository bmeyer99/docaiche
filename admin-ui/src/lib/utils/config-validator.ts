/**
 * Configuration validation utilities
 * Validates configuration dependencies and provides user-friendly error messages
 */

export interface ValidationError {
  field: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
  suggestion?: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

/**
 * Validate Vector Search configuration
 */
export function validateVectorSearchConfig(
  vectorConfig: any,
  embeddingConfig: any,
  providers: any
): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationError[] = [];

  // Check if vector search is enabled
  if (vectorConfig?.enabled) {
    // Validate Weaviate connection
    if (!vectorConfig.base_url) {
      errors.push({
        field: 'vectorConfig.base_url',
        message: 'Weaviate base URL is required when vector search is enabled',
        severity: 'error',
        suggestion: 'Configure the Weaviate connection in the Connection tab'
      });
    }

    if (!vectorConfig.connected) {
      warnings.push({
        field: 'vectorConfig.connection',
        message: 'Weaviate connection has not been tested',
        severity: 'warning',
        suggestion: 'Test the connection to ensure it works properly'
      });
    }

    // Validate embedding configuration
    if (!embeddingConfig?.useDefaultEmbedding) {
      if (!embeddingConfig?.provider) {
        errors.push({
          field: 'embeddingConfig.provider',
          message: 'Embedding provider must be selected when not using default embedding',
          severity: 'error',
          suggestion: 'Select an embedding provider in the Models tab'
        });
      }

      if (!embeddingConfig?.model) {
        errors.push({
          field: 'embeddingConfig.model',
          message: 'Embedding model must be selected when not using default embedding',
          severity: 'error',
          suggestion: 'Select an embedding model in the Models tab'
        });
      }

      // Validate provider is tested
      if (embeddingConfig?.provider && providers) {
        const providerStatus = providers[embeddingConfig.provider]?.status;
        if (providerStatus !== 'tested' && providerStatus !== 'connected') {
          warnings.push({
            field: 'embeddingConfig.provider',
            message: `Embedding provider "${embeddingConfig.provider}" has not been tested`,
            severity: 'warning',
            suggestion: 'Test the provider connection in the Providers tab'
          });
        }
      }
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Validate Text AI configuration
 */
export function validateTextAIConfig(
  modelSelection: any,
  modelParameters: any,
  providers: any
): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationError[] = [];

  const { provider, model } = modelSelection?.textGeneration || {};

  if (provider && model) {
    // Validate provider is tested
    if (providers) {
      const providerStatus = providers[provider]?.status;
      if (providerStatus !== 'tested' && providerStatus !== 'connected') {
        warnings.push({
          field: 'textGeneration.provider',
          message: `Text AI provider "${provider}" has not been tested`,
          severity: 'warning',
          suggestion: 'Test the provider connection in the Providers tab'
        });
      }
    }

    // Validate model parameters exist
    if (!modelParameters?.[provider]?.[model]) {
      warnings.push({
        field: 'textGeneration.parameters',
        message: 'Model parameters have not been configured',
        severity: 'warning',
        suggestion: 'Configure model parameters in the Model Parameters tab'
      });
    }
  } else if (provider && !model) {
    errors.push({
      field: 'textGeneration.model',
      message: 'Text AI model must be selected when provider is chosen',
      severity: 'error',
      suggestion: 'Select a model in the Model Selection tab'
    });
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Validate provider configuration
 */
export function validateProviderConfig(providers: any): ValidationResult {
  const errors: ValidationError[] = [];
  const warnings: ValidationError[] = [];

  if (!providers || Object.keys(providers).length === 0) {
    warnings.push({
      field: 'providers',
      message: 'No AI providers have been configured',
      severity: 'warning',
      suggestion: 'Configure at least one AI provider in the Providers tab'
    });
  } else {
    // Check if any providers are tested
    const testedProviders = Object.entries(providers).filter(
      ([, config]: [string, any]) => 
        config?.status === 'tested' || config?.status === 'connected'
    );

    if (testedProviders.length === 0) {
      warnings.push({
        field: 'providers',
        message: 'No AI providers have been successfully tested',
        severity: 'warning',
        suggestion: 'Test your provider connections to ensure they work properly'
      });
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Validate complete search configuration
 */
export function validateSearchConfig(
  vectorConfig: any,
  embeddingConfig: any,
  modelSelection: any,
  modelParameters: any,
  providers: any
): ValidationResult {
  const vectorValidation = validateVectorSearchConfig(vectorConfig, embeddingConfig, providers);
  const textAIValidation = validateTextAIConfig(modelSelection, modelParameters, providers);
  const providerValidation = validateProviderConfig(providers);

  return {
    isValid: vectorValidation.isValid && textAIValidation.isValid && providerValidation.isValid,
    errors: [
      ...vectorValidation.errors,
      ...textAIValidation.errors,
      ...providerValidation.errors
    ],
    warnings: [
      ...vectorValidation.warnings,
      ...textAIValidation.warnings,
      ...providerValidation.warnings
    ]
  };
}

/**
 * Get validation summary for UI display
 */
export function getValidationSummary(validation: ValidationResult): string {
  if (validation.isValid && validation.warnings.length === 0) {
    return 'Configuration is valid and complete';
  }
  
  if (validation.isValid && validation.warnings.length > 0) {
    return `Configuration is valid with ${validation.warnings.length} warning(s)`;
  }
  
  return `Configuration has ${validation.errors.length} error(s) that must be fixed`;
}