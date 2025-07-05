'use client';

/**
 * Centralized form state management hook for Search Configuration
 * 
 * This hook provides a single source of truth for all form state across
 * all search config tabs, with proper change detection and loading state management.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { useSearchConfig } from '../contexts/config-context';
import { useToast } from '@/hooks/use-toast';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { type ConfigurationResponse } from '@/lib/config/api';
import { produce } from 'immer';

/**
 * Helper function to get a value from an object using a path string
 */
function get(obj: any, path: string): any {
  return path.split('.').reduce((current, key) => current?.[key], obj);
}

/**
 * Helper function to set a value in an object using a path string
 */
function set(obj: any, path: string, value: any): void {
  const keys = path.split('.');
  const lastKey = keys.pop()!;
  const target = keys.reduce((current, key) => {
    if (!current[key]) current[key] = {};
    return current[key];
  }, obj);
  target[lastKey] = value;
}

/**
 * Helper function to deep clone an object
 */
function cloneDeep<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}

/**
 * Helper function to check if two values are deeply equal
 */
function isEqual(a: any, b: any): boolean {
  return JSON.stringify(a) === JSON.stringify(b);
}

/**
 * Source of a field update - used for change detection
 */
type UpdateSource = 'user' | 'system';

/**
 * Change tracking information for a field
 */
interface FieldChange {
  path: string;
  value: any;
  previousValue: any;
  source: UpdateSource;
  timestamp: number;
}

/**
 * Form state that combines all configuration sections
 */
interface FormState {
  // Vector Search
  vectorConfig: {
    enabled: boolean;
    base_url: string;
    api_key?: string;
    timeout_seconds: number;
    max_retries: number;
    verify_ssl: boolean;
  } | null;
  
  workspaces: Array<{
    id: string;
    name: string;
    enabled: boolean;
    priority: number;
    settings: Record<string, any>;
  }>;
  
  embeddingConfig: {
    useDefaultEmbedding: boolean;
    provider?: string;
    model?: string;
    dimensions?: number;
    chunkSize?: number;
    chunkOverlap?: number;
  } | null;
  
  // Text AI
  modelParameters: Record<string, Record<string, {
    temperature: number;
    topP: number;
    topK?: number;
    maxTokens: number;
    presencePenalty?: number;
    frequencyPenalty?: number;
    systemPrompt?: string;
  }>>;
  
  // Providers
  providers: Array<{
    id: string;
    type: string;
    name: string;
    enabled: boolean;
    priority: number;
    config: Record<string, any>;
    rate_limits?: {
      requests_per_minute: number;
      requests_per_day: number;
    };
    cost_limits?: {
      monthly_budget_usd: number;
      cost_per_request: number;
    };
  }>;
  
  // Ingestion
  ingestionRules: any[];
  ingestionSettings: any;
  
  // Monitoring
  alertRules: any[];
  dashboardUrls: any;
  
  // System Settings
  systemSettings: {
    queue_management?: {
      max_queue_depth: number;
      overflow_strategy: 'reject' | 'evict_oldest';
      priority_levels: number;
      stale_timeout_seconds: number;
    };
    timeouts?: {
      search_timeout_seconds: number;
      ai_timeout_seconds: number;
      provider_timeout_seconds: number;
      cache_ttl_seconds: number;
    };
    performance_thresholds?: {
      max_search_latency_ms: number;
      max_ai_latency_ms: number;
      min_cache_hit_rate: number;
      max_error_rate: number;
    };
    resource_limits?: {
      max_concurrent_searches: number;
      max_ai_calls_per_minute: number;
      max_provider_calls_per_minute: number;
      max_cache_size_mb: number;
    };
    feature_toggles?: {
      enable_external_search: boolean;
      enable_ai_evaluation: boolean;
      enable_query_refinement: boolean;
      enable_knowledge_ingestion: boolean;
      enable_result_caching: boolean;
    };
    advanced_settings?: {
      workspace_selection_strategy: string;
      result_ranking_algorithm: string;
      external_provider_priority: string[];
    };
  };
}

/**
 * Return type of the useSearchConfigForm hook
 */
interface UseSearchConfigFormReturn {
  // Form state
  formState: FormState;
  
  // Dirty state tracking (only true for user changes)
  isDirty: boolean;
  
  // Loading state
  isLoading: boolean;
  
