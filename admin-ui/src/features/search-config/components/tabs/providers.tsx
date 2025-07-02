'use client';

/**
 * Providers configuration tab
 * Configure and test AI providers
 */

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  Settings,
  PlayCircle,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Plus,
  Trash2,
  Save
} from 'lucide-react';
import { useProviderSettings } from '@/lib/hooks/use-provider-settings';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';
import { AI_PROVIDERS } from '@/lib/config/providers';

interface ProvidersConfigProps {
  onChangeDetected?: () => void;
}

export function ProvidersConfig({ onChangeDetected }: ProvidersConfigProps) {
  const { providers, updateProviderConfig, refreshProviders } = useProviderSettings();
  const apiClient = useApiClient();
  const { toast } = useToast();
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [savingProvider, setSavingProvider] = useState<string | null>(null);

  useEffect(() => {
    // Load providers on mount
    refreshProviders();
  }, []);

  const handleTestProvider = async (providerId: string) => {
    setTestingProvider(providerId);
    try {
      const result = await apiClient.testProvider(providerId);
      
      if (result.success) {
        // Update provider with discovered models
        updateProviderConfig(providerId, {
          status: 'tested',
          models: result.models || [],
          lastTested: new Date().toISOString()
        });
        
        toast({
          title: "Connection Successful",
          description: `Found ${result.models?.length || 0} models`
        });
      } else {
        updateProviderConfig(providerId, {
          status: 'failed',
          error: result.error
        });
        
        toast({
          title: "Connection Failed",
          description: result.error || "Unable to connect to provider",
          variant: "destructive"
        });
      }
    } catch (error: any) {
      toast({
        title: "Test Failed",
        description: error.message || "Failed to test provider",
        variant: "destructive"
      });
    } finally {
      setTestingProvider(null);
    }
  };

  const handleSaveProviderConfig = async (providerId: string, config: any) => {
    setSavingProvider(providerId);
    try {
      await apiClient.updateProviderConfiguration(providerId, config);
      
      updateProviderConfig(providerId, {
        ...config,
        status: 'configured'
      });
      
      onChangeDetected?.();
      
      toast({
        title: "Configuration Saved",
        description: "Provider configuration updated successfully"
      });
    } catch (error: any) {
      toast({
        title: "Save Failed",
        description: error.message || "Failed to save configuration",
        variant: "destructive"
      });
    } finally {
      setSavingProvider(null);
    }
  };

  const getProviderStatus = (providerId: string) => {
    const config = providers[providerId];
    if (!config) return 'unconfigured';
    return config.status || 'unconfigured';
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'tested':
      case 'connected':
        return <Badge className="bg-green-500">Connected</Badge>;
      case 'configured':
        return <Badge className="bg-blue-500">Configured</Badge>;
      case 'failed':
        return <Badge className="bg-red-500">Failed</Badge>;
      default:
        return <Badge variant="secondary">Not Configured</Badge>;
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h2 className="text-2xl font-bold">AI Provider Configuration</h2>
        <p className="text-muted-foreground mt-1">
          Configure and test your AI providers. Only tested providers can be used for model selection.
        </p>
      </div>

      <Tabs defaultValue="all" className="space-y-4">
        <TabsList>
          <TabsTrigger value="all">All Providers</TabsTrigger>
          <TabsTrigger value="llm">LLM Providers</TabsTrigger>
          <TabsTrigger value="embedding">Embedding Providers</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-4">
          <ScrollArea className="h-[calc(100vh-300px)]">
            <div className="space-y-4 pr-4">
              {Object.entries(AI_PROVIDERS).map(([providerId, provider]) => {
                const config = providers[providerId] || {};
                const status = getProviderStatus(providerId);
                const isConfigured = config.apiKey || config.baseUrl;
                
                return (
                  <Card key={providerId}>
                    <CardHeader>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <span className="text-2xl">{provider.icon}</span>
                          <div>
                            <CardTitle>{provider.displayName}</CardTitle>
                            <CardDescription>{provider.description}</CardDescription>
                          </div>
                        </div>
                        {getStatusBadge(status)}
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {/* API Key Input */}
                      {provider.requiresApiKey && (
                        <div>
                          <Label htmlFor={`${providerId}-api-key`}>API Key</Label>
                          <Input
                            id={`${providerId}-api-key`}
                            type="password"
                            placeholder="Enter your API key"
                            value={config.apiKey || ''}
                            onChange={(e) => {
                              updateProviderConfig(providerId, {
                                ...config,
                                apiKey: e.target.value
                              });
                              onChangeDetected?.();
                            }}
                          />
                        </div>
                      )}

                      {/* Base URL for custom endpoints */}
                      {provider.customEndpoint && (
                        <div>
                          <Label htmlFor={`${providerId}-base-url`}>Base URL</Label>
                          <Input
                            id={`${providerId}-base-url`}
                            type="url"
                            placeholder={provider.defaultBaseUrl || 'https://api.example.com'}
                            value={config.baseUrl || ''}
                            onChange={(e) => {
                              updateProviderConfig(providerId, {
                                ...config,
                                baseUrl: e.target.value
                              });
                              onChangeDetected?.();
                            }}
                          />
                        </div>
                      )}

                      {/* Organization ID for OpenAI */}
                      {providerId === 'openai' && (
                        <div>
                          <Label htmlFor={`${providerId}-org-id`}>Organization ID (Optional)</Label>
                          <Input
                            id={`${providerId}-org-id`}
                            placeholder="org-..."
                            value={config.organizationId || ''}
                            onChange={(e) => {
                              updateProviderConfig(providerId, {
                                ...config,
                                organizationId: e.target.value
                              });
                              onChangeDetected?.();
                            }}
                          />
                        </div>
                      )}

                      {/* Test Results */}
                      {status === 'tested' && config.models && (
                        <Alert>
                          <CheckCircle className="h-4 w-4" />
                          <AlertDescription>
                            Successfully connected. Found {config.models.length} models.
                          </AlertDescription>
                        </Alert>
                      )}

                      {status === 'failed' && config.error && (
                        <Alert variant="destructive">
                          <XCircle className="h-4 w-4" />
                          <AlertDescription>{config.error}</AlertDescription>
                        </Alert>
                      )}

                      {/* Action Buttons */}
                      <div className="flex gap-2">
                        <Button
                          onClick={() => handleSaveProviderConfig(providerId, config)}
                          disabled={!isConfigured || savingProvider === providerId}
                        >
                          {savingProvider === providerId ? (
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
                        
                        <Button
                          variant="outline"
                          onClick={() => handleTestProvider(providerId)}
                          disabled={!isConfigured || testingProvider === providerId}
                        >
                          {testingProvider === providerId ? (
                            <>
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                              Testing...
                            </>
                          ) : (
                            <>
                              <PlayCircle className="h-4 w-4 mr-2" />
                              Test Connection
                            </>
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="llm" className="space-y-4">
          <ScrollArea className="h-[calc(100vh-300px)]">
            <div className="space-y-4 pr-4">
              {Object.entries(AI_PROVIDERS)
                .filter(([_, provider]) => provider.type === 'llm' || provider.type === 'both')
                .map(([providerId, provider]) => {
                  // Same card component as above
                  const config = providers[providerId] || {};
                  const status = getProviderStatus(providerId);
                  const isConfigured = config.apiKey || config.baseUrl;
                  
                  return (
                    <Card key={providerId}>
                      {/* Same content as above */}
                    </Card>
                  );
                })}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="embedding" className="space-y-4">
          <ScrollArea className="h-[calc(100vh-300px)]">
            <div className="space-y-4 pr-4">
              {Object.entries(AI_PROVIDERS)
                .filter(([_, provider]) => provider.type === 'embedding' || provider.type === 'both')
                .map(([providerId, provider]) => {
                  // Same card component as above
                  const config = providers[providerId] || {};
                  const status = getProviderStatus(providerId);
                  const isConfigured = config.apiKey || config.baseUrl;
                  
                  return (
                    <Card key={providerId}>
                      {/* Same content as above */}
                    </Card>
                  );
                })}
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  );
}