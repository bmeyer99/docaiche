/**
 * React Hook for Circuit Breaker Pattern
 * 
 * Prevents components from making API calls when the backend is unavailable,
 * providing immediate feedback and preventing console spam.
 */

import { useState, useEffect, useRef, useCallback } from 'react';

interface CircuitBreakerState {
  isOpen: boolean;
  failureCount: number;
  lastFailureTime: number;
  lastSuccessTime: number;
  nextAttemptTime: number;
  isHalfOpen: boolean;
}

interface CircuitBreakerConfig {
  failureThreshold: number;
  resetTimeoutMs: number;
  monitorIntervalMs: number;
}

interface UseCircuitBreakerResult {
  isCircuitOpen: boolean;
  canMakeRequest: boolean;
  recordSuccess: () => void;
  recordFailure: () => void;
  getCircuitState: () => 'CLOSED' | 'OPEN' | 'HALF_OPEN';
  getTimeSinceLastFailure: () => number;
  resetCircuit: () => void;
}

const DEFAULT_CONFIG: CircuitBreakerConfig = {
  failureThreshold: 3, // Fail fast - only 3 failures
  resetTimeoutMs: 30000, // 30 seconds
  monitorIntervalMs: 5000, // Check every 5 seconds
};

// Global circuit breaker state for all components
const globalCircuitState = new Map<string, CircuitBreakerState>();

export function useCircuitBreaker(
  identifier: string,
  config: Partial<CircuitBreakerConfig> = {}
): UseCircuitBreakerResult {
  const finalConfig = { ...DEFAULT_CONFIG, ...config };
  const intervalRef = useRef<NodeJS.Timeout | undefined>(undefined);
  const [, forceUpdate] = useState({});

  // Initialize or get existing circuit state
  const getState = useCallback((): CircuitBreakerState => {
    if (!globalCircuitState.has(identifier)) {
      globalCircuitState.set(identifier, {
        isOpen: false,
        failureCount: 0,
        lastFailureTime: 0,
        lastSuccessTime: Date.now(),
        nextAttemptTime: 0,
        isHalfOpen: false,
      });
    }
    return globalCircuitState.get(identifier)!;
  }, [identifier]);

  const updateState = useCallback((updater: (state: CircuitBreakerState) => void) => {
    const state = getState();
    updater(state);
    globalCircuitState.set(identifier, state);
    forceUpdate({}); // Force re-render
  }, [identifier, getState]);

  // Monitor circuit state and automatically transition to half-open
  useEffect(() => {
    intervalRef.current = setInterval(() => {
      const state = getState();
      const now = Date.now();

      if (state.isOpen && now >= state.nextAttemptTime && !state.isHalfOpen) {
        updateState(s => {
          s.isHalfOpen = true;
          console.warn(`🔄 Circuit breaker for "${identifier}" entering HALF_OPEN state - allowing test request`);
        });
      }
    }, finalConfig.monitorIntervalMs);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [identifier, finalConfig.monitorIntervalMs, getState, updateState]);

  const recordSuccess = useCallback(() => {
    updateState(state => {
      const wasOpen = state.isOpen;
      state.failureCount = 0;
      state.isOpen = false;
      state.isHalfOpen = false;
      state.lastSuccessTime = Date.now();
      state.nextAttemptTime = 0;

      if (wasOpen) {
        console.info(`✅ Circuit breaker for "${identifier}" CLOSED - backend connection restored`);
      }
    });
  }, [identifier, updateState]);

  const recordFailure = useCallback(() => {
    updateState(state => {
      state.failureCount++;
      state.lastFailureTime = Date.now();

      if (state.failureCount >= finalConfig.failureThreshold) {
        if (!state.isOpen) {
          state.isOpen = true;
          state.nextAttemptTime = Date.now() + finalConfig.resetTimeoutMs;
          console.error(`🚫 Circuit breaker for "${identifier}" OPENED - backend connection failed after ${state.failureCount} attempts`);
          console.warn(`⏰ Next attempt allowed in ${finalConfig.resetTimeoutMs / 1000} seconds`);
        }
        state.isHalfOpen = false;
      } else if (state.isHalfOpen) {
        // Half-open test failed, go back to open
        state.isOpen = true;
        state.isHalfOpen = false;
        state.nextAttemptTime = Date.now() + finalConfig.resetTimeoutMs;
        console.warn(`⚠️ Circuit breaker for "${identifier}" test failed - returning to OPEN state`);
      }
    });
  }, [identifier, finalConfig.failureThreshold, finalConfig.resetTimeoutMs, updateState]);

  const getCircuitState = useCallback((): 'CLOSED' | 'OPEN' | 'HALF_OPEN' => {
    const state = getState();
    if (state.isHalfOpen) return 'HALF_OPEN';
    if (state.isOpen) return 'OPEN';
    return 'CLOSED';
  }, [getState]);

  const getTimeSinceLastFailure = useCallback((): number => {
    const state = getState();
    return state.lastFailureTime ? Date.now() - state.lastFailureTime : 0;
  }, [getState]);

  const resetCircuit = useCallback(() => {
    updateState(state => {
      state.isOpen = false;
      state.isHalfOpen = false;
      state.failureCount = 0;
      state.lastFailureTime = 0;
      state.nextAttemptTime = 0;
    });
    console.info(`🔄 Circuit breaker for "${identifier}" manually reset`);
  }, [identifier, updateState]);

  const state = getState();
  const canMakeRequest = !state.isOpen || state.isHalfOpen;
  const isCircuitOpen = state.isOpen;

  return {
    isCircuitOpen,
    canMakeRequest,
    recordSuccess,
    recordFailure,
    getCircuitState,
    getTimeSinceLastFailure,
    resetCircuit,
  };
}

/**
 * Higher-order function to wrap API calls with circuit breaker protection
 */
export function withCircuitBreaker<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  identifier: string,
  config?: Partial<CircuitBreakerConfig>
): T {
  return ((...args: any[]) => {
    const circuitBreaker = useCircuitBreaker(identifier, config);
    
    if (!circuitBreaker.canMakeRequest) {
      const state = circuitBreaker.getCircuitState();
      console.warn(`🚫 Request blocked by circuit breaker for "${identifier}" (state: ${state})`);
      return Promise.reject(new Error(`Circuit breaker is ${state} for ${identifier}`));
    }

    return fn(...args)
      .then((result: any) => {
        circuitBreaker.recordSuccess();
        return result;
      })
      .catch((error: any) => {
        circuitBreaker.recordFailure();
        throw error;
      });
  }) as T;
}