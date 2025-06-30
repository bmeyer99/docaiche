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
  const timeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

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
  const ref = useRef<{ deps: React.DependencyList; value: T } | undefined>(undefined);
  
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
  const ref = useRef<{ deps: React.DependencyList; value: T } | undefined>(undefined);
  
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
  const lastRenderTime = useRef<number | undefined>(undefined);
  
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
 * Enhanced batch state updates to reduce re-renders
 */
export function useBatchedUpdates<T extends Record<string, any>>(
  initialState: T
): [T, (updates: Partial<T> | ((prev: T) => Partial<T>)) => void] {
  const [state, setState] = useState<T>(initialState);
  const batchedUpdateRef = useRef<{
    pendingUpdates: Partial<T>;
    timeoutId: NodeJS.Timeout | null;
  }>({ pendingUpdates: {}, timeoutId: null });

  const batchedSetState = useCallback((updates: Partial<T> | ((prev: T) => Partial<T>)) => {
    const currentUpdates = typeof updates === 'function' 
      ? updates({ ...state, ...batchedUpdateRef.current.pendingUpdates })
      : updates;

    // Merge with pending updates
    batchedUpdateRef.current.pendingUpdates = {
      ...batchedUpdateRef.current.pendingUpdates,
      ...currentUpdates
    };

    // Clear existing timeout
    if (batchedUpdateRef.current.timeoutId) {
      clearTimeout(batchedUpdateRef.current.timeoutId);
    }

    // Set new timeout to batch updates
    batchedUpdateRef.current.timeoutId = setTimeout(() => {
      setState(prevState => ({
        ...prevState,
        ...batchedUpdateRef.current.pendingUpdates
      }));
      batchedUpdateRef.current.pendingUpdates = {};
      batchedUpdateRef.current.timeoutId = null;
    }, 0); // Batch in next tick
  }, [state]);

  useEffect(() => {
    return () => {
      if (batchedUpdateRef.current.timeoutId) {
        clearTimeout(batchedUpdateRef.current.timeoutId);
      }
    };
  }, []);

  return [state, batchedSetState];
}

/**
 * Hook for smart component updates that skip unnecessary renders
 */
export function useSmartUpdate<T>(
  value: T,
  equalityFn: (prev: T, next: T) => boolean = shallowEqual,
  skipInitial: boolean = true
): [T, boolean] {
  const [currentValue, setCurrentValue] = useState<T>(value);
  const [hasChanged, setHasChanged] = useState(!skipInitial);
  
  useEffect(() => {
    if (!equalityFn(currentValue, value)) {
      setCurrentValue(value);
      setHasChanged(true);
    } else {
      setHasChanged(false);
    }
  }, [value, currentValue, equalityFn]);

  return [currentValue, hasChanged];
}

/**
 * Hook for efficiently managing large form state with minimal re-renders
 */
