'use client';

/**
 * Embedding AI configuration tab
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Slider } from '@/components/ui/slider';
import { 
  Bot,
  Settings,
  Info,
  Save,
  Loader2
} from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import { useProviderSettings } from '@/lib/hooks/use-provider-settings';
import { AI_PROVIDERS } from '@/lib/config/providers';
import { useSearchConfigSection } from '../../hooks/use-search-config-form';

interface EmbeddingAIConfigProps {
  onChangeDetected?: () => void;
  onSaveSuccess?: () => void;
}

interface EmbeddingConfig {
  useDefaultEmbedding: boolean;
  provider?: string;
  model?: string;
  dimensions?: number;
  chunkSize?: number;
  chunkOverlap?: number;
}

export function EmbeddingAIConfig({ onChangeDetected, onSaveSuccess }: EmbeddingAIConfigProps) {
  const [isSaving, setIsSaving] = useState(false);
  const { providers } = useProviderSettings();
  const { toast } = useToast();
  
  // Use the centralized form hook for embedding config
  const {
    value: embeddingConfig,
    setValue: setEmbeddingConfig,
    isDirty
  } = useSearchConfigSection<EmbeddingConfig>('embeddingConfig', {
    useDefaultEmbedding: true,
    provider: '',
    model: '',
    dimensions: 768,
    chunkSize: 1000,
    chunkOverlap: 200
  });

  // Track initialization to prevent false change detection
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize once when component mounts
  useEffect(() => {
    setIsInitialized(true);
  }, []);

  // Only trigger change detection for actual user changes
  useEffect(() => {
    if (isInitialized && isDirty) {
      onChangeDetected?.();
    }
  }, [isDirty, isInitialized, onChangeDetected]);

  // Debug logging
  useEffect(() => {
    console.log('[EmbeddingAI] Current config:', embeddingConfig);
    console.log('[EmbeddingAI] Available providers:', providers);
    console.log('[EmbeddingAI] Is dirty:', isDirty);
  }, [embeddingConfig, providers, isDirty]);

  // Update field with proper source tracking
  const updateField = useCallback(<K extends keyof EmbeddingConfig>(
    field: K,
    value: EmbeddingConfig[K]
  ) => {
    setEmbeddingConfig({
      ...embeddingConfig,
      [field]: value
    }, 'user'); // Mark as user change
  }, [embeddingConfig, setEmbeddingConfig]);

  // Handle save
  const handleSave = async () => {
    setIsSaving(true);
    try {
      // In the new architecture, saving is handled by the centralized form
      // This component just manages the local state and change detection
      // The actual save will be triggered by the parent layout component
      
      // For now, we'll just show a message that changes need to be saved
      toast({
        title: "Save Required",
        description: "Please use the global save button to save all changes",
        variant: "default"
      });
    } catch (error: any) {
      console.error('[EmbeddingAI] Save error:', error);
      toast({
        title: "Error",
        description: error.message || "An error occurred",
        variant: "destructive"
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Get configured providers that support embeddings
  const getEmbeddingProviders = () => {
    if (!providers || typeof providers !== 'object') {
      console.warn('[EmbeddingAI] Providers data is invalid:', providers);
      return [];
    }
    
    const embeddingProviders = Object.entries(providers)
      .filter(([id, config]) => {
        if (!config || !id) return false;
        
        const provider = AI_PROVIDERS[id];
        if (!provider) {
          console.warn(`[EmbeddingAI] Provider definition not found for: ${id}`);
          return false;
        }
        
        // Only show providers that are configured and support embeddings
        const isConfigured = config.status === 'tested' || config.status === 'connected' || config.configured === true;
        
        return provider?.supportsEmbedding && isConfigured;
      })
      .map(([id, config]) => ({
        id,
        name: AI_PROVIDERS[id]?.displayName || id,
        models: Array.isArray(config.models) ? config.models : []
      }));
      
    console.log('[EmbeddingAI] Configured embedding providers:', embeddingProviders);
    return embeddingProviders;
  };

  // Get embedding models for selected provider
  const getEmbeddingModels = () => {
    if (!embeddingConfig.provider || !providers || !providers[embeddingConfig.provider]) {
      console.warn('[EmbeddingAI] Cannot get models - invalid provider data');
      return [];
    }
    
    const providerData = providers[embeddingConfig.provider];
    if (!providerData || !Array.isArray(providerData.models)) {
      console.warn('[EmbeddingAI] Provider models data is invalid:', providerData);
      return [];
    }
    
    const models = providerData.models;
    
    // For Ollama, show models that have embedding capabilities
    if (embeddingConfig.provider === 'ollama') {
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
      console.log('[EmbeddingAI] Ollama embedding models:', ollamaEmbedModels);
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
    
    console.log('[EmbeddingAI] Filtered embedding models for', embeddingConfig.provider, ':', filteredModels);
    return filteredModels;
  };

  return (
    <div className="p-6 space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Embedding Model Configuration</CardTitle>
          <CardDescription>
            Configure the embedding model for vector search
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
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
              onCheckedChange={(checked) => updateField('useDefaultEmbedding', checked)}
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
                      updateField('provider', value);
                      updateField('model', ''); // Reset model when provider changes
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
                    onValueChange={(value) => updateField('model', value)}
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

              {/* Display Current Configuration */}
              {(embeddingConfig.provider && embeddingConfig.model) && (
                <div className="p-4 border rounded-lg bg-muted/30">
                  <h4 className="font-medium mb-2">Current Configuration</h4>
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
                      <Badge variant={isDirty ? "destructive" : "outline"}>
                        {isDirty ? "Unsaved Changes" : "Saved"}
                      </Badge>
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
                      value={embeddingConfig.dimensions}
                      onChange={(e) => updateField('dimensions', parseInt(e.target.value) || 768)}
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
                        onValueChange={(value) => updateField('chunkSize', value[0])}
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
                        onValueChange={(value) => updateField('chunkOverlap', value[0])}
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
            <Button 
              onClick={handleSave} 
              disabled={!isDirty || isSaving}
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save Configuration
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}