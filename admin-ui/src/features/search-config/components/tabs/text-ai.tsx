'use client';

/**
 * Text AI configuration tab
 * 
 * Refactored to use proper state synchronization with change tracking
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
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

interface TextGenerationConfig {
  provider: string;
  model: string;
}

export function TextAIConfig({ onChangeDetected, onSaveSuccess }: TextAIConfigProps) {
  const [isSaving, setIsSaving] = useState(false);
  const { providers } = useProviderSettings();
  const { modelSelection, updateModelSelection } = useModelSelection();
  const apiClient = useApiClient();
  const { toast } = useToast();
  const { modelParameters, updateModelParameters } = useSearchConfig();
  
  // Track saved state to detect changes
  const [savedTextGenConfig, setSavedTextGenConfig] = useState<TextGenerationConfig>({
    provider: '',
    model: ''
  });
  
  // Current text generation config
  const [textGenConfig, setTextGenConfig] = useState<TextGenerationConfig>({
    provider: '',
    model: ''
  });
  
  // Track if this is a system update (loading saved values)
  const isSystemUpdateRef = useRef(false);
  
  // Selected provider and model
  const selectedProvider = textGenConfig.provider || modelSelection.textGeneration.provider;
  const selectedModel = textGenConfig.model || modelSelection.textGeneration.model;
  
  // Track saved parameters for current model
  const [savedParams, setSavedParams] = useState<ModelParameters>({
    temperature: 0.7,
    topP: 0.9,
    topK: 40,
    maxTokens: 2048,
    presencePenalty: 0,
    frequencyPenalty: 0,
    systemPrompt: ''
  });
  
  // Current parameters
  const [currentParams, setCurrentParams] = useState<ModelParameters>({
    temperature: 0.7,
    topP: 0.9,
    topK: 40,
    maxTokens: 2048,
    presencePenalty: 0,
    frequencyPenalty: 0,
    systemPrompt: ''
  });
  
  // Check if configuration has changed
  const hasTextGenChanges = 
    textGenConfig.provider !== savedTextGenConfig.provider ||
    textGenConfig.model !== savedTextGenConfig.model;
    
  const hasParamChanges = JSON.stringify(currentParams) !== JSON.stringify(savedParams);
  
  // Notify parent when changes are detected
  useEffect(() => {
    if ((hasTextGenChanges || hasParamChanges) && !isSystemUpdateRef.current && onChangeDetected) {
      onChangeDetected();
    }
  }, [hasTextGenChanges, hasParamChanges, onChangeDetected]);
  
  // Load saved configuration from synchronized state
  useEffect(() => {
    if (modelSelection.textGeneration?.provider && modelSelection.textGeneration?.model) {
      isSystemUpdateRef.current = true;
      const config = {
        provider: modelSelection.textGeneration.provider,
        model: modelSelection.textGeneration.model
      };
      setTextGenConfig(config);
      setSavedTextGenConfig(config);
      isSystemUpdateRef.current = false;
      console.log('[TextAI] Loaded saved configuration from synchronized state:', config);
    }
  }, [modelSelection.textGeneration]);
  
  // Load model parameters when selection changes
  useEffect(() => {
    if (selectedProvider && selectedModel) {
      isSystemUpdateRef.current = true;
      
      // Check if we already have loaded parameters
      const loadedParams = modelParameters[selectedProvider]?.[selectedModel];
      if (loadedParams) {
        setCurrentParams(loadedParams);
        setSavedParams(loadedParams);
        isSystemUpdateRef.current = false;
      } else {
        // Load from API
        loadModelParameters();
      }
    }
  }, [selectedProvider, selectedModel]);
  
  const loadModelParameters = async () => {
    if (!selectedProvider || !selectedModel) return;
    
    try {
      const params = await apiClient.getModelParameters(selectedProvider, selectedModel);
      if (params) {
        // Update context
        updateModelParameters(selectedProvider, selectedModel, params);
        setCurrentParams(params);
        setSavedParams(params);
      }
    } catch (error) {
      console.error('Failed to load model parameters:', error);
    } finally {
      isSystemUpdateRef.current = false;
    }
  };
  
  const handleSaveConfig = async () => {
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
      // Save model parameters
      await apiClient.updateModelParameters(selectedProvider, selectedModel, currentParams);
      updateModelParameters(selectedProvider, selectedModel, currentParams);
      
      // Save text generation config
      const currentConfig = await apiClient.getConfiguration();
      const modelSelectionItem = currentConfig.items?.find(i => i.key === 'ai.model_selection');
      const currentModelSelection = modelSelectionItem?.value || {};
      
      await apiClient.updateConfiguration({
        key: 'ai.model_selection',
        value: {
          ...(typeof currentModelSelection === 'object' ? currentModelSelection : {}),
          textGeneration: {
            provider: selectedProvider,
            model: selectedModel
          }
        }
      });
      
      // Update saved state
      setSavedTextGenConfig({
        provider: selectedProvider,
        model: selectedModel
      });
      setSavedParams(currentParams);
      
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
    if (!providers || typeof providers !== 'object') {
      console.warn('[TextAI] Providers data is invalid:', providers);
      return [];
    }
    
    const textProviders = Object.entries(providers)
      .filter(([id, config]) => {
        if (!config || !id) return false;
        
        const provider = AI_PROVIDERS[id];
        if (!provider) {
          console.warn(`[TextAI] Provider definition not found for: ${id}`);
          return false;
        }
        
        // Only show providers that are marked as configured (tested/connected)
        // Check multiple status indicators for robustness
        const isConfigured = 
          config.status === 'tested' || 
          config.status === 'connected' || 
          config.configured === true ||
          (config.models && Array.isArray(config.models) && config.models.length > 0);
        
        const supportsChat = provider?.supportsChat || false;
        
        console.log(`[TextAI] Provider ${id}:`, {
          status: config.status,
          configured: config.configured,
          hasModels: config.models?.length > 0,
          supportsChat,
          isConfigured
        });
        
        return supportsChat && isConfigured;
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

  const handleProviderChange = (providerId: string) => {
    setTextGenConfig({
      provider: providerId,
      model: ''
    });
    
    // Update model selection context
    const newSelection = {
      ...modelSelection,
      textGeneration: {
        provider: providerId,
        model: ''
      }
    };
    updateModelSelection(newSelection);
  };

  const handleModelChange = (model: string) => {
    setTextGenConfig({
      provider: selectedProvider,
      model
    });
    
    // Update model selection context
    const newSelection = {
      ...modelSelection,
      textGeneration: {
        provider: selectedProvider,
        model
      }
    };
    updateModelSelection(newSelection);
  };
  
  const handleParameterChange = (key: keyof ModelParameters, value: any) => {
    setCurrentParams({
      ...currentParams,
      [key]: value
    });
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
                  <h4 className="font-medium mb-2">Current Configuration</h4>
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
                      <Badge variant={hasTextGenChanges || hasParamChanges ? "default" : "outline"}>
                        {hasTextGenChanges || hasParamChanges ? "Unsaved Changes" : "Saved"}
                      </Badge>
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
              {!selectedModel ? (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    Please select a provider and model in the Model Selection tab first.
                  </AlertDescription>
                </Alert>
              ) : (
                <div className="space-y-6">
                  <div className="grid grid-cols-2 gap-6">
                    <div className="space-y-2">
                      <Label htmlFor="temperature">Temperature</Label>
                      <div className="flex items-center gap-4">
                        <Slider
                          id="temperature"
                          min={0}
                          max={2}
                          step={0.1}
                          value={[currentParams.temperature]}
                          onValueChange={(value) => handleParameterChange('temperature', value[0])}
                          className="flex-1"
                        />
                        <span className="w-12 text-sm">{currentParams.temperature}</span>
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
                          value={[currentParams.topP]}
                          onValueChange={(value) => handleParameterChange('topP', value[0])}
                          className="flex-1"
                        />
                        <span className="w-12 text-sm">{currentParams.topP}</span>
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
                        value={currentParams.maxTokens}
                        onChange={(e) => handleParameterChange('maxTokens', parseInt(e.target.value) || 0)}
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
                        value={currentParams.topK || ''}
                        onChange={(e) => handleParameterChange('topK', e.target.value ? parseInt(e.target.value) : undefined)}
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
                          value={[currentParams.presencePenalty || 0]}
                          onValueChange={(value) => handleParameterChange('presencePenalty', value[0])}
                          className="flex-1"
                        />
                        <span className="w-12 text-sm">{currentParams.presencePenalty || 0}</span>
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
                          value={[currentParams.frequencyPenalty || 0]}
                          onValueChange={(value) => handleParameterChange('frequencyPenalty', value[0])}
                          className="flex-1"
                        />
                        <span className="w-12 text-sm">{currentParams.frequencyPenalty || 0}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Penalize repetition (-2 to 2)
                      </p>
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <Button 
                      onClick={handleSaveConfig} 
                      disabled={isSaving || (!hasTextGenChanges && !hasParamChanges)}
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
                </div>
              )}
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