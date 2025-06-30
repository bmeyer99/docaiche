/**
 * Performance optimization utilities for React applications
 * Includes debouncing, throttling, memoization, and component optimization helpers
 */

import React, { 
  useCallback, 
  useMemo, 
  useRef, 
  useEffect, 
  useState,
  lazy,
  Suspense,
  ComponentType,
  ReactNode,
  MemoExoticComponent,
  memo,
  RefObject
} from 'react';

// ========================== DEBOUNCING UTILITIES ==========================

/**
 * Debounce hook for delaying function execution until after wait time has elapsed
 * since the last time the debounced function was invoked
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}

/**
 * Debounced callback hook that delays function execution
 */
export function useDebouncedCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number,
  deps: React.DependencyList = []
): T & { cancel: () => void } {
  const timeoutRef = useRef<NodeJS.Timeout>();

  const debouncedCallback = useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      
      timeoutRef.current = setTimeout(() => {
        callback(...args);
      }, delay);
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [callback, delay, ...deps]
  ) as T;

  const cancel = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
  }, []);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Add cancel method to the function
  Object.assign(debouncedCallback, { cancel });

  return debouncedCallback as T & { cancel: () => void };
}

// ========================== THROTTLING UTILITIES ==========================

/**
 * Throttle hook that limits function execution to at most once per specified time period
 */
