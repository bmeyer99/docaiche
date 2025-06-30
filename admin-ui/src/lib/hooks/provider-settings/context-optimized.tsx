/**
 * Performance-optimized Provider Settings Context
 * Splits large context into smaller, focused contexts to prevent unnecessary re-renders
 * Uses memoization and performance optimization techniques
 */

import React, { 
  createContext, 
  useState, 
  useEffect, 
  ReactNode, 
  useRef,
  useMemo 
} from 'react';
import { useProviderTestCache } from '../use-provider-test-cache';
import { ProviderConfiguration, ProviderDefinition } from '@/lib/config/providers';
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
import { 
  validateProviderConfig, 
  validateModelSelection,
  sanitizeProviderConfig,
  isValidProviderId 
} from './utils/validation';
import { useIsMounted, CleanupManager } from './utils/cleanup-helpers';
import { 
  useDebouncedCallback,
  useStableMemo, 
  shallowEqual,
  useStableCallback,
  usePerformanceMonitor
} from '@/lib/utils/performance-helpers';
import type { 
  ProviderSettingsContextValue, 
  SavedState
} from './types';

// ========================== CONTEXT SPLITTING ==========================

// Provider Data Context - holds the actual data
interface ProviderDataContextValue {
  providers: Record<string, ProviderConfiguration>;
  modelSelection: typeof DEFAULT_MODEL_SELECTION;
  savedState: SavedState;
}

// Provider Actions Context - holds the actions
interface ProviderActionsContextValue {
  updateProvider: (providerId: string, config: Partial<ProviderConfiguration['config']>) => void;
  updateModelSelection: (selection: Partial<typeof DEFAULT_MODEL_SELECTION>) => void;
  loadSettings: () => Promise<void>;
  saveAllChanges: () => Promise<void>;
  resetToSaved: () => void;
}

// Provider State Context - holds loading/error states
interface ProviderStateContextValue {
  isLoading: boolean;
  isSaving: boolean;
  loadError: string | null;
  saveError: string | null;
  dirtyFields: Set<string>;
}

// Provider Utilities Context - holds utility functions
interface ProviderUtilitiesContextValue {
  hasUnsavedChanges: () => boolean;
  isFieldDirty: (fieldPath: string) => boolean;
  markFieldClean: (fieldPath: string) => void;
}

// Create separate contexts
const ProviderDataContext = createContext<ProviderDataContextValue | null>(null);
const ProviderActionsContext = createContext<ProviderActionsContextValue | null>(null);
const ProviderStateContext = createContext<ProviderStateContextValue | null>(null);
const ProviderUtilitiesContext = createContext<ProviderUtilitiesContextValue | null>(null);

// ========================== OPTIMIZED PROVIDER ==========================

interface OptimizedProviderSettingsProviderProps {
  children: ReactNode;
  debounceDelay?: number;
  enablePerformanceMonitoring?: boolean;
}

