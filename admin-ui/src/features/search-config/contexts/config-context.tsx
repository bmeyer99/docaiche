'use client';

/**
 * Context for centralized configuration management
 * Loads all configurations at page load and provides them to tabs
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';
import { useModelSelection } from '@/lib/hooks/use-provider-settings';

interface VectorConfig {
  enabled: boolean;
  base_url: string;
  api_key?: string;
  timeout_seconds: number;
  max_retries: number;
  verify_ssl: boolean;
  connected?: boolean;
  version?: string;
  workspaces_count?: number;
  message?: string;
}

interface EmbeddingConfig {
  useDefaultEmbedding: boolean;
  provider?: string;
  model?: string;
  dimensions?: number;
  chunkSize?: number;
  chunkOverlap?: number;
}

interface ModelParameters {
  temperature: number;
  topP: number;
  topK?: number;
  maxTokens: number;
  presencePenalty?: number;
  frequencyPenalty?: number;
  systemPrompt?: string;
}

interface LoadingState {
  // Overall loading state
  isLoading: boolean;
  
  // Individual data source loading states
  providersLoaded: boolean;
  configLoaded: boolean;
  modelsLoaded: boolean;
  vectorConfigLoaded: boolean;
  workspacesLoaded: boolean;
  
  // Error tracking
  loadError: string | null;
  
  // Computed property helpers
  allDataLoaded: boolean;
}

interface ConfigState {
  // Vector Search
  vectorConfig: VectorConfig | null;
  workspaces: any[];
  embeddingConfig: EmbeddingConfig | null;
  
  // Text AI
  modelParameters: Record<string, Record<string, ModelParameters>>;
  availableProviders: string[];
  availableModels: Record<string, string[]>;
  
  // Ingestion
  ingestionRules: any[];
  ingestionSettings: any;
  
  // Monitoring
  alertRules: any[];
  dashboardUrls: any;
  
  // System Settings
  systemSettings: any;
  
  // Loading state
  loading: LoadingState;
}

interface ConfigContextValue extends ConfigState {
  // Update methods
  updateVectorConfig: (config: VectorConfig) => void;
  updateEmbeddingConfig: (config: EmbeddingConfig) => Promise<void>;
  updateModelParameters: (provider: string, model: string, params: ModelParameters) => Promise<void>;
  updateIngestionRules: (rules: any[]) => void;
  updateIngestionSettings: (settings: any) => void;
  updateAlertRules: (rules: any[]) => void;
  updateSystemSettings: (settings: any) => void;
  
  // Reload all configurations
  reloadConfigurations: () => Promise<void>;
  
  // Loading state helpers (for easier access)
  isLoading: boolean;
  allDataLoaded: boolean;
  loadError: string | null;
}

const ConfigContext = createContext<ConfigContextValue | null>(null);

export function useSearchConfig() {
  const context = useContext(ConfigContext);
  if (!context) {
    throw new Error('useSearchConfig must be used within ConfigProvider');
  }
  return context;
}

interface ConfigProviderProps {
  children: ReactNode;
}

export function ConfigProvider({ children }: ConfigProviderProps) {
  const apiClient = useApiClient();
  const { toast } = useToast();
  const { modelSelection, updateModelSelection } = useModelSelection();
  
  const [state, setState] = useState<ConfigState>({
    vectorConfig: null,
    workspaces: [],
    embeddingConfig: null,
    modelParameters: {},
    availableProviders: [],
    availableModels: {},
    ingestionRules: [],
    ingestionSettings: null,
    alertRules: [],
    dashboardUrls: null,
    systemSettings: null,
    loading: {
      isLoading: true,
      providersLoaded: false,
      configLoaded: false,
      modelsLoaded: false,
      vectorConfigLoaded: false,
      workspacesLoaded: false,
      loadError: null,
      allDataLoaded: false
    }
  });
  
  // Load all configurations on mount
  useEffect(() => {
    loadAllConfigurations();
  }, []);
  
  // Helper to update individual loading states
  const updateLoadingState = (updates: Partial<LoadingState>) => {
    setState(prev => ({
      ...prev,
      loading: {
        ...prev.loading,
        ...updates,
        // Recompute allDataLoaded
        allDataLoaded: updates.allDataLoaded !== undefined ? updates.allDataLoaded : (
          prev.loading.providersLoaded &&
          prev.loading.configLoaded &&
          prev.loading.modelsLoaded &&
          prev.loading.vectorConfigLoaded &&
          prev.loading.workspacesLoaded
        )
      }
    }));
  };
  
  const loadAllConfigurations = async () => {
    // Reset loading state
    setState(prev => ({ 
      ...prev, 
      loading: {
        ...prev.loading,
        isLoading: true, 
        loadError: null,
        providersLoaded: false,
        configLoaded: false,
        modelsLoaded: false,
        vectorConfigLoaded: false,
        workspacesLoaded: false,
        allDataLoaded: false
      }
    }));
    
    try {
      // Load providers and models from saved configuration
      let availableProviders: string[] = [];
      let availableModels: Record<string, string[]> = {};
      
      try {
        // Get provider configurations which includes models
        const providerConfigs = await apiClient.getProviderConfigurations();
        
        // Extract provider IDs and models from the configurations
        availableProviders = providerConfigs.map(p => p.id);
        
        // Build models map from provider configurations
        providerConfigs.forEach(provider => {
          availableModels[provider.id] = provider.models || [];
        });
        
        console.log('[ConfigProvider] Loaded providers and models from saved config:', {
          providers: availableProviders,
          modelCounts: Object.entries(availableModels).map(([id, models]) => `${id}: ${models.length}`)
        });
        
        setState(prev => ({ 
          ...prev, 
          availableProviders,
          availableModels,
          loading: { ...prev.loading, providersLoaded: true, modelsLoaded: true }
        }));
      } catch (error) {
        console.error('[ConfigProvider] Failed to load providers:', error);
        setState(prev => ({ 
          ...prev, 
          loading: { ...prev.loading, providersLoaded: true, modelsLoaded: true }
        }));
      }
      
      // Load central configuration
      let configs: any = {};
      try {
        const centralConfig = await apiClient.getConfiguration();
        console.log('[ConfigProvider] Loaded central configuration');
        configs = extractConfigurationsFromCentral(centralConfig);
        
        // Synchronize model selections with ProviderSettingsProvider
        if (configs.modelSelections && updateModelSelection) {
          const hasTextGeneration = configs.modelSelections.textGeneration?.provider && configs.modelSelections.textGeneration?.model;
          const hasEmbeddings = configs.modelSelections.embeddings?.provider && configs.modelSelections.embeddings?.model;
          
          if (hasTextGeneration || hasEmbeddings) {
            console.log('[ConfigProvider] Synchronizing model selections with ProviderSettingsProvider:', configs.modelSelections);
            updateModelSelection(configs.modelSelections);
          }
        }
        
        setState(prev => ({ 
          ...prev, 
          loading: { ...prev.loading, configLoaded: true }
        }));
      } catch (error) {
        console.error('[ConfigProvider] Failed to load central configuration:', error);
        setState(prev => ({ 
          ...prev, 
          loading: { ...prev.loading, configLoaded: true }
        }));
      }
      
      // Load service-specific data
      const [
        vectorConfig,
        workspaces
      ] = await Promise.allSettled([
        apiClient.getWeaviateConfig(),
        apiClient.getWeaviateWorkspaces()
      ]);
      
      console.log('[ConfigProvider] Loaded service configurations:', {
        vectorConfig: vectorConfig.status,
        workspaces: workspaces.status
      });
      
      // Check if all data is loaded
      const allLoaded = 
        vectorConfig.status === 'fulfilled' && 
        workspaces.status === 'fulfilled' &&
        availableProviders.length > 0;
      
      setState({
        // From providers/models
        availableProviders,
        availableModels,
        
        // From central config
        embeddingConfig: configs.embeddingConfig || null,
        modelParameters: configs.modelParameters || {},
        ingestionSettings: configs.ingestionSettings,
        systemSettings: configs.systemSettings || {},
        dashboardUrls: configs.dashboardUrls,
        
        // From service endpoints
        vectorConfig: vectorConfig.status === 'fulfilled' ? vectorConfig.value : null,
        workspaces: workspaces.status === 'fulfilled' ? workspaces.value : [],
        
        // Not yet implemented
        ingestionRules: [],
        alertRules: [],
        
        // Update loading state
        loading: {
          isLoading: false,
          providersLoaded: true,
          configLoaded: true,
          modelsLoaded: true,
          vectorConfigLoaded: vectorConfig.status === 'fulfilled',
          workspacesLoaded: workspaces.status === 'fulfilled',
          loadError: null,
          allDataLoaded: allLoaded
        }
      });
    } catch (error) {
      console.error('[ConfigProvider] Failed to load configurations:', error);
      setState(prev => ({
        ...prev,
        loading: {
          ...prev.loading,
          isLoading: false,
          loadError: 'Failed to load configurations',
          allDataLoaded: false
        }
      }));
      toast({
        title: "Configuration Load Failed",
        description: "Some configurations could not be loaded",
        variant: "destructive"
      });
    }
  };
  
  // Helper function to extract configurations from central config response
  const extractConfigurationsFromCentral = (configResponse: any) => {
    const configs = {
      embeddingConfig: {
        useDefaultEmbedding: true,
        provider: '',
        model: '',
        dimensions: 768,
        chunkSize: 1000,
        chunkOverlap: 200
      },
      modelParameters: {} as Record<string, Record<string, ModelParameters>>,
      ingestionSettings: null,
      systemSettings: {} as Record<string, any>,
      dashboardUrls: null,
      modelSelections: {
        textGeneration: { provider: '', model: '' },
        embeddings: { provider: '', model: '' },
        sharedProvider: false
      }
    };
    
    // Process config items
    if (configResponse?.items) {
      configResponse.items.forEach((item: any) => {
        // Extract model selection for embedding config and model selections
        if (item.key === 'ai.model_selection' && item.value) {
          const selection = item.value;
          
          // Extract embedding configuration
          if (selection.embeddings) {
            configs.embeddingConfig = {
              useDefaultEmbedding: false,
              provider: selection.embeddings.provider || '',
              model: selection.embeddings.model || '',
              dimensions: 768,
              chunkSize: 1000,
              chunkOverlap: 200
            };
          }
          
          // Extract model selections for synchronization
          if (selection.textGeneration) {
            configs.modelSelections.textGeneration = {
              provider: selection.textGeneration.provider || '',
              model: selection.textGeneration.model || ''
            };
          }
          
          if (selection.embeddings) {
            configs.modelSelections.embeddings = {
              provider: selection.embeddings.provider || '',
              model: selection.embeddings.model || ''
            };
          }
          
          if (typeof selection.sharedProvider === 'boolean') {
            configs.modelSelections.sharedProvider = selection.sharedProvider;
          }
        }
        
        // Extract model parameters
        const modelParamMatch = item.key.match(/^ai\.models\.([^.]+)\.([^.]+)\.parameters$/);
        if (modelParamMatch) {
          const [, provider, model] = modelParamMatch;
          if (!configs.modelParameters[provider]) {
            configs.modelParameters[provider] = {};
          }
          configs.modelParameters[provider][model] = item.value;
        }
        
        // Extract ingestion settings
        if (item.key === 'ingestion.settings' && item.value) {
          configs.ingestionSettings = item.value;
        }
        
        // Extract system settings
        if (item.key.startsWith('system.') && item.value) {
          const settingKey = item.key.replace('system.', '');
          configs.systemSettings[settingKey] = item.value;
        }
        
        // Extract dashboard URLs
        if (item.key === 'monitoring.dashboard_urls' && item.value) {
          configs.dashboardUrls = item.value;
        }
      });
    }
    
    return configs;
  };
  
  // Update methods
  const updateVectorConfig = (config: VectorConfig) => {
    setState(prev => ({ ...prev, vectorConfig: config }));
  };
  
  const updateEmbeddingConfig = async (config: EmbeddingConfig) => {
    setState(prev => ({ ...prev, embeddingConfig: config }));
    
    // Save to central config if not using default embedding
    if (!config.useDefaultEmbedding && config.provider && config.model) {
      try {
        const currentConfig = await apiClient.getConfiguration();
        const modelSelectionItem = currentConfig.items.find(i => i.key === 'ai.model_selection');
        const currentModelSelection = modelSelectionItem?.value || {};
        
        await apiClient.updateConfiguration({
          key: 'ai.model_selection',
          value: {
            ...(typeof currentModelSelection === 'object' ? currentModelSelection : {}),
            embeddings: {
              provider: config.provider,
              model: config.model
            }
          }
        });
      } catch (error) {
        console.error('[ConfigProvider] Failed to save embedding config:', error);
      }
    }
  };
  
  const updateModelParameters = async (provider: string, model: string, params: ModelParameters) => {
    setState(prev => ({
      ...prev,
      modelParameters: {
        ...prev.modelParameters,
        [provider]: {
          ...(prev.modelParameters[provider] || {}),
          [model]: params
        }
      }
    }));
    
    // Save to central config
    try {
      await apiClient.updateConfiguration({
        key: `ai.models.${provider}.${model}.parameters`,
        value: params as unknown as Record<string, unknown>
      });
    } catch (error) {
      console.error('[ConfigProvider] Failed to save model parameters:', error);
    }
  };
  
  const updateIngestionRules = (rules: any[]) => {
    setState(prev => ({ ...prev, ingestionRules: rules }));
  };
  
  const updateIngestionSettings = (settings: any) => {
    setState(prev => ({ ...prev, ingestionSettings: settings }));
  };
  
  const updateAlertRules = (rules: any[]) => {
    setState(prev => ({ ...prev, alertRules: rules }));
  };
  
  const updateSystemSettings = (settings: any) => {
    setState(prev => ({ ...prev, systemSettings: settings }));
  };
  
  const value: ConfigContextValue = {
    ...state,
    updateVectorConfig,
    updateEmbeddingConfig,
    updateModelParameters,
    updateIngestionRules,
    updateIngestionSettings,
    updateAlertRules,
    updateSystemSettings,
    reloadConfigurations: loadAllConfigurations,
    // Loading state helpers for easier access
    isLoading: state.loading.isLoading,
    allDataLoaded: state.loading.allDataLoaded,
    loadError: state.loading.loadError
  };
  
  return (
    <ConfigContext.Provider value={value}>
      {children}
    </ConfigContext.Provider>
  );
}