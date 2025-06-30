/**
 * Hook for loading provider settings with comprehensive error handling and resilience
 */

import { useCallback, useState, useRef, useEffect } from 'react';
import { 
  loadProviderConfigurations, 
  loadModelSelection,
  populateTestCacheFromProviders 
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
import {
  RetryManager,
  CircuitBreaker,
  GlobalErrorHandler,
  ErrorContextManager,
  NetworkError,
  TimeoutError,
  createUserFriendlyMessage,
  isRetryableError
} from '../utils/error-handling';

interface LoadAttempt {
  timestamp: Date;
  success: boolean;
  error?: Error;
  duration: number;
}

interface UseProviderLoaderReturn {
  isLoading: boolean;
  loadError: string | null;
  loadAttempts: LoadAttempt[];
  connectionStatus: 'online' | 'offline' | 'degraded';
  loadSettings: (testedProviders: Record<string, any>) => Promise<{
    providers: Record<string, ProviderConfiguration>;
    modelSelection: typeof DEFAULT_MODEL_SELECTION;
    savedState: SavedState;
  }>;
  retryLoad: (testedProviders: Record<string, any>) => Promise<void>;
  getLoadStatistics: () => {
    totalAttempts: number;
    successRate: number;
    averageLoadTime: number;
    lastSuccessfulLoad?: Date;
  };
}

export function useProviderLoader(): UseProviderLoaderReturn {
  const [isLoading, setIsLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadAttempts, setLoadAttempts] = useState<LoadAttempt[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<'online' | 'offline' | 'degraded'>('online');
  
  const isMounted = useIsMounted();
  const abortControllerRef = useRef<AbortController | null>(null);
  const deduplicatorRef = useRef<RequestDeduplicator<any>>(new RequestDeduplicator());
  const retryManagerRef = useRef(new RetryManager({
    maxAttempts: 5,
    baseDelayMs: 2000,
    maxDelayMs: 30000,
    backoffFactor: 1.5,
    onRetry: (attempt, error) => {
      console.log(`Retrying load operation, attempt ${attempt}:`, error.message);
      if (isMounted()) {
        setConnectionStatus('degraded');
      }
    }
  }));
  const circuitBreakerRef = useRef(new CircuitBreaker({
    failureThreshold: 3,
    resetTimeoutMs: 60000, // 1 minute
    monitoringPeriodMs: 300000 // 5 minutes
  }));
  const errorHandlerRef = useRef(GlobalErrorHandler.getInstance());
  const contextManagerRef = useRef(ErrorContextManager.getInstance());

  // Set error context
  useEffect(() => {
    contextManagerRef.current.setContext({
      component: 'useProviderLoader',
      operation: 'provider-settings-load'
    });
  }, []);

  // Monitor connection status
  useEffect(() => {
    const handleOnline = () => {
      if (isMounted()) {
        setConnectionStatus('online');
        circuitBreakerRef.current.reset();
      }
    };
    
    const handleOffline = () => {
      if (isMounted()) {
        setConnectionStatus('offline');
      }
    };
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    // Set initial status
    if (!navigator.onLine && isMounted()) {
      setConnectionStatus('offline');
    }
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [isMounted]);

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
      // Clear error context
      contextManagerRef.current.clearContext();
    };
  }, []);

  const loadSettings = useCallback(async (testedProviders: Record<string, any>) => {
    const startTime = Date.now();
    let attempt: LoadAttempt = {
      timestamp: new Date(),
      success: false,
      duration: 0
    };
    
    try {
      // Check circuit breaker
      return await circuitBreakerRef.current.execute(async () => {
        // Check connection status
        if (connectionStatus === 'offline') {
          throw new NetworkError('Device is offline');
        }
        
        // Cancel any previous load operation
        if (abortControllerRef.current) {
          abortControllerRef.current.abort();
        }

        // Create new abort controller for this load
        const abortController = createAbortController(45000); // 45 second timeout for resilience  
        abortControllerRef.current = abortController;

        if (isMounted()) {
          setIsLoading(true);
          setLoadError(null);
        }
        
        // Execute with retry logic
        return await retryManagerRef.current.execute(async () => {
          try {
            // Use deduplication for provider configurations
            const providersPromise = deduplicatorRef.current.deduplicate(
              'providers',
              async (_signal) => {
                // Pass abort signal to API call
                return await loadProviderConfigurations(testedProviders);
              },
              abortController.signal
            );

            // Use deduplication for model selection
            const modelSelectionPromise = deduplicatorRef.current.deduplicate(
              'modelSelection',
              async (_signal) => {
                // Pass abort signal to API call
                return await loadModelSelection();
              },
              abortController.signal
            );

            // Load both in parallel with timeout protection
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
            
            // Mark as successful
            attempt.success = true;
            attempt.duration = Date.now() - startTime;
            
            if (isMounted()) {
              setConnectionStatus('online');
              setLoadAttempts(prev => [...prev.slice(-9), attempt]); // Keep last 10 attempts
            }
            
            return {
              providers: allProviders,
              modelSelection,
              savedState,
            };
            
          } catch (loadError) {
            // Transform errors into appropriate types
            if (loadError instanceof Error) {
              if (loadError.name === 'AbortError') {
                throw new Error('Operation cancelled');
              }
              
              if (loadError.message.includes('network') || loadError.message.includes('fetch')) {
                throw new NetworkError(loadError.message);
              }
              
              if (loadError.message.includes('timeout')) {
                throw new TimeoutError('load-settings', 45000);
              }
            }
            
            throw loadError;
          }
        }, 'load-provider-settings', abortController.signal);
        
      }, 'load-settings-circuit');
      
    } catch (error) {
      // Record failed attempt
      attempt.success = false;
      attempt.duration = Date.now() - startTime;
      attempt.error = error instanceof Error ? error : new Error(String(error));
      
      if (isMounted()) {
        setLoadAttempts(prev => [...prev.slice(-9), attempt]);
      }
      
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
      
      // Handle error through global error handler
      await errorHandlerRef.current.handle(error as Error, {
        testedProviders,
        connectionStatus,
        circuitBreakerState: circuitBreakerRef.current.getState()
      });
      
      const errorMessage = createUserFriendlyMessage(error instanceof Error ? error : new Error(String(error)));
      
      if (isMounted()) {
        setLoadError(errorMessage);
        
        // Update connection status based on error type
        if (error instanceof NetworkError) {
          setConnectionStatus('offline');
        } else if (isRetryableError(error instanceof Error ? error : new Error(String(error)))) {
          setConnectionStatus('degraded');
        }
      }
      
      throw error;
    } finally {
      if (isMounted()) {
        setIsLoading(false);
      }
      // Clear abort controller reference
      const currentController = abortControllerRef.current;
      if (currentController) {
        abortControllerRef.current = null;
      }
    }
  }, [isMounted, connectionStatus]);

  const retryLoad = useCallback(async (testedProviders: Record<string, any>) => {
    // Clear any existing errors
    if (isMounted()) {
      setLoadError(null);
      setConnectionStatus('online');
    }
    
    // Reset circuit breaker
    circuitBreakerRef.current.reset();
    
    // Attempt to load again
    try {
      await loadSettings(testedProviders);
    } catch (error) {
      // Error is already handled in loadSettings
      console.log('Retry load failed:', error);
    }
  }, [loadSettings, isMounted]);
  
  const getLoadStatistics = useCallback(() => {
    const totalAttempts = loadAttempts.length;
    const successfulAttempts = loadAttempts.filter(a => a.success);
    const successRate = totalAttempts > 0 ? (successfulAttempts.length / totalAttempts) * 100 : 0;
    const averageLoadTime = successfulAttempts.length > 0 
      ? successfulAttempts.reduce((sum, a) => sum + a.duration, 0) / successfulAttempts.length
      : 0;
    const lastSuccessfulLoad = successfulAttempts.length > 0 
      ? successfulAttempts[successfulAttempts.length - 1]?.timestamp
      : undefined;
    
    return {
      totalAttempts,
      successRate,
      averageLoadTime,
      lastSuccessfulLoad
    };
  }, [loadAttempts]);

  return {
    isLoading,
    loadError,
    loadAttempts,
    connectionStatus,
    loadSettings,
    retryLoad,
    getLoadStatistics,
  };
}