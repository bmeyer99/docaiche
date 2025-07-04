'use client';

/**
 * Text AI configuration tab
 */

import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { 
  Bot, 
  Sparkles, 
  AlertCircle,
  Info,
  Save,
  Loader2
} from 'lucide-react';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';
import { useProviderSettings, useModelSelection } from '@/lib/hooks/use-provider-settings';
import { AI_PROVIDERS } from '@/lib/config/providers';
import { useSearchConfig } from '../../contexts/config-context';
import { SystemPromptsManager } from '../system-prompts-manager';

interface TextAIConfigProps {
  onChangeDetected?: () => void;
  onSaveSuccess?: () => void;
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

export function TextAIConfig({ onChangeDetected, onSaveSuccess }: TextAIConfigProps) {
  const [isSaving, setIsSaving] = useState(false);
  const { providers } = useProviderSettings();
  const { modelSelection, updateModelSelection } = useModelSelection();
  const apiClient = useApiClient();
  const { toast } = useToast();
  const { modelParameters, updateModelParameters } = useSearchConfig();
  
  // Try to get saved configuration from central config first
  const [savedConfig, setSavedConfig] = useState<{provider: string, model: string} | null>(null);
  
  useEffect(() => {
    // Load saved text generation configuration
    const loadSavedConfig = async () => {
      try {
        const centralConfig = await apiClient.getConfiguration();
        const modelSelectionItem = centralConfig.items?.find(i => i.key === 'ai.model_selection');
        if (modelSelectionItem?.value && typeof modelSelectionItem.value === 'object' && 'textGeneration' in modelSelectionItem.value) {
          const textConfig = (modelSelectionItem.value as any).textGeneration;
          setSavedConfig({
            provider: textConfig.provider || '',
            model: textConfig.model || ''
          });
          // Update model selection to show saved config
          if (textConfig.provider && textConfig.model) {
            updateModelSelection({
              ...modelSelection,
              textGeneration: {
                provider: textConfig.provider,
                model: textConfig.model
              }
            });
          }
        }
      } catch (error) {
        console.warn('[TextAI] Failed to load saved configuration:', error);
      }
    };
    loadSavedConfig();
  }, []);

  const selectedProvider = savedConfig?.provider || modelSelection.textGeneration.provider;
  const selectedModel = savedConfig?.model || modelSelection.textGeneration.model;
  
  // Get pre-loaded parameters for selected model
  const loadedParams = modelParameters[selectedProvider]?.[selectedModel];

  const { register, handleSubmit, watch, setValue } = useForm<ModelParameters>({
    defaultValues: loadedParams || {
      temperature: 0.7,
      topP: 0.9,
      topK: 40,
      maxTokens: 2048,
      presencePenalty: 0,
      frequencyPenalty: 0,
      systemPrompt: ''
    }
  });

  useEffect(() => {
    // When model changes, load parameters if not already loaded
    if (selectedProvider && selectedModel && !loadedParams) {
      loadModelParameters();
    } else if (loadedParams) {
      // Use pre-loaded parameters
      setValue('temperature', loadedParams.temperature || 0.7);
      setValue('topP', loadedParams.topP || 0.9);
      setValue('topK', loadedParams.topK || 40);
      setValue('maxTokens', loadedParams.maxTokens || 2048);
      setValue('presencePenalty', loadedParams.presencePenalty || 0);
      setValue('frequencyPenalty', loadedParams.frequencyPenalty || 0);
      setValue('systemPrompt', loadedParams.systemPrompt || '');
    }
  }, [selectedProvider, selectedModel, loadedParams]);

  const loadModelParameters = async () => {
    if (!selectedProvider || !selectedModel) return;
    
    try {
      const params = await apiClient.getModelParameters(selectedProvider, selectedModel);
      if (params) {
        updateModelParameters(selectedProvider, selectedModel, params);
        setValue('temperature', params.temperature || 0.7);
        setValue('topP', params.topP || 0.9);
        setValue('topK', params.topK || 40);
        setValue('maxTokens', params.maxTokens || 2048);
        setValue('presencePenalty', params.presencePenalty || 0);
        setValue('frequencyPenalty', params.frequencyPenalty || 0);
        setValue('systemPrompt', params.systemPrompt || '');
      }
    } catch (error) {
      console.error('Failed to load model parameters:', error);
    }
  };

  const handleSaveConfig = async (data: ModelParameters) => {
    if (!selectedProvider || !selectedModel) {
      toast({
        title: "No Model Selected",
        description: "Please select a provider and model first",
        variant: "destructive"
      });
      return;
    }

    setIsSaving(true);
    try {
      await apiClient.updateModelParameters(selectedProvider, selectedModel, data);
      updateModelParameters(selectedProvider, selectedModel, data);
      // Clear unsaved changes after successful save
      onSaveSuccess?.();
      toast({
        title: "Configuration Saved",
        description: "Text AI model parameters updated successfully"
      });
    } catch (error: any) {
      toast({
        title: "Save Failed",
        description: error.message || "Failed to save configuration",
        variant: "destructive"
      });
    } finally {
      setIsSaving(false);
    }
  };

  // Get configured providers that support text generation
  const getTextProviders = () => {
    // Guard against missing or invalid providers data
    if (!providers || typeof providers !== 'object') {
      console.warn('[TextAI] Providers data is invalid:', providers);
      return [];
    }
    
    const textProviders = Object.entries(providers)
      .filter(([id, config]) => {
        // Guard against missing config or provider definition
        if (!config || !id) return false;
        
        const provider = AI_PROVIDERS[id];
        if (!provider) {
          console.warn(`[TextAI] Provider definition not found for: ${id}`);
          return false;
        }
        
        // Only show providers that are marked as configured (tested/connected)
        const isConfigured = config.status === 'tested' || config.status === 'connected' || config.configured === true;
        
        return provider?.supportsChat && isConfigured;
      })
      .map(([id, config]) => ({
        id,
        name: AI_PROVIDERS[id]?.displayName || id,
        models: Array.isArray(config.models) ? config.models : []
      }));
      
    console.log('[TextAI] Configured text providers:', textProviders);
    console.log('[TextAI] Current selection:', { selectedProvider, selectedModel });
    return textProviders;
  };

  // Get text generation models for selected provider
  const getTextModels = () => {
    // Guard against missing or invalid data
    if (!selectedProvider || !providers || !providers[selectedProvider]) {
      console.warn('[TextAI] Cannot get models - invalid provider data:', { selectedProvider, providers });
      return [];
    }
    
    const providerData = providers[selectedProvider];
    if (!providerData || !Array.isArray(providerData.models)) {
      console.warn('[TextAI] Provider models data is invalid:', providerData);
      return [];
    }
    
    const models = providerData.models;
    // Filter out embedding models
    const textModels = models.filter((model: string) => {
      if (typeof model !== 'string') return false;
      const lowerModel = model.toLowerCase();
      // For Ollama, be more specific about what to exclude
      if (selectedProvider === 'ollama') {
        return !(
          lowerModel.includes('embed') ||
          lowerModel === 'nomic-embed-text:latest' ||
          lowerModel === 'mxbai-embed-large:latest'
        );
      }
      // For other providers, use general filter
      return !(
        lowerModel.includes('embed') ||
        lowerModel.includes('e5-') ||
        lowerModel.includes('bge-') ||
        lowerModel.includes('sentence') ||
        lowerModel.includes('all-minilm')
      );
    });
    
    console.log('[TextAI] Text models for', selectedProvider, ':', textModels);
    return textModels;
  };

  const handleProviderChange = async (providerId: string) => {
    const newSelection = {
      ...modelSelection,
      textGeneration: {
        provider: providerId,
        model: '' // Reset model
      }
    };
    updateModelSelection(newSelection);
    setSavedConfig({ provider: providerId, model: '' });
    
    // Save to central config
    try {
      const currentConfig = await apiClient.getConfiguration();
      const modelSelectionItem = currentConfig.items?.find(i => i.key === 'ai.model_selection');
      const currentModelSelection = modelSelectionItem?.value || {};
      
      await apiClient.updateConfiguration({
        key: 'ai.model_selection',
        value: {
          ...(typeof currentModelSelection === 'object' ? currentModelSelection : {}),
          textGeneration: {
            provider: providerId,
            model: ''
          }
        }
      });
    } catch (error) {
      console.error('[TextAI] Failed to save provider selection:', error);
    }
    
    // Only trigger change detection if this is a user-initiated change
    if (providerId !== savedConfig?.provider) {
      onChangeDetected?.();
    }
  };

  const handleModelChange = async (model: string) => {
    const newSelection = {
      ...modelSelection,
      textGeneration: {
        provider: selectedProvider,
        model
      }
    };
    updateModelSelection(newSelection);
    setSavedConfig({ provider: selectedProvider, model });
    
    // Save to central config
    try {
      const currentConfig = await apiClient.getConfiguration();
      const modelSelectionItem = currentConfig.items?.find(i => i.key === 'ai.model_selection');
      const currentModelSelection = modelSelectionItem?.value || {};
      
      await apiClient.updateConfiguration({
        key: 'ai.model_selection',
        value: {
          ...(typeof currentModelSelection === 'object' ? currentModelSelection : {}),
          textGeneration: {
            provider: selectedProvider,
            model
          }
        }
      });
    } catch (error) {
      console.error('[TextAI] Failed to save model selection:', error);
    }
    
    // Only trigger change detection if this is a user-initiated change
    if (model !== savedConfig?.model) {
      onChangeDetected?.();
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Text AI Configuration</h2>
        <p className="text-muted-foreground mt-1">
          Configure language models for text generation and AI-enhanced search
        </p>
      </div>

      <Tabs defaultValue="model" className="space-y-4">
        <TabsList>
          <TabsTrigger value="model">Model Selection</TabsTrigger>
          <TabsTrigger value="parameters">Model Parameters</TabsTrigger>
          <TabsTrigger value="prompts">System Prompts</TabsTrigger>
        </TabsList>

        {/* Model Selection Tab */}
        <TabsContent value="model" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Language Model Selection</CardTitle>
              <CardDescription>
                Choose the AI provider and model for text generation
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <Alert>
                <Info className="h-4 w-4" />
                <AlertDescription>
                  Only providers that have been tested and support text generation are shown.
                  Test providers in the Providers tab first.
                </AlertDescription>
              </Alert>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="provider">AI Provider</Label>
                  <Select
                    value={selectedProvider}
                    onValueChange={handleProviderChange}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select provider" />
                    </SelectTrigger>
                    <SelectContent>
                      {getTextProviders().map((provider) => (
                        <SelectItem key={provider.id} value={provider.id}>
                          <div className="flex items-center gap-2">
                            <span>{AI_PROVIDERS[provider.id].icon}</span>
                            {provider.name}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="model">Model</Label>
                  <Select
                    value={selectedModel}
                    onValueChange={handleModelChange}
                    disabled={!selectedProvider}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select model" />
                    </SelectTrigger>
                    <SelectContent>
                      {getTextModels().map((model: string) => (
                        <SelectItem key={model} value={model}>
                          {model}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {selectedProvider && selectedModel && (
                <div className="p-4 border rounded-lg bg-muted/30">
                  <h4 className="font-medium mb-2">Current Saved Configuration</h4>
                  <div className="space-y-1 text-sm">
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Provider:</span>
                      <Badge variant="secondary">
                        {AI_PROVIDERS[selectedProvider]?.displayName}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Model:</span>
                      <Badge variant="secondary">{selectedModel}</Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">Status:</span>
                      <Badge variant="outline">Saved</Badge>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Model Parameters Tab */}
        <TabsContent value="parameters" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Model Parameters</CardTitle>
              <CardDescription>
                Fine-tune the behavior of your selected language model
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit(handleSaveConfig)} className="space-y-6">
                {!selectedModel ? (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Please select a provider and model in the Model Selection tab first.
                    </AlertDescription>
                  </Alert>
                ) : (
                  <>
                    <div className="grid grid-cols-2 gap-6">
                      <div className="space-y-2">
                        <Label htmlFor="temperature">Temperature</Label>
                        <div className="flex items-center gap-4">
                          <Slider
                            id="temperature"
                            min={0}
                            max={2}
                            step={0.1}
                            value={[watch('temperature')]}
                            onValueChange={(value) => {
                              setValue('temperature', value[0]);
                              onChangeDetected?.();
                            }}
                            className="flex-1"
                          />
                          <span className="w-12 text-sm">{watch('temperature')}</span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Controls randomness (0 = deterministic, 2 = very random)
                        </p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="topP">Top P</Label>
                        <div className="flex items-center gap-4">
                          <Slider
                            id="topP"
                            min={0}
                            max={1}
                            step={0.05}
                            value={[watch('topP')]}
                            onValueChange={(value) => {
                              setValue('topP', value[0]);
                              onChangeDetected?.();
                            }}
                            className="flex-1"
                          />
                          <span className="w-12 text-sm">{watch('topP')}</span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Nucleus sampling threshold
                        </p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="maxTokens">Max Tokens</Label>
                        <Input
                          id="maxTokens"
                          type="number"
                          {...register('maxTokens', { valueAsNumber: true })}
                          onChange={(e) => onChangeDetected?.()}
                        />
                        <p className="text-xs text-muted-foreground">
                          Maximum response length
                        </p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="topK">Top K (Optional)</Label>
                        <Input
                          id="topK"
                          type="number"
                          {...register('topK', { valueAsNumber: true })}
                          onChange={(e) => onChangeDetected?.()}
                        />
                        <p className="text-xs text-muted-foreground">
                          Top-k sampling (if supported)
                        </p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="presencePenalty">Presence Penalty</Label>
                        <div className="flex items-center gap-4">
                          <Slider
                            id="presencePenalty"
                            min={-2}
                            max={2}
                            step={0.1}
                            value={[watch('presencePenalty') || 0]}
                            onValueChange={(value) => {
                              setValue('presencePenalty', value[0]);
                              onChangeDetected?.();
                            }}
                            className="flex-1"
                          />
                          <span className="w-12 text-sm">{watch('presencePenalty') || 0}</span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Penalize new topics (-2 to 2)
                        </p>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="frequencyPenalty">Frequency Penalty</Label>
                        <div className="flex items-center gap-4">
                          <Slider
                            id="frequencyPenalty"
                            min={-2}
                            max={2}
                            step={0.1}
                            value={[watch('frequencyPenalty') || 0]}
                            onValueChange={(value) => {
                              setValue('frequencyPenalty', value[0]);
                              onChangeDetected?.();
                            }}
                            className="flex-1"
                          />
                          <span className="w-12 text-sm">{watch('frequencyPenalty') || 0}</span>
                        </div>
                        <p className="text-xs text-muted-foreground">
                          Penalize repetition (-2 to 2)
                        </p>
                      </div>
                    </div>

                    <div className="flex justify-end">
                      <Button type="submit" disabled={isSaving}>
                        {isSaving ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Save className="h-4 w-4 mr-2" />
                            Save Parameters
                          </>
                        )}
                      </Button>
                    </div>
                  </>
                )}
              </form>
            </CardContent>
          </Card>
        </TabsContent>

        {/* System Prompts Tab */}
        <TabsContent value="prompts" className="h-full">
          <SystemPromptsManager 
            onChangeDetected={onChangeDetected}
            onSaveSuccess={onSaveSuccess}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}