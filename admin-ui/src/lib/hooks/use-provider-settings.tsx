/**
 * Provider Settings Context
 * Centralized management of all provider configurations and settings
 * Integrates with ProviderTestCache and provides dirty state tracking
 */

import React, { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react';
import { apiClient } from '../utils/api-client';
import { useProviderTestCache } from './use-provider-test-cache';
import { AI_PROVIDERS, type ProviderConfiguration } from '../config/providers';

interface ModelSelection {
  provider: string;
  model: string;
}

interface ProviderSettings {
  // Provider configurations keyed by provider ID
  providers: Record<string, ProviderConfiguration>;
  
  // Model selections
  modelSelection: {
    textGeneration: ModelSelection;
    embeddings: ModelSelection;
    sharedProvider: boolean;
  };
  
  // Track which fields have been modified
  dirtyFields: Set<string>;
  
  // Loading states
  isLoading: boolean;
  isSaving: boolean;
  
  // Error states
  loadError: string | null;
  saveError: string | null;
}

interface ProviderSettingsContextValue extends ProviderSettings {
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

const ProviderSettingsContext = createContext<ProviderSettingsContextValue | null>(null);

// Default values
const DEFAULT_MODEL_SELECTION = {
  textGeneration: { provider: 'ollama', model: '' },
  embeddings: { provider: 'ollama', model: '' },
  sharedProvider: true,
};

export function ProviderSettingsProvider({ children }: { children: ReactNode }) {
  const { testedProviders, setProviderTested } = useProviderTestCache();
  
  // State
  const [providers, setProviders] = useState<Record<string, ProviderConfiguration>>({});
  const [modelSelection, setModelSelection] = useState(DEFAULT_MODEL_SELECTION);
  const [dirtyFields, setDirtyFields] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  
  // Keep a copy of the last saved state for reset functionality
  const [savedState, setSavedState] = useState<{
    providers: Record<string, ProviderConfiguration>;
    modelSelection: typeof DEFAULT_MODEL_SELECTION;
  }>({
    providers: {},
    modelSelection: DEFAULT_MODEL_SELECTION,
  });

  /**
   * Load all settings from the backend
   */
  const loadSettings = useCallback(async () => {
    setIsLoading(true);
    setLoadError(null);
    
    try {
      // Load provider configurations
      const providerConfigs = await apiClient.getProviderConfigurations();
      const providersMap: Record<string, ProviderConfiguration> = {};
      
      // Process provider configurations
      providerConfigs.forEach((config: any) => {
        const providerDef = AI_PROVIDERS[config.id];
        if (providerDef) {
          providersMap[config.id] = {
            id: config.id,
            providerId: config.id,
            name: providerDef.displayName,
            enabled: config.enabled ?? true,
            config: config.config || {},
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
      
      // Initialize missing providers with defaults
      Object.values(AI_PROVIDERS).forEach(provider => {
        if (!providersMap[provider.id]) {
          providersMap[provider.id] = {
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
      
      // Load model selection
      const modelSelectionData = await apiClient.getModelSelection();
      const loadedModelSelection = modelSelectionData || DEFAULT_MODEL_SELECTION;
      
      // Update state
      setProviders(providersMap);
      setModelSelection(loadedModelSelection);
      
      // Save the loaded state as the "saved" state
      setSavedState({
        providers: JSON.parse(JSON.stringify(providersMap)),
        modelSelection: JSON.parse(JSON.stringify(loadedModelSelection)),
      });
      
      // Clear dirty fields since we just loaded
      setDirtyFields(new Set());
      
    } catch (error) {
      console.error('Failed to load provider settings:', error);
      setLoadError(error instanceof Error ? error.message : 'Failed to load settings');
    } finally {
      setIsLoading(false);
    }
  }, [testedProviders]);

  /**
   * Update a provider's configuration
   */
  const updateProvider = useCallback((providerId: string, config: Partial<ProviderConfiguration['config']>) => {
    setProviders(prev => {
      const provider = prev[providerId];
      if (!provider) return prev;
      
      const updated = {
        ...prev,
        [providerId]: {
          ...provider,
          config: {
            ...provider.config,
            ...config,
          },
        },
      };
      
      // Mark fields as dirty
      Object.keys(config).forEach(key => {
        setDirtyFields(prev => new Set(prev).add(`provider.${providerId}.${key}`));
      });
      
      return updated;
    });
  }, []);

  /**
   * Update model selection
   */
  const updateModelSelection = useCallback((selection: Partial<typeof modelSelection>) => {
    setModelSelection(prev => {
      const updated = { ...prev, ...selection };
      
      // Mark fields as dirty
      Object.keys(selection).forEach(key => {
        setDirtyFields(prev => new Set(prev).add(`modelSelection.${key}`));
      });
      
      return updated;
    });
  }, []);

  /**
   * Save all changes to the backend
   */
  const saveAllChanges = useCallback(async () => {
    if (dirtyFields.size === 0) return;
    
    setIsSaving(true);
    setSaveError(null);
    
    try {
      const promises: Promise<any>[] = [];
      
      // Save provider configurations
      const providerUpdates = new Map<string, ProviderConfiguration['config']>();
      
      dirtyFields.forEach(field => {
        if (field.startsWith('provider.')) {
          const [, providerId] = field.split('.');
          if (!providerUpdates.has(providerId)) {
            providerUpdates.set(providerId, providers[providerId].config);
          }
        }
      });
      
      // Batch provider updates
      providerUpdates.forEach((config, providerId) => {
        promises.push(apiClient.updateProviderConfiguration(providerId, { config } as any));
      });
      
      // Save model selection if dirty
      const hasModelSelectionChanges = Array.from(dirtyFields).some(f => f.startsWith('modelSelection.'));
      if (hasModelSelectionChanges) {
        promises.push(apiClient.updateModelSelection(modelSelection));
      }
      
      // Execute all saves in parallel
      await Promise.all(promises);
      
      // Update saved state
      setSavedState({
        providers: JSON.parse(JSON.stringify(providers)),
        modelSelection: JSON.parse(JSON.stringify(modelSelection)),
      });
      
      // Clear dirty fields
      setDirtyFields(new Set());
      
      // Update test cache with saved configurations
      providerUpdates.forEach((config, providerId) => {
        const testedProvider = testedProviders[providerId];
        if (testedProvider?.status === 'tested') {
          setProviderTested(providerId, testedProvider.models, config);
        }
      });
      
    } catch (error) {
      console.error('Failed to save provider settings:', error);
      setSaveError(error instanceof Error ? error.message : 'Failed to save settings');
      throw error;
    } finally {
      setIsSaving(false);
    }
  }, [dirtyFields, providers, modelSelection, testedProviders, setProviderTested]);

  /**
   * Reset to last saved state
   */
  const resetToSaved = useCallback(() => {
    setProviders(JSON.parse(JSON.stringify(savedState.providers)));
    setModelSelection(JSON.parse(JSON.stringify(savedState.modelSelection)));
    setDirtyFields(new Set());
    setSaveError(null);
  }, [savedState]);

  /**
   * Check if there are unsaved changes
   */
  const hasUnsavedChanges = useCallback(() => {
    return dirtyFields.size > 0;
  }, [dirtyFields]);

  /**
   * Check if a specific field is dirty
   */
  const isFieldDirty = useCallback((fieldPath: string) => {
    return dirtyFields.has(fieldPath);
  }, [dirtyFields]);

  /**
   * Mark a field as clean (not dirty)
   */
  const markFieldClean = useCallback((fieldPath: string) => {
    setDirtyFields(prev => {
      const next = new Set(prev);
      next.delete(fieldPath);
      return next;
    });
  }, []);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync with test cache updates
  useEffect(() => {
    setProviders(prev => {
      let updated = false;
      const next = { ...prev };
      
      Object.entries(testedProviders).forEach(([providerId, testedProvider]) => {
        if (prev[providerId] && testedProvider.status === 'tested') {
          next[providerId] = {
            ...prev[providerId],
            models: testedProvider.models,
            status: 'connected',
            lastTested: testedProvider.lastTested.toISOString(),
          };
          updated = true;
        }
      });
      
      return updated ? next : prev;
    });
  }, [testedProviders]);

  const value: ProviderSettingsContextValue = {
    providers,
    modelSelection,
    dirtyFields,
    isLoading,
    isSaving,
    loadError,
    saveError,
    loadSettings,
    updateProvider,
    updateModelSelection,
    saveAllChanges,
    resetToSaved,
    hasUnsavedChanges,
    isFieldDirty,
    markFieldClean,
  };

  return (
    <ProviderSettingsContext.Provider value={value}>
      {children}
    </ProviderSettingsContext.Provider>
  );
}

/**
 * Hook to use the provider settings context
 */
export function useProviderSettings(): ProviderSettingsContextValue {
  const context = useContext(ProviderSettingsContext);
  if (!context) {
    throw new Error('useProviderSettings must be used within a ProviderSettingsProvider');
  }
  return context;
}

/**
 * Hook to get a specific provider's configuration
 */
export function useProviderConfig(providerId: string): {
  provider: ProviderConfiguration | undefined;
  updateConfig: (config: Partial<ProviderConfiguration['config']>) => void;
  isDirty: boolean;
} {
  const { providers, updateProvider, dirtyFields } = useProviderSettings();
  
  const provider = providers[providerId];
  const isDirty = Array.from(dirtyFields).some(field => field.startsWith(`provider.${providerId}.`));
  
  const updateConfig = useCallback((config: Partial<ProviderConfiguration['config']>) => {
    updateProvider(providerId, config);
  }, [providerId, updateProvider]);
  
  return { provider, updateConfig, isDirty };
}

/**
 * Hook to manage model selection with dirty tracking
 */
export function useModelSelection() {
  const { modelSelection, updateModelSelection, isFieldDirty } = useProviderSettings();
  
  const isDirty = isFieldDirty('modelSelection.textGeneration') || 
                  isFieldDirty('modelSelection.embeddings') || 
                  isFieldDirty('modelSelection.sharedProvider');
  
  return {
    modelSelection,
    updateModelSelection,
    isDirty,
  };
}