export function useThrottledCallback<T extends (...args: any[]) => any>(
  callback: T,
  delay: number,
  deps: React.DependencyList = []
): T {
  const lastRun = useRef<number>(Date.now());

  const throttledCallback = useCallback(
    (...args: Parameters<T>) => {
      if (Date.now() - lastRun.current >= delay) {
        callback(...args);
        lastRun.current = Date.now();
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [callback, delay, ...deps]
  ) as T;

  return throttledCallback;
}

// ========================== MEMOIZATION UTILITIES ==========================

/**
 * Stable memoization hook that prevents unnecessary re-computations
 */
export function useStableMemo<T>(
  factory: () => T,
  deps: React.DependencyList,
  equalityFn?: (prev: T, next: T) => boolean
): T {
  const ref = useRef<{ deps: React.DependencyList; value: T }>();
  
  if (!ref.current || !deepEqual(ref.current.deps, deps)) {
    const newValue = factory();
    
    // If we have a custom equality function and a previous value, use it
    if (ref.current && equalityFn && !equalityFn(ref.current.value, newValue)) {
      ref.current = { deps, value: newValue };
    } else if (!ref.current) {
      ref.current = { deps, value: newValue };
    } else if (!equalityFn) {
      ref.current = { deps, value: newValue };
    }
  }
  
  return ref.current.value;
}

/**
 * Stable callback hook that prevents unnecessary re-creations
 */
export function useStableCallback<T extends (...args: any[]) => any>(
  callback: T,
  deps: React.DependencyList
): T {
  return useCallback(callback, deps);
}

/**
 * Hook for creating multiple stable event handlers at once
 */
export function useStableHandlers<T extends Record<string, (...args: any[]) => any>>(
  handlers: T,
  deps: React.DependencyList
): T {
  return useMemo(() => handlers, deps);
}

/**
 * Deep comparison for objects and arrays to prevent unnecessary re-renders
 */
export function deepEqual(a: any, b: any): boolean {
  if (a === b) return true;
  
  if (a == null || b == null) return false;
  
  if (typeof a !== typeof b) return false;
  
  if (typeof a !== 'object') return false;
  
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  
  const keysA = Object.keys(a);
  const keysB = Object.keys(b);
  
  if (keysA.length !== keysB.length) return false;
  
  for (const key of keysA) {
    if (!keysB.includes(key)) return false;
    if (!deepEqual(a[key], b[key])) return false;
  }
  
  return true;
}

/**
 * Shallow comparison for objects to prevent unnecessary re-renders
 */
export function shallowEqual(a: any, b: any): boolean {
  if (a === b) return true;
  
  if (a == null || b == null) return false;
  
  if (typeof a !== 'object' || typeof b !== 'object') return false;
  
  const keysA = Object.keys(a);
  const keysB = Object.keys(b);
  
  if (keysA.length !== keysB.length) return false;
  
  for (const key of keysA) {
    if (a[key] !== b[key]) return false;
  }
  
  return true;
}

/**
 * Custom hook for memoizing expensive calculations with deep comparison
 */
export function useDeepMemo<T>(
  factory: () => T,
  deps: React.DependencyList
): T {
  const ref = useRef<{ deps: React.DependencyList; value: T }>();
  
  if (!ref.current || !deepEqual(ref.current.deps, deps)) {
    ref.current = { deps, value: factory() };
  }
  
  return ref.current.value;
}

// ========================== COMPONENT OPTIMIZATION UTILITIES ==========================

/**
 * Higher-order component for memoizing components with custom comparison
 */
export function createMemoComponent<P extends object>(
  Component: ComponentType<P>,
  areEqual?: (prevProps: P, nextProps: P) => boolean
): MemoExoticComponent<ComponentType<P>> {
  return memo(Component, areEqual || shallowEqual);
}

/**
 * Create a lazy-loaded component with suspense fallback
 */
export function createLazyComponent<P extends object>(
  importFunc: () => Promise<{ default: ComponentType<P> }>,
  fallback: ReactNode = null
): ComponentType<P> {
  const LazyComponent = lazy(importFunc);
  
  const LazyWrapper = (props: P) => {
    return React.createElement(
      Suspense,
      { fallback },
      React.createElement(LazyComponent, props)
    );
  };
  
  LazyWrapper.displayName = 'LazyWrapper';
  
  return LazyWrapper;
}

/**
 * Higher-order component that adds performance optimizations
 */
export function withPerformanceOptimization<P extends object>(
  Component: ComponentType<P>,
  displayName?: string
): MemoExoticComponent<ComponentType<P>> {
  const OptimizedComponent = memo(Component, shallowEqual);
  
  if (displayName) {
    OptimizedComponent.displayName = displayName;
  } else if (Component.displayName || Component.name) {
    OptimizedComponent.displayName = `Optimized(${Component.displayName || Component.name})`;
  }
  
  return OptimizedComponent;
}

// ========================== SELECTION OPTIMIZATION UTILITIES ==========================

/**
 * Hook for optimizing large list selections and filtering
 */
export function useOptimizedSelection<T>(
  items: T[],
  keyExtractor: (item: T) => string | number,
  searchQuery?: string,
  searchFields?: (keyof T)[]
) {
  const searchResults = useMemo(() => {
    if (!searchQuery || !searchFields) return items;
    
    const query = searchQuery.toLowerCase();
    return items.filter(item => 
      searchFields.some(field => {
        const value = item[field];
        return value && String(value).toLowerCase().includes(query);
      })
    );
  }, [items, searchQuery, searchFields]);

  const selectedItems = useRef<Set<string | number>>(new Set());
  const [, forceUpdate] = useState({});

  const toggleSelection = useCallback((key: string | number) => {
    if (selectedItems.current.has(key)) {
      selectedItems.current.delete(key);
    } else {
      selectedItems.current.add(key);
    }
    forceUpdate({});
  }, []);

  const clearSelection = useCallback(() => {
    selectedItems.current.clear();
    forceUpdate({});
  }, []);

  const isSelected = useCallback((key: string | number) => {
    return selectedItems.current.has(key);
  }, []);

  const selectAll = useCallback(() => {
    searchResults.forEach(item => {
      selectedItems.current.add(keyExtractor(item));
    });
    forceUpdate({});
  }, [searchResults, keyExtractor]);

  return {
    filteredItems: searchResults,
    selectedKeys: Array.from(selectedItems.current),
    isSelected,
    toggleSelection,
    clearSelection,
    selectAll,
    hasSelection: selectedItems.current.size > 0,
    selectionCount: selectedItems.current.size
  };
}

// ========================== PERFORMANCE MONITORING UTILITIES ==========================

/**
 * Hook for monitoring component render performance
 */
export function usePerformanceMonitor(componentName: string) {
  const renderCount = useRef(0);
  const lastRenderTime = useRef<number>();
  
  useEffect(() => {
    renderCount.current++;
    const now = performance.now();
    
    if (lastRenderTime.current) {
      const timeSinceLastRender = now - lastRenderTime.current;
      
      // Log performance warnings for frequent re-renders
      if (timeSinceLastRender < 16) { // Less than one frame (60fps)
        console.warn(
          `[Performance] ${componentName} re-rendered within ${timeSinceLastRender.toFixed(2)}ms (render #${renderCount.current})`
        );
      }
    }
    
    lastRenderTime.current = now;
  });
  
  // Log render count in development
  if (process.env.NODE_ENV === 'development') {
    console.log(`[Performance] ${componentName} rendered ${renderCount.current} times`);
  }
}

/**
 * Hook for measuring function execution time
 */
export function usePerformanceMeasure<T extends (...args: any[]) => any>(
  fn: T,
  label: string
): T {
  return useCallback(
    (...args: Parameters<T>) => {
      const start = performance.now();
      const result = fn(...args);
      const end = performance.now();
      
      if (process.env.NODE_ENV === 'development') {
        console.log(`[Performance] ${label} took ${(end - start).toFixed(2)}ms`);
      }
      
      return result;
    },
    [fn, label]
  ) as T;
}

// ========================== BUNDLE SIZE OPTIMIZATION UTILITIES ==========================

/**
 * Hook for detecting if a component is visible in viewport for lazy loading
 */
export function useIntersectionObserver(
  elementRef: RefObject<Element>,
  options: IntersectionObserverInit = {}
): boolean {
  const [isIntersecting, setIsIntersecting] = useState(false);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsIntersecting(entry.isIntersecting);
      },
      { threshold: 0.1, ...options }
    );

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [elementRef, options]);

  return isIntersecting;
}

