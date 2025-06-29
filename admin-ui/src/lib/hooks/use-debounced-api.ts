/**
 * Debounced API Hook with Aggressive Circuit Breaking
 * 
 * Prevents API call spam by debouncing requests and implementing
 * immediate circuit breaking at the hook level.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useCircuitBreaker } from './use-circuit-breaker';

interface DebouncedApiOptions {
  debounceMs?: number;
  enabledCondition?: boolean;
  onSuccess?: (data: any) => void;
  onError?: (error: any) => void;
  immediate?: boolean; // Run immediately on mount
}

interface DebouncedApiResult<T> {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => void;
  canMakeRequest: boolean;
  circuitState: string;
}

export function useDebouncedApi<T>(
  apiCall: () => Promise<T>,
  identifier: string,
  options: DebouncedApiOptions = {}
): DebouncedApiResult<T> {
  const {
    debounceMs = 1000,
    enabledCondition = true,
    onSuccess,
    onError,
    immediate = true
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const debounceTimeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const lastCallTimeRef = useRef<number>(0);
  const requestCountRef = useRef<number>(0);
  const mountedRef = useRef(true);

  const circuitBreaker = useCircuitBreaker(identifier, {
    failureThreshold: 2, // Very aggressive - only 2 failures
    resetTimeoutMs: 60000, // 1 minute
  });

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (debounceTimeoutRef.current) {
        clearTimeout(debounceTimeoutRef.current);
      }
    };
  }, []);

  const executeApiCall = useCallback(async () => {
    if (!mountedRef.current) return;

    // Check circuit breaker first
    if (!circuitBreaker.canMakeRequest) {
      const state = circuitBreaker.getCircuitState();
      console.warn(`🚫 ${identifier}: Circuit breaker ${state} - blocking request #${requestCountRef.current + 1}`);
      
      setError(new Error(`Circuit breaker is ${state}`));
      setLoading(false);
      return;
    }

    // Rate limiting - prevent rapid fire requests
    const now = Date.now();
    if (now - lastCallTimeRef.current < 500) { // Minimum 500ms between calls
      console.warn(`⏱️ ${identifier}: Rate limited - too frequent requests`);
      return;
    }
    lastCallTimeRef.current = now;
    requestCountRef.current++;

    console.info(`📡 ${identifier}: Making API request #${requestCountRef.current}`);
    setLoading(true);
    setError(null);

    try {
      const result = await apiCall();
      
      if (!mountedRef.current) return;
      
      circuitBreaker.recordSuccess();
      setData(result);
      setError(null);
      onSuccess?.(result);
      
      console.info(`✅ ${identifier}: Request #${requestCountRef.current} succeeded`);
    } catch (err) {
      if (!mountedRef.current) return;
      
      const error = err as Error;
      circuitBreaker.recordFailure();
      setError(error);
      onError?.(error);
      
      console.error(`🔥 ${identifier}: Request #${requestCountRef.current} failed:`, error.message);
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [apiCall, identifier, circuitBreaker, onSuccess, onError]);

  const debouncedExecute = useCallback(() => {
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }

    debounceTimeoutRef.current = setTimeout(() => {
      executeApiCall();
    }, debounceMs);
  }, [executeApiCall, debounceMs]);

  const refetch = useCallback(() => {
    if (!enabledCondition) {
      console.warn(`🚫 ${identifier}: Refetch blocked - condition not met`);
      return;
    }
    
    // Clear any pending debounced calls
    if (debounceTimeoutRef.current) {
      clearTimeout(debounceTimeoutRef.current);
    }
    
    executeApiCall();
  }, [executeApiCall, enabledCondition, identifier]);

  // Initial call on mount
  useEffect(() => {
    if (immediate && enabledCondition) {
      if (circuitBreaker.canMakeRequest) {
        executeApiCall();
      } else {
        console.warn(`🚫 ${identifier}: Initial load blocked by circuit breaker`);
      }
    }
  }, [immediate, enabledCondition, identifier]); // Removed executeApiCall and circuitBreaker from deps to prevent loops

  return {
    data,
    loading,
    error,
    refetch,
    canMakeRequest: circuitBreaker.canMakeRequest,
    circuitState: circuitBreaker.getCircuitState(),
  };
}