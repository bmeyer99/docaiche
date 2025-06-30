/**
 * Provider Settings Context with proper cleanup
 * Centralized management of all provider configurations and settings
 * Integrates with ProviderTestCache and provides dirty state tracking
 */

import React, { createContext, useState, useCallback, useEffect, ReactNode, useRef } from 'react';
import { useProviderTestCache } from '../use-provider-test-cache';
import { ProviderConfiguration } from '@/lib/config/providers';
import { useProviderLoader } from './hooks/use-provider-loader';
import { useProviderSaver } from './hooks/use-provider-saver';
import { 
  deepClone, 
  markFieldsAsDirty, 
  removeFieldFromDirty,
  createSavedState
} from './utils/state-helpers';
import { 
  createProviderFieldPath, 
  createModelSelectionFieldPath 
} from './utils/field-path';
import { DEFAULT_MODEL_SELECTION } from './constants';
import type { 
  ProviderSettingsContextValue, 
  SavedState
} from './types';
import { 
  validateProviderConfig, 
  validateModelSelection,
  sanitizeProviderConfig,
  isValidProviderId 
} from './utils/validation';
import { useIsMounted, CleanupManager } from './utils/cleanup-helpers';

export const ProviderSettingsContext = createContext<ProviderSettingsContextValue | null>(null);

