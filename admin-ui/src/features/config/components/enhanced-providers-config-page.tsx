'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Checkbox } from '@/components/ui/checkbox';
import { Icons } from '@/components/icons';
import { AI_PROVIDERS, ProviderDefinition, ProviderConfiguration } from '@/lib/config/providers';
import { DocaicheApiClient } from '@/lib/utils/api-client';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/lib/utils';

interface ProviderStatus {
  id: string;
  status: 'healthy' | 'degraded' | 'unhealthy' | 'testing' | 'unknown';
  lastChecked?: string;
  responseTime?: number;
  errorMessage?: string;
}

export default function EnhancedProvidersConfigPage() {
  const [configurations, setConfigurations] = useState<Record<string, ProviderConfiguration>>({});
  const [providerStatuses, setProviderStatuses] = useState<Record<string, ProviderStatus>>({});
  const [selectedProviders, setSelectedProviders] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [activeProvider, setActiveProvider] = useState('ollama');
  const [batchOperation, setBatchOperation] = useState<'test' | 'enable' | 'disable' | null>(null);
  const { toast } = useToast();
  const apiClient = new DocaicheApiClient();

  const loadProviderConfigurations = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiClient.getProviderConfigurations();
      const configRecord = Array.isArray(data) 
        ? data.reduce((acc, provider) => {
            acc[provider.id] = {
              id: provider.id,
              providerId: provider.providerId || provider.id,
              name: provider.name,
              enabled: provider.enabled || false,
              config: provider.config || {},
              status: provider.status || 'disconnected'
            };
            return acc;
          }, {} as Record<string, any>)
        : data || {};
      setConfigurations(configRecord);
      
      // Initialize provider statuses
      const statusRecord: Record<string, ProviderStatus> = {};
      Object.keys(AI_PROVIDERS).forEach(providerId => {
        statusRecord[providerId] = {
          id: providerId,
          status: configRecord[providerId]?.enabled ? 'unknown' : 'unhealthy',
          lastChecked: undefined
        };
      });
      setProviderStatuses(statusRecord);
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

  const testProviderConnection = async (providerId: string) => {
    setProviderStatuses(prev => ({
      ...prev,
      [providerId]: { ...prev[providerId], status: 'testing' }
    }));

    try {
      const providerConfig = configurations[providerId];
      if (!providerConfig) {
        throw new Error('Provider configuration not found');
      }
      
      const startTime = Date.now();
      const result = await apiClient.testProviderConnection(providerId, {
        base_url: providerConfig.config?.base_url || "",
        api_key: providerConfig.config?.api_key || "",
        model: providerConfig.config?.model || ""
      });
      const responseTime = Date.now() - startTime;

      setProviderStatuses(prev => ({
        ...prev,
        [providerId]: {
          ...prev[providerId],
          status: result.success ? 'healthy' : 'degraded',
          lastChecked: new Date().toISOString(),
          responseTime,
          errorMessage: result.success ? undefined : result.message
        }
      }));

      toast({
        title: result.success ? "Success" : "Warning",
        description: result.message,
        variant: result.success ? "default" : "destructive",
      });
    } catch (error) {
      setProviderStatuses(prev => ({
        ...prev,
        [providerId]: {
          ...prev[providerId],
          status: 'unhealthy',
          lastChecked: new Date().toISOString(),
          errorMessage: error instanceof Error ? error.message : 'Unknown error'
        }
      }));

      toast({
        title: "Error",
        description: "Failed to test connection",
        variant: "destructive",
      });
    }
  };

  const testAllProviders = async () => {
    setTesting(true);
    setBatchOperation('test');
    
    const configuredProviders = Object.keys(configurations).filter(
      id => configurations[id]?.enabled
    );
    
    for (const providerId of configuredProviders) {
      await testProviderConnection(providerId);
      // Small delay between tests to avoid overwhelming the API
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    setTesting(false);
    setBatchOperation(null);
    toast({
      title: "Batch Test Complete",
      description: `Tested ${configuredProviders.length} configured providers`,
    });
  };

  const handleBatchOperation = async (operation: 'enable' | 'disable') => {
    if (selectedProviders.size === 0) {
      toast({
        title: "No Providers Selected",
        description: "Please select providers to perform batch operation",
        variant: "destructive",
      });
      return;
    }

    setBatchOperation(operation);
    const selectedArray = Array.from(selectedProviders);
    
    for (const providerId of selectedArray) {
      try {
        const config = configurations[providerId] || {};
        await saveConfiguration(providerId, { ...config, enabled: operation === 'enable' });
      } catch (error) {
        // Silently continue with other providers
      }
    }
    
    setBatchOperation(null);
    setSelectedProviders(new Set());
    toast({
      title: "Batch Operation Complete",
      description: `${operation === 'enable' ? 'Enabled' : 'Disabled'} ${selectedArray.length} providers`,
    });
  };

  const saveConfiguration = async (providerId: string, config: Partial<ProviderConfiguration>) => {
    setLoading(true);
    try {
      const updatedConfig = { ...configurations[providerId], ...config };
      await apiClient.updateProviderConfiguration(providerId, updatedConfig);
      setConfigurations(prev => ({ ...prev, [providerId]: updatedConfig }));
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save configuration",
        variant: "destructive",
      });
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: ProviderStatus['status']) => {
    switch (status) {
      case 'healthy': return 'text-green-500';
      case 'degraded': return 'text-yellow-500';
      case 'unhealthy': return 'text-red-500';
      case 'testing': return 'text-blue-500';
      default: return 'text-gray-500';
    }
  };

  const getStatusIcon = (status: ProviderStatus['status']) => {
    switch (status) {
      case 'healthy': return <Icons.checkCircle className="w-4 h-4" />;
      case 'degraded': return <Icons.warning className="w-4 h-4" />;
      case 'unhealthy': return <Icons.alertCircle className="w-4 h-4" />;
      case 'testing': return <Icons.spinner className="w-4 h-4 animate-spin" />;
      default: return <Icons.circle className="w-4 h-4" />;
    }
  };

  const getProvidersByCategory = () => {
    return Object.entries(AI_PROVIDERS).reduce((acc, [, provider]) => {
      if (!acc[provider.category]) acc[provider.category] = [];
      acc[provider.category].push(provider);
      return acc;
    }, {} as Record<string, Array<ProviderDefinition>>);
  };

  const renderProviderCard = (provider: ProviderDefinition & { id: string }) => {
    const config = configurations[provider.id] || {};
    const status = providerStatuses[provider.id];
    const isSelected = selectedProviders.has(provider.id);
    
    return (
      <div
        key={provider.id}
        className={cn(
          "p-4 rounded-lg border transition-all duration-200 hover:shadow-md",
          activeProvider === provider.id 
            ? 'bg-accent border-accent-foreground shadow-sm' 
            : 'hover:bg-accent/50',
          isSelected && 'ring-2 ring-primary'
        )}
      >
        <div className="flex items-start justify-between">
          <div 
            className="flex items-center gap-3 cursor-pointer flex-1"
            onClick={() => setActiveProvider(provider.id)}
          >
            <div className="flex flex-col items-center gap-1">
              <div 
                className="w-8 h-8 rounded-lg flex items-center justify-center text-lg"
                style={{ backgroundColor: `${provider.color}20`, color: provider.color }}
              >
                {provider.icon}
              </div>
              <div className={cn("text-xs", getStatusColor(status?.status || 'unknown'))}>
                {getStatusIcon(status?.status || 'unknown')}
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{provider.displayName}</span>
                {config.enabled && (
                  <Badge variant="secondary" className="text-xs">
                    Enabled
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                {provider.description}
              </p>
              {status?.responseTime && (
                <p className="text-xs text-muted-foreground mt-1">
                  Response: {status.responseTime}ms
                </p>
              )}
            </div>
          </div>
          <Checkbox
            checked={isSelected}
            onCheckedChange={(checked) => {
              const newSelected = new Set(selectedProviders);
              if (checked) {
                newSelected.add(provider.id);
              } else {
                newSelected.delete(provider.id);
              }
              setSelectedProviders(newSelected);
            }}
            className="ml-2"
          />
        </div>
      </div>
    );
  };

  const renderConfigurationForm = (provider: ProviderDefinition & { id: string }) => {
    const config = configurations[provider.id] || {};

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium flex items-center gap-2">
              <span 
                className="w-6 h-6 rounded flex items-center justify-center text-sm"
                style={{ backgroundColor: `${provider.color}20`, color: provider.color }}
              >
                {provider.icon}
              </span>
              {provider.displayName} Configuration
            </h3>
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
              value={config.config?.base_url || provider.defaultBaseUrl || ''}
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
                value={config.config?.api_key || ''}
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
              {field.type === 'textarea' ? (
                <Textarea
                  id={field.key}
                  value={config.config?.[field.key] || ''}
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
                  value={config.config?.[field.key] || ''}
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
                  value={config.config?.[field.key] || ''}
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
            onClick={() => testProviderConnection(provider.id)}
            disabled={testing || !config.enabled}
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
      {/* Header with enhanced styling */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">AI Providers Configuration</h1>
          <p className="text-muted-foreground">
            Configure and manage AI providers for text generation and embeddings
          </p>
        </div>
        <div className="flex items-center gap-2">
          {selectedProviders.size > 0 && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleBatchOperation('enable')}
                disabled={batchOperation !== null}
              >
                Enable Selected ({selectedProviders.size})
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleBatchOperation('disable')}
                disabled={batchOperation !== null}
              >
                Disable Selected ({selectedProviders.size})
              </Button>
            </>
          )}
          <Button
            onClick={testAllProviders}
            disabled={testing}
            size="sm"
          >
            {testing ? (
              <>
                <Icons.spinner className="w-4 h-4 mr-2 animate-spin" />
                Testing...
              </>
            ) : (
              <>
                <Icons.activity className="w-4 h-4 mr-2" />
                Test All
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Batch operation progress */}
      {batchOperation && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <Icons.spinner className="w-4 h-4 animate-spin" />
              <span className="text-sm">
                {batchOperation === 'test' && 'Testing all configured providers...'}
                {batchOperation === 'enable' && 'Enabling selected providers...'}
                {batchOperation === 'disable' && 'Disabling selected providers...'}
              </span>
            </div>
          </CardContent>
        </Card>
      )}

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
                  <TabsTrigger value="enterprise">Enterprise</TabsTrigger>
                </TabsList>
                {Object.entries(providersByCategory).map(([category, providers]) => (
                  <TabsContent key={category} value={category} className="space-y-3 p-4">
                    {providers.map(provider => renderProviderCard(provider))}
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