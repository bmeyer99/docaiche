'use client';

import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Icons } from '@/components/icons';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AI_PROVIDERS, ProviderDefinition } from '@/lib/config/providers';
import { useToast } from '@/hooks/use-toast';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useProviderTestCache } from '@/lib/hooks/use-provider-test-cache';
import { useProviderSettings } from '@/lib/hooks/use-provider-settings';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckCircle2, Activity } from 'lucide-react';

interface ProviderFormProps {
  provider: ProviderDefinition & { id: string };
}

// Save Provider Configuration Button Component
function SaveProviderConfigButton({ providerId, providerName }: { providerId: string; providerName: string }) {
  const [isSaving, setIsSaving] = useState(false);
  const { toast } = useToast();
  const apiClient = useApiClient();
  const { providers } = useProviderSettings();

  const handleSaveConfig = async () => {
    setIsSaving(true);
    try {
      const providerConfig = providers[providerId];
      if (!providerConfig?.config) {
        throw new Error('No configuration to save');
      }

      // Save configuration (without enabled field since we removed it)
      await apiClient.updateProviderConfiguration(providerId, { config: providerConfig.config });
      toast({
        title: "Configuration Saved",
        description: `${providerName} configuration has been saved successfully.`,
      });
    } catch (error: any) {
      toast({
        title: "Save Failed",
        description: error.message || "Failed to save provider configuration. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const providerConfig = providers[providerId];
  const hasConfig = providerConfig?.config && Object.keys(providerConfig.config).length > 0;

  return (
    <Button
      onClick={handleSaveConfig}
      disabled={isSaving || !hasConfig}
      className="flex items-center gap-2"
    >
      {isSaving ? (
        <>
          <Icons.spinner className="w-4 h-4 animate-spin" />
          Saving...
        </>
      ) : (
        <>
          <Icons.check className="w-4 h-4" />
          Save Configuration
        </>
      )}
    </Button>
  );
}

function ProviderForm({ provider }: ProviderFormProps) {
  const { toast } = useToast();
  const apiClient = useApiClient();
  const testCache = useProviderTestCache();
  const { providers, updateProvider } = useProviderSettings();
  const [isTesting, setIsTesting] = useState(false);

  const providerConfig = providers[provider.id];
  const testStatus = testCache.getProviderStatus(provider.id);
  const testModels = testCache.getProviderModels(provider.id);

  // Debug logging
  console.log(`ProviderForm ${provider.id} - Config:`, providerConfig);
  console.log(`ProviderForm ${provider.id} - Test Status:`, testStatus);
  console.log(`ProviderForm ${provider.id} - Models:`, testModels);

  const handleFieldChange = (fieldKey: string, value: string | number | boolean) => {
    updateProvider(provider.id, {
      [fieldKey]: value
    });
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    const config = providerConfig?.config || {};
    testCache.setProviderTesting(provider.id, config);

    try {
      const response = await apiClient.testProviderConnection(provider.id, config);
      
      if (response.success) {
        const models = response.models || [];
        testCache.setProviderTested(provider.id, models, config);
        
        toast({
          title: "Connection Successful",
          description: `${provider.displayName} connected successfully. Found ${models.length} models.`,
        });
      } else {
        testCache.setProviderFailed(provider.id, response.message, config);
        toast({
          title: "Connection Failed", 
          description: response.message || "Failed to connect to provider",
          variant: "destructive"
        });
      }
    } catch (error: any) {
      testCache.setProviderFailed(provider.id, error.message, config);
      toast({
        title: "Connection Error",
        description: error.message || "Failed to test provider connection",
        variant: "destructive"
      });
    } finally {
      setIsTesting(false);
    }
  };

  const getStatusBadge = () => {
    if (isTesting || testStatus === 'testing') {
      return <Badge variant="outline" className="border-blue-500 text-blue-600">Testing...</Badge>;
    }
    if (testStatus === 'tested') {
      return <Badge variant="outline" className="border-green-500 text-green-600">Connected ({testModels.length} models)</Badge>;
    }
    if (testStatus === 'failed') {
      return <Badge variant="outline" className="border-red-500 text-red-600">Failed</Badge>;
    }
    return <Badge variant="outline" className="border-amber-500 text-amber-600">Not Tested</Badge>;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <div 
            className="w-10 h-10 rounded-lg flex items-center justify-center text-lg"
            style={{ backgroundColor: provider.color + '20', color: provider.color }}
          >
            {provider.icon}
          </div>
          <div>
            <CardTitle className="flex items-center gap-2">
              {provider.displayName}
              {getStatusBadge()}
            </CardTitle>
            <CardDescription>{provider.description}</CardDescription>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Configuration Fields */}
        <div className="grid gap-4">
          {provider.configFields?.map((field) => {
            const fieldValue = providerConfig?.config?.[field.key] || 
              (field.key === 'base_url' ? provider.defaultBaseUrl : '');

            return (
              <div key={field.key} className="grid gap-2">
                <Label htmlFor={`${provider.id}-${field.key}`}>
                  {field.label}
                  {field.required && <span className="text-red-500 ml-1">*</span>}
                </Label>
                
                {field.type === 'textarea' ? (
                  <Textarea
                    id={`${provider.id}-${field.key}`}
                    value={String(fieldValue || '')}
                    onChange={(e) => handleFieldChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    className="min-h-[100px]"
                  />
                ) : field.type === 'number' ? (
                  <Input
                    id={`${provider.id}-${field.key}`}
                    type="number"
                    value={String(fieldValue || '')}
                    onChange={(e) => handleFieldChange(field.key, parseInt(e.target.value) || 0)}
                    placeholder={field.placeholder}
                    min={field.validation?.min}
                    max={field.validation?.max}
                  />
                ) : (
                  <Input
                    id={`${provider.id}-${field.key}`}
                    type={field.type === 'password' ? 'password' : 'text'}
                    value={String(fieldValue || '')}
                    onChange={(e) => handleFieldChange(field.key, e.target.value)}
                    placeholder={field.placeholder}
                    className={field.type === 'password' ? 'font-mono' : ''}
                  />
                )}
                
                {field.description && (
                  <p className="text-xs text-muted-foreground">{field.description}</p>
                )}
              </div>
            );
          })}
        </div>

        {/* Status Alerts */}
        {testStatus === 'failed' && (
          <Alert className="border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950">
            <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400" />
            <AlertDescription className="text-red-800 dark:text-red-200">
              Connection test failed. Please check your configuration and try again.
            </AlertDescription>
          </Alert>
        )}

        {testStatus === 'tested' && (
          <Alert className="border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950">
            <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400" />
            <AlertDescription className="text-green-800 dark:text-green-200">
              <strong>Connected successfully!</strong> Found {testModels.length} available models.
              {testModels.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {testModels.slice(0, 5).map(model => (
                    <Badge key={model} variant="outline" className="text-xs">
                      {model}
                    </Badge>
                  ))}
                  {testModels.length > 5 && (
                    <Badge variant="outline" className="text-xs">
                      +{testModels.length - 5} more
                    </Badge>
                  )}
                </div>
              )}
            </AlertDescription>
          </Alert>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2">
          <Button
            onClick={handleTestConnection}
            disabled={isTesting}
            variant="outline"
            className="flex items-center gap-2"
          >
            {isTesting ? (
              <Icons.spinner className="w-4 h-4 animate-spin" />
            ) : (
              <Activity className="w-4 h-4" />
            )}
            {isTesting ? 'Testing...' : 'Test Connection'}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export default function ProviderConfigurationSection() {
  const [activeProvider, setActiveProvider] = useState('ollama');

  // Group providers by category
  const providersByCategory = Object.entries(AI_PROVIDERS).reduce((acc, [id, provider]) => {
    const providerWithId = { ...provider, id };
    if (!acc[provider.category]) acc[provider.category] = [];
    acc[provider.category].push(providerWithId);
    return acc;
  }, {} as Record<string, Array<ProviderDefinition & { id: string }>>);

  const providerCategories = {
    'local': 'Local',
    'cloud': 'Cloud', 
    'enterprise': 'Enterprise'
  };

  const activeProviderData = Object.values(AI_PROVIDERS).find(p => p.id === activeProvider);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Provider Configuration</CardTitle>
        <CardDescription>
          Configure and test your AI providers. Test connections to discover available models.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Provider Selection Sidebar */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>Available Providers</CardTitle>
                <CardDescription>Select a provider to configure</CardDescription>
              </CardHeader>
              <CardContent className="p-0">
                <Tabs defaultValue="local" className="w-full">
                  <TabsList className="grid w-full grid-cols-3">
                    {Object.entries(providerCategories).map(([key, label]) => (
                      <TabsTrigger key={key} value={key}>{label}</TabsTrigger>
                    ))}
                  </TabsList>
                  {Object.entries(providersByCategory).map(([category, categoryProviders]) => (
                    <TabsContent key={category} value={category} className="space-y-2 p-4">
                      {categoryProviders.map(provider => (
                        <div
                          key={provider.id}
                          className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                            activeProvider === provider.id 
                              ? 'bg-primary text-primary-foreground border-primary shadow-sm' 
                              : 'hover:bg-secondary hover:text-secondary-foreground hover:border-secondary'
                          }`}
                          onClick={() => setActiveProvider(provider.id)}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <div 
                                className="w-3 h-3 rounded" 
                                style={{ backgroundColor: provider.color || '#6b7280' }}
                              />
                              <span className="font-medium">{provider.displayName}</span>
                            </div>
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

          {/* Provider Configuration Form */}
          <div className="lg:col-span-2">
            <Card>
              <CardContent className="p-6">
                {activeProviderData ? (
                  <ProviderForm provider={{ ...activeProviderData, id: activeProvider }} />
                ) : (
                  <div className="text-center py-12 text-muted-foreground">
                    Select a provider to configure
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}