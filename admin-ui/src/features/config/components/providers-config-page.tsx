'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Icons } from '@/components/icons';
import { AI_PROVIDERS, ProviderDefinition, ProviderConfiguration } from '@/lib/config/providers';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';

export default function ProvidersConfigPage() {
  const [configurations, setConfigurations] = useState<Record<string, ProviderConfiguration>>({});
  const [loading, setLoading] = useState(false);
  const [activeProvider, setActiveProvider] = useState('ollama');
  const { toast } = useToast();
  const apiClient = useApiClient();

  const loadProviderConfigurations = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getProviderConfigurations();
      // Convert array response to Record format expected by the component
      const configRecord = Array.isArray(data) 
        ? data.reduce((acc, provider) => {
            acc[provider.id] = {
              id: provider.id,
              name: provider.name,
              type: provider.type,
              status: provider.status,
              configured: provider.configured
            };
            return acc;
          }, {} as Record<string, any>)
        : data || {};
      setConfigurations(configRecord);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to load provider configurations",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [apiClient, toast]);

  useEffect(() => {
    loadProviderConfigurations();
  }, [loadProviderConfigurations]);

  const saveConfiguration = async (providerId: string, config: Partial<ProviderConfiguration>) => {
    setLoading(true);
    try {
      const updatedConfig = { ...configurations[providerId], ...config };
      await apiClient.updateProviderConfiguration(providerId, updatedConfig);
      setConfigurations(prev => ({ ...prev, [providerId]: updatedConfig }));
      toast({
        title: "Success",
        description: `${AI_PROVIDERS[providerId]?.displayName} configuration saved`,
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save configuration",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async (providerId: string) => {
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
      toast({
        title: result.success ? "Success" : "Error",
        description: result.message,
        variant: result.success ? "default" : "destructive",
      });
    } catch (error) {
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
        <h1 className="text-3xl font-bold">AI Providers Configuration</h1>
        <p className="text-muted-foreground">
          Configure and manage AI providers for text generation and embeddings
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Available Providers</CardTitle>
              <CardDescription>Select a provider to configure</CardDescription>
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
    </div>
  );
}