export function OptimizedProviderSettingsProvider({ 
  children, 
  debounceDelay = 300
}: OptimizedProviderSettingsProviderProps) {
  // Performance monitoring
  usePerformanceMonitor('OptimizedProviderSettingsProvider');
  
  const { testedProviders, setProviderTested } = useProviderTestCache();
  const { isLoading, loadError, loadSettings: loadSettingsCore } = useProviderLoader();
  const { isSaving, saveError, saveAllChanges: saveAllChangesCore, clearSaveError } = useProviderSaver();
  const isMounted = useIsMounted();
  const cleanupManagerRef = useRef(new CleanupManager());
  
  // State
  const [providers, setProviders] = useState<Record<string, ProviderConfiguration>>({});
  const [modelSelection, setModelSelection] = useState(DEFAULT_MODEL_SELECTION);
  const [dirtyFields, setDirtyFields] = useState<Set<string>>(new Set());
  const [savedState, setSavedState] = useState<SavedState>({
    providers: {},
    modelSelection: DEFAULT_MODEL_SELECTION,
  });

  const hasWarnedRef = useRef(false);

  // ========================== MEMOIZED DATA CONTEXTS ==========================

  // Memoize provider data context to prevent unnecessary re-renders
  const providerDataValue = useStableMemo(
    () => ({
      providers,
      modelSelection,
      savedState,
    }),
    [providers, modelSelection, savedState],
    shallowEqual
  );

  // Memoize provider state context
  const providerStateValue = useStableMemo(
    () => ({
      isLoading,
      isSaving,
      loadError,
      saveError,
      dirtyFields,
    }),
    [isLoading, isSaving, loadError, saveError, dirtyFields],
    shallowEqual
  );

  // ========================== OPTIMIZED ACTIONS ==========================

  /**
   * Load all settings from the backend
   */
  const loadSettings = useStableCallback(async () => {
    try {
      const { 
        providers: loadedProviders, 
        modelSelection: loadedModelSelection, 
        savedState: newSavedState 
      } = await loadSettingsCore(testedProviders);
      
      if (!isMounted()) return;

      setProviders(loadedProviders);
      setModelSelection(loadedModelSelection);
      setSavedState(newSavedState);
      setDirtyFields(new Set());
      
    } catch (error) {
      if (error instanceof Error && 
          (error.message === 'Component unmounted' || error.message === 'Operation cancelled')) {
        return;
      }
    }
  }, [testedProviders, loadSettingsCore, isMounted]);

  /**
   * Debounced provider update to prevent excessive re-renders
   */
  const updateProviderDebounced = useDebouncedCallback(
    (providerId: string, config: Partial<ProviderConfiguration['config']>) => {
      if (!isValidProviderId(providerId)) {
        console.error('Invalid provider ID:', providerId);
        return;
      }
      
      setProviders(prev => {
        const provider = prev[providerId];
        if (!provider) return prev;
        
        const mergedConfig = { ...provider.config, ...config };
        const sanitizedConfig = sanitizeProviderConfig(providerId, mergedConfig);
        
        const validation = validateProviderConfig(providerId, sanitizedConfig);
        if (!validation.isValid) {
          console.warn(`Invalid configuration for provider ${providerId}:`, validation.errors);
        }
        
        const updated = {
          ...prev,
          [providerId]: {
            ...provider,
            config: sanitizedConfig,
          },
        };
        
        return updated;
      });
    },
    debounceDelay,
    []
  );

  /**
   * Immediate provider update (for non-debounced updates)
   */
  const updateProviderImmediate = useStableCallback((
    providerId: string, 
    config: Partial<ProviderConfiguration['config']>
  ) => {
    // Mark fields as dirty immediately
    const newDirtyFields = Object.keys(config).map(key => 
      createProviderFieldPath(providerId, key)
    );
    setDirtyFields(prev => markFieldsAsDirty(prev, newDirtyFields));

    // Update with debouncing
    updateProviderDebounced(providerId, config);
  }, [updateProviderDebounced]);

  /**
   * Update model selection with debouncing
   */
  const updateModelSelectionDebounced = useDebouncedCallback(
    (selection: Partial<typeof modelSelection>) => {
      setModelSelection(prev => {
        const updated = { ...prev, ...selection };
        
        if (selection.textGeneration && !validateModelSelection(selection.textGeneration)) {
          console.warn('Invalid text generation model selection');
        }
        if (selection.embeddings && !validateModelSelection(selection.embeddings)) {
          console.warn('Invalid embeddings model selection');
        }
        
        return updated;
      });
    },
    debounceDelay,
    []
  );

  const updateModelSelectionImmediate = useStableCallback((
    selection: Partial<typeof modelSelection>
  ) => {
    // Mark fields as dirty immediately
    const newDirtyFields = Object.keys(selection).map(key => 
      createModelSelectionFieldPath(key)
    );
    setDirtyFields(prev => markFieldsAsDirty(prev, newDirtyFields));

    // Update with debouncing
    updateModelSelectionDebounced(selection);
  }, [updateModelSelectionDebounced]);

  /**
   * Save all changes to the backend
   */
  const saveAllChanges = useStableCallback(async () => {
    try {
      await saveAllChangesCore(dirtyFields, providers, modelSelection);
      
      if (!isMounted()) return;

      setSavedState(createSavedState(providers, modelSelection));
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
      if (error instanceof Error && 
          (error.message === 'Component unmounted' || error.message === 'Operation cancelled')) {
        return;
      }
    }
  }, [dirtyFields, providers, modelSelection, testedProviders, setProviderTested, saveAllChangesCore, isMounted]);

  /**
   * Reset to last saved state
   */
  const resetToSaved = useStableCallback(() => {
    if (!isMounted()) return;

    setProviders(deepClone(savedState.providers));
    setModelSelection(deepClone(savedState.modelSelection));
    setDirtyFields(new Set());
    clearSaveError();
  }, [savedState, clearSaveError, isMounted]);

  // ========================== MEMOIZED ACTIONS CONTEXT ==========================

  const providerActionsValue = useMemo(
    () => ({
      updateProvider: updateProviderImmediate,
      updateModelSelection: updateModelSelectionImmediate,
      loadSettings,
      saveAllChanges,
      resetToSaved,
    }),
    [updateProviderImmediate, updateModelSelectionImmediate, loadSettings, saveAllChanges, resetToSaved]
  );

  // ========================== UTILITY FUNCTIONS ==========================

  const hasUnsavedChanges = useStableCallback(() => {
    return dirtyFields.size > 0;
  }, [dirtyFields]);

  const isFieldDirty = useStableCallback((fieldPath: string) => {
    return dirtyFields.has(fieldPath);
  }, [dirtyFields]);

  const markFieldClean = useStableCallback((fieldPath: string) => {
    if (!isMounted()) return;
    setDirtyFields(prev => removeFieldFromDirty(prev, fieldPath));
  }, [isMounted]);

  const providerUtilitiesValue = useMemo(
    () => ({
      hasUnsavedChanges,
      isFieldDirty,
      markFieldClean,
    }),
    [hasUnsavedChanges, isFieldDirty, markFieldClean]
  );

  // ========================== EFFECTS ==========================

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
      // Cancel any pending debounced updates
      updateProviderDebounced.cancel();
      updateModelSelectionDebounced.cancel();
    };
  }, [updateProviderDebounced, updateModelSelectionDebounced]);

  // ========================== RENDER ==========================

  return (
    <ProviderDataContext.Provider value={providerDataValue}>
      <ProviderActionsContext.Provider value={providerActionsValue}>
        <ProviderStateContext.Provider value={providerStateValue}>
          <ProviderUtilitiesContext.Provider value={providerUtilitiesValue}>
            {children}
          </ProviderUtilitiesContext.Provider>
        </ProviderStateContext.Provider>
      </ProviderActionsContext.Provider>
    </ProviderDataContext.Provider>
  );
}