  // Field update with source tracking
  updateField: (path: string, value: any, source?: UpdateSource) => void;
  
  // Batch update multiple fields
  updateFields: (updates: Array<{ path: string; value: any; source?: UpdateSource }>) => void;
  
  // Reset form to saved state
  resetForm: () => void;
  
  // Save all changes
  saveForm: () => Promise<void>;
  
  // Get specific field value
  getFieldValue: (path: string) => any;
  
  // Check if specific field is dirty
  isFieldDirty: (path: string) => boolean;
  
  // Get changes for a specific section
  getSectionChanges: (section: string) => FieldChange[];
}

/**
 * Centralized form state management hook
 */
export function useSearchConfigForm(): UseSearchConfigFormReturn {
  const config = useSearchConfig();
  const apiClient = useApiClient();
  const { toast } = useToast();
  
  // Form state
  const [formState, setFormState] = useState<FormState>({
    vectorConfig: null,
    workspaces: [],
    embeddingConfig: null,
    modelParameters: {},
    providers: [],
    ingestionRules: [],
    ingestionSettings: null,
    alertRules: [],
    dashboardUrls: null,
    systemSettings: {}
  });
  
  // Saved state for comparison
  const savedStateRef = useRef<FormState>(cloneDeep(formState));
  
  // Track changes with source information
  const changesRef = useRef<Map<string, FieldChange>>(new Map());
  
  // Track user changes only
  const userChangesRef = useRef<Set<string>>(new Set());
  
  // Loading state
  const [isLoading, setIsLoading] = useState(false);
  
  // Initialize form state from config context
  useEffect(() => {
    if (!config.isLoading && config.vectorConfig) {
      const initialState: FormState = {
        vectorConfig: config.vectorConfig,
        workspaces: config.workspaces || [],
        embeddingConfig: config.embeddingConfig,
        modelParameters: config.modelParameters || {},
        providers: [], // Will be loaded separately
        ingestionRules: config.ingestionRules || [],
        ingestionSettings: config.ingestionSettings,
        alertRules: config.alertRules || [],
        dashboardUrls: config.dashboardUrls,
        systemSettings: config.systemSettings || {}
      };
      
      setFormState(initialState);
      savedStateRef.current = cloneDeep(initialState);
      
      // Clear any previous changes when loading new data
      changesRef.current.clear();
      userChangesRef.current.clear();
    }
  }, [
    config.isLoading,
    config.vectorConfig,
    config.workspaces,
    config.embeddingConfig,
    config.modelParameters,
    config.ingestionRules,
    config.ingestionSettings,
    config.alertRules,
    config.dashboardUrls,
    config.systemSettings
  ]);
  
  /**
   * Update a single field with source tracking
   */
  const updateField = useCallback((path: string, value: any, source: UpdateSource = 'user') => {
    setFormState(prev => {
      const newState = cloneDeep(prev);
      const previousValue = get(newState, path);
      
      // Only update if value actually changed
      if (!isEqual(previousValue, value)) {
        set(newState, path, value);
        
        // Track the change
        const change: FieldChange = {
          path,
          value,
          previousValue,
          source,
          timestamp: Date.now()
        };
        
        changesRef.current.set(path, change);
        
        // Track user changes separately
        if (source === 'user') {
          userChangesRef.current.add(path);
        } else {
          // System changes remove the field from user changes
          userChangesRef.current.delete(path);
        }
      }
      
      return newState;
    });
  }, []);
  
  /**
   * Batch update multiple fields
   */
  const updateFields = useCallback((updates: Array<{ path: string; value: any; source?: UpdateSource }>) => {
    setFormState(prev => {
      const newState = cloneDeep(prev);
      
      updates.forEach(({ path, value, source = 'user' }) => {
        const previousValue = get(newState, path);
        
        if (!isEqual(previousValue, value)) {
          set(newState, path, value);
          
          const change: FieldChange = {
            path,
            value,
            previousValue,
            source,
            timestamp: Date.now()
          };
          
          changesRef.current.set(path, change);
          
          if (source === 'user') {
            userChangesRef.current.add(path);
          } else {
            userChangesRef.current.delete(path);
          }
        }
      });
      
      return newState;
    });
  }, []);
  
  /**
   * Get value of a specific field
   */
  const getFieldValue = useCallback((path: string) => {
    return get(formState, path);
  }, [formState]);
  
  /**
   * Check if a specific field has user changes
   */
  const isFieldDirty = useCallback((path: string) => {
    return userChangesRef.current.has(path);
  }, []);
  
  /**
   * Get changes for a specific section
   */
  const getSectionChanges = useCallback((section: string) => {
    const changes: FieldChange[] = [];
    
    changesRef.current.forEach((change, path) => {
      if (path.startsWith(section)) {
        changes.push(change);
      }
    });
    
    return changes;
  }, []);
  
  /**
   * Check if form has any user changes
   */
  const isDirty = userChangesRef.current.size > 0;
  
  /**
   * Reset form to saved state
   */
  const resetForm = useCallback(() => {
    setFormState(cloneDeep(savedStateRef.current));
    changesRef.current.clear();
    userChangesRef.current.clear();
    
    toast({
      title: "Form Reset",
      description: "All unsaved changes have been discarded"
    });
  }, [toast]);
  
  /**
   * Save all form changes
   */
  const saveForm = useCallback(async () => {
    setIsLoading(true);
    
    try {
      const savePromises: Promise<any>[] = [];
      
      // Save vector config
      if (formState.vectorConfig && userChangesRef.current.has('vectorConfig')) {
        savePromises.push(apiClient.updateWeaviateConfig(formState.vectorConfig));
      }
      
      // Save embedding config
      if (formState.embeddingConfig && userChangesRef.current.has('embeddingConfig')) {
        savePromises.push(apiClient.updateEmbeddingConfig(formState.embeddingConfig));
      }
      
      // Save model parameters
      Object.entries(formState.modelParameters).forEach(([provider, models]) => {
        Object.entries(models).forEach(([model, params]) => {
          const path = `modelParameters.${provider}.${model}`;
          if (userChangesRef.current.has(path)) {
            config.updateModelParameters(provider, model, params);
          }
        });
      });
      
      // Save system settings
      if (formState.systemSettings) {
        const systemPromises = Object.entries(formState.systemSettings)
          .map(([key, value]) => {
            const path = `systemSettings.${key}`;
            if (userChangesRef.current.has(path)) {
              return apiClient.updateConfiguration({
                key: `system.${key}`,
                value: value as Record<string, unknown>
              });
            }
            return null;
          })
          .filter((promise): promise is Promise<ConfigurationResponse> => promise !== null);
        
        savePromises.push(...systemPromises);
      }
      
      // Wait for all saves to complete
      await Promise.all(savePromises);
      
      // Update saved state
      savedStateRef.current = cloneDeep(formState);
      
      // Clear user changes
      userChangesRef.current.clear();
      
      // Keep system changes in the changes map but not in user changes
      const systemChanges = new Map<string, FieldChange>();
      changesRef.current.forEach((change, path) => {
        if (change.source === 'system') {
          systemChanges.set(path, change);
        }
      });
      changesRef.current = systemChanges;
      
      toast({
        title: "Configuration Saved",
        description: "All changes have been saved successfully"
      });
      
      // Reload configurations to ensure sync
      await config.reloadConfigurations();
    } catch (error) {
      console.error('[useSearchConfigForm] Save failed:', error);
      toast({
        title: "Save Failed",
        description: "Failed to save configuration changes",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  }, [formState, apiClient, config, toast]);
  
  return {
    formState,
    isDirty,
    isLoading: isLoading || config.isLoading,
    updateField,
    updateFields,
    resetForm,
    saveForm,
    getFieldValue,
    isFieldDirty,
    getSectionChanges
  };
}

/**
 * Hook to use form state for a specific section
 */
export function useSearchConfigSection<T>(
  sectionPath: string,
  defaultValue: T
): {
  value: T;
  setValue: (value: T, source?: UpdateSource) => void;
  isDirty: boolean;
  changes: FieldChange[];
} {
  const form = useSearchConfigForm();
  
  const value = form.getFieldValue(sectionPath) ?? defaultValue;
  
  const setValue = useCallback((newValue: T, source: UpdateSource = 'user') => {
    form.updateField(sectionPath, newValue, source);
  }, [form, sectionPath]);
  
  const isDirty = form.isFieldDirty(sectionPath);
  const changes = form.getSectionChanges(sectionPath);
  
  return {
    value,
    setValue,
    isDirty,
    changes
  };
}