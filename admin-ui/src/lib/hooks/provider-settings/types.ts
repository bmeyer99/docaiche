/**
 * Type definitions for the provider settings system
 */

import { z } from 'zod';
import type { ProviderConfiguration } from '@/lib/config/providers';

// Zod schemas for runtime validation
export const ModelSelectionSchema = z.object({
  provider: z.string().min(1, 'Provider is required'),
  model: z.string()
});

export type ModelSelection = z.infer<typeof ModelSelectionSchema>;

export const ModelSelectionConfigSchema = z.object({
  textGeneration: ModelSelectionSchema,
  embeddings: ModelSelectionSchema,
  sharedProvider: z.boolean()
});

export const ProviderSettingsSchema = z.object({
  // Provider configurations keyed by provider ID
  providers: z.record(z.string(), z.any()), // Will be refined with ProviderConfigurationSchema
  
  // Model selections
  modelSelection: ModelSelectionConfigSchema,
  
  // Track which fields have been modified
  dirtyFields: z.set(z.string()),
  
  // Loading states
  isLoading: z.boolean(),
  isSaving: z.boolean(),
  
  // Error states
  loadError: z.string().nullable(),
  saveError: z.string().nullable()
});

export type ProviderSettings = z.infer<typeof ProviderSettingsSchema>;

export interface ProviderSettingsContextValue extends ProviderSettings {
  // Actions
  loadSettings: () => Promise<void>;
  updateProvider: (providerId: string, config: Partial<ProviderConfiguration['config']>) => void;
  updateModelSelection: (selection: Partial<ProviderSettings['modelSelection']>) => void;
  saveAllChanges: () => Promise<void>;
  resetToSaved: () => void;
  hasUnsavedChanges: () => boolean;
  isFieldDirty: (fieldPath: string) => boolean;
  markFieldClean: (fieldPath: string) => void;
}

export const SavedStateSchema = z.object({
  providers: z.record(z.string(), z.any()), // Will be refined with ProviderConfigurationSchema
  modelSelection: ModelSelectionConfigSchema
});

export type SavedState = z.infer<typeof SavedStateSchema>;

export interface ProviderConfigHookReturn {
  provider: ProviderConfiguration | undefined;
  updateConfig: (config: Partial<ProviderConfiguration['config']>) => void;
  isDirty: boolean;
}

export interface ModelSelectionHookReturn {
  modelSelection: ProviderSettings['modelSelection'];
  updateModelSelection: (selection: Partial<ProviderSettings['modelSelection']>) => void;
  isDirty: boolean;
}

// API Response schemas
export const ProviderConfigurationResponseSchema = z.object({
  id: z.string(),
  enabled: z.boolean().optional(),
  config: z.record(z.string(), z.any()).optional(),
  status: z.enum(['connected', 'disconnected', 'error', 'available', 'tested', 'failed', 'testing', 'untested']).optional(),
  last_tested: z.string().nullable().optional(),
  models: z.array(z.string()).optional()
}).passthrough();

export type ProviderConfigurationResponse = z.infer<typeof ProviderConfigurationResponseSchema>;

export const ModelSelectionResponseSchema = z.object({
  textGeneration: ModelSelectionSchema.optional(),
  embeddings: ModelSelectionSchema.optional(),
  sharedProvider: z.boolean().optional()
}).nullable().optional();

export type ModelSelectionResponse = z.infer<typeof ModelSelectionResponseSchema>;

// Type guards
export function isProviderConfiguration(value: unknown): value is ProviderConfiguration {
  return (
    typeof value === 'object' &&
    value !== null &&
    'id' in value &&
    'providerId' in value &&
    'name' in value &&
    'enabled' in value &&
    'config' in value &&
    'status' in value
  );
}

export function isModelSelection(value: unknown): value is ModelSelection {
  try {
    ModelSelectionSchema.parse(value);
    return true;
  } catch {
    return false;
  }
}