export function useOptimizedFormState<T extends Record<string, any>>(
  initialState: T,
  validator?: (state: T) => Record<string, string>
) {
  const [state, setState] = useBatchedUpdates(initialState);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touchedFields, setTouchedFields] = useState<Set<string>>(new Set());
  
  const validateField = useCallback((fieldName: string, value: any) => {
    if (!validator) return null;
    
    const testState = { ...state, [fieldName]: value };
    const validationErrors = validator(testState);
    return validationErrors[fieldName] || null;
  }, [validator, state]);

  const updateField = useCallback((fieldName: string, value: any) => {
    setState(prev => ({ ...prev, [fieldName]: value }));
    
    // Mark field as touched
    setTouchedFields(prev => new Set(Array.from(prev).concat(fieldName)));
    
    // Validate field if validator exists
    if (validator) {
      const fieldError = validateField(fieldName, value);
      if (fieldError) {
        setErrors(prev => ({
          ...prev,
          [fieldName]: fieldError
        }));
      } else {
        setErrors(prev => {
          const { [fieldName]: _, ...rest } = prev;
          return rest;
        });
      }
    }
  }, [setState, validator, validateField]);

  const updateFields = useCallback((updates: Partial<T>) => {
    setState(updates);
    
    // Mark all updated fields as touched
    const updatedFieldNames = Object.keys(updates);
    setTouchedFields(prev => new Set(Array.from(prev).concat(updatedFieldNames)));
    
    // Validate all updated fields
    if (validator) {
      const newErrors: Record<string, string> = {};
      updatedFieldNames.forEach(fieldName => {
        const fieldError = validateField(fieldName, updates[fieldName]);
        if (fieldError) {
          newErrors[fieldName] = fieldError;
        }
      });
      setErrors(prev => ({ ...prev, ...newErrors }));
    }
  }, [setState, validator, validateField]);

  const validateAllFields = useCallback(() => {
    if (!validator) return {};
    
    const allErrors = validator(state);
    setErrors(allErrors);
    return allErrors;
  }, [validator, state]);

  const resetForm = useCallback(() => {
    setState(initialState);
    setErrors({});
    setTouchedFields(new Set());
  }, [setState, initialState]);

  const isFieldTouched = useCallback((fieldName: string) => {
    return touchedFields.has(fieldName);
  }, [touchedFields]);

  const hasErrors = useMemo(() => {
    return Object.keys(errors).some(key => !!errors[key]);
  }, [errors]);

  const isDirty = useMemo(() => {
    return !shallowEqual(state, initialState);
  }, [state, initialState]);

  return {
    state,
    errors,
    touchedFields: touchedFields,
    updateField,
    updateFields,
    validateAllFields,
    resetForm,
    isFieldTouched,
    hasErrors,
    isDirty
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

// ========================== ADVANCED PERFORMANCE MONITORING ==========================

/**
 * Performance monitoring store for tracking app-wide metrics
 */
class PerformanceMonitoringStore {
  private metrics: Map<string, {
    renderCount: number;
    totalTime: number;
    averageTime: number;
    maxTime: number;
    minTime: number;
    lastRenderTime: number;
    warnings: string[];
  }> = new Map();

  private bundleMetrics = {
    initialLoadTime: 0,
    chunkLoadTimes: new Map<string, number>(),
    totalBundleSize: 0,
    loadedChunks: new Set<string>()
  };

  recordRender(componentName: string, renderTime: number) {
    const existing = this.metrics.get(componentName) || {
      renderCount: 0,
      totalTime: 0,
      averageTime: 0,
      maxTime: 0,
      minTime: Infinity,
      lastRenderTime: 0,
      warnings: []
    };

    existing.renderCount++;
    existing.totalTime += renderTime;
    existing.averageTime = existing.totalTime / existing.renderCount;
    existing.maxTime = Math.max(existing.maxTime, renderTime);
    existing.minTime = Math.min(existing.minTime, renderTime);
    existing.lastRenderTime = renderTime;

    // Add performance warnings
    if (renderTime > 16) {
      existing.warnings.push(`Slow render: ${renderTime.toFixed(2)}ms at ${new Date().toISOString()}`);
      // Keep only last 10 warnings
      if (existing.warnings.length > 10) {
        existing.warnings.shift();
      }
    }

    this.metrics.set(componentName, existing);

    // Log warnings in development
    if (process.env.NODE_ENV === 'development' && renderTime > 16) {
      console.warn(`[Performance Warning] ${componentName} took ${renderTime.toFixed(2)}ms to render`);
    }
  }

  recordBundleLoad(chunkName: string, loadTime: number, size?: number) {
    this.bundleMetrics.chunkLoadTimes.set(chunkName, loadTime);
    this.bundleMetrics.loadedChunks.add(chunkName);
    
    if (size) {
      this.bundleMetrics.totalBundleSize += size;
    }

    if (process.env.NODE_ENV === 'development') {
      console.log(`[Bundle] ${chunkName} loaded in ${loadTime.toFixed(2)}ms${size ? ` (${(size / 1024).toFixed(2)}KB)` : ''}`);
    }
  }

  getMetrics() {
    return {
      components: Object.fromEntries(this.metrics),
      bundle: this.bundleMetrics
    };
  }

  getSlowComponents(threshold: number = 16) {
    return Array.from(this.metrics.entries())
      .filter(([, metrics]) => metrics.averageTime > threshold)
      .sort(([, a], [, b]) => b.averageTime - a.averageTime);
  }

  getComponentReport(componentName: string) {
    return this.metrics.get(componentName);
  }

  generatePerformanceReport() {
    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalComponents: this.metrics.size,
        slowComponents: this.getSlowComponents().length,
        totalBundleSize: (this.bundleMetrics.totalBundleSize / 1024).toFixed(2) + 'KB',
        loadedChunks: this.bundleMetrics.loadedChunks.size
      },
      slowComponents: this.getSlowComponents().map(([name, metrics]) => ({
        name,
        averageTime: metrics.averageTime.toFixed(2) + 'ms',
        maxTime: metrics.maxTime.toFixed(2) + 'ms',
        renderCount: metrics.renderCount,
        warnings: metrics.warnings.length
      })),
      bundleMetrics: {
        totalSize: (this.bundleMetrics.totalBundleSize / 1024).toFixed(2) + 'KB',
        chunkCount: this.bundleMetrics.loadedChunks.size,
        slowestChunks: Array.from(this.bundleMetrics.chunkLoadTimes.entries())
          .sort(([, a], [, b]) => b - a)
          .slice(0, 5)
          .map(([name, time]) => ({ name, time: time.toFixed(2) + 'ms' }))
      }
    };

    return report;
  }

  clear() {
    this.metrics.clear();
    this.bundleMetrics.chunkLoadTimes.clear();
    this.bundleMetrics.loadedChunks.clear();
    this.bundleMetrics.totalBundleSize = 0;
  }
}

// Global performance monitoring instance
const performanceStore = new PerformanceMonitoringStore();

/**
 * Hook for advanced performance monitoring with detailed reporting
 */
