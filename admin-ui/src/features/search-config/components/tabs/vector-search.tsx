'use client';

/**
 * Vector Search configuration tab
 * Refactored to use centralized state management with proper change detection
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Slider } from '@/components/ui/slider';
import { 
  Database,
  Settings,
  PlayCircle,
  CheckCircle,
  AlertCircle,
  Loader2,
  Info
} from 'lucide-react';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';
import { useProviderSettings } from '@/lib/hooks/use-provider-settings';
import { AI_PROVIDERS } from '@/lib/config/providers';
import { useSearchConfig } from '../../contexts/config-context';
import { useSearchConfigSection } from '../../hooks/use-search-config-form';

interface VectorSearchConfigProps {
  onChangeDetected?: () => void;
  onSaveSuccess?: () => void;
}

interface VectorConfig {
  enabled: boolean;
  base_url: string;
  api_key?: string;
  timeout_seconds: number;
  max_retries: number;
  verify_ssl: boolean;
}

interface EmbeddingConfig {
  useDefaultEmbedding: boolean;
  provider?: string;
  model?: string;
  dimensions?: number;
  chunkSize?: number;
  chunkOverlap?: number;
}

export function VectorSearchConfig({ onChangeDetected, onSaveSuccess }: VectorSearchConfigProps) {
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<any>(null);
  const { providers } = useProviderSettings();
  const apiClient = useApiClient();
  const { toast } = useToast();
  const { 
    vectorConfig: loadedVectorConfig, 
    workspaces,
    embeddingConfig: loadedEmbeddingConfig,
    updateVectorConfig,
    updateEmbeddingConfig 
  } = useSearchConfig();

  // Use centralized form state management for vector config
  const {
    value: vectorConfig,
    setValue: setVectorConfig,
    isDirty: isVectorConfigDirty
  } = useSearchConfigSection<VectorConfig>('vectorConfig', {
    enabled: true,
    base_url: 'http://weaviate:8080',
    api_key: '',
    timeout_seconds: 30,
    max_retries: 3,
    verify_ssl: false
  });

  // Use centralized form state management for embedding config
  const {
    value: embeddingConfig,
    setValue: setEmbeddingConfig,
    isDirty: isEmbeddingConfigDirty
  } = useSearchConfigSection<EmbeddingConfig>('embeddingConfig', {
    useDefaultEmbedding: true,
    provider: '',
    model: '',
    dimensions: 768,
    chunkSize: 1000,
    chunkOverlap: 200
  });

  // Helper functions to update individual fields
  const updateVectorField = useCallback((field: keyof VectorConfig, value: any) => {
    setVectorConfig({ ...vectorConfig, [field]: value }, 'user');
  }, [vectorConfig, setVectorConfig]);

  const updateEmbeddingField = useCallback((field: keyof EmbeddingConfig, value: any) => {
    setEmbeddingConfig({ ...embeddingConfig, [field]: value }, 'user');
  }, [embeddingConfig, setEmbeddingConfig]);

  // Initialize connection status from loaded config
  useEffect(() => {
    if (loadedVectorConfig) {
      setConnectionStatus({
        connected: loadedVectorConfig.connected || false,
        version: loadedVectorConfig.version,
        workspaces_count: loadedVectorConfig.workspaces_count || 0,
        message: loadedVectorConfig.message
      });
    }
  }, [loadedVectorConfig]);

  // Load saved configs using system updates (doesn't trigger dirty state)
  useEffect(() => {
    if (loadedVectorConfig) {
      setVectorConfig(loadedVectorConfig, 'system');
    }
  }, [loadedVectorConfig, setVectorConfig]);

  useEffect(() => {
    if (loadedEmbeddingConfig) {
      setEmbeddingConfig(loadedEmbeddingConfig, 'system');
    }
  }, [loadedEmbeddingConfig, setEmbeddingConfig]);

  // Notify parent when there are user changes
  useEffect(() => {
    if (isVectorConfigDirty || isEmbeddingConfigDirty) {
      onChangeDetected?.();
    }
  }, [isVectorConfigDirty, isEmbeddingConfigDirty, onChangeDetected]);

  const handleConnectionTest = async () => {
    setIsTestingConnection(true);
    try {
      const result = await apiClient.testWeaviateConnection({
        base_url: vectorConfig.base_url,
        api_key: vectorConfig.api_key,
        timeout_seconds: vectorConfig.timeout_seconds,
        verify_ssl: vectorConfig.verify_ssl
      });
      
      setConnectionStatus({
        connected: result.success,
        version: result.version,
        workspaces_count: result.workspaces_count || 0,
        message: result.message
      });
      
      toast({
        title: result.success ? "Connection Successful" : "Connection Failed",
        description: result.message,
        variant: result.success ? "default" : "destructive"
      });
    } catch (error: any) {
      setConnectionStatus({
        connected: false,
        message: error.message || 'Failed to connect'
      });
      toast({
        title: "Connection Failed",
        description: error.message || "Unable to connect to Weaviate",
        variant: "destructive"
      });
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleSaveVectorConfig = async () => {
    try {
      const updated = await apiClient.updateWeaviateConfig(vectorConfig);
      updateVectorConfig(updated);
      // Update the form state with system source to clear dirty flag
      setVectorConfig(updated, 'system');
      toast({
        title: "Configuration Saved",
        description: "Weaviate configuration updated successfully"
      });
    } catch (error: any) {
      toast({
        title: "Save Failed",
        description: error.message || "Failed to save configuration",
        variant: "destructive"
      });
    }
  };

  const handleSaveEmbeddingConfig = async () => {
    try {
      // Include all embedding config fields
      const configToSave = {
        useDefaultEmbedding: embeddingConfig.useDefaultEmbedding,
        provider: embeddingConfig.provider || '',
        model: embeddingConfig.model || '',
        dimensions: embeddingConfig.dimensions || 768,
        chunkSize: embeddingConfig.chunkSize || 1000,
        chunkOverlap: embeddingConfig.chunkOverlap || 200
      };
      
      const updated = await apiClient.updateEmbeddingConfig(configToSave);
      updateEmbeddingConfig(updated);
      // Update the form state with system source to clear dirty flag
      setEmbeddingConfig(updated, 'system');
      // Clear unsaved changes after successful save
      onSaveSuccess?.();
      toast({
        title: "Configuration Saved",
        description: "Embedding configuration updated successfully"
      });
    } catch (error: any) {
      console.error('[VectorSearch] Save error:', error);
      toast({
        title: "Save Failed",
        description: error.message || "Failed to save configuration",
        variant: "destructive"
      });
    }
  };

  // Get configured providers that support embeddings
  const getEmbeddingProviders = () => {
    // Guard against missing or invalid providers data
    if (!providers || typeof providers !== 'object') {
      console.warn('[VectorSearch] Providers data is invalid:', providers);
      return [];
    }
    
    const embeddingProviders = Object.entries(providers)
      .filter(([id, config]) => {
        // Guard against missing config or provider definition
        if (!config || !id) return false;
        
        const provider = AI_PROVIDERS[id];
        if (!provider) {
          console.warn(`[VectorSearch] Provider definition not found for: ${id}`);
          return false;
        }
        
        // Only show providers that are marked as configured (tested/connected)
        // Check multiple status indicators for robustness
        const isConfigured = 
          config.status === 'tested' || 
          config.status === 'connected' || 
          config.configured === true ||
          (config.models && Array.isArray(config.models) && config.models.length > 0);
        
        const supportsEmbedding = provider?.supportsEmbedding || false;
        
        console.log(`[VectorSearch] Provider ${id}:`, {
          status: config.status,
          configured: config.configured,
          hasModels: config.models?.length > 0,
          supportsEmbedding,
          isConfigured
        });
        
        return supportsEmbedding && isConfigured;
      })
      .map(([id, config]) => ({
        id,
        name: AI_PROVIDERS[id]?.displayName || id,
        models: Array.isArray(config.models) ? config.models : []
      }));
      
    console.log('[VectorSearch] Configured embedding providers:', embeddingProviders);
    return embeddingProviders;
  };

  // Get embedding models for selected provider
  const getEmbeddingModels = () => {
    // Guard against missing or invalid data
    const selectedProvider = embeddingConfig.provider;
    if (!selectedProvider || !providers || !providers[selectedProvider]) {
      console.warn('[VectorSearch] Cannot get models - invalid provider data:', { selectedProvider, providers });
      return [];
    }
    
    const providerData = providers[selectedProvider];
    if (!providerData || !Array.isArray(providerData.models)) {
      console.warn('[VectorSearch] Provider models data is invalid:', providerData);
      return [];
    }
    
    const models = providerData.models;
    
    // For Ollama, show models that have embedding capabilities
    if (selectedProvider === 'ollama') {
      const ollamaEmbedModels = models.filter((model: string) => {
        if (typeof model !== 'string') return false;
        const modelName = model.toLowerCase();
        return (
          modelName.includes('embed') ||
          modelName.includes('e5') ||
          modelName.includes('bge') ||
          modelName.includes('nomic') ||
          modelName.includes('mxbai')
        );
      });
      console.log('[VectorSearch] Ollama embedding models:', ollamaEmbedModels);
      return ollamaEmbedModels;
    }
    
    // For other providers, filter for embedding models
    const filteredModels = models.filter((model: string) => {
      if (typeof model !== 'string') return false;
      const lowerModel = model.toLowerCase();
      return (
        lowerModel.includes('embed') ||
        lowerModel.includes('e5') ||
        lowerModel.includes('bge') ||
        lowerModel.includes('sentence') ||
        lowerModel.includes('all-minilm')
      );
    });
    
    console.log('[VectorSearch] Filtered embedding models for', selectedProvider, ':', filteredModels);
    return filteredModels;
  };

  return (
    <div className="p-6 space-y-6">
      <Tabs defaultValue="connection" className="space-y-4">
        <TabsList>
          <TabsTrigger value="connection">Connection</TabsTrigger>
          <TabsTrigger value="models">Models</TabsTrigger>
          <TabsTrigger value="workspaces">Workspaces</TabsTrigger>
        </TabsList>

        {/* Connection Tab */}
        <TabsContent value="connection" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Weaviate Connection</CardTitle>
              <CardDescription>
                Configure the connection to your Weaviate vector database
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={(e) => { e.preventDefault(); handleSaveVectorConfig(); }} className="space-y-4">
                <div className="flex items-start gap-4">
                  <div className="flex-1 space-y-4">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="enabled"
                        checked={vectorConfig.enabled}
                        onCheckedChange={(checked) => updateVectorField('enabled', checked)}
                      />
                      <Label htmlFor="enabled">Enable Vector Search</Label>
                    </div>

                    <div>
                      <Label htmlFor="base_url">Base URL</Label>
                      <Input
                        id="base_url"
                        value={vectorConfig.base_url}
                        onChange={(e) => updateVectorField('base_url', e.target.value)}
                        placeholder="http://weaviate:8080"
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="api_key">API Key (Optional)</Label>
                      <Input
                        id="api_key"
                        type="password"
                        value={vectorConfig.api_key || ''}
                        onChange={(e) => updateVectorField('api_key', e.target.value)}
                        placeholder="Enter API key if required"
                      />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="timeout_seconds">Timeout (seconds)</Label>
                        <Input
                          id="timeout_seconds"
                          type="number"
                          value={vectorConfig.timeout_seconds}
                          onChange={(e) => updateVectorField('timeout_seconds', parseInt(e.target.value) || 30)}
                        />
                      </div>
                      
                      <div>
                        <Label htmlFor="max_retries">Max Retries</Label>
                        <Input
                          id="max_retries"
                          type="number"
                          value={vectorConfig.max_retries}
                          onChange={(e) => updateVectorField('max_retries', parseInt(e.target.value) || 3)}
                        />
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="verify_ssl"
                        checked={vectorConfig.verify_ssl}
                        onCheckedChange={(checked) => updateVectorField('verify_ssl', checked)}
                      />
                      <Label htmlFor="verify_ssl">Verify SSL Certificate</Label>
                    </div>
                  </div>

                  <div className="w-64 space-y-4">
                    <Card>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-base">Connection Status</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {connectionStatus ? (
                          <>
                            <div className="flex items-center gap-2">
                              {connectionStatus.connected ? (
                                <CheckCircle className="h-4 w-4 text-green-500" />
                              ) : (
                                <AlertCircle className="h-4 w-4 text-red-500" />
                              )}
                              <span className="text-sm font-medium">
                                {connectionStatus.connected ? 'Connected' : 'Disconnected'}
                              </span>
                            </div>
                            
                            {connectionStatus.version && (
                              <div className="space-y-1 text-sm">
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Version:</span>
                                  <span>{connectionStatus.version}</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-muted-foreground">Workspaces:</span>
                                  <span>{connectionStatus.workspaces_count}</span>
                                </div>
                              </div>
                            )}
                          </>
                        ) : (
                          <p className="text-sm text-muted-foreground">Not tested</p>
                        )}
                        
                        <Button 
                          type="button"
                          size="sm" 
                          className="w-full"
                          onClick={handleConnectionTest}
                          disabled={isTestingConnection}
                        >
                          {isTestingConnection ? (
                            <>
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                              Testing...
                            </>
                          ) : (
                            <>
                              <PlayCircle className="h-4 w-4 mr-2" />
                              Test Connection
                            </>
                          )}
                        </Button>
                      </CardContent>
                    </Card>
                  </div>
                </div>

                <div className="flex justify-end items-center gap-4">
                  {isVectorConfigDirty && (
                    <span className="text-sm text-muted-foreground">You have unsaved changes</span>
                  )}
                  <Button type="submit" disabled={!isVectorConfigDirty}>
                    Save Connection Settings
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Models Tab */}
        <TabsContent value="models" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Embedding Model Configuration</CardTitle>
              <CardDescription>
                Configure the embedding model for vector search
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={(e) => { e.preventDefault(); handleSaveEmbeddingConfig(); }} className="space-y-6">
                {/* Default Embedding Toggle */}
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div className="space-y-1">
                    <Label htmlFor="useDefaultEmbedding">Use Weaviate Default Embedding</Label>
                    <p className="text-sm text-muted-foreground">
                      Weaviate's built-in text2vec-transformers module (enabled by default)
                    </p>
                  </div>
                  <Switch
                    id="useDefaultEmbedding"
                    checked={embeddingConfig.useDefaultEmbedding}
                    onCheckedChange={(checked) => updateEmbeddingField('useDefaultEmbedding', checked)}
                  />
                </div>

                {/* Custom Embedding Configuration */}
                {!embeddingConfig.useDefaultEmbedding && (
                  <div className="space-y-4">
                    <Alert>
                      <Info className="h-4 w-4" />
                      <AlertDescription>
                        Only providers that have been tested and support embeddings are shown below.
                        Test providers in the Providers tab first.
                      </AlertDescription>
                    </Alert>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="provider">Embedding Provider</Label>
                        <Select
                          value={embeddingConfig.provider || ''}
                          onValueChange={(value) => {
                            updateEmbeddingField('provider', value);
                            updateEmbeddingField('model', ''); // Reset model
                          }}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select provider" />
                          </SelectTrigger>
                          <SelectContent>
                            {getEmbeddingProviders().map((provider) => (
                              <SelectItem key={provider.id} value={provider.id}>
                                {provider.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      <div>
                        <Label htmlFor="model">Embedding Model</Label>
                        <Select
                          value={embeddingConfig.model || ''}
                          onValueChange={(value) => updateEmbeddingField('model', value)}
                          disabled={!embeddingConfig.provider}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select model" />
                          </SelectTrigger>
                          <SelectContent>
                            {getEmbeddingModels().length === 0 ? (
                              <div className="py-2 px-3 text-sm text-muted-foreground">
                                No embedding models available
                              </div>
                            ) : (
                              getEmbeddingModels().map((model: string) => (
                                <SelectItem key={model} value={model}>
                                  {model}
                                </SelectItem>
                              ))
                            )}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* Display Current Saved Configuration */}
                    {(embeddingConfig.provider && embeddingConfig.model) && (
                      <div className="p-4 border rounded-lg bg-muted/30">
                        <h4 className="font-medium mb-2">Current Saved Configuration</h4>
                        <div className="space-y-1 text-sm">
                          <div className="flex items-center gap-2">
                            <span className="text-muted-foreground">Provider:</span>
                            <Badge variant="secondary">
                              {AI_PROVIDERS[embeddingConfig.provider]?.displayName || embeddingConfig.provider}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-muted-foreground">Model:</span>
                            <Badge variant="secondary">{embeddingConfig.model}</Badge>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-muted-foreground">Status:</span>
                            <Badge variant="outline">Saved</Badge>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Model Configuration */}
                    {embeddingConfig.model && (
                      <div className="space-y-4 p-4 border rounded-lg">
                        <h4 className="font-medium">Model Configuration</h4>
                        
                        <div>
                          <Label htmlFor="dimensions">Embedding Dimensions</Label>
                          <Input
                            id="dimensions"
                            type="number"
                            value={embeddingConfig.dimensions || 768}
                            onChange={(e) => updateEmbeddingField('dimensions', parseInt(e.target.value) || 768)}
                            placeholder="768"
                          />
                          <p className="text-xs text-muted-foreground mt-1">
                            Vector dimensions (typically 384, 768, or 1536)
                          </p>
                        </div>

                        <div>
                          <Label htmlFor="chunkSize">Chunk Size</Label>
                          <div className="flex items-center gap-4">
                            <Slider
                              id="chunkSize"
                              min={100}
                              max={4000}
                              step={100}
                              value={[embeddingConfig.chunkSize || 1000]}
                              onValueChange={(value) => updateEmbeddingField('chunkSize', value[0])}
                              className="flex-1"
                            />
                            <span className="w-16 text-sm">{embeddingConfig.chunkSize}</span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            Maximum number of tokens per chunk
                          </p>
                        </div>

                        <div>
                          <Label htmlFor="chunkOverlap">Chunk Overlap</Label>
                          <div className="flex items-center gap-4">
                            <Slider
                              id="chunkOverlap"
                              min={0}
                              max={500}
                              step={50}
                              value={[embeddingConfig.chunkOverlap || 200]}
                              onValueChange={(value) => updateEmbeddingField('chunkOverlap', value[0])}
                              className="flex-1"
                            />
                            <span className="w-16 text-sm">{embeddingConfig.chunkOverlap}</span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            Number of overlapping tokens between chunks
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <div className="flex justify-end items-center gap-4">
                  {isEmbeddingConfigDirty && (
                    <span className="text-sm text-muted-foreground">You have unsaved changes</span>
                  )}
                  <Button type="submit" disabled={!isEmbeddingConfigDirty}>
                    Save Model Configuration
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Workspaces Tab */}
        <TabsContent value="workspaces" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Workspace Management</CardTitle>
              <CardDescription>
                View and manage Weaviate workspaces (tenants)
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {workspaces.length > 0 ? (
                  <div className="space-y-2">
                    {workspaces.map((workspace) => (
                      <div key={workspace.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div>
                          <p className="font-medium">{workspace.name || workspace.class_name}</p>
                          <p className="text-sm text-muted-foreground">
                            Class: {workspace.class_name} • Objects: {workspace.object_count || 0}
                          </p>
                          {workspace.description && (
                            <p className="text-xs text-muted-foreground mt-1">
                              {workspace.description}
                            </p>
                          )}
                        </div>
                        <Badge variant={workspace.status === 'READY' ? "default" : "secondary"}>
                          {workspace.status || "Unknown"}
                        </Badge>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <Database className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>No workspaces found</p>
                    <p className="text-sm">Workspaces will be created automatically when documents are ingested</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}