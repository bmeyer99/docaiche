'use client';

import { useState, useEffect } from 'react';
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
import { cn } from '@/lib/utils';
import { Input } from '@/components/ui/input';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

interface ModelConfiguration {
  provider: string;
  model: string;
  status: 'healthy' | 'testing' | 'error' | 'not_configured';
}

interface ModelSelectionConfig {
  textGeneration: ModelConfiguration;
  embeddings: ModelConfiguration;
  sharedProvider: boolean;
}

interface ProviderModels {
  provider: string;
  models: string[];
  queryable: boolean;
  message?: string;
  custom_count?: number;
}

export default function ModelSelection() {
  const [config, setConfig] = useState<ModelSelectionConfig>({
    textGeneration: { provider: '', model: '', status: 'not_configured' },
    embeddings: { provider: '', model: '', status: 'not_configured' },
    sharedProvider: false
  });
  const [testing, setTesting] = useState<{ text: boolean; embeddings: boolean }>({
    text: false,
    embeddings: false
  });
  const [providerModels, setProviderModels] = useState<Record<string, ProviderModels>>({});
  const [customModelInput, setCustomModelInput] = useState<Record<string, string>>({});
  const [providerConfigs, setProviderConfigs] = useState<any[]>([]);
  const { toast } = useToast();
  const apiClient = useApiClient();

  // Define queryable providers
  const queryableProviders = ['ollama', 'lmstudio', 'openrouter'];

  // Load existing configuration and provider configs on mount
  useEffect(() => {
    const loadData = async () => {
      try {
        // Load model selection config
        const existingConfig = await apiClient.getModelSelection();
        if (existingConfig) {
          // Add default status to loaded config
          setConfig({
            textGeneration: {
              ...existingConfig.textGeneration,
              status: 'not_configured'
            },
            embeddings: {
              ...existingConfig.embeddings,
              status: 'not_configured'
            },
            sharedProvider: existingConfig.sharedProvider
          });
        }

        // Load provider configurations to check what's configured
        const configs = await apiClient.getProviderConfigurations();
        setProviderConfigs(configs || []);
      } catch {
        // Silently ignore error on load
      }
    };
    
    loadData();
  }, [apiClient]);

  // Load models for non-queryable providers on mount
  useEffect(() => {
    const loadInitialModels = async () => {
      const nonQueryableProviders = Object.keys(AI_PROVIDERS).filter(
        id => !queryableProviders.includes(id.toLowerCase())
      );

      for (const providerId of nonQueryableProviders) {
        try {
          const response = await apiClient.getProviderModels(providerId);
          setProviderModels(prev => ({
            ...prev,
            [providerId]: response
          }));
        } catch (error) {
          // Use empty models on error
          setProviderModels(prev => ({
            ...prev,
            [providerId]: {
              provider: providerId,
              models: [],
              queryable: false
            }
          }));
        }
      }
    };

    loadInitialModels();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiClient]);

  // Check if a provider is configured
  const isProviderConfigured = (providerId: string): boolean => {
    const config = providerConfigs.find(c => c.id === providerId);
    if (!config) return false;

    const provider = AI_PROVIDERS[providerId];
    if (!provider) return false;

    // Check if required fields are filled
    if (provider.requiresApiKey && !config.config?.api_key) return false;
    
    // For local providers, check if base URL is set (if it's not using default)
    if (providerId === 'ollama' || providerId === 'lmstudio') {
      return !!config.config?.base_url || !!provider.defaultBaseUrl;
    }

    return true;
  };

  // Get enabled providers only (that are configured)
  const getEnabledProviders = (): ProviderDefinition[] => {
    return Object.values(AI_PROVIDERS);
  };

  // Get models for a provider
  const getModelsForProvider = (providerId: string): string[] => {
    const cached = providerModels[providerId];
    if (cached) {
      return cached.models;
    }
    return [];
  };

  const getProviderIcon = (providerId: string) => {
    const provider = AI_PROVIDERS[providerId];
    return provider?.icon || '🤖';
  };

  const getProviderColor = (providerId: string) => {
    const provider = AI_PROVIDERS[providerId];
    return provider?.color || '#6b7280';
  };

  const handleProviderChange = async (section: 'textGeneration' | 'embeddings', providerId: string) => {
    // Check if provider is configured
    if (!isProviderConfigured(providerId)) {
      toast({
        title: "Provider Not Configured",
        description: `Please configure ${AI_PROVIDERS[providerId]?.displayName} first by scrolling down to the Individual Provider Configuration section.`,
        variant: "destructive"
      });
      return;
    }

    const newConfig = {
      ...config,
      [section]: {
        ...config[section],
        provider: providerId,
        model: '', // Clear model when provider changes
        status: 'not_configured' as const
      }
    };

    // If shared provider is enabled, sync both sections
    if (config.sharedProvider && section === 'textGeneration') {
      newConfig.embeddings = {
        ...newConfig.textGeneration
      };
    }

    setConfig(newConfig);

    // For queryable providers, we need to test connection first to get models
    if (queryableProviders.includes(providerId.toLowerCase())) {
      toast({
        title: "Test Required",
        description: `Please test the ${AI_PROVIDERS[providerId]?.displayName} connection to discover available models`,
      });
    }
  };

  const handleModelChange = (section: 'textGeneration' | 'embeddings', model: string) => {
    const newConfig = {
      ...config,
      [section]: {
        ...config[section],
        model,
        status: 'not_configured' as const
      }
    };

    // If shared provider is enabled, sync both sections
    if (config.sharedProvider && section === 'textGeneration') {
      newConfig.embeddings = {
        ...newConfig.textGeneration
      };
    }

    setConfig(newConfig);
  };

  const handleSharedProviderToggle = (enabled: boolean) => {
    const newConfig = {
      ...config,
      sharedProvider: enabled
    };

    // If enabling shared provider, copy text generation config to embeddings
    if (enabled) {
      newConfig.embeddings = { ...config.textGeneration };
    }

    setConfig(newConfig);
  };

  const testConfiguration = async (section: 'textGeneration' | 'embeddings') => {
    const sectionConfig = config[section];
    if (!sectionConfig.provider) {
      toast({
        title: "Configuration Required",
        description: "Please select a provider first",
        variant: "destructive"
      });
      return;
    }

    setTesting(prev => ({ ...prev, [section === 'textGeneration' ? 'text' : 'embeddings']: true }));

    try {
      // Get provider configuration (base_url, api_key, etc.)
      const providerConfig = providerConfigs.find(p => p.id === sectionConfig.provider);
      
      // Test the provider connection
      const result = await apiClient.testProviderConnection(sectionConfig.provider, {
        base_url: providerConfig?.config?.base_url || '',
        api_key: providerConfig?.config?.api_key || '',
        model: sectionConfig.model || ''
      });

      const newStatus: ModelConfiguration['status'] = result.success ? 'healthy' : 'error';
      
      setConfig(prev => ({
        ...prev,
        [section]: {
          ...prev[section],
          status: newStatus
        }
      }));

      // If successful and models were returned, update the provider models
      if (result.success && result.models && result.models.length > 0) {
        setProviderModels(prev => ({
          ...prev,
          [sectionConfig.provider]: {
            provider: sectionConfig.provider,
            models: result.models || [],
            queryable: true
          }
        }));

        // Auto-select first model if none selected
        if (!sectionConfig.model && result.models.length > 0) {
          handleModelChange(section, result.models[0]);
        }
      }

      toast({
        title: result.success ? "Test Successful" : "Test Failed",
        description: result.message,
        variant: result.success ? "default" : "destructive"
      });
    } catch (error) {
      setConfig(prev => ({
        ...prev,
        [section]: {
          ...prev[section],
          status: 'error'
        }
      }));

      toast({
        title: "Test Failed",
        description: "Failed to test configuration",
        variant: "destructive"
      });
    } finally {
      setTesting(prev => ({ ...prev, [section === 'textGeneration' ? 'text' : 'embeddings']: false }));
    }
  };

  const addCustomModel = async (providerId: string) => {
    const modelName = customModelInput[providerId]?.trim();
    if (!modelName) return;

    try {
      await apiClient.addCustomModel(providerId, modelName);
      
      // Reload models for this provider
      const response = await apiClient.getProviderModels(providerId);
      setProviderModels(prev => ({
        ...prev,
        [providerId]: response
      }));

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

  // const removeCustomModel = async (providerId: string, modelName: string) => {
  //   try {
  //     await apiClient.removeCustomModel(providerId, modelName);
      
  //     // Reload models for this provider
  //     const response = await apiClient.getProviderModels(providerId);
  //     setProviderModels(prev => ({
  //       ...prev,
  //       [providerId]: response
  //     }));

  //     toast({
  //       title: "Model Removed",
  //       description: `Removed custom model: ${modelName}`,
  //     });
  //   } catch (error: any) {
  //     toast({
  //       title: "Failed to Remove Model",
  //       description: error.message || "Could not remove custom model",
  //       variant: "destructive"
  //     });
  //   }
  // };

  const saveConfiguration = async () => {
    try {
      // Use the convenience method for cleaner code
      await apiClient.updateModelSelection(config);
      
      toast({
        title: "Configuration Saved",
        description: "Model selection preferences have been saved",
      });
    } catch (error) {
      toast({
        title: "Save Failed",
        description: "Failed to save model selection configuration",
        variant: "destructive"
      });
    }
  };

  const getStatusIcon = (status: ModelConfiguration['status']) => {
    switch (status) {
      case 'healthy': return <Icons.checkCircle className="w-4 h-4 text-green-500" />;
      case 'testing': return <Icons.spinner className="w-4 h-4 animate-spin text-blue-500" />;
      case 'error': return <Icons.alertCircle className="w-4 h-4 text-red-500" />;
      default: return <Icons.circle className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusText = (status: ModelConfiguration['status']) => {
    switch (status) {
      case 'healthy': return 'Ready';
      case 'testing': return 'Testing...';
      case 'error': return 'Error';
      default: return 'Not configured';
    }
  };

  const scrollToProviderConfig = () => {
    // Find the provider configuration section and scroll to it
    const element = document.querySelector('[data-provider-config]');
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  const renderModelSection = (
    section: 'textGeneration' | 'embeddings',
    title: string,
    description: string,
    disabled = false
  ) => {
    const sectionConfig = config[section];
    const isTextSection = section === 'textGeneration';
    const testingKey = isTextSection ? 'text' : 'embeddings';
    const isQueryable = sectionConfig.provider && queryableProviders.includes(sectionConfig.provider.toLowerCase());
    const models = getModelsForProvider(sectionConfig.provider);
    const providerInfo = providerModels[sectionConfig.provider];
    const isConfigured = sectionConfig.provider ? isProviderConfigured(sectionConfig.provider) : true;

    return (
      <div className={cn("space-y-4", disabled && "opacity-50 pointer-events-none")}>
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium">{title}</h3>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
          <div className="flex items-center gap-2">
            {getStatusIcon(sectionConfig.status)}
            <span className="text-sm font-medium">{getStatusText(sectionConfig.status)}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Provider</Label>
            <Select
              value={sectionConfig.provider}
              onValueChange={(value) => handleProviderChange(section, value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select provider" />
              </SelectTrigger>
              <SelectContent>
                {getEnabledProviders().map((provider) => {
                  const configured = isProviderConfigured(provider.id);
                  return (
                    <SelectItem 
                      key={provider.id} 
                      value={provider.id}
                      className={cn(!configured && "opacity-60")}
                    >
                      <div className="flex items-center gap-2">
                        <span style={{ color: getProviderColor(provider.id) }}>
                          {getProviderIcon(provider.id)}
                        </span>
                        {provider.displayName}
                        {!configured && (
                          <Badge variant="outline" className="ml-2 text-xs border-amber-500 text-amber-600 dark:border-amber-600 dark:text-amber-400">
                            Not Configured
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
            {isQueryable && models.length === 0 ? (
              <div className="text-sm text-muted-foreground p-2 border rounded-md bg-muted/50">
                Test connection to discover models
              </div>
            ) : (
              <Select
                value={sectionConfig.model}
                onValueChange={(value) => handleModelChange(section, value)}
                disabled={!sectionConfig.provider || (!!isQueryable && models.length === 0) || !isConfigured}
              >
                <SelectTrigger>
                  <SelectValue placeholder={models.length > 0 ? "Select model" : "No models available"} />
                </SelectTrigger>
                <SelectContent>
                  {models.map((model) => (
                    <SelectItem key={model} value={model}>
                      {model}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </div>

        {/* Show configuration alert if provider not configured */}
        {sectionConfig.provider && !isConfigured && (
          <Alert className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950">
            <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            <AlertDescription className="text-amber-800 dark:text-amber-200">
              <strong>{AI_PROVIDERS[sectionConfig.provider]?.displayName}</strong> needs to be configured first.
              {AI_PROVIDERS[sectionConfig.provider]?.requiresApiKey && " An API key is required."}
              {(sectionConfig.provider === 'ollama' || sectionConfig.provider === 'lmstudio') && " A base URL is required."}
              {' '}
              <button
                onClick={scrollToProviderConfig}
                className="underline text-amber-700 hover:text-amber-800 dark:text-amber-300 dark:hover:text-amber-200"
              >
                → Configure provider below
              </button>
            </AlertDescription>
          </Alert>
        )}

        {/* Custom model management for non-queryable providers */}
        {sectionConfig.provider && !isQueryable && providerInfo && isConfigured && (
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
            {providerInfo.custom_count && providerInfo.custom_count > 0 && (
              <div className="text-xs text-muted-foreground">
                {providerInfo.custom_count} custom model{providerInfo.custom_count > 1 ? 's' : ''} added
              </div>
            )}
          </div>
        )}

        <Button
          variant="outline"
          onClick={() => testConfiguration(section)}
          disabled={testing[testingKey] || !sectionConfig.provider || !isConfigured}
          className="w-full"
        >
          {testing[testingKey] ? (
            <>
              <Icons.spinner className="w-4 h-4 mr-2 animate-spin" />
              Testing...
            </>
          ) : (
            <>
              <Icons.activity className="w-4 h-4 mr-2" />
              Test Configuration
            </>
          )}
        </Button>
      </div>
    );
  };

  // Count how many providers are configured
  const configuredProviders = Object.keys(AI_PROVIDERS).filter(id => isProviderConfigured(id));
  const totalProviders = Object.keys(AI_PROVIDERS).length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Icons.settings className="w-5 h-5" />
          Model Selection
        </CardTitle>
        <CardDescription>
          Select which AI providers and models to use for text generation and embeddings.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Configuration Status Alert */}
        {configuredProviders.length === 0 ? (
          <Alert className="border-amber-200 bg-amber-50 dark:border-amber-900 dark:bg-amber-950">
            <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            <AlertDescription className="text-amber-800 dark:text-amber-200">
              <strong>No providers configured yet!</strong> You need to configure at least one provider below before you can select models.
              <button
                onClick={() => {
                  const element = document.querySelector('[data-provider-config]');
                  if (element) {
                    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                  }
                }}
                className="block mt-2 underline text-amber-700 hover:text-amber-800 dark:text-amber-300 dark:hover:text-amber-200"
              >
                → Configure providers below
              </button>
            </AlertDescription>
          </Alert>
        ) : configuredProviders.length < totalProviders ? (
          <Alert>
            <Icons.zap className="h-4 w-4" />
            <AlertDescription>
              <strong>{configuredProviders.length} of {totalProviders} providers configured.</strong> Only configured providers are available for selection.
              {configuredProviders.length < 3 && (
                <button
                  onClick={() => {
                    const element = document.querySelector('[data-provider-config]');
                    if (element) {
                      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                  }}
                  className="block mt-1 text-sm underline text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
                >
                  Configure more providers
                </button>
              )}
            </AlertDescription>
          </Alert>
        ) : null}

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
          'Choose the provider and model for document embeddings and semantic search',
          config.sharedProvider
        )}

        {config.sharedProvider && (
          <div className="flex items-center gap-2 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <Icons.zap className="w-4 h-4 text-blue-600" />
            <span className="text-sm text-blue-700">
              Embeddings configuration is synced with text generation
            </span>
          </div>
        )}

        {/* Save Button */}
        <div className="flex justify-end">
          <Button onClick={saveConfiguration} className="px-6">
            <Icons.check className="w-4 h-4 mr-2" />
            Save Configuration
          </Button>
        </div>

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
      </CardContent>
    </Card>
  );
}