// ========================== OPTIMIZED HOOKS ==========================

/**
 * Hook to access provider data (causes re-renders only when data changes)
 */
export function useProviderData(): ProviderDataContextValue {
  const context = React.useContext(ProviderDataContext);
  if (!context) {
    throw new Error('useProviderData must be used within an OptimizedProviderSettingsProvider');
  }
  return context;
}

/**
 * Hook to access provider actions (never causes re-renders)
 */
export function useProviderActions(): ProviderActionsContextValue {
  const context = React.useContext(ProviderActionsContext);
  if (!context) {
    throw new Error('useProviderActions must be used within an OptimizedProviderSettingsProvider');
  }
  return context;
}

/**
 * Hook to access provider state (causes re-renders only when state changes)
 */
export function useProviderState(): ProviderStateContextValue {
  const context = React.useContext(ProviderStateContext);
  if (!context) {
    throw new Error('useProviderState must be used within an OptimizedProviderSettingsProvider');
  }
  return context;
}

/**
 * Hook to access provider utilities (never causes re-renders)
 */
export function useProviderUtilities(): ProviderUtilitiesContextValue {
  const context = React.useContext(ProviderUtilitiesContext);
  if (!context) {
    throw new Error('useProviderUtilities must be used within an OptimizedProviderSettingsProvider');
  }
  return context;
}

/**
 * Combined hook for backward compatibility
 */
export function useOptimizedProviderSettings(): ProviderSettingsContextValue {
  const data = useProviderData();
  const actions = useProviderActions();
  const state = useProviderState();
  const utilities = useProviderUtilities();

  return useMemo(
    () => ({
      ...data,
      ...actions,
      ...state,
      ...utilities,
    }),
    [data, actions, state, utilities]
  );
}

/**
 * Selector hook for specific provider data (prevents re-renders when other providers change)
 */
export function useProviderSelector<T>(
  selector: (providers: Record<string, ProviderConfiguration>) => T,
  equalityFn: (prev: T, next: T) => boolean = shallowEqual
): T {
  const { providers } = useProviderData();
  
  return useStableMemo(
    () => selector(providers),
    [providers],
    equalityFn
  );
}

/**
 * Hook for specific provider configuration (prevents re-renders when other providers change)
 */
export function useProviderConfig(providerId: string): ProviderConfiguration | undefined {
  return useProviderSelector(
    (providers) => providers[providerId],
    (prev, next) => prev === next
  );
}

/**
 * Hook for provider models (prevents re-renders when other data changes)
 */
export function useProviderModels(providerId: string): string[] {
  return useProviderSelector(
    (providers) => providers[providerId]?.models || [],
    shallowEqual
  );
}

/**
 * Hook for enabled providers only
 */
export function useEnabledProviders(): ProviderConfiguration[] {
  return useProviderSelector(
    (providers) => Object.values(providers).filter(p => p.enabled),
    shallowEqual
  );
}

/**
 * Hook for providers by category
 */
export function useProvidersByCategory(category: string): ProviderDefinition[] {
  return useStableMemo(() => {
    const { AI_PROVIDERS } = require('@/lib/config/providers');
    return Object.values(AI_PROVIDERS).filter((p: any) => p.category === category) as ProviderDefinition[];
  }, [category]);
}