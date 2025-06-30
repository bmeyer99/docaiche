'use client';

import React, { useState, useEffect, useMemo, useCallback, Suspense } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';
import { Icons } from '@/components/icons';
import { AI_PROVIDERS, ProviderDefinition } from '@/lib/config/providers';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';
import { ProviderTestProvider, useProviderTestCache } from '@/lib/hooks/use-provider-test-cache';
import { 
  OptimizedProviderSettingsProvider, 
  useProviderData,
  useProviderActions,
  useProviderState,
  useProviderUtilities,
  useProvidersByCategory
} from '@/lib/hooks/provider-settings/context-optimized';
import { 
  OptimizedProviderForm,
  OptimizedProviderList
} from '@/components/optimized/provider-form-optimized';
import { 
  useStableMemo,
  useStableCallback,
  useStableHandlers,
  usePerformanceMonitor,
  shallowEqual,
  createLazyComponent
} from '@/lib/utils/performance-helpers';

// Lazy load the model selection component for better initial load performance
const ModelSelectionRedesigned = createLazyComponent(
  () => import('./model-selection-redesigned'),
  () => <div className="animate-pulse bg-muted h-32 rounded-lg" />
);

// ========================== OPTIMIZED COMPONENTS ==========================

const OptimizedRefreshButton = React.memo<{
  onRefresh: () => void;
  isLoading: boolean;
}>(({ onRefresh, isLoading }) => (
  <Button
    variant="outline"
    size="sm"
    onClick={onRefresh}
    disabled={isLoading}
    className="flex items-center gap-2"
  >
    {isLoading ? (
      <Icons.spinner className="w-4 h-4 animate-spin" />
    ) : (
      <Icons.refresh className="w-4 h-4" />
    )}
    Refresh
  </Button>
), shallowEqual);

OptimizedRefreshButton.displayName = 'OptimizedRefreshButton';

const OptimizedSaveButton = React.memo<{
  onSave: () => void;
  isSaving: boolean;
  hasChanges: boolean;
}>(({ onSave, isSaving, hasChanges }) => {
  if (!hasChanges) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <div className="bg-background border rounded-lg shadow-lg p-4 flex items-center gap-4">
        <div className="text-sm text-muted-foreground">
          You have unsaved changes
        </div>
        <Button
          onClick={onSave}
          disabled={isSaving}
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
              Save All Changes
            </>
          )}
        </Button>
      </div>
    </div>
  );
}, shallowEqual);

OptimizedSaveButton.displayName = 'OptimizedSaveButton';

const OptimizedErrorDisplay = React.memo<{
  error: string | null;
  onRetry: () => void;
  isLoading: boolean;
}>(({ error, onRetry, isLoading }) => {
  if (!error) return null;

  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icons.alertCircle className="w-5 h-5 text-yellow-600" />
          <div>
            <div className="font-medium text-yellow-800">Connection Issue</div>
            <div className="text-sm text-yellow-600">
              {error}. You can still configure providers manually.
            </div>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onRetry}
          disabled={isLoading}
          className="ml-4"
        >
          {isLoading ? (
            <Icons.spinner className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <Icons.refresh className="w-4 h-4 mr-1" />
              Retry
            </>
          )}
        </Button>
      </div>
    </div>
  );
}, shallowEqual);

OptimizedErrorDisplay.displayName = 'OptimizedErrorDisplay';

// ========================== MAIN CONTENT COMPONENT ==========================

