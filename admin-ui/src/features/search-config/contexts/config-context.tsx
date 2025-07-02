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
  updateEmbeddingConfig: (config: EmbeddingConfig) => void;
  updateModelParameters: (provider: string, model: string, params: ModelParameters) => void;
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
      // Load all configurations in parallel
      const [
        vectorConfig,
        workspaces,
        embeddingConfig,
        ingestionRules,
        ingestionSettings,
        alertRules,
        dashboardUrls,
        systemSettings
      ] = await Promise.allSettled([
        apiClient.getWeaviateConfig(),
        apiClient.getWeaviateWorkspaces(),
        apiClient.getEmbeddingConfig(),
        apiClient.getIngestionRules(),
        apiClient.getIngestionSettings(),
        apiClient.getAlertRules(),
        apiClient.getDashboardUrls(),
        apiClient.getSystemSettings()
      ]);
      
      setState({
        vectorConfig: vectorConfig.status === 'fulfilled' ? vectorConfig.value : null,
        workspaces: workspaces.status === 'fulfilled' ? workspaces.value : [],
        embeddingConfig: embeddingConfig.status === 'fulfilled' ? embeddingConfig.value : null,
        modelParameters: {}, // Will be loaded on demand per provider/model
        ingestionRules: ingestionRules.status === 'fulfilled' ? ingestionRules.value : [],
        ingestionSettings: ingestionSettings.status === 'fulfilled' ? ingestionSettings.value : null,
        alertRules: alertRules.status === 'fulfilled' ? alertRules.value : [],
        dashboardUrls: dashboardUrls.status === 'fulfilled' ? dashboardUrls.value : null,
        systemSettings: systemSettings.status === 'fulfilled' ? systemSettings.value : null,
        isLoading: false,
        loadError: null
      });
    } catch (error) {
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
  
  // Update methods
  const updateVectorConfig = (config: VectorConfig) => {
    setState(prev => ({ ...prev, vectorConfig: config }));
  };
  
  const updateEmbeddingConfig = (config: EmbeddingConfig) => {
    setState(prev => ({ ...prev, embeddingConfig: config }));
  };
  
  const updateModelParameters = (provider: string, model: string, params: ModelParameters) => {
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