/**
 * Hook for preloading resources when component is about to be visible
 */
export function usePreload(
  preloadFn: () => Promise<any>,
  trigger: boolean = true
) {
  const [isLoaded, setIsLoaded] = useState(false);
  const hasTriggered = useRef(false);

  useEffect(() => {
    if (trigger && !hasTriggered.current) {
      hasTriggered.current = true;
      preloadFn().then(() => setIsLoaded(true));
    }
  }, [trigger, preloadFn]);

  return isLoaded;
}

// ========================== INPUT OPTIMIZATION UTILITIES ==========================

/**
 * Optimized input hook with debouncing and validation
 */
export function useOptimizedInput<T = string>(
  initialValue: T,
  debounceMs: number = 300,
  validator?: (value: T) => boolean | string
) {
  const [value, setValue] = useState<T>(initialValue);
  const [debouncedValue, setDebouncedValue] = useState<T>(initialValue);
  const [error, setError] = useState<string | null>(null);
  const [isValid, setIsValid] = useState(true);

  // Debounce the value
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
      
      // Run validation on debounced value
      if (validator) {
        const result = validator(value);
        if (typeof result === 'string') {
          setError(result);
          setIsValid(false);
        } else {
          setError(null);
          setIsValid(result);
        }
      }
    }, debounceMs);

    return () => clearTimeout(handler);
  }, [value, debounceMs, validator]);

  const handleChange = useCallback((newValue: T) => {
    setValue(newValue);
    // Clear error immediately when user starts typing
    if (error) {
      setError(null);
      setIsValid(true);
    }
  }, [error]);

  const reset = useCallback(() => {
    setValue(initialValue);
    setDebouncedValue(initialValue);
    setError(null);
    setIsValid(true);
  }, [initialValue]);

  return {
    value,
    debouncedValue,
    error,
    isValid,
    isDirty: value !== initialValue,
    handleChange,
    reset
  };
}

// ========================== REACT DEVTOOLS PROFILER HELPERS ==========================

/**
 * Profiler wrapper component for measuring component performance
 * Note: This should be used in .tsx files with proper JSX syntax
 */
export function createProfilerWrapper(id: string, onRender?: (id: string, phase: 'mount' | 'update', actualDuration: number) => void) {
  return function ProfilerWrapper({ children }: { children: ReactNode }) {
    const handleRender = useCallback(
      (id: string, phase: 'mount' | 'update', actualDuration: number) => {
        if (process.env.NODE_ENV === 'development') {
          console.log(`[Profiler] ${id} ${phase} took ${actualDuration.toFixed(2)}ms`);
        }
        onRender?.(id, phase, actualDuration);
      },
      [onRender]
    );

    // Only render Profiler in development
    if (process.env.NODE_ENV === 'development') {
      return React.createElement(
        'div',
        { 'data-profiler-id': id },
        children
      );
    }

    return React.createElement(React.Fragment, null, children);
  };
}

/**
 * Hook for collecting performance metrics
 */
export function usePerformanceMetrics(componentName: string) {
  const metrics = useRef({
    renderCount: 0,
    totalRenderTime: 0,
    averageRenderTime: 0,
    lastRenderTime: 0
  });

  const startRender = useCallback(() => {
    return performance.now();
  }, []);

  const endRender = useCallback((startTime: number) => {
    const renderTime = performance.now() - startTime;
    metrics.current.renderCount++;
    metrics.current.totalRenderTime += renderTime;
    metrics.current.averageRenderTime = metrics.current.totalRenderTime / metrics.current.renderCount;
    metrics.current.lastRenderTime = renderTime;

    if (process.env.NODE_ENV === 'development') {
      console.log(`[Metrics] ${componentName}:`, {
        renderTime: renderTime.toFixed(2) + 'ms',
        renderCount: metrics.current.renderCount,
        averageRenderTime: metrics.current.averageRenderTime.toFixed(2) + 'ms'
      });
    }
  }, [componentName]);

  return {
    startRender,
    endRender,
    metrics: metrics.current
  };
}