function ProvidersConfigPageContent() {
  usePerformanceMonitor('ProvidersConfigPageContent');

  const [activeProvider, setActiveProvider] = useState('ollama');
  const { toast } = useToast();
  const apiClient = useApiClient();
  const testCache = useProviderTestCache();
  
  // Use optimized context hooks
  const { providers } = useProviderData();
  const { loadSettings, updateProvider, saveAllChanges } = useProviderActions();
  const { isLoading, isSaving, loadError } = useProviderState();
  const { hasUnsavedChanges } = useProviderUtilities();

  // Load settings on mount
  useEffect(() => {
    loadSettings();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Stable event handlers
  const handleRefresh = useStableCallback(() => {
    loadSettings();
  }, [loadSettings]);

  const handleSaveAllChanges = useStableCallback(async () => {
    try {
      await saveAllChanges();
      toast({
        title: "Settings Saved",
        description: "All configuration changes have been saved successfully.",
      });
    } catch (error) {
      toast({
        title: "Save Failed",
        description: "Failed to save configuration changes. Please try again.",
        variant: "destructive",
      });
    }
  }, [saveAllChanges, toast]);



  const testConnection = useStableCallback(async (providerId: string) => {
    try {
      const providerConfig = providers[providerId];
      if (!providerConfig) {
        toast({
          title: "Error",
          description: "Provider configuration not found",
          variant: "destructive",
        });
        return;
      }
      
      const testConfig = {
        base_url: providerConfig.config?.base_url ? String(providerConfig.config.base_url) : '',
        api_key: providerConfig.config?.api_key ? String(providerConfig.config.api_key) : '',
        ...providerConfig.config
      };
      
      testCache.setProviderTesting(providerId, testConfig);
      
      const testParams: Record<string, string> = {};
      if (testConfig.base_url) {
        testParams.base_url = testConfig.base_url;
      }
      if (testConfig.api_key) {
        testParams.api_key = testConfig.api_key;
      }
      
      const result = await apiClient.testProviderConnection(providerId, testParams);
      
      if (result.success) {
        testCache.setProviderTested(providerId, result.models || [], testConfig);
        
        let message = result.message;
        if (result.models && result.models.length > 0) {
          message = `${result.message} Found ${result.models.length} models.`;
        }
        
        toast({
          title: "Success",
          description: message,
        });
      } else {
        testCache.setProviderFailed(providerId, result.message || 'Connection test failed', testConfig);
        
        toast({
          title: "Test Failed",
          description: result.message,
          variant: "destructive",
        });
      }
    } catch (error: any) {
      const providerConfig = providers[providerId];
      const testConfig = {
        base_url: providerConfig?.config?.base_url ? String(providerConfig.config.base_url) : '',
        api_key: providerConfig?.config?.api_key ? String(providerConfig.config.api_key) : '',
        ...providerConfig?.config
      };
      
      testCache.setProviderFailed(providerId, error.message || 'Connection test failed', testConfig);
      
      toast({
        title: "Error",
        description: "Failed to test connection",
        variant: "destructive",
      });
    }
  }, [providers, testCache, apiClient, toast]);

  // Memoized provider data processing
  const providersByCategory = useStableMemo(() => {
    return Object.entries(AI_PROVIDERS).reduce((acc, [, provider]) => {
      if (!acc[provider.category]) acc[provider.category] = [];
      acc[provider.category].push(provider);
      return acc;
    }, {} as Record<string, Array<ProviderDefinition>>);
  }, []);

  const providerCategories = useStableMemo(() => ({
    'local': 'Local',
    'cloud': 'Cloud', 
    'enterprise': 'Enterprise'
  }), []);

  // Stable provider selection handler
  const handleProviderSelect = useStableCallback((providerId: string) => {
    setActiveProvider(providerId);
  }, []);

  // Memoized active provider data
  const activeProviderData = useStableMemo(() => {
    return AI_PROVIDERS[activeProvider];
  }, [activeProvider]);

  // Memoized provider config
  const activeProviderConfig = useStableMemo(() => {
    return providers[activeProvider] || {};
  }, [providers, activeProvider]);

  const renderConfigurationForm = (provider: ProviderDefinition & { id: string }) => {
    const config = providers[provider.id] || {};

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-medium">{provider.displayName} Configuration</h3>
            <p className="text-sm text-muted-foreground">{provider.description}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Enable Provider</span>
            <Switch
              checked={config.enabled || false}
              onCheckedChange={(enabled) => {
                updateProvider(provider.id, { enabled });
              }}
            />
          </div>
        </div>

        <Separator />

        <div className="grid gap-4">
          {/* Render all config fields */}
          {provider.configFields?.map((field) => (
            <div key={field.key} className="grid gap-2">
              <Label htmlFor={`${provider.id}-${field.key}`}>
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </Label>
              <div className="relative">
                {field.type === 'textarea' ? (
                  <Textarea
                    id={`${provider.id}-${field.key}`}
                    value={String(config.config?.[field.key] || field.key === 'base_url' ? provider.defaultBaseUrl || '' : '')}
                    onChange={(e) => updateFieldValue(provider.id, field.key, e.target.value)}
                    placeholder={field.placeholder}
                  />
                ) : field.type === 'number' ? (
                  <Input
                    id={`${provider.id}-${field.key}`}
                    type="number"
                    value={String(config.config?.[field.key] || '')}
                    onChange={(e) => updateFieldValue(provider.id, field.key, parseInt(e.target.value) || 0)}
                    placeholder={field.placeholder}
                    min={field.validation?.min}
                    max={field.validation?.max}
                  />
                ) : (
                  <Input
                    id={`${provider.id}-${field.key}`}
                    type={field.type === 'password' ? 'password' : 'text'}
                    value={String(config.config?.[field.key] || (field.key === 'base_url' ? provider.defaultBaseUrl || '' : ''))}
                    onChange={(e) => updateFieldValue(provider.id, field.key, e.target.value)}
                    placeholder={field.placeholder}
                  />
                )}
              </div>
              {field.description && (
                <p className="text-xs text-muted-foreground">{field.description}</p>
              )}
              {/* Add helpful links for API key fields */}
              {field.key === 'api_key' && (
                <p className="text-xs text-muted-foreground">
                  {provider.id === 'openai' && 'Get your API key from platform.openai.com'}
                  {provider.id === 'anthropic' && 'Get your API key from console.anthropic.com'}
                  {provider.id === 'groq' && 'Get your API key from console.groq.com'}
                  {provider.id === 'openrouter' && 'Get your API key from openrouter.ai'}
                  {provider.id === 'mistral' && 'Get your API key from console.mistral.ai'}
                </p>
              )}
            </div>
          ))}
        </div>

        <div className="flex gap-2">
          <button 
            type="button"
            onClick={() => testConnection(provider.id)}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Icons.activity className="w-4 h-4 mr-2" />
            Test Connection
          </button>
        </div>
      </div>
    );
  };

  const providersByCategory = getProvidersByCategory();
  const activeProviderData = AI_PROVIDERS[activeProvider];

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">AI Model Configuration</h1>
          <p className="text-muted-foreground">
            Select your AI models for text generation and embeddings, then configure individual providers as needed
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          className="inline-flex items-center px-3 py-1.5 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50"
        >
          {loading ? (
            <Icons.spinner className="w-4 h-4 animate-spin" />
          ) : (
            <>
              <Icons.refresh className="w-4 h-4 mr-1" />
              Refresh
            </>
          )}
        </button>
      </div>

      {/* Model Selection Interface */}
      <ModelSelectionRedesigned />

      {/* Save All Changes Button */}
      {hasUnsavedChanges() && (
        <div className="fixed bottom-6 right-6 z-50">
          <div className="bg-background border rounded-lg shadow-lg p-4 flex items-center gap-4">
            <div className="text-sm text-muted-foreground">
              You have unsaved changes
            </div>
            <button
              onClick={handleSaveAllChanges}
              disabled={saving}
              className="inline-flex items-center px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2 disabled:opacity-50"
            >
              {saving ? (
                <>
                  <Icons.spinner className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Icons.check className="w-4 h-4 mr-2" />
                  Save All Changes
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Icons.alertCircle className="w-5 h-5 text-yellow-600" />
              <div>
                <div className="font-medium text-yellow-800">Connection Issue</div>
                <div className="text-sm text-yellow-600">
                  {error}. You can still configure providers manually.
                </div>
              </div>
            </div>
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="inline-flex items-center px-3 py-1.5 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 ml-4"
            >
              {loading ? (
                <Icons.spinner className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <Icons.refresh className="w-4 h-4 mr-1" />
                  Retry
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Individual Provider Configuration Section */}
      <div className="flex items-center gap-3" data-provider-config>
        <Separator className="flex-1" />
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Icons.settings className="w-4 h-4" />
          <span>Individual Provider Configuration</span>
        </div>
        <Separator className="flex-1" />
      </div>

      {/* Main Configuration Interface */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
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
                    {categoryProviders.map(provider => {
                      const config = providers[provider.id];
                      const isConfigured = config?.enabled || Object.keys(config?.config || {}).length > 0;
                      
                      return (
                        <div
                          key={provider.id}
                          className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                            activeProvider === provider.id 
                              ? 'bg-selection text-selection-foreground border-selection shadow-sm' 
                              : 'hover:bg-selection-hover hover:text-selection-hover-foreground hover:border-selection-hover'
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
                            {isConfigured && (
                              <div className="w-2 h-2 bg-success rounded-full" title="Configured" />
                            )}
                          </div>
                          <p className="text-xs text-muted-foreground mt-1">
                            {provider.description}
                          </p>
                        </div>
                      );
                    })}
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

export default function ProvidersConfigPage() {
  return (
    <ProviderSettingsProvider>
      <ProviderTestProvider>
        <ProvidersConfigPageContent />
      </ProviderTestProvider>
    </ProviderSettingsProvider>
  );
}