export function useAdvancedPerformanceMonitor(componentName: string, options: {
  enableReporting?: boolean;
  threshold?: number;
  enableMemoryTracking?: boolean;
} = {}) {
  const { enableReporting = true, threshold = 16, enableMemoryTracking = false } = options;
  const renderStartTime = useRef<number | undefined>(undefined);
  const memoryUsageRef = useRef<number | undefined>(undefined);

  useEffect(() => {
    if (enableMemoryTracking && 'memory' in performance) {
      memoryUsageRef.current = (performance as any).memory.usedJSHeapSize;
    }
  });

  useEffect(() => {
    renderStartTime.current = performance.now();
    
    return () => {
      if (renderStartTime.current) {
        const renderTime = performance.now() - renderStartTime.current;
        
        if (enableReporting) {
          performanceStore.recordRender(componentName, renderTime);
        }

        if (enableMemoryTracking && 'memory' in performance && memoryUsageRef.current) {
          const currentMemory = (performance as any).memory.usedJSHeapSize;
          const memoryDiff = currentMemory - memoryUsageRef.current;
          
          if (Math.abs(memoryDiff) > 1024 * 1024) { // 1MB threshold
            console.log(`[Memory] ${componentName} changed memory usage by ${(memoryDiff / 1024 / 1024).toFixed(2)}MB`);
          }
        }
      }
    };
  });

  const getComponentMetrics = useCallback(() => {
    return performanceStore.getComponentReport(componentName);
  }, [componentName]);

  const generateReport = useCallback(() => {
    return performanceStore.generatePerformanceReport();
  }, []);

  return {
    getComponentMetrics,
    generateReport,
    clearMetrics: () => performanceStore.clear()
  };
}

/**
 * Hook for tracking bundle loading performance
 */
export function useBundlePerformanceTracker() {
  const trackChunkLoad = useCallback((chunkName: string, loadPromise: Promise<any>) => {
    const startTime = performance.now();
    
    return loadPromise.then(
      (result) => {
        const loadTime = performance.now() - startTime;
        performanceStore.recordBundleLoad(chunkName, loadTime);
        return result;
      },
      (error) => {
        const loadTime = performance.now() - startTime;
        performanceStore.recordBundleLoad(chunkName, loadTime);
        throw error;
      }
    );
  }, []);

  const trackInitialLoad = useCallback(() => {
    const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
    performanceStore.recordBundleLoad('initial', loadTime);
  }, []);

  return {
    trackChunkLoad,
    trackInitialLoad
  };
}

/**
 * Hook for virtual scrolling optimization
 */
export function useVirtualScrolling<T>({
  items,
  itemHeight,
  containerHeight,
  overscan = 5
}: {
  items: T[];
  itemHeight: number;
  containerHeight: number;
  overscan?: number;
}) {
  const [scrollTop, setScrollTop] = useState(0);

  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const endIndex = Math.min(
    items.length - 1,
    Math.ceil((scrollTop + containerHeight) / itemHeight) + overscan
  );

  const visibleItems = useMemo(() => {
    return items.slice(startIndex, endIndex + 1).map((item, index) => ({
      item,
      index: startIndex + index
    }));
  }, [items, startIndex, endIndex]);

  const totalHeight = items.length * itemHeight;
  const offsetY = startIndex * itemHeight;

  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(event.currentTarget.scrollTop);
  }, []);

  return {
    visibleItems,
    totalHeight,
    offsetY,
    handleScroll
  };
}

/**
 * Hook for optimizing expensive computations with Web Workers
 */
export function useWebWorkerComputation<T, R>(
  computation: (data: T) => R,
  dependencies: React.DependencyList
): [(data: T) => Promise<R>, boolean] {
  const [isLoading, setIsLoading] = useState(false);
  const workerRef = useRef<Worker | undefined>(undefined);

  useEffect(() => {
    // Create worker from function
    const workerCode = `
      self.onmessage = function(e) {
        const { data } = e.data;
        try {
          const result = (${computation.toString()})(data);
          self.postMessage({ result });
        } catch (error) {
          self.postMessage({ error: error.message });
        }
      };
    `;

    const blob = new Blob([workerCode], { type: 'application/javascript' });
    const blobUrl = URL.createObjectURL(blob);
    workerRef.current = new Worker(blobUrl);

    return () => {
      if (workerRef.current) {
        workerRef.current.terminate();
        URL.revokeObjectURL(blobUrl);
      }
    };
  }, dependencies);

  const runComputation = useCallback(async (data: T): Promise<R> => {
    if (!workerRef.current) {
      throw new Error('Worker not initialized');
    }

    setIsLoading(true);

    return new Promise((resolve, reject) => {
      const handleMessage = (e: MessageEvent) => {
        workerRef.current?.removeEventListener('message', handleMessage);
        setIsLoading(false);

        if (e.data.error) {
          reject(new Error(e.data.error));
        } else {
          resolve(e.data.result);
        }
      };

      workerRef.current?.addEventListener('message', handleMessage);
      workerRef.current?.postMessage({ data });
    });
  }, []);

  return [runComputation, isLoading];
}

// Export performance monitoring store for advanced usage
export { performanceStore };