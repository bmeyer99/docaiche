'use client';

import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Icons } from '@/components/icons';
import { AI_PROVIDERS, ProviderDefinition } from '@/lib/config/providers';
import { useToast } from '@/hooks/use-toast';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useProviderTestCache } from '@/lib/hooks/use-provider-test-cache';
import { useModelSelection } from '@/lib/hooks/use-provider-settings';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import ProviderConfigurationSection from './provider-configuration-section';

// Save Model Configuration Button Component
function SaveModelConfigurationButton() {
  const [isSaving, setIsSaving] = useState(false);
  const { toast } = useToast();
  const apiClient = useApiClient();
  const { modelSelection: config } = useModelSelection();

  const handleSaveConfiguration = async () => {
    setIsSaving(true);
    try {
      await apiClient.updateModelSelection(config);
      toast({
        title: "Configuration Saved",
        description: "Model selection configuration has been saved successfully.",
      });
    } catch (error: any) {
      toast({
        title: "Save Failed",
        description: error.message || "Failed to save model configuration. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const hasValidConfig = config.textGeneration.provider && config.textGeneration.model &&
                         config.embeddings.provider && config.embeddings.model;

  return (
    <Button
      onClick={handleSaveConfiguration}
      disabled={isSaving || !hasValidConfig}
      className="flex items-center gap-2"
    >
      {isSaving ? (
        <>
          <Icons.spinner className="w-4 h-4 animate-spin" />
          Saving Configuration...
        </>
      ) : (
        <>
          <Icons.check className="w-4 h-4" />
          Save Model Configuration
        </>
      )}
    </Button>
  );
}


export default function ProvidersConfigPage() {
  const [customModelInput, setCustomModelInput] = useState<Record<string, string>>({});
  const { toast } = useToast();
  const apiClient = useApiClient();
  const testCache = useProviderTestCache();
  const { modelSelection: config, updateModelSelection } = useModelSelection();

  // No need to load configuration anymore - it comes from context

  // IMPORTANT: Models should only be loaded when user clicks "Test Connection"
  // No automatic model loading on page mount to prevent 500 errors

  const getEnabledProviders = (): (ProviderDefinition & { id: string })[] => {
    return Object.entries(AI_PROVIDERS).map(([id, provider]) => ({
      ...provider,
      id
    }));
  };

  const getProviderIcon = (providerId: string) => {
    const provider = AI_PROVIDERS[providerId];
    return provider?.icon || '🤖';
  };

  const getProviderColor = (providerId: string) => {
    const provider = AI_PROVIDERS[providerId];
    return provider?.color || '#6b7280';
  };

  const handleProviderChange = (section: 'textGeneration' | 'embeddings', providerId: string) => {
    const newConfig = {
      ...config,
      [section]: {
        ...config[section],
        provider: providerId,
        model: '', // Clear model when provider changes
      }
    };

    // If shared provider is enabled, sync both sections
    if (config.sharedProvider && section === 'textGeneration') {
      newConfig.embeddings = { ...newConfig.textGeneration };
    }

    updateModelSelection(newConfig);
  };

  const handleModelChange = (section: 'textGeneration' | 'embeddings', model: string) => {
    const newConfig = {
      ...config,
      [section]: {
        ...config[section],
        model,
      }
    };

    // If shared provider is enabled, sync both sections
    if (config.sharedProvider && section === 'textGeneration') {
      newConfig.embeddings = { ...newConfig.textGeneration };
    }

    updateModelSelection(newConfig);
  };

  const handleSharedProviderToggle = (enabled: boolean) => {
    const newConfig = {
      ...config,
      sharedProvider: enabled
    };

    // If enabling shared provider, sync provider but keep model separate
    if (enabled) {
      newConfig.embeddings = { 
        provider: config.textGeneration.provider,
        model: config.embeddings.model || '' // Keep existing embedding model or clear
      };
    }

    updateModelSelection(newConfig);
  };

  const addCustomModel = async (providerId: string) => {
    const modelName = customModelInput[providerId]?.trim();
    if (!modelName) return;

    try {
      await apiClient.addCustomModel(providerId, modelName);
      
      // Reload models for this provider
      const response = await apiClient.getProviderModels(providerId);
      if (response?.models) {
        const currentProvider = testCache.testedProviders[providerId];
        testCache.setProviderTested(providerId, response.models, currentProvider?.config || {});
      }

      // Clear input
      setCustomModelInput(prev => ({ ...prev, [providerId]: '' }));

      toast({
        title: "Model Added",
        description: `Added custom model: ${modelName}`,
      });
    } catch (error: any) {
      toast({
        title: "Failed to Add Model",
        description: error.message || "Could not add custom model",
        variant: "destructive"
      });
    }
  };

  // Configuration saving is now handled by the central ProviderSettings context

  const scrollToProviderConfig = () => {
    const element = document.querySelector('[data-provider-config]');
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const getProviderTestStatus = (providerId: string) => {
    const status = testCache.getProviderStatus(providerId);
    const models = testCache.getProviderModels(providerId);
    
    return {
      status,
      models,
      tested: status === 'tested',
      testing: status === 'testing',
      failed: status === 'failed',
      untested: status === 'untested'
    };
  };

  const renderModelSection = (
    section: 'textGeneration' | 'embeddings',
    title: string,
    description: string
  ) => {
    const sectionConfig = config[section];
    const providerTestStatus = sectionConfig.provider ? getProviderTestStatus(sectionConfig.provider) : null;
    const queryableProviders = ['ollama', 'lmstudio', 'openrouter'];
    const isQueryable = sectionConfig.provider && queryableProviders.includes(sectionConfig.provider.toLowerCase());

    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium">{title}</h3>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Provider</Label>
            <Select
              value={sectionConfig.provider}
              onValueChange={(value) => handleProviderChange(section, value)}
              disabled={section === 'embeddings' && config.sharedProvider}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select provider" />
              </SelectTrigger>
              <SelectContent>
                {getEnabledProviders().map((provider) => {
                  const testStatus = getProviderTestStatus(provider.id);
                  return (
                    <SelectItem 
                      key={provider.id} 
                      value={provider.id}
                    >
                      <div className="flex items-center gap-2">
                        <span style={{ color: getProviderColor(provider.id) }}>
                          {getProviderIcon(provider.id)}
                        </span>
                        {provider.displayName}
                        {testStatus.testing && (
                          <Badge variant="outline" className="ml-2 text-xs border-blue-500 text-blue-600">
                            Testing...
                          </Badge>
                        )}
                        {testStatus.tested && (
                          <Badge variant="outline" className="ml-2 text-xs border-green-500 text-green-600">
                            {testStatus.models.length} models
                          </Badge>
                        )}
                        {testStatus.failed && (
                          <Badge variant="outline" className="ml-2 text-xs border-red-500 text-red-600">
                            Failed
                          </Badge>
                        )}
                        {testStatus.untested && (
                          <Badge variant="outline" className="ml-2 text-xs border-amber-500 text-amber-600">
                            Not Tested
                          </Badge>
                        )}
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Model</Label>
            {providerTestStatus && !providerTestStatus.tested ? (
              <div className="flex items-center gap-2 p-2 border rounded-md bg-muted/50">
                <Clock className="w-4 h-4 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">
                  {providerTestStatus.testing ? 'Testing connection...' : 'Test provider connection first'}
                </span>
              </div>
            ) : (
              <Select
                value={sectionConfig.model}
                onValueChange={(value) => handleModelChange(section, value)}
                disabled={!sectionConfig.provider || !providerTestStatus?.tested}
              >
                <SelectTrigger>
                  <SelectValue placeholder={
                    providerTestStatus?.models.length ? "Select model" : "No models available"
                  } />
                </SelectTrigger>
                <SelectContent>
                  {providerTestStatus?.models
                    .filter((model) => {
                      // Always filter embedding models for embeddings section
                      if (section === 'embeddings') {
                        // Common embedding model patterns
                        const embeddingPatterns = [
                          'embed', 'embedding', 'sentence', 'e5-', 'bge-', 'nomic-embed',
                          'text-embedding', 'all-minilm', 'instructor'
                        ];
                        const modelLower = model.toLowerCase();
                        return embeddingPatterns.some(pattern => modelLower.includes(pattern));
                      }
                      
                      // For text generation, exclude embedding models
                      if (section === 'textGeneration') {
                        const embeddingPatterns = [
                          'embed', 'embedding', 'sentence', 'e5-', 'bge-', 'nomic-embed',
                          'text-embedding', 'all-minilm', 'instructor'
                        ];
                        const modelLower = model.toLowerCase();
                        return !embeddingPatterns.some(pattern => modelLower.includes(pattern));
                      }
                      
                      return true;
                    })
                    .map((model) => (
                      <SelectItem key={model} value={model}>
                        {model}
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>

        {/* Provider Test Status Alert */}
        {sectionConfig.provider && providerTestStatus && (
          <>
            {providerTestStatus.untested && (
              <Alert className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950">
                <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                <AlertDescription className="text-amber-800 dark:text-amber-200">
                  <strong>{AI_PROVIDERS[sectionConfig.provider]?.displayName}</strong> needs to be tested before models can be selected.
                  <button
                    onClick={scrollToProviderConfig}
                    className="block mt-1 underline text-amber-700 hover:text-amber-800 dark:text-amber-300 dark:hover:text-amber-200"
                  >
                    → Configure and test provider below
                  </button>
                </AlertDescription>
              </Alert>
            )}
            {providerTestStatus.failed && (
              <Alert className="border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950">
                <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
                <AlertDescription className="text-red-800 dark:text-red-200">
                  <strong>{AI_PROVIDERS[sectionConfig.provider]?.displayName}</strong> connection test failed.
                  <button
                    onClick={scrollToProviderConfig}
                    className="block mt-1 underline text-red-700 hover:text-red-800 dark:text-red-300 dark:hover:text-red-200"
                  >
                    → Fix configuration below
                  </button>
                </AlertDescription>
              </Alert>
            )}
            {providerTestStatus.tested && providerTestStatus.models.length === 0 && (
              <Alert className="border-orange-200 bg-orange-50 dark:border-orange-900 dark:bg-orange-950">
                <AlertCircle className="h-4 w-4 text-orange-600 dark:text-orange-400" />
                <AlertDescription className="text-orange-800 dark:text-orange-200">
                  <strong>{AI_PROVIDERS[sectionConfig.provider]?.displayName}</strong> connection succeeded but no models were found.
                </AlertDescription>
              </Alert>
            )}
            {providerTestStatus.tested && providerTestStatus.models.length > 0 && (
              <Alert className="border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950">
                <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
                <AlertDescription className="text-green-800 dark:text-green-200">
                  <strong>{providerTestStatus.models.length} model{providerTestStatus.models.length > 1 ? 's' : ''}</strong> available from {AI_PROVIDERS[sectionConfig.provider]?.displayName}
                </AlertDescription>
              </Alert>
            )}
          </>
        )}

        {/* Custom model management for non-queryable tested providers */}
        {sectionConfig.provider && !isQueryable && providerTestStatus?.tested && (
          <div className="space-y-2 p-3 border rounded-lg bg-muted/30">
            <Label className="text-sm">Custom Models</Label>
            <div className="flex gap-2">
              <Input
                placeholder="Enter custom model name"
                value={customModelInput[sectionConfig.provider] || ''}
                onChange={(e) => setCustomModelInput(prev => ({ 
                  ...prev, 
                  [sectionConfig.provider]: e.target.value 
                }))}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    addCustomModel(sectionConfig.provider);
                  }
                }}
              />
              <Button
                size="sm"
                variant="outline"
                onClick={() => addCustomModel(sectionConfig.provider)}
                disabled={!customModelInput[sectionConfig.provider]?.trim()}
              >
                <Icons.add className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </div>
    );
  };

  // Count how many providers are tested successfully
  const testedProviders = Object.values(testCache.testedProviders).filter(p => p.status === 'tested');
  const totalProviders = Object.keys(AI_PROVIDERS).length;
  
  // Only count providers that have been successfully tested, not just "configured"
  const configuredProviders = testedProviders; // This replaces the old logic that was counting untested providers

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">AI Provider Configuration</h1>
        <p className="text-muted-foreground">
          Configure your AI providers for text generation and embeddings
        </p>
      </div>

      {/* Model Selection Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Icons.settings className="w-5 h-5" />
            Model Selection
          </CardTitle>
          <CardDescription>
            Select which AI providers and models to use for text generation and embeddings.
            Test your providers below first to discover available models.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Configuration Status Alert */}
          {configuredProviders.length === 0 ? (
            <Alert className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950">
              <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <AlertDescription className="text-amber-800 dark:text-amber-200">
                <strong>No providers tested yet!</strong> You need to configure and test at least one provider below before you can select models.
                <button
                  onClick={scrollToProviderConfig}
                  className="block mt-2 underline text-amber-700 hover:text-amber-800 dark:text-amber-300 dark:hover:text-amber-200"
                >
                  → Configure and test providers below
                </button>
              </AlertDescription>
            </Alert>
          ) : (
            <Alert>
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <AlertDescription>
                <strong>{configuredProviders.length} of {totalProviders} providers tested successfully.</strong> 
                {' '}Models discovered: {configuredProviders.reduce((sum, p) => sum + p.models.length, 0)}
                {configuredProviders.length < totalProviders && (
                  <button
                    onClick={scrollToProviderConfig}
                    className="block mt-1 text-sm underline text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                  >
                    Test more providers below
                  </button>
                )}
              </AlertDescription>
            </Alert>
          )}

          {/* Shared Provider Toggle */}
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div className="space-y-1">
              <Label htmlFor="shared-provider">Use same provider for both</Label>
              <p className="text-sm text-muted-foreground">
                Enable this to use the same provider and model for both text generation and embeddings
              </p>
            </div>
            <Switch
              id="shared-provider"
              checked={config.sharedProvider}
              onCheckedChange={handleSharedProviderToggle}
            />
          </div>

          {/* Text Generation Section */}
          {renderModelSection(
            'textGeneration',
            'Text Generation',
            'Choose the provider and model for chat, completions, and text generation'
          )}

          <Separator />

          {/* Embeddings Section */}
          {renderModelSection(
            'embeddings',
            'Embeddings',
            config.sharedProvider 
              ? 'Choose the embedding model from the same provider'
              : 'Choose the provider and model for document embeddings and semantic search'
          )}

          {config.sharedProvider && (
            <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg dark:bg-blue-950 dark:border-blue-800">
              <Icons.zap className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span className="text-sm text-blue-700 dark:text-blue-300">
                Embeddings configuration is synced with text generation
              </span>
            </div>
          )}

          {/* Current Configuration Summary */}
          <div className="border-t pt-4">
            <h4 className="font-medium mb-3">Current Configuration</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium">Text Generation:</span>
                <div className="mt-1">
                  {config.textGeneration.provider ? (
                    <Badge variant="outline" className="mr-2">
                      {AI_PROVIDERS[config.textGeneration.provider]?.displayName} • {config.textGeneration.model || 'No model selected'}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">Not configured</span>
                  )}
                </div>
              </div>
              <div>
                <span className="font-medium">Embeddings:</span>
                <div className="mt-1">
                  {config.embeddings.provider ? (
                    <Badge variant="outline" className="mr-2">
                      {AI_PROVIDERS[config.embeddings.provider]?.displayName} • {config.embeddings.model || 'No model selected'}
                    </Badge>
                  ) : (
                    <span className="text-muted-foreground">Not configured</span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Save Configuration Button */}
          <div className="border-t pt-4">
            <SaveModelConfigurationButton />
          </div>
        </CardContent>
      </Card>

      {/* Provider Configuration Section */}
      <div data-provider-config>
        <ProviderConfigurationSection />
      </div>
    </div>
  );
}