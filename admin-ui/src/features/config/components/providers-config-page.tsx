'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { Icons } from '@/components/icons';
import { AI_PROVIDERS, ProviderDefinition, ProviderConfiguration } from '@/lib/config/providers';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';
import { useCircuitBreaker } from '@/lib/hooks/use-circuit-breaker';
import { CircuitBreakerIndicator } from '@/components/ui/circuit-breaker-indicator';
import { useDebouncedApi } from '@/lib/hooks/use-debounced-api';

export default function ProvidersConfigPage() {
  const [configurations, setConfigurations] = useState<Record<string, ProviderConfiguration>>({});
  const [loading, setLoading] = useState(false);
  const [activeProvider, setActiveProvider] = useState('ollama');
  const [isQuickSetup, setIsQuickSetup] = useState(false);
  const [quickSetupProvider, setQuickSetupProvider] = useState('');
  const { toast } = useToast();
  const router = useRouter();
  const apiClient = useApiClient();
  
  // Use debounced API hook instead of manual circuit breaker
  const {
    data: providerData,
    loading: providersLoading,
    error: providersError,
    refetch: refetchProviders,
    canMakeRequest,
    circuitState
  } = useDebouncedApi(
    () => apiClient.getProviderConfigurations(),
    'providers-api',
    {
      debounceMs: 2000, // 2 second debounce
      onSuccess: (data) => {
        // Convert array response to Record format expected by the component
        const configRecord = Array.isArray(data) 
          ? data.reduce((acc, provider) => {
              acc[provider.id] = {
                id: provider.id,
                name: provider.name,
                type: provider.type,
                status: provider.status,
                configured: provider.configured,
                enabled: provider.enabled || false,
                config: provider.config || {},
                // Preserve all other fields that might exist
                ...provider
              };
              return acc;
            }, {} as Record<string, any>)
          : data || {};
        setConfigurations(configRecord);
        
        // Check if this is first-time setup (no providers configured)
        const hasConfiguredProviders = Object.values(configRecord).some(
          (config: any) => config.configured || config.enabled
        );
        if (!hasConfiguredProviders) {
          setIsQuickSetup(true);
          // Default to Ollama for quick setup (most common local setup)
          setQuickSetupProvider('ollama');
          setActiveProvider('ollama');
        }
      },
      onError: (error) => {
        console.error('🔥 Provider configurations load failed:', error);
        
        // If backend is down, still show quick setup for first-time users
        setIsQuickSetup(true);
        setQuickSetupProvider('ollama');
        setActiveProvider('ollama');
        
        toast({
          title: "Backend Connection Issue",
          description: "Unable to load existing configurations. You can still set up a new provider.",
          variant: "destructive",
        });
      }
    }
  );

  // Circuit breaker for manual operations
  const providerCircuitBreaker = useCircuitBreaker('providers-manual', {
    failureThreshold: 2,
    resetTimeoutMs: 30000,
  });

  const saveConfiguration = async (providerId: string, config: Partial<ProviderConfiguration>) => {
    if (!providerCircuitBreaker.canMakeRequest) {
      const state = providerCircuitBreaker.getCircuitState();
      toast({
        title: "Backend Connection Issue",
        description: `Cannot save configuration - API unavailable (Circuit: ${state})`,
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      const updatedConfig = { ...configurations[providerId], ...config };
      await apiClient.updateProviderConfiguration(providerId, updatedConfig);
      providerCircuitBreaker.recordSuccess();
      
      setConfigurations(prev => ({ ...prev, [providerId]: updatedConfig }));
      toast({
        title: "Success",
        description: `${AI_PROVIDERS[providerId]?.displayName} configuration saved`,
      });
    } catch (error) {
      providerCircuitBreaker.recordFailure();
      console.error('🔥 Provider configuration save failed:', error);
      
      toast({
        title: "Error",
        description: "Failed to save configuration",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const completeQuickSetup = async () => {
    try {
      // Validate that a provider is selected
      if (!quickSetupProvider) {
        toast({
          title: "No Provider Selected",
          description: "Please select an AI provider to continue.",
          variant: "destructive",
        });
        return;
      }

      const providerDef = AI_PROVIDERS[quickSetupProvider];
      const config = configurations[quickSetupProvider] || {};
      
      // Validate required fields based on provider
      if (providerDef?.requiresApiKey && !config.config?.api_key) {
        toast({
          title: "API Key Required",
          description: `Please enter your ${providerDef.displayName} API key to continue.`,
          variant: "destructive",
        });
        return;
      }
      
      // Validate base URL is present
      if (!config.config?.base_url && !providerDef?.defaultBaseUrl) {
        toast({
          title: "Base URL Required",
          description: "Please enter the base URL for the provider.",
          variant: "destructive",
        });
        return;
      }

      // Save the configuration with proper values
      const finalConfig = {
        ...config,
        enabled: true,
        configured: true,
        config: {
          ...config.config,
          base_url: config.config?.base_url || providerDef?.defaultBaseUrl
        }
      };
      
      await saveConfiguration(quickSetupProvider, finalConfig);
      
      toast({
        title: "Setup Complete!",
        description: "Your AI provider has been configured. Redirecting to Analytics...",
      });
      
      // Navigate to analytics after brief delay
      setTimeout(() => {
        router.push('/dashboard/analytics');
      }, 1500);
      
    } catch (error) {
      console.error('🔥 Quick setup completion failed:', error);
      toast({
        title: "Error",
        description: "Failed to complete setup. Please try again.",
        variant: "destructive",
      });
    }
  };

  const testConnection = async (providerId: string) => {
    if (!providerCircuitBreaker.canMakeRequest) {
      const state = providerCircuitBreaker.getCircuitState();
      toast({
        title: "Backend Connection Issue",
        description: `Cannot test connection - API unavailable (Circuit: ${state})`,
        variant: "destructive",
      });
      return;
    }

    try {
      // Get the provider config for testing
      const providerConfig = configurations[providerId];
      if (!providerConfig) {
        toast({
          title: "Error",
          description: "Provider configuration not found",
          variant: "destructive",
        });
        return;
      }
      
      const result = await apiClient.testProviderConnection(providerId, {
        base_url: String(providerConfig.config?.base_url || ""),
        api_key: String(providerConfig.config?.api_key || ""),
        model: String(providerConfig.config?.model || "")
      });
      
      if (result.success) {
        providerCircuitBreaker.recordSuccess();
      } else {
        providerCircuitBreaker.recordFailure();
      }
      
      toast({
        title: result.success ? "Success" : "Error",
        description: result.message,
        variant: result.success ? "default" : "destructive",
      });
    } catch (error) {
      providerCircuitBreaker.recordFailure();
      console.error('🔥 Provider connection test failed:', error);
      
      toast({
        title: "Error",
        description: "Failed to test connection",
        variant: "destructive",
      });
    }
  };

  const getProvidersByCategory = () => {
    return Object.entries(AI_PROVIDERS).reduce((acc, [, provider]) => {
      if (!acc[provider.category]) acc[provider.category] = [];
      acc[provider.category].push(provider);
      return acc;
    }, {} as Record<string, Array<ProviderDefinition>>);
  };

  

  const renderQuickSetupCard = () => {
    const recommendedProviders = [
      { id: 'ollama', name: 'Ollama', description: 'Local AI - Easy setup, no API key required', color: '#10b981' },
      { id: 'openai', name: 'OpenAI', description: 'Cloud AI - Requires API key, high quality', color: '#0ea5e9' },
      { id: 'anthropic', name: 'Anthropic', description: 'Cloud AI - Claude models, requires API key', color: '#f59e0b' }
    ];

    return (
      <Card className="border-blue-200 bg-blue-50/50">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Icons.zap className="w-5 h-5 text-blue-600" />
            <CardTitle className="text-blue-900">Quick Setup</CardTitle>
            <Badge variant="secondary" className="bg-blue-100 text-blue-700">First Time</Badge>
          </div>
          <CardDescription className="text-blue-700">
            Get started quickly by configuring one AI provider. You can add more providers later.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3">
            <Label className="text-sm font-medium">Choose your preferred AI provider:</Label>
            {recommendedProviders.map(provider => (
              <div
                key={provider.id}
                className={`p-3 rounded-lg border cursor-pointer transition-all ${
                  quickSetupProvider === provider.id 
                    ? 'bg-white border-blue-300 shadow-sm ring-1 ring-blue-200' 
                    : 'bg-white/50 border-gray-200 hover:border-blue-200 hover:bg-white'
                }`}
                onClick={() => {
                  setQuickSetupProvider(provider.id);
                  setActiveProvider(provider.id);
                }}
              >
                <div className="flex items-center gap-3">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: provider.color }}
                  />
                  <div className="flex-1">
                    <div className="font-medium text-gray-900">{provider.name}</div>
                    <div className="text-xs text-gray-600">{provider.description}</div>
                  </div>
                  {quickSetupProvider === provider.id && (
                    <Icons.check className="w-4 h-4 text-blue-600" />
                  )}
                </div>
              </div>
            ))}
          </div>
          
          <div className="flex gap-2 pt-2">
            <Button 
              onClick={() => setIsQuickSetup(false)}
              variant="outline"
              className="flex-1"
            >
              Advanced Setup
            </Button>
            <Button 
              onClick={completeQuickSetup}
              disabled={!quickSetupProvider || loading || !canMakeRequest}
              className="flex-1 bg-blue-600 hover:bg-blue-700"
            >
              {loading ? (
                <>
                  <Icons.spinner className="w-4 h-4 mr-2 animate-spin" />
                  Setting up...
                </>
              ) : !canMakeRequest ? (
                <>
                  <Icons.alertCircle className="w-4 h-4 mr-2" />
                  Backend Unavailable
                </>
              ) : (
                <>
                  Complete Setup & Go to Analytics
                  <Icons.arrowRight className="w-4 h-4 ml-2" />
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  };

  const renderConfigurationForm = (provider: ProviderDefinition & { id: string }) => {
    const config = configurations[provider.id] || {};

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium">{provider.displayName} Configuration</h3>
            <p className="text-sm text-muted-foreground">{provider.description}</p>
          </div>
          <Switch
            checked={config.enabled || false}
            onCheckedChange={(enabled) => 
              saveConfiguration(provider.id, { ...config, enabled })
            }
          />
        </div>

        <Separator />

        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="baseUrl">Base URL</Label>
            <Input
              id="baseUrl"
              value={String(config.config?.base_url || provider.defaultBaseUrl || '')}
              onChange={(e) => 
                setConfigurations(prev => ({
                  ...prev,
                  [provider.id]: { 
                    ...config, 
                    config: { 
                      ...config.config, 
                      base_url: e.target.value 
                    }
                  }
                }))
              }
              placeholder={provider.defaultBaseUrl}
            />
          </div>

          {provider.requiresApiKey && (
            <div className="grid gap-2">
              <Label htmlFor="apiKey">API Key</Label>
              <Input
                id="apiKey"
                type="password"
                value={String(config.config?.api_key || '')}
                onChange={(e) => 
                  setConfigurations(prev => ({
                    ...prev,
                    [provider.id]: { 
                      ...config, 
                      config: { 
                        ...config.config, 
                        api_key: e.target.value 
                      }
                    }
                  }))
                }
                placeholder="Enter your API key"
              />
            </div>
          )}

          {provider.configFields?.map((field) => (
            <div key={field.key} className="grid gap-2">
              <Label htmlFor={field.key}>
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </Label>
              {false ? (
                <Textarea
                  id={field.key}
                  value={String(config.config?.[field.key] || '')}
                  onChange={(e) => 
                    setConfigurations(prev => ({
                      ...prev,
                      [provider.id]: { 
                        ...config, 
                        config: { 
                          ...config.config, 
                          [field.key]: e.target.value 
                        }
                      }
                    }))
                  }
                  placeholder={field.placeholder}
                />
              ) : field.type === 'number' ? (
                <Input
                  id={field.key}
                  type="number"
                  value={String(config.config?.[field.key] || '')}
                  onChange={(e) => 
                    setConfigurations(prev => ({
                      ...prev,
                      [provider.id]: { 
                        ...config, 
                        config: { 
                          ...config.config, 
                          [field.key]: parseInt(e.target.value) || 0
                        }
                      }
                    }))
                  }
                  placeholder={field.placeholder}
                />
              ) : (
                <Input
                  id={field.key}
                  value={String(config.config?.[field.key] || '')}
                  onChange={(e) => 
                    setConfigurations(prev => ({
                      ...prev,
                      [provider.id]: { 
                        ...config, 
                        config: { 
                          ...config.config, 
                          [field.key]: e.target.value 
                        }
                      }
                    }))
                  }
                  placeholder={field.placeholder}
                />
              )}
              {field.description && (
                <p className="text-xs text-muted-foreground">{field.description}</p>
              )}
            </div>
          ))}
        </div>

        <div className="flex gap-2">
          <Button 
            onClick={() => saveConfiguration(provider.id, config)}
            disabled={loading}
          >
            {loading ? (
              <>
                <Icons.spinner className="w-4 h-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              'Save Configuration'
            )}
          </Button>
          <Button 
            variant="outline" 
            onClick={() => testConnection(provider.id)}
            disabled={loading || !config.enabled}
          >
            <Icons.activity className="w-4 h-4 mr-2" />
            Test Connection
          </Button>
        </div>
      </div>
    );
  };

  const providersByCategory = getProvidersByCategory();
  const activeProviderData = AI_PROVIDERS[activeProvider];

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">
          {isQuickSetup ? 'Welcome to Docaiche!' : 'AI Providers Configuration'}
        </h1>
        <p className="text-muted-foreground">
          {isQuickSetup 
            ? 'Let\'s get you set up with an AI provider to start using the system'
            : 'Configure and manage AI providers for text generation and embeddings'
          }
        </p>
      </div>

      {/* Circuit Breaker Status */}
      <CircuitBreakerIndicator 
        identifier="providers-api" 
        onReset={refetchProviders}
      />
      
      {/* Show circuit state info */}
      {!canMakeRequest && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <Icons.alertCircle className="w-5 h-5 text-red-600" />
            <div>
              <div className="font-medium text-red-800">API Connection Blocked</div>
              <div className="text-sm text-red-600">
                Circuit breaker is {circuitState} - Provider API calls are temporarily disabled
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Setup Mode */}
      {isQuickSetup ? (
        <div className="max-w-2xl mx-auto">
          {renderQuickSetupCard()}
          
          {/* Show selected provider configuration */}
          {quickSetupProvider && activeProviderData && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: AI_PROVIDERS[quickSetupProvider]?.color || '#6b7280' }}
                  />
                  Configure {activeProviderData.displayName}
                </CardTitle>
                <CardDescription>
                  Complete the configuration for your selected provider
                </CardDescription>
              </CardHeader>
              <CardContent>
                {renderConfigurationForm(activeProviderData)}
              </CardContent>
            </Card>
          )}
        </div>
      ) : (
        /* Advanced Setup Mode */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Available Providers</CardTitle>
                    <CardDescription>Select a provider to configure</CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsQuickSetup(true)}
                    className="text-blue-600 border-blue-200 hover:bg-blue-50"
                  >
                    <Icons.zap className="w-4 h-4 mr-1" />
                    Quick Setup
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="p-0">
                <Tabs value={Object.keys(providersByCategory)[0]} className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="local">Local</TabsTrigger>
                    <TabsTrigger value="cloud">Cloud</TabsTrigger>
                    <TabsTrigger value="proxy">Proxy</TabsTrigger>
                  </TabsList>
                  {Object.entries(providersByCategory).map(([category, providers]) => (
                    <TabsContent key={category} value={category} className="space-y-2 p-4">
                      {providers.map(provider => (
                        <div
                          key={provider.id}
                          className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                            activeProvider === provider.id 
                              ? 'bg-accent border-accent-foreground' 
                              : 'hover:bg-accent/50'
                          }`}
                          onClick={() => setActiveProvider(provider.id)}
                        >
                          <div className="flex items-center gap-2">
                            <div 
                              className="w-3 h-3 rounded" 
                              style={{ backgroundColor: provider.color || '#6b7280' }}
                            />
                            <span className="font-medium">{provider.displayName}</span>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {provider.description}
                          </p>
                        </div>
                      ))}
                    </TabsContent>
                  ))}
                </Tabs>
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-2">
            <Card>
              <CardContent className="p-6">
                {activeProviderData ? (
                  renderConfigurationForm(activeProviderData)
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    Select a provider to configure
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}