/**
 * API integration helper functions
 */

import { apiClient } from '@/lib/utils/api-client';
import { ProviderConfiguration } from '@/lib/config/providers';
import { AI_PROVIDERS } from '@/lib/config/providers';
import { 
  ProviderSettings, 
  ProviderConfigurationResponse,
  ModelSelectionResponse,
  ProviderConfigurationResponseSchema,
  ModelSelectionResponseSchema
} from '../types';
import { DEFAULT_MODEL_SELECTION } from '../constants';
import { sanitizeProviderConfig } from './validation';

interface TestedProvider {
  status: string;
  models: string[];
  lastTested: Date;
}

// Validate API response for provider configurations
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

// Validate API response for model selection
function validateModelSelectionResponse(data: unknown): ModelSelectionResponse {
  try {
    return ModelSelectionResponseSchema.parse(data) || DEFAULT_MODEL_SELECTION;
  } catch (error) {
    console.error('Invalid model selection response:', error);
    return DEFAULT_MODEL_SELECTION;
  }
}

export async function loadProviderConfigurations(
  testedProviders: Record<string, TestedProvider>,
  signal?: AbortSignal
): Promise<Record<string, ProviderConfiguration>> {
  const rawResponse = await apiClient.getProviderConfigurations();
  const providerConfigs = validateProviderResponse(rawResponse);
  const providersMap: Record<string, ProviderConfiguration> = {};
  
  // Process provider configurations
  providerConfigs.forEach((config) => {
    const providerDef = AI_PROVIDERS[config.id];
    if (providerDef) {
      // Sanitize the provider config
      const sanitizedConfig = sanitizeProviderConfig(config.id, config.config || {});
      
      providersMap[config.id] = {
        id: config.id,
        providerId: config.id,
        name: providerDef.displayName,
        enabled: config.enabled ?? true,
        config: sanitizedConfig,
        status: config.status || 'disconnected',
        lastTested: config.last_tested,
        models: config.models || [],
      };
      
      // Sync with test cache if provider was tested
      if (testedProviders[config.id]?.status === 'tested') {
        providersMap[config.id].models = testedProviders[config.id].models;
        providersMap[config.id].status = 'connected';
      }
    }
  });
  
  return providersMap;
}

export async function loadModelSelection(signal?: AbortSignal): Promise<ProviderSettings['modelSelection']> {
  const rawResponse = await apiClient.getModelSelection();
  const validated = validateModelSelectionResponse(rawResponse);
  
  // Merge with defaults to ensure all required fields are present
  return {
    textGeneration: validated?.textGeneration || DEFAULT_MODEL_SELECTION.textGeneration,
    embeddings: validated?.embeddings || DEFAULT_MODEL_SELECTION.embeddings,
    sharedProvider: validated?.sharedProvider ?? DEFAULT_MODEL_SELECTION.sharedProvider
  };
}

export async function saveProviderConfiguration(
  providerId: string,
  config: ProviderConfiguration['config'],
  signal?: AbortSignal
): Promise<void> {
  // Sanitize config before sending to API
  const sanitizedConfig = sanitizeProviderConfig(providerId, config);
  
  await apiClient.updateProviderConfiguration(providerId, { 
    config: sanitizedConfig 
  });
}

export async function saveModelSelection(
  modelSelection: ProviderSettings['modelSelection'],
  signal?: AbortSignal
): Promise<void> {
  // Validate model selection before sending
  try {
    const validated = {
      textGeneration: {
        provider: modelSelection.textGeneration.provider,
        model: modelSelection.textGeneration.model
      },
      embeddings: {
        provider: modelSelection.embeddings.provider,
        model: modelSelection.embeddings.model
      },
      sharedProvider: modelSelection.sharedProvider
    };
    
    await apiClient.updateModelSelection(validated);
  } catch (error) {
    throw new Error('Invalid model selection: ' + (error instanceof Error ? error.message : 'Unknown error'));
  }
}

export function extractProviderUpdatesFromDirtyFields(
  dirtyFields: Set<string>,
  providers: Record<string, ProviderConfiguration>
): Map<string, ProviderConfiguration['config']> {
  const providerUpdates = new Map<string, ProviderConfiguration['config']>();
  
  dirtyFields.forEach(field => {
    if (field.startsWith('provider.')) {
      const [, providerId] = field.split('.');
      if (!providerUpdates.has(providerId) && providers[providerId]) {
        providerUpdates.set(providerId, providers[providerId].config);
      }
    }
  });
  
  return providerUpdates;
}

export function hasModelSelectionChanges(dirtyFields: Set<string>): boolean {
  return Array.from(dirtyFields).some(f => f.startsWith('modelSelection.'));
}