export function ProviderSettingsProvider({ children }: { children: ReactNode }) {
  const { testedProviders, setProviderTested } = useProviderTestCache();
  const { isLoading, loadError, loadSettings: loadSettingsCore } = useProviderLoader();
  const { isSaving, saveError, saveAllChanges: saveAllChangesCore, clearSaveError } = useProviderSaver();
  const isMounted = useIsMounted();
  const cleanupManagerRef = useRef(new CleanupManager());
  
  // State
  const [providers, setProviders] = useState<Record<string, ProviderConfiguration>>({});
  const [modelSelection, setModelSelection] = useState(DEFAULT_MODEL_SELECTION);
  const [dirtyFields, setDirtyFields] = useState<Set<string>>(new Set());
  
  // Keep a copy of the last saved state for reset functionality
  const [savedState, setSavedState] = useState<SavedState>({
    providers: {},
    modelSelection: DEFAULT_MODEL_SELECTION,
  });

  // Flag to track if we've warned about unsaved changes
  const hasWarnedRef = useRef(false);

  /**
   * Load all settings from the backend
   */
  const loadSettings = useCallback(async () => {
    try {
      const { 
        providers: loadedProviders, 
        modelSelection: loadedModelSelection, 
        savedState: newSavedState 
      } = await loadSettingsCore(testedProviders);
      
      // Check if still mounted
      if (!isMounted()) return;

      // Update state
      setProviders(loadedProviders);
      setModelSelection(loadedModelSelection);
      setSavedState(newSavedState);
      
      // Populate test cache from loaded provider data
      const { populateTestCacheFromProviders } = await import('./utils/api-helpers');
      populateTestCacheFromProviders(
        loadedProviders,
        setProviderTested,
        (providerId: string, error: string) => {
          // Map to test cache failed method if available
          // For now, just log since we don't have the failed method here
          console.log(`Provider ${providerId} test failed: ${error}`);
        }
      );
      
      // Clear dirty fields since we just loaded
      setDirtyFields(new Set());
      
    } catch (error) {
      // Error is already handled in loadSettingsCore
      // Check for abort/unmount errors
      if (error instanceof Error && 
          (error.message === 'Component unmounted' || error.message === 'Operation cancelled')) {
        return;
      }
    }
  }, [testedProviders, loadSettingsCore, isMounted, setProviderTested]);

  /**
   * Update a provider's configuration with validation
   */
  const updateProvider = useCallback((providerId: string, config: Partial<ProviderConfiguration['config']>) => {
    // Validate provider ID
    if (!isValidProviderId(providerId)) {
      console.error('Invalid provider ID:', providerId);
      return;
    }
    
    setProviders(prev => {
      const provider = prev[providerId];
      if (!provider) return prev;
      
      // Merge with existing config
      const mergedConfig = {
        ...provider.config,
        ...config,
      };
      
      // Sanitize the configuration
      const sanitizedConfig = sanitizeProviderConfig(providerId, mergedConfig);
      
      // Validate the configuration
      const validation = validateProviderConfig(providerId, sanitizedConfig);
      if (!validation.isValid) {
        console.warn(`Invalid configuration for provider ${providerId}:`, validation.errors);
        // Still allow the update but log the warning
      }
      
      const updated = {
        ...prev,
        [providerId]: {
          ...provider,
          config: sanitizedConfig,
        },
      };
      
      // Mark fields as dirty
      const newDirtyFields = Object.keys(config).map(key => 
        createProviderFieldPath(providerId, key)
      );
      setDirtyFields(prev => markFieldsAsDirty(prev, newDirtyFields));
      
      return updated;
    });
  }, []);

  /**
   * Update model selection with validation
   */
  const updateModelSelection = useCallback((selection: Partial<typeof modelSelection>) => {
    setModelSelection(prev => {
      const updated = { ...prev, ...selection };
      
      // Validate model selections
      if (selection.textGeneration && !validateModelSelection(selection.textGeneration)) {
        console.warn('Invalid text generation model selection');
      }
      if (selection.embeddings && !validateModelSelection(selection.embeddings)) {
        console.warn('Invalid embeddings model selection');
      }
      
      // Mark fields as dirty
      const newDirtyFields = Object.keys(selection).map(key => 
        createModelSelectionFieldPath(key)
      );
      setDirtyFields(prev => markFieldsAsDirty(prev, newDirtyFields));
      
      return updated;
    });
  }, []);

  /**
   * Save all changes to the backend
   */
  const saveAllChanges = useCallback(async () => {
    try {
      await saveAllChangesCore(dirtyFields, providers, modelSelection);
      
      // Check if still mounted
      if (!isMounted()) return;

      // Update saved state
      setSavedState(createSavedState(providers, modelSelection));
      
      // Clear dirty fields
      setDirtyFields(new Set());
      
      // Update test cache with saved configurations
      const providerUpdates = new Map<string, ProviderConfiguration['config']>();
      dirtyFields.forEach(field => {
        if (field.startsWith('provider.')) {
          const [, providerId] = field.split('.');
          if (!providerUpdates.has(providerId)) {
            providerUpdates.set(providerId, providers[providerId].config);
          }
        }
      });
      
      providerUpdates.forEach((config, providerId) => {
        const testedProvider = testedProviders[providerId];
        if (testedProvider?.status === 'tested') {
          setProviderTested(providerId, testedProvider.models, config);
        }
      });
      
    } catch (error) {
      // Check for abort/unmount errors
      if (error instanceof Error && 
          (error.message === 'Component unmounted' || error.message === 'Operation cancelled')) {
        return;
      }
      // Other errors are already handled in saveAllChangesCore
    }
  }, [dirtyFields, providers, modelSelection, testedProviders, setProviderTested, saveAllChangesCore, isMounted]);

  /**
   * Reset to last saved state
   */
  const resetToSaved = useCallback(() => {
    if (!isMounted()) return;

    setProviders(deepClone(savedState.providers));
    setModelSelection(deepClone(savedState.modelSelection));
    setDirtyFields(new Set());
    clearSaveError();
  }, [savedState, clearSaveError, isMounted]);

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
    if (!isMounted()) return;
    setDirtyFields(prev => removeFieldFromDirty(prev, fieldPath));
  }, [isMounted]);

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync with test cache updates
  useEffect(() => {
    if (!isMounted()) return;

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
  }, [testedProviders, isMounted]);

  // Add beforeunload handler for unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (hasUnsavedChanges() && !hasWarnedRef.current) {
        hasWarnedRef.current = true;
        const message = 'You have unsaved changes. Are you sure you want to leave?';
        e.preventDefault();
        e.returnValue = message;
        return message;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    // Register cleanup
    cleanupManagerRef.current.register(() => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    });

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [hasUnsavedChanges]);

  // Reset warned flag when dirty fields change
  useEffect(() => {
    if (dirtyFields.size === 0) {
      hasWarnedRef.current = false;
    }
  }, [dirtyFields]);

  // Cleanup on unmount
  useEffect(() => {
    const cleanupManager = cleanupManagerRef.current;
    return () => {
      cleanupManager.cleanup();
    };
  }, []);

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