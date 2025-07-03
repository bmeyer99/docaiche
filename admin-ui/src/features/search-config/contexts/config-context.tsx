'use client';

/**
 * Context for centralized configuration management
 * Loads all configurations at page load and provides them to tabs
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';

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

interface ConfigState {
  // Vector Search
  vectorConfig: VectorConfig | null;
  workspaces: any[];
  embeddingConfig: EmbeddingConfig | null;
  
  // Text AI
  modelParameters: Record<string, Record<string, ModelParameters>>;
  
  // Ingestion
  ingestionRules: any[];
  ingestionSettings: any;
  
  // Monitoring
  alertRules: any[];
  dashboardUrls: any;
  
  // System Settings
  systemSettings: any;
  
  // Loading state
  isLoading: boolean;
  loadError: string | null;
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
  
  const [state, setState] = useState<ConfigState>({
    vectorConfig: null,
    workspaces: [],
    embeddingConfig: null,
    modelParameters: {},
    ingestionRules: [],
    ingestionSettings: null,
    alertRules: [],
    dashboardUrls: null,
    systemSettings: null,
    isLoading: true,
    loadError: null
  });
  
  // Load all configurations on mount
  useEffect(() => {
    loadAllConfigurations();
  }, []);
  
  const loadAllConfigurations = async () => {
    setState(prev => ({ ...prev, isLoading: true, loadError: null }));
    
    try {
      // Load central configuration first
      const centralConfig = await apiClient.getConfiguration();
      console.log('[ConfigProvider] Loaded central configuration');
      
      // Extract configurations from central store
      const configs = extractConfigurationsFromCentral(centralConfig);
      
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
      
      setState({
        // From central config
        embeddingConfig: configs.embeddingConfig,
        modelParameters: configs.modelParameters,
        ingestionSettings: configs.ingestionSettings,
        systemSettings: configs.systemSettings,
        dashboardUrls: configs.dashboardUrls,
        
        // From service endpoints
        vectorConfig: vectorConfig.status === 'fulfilled' ? vectorConfig.value : null,
        workspaces: workspaces.status === 'fulfilled' ? workspaces.value : [],
        
        // Not yet implemented
        ingestionRules: [],
        alertRules: [],
        
        isLoading: false,
        loadError: null
      });
    } catch (error) {
      console.error('[ConfigProvider] Failed to load configurations:', error);
      setState(prev => ({
        ...prev,
        isLoading: false,
        loadError: 'Failed to load configurations'
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
      dashboardUrls: null
    };
    
    // Process config items
    if (configResponse?.items) {
      configResponse.items.forEach((item: any) => {
        // Extract model selection for embedding config
        if (item.key === 'ai.model_selection' && item.value) {
          const selection = item.value;
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
    reloadConfigurations: loadAllConfigurations
  };
  
  return (
    <ConfigContext.Provider value={value}>
      {children}
    </ConfigContext.Provider>
  );
}