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


// Validate API response for provider configurations
function validateProviderResponse(data: unknown): ProviderConfigurationResponse[] {
  if (!Array.isArray(data)) {
    console.error('Invalid provider configurations response: expected array');
    return [];
  }
  
  // Skip validation for now - just return the data as-is
  return data as ProviderConfigurationResponse[];
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
  testedProviders: Record<string, any> = {}
): Promise<Record<string, ProviderConfiguration>> {
  try {
    // First try to get the saved providers from configuration
    const rawResponse = await apiClient.getProviderConfigurations();
    const providerConfigs = validateProviderResponse(rawResponse);
    const providersMap: Record<string, ProviderConfiguration> = {};
    
    // Process provider configurations from saved config
    providerConfigs.forEach((config) => {
      const sanitizedConfig = sanitizeProviderConfig(config.id, config.config || {});
      
      // Map backend status to frontend status
      let frontendStatus: 'connected' | 'disconnected' | 'error' | 'available' | 'tested' | 'failed' | 'testing' = 'disconnected';
      if (config.status === 'tested') frontendStatus = 'tested';
      else if (config.status === 'testing') frontendStatus = 'testing';
      else if (config.status === 'failed') frontendStatus = 'error';
      else if (config.status === 'connected') frontendStatus = 'connected';
      else if (config.status === 'available') frontendStatus = 'available';
      else if (config.status === 'error') frontendStatus = 'error';
      else if (config.status === 'untested') frontendStatus = 'disconnected';
      
      // Use data from saved configuration
      providersMap[config.id] = {
        id: config.id,
        providerId: config.id,
        name: (config as any).name || config.id,
        enabled: (config as any).enabled ?? true,
        config: sanitizedConfig,
        status: frontendStatus,
        lastTested: (config as any).last_tested,
        models: (config as any).models || [],
        // Add additional fields from backend
        category: (config as any).category,
        description: (config as any).description,
        requiresApiKey: (config as any).requires_api_key,
        supportsEmbedding: (config as any).supports_embedding,
        supportsChat: (config as any).supports_chat,
      };
    });
    
    // If we have configured providers, return them
    if (Object.keys(providersMap).length > 0) {
      console.log('[loadProviderConfigurations] Loaded providers from saved config:', Object.keys(providersMap));
      return providersMap;
    }
    
    // If no providers found in saved config, initialize with defaults from AI_PROVIDERS
    console.log('[loadProviderConfigurations] No saved providers found, initializing defaults');
    Object.entries(AI_PROVIDERS).forEach(([id, provider]) => {
      providersMap[id] = {
        id,
        providerId: id,
        name: provider.displayName,
        enabled: false,
        config: {},
        status: 'disconnected',
        lastTested: null,
        models: [],
        category: provider.category,
        description: provider.description || '',
        requiresApiKey: provider.requiresApiKey,
        supportsEmbedding: provider.supportsEmbedding,
        supportsChat: provider.supportsChat,
      };
    });
    
    return providersMap;
    
  } catch (error) {
    console.error('[loadProviderConfigurations] Failed to load provider configurations:', error);
    
    // On error, return defaults from AI_PROVIDERS
    const providersMap: Record<string, ProviderConfiguration> = {};
    Object.entries(AI_PROVIDERS).forEach(([id, provider]) => {
      providersMap[id] = {
        id,
        providerId: id,
        name: provider.displayName,
        enabled: false,
        config: {},
        status: 'disconnected',
        lastTested: null,
        models: [],
        category: provider.category,
        description: provider.description || '',
        requiresApiKey: provider.requiresApiKey,
        supportsEmbedding: provider.supportsEmbedding,
        supportsChat: provider.supportsChat,
      };
    });
    
    return providersMap;
  }
}


export async function loadModelSelection(): Promise<ProviderSettings['modelSelection']> {
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
  config: ProviderConfiguration['config']
): Promise<void> {
  // Sanitize config before sending to API
  const sanitizedConfig = sanitizeProviderConfig(providerId, config);
  
  await apiClient.updateProviderConfiguration(providerId, { 
    config: sanitizedConfig 
  });
}

export async function saveModelSelection(
  modelSelection: ProviderSettings['modelSelection']
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