/**
 * Simplified Provider Loader Hook
 * Relies on global API client circuit breaker and health monitoring
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
import { useIsMounted } from '../utils/cleanup-helpers';

interface UseProviderLoaderReturn {
  isLoading: boolean;
  loadError: string | null;
  loadSettings: (testedProviders: Record<string, any>) => Promise<{
    providers: Record<string, ProviderConfiguration>;
    modelSelection: typeof DEFAULT_MODEL_SELECTION;
    savedState: SavedState;
  }>;
  clearError: () => void;
}

export function useProviderLoader(): UseProviderLoaderReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const isMounted = useIsMounted();
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      // Cancel any pending requests
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const loadSettings = useCallback(async (testedProviders: Record<string, any> = {}) => {
    try {
      // Cancel any previous load operation
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller for this load
      const abortController = new AbortController();
      abortControllerRef.current = abortController;

      if (isMounted()) {
        setIsLoading(true);
        setLoadError(null);
      }

      // Load both in parallel - let the API client handle retries and circuit breaking
      const [providersMap, modelSelection] = await Promise.all([
        loadProviderConfigurations(testedProviders),
        loadModelSelection()
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
      abortControllerRef.current = null;
    }
  }, [isMounted]);

  const clearError = useCallback(() => {
    if (isMounted()) {
      setLoadError(null);
    }
  }, [isMounted]);

  return {
    isLoading,
    loadError,
    loadSettings,
    clearError,
  };
}