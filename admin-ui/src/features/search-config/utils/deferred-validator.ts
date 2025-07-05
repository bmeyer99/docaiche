'use client';

import { useEffect, useState, useRef, useCallback } from 'react';

/**
 * Deferred Validation System
 * 
 * This system ensures validation only runs after all required data is loaded,
 * preventing false warnings like "No AI providers configured" during initial load.
 */

import { 
  ValidationResult, 
  validateSearchConfig,
  ValidationError 
} from '@/lib/utils/config-validator';

interface ValidationRequest {
  id: string;
  timestamp: number;
  params: ValidationParams;
  resolve: (result: ValidationResult) => void;
  reject: (error: Error) => void;
}

interface ValidationParams {
  vectorConfig: any;
  embeddingConfig: any;
  modelSelection: any;
  modelParameters: any;
  providers: any;
}

interface LoadingStates {
  providers?: boolean;
  vectorConfig?: boolean;
  embeddingConfig?: boolean;
  modelSelection?: boolean;
  modelParameters?: boolean;
}

interface ValidationCache {
  key: string;
  result: ValidationResult;
  timestamp: number;
}

export class DeferredValidator {
  private queue: ValidationRequest[] = [];
  private cache: ValidationCache | null = null;
  private loadingStates: LoadingStates = {};
  private processTimer: NodeJS.Timeout | null = null;
  private readonly CACHE_TTL = 1000; // 1 second cache TTL
  private readonly PROCESS_DELAY = 100; // 100ms delay before processing

  /**
   * Update loading states for different data sources
   */
  updateLoadingState(states: LoadingStates) {
    this.loadingStates = { ...this.loadingStates, ...states };
    
    // If all data is loaded, process the queue
    if (this.isAllDataLoaded()) {
      this.scheduleProcessing();
    }
  }

  /**
   * Check if all required data is loaded and available
   */
  private isAllDataLoaded(): boolean {
    const states = this.loadingStates;
    
    // All these should be explicitly false (not undefined or true)
    return states.providers === false &&
           states.vectorConfig === false &&
           states.embeddingConfig === false &&
           states.modelSelection === false &&
           states.modelParameters === false;
  }

  /**
   * Check if data is available and not empty (to distinguish from API failures)
   */
  private isDataAvailable(params: ValidationParams): boolean {
    // If providers is null/undefined or empty object, it means API failed
    if (!params.providers || (typeof params.providers === 'object' && Object.keys(params.providers).length === 0)) {
      return false;
    }
    return true;
  }

  /**
   * Generate a cache key from validation parameters
   */
  private generateCacheKey(params: ValidationParams): string {
    // Create a stable key based on the actual data
    const keyData = {
      providers: Object.keys(params.providers || {}).sort().join(','),
      providerStatuses: Object.entries(params.providers || {})
        .map(([id, config]: [string, any]) => `${id}:${config?.status || 'none'}`)
        .sort()
        .join(','),
      vectorEnabled: params.vectorConfig?.enabled || false,
      vectorUrl: params.vectorConfig?.base_url || '',
      embeddingProvider: params.embeddingConfig?.provider || '',
      embeddingModel: params.embeddingConfig?.model || '',
      textProvider: params.modelSelection?.textGeneration?.provider || '',
      textModel: params.modelSelection?.textGeneration?.model || '',
    };
    
    return JSON.stringify(keyData);
  }

  /**
   * Check if cached result is still valid
   */
  private isCacheValid(cacheKey: string): boolean {
    if (!this.cache) return false;
    
    const now = Date.now();
    const isExpired = now - this.cache.timestamp > this.CACHE_TTL;
    const keyMatches = this.cache.key === cacheKey;
    
    return !isExpired && keyMatches;
  }

  /**
   * Schedule processing of the validation queue
   */
  private scheduleProcessing() {
    // Clear any existing timer
    if (this.processTimer) {
      clearTimeout(this.processTimer);
    }
    
    // Schedule processing with a small delay to batch requests
    this.processTimer = setTimeout(() => {
      this.processQueue();
    }, this.PROCESS_DELAY);
  }

  /**
   * Process all queued validation requests
   */
  private processQueue() {
    if (!this.isAllDataLoaded() || this.queue.length === 0) {
      return;
    }

    // Process all requests in the queue
    const requests = [...this.queue];
    this.queue = [];

    for (const request of requests) {
      try {
        const cacheKey = this.generateCacheKey(request.params);
        
        // Check cache first
        if (this.isCacheValid(cacheKey)) {
          request.resolve(this.cache!.result);
          continue;
        }

        // Check if data is actually available before validating
        if (!this.isDataAvailable(request.params)) {
          // Return a special validation result indicating data is not available
          const result: ValidationResult = {
            isValid: true, // Don't show errors if we can't load data
            errors: [],
            warnings: [{
              field: 'data_loading',
              message: 'Configuration data is currently unavailable. Please check your connection.',
              severity: 'warning' as const,
              suggestion: 'Refresh the page or check your network connection'
            }]
          };
          
          // Cache this result briefly
          this.cache = {
            key: cacheKey,
            result,
            timestamp: Date.now()
          };
          
          request.resolve(result);
          continue;
        }

        // Perform validation
        const result = validateSearchConfig(
          request.params.vectorConfig,
          request.params.embeddingConfig,
          request.params.modelSelection,
          request.params.modelParameters,
          request.params.providers
        );

        // Update cache
        this.cache = {
          key: cacheKey,
          result,
          timestamp: Date.now()
        };

        request.resolve(result);
      } catch (error) {
        request.reject(error as Error);
      }
    }
  }

  /**
   * Request validation with automatic deferral
   */
  async validate(params: ValidationParams): Promise<ValidationResult> {
    // If all data is loaded, check cache first
    if (this.isAllDataLoaded()) {
      const cacheKey = this.generateCacheKey(params);
      if (this.isCacheValid(cacheKey)) {
        return Promise.resolve(this.cache!.result);
      }
    }

    // Create a promise that will be resolved when validation completes
    return new Promise<ValidationResult>((resolve, reject) => {
      const request: ValidationRequest = {
        id: `${Date.now()}-${Math.random()}`,
        timestamp: Date.now(),
        params,
        resolve,
        reject
      };

      this.queue.push(request);

      // If all data is loaded, process immediately
      if (this.isAllDataLoaded()) {
        this.scheduleProcessing();
      }
    });
  }

  /**
   * Invalidate the cache (e.g., when configuration changes)
   */
  invalidateCache() {
    this.cache = null;
  }

  /**
   * Clear all pending validations
   */
  clearQueue() {
    // Reject all pending requests
    for (const request of this.queue) {
      request.reject(new Error('Validation cancelled'));
    }
    this.queue = [];
    
    // Clear the processing timer
    if (this.processTimer) {
      clearTimeout(this.processTimer);
      this.processTimer = null;
    }
  }

  /**
   * Get a default "loading" validation result
   */
  static getLoadingResult(): ValidationResult {
    return {
      isValid: true,
      errors: [],
      warnings: []
    };
  }

  /**
   * Create a validation result with a loading message
   */
  static getLoadingMessage(): ValidationResult {
    return {
      isValid: true,
      errors: [],
      warnings: [{
        field: 'loading',
        message: 'Loading configuration data...',
        severity: 'info' as const,
        suggestion: 'Please wait while data is being loaded'
      }]
    };
  }
}

// Create a singleton instance
let validatorInstance: DeferredValidator | null = null;

/**
 * Get or create the deferred validator instance
 */
export function getDeferredValidator(): DeferredValidator {
  if (!validatorInstance) {
    validatorInstance = new DeferredValidator();
  }
  return validatorInstance;
}

// React imports moved to top of file
// Hook implementation below

interface UseDeferredValidationOptions {
  vectorConfig: any;
  embeddingConfig: any;
  modelSelection: any;
  modelParameters: any;
  providers: any;
  isLoading?: {
    providers?: boolean;
    vectorConfig?: boolean;
    embeddingConfig?: boolean;
    modelSelection?: boolean;
    modelParameters?: boolean;
  };
}

export function useDeferredValidation({
  vectorConfig,
  embeddingConfig,
  modelSelection,
  modelParameters,
  providers,
  isLoading = {}
}: UseDeferredValidationOptions): ValidationResult {
  const [validation, setValidation] = useState<ValidationResult>(
    DeferredValidator.getLoadingResult()
  );
  const validatorRef = useRef(getDeferredValidator());
  const isMountedRef = useRef(true);

  // Update loading states
  useEffect(() => {
    validatorRef.current.updateLoadingState(isLoading);
  }, [isLoading]);

  // Perform validation
  const performValidation = useCallback(async () => {
    try {
      const result = await validatorRef.current.validate({
        vectorConfig,
        embeddingConfig,
        modelSelection,
        modelParameters,
        providers
      });

      // Only update state if component is still mounted
      if (isMountedRef.current) {
        setValidation(result);
      }
    } catch (error) {
      // Handle validation errors gracefully
      if (isMountedRef.current && error instanceof Error && error.message !== 'Validation cancelled') {
        console.error('Validation error:', error);
        setValidation({
          isValid: false,
          errors: [{
            field: 'validation',
            message: 'Failed to validate configuration',
            severity: 'error',
            suggestion: 'Please refresh and try again'
          }],
          warnings: []
        });
      }
    }
  }, [vectorConfig, embeddingConfig, modelSelection, modelParameters, providers]);

  // Trigger validation when data changes
  useEffect(() => {
    performValidation();
  }, [performValidation]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      // Don't clear the queue here as other components might be using it
    };
  }, []);

  // Show loading state if any data is still loading
  const anyLoading = Object.values(isLoading).some(loading => loading === true);
  if (anyLoading) {
    return DeferredValidator.getLoadingMessage();
  }

  return validation;
}

/**
 * Utility to check if validation has real issues (not just loading)
 */
export function hasRealValidationIssues(validation: ValidationResult): boolean {
  const hasRealErrors = validation.errors.length > 0;
  const hasRealWarnings = validation.warnings.some(w => w.field !== 'loading');
  return hasRealErrors || hasRealWarnings;
}