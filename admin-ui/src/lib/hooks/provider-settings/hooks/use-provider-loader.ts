/**
 * Hook for loading provider settings with proper cleanup
 */

import { useCallback, useState, useRef, useEffect } from 'react';
import { 
  loadProviderConfigurations, 
  loadModelSelection 
} from '../utils/api-helpers';
import { 
  initializeMissingProviders, 
  createSavedState 
} from '../utils/state-helpers';
import type { SavedState } from '../types';
import { ProviderConfiguration } from '@/lib/config/providers';
import { DEFAULT_MODEL_SELECTION } from '../constants';
import { 
  useIsMounted, 
  createAbortController,
  RequestDeduplicator 
} from '../utils/cleanup-helpers';

interface UseProviderLoaderReturn {
  isLoading: boolean;
  loadError: string | null;
  loadSettings: (testedProviders: Record<string, any>) => Promise<{
    providers: Record<string, ProviderConfiguration>;
    modelSelection: typeof DEFAULT_MODEL_SELECTION;
    savedState: SavedState;
  }>;
}

export function useProviderLoader(): UseProviderLoaderReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const isMounted = useIsMounted();
  const abortControllerRef = useRef<AbortController | null>(null);
  const deduplicatorRef = useRef<RequestDeduplicator<any>>(new RequestDeduplicator());

  // Cleanup on unmount
  useEffect(() => {
    const deduplicator = deduplicatorRef.current;
    return () => {
      // Cancel any pending requests
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      // Cancel all deduplicated requests
      deduplicator.cancelAll();
    };
  }, []);

  const loadSettings = useCallback(async (testedProviders: Record<string, any>) => {
    // Cancel any previous load operation
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller for this load
    const abortController = createAbortController(30000); // 30 second timeout
    abortControllerRef.current = abortController;

    if (isMounted()) {
      setIsLoading(true);
      setLoadError(null);
    }
    
    try {
      // Use deduplication for provider configurations
      const providersPromise = deduplicatorRef.current.deduplicate(
        'providers',
        async (signal) => {
          // Pass abort signal to API call
          return await loadProviderConfigurations(testedProviders, signal);
        },
        abortController.signal
      );

      // Use deduplication for model selection
      const modelSelectionPromise = deduplicatorRef.current.deduplicate(
        'modelSelection',
        async (signal) => {
          // Pass abort signal to API call
          return await loadModelSelection(signal);
        },
        abortController.signal
      );

      // Load both in parallel
      const [providersMap, modelSelection] = await Promise.all([
        providersPromise,
        modelSelectionPromise
      ]);
      
      // Check if still mounted before processing results
      if (!isMounted()) {
        throw new Error('Component unmounted');
      }

      // Initialize missing providers with defaults
      const allProviders = initializeMissingProviders(providersMap);
      
      // Create saved state
      const savedState = createSavedState(allProviders, modelSelection);
      
      return {
        providers: allProviders,
        modelSelection,
        savedState,
      };
      
    } catch (error) {
      // Check if error is due to abort
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Load operation was cancelled');
        throw new Error('Operation cancelled');
      }

      // Check if component was unmounted
      if (error instanceof Error && error.message === 'Component unmounted') {
        throw error;
      }

      console.error('Failed to load provider settings:', error);
      const errorMessage = error instanceof Error ? error.message : 'Failed to load settings';
      
      if (isMounted()) {
        setLoadError(errorMessage);
      }
      
      throw error;
    } finally {
      if (isMounted()) {
        setIsLoading(false);
      }
      // Clear abort controller reference
      if (abortControllerRef.current === abortController) {
        abortControllerRef.current = null;
      }
    }
  }, [isMounted]);

  return {
    isLoading,
    loadError,
    loadSettings,
  };
}