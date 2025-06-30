/**
 * Hook for saving provider settings with comprehensive error handling and resilience
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
import {
  RetryManager,
  OptimisticUpdateManager,
  GlobalErrorHandler,
  ErrorContextManager,
  PartialFailureError,
  ConflictError,
  NetworkError,
  TimeoutError,
  createUserFriendlyMessage
} from '../utils/error-handling';

interface SaveOperation {
  id: string;
  type: 'provider' | 'model-selection';
  providerId?: string;
  data: any;
  status: 'pending' | 'success' | 'failed' | 'retrying';
  error?: Error;
  attempts: number;
}

interface UseProviderSaverReturn {
  isSaving: boolean;
  saveError: string | null;
  partialFailures: SaveOperation[];
  saveProgress: number;
  saveAllChanges: (
    dirtyFields: Set<string>,
    providers: Record<string, ProviderConfiguration>,
    modelSelection: ProviderSettings['modelSelection']
  ) => Promise<void>;
  retrySaveOperation: (operationId: string) => Promise<void>;
  rollbackOptimisticUpdates: () => void;
  clearSaveError: () => void;
  getSaveOperationStatus: () => SaveOperation[];
}

export function useProviderSaver(): UseProviderSaverReturn {
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [partialFailures, setPartialFailures] = useState<SaveOperation[]>([]);
  const [saveProgress, setSaveProgress] = useState<number>(0);
  const [saveOperations, setSaveOperations] = useState<SaveOperation[]>([]);
  
  const isMounted = useIsMounted();
  const abortControllerRef = useRef<AbortController | null>(null);
  const saveQueueRef = useRef<SaveQueue>(new SaveQueue());
  const retryManagerRef = useRef(new RetryManager({
    maxAttempts: 3,
    baseDelayMs: 1000,
    maxDelayMs: 5000,
    onRetry: (attempt, error) => {
      console.log(`Retrying save operation, attempt ${attempt}:`, error.message);
    }
  }));
  const optimisticUpdateManagerRef = useRef(new OptimisticUpdateManager());
  const errorHandlerRef = useRef(GlobalErrorHandler.getInstance());
  const contextManagerRef = useRef(ErrorContextManager.getInstance());

  // Set error context
  useEffect(() => {
    contextManagerRef.current.setContext({
      component: 'useProviderSaver',
      operation: 'provider-settings-save'
    });
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    const saveQueue = saveQueueRef.current;
    const optimisticManager = optimisticUpdateManagerRef.current;
    
    return () => {
      // Cancel any pending save operations
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      // Cancel all queued saves
      saveQueue.cancelAll();
      // Rollback any pending optimistic updates
      optimisticManager.rollbackAll();
      // Clear error context
      contextManagerRef.current.clearContext();
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
      const abortController = createAbortController(45000); // 45 second timeout for resilience
      abortControllerRef.current = abortController;
      
      if (isMounted()) {
        setIsSaving(true);
        setSaveError(null);
        setPartialFailures([]);
        setSaveProgress(0);
      }
      
      // Create save operations
      const operations: SaveOperation[] = [];
      const providerUpdates = extractProviderUpdatesFromDirtyFields(dirtyFields, providers);
      
      // Add provider save operations
      providerUpdates.forEach((config, providerId) => {
        operations.push({
          id: `provider-${providerId}-${Date.now()}`,
          type: 'provider',
          providerId,
          data: config,
          status: 'pending',
          attempts: 0
        });
      });
      
      // Add model selection save operation
      if (hasModelSelectionChanges(dirtyFields)) {
        operations.push({
          id: `model-selection-${Date.now()}`,
          type: 'model-selection',
          data: modelSelection,
          status: 'pending',
          attempts: 0
        });
      }
      
      if (isMounted()) {
        setSaveOperations(operations);
      }
      
      const successfulOperations: string[] = [];
      const failedOperations: Array<{ operation: string; error: Error }> = [];
      
      try {
        // Process operations with progress tracking
        for (let i = 0; i < operations.length; i++) {
          const operation = operations[i];
          
          if (!isMounted() || abortController.signal.aborted) {
            throw new Error('Operation cancelled');
          }
          
          try {
            // Update operation status
            operation.status = 'retrying';
            operation.attempts++;
            
            if (isMounted()) {
              setSaveOperations([...operations]);
            }
            
            // Execute save operation with retry logic
            await retryManagerRef.current.execute(async () => {
              if (operation.type === 'provider') {
                return await saveProviderConfiguration(
                  operation.providerId!,
                  operation.data
                );
              } else {
                return await saveModelSelection(
                  operation.data
                );
              }
            }, `${operation.type}-${operation.providerId || 'model-selection'}`, abortController.signal);
            
            // Mark as successful
            operation.status = 'success';
            successfulOperations.push(operation.id);
            
            // Confirm optimistic update
            optimisticUpdateManagerRef.current.confirmUpdate(operation.id);
            
          } catch (operationError) {
            const error = operationError instanceof Error ? operationError : new Error(String(operationError));
            
            // Handle specific error types
            if (error.message.includes('conflict') || error.message.includes('version')) {
              const conflictError = new ConflictError(
                [operation.id],
                'server-version-unknown',
                'client-version-unknown',
                { operation }
              );
              operation.error = conflictError;
            } else if (error.message.includes('network') || error.message.includes('fetch')) {
              operation.error = new NetworkError(error.message, { operation });
            } else if (error.message.includes('timeout')) {
              operation.error = new TimeoutError(operation.type, 30000, { operation });
            } else {
              operation.error = error;
            }
            
            operation.status = 'failed';
            failedOperations.push({ operation: operation.id, error: operation.error });
            
            // Rollback optimistic update
            optimisticUpdateManagerRef.current.rollbackUpdate(operation.id);
          }
          
          // Update progress
          const progress = ((i + 1) / operations.length) * 100;
          if (isMounted()) {
            setSaveProgress(progress);
            setSaveOperations([...operations]);
          }
        }
        
        // Handle partial failures
        if (failedOperations.length > 0) {
          const partialFailureError = new PartialFailureError(
            successfulOperations,
            failedOperations,
            { totalOperations: operations.length }
          );
          
          const failedOps = operations.filter(op => op.status === 'failed');
          if (isMounted()) {
            setPartialFailures(failedOps);
          }
          
          // If all operations failed, throw the error
          if (successfulOperations.length === 0) {
            throw partialFailureError;
          }
          
          // Log partial failure but don't throw (some operations succeeded)
          console.warn('Partial save failure:', partialFailureError);
          await errorHandlerRef.current.handle(partialFailureError);
        }
        
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
        
        // Handle error through global error handler
        await errorHandlerRef.current.handle(error as Error, {
          dirtyFields: Array.from(dirtyFields),
          operations
        });
        
        const errorMessage = createUserFriendlyMessage(error instanceof Error ? error : new Error(String(error)));
        
        if (isMounted()) {
          setSaveError(errorMessage);
        }
        
        throw error;
      } finally {
        if (isMounted()) {
          setIsSaving(false);
          setSaveProgress(100);
        }
        // Clear abort controller reference
        if (abortControllerRef.current === abortController) {
          abortControllerRef.current = null;
        }
      }
    });
  }, [isMounted]);

  const retrySaveOperation = useCallback(async (operationId: string) => {
    const operation = saveOperations.find(op => op.id === operationId);
    if (!operation || operation.status !== 'failed') {
      return;
    }
    
    if (!isMounted()) return;
    
    setIsSaving(true);
    
    try {
      operation.status = 'retrying';
      operation.attempts++;
      setSaveOperations([...saveOperations]);
      
      await retryManagerRef.current.execute(async () => {
        if (operation.type === 'provider') {
          return await saveProviderConfiguration(
            operation.providerId!,
            operation.data
          );
        } else {
          return await saveModelSelection(operation.data);
        }
      }, `retry-${operation.type}`);
      
      operation.status = 'success';
      operation.error = undefined;
      
      // Remove from partial failures
      setPartialFailures(prev => prev.filter(op => op.id !== operationId));
      setSaveOperations([...saveOperations]);
      
      // Confirm optimistic update
      optimisticUpdateManagerRef.current.confirmUpdate(operation.id);
      
    } catch (error) {
      operation.status = 'failed';
      operation.error = error instanceof Error ? error : new Error(String(error));
      setSaveOperations([...saveOperations]);
      
      const errorMessage = createUserFriendlyMessage(operation.error);
      setSaveError(errorMessage);
    } finally {
      if (isMounted()) {
        setIsSaving(false);
      }
    }
  }, [saveOperations, isMounted]);
  
  const rollbackOptimisticUpdates = useCallback(() => {
    optimisticUpdateManagerRef.current.rollbackAll();
    if (isMounted()) {
      setPartialFailures([]);
      setSaveOperations([]);
      setSaveError(null);
    }
  }, [isMounted]);
  
  const clearSaveError = useCallback(() => {
    if (isMounted()) {
      setSaveError(null);
    }
  }, [isMounted]);
  
  const getSaveOperationStatus = useCallback(() => {
    return [...saveOperations];
  }, [saveOperations]);

  return {
    isSaving,
    saveError,
    partialFailures,
    saveProgress,
    saveAllChanges,
    retrySaveOperation,
    rollbackOptimisticUpdates,
    clearSaveError,
    getSaveOperationStatus,
  };
}