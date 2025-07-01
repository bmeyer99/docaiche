/**
 * Simplified Provider Saver Hook
 * Relies on global API client circuit breaker and health monitoring
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';
import { 
  saveProviderConfiguration, 
  saveModelSelection 
} from '../utils/api-helpers';
import { ProviderConfiguration, AI_PROVIDERS } from '@/lib/config/providers';
import { DEFAULT_MODEL_SELECTION } from '../constants';
import { useIsMounted } from '../utils/cleanup-helpers';

interface SaveOperation {
  type: 'provider' | 'model-selection';
  data: any;
  fieldPath: string;
}

interface UseProviderSaverReturn {
  isSaving: boolean;
  saveError: string | null;
  saveAllChanges: (
    dirtyFields: Set<string>,
    providers: Record<string, ProviderConfiguration>,
    modelSelection: typeof DEFAULT_MODEL_SELECTION
  ) => Promise<void>;
  clearSaveError: () => void;
}

export function useProviderSaver(): UseProviderSaverReturn {
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const { toast } = useToast();
  const apiClient = useApiClient();
  const isMounted = useIsMounted();
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const saveAllChanges = useCallback(async (
    dirtyFields: Set<string>,
    providers: Record<string, ProviderConfiguration>,
    modelSelection: typeof DEFAULT_MODEL_SELECTION
  ) => {
    if (dirtyFields.size === 0) {
      return; // Nothing to save
    }

    // Cancel any previous save operation
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    if (isMounted()) {
      setIsSaving(true);
      setSaveError(null);
    }

    const operations: SaveOperation[] = [];

    // Collect all save operations
    dirtyFields.forEach(fieldPath => {
      if (fieldPath.startsWith('provider.')) {
        const [, providerId] = fieldPath.split('.');
        if (providerId && providers[providerId]) {
          operations.push({
            type: 'provider',
            data: providers[providerId],
            fieldPath
          });
        }
      } else if (fieldPath.startsWith('modelSelection.')) {
        operations.push({
          type: 'model-selection',
          data: modelSelection,
          fieldPath
        });
      }
    });

    try {
      // Execute all save operations - let the API client handle retries
      const results = await Promise.allSettled(
        operations.map(async (op) => {
          if (op.type === 'provider') {
            const provider = op.data as ProviderConfiguration;
            return saveProviderConfiguration(provider.id, provider.config);
          } else {
            return saveModelSelection(op.data);
          }
        })
      );

      // Check results
      const failures = results.filter(r => r.status === 'rejected');
      if (failures.length > 0) {
        const firstError = (failures[0] as PromiseRejectedResult).reason;
        throw firstError;
      }

      if (isMounted()) {
        toast({
          title: 'Settings Saved',
          description: `Successfully saved ${operations.length} configuration${operations.length > 1 ? 's' : ''}.`,
        });
      }

    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('Save operation was cancelled');
        return;
      }

      console.error('Failed to save settings:', error);
      
      const errorMessage = error instanceof Error ? error.message : 'Failed to save settings';
      
      if (isMounted()) {
        setSaveError(errorMessage);
        
        // Don't show toast for circuit breaker errors - global health provider handles those
        if (!errorMessage.includes('Circuit Breaker') && !errorMessage.includes('Connection')) {
          toast({
            title: 'Save Failed',
            description: errorMessage,
            variant: 'destructive',
          });
        }
      }
      
      throw error;
    } finally {
      if (isMounted()) {
        setIsSaving(false);
      }
      abortControllerRef.current = null;
    }
  }, [toast, isMounted]);

  const clearSaveError = useCallback(() => {
    if (isMounted()) {
      setSaveError(null);
    }
  }, [isMounted]);

  return {
    isSaving,
    saveError,
    saveAllChanges,
    clearSaveError,
  };
}