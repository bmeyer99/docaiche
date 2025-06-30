/**
 * State manipulation helper functions
 */

import { ProviderConfiguration } from '@/lib/config/providers';
import { AI_PROVIDERS } from '@/lib/config/providers';
import type { SavedState } from '../types';

export function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

export function initializeMissingProviders(
  providersMap: Record<string, ProviderConfiguration>
): Record<string, ProviderConfiguration> {
  const result = { ...providersMap };
  
  Object.values(AI_PROVIDERS).forEach(provider => {
    if (!result[provider.id]) {
      result[provider.id] = {
        id: provider.id,
        providerId: provider.id,
        name: provider.displayName,
        enabled: false,
        config: {},
        status: 'disconnected',
        models: [],
      };
    }
  });
  
  return result;
}

export function createSavedState(
  providers: Record<string, ProviderConfiguration>,
  modelSelection: SavedState['modelSelection']
): SavedState {
  return {
    providers: deepClone(providers),
    modelSelection: deepClone(modelSelection),
  };
}

export function markFieldsAsDirty(
  currentDirtyFields: Set<string>,
  newFields: string[]
): Set<string> {
  const updatedFields = new Set(currentDirtyFields);
  newFields.forEach(field => updatedFields.add(field));
  return updatedFields;
}

export function removeFieldFromDirty(
  currentDirtyFields: Set<string>,
  fieldToRemove: string
): Set<string> {
  const updatedFields = new Set(currentDirtyFields);
  updatedFields.delete(fieldToRemove);
  return updatedFields;
}