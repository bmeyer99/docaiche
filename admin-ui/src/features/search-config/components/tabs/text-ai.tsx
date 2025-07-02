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

interface TextAIConfigProps {
  onChangeDetected?: () => void;
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

export function TextAIConfig({ onChangeDetected }: TextAIConfigProps) {
  const [isSaving, setIsSaving] = useState(false);
  const { providers } = useProviderSettings();
  const { modelSelection, updateModelSelection } = useModelSelection();
  const apiClient = useApiClient();
  const { toast } = useToast();

  const { register, handleSubmit, watch, setValue } = useForm<ModelParameters>({
    defaultValues: {
      temperature: 0.7,
      topP: 0.9,
      topK: 40,
      maxTokens: 2048,
      presencePenalty: 0,
      frequencyPenalty: 0,
      systemPrompt: ''
    }
  });

  const selectedProvider = modelSelection.textGeneration.provider;
  const selectedModel = modelSelection.textGeneration.model;

  useEffect(() => {
    // Load saved model parameters
    loadModelParameters();
  }, [selectedProvider, selectedModel]);

  const loadModelParameters = async () => {
    if (!selectedProvider || !selectedModel) return;
    
    try {
      const params = await apiClient.getModelParameters(selectedProvider, selectedModel);
      if (params) {
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
      toast({
        title: "Configuration Saved",
        description: "Text AI model parameters updated successfully"
      });
      onChangeDetected?.();
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

  // Get tested providers that support text generation
  const getTextProviders = () => {
    return Object.entries(providers)
      .filter(([id, config]) => {
        const provider = AI_PROVIDERS[id];
        return (
          provider?.supportsChat &&
          (config.status === 'tested' || config.status === 'connected')
        );
      })
      .map(([id, config]) => ({
        id,
        name: AI_PROVIDERS[id].displayName,
        models: config.models || []
      }));
  };

  // Get text generation models for selected provider
  const getTextModels = () => {
    if (!selectedProvider || !providers[selectedProvider]) return [];
    
    const models = providers[selectedProvider].models || [];
    // Filter out embedding models
    return models.filter((model: string) => {
      const lowerModel = model.toLowerCase();
      return !(
        lowerModel.includes('embed') ||
        lowerModel.includes('e5-') ||
        lowerModel.includes('bge-') ||
        lowerModel.includes('sentence') ||
        lowerModel.includes('all-minilm')
      );
    });
  };

  const handleProviderChange = (providerId: string) => {
    updateModelSelection({
      ...modelSelection,
      textGeneration: {
        provider: providerId,
        model: '' // Reset model
      }
    });
    onChangeDetected?.();
  };

  const handleModelChange = (model: string) => {
    updateModelSelection({
      ...modelSelection,
      textGeneration: {
        ...modelSelection.textGeneration,
        model
      }
    });
    onChangeDetected?.();
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
                  <h4 className="font-medium mb-2">Selected Configuration</h4>
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
        <TabsContent value="prompts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>System Prompts</CardTitle>
              <CardDescription>
                Configure system prompts for different use cases
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="systemPrompt">Default System Prompt</Label>
                <Textarea
                  id="systemPrompt"
                  {...register('systemPrompt')}
                  placeholder="Enter a system prompt to guide the AI's behavior..."
                  className="min-h-[200px] font-mono text-sm"
                  onChange={(e) => onChangeDetected?.()}
                />
                <p className="text-xs text-muted-foreground mt-2">
                  This prompt will be prepended to all AI requests to set context and behavior
                </p>
              </div>

              <div className="space-y-4">
                <h4 className="font-medium">Prompt Templates</h4>
                <div className="grid gap-3">
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <h5 className="font-medium">Search Enhancement</h5>
                      <Badge variant="secondary">Default</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      You are an AI assistant helping users find technical documentation. 
                      Provide clear, concise answers based on the search results provided.
                    </p>
                  </div>
                  
                  <div className="p-4 border rounded-lg">
                    <div className="flex items-center justify-between mb-2">
                      <h5 className="font-medium">Code Explanation</h5>
                      <Badge variant="secondary">Custom</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      You are a code expert. When presented with code snippets, explain them 
                      clearly, identify potential issues, and suggest improvements.
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex justify-end">
                <Button onClick={() => handleSubmit(handleSaveConfig)()} disabled={isSaving}>
                  {isSaving ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
                      Save Prompts
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}