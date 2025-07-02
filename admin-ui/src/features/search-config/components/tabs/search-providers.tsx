'use client';

/**
 * Search Providers configuration tab
 * Configure external search providers (MCP)
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  Globe,
  PlayCircle,
  Save,
  Loader2,
  AlertCircle,
  CheckCircle,
  Info,
  Search
} from 'lucide-react';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';

interface SearchProvidersConfigProps {
  onChangeDetected?: () => void;
}

interface MCPProvider {
  id: string;
  name: string;
  enabled: boolean;
  priority: number;
  api_key?: string;
  search_engine_id?: string;
  max_requests_per_minute: number;
  timeout_seconds: number;
  status?: 'healthy' | 'unhealthy' | 'untested';
  last_error?: string;
}

export function SearchProvidersConfig({ onChangeDetected }: SearchProvidersConfigProps) {
  const [providers, setProviders] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const apiClient = useApiClient();
  const { toast } = useToast();

  useEffect(() => {
    loadProviders();
  }, []);

  const loadProviders = async () => {
    setIsLoading(true);
    try {
      const mcpProviders = await apiClient.getMCPProviders();
      if (mcpProviders?.providers) {
        const providerList = mcpProviders.providers.map((provider) => ({
          id: provider.provider_id,
          name: provider.provider_id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
          ...provider.config,
          status: provider.health.status,
          stats: provider.stats
        }));
        setProviders(providerList);
      }
    } catch (error) {
      console.error('Failed to load MCP providers:', error);
      toast({
        title: "Failed to Load Providers",
        description: "Unable to load search provider configuration",
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleProviderToggle = (providerId: string, enabled: boolean) => {
    setProviders(prev => prev.map(p => 
      p.id === providerId ? { ...p, enabled } : p
    ));
    onChangeDetected?.();
  };

  const handleProviderUpdate = (providerId: string, updates: Partial<MCPProvider>) => {
    setProviders(prev => prev.map(p => 
      p.id === providerId ? { ...p, ...updates } : p
    ));
    onChangeDetected?.();
  };

  const handleTestProvider = async (providerId: string) => {
    setTestingProvider(providerId);
    try {
      const result = await apiClient.testMCPProvider(providerId);
      
      if (result.success) {
        handleProviderUpdate(providerId, {
          status: 'healthy',
          last_error: undefined
        });
        
        toast({
          title: "Test Successful",
          description: `${providerId} is working correctly`
        });
      } else {
        handleProviderUpdate(providerId, {
          status: 'unhealthy',
          last_error: result.error_message
        });
        
        toast({
          title: "Test Failed",
          description: result.error_message || "Provider test failed",
          variant: "destructive"
        });
      }
    } catch (error: any) {
      handleProviderUpdate(providerId, {
        status: 'unhealthy',
        last_error: error.message
      });
      
      toast({
        title: "Test Failed",
        description: error.message || "Failed to test provider",
        variant: "destructive"
      });
    } finally {
      setTestingProvider(null);
    }
  };

  const handleSaveConfiguration = async () => {
    setIsSaving(true);
    try {
      const mcpConfig = {
        providers: providers.reduce((acc, provider) => {
          const { id, name, status, last_error, ...config } = provider;
          acc[id] = config;
          return acc;
        }, {} as Record<string, any>)
      };
      
      await apiClient.updateMCPConfig(mcpConfig as any);
      
      toast({
        title: "Configuration Saved",
        description: "Search provider configuration updated successfully"
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

  const getStatusBadge = (provider: MCPProvider) => {
    if (provider.status === 'healthy') {
      return <Badge className="bg-green-500">Healthy</Badge>;
    } else if (provider.status === 'unhealthy') {
      return <Badge className="bg-red-500">Error</Badge>;
    } else {
      return <Badge variant="secondary">Not Tested</Badge>;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold">External Search Providers</h2>
        <p className="text-muted-foreground mt-1">
          Configure MCP (Model Context Protocol) search providers for enhanced search capabilities
        </p>
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Search providers extend DocAIche's capabilities by searching external sources like Google, 
          Brave Search, and DuckDuckGo when local documentation doesn't have the answer.
        </AlertDescription>
      </Alert>

      <div className="space-y-4">
        {providers.map((provider) => (
          <Card key={provider.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Globe className="h-5 w-5" />
                  <div>
                    <CardTitle className="text-lg">{provider.name}</CardTitle>
                    <CardDescription>Priority: {provider.priority}</CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  {getStatusBadge(provider)}
                  <Switch
                    checked={provider.enabled}
                    onCheckedChange={(checked) => handleProviderToggle(provider.id, checked)}
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {provider.last_error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{provider.last_error}</AlertDescription>
                </Alert>
              )}

              <div className="grid grid-cols-2 gap-4">
                {provider.id !== 'duckduckgo' && (
                  <div>
                    <Label htmlFor={`${provider.id}-api-key`}>API Key</Label>
                    <Input
                      id={`${provider.id}-api-key`}
                      type="password"
                      placeholder="Enter API key"
                      value={provider.api_key || ''}
                      onChange={(e) => {
                        handleProviderUpdate(provider.id, { api_key: e.target.value });
                      }}
                    />
                  </div>
                )}

                {provider.id === 'google_search' && (
                  <div>
                    <Label htmlFor={`${provider.id}-engine-id`}>Search Engine ID</Label>
                    <Input
                      id={`${provider.id}-engine-id`}
                      placeholder="Enter search engine ID"
                      value={provider.search_engine_id || ''}
                      onChange={(e) => {
                        handleProviderUpdate(provider.id, { search_engine_id: e.target.value });
                      }}
                    />
                  </div>
                )}

                <div>
                  <Label htmlFor={`${provider.id}-rate-limit`}>Rate Limit (req/min)</Label>
                  <Input
                    id={`${provider.id}-rate-limit`}
                    type="number"
                    value={provider.max_requests_per_minute}
                    onChange={(e) => {
                      handleProviderUpdate(provider.id, { 
                        max_requests_per_minute: parseInt(e.target.value) || 60 
                      });
                    }}
                  />
                </div>

                <div>
                  <Label htmlFor={`${provider.id}-timeout`}>Timeout (seconds)</Label>
                  <Input
                    id={`${provider.id}-timeout`}
                    type="number"
                    value={provider.timeout_seconds}
                    onChange={(e) => {
                      handleProviderUpdate(provider.id, { 
                        timeout_seconds: parseFloat(e.target.value) || 3 
                      });
                    }}
                  />
                </div>

                <div>
                  <Label htmlFor={`${provider.id}-priority`}>Priority</Label>
                  <Input
                    id={`${provider.id}-priority`}
                    type="number"
                    min="1"
                    max="10"
                    value={provider.priority}
                    onChange={(e) => {
                      handleProviderUpdate(provider.id, { 
                        priority: parseInt(e.target.value) || 1 
                      });
                    }}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    Lower number = higher priority
                  </p>
                </div>
              </div>

              <div className="flex justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleTestProvider(provider.id)}
                  disabled={!provider.enabled || testingProvider === provider.id}
                >
                  {testingProvider === provider.id ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Testing...
                    </>
                  ) : (
                    <>
                      <PlayCircle className="h-4 w-4 mr-2" />
                      Test Provider
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex justify-end">
        <Button onClick={handleSaveConfiguration} disabled={isSaving}>
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
  );
}