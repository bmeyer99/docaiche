'use client';

/**
 * Vector Search configuration tab
 */

import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
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

  const { register: registerVector, handleSubmit: handleSubmitVector, watch: watchVector, reset, setValue: setVectorValue } = useForm<VectorConfig>({
    defaultValues: loadedVectorConfig || {
      enabled: true,
      base_url: 'http://weaviate:8080',
      api_key: '',
      timeout_seconds: 30,
      max_retries: 3,
      verify_ssl: false
    }
  });

  const vectorConfig = watchVector();

  const { register: registerEmbedding, handleSubmit: handleSubmitEmbedding, watch: watchEmbedding, setValue: setEmbeddingValue } = useForm<EmbeddingConfig>({
    defaultValues: loadedEmbeddingConfig || {
      useDefaultEmbedding: true,
      provider: '',
      model: '',
      dimensions: 768,
      chunkSize: 1000,
      chunkOverlap: 200
    }
  });

  const embeddingConfig = watchEmbedding();
  const selectedProvider = embeddingConfig.provider;

  // Set connection status from loaded config
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

  // Track changes to embedding config
  useEffect(() => {
    // Skip on initial load
    if (embeddingConfig.provider || embeddingConfig.model) {
      onChangeDetected?.();
    }
  }, [embeddingConfig.provider, embeddingConfig.model, embeddingConfig.useDefaultEmbedding]);


  const handleConnectionTest = async () => {
    setIsTestingConnection(true);
    try {
      const formData = watchVector();
      const result = await apiClient.testWeaviateConnection({
        base_url: formData.base_url,
        api_key: formData.api_key,
        timeout_seconds: formData.timeout_seconds,
        verify_ssl: formData.verify_ssl
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

  const handleSaveVectorConfig = async (data: VectorConfig) => {
    try {
      const updated = await apiClient.updateWeaviateConfig(data);
      updateVectorConfig(updated);
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

  const handleSaveEmbeddingConfig = async (data: EmbeddingConfig) => {
    try {
      const updated = await apiClient.updateEmbeddingConfig(data);
      updateEmbeddingConfig(updated);
      // Clear unsaved changes after successful save
      onSaveSuccess?.();
      toast({
        title: "Configuration Saved",
        description: "Embedding configuration updated successfully"
      });
    } catch (error: any) {
      toast({
        title: "Save Failed",
        description: error.message || "Failed to save configuration",
        variant: "destructive"
      });
    }
  };

  // Get tested providers that support embeddings
  const getEmbeddingProviders = () => {
    // Guard against missing or invalid providers data
    if (!providers || typeof providers !== 'object') {
      console.warn('[VectorSearch] Providers data is invalid:', providers);
      return [];
    }
    
    return Object.entries(providers)
      .filter(([id, config]) => {
        // Guard against missing config or provider definition
        if (!config || !id) return false;
        
        const provider = AI_PROVIDERS[id];
        if (!provider) {
          console.warn(`[VectorSearch] Provider definition not found for: ${id}`);
          return false;
        }
        
        return (
          provider?.supportsEmbedding &&
          (config.status === 'tested' || config.status === 'connected')
        );
      })
      .map(([id, config]) => ({
        id,
        name: AI_PROVIDERS[id]?.displayName || id,
        models: Array.isArray(config.models) ? config.models : []
      }));
  };

  // Get embedding models for selected provider
  const getEmbeddingModels = () => {
    // Guard against missing or invalid data
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
    // Filter for embedding models
    return models.filter((model: string) => {
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
              <form onSubmit={handleSubmitVector(handleSaveVectorConfig)} className="space-y-4">
                <div className="flex items-start gap-4">
                  <div className="flex-1 space-y-4">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="enabled"
                        checked={vectorConfig.enabled}
                        onCheckedChange={(checked) => {
                          setVectorValue('enabled', checked);
                          onChangeDetected?.();
                        }}
                      />
                      <Label htmlFor="enabled">Enable Vector Search</Label>
                    </div>

                    <div>
                      <Label htmlFor="base_url">Base URL</Label>
                      <Input
                        id="base_url"
                        {...registerVector('base_url')}
                        placeholder="http://weaviate:8080"
                      />
                    </div>
                    
                    <div>
                      <Label htmlFor="api_key">API Key (Optional)</Label>
                      <Input
                        id="api_key"
                        type="password"
                        {...registerVector('api_key')}
                        placeholder="Enter API key if required"
                      />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <Label htmlFor="timeout_seconds">Timeout (seconds)</Label>
                        <Input
                          id="timeout_seconds"
                          type="number"
                          {...registerVector('timeout_seconds', { valueAsNumber: true })}
                        />
                      </div>
                      
                      <div>
                        <Label htmlFor="max_retries">Max Retries</Label>
                        <Input
                          id="max_retries"
                          type="number"
                          {...registerVector('max_retries', { valueAsNumber: true })}
                        />
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="verify_ssl"
                        checked={vectorConfig.verify_ssl}
                        onCheckedChange={(checked) => {
                          setVectorValue('verify_ssl', checked);
                          onChangeDetected?.();
                        }}
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

                <div className="flex justify-end">
                  <Button type="submit">Save Connection Settings</Button>
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
              <form onSubmit={handleSubmitEmbedding(handleSaveEmbeddingConfig)} className="space-y-6">
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
                    onCheckedChange={(checked) => {
                      setEmbeddingValue('useDefaultEmbedding', checked);
                      onChangeDetected?.();
                    }}
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
                          value={embeddingConfig.provider}
                          onValueChange={(value) => {
                            setEmbeddingValue('provider', value);
                            setEmbeddingValue('model', ''); // Reset model
                            onChangeDetected?.();
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
                          value={embeddingConfig.model}
                          onValueChange={(value) => {
                            setEmbeddingValue('model', value);
                            onChangeDetected?.();
                          }}
                          disabled={!embeddingConfig.provider}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select model" />
                          </SelectTrigger>
                          <SelectContent>
                            {getEmbeddingModels().map((model: string) => (
                              <SelectItem key={model} value={model}>
                                {model}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    </div>

                    {/* Model Configuration */}
                    {embeddingConfig.model && (
                      <div className="space-y-4 p-4 border rounded-lg">
                        <h4 className="font-medium">Model Configuration</h4>
                        
                        <div>
                          <Label htmlFor="dimensions">Embedding Dimensions</Label>
                          <Input
                            id="dimensions"
                            type="number"
                            {...registerEmbedding('dimensions', { valueAsNumber: true })}
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
                              onValueChange={(value) => {
                                setEmbeddingValue('chunkSize', value[0]);
                                onChangeDetected?.();
                              }}
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
                              onValueChange={(value) => {
                                setEmbeddingValue('chunkOverlap', value[0]);
                                onChangeDetected?.();
                              }}
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

                <div className="flex justify-end">
                  <Button type="submit">Save Model Configuration</Button>
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