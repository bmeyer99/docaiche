/**
 * Hook for saving provider settings with proper cleanup
 */

import { useCallback, useState, useRef, useEffect } from 'react';
import { 
  saveProviderConfiguration, 
  saveModelSelection,
  extractProviderUpdatesFromDirtyFields,
  hasModelSelectionChanges
} from '../utils/api-helpers';
import { ProviderConfiguration } from '@/lib/config/providers';
import type { ProviderSettings } from '../types';
import { 
  useIsMounted, 
  createAbortController,
  SaveQueue 
} from '../utils/cleanup-helpers';

interface UseProviderSaverReturn {
  isSaving: boolean;
  saveError: string | null;
  saveAllChanges: (
    dirtyFields: Set<string>,
    providers: Record<string, ProviderConfiguration>,
    modelSelection: ProviderSettings['modelSelection']
  ) => Promise<void>;
  clearSaveError: () => void;
}

export function useProviderSaver(): UseProviderSaverReturn {
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const isMounted = useIsMounted();
  const abortControllerRef = useRef<AbortController | null>(null);
  const saveQueueRef = useRef<SaveQueue<void>>(new SaveQueue());

  // Cleanup on unmount
  useEffect(() => {
    const saveQueue = saveQueueRef.current;
    return () => {
      // Cancel any pending save operations
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      // Cancel all queued saves
      saveQueue.cancelAll();
    };
  }, []);

  const saveAllChanges = useCallback(async (
    dirtyFields: Set<string>,
    providers: Record<string, ProviderConfiguration>,
    modelSelection: ProviderSettings['modelSelection']
  ) => {
    if (dirtyFields.size === 0) return;

    // Queue the save operation to prevent overlapping saves
    return saveQueueRef.current.enqueue(async () => {
      // Check if component is still mounted
      if (!isMounted()) {
        throw new Error('Component unmounted');
      }

      // Cancel any previous save operation
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      // Create new abort controller for this save
      const abortController = createAbortController(30000); // 30 second timeout
      abortControllerRef.current = abortController;
      
      if (isMounted()) {
        setIsSaving(true);
        setSaveError(null);
      }
      
      try {
        const promises: Promise<any>[] = [];
        
        // Extract provider updates from dirty fields
        const providerUpdates = extractProviderUpdatesFromDirtyFields(dirtyFields, providers);
        
        // Batch provider updates with abort signal
        providerUpdates.forEach((config, providerId) => {
          promises.push(
            saveProviderConfiguration(providerId, config, abortController.signal)
          );
        });
        
        // Save model selection if dirty with abort signal
        if (hasModelSelectionChanges(dirtyFields)) {
          promises.push(
            saveModelSelection(modelSelection, abortController.signal)
          );
        }
        
        // Execute all saves in parallel
        await Promise.all(promises);
        
        // Check if still mounted after save
        if (!isMounted()) {
          throw new Error('Component unmounted');
        }
        
      } catch (error) {
        // Check if error is due to abort
        if (error instanceof Error && error.name === 'AbortError') {
          console.log('Save operation was cancelled');
          throw new Error('Operation cancelled');
        }

        // Check if component was unmounted
        if (error instanceof Error && error.message === 'Component unmounted') {
          throw error;
        }

        console.error('Failed to save provider settings:', error);
        const errorMessage = error instanceof Error ? error.message : 'Failed to save settings';
        
        if (isMounted()) {
          setSaveError(errorMessage);
        }
        
        throw error;
      } finally {
        if (isMounted()) {
          setIsSaving(false);
        }
        // Clear abort controller reference
        if (abortControllerRef.current === abortController) {
          abortControllerRef.current = null;
        }
      }
    });
  }, [isMounted]);

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