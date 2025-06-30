'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Icons } from '@/components/icons';
import { AI_PROVIDERS, ProviderDefinition } from '@/lib/config/providers';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useToast } from '@/hooks/use-toast';

// Simple provider configuration form
function SimpleProviderForm({ provider }: { provider: ProviderDefinition & { id: string } }) {
  const [formData, setFormData] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);
  const { toast } = useToast();
  const apiClient = useApiClient();

  // Initialize form with defaults
  useEffect(() => {
    const initialData: Record<string, string> = {};
    provider.configFields?.forEach(field => {
      const value = field.key === 'base_url' ? provider.defaultBaseUrl || '' : '';
      initialData[field.key] = String(value);
    });
    setFormData(initialData);
  }, [provider.id, provider.configFields, provider.defaultBaseUrl]);

  const handleFieldChange = (fieldKey: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [fieldKey]: value
    }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await apiClient.updateProviderConfiguration(provider.id, { config: formData });
      toast({
        title: "Configuration Saved",
        description: `${provider.displayName} configuration has been saved successfully.`,
      });
    } catch (error) {
      console.error('Save error:', error);
      toast({
        title: "Save Failed",
        description: "Failed to save configuration. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium">{provider.displayName} Configuration</h3>
        <p className="text-sm text-muted-foreground">{provider.description}</p>
      </div>

      <div className="grid gap-4">
        {provider.configFields?.map((field) => {
          const fieldValue = formData[field.key] || '';
          const inputId = `${provider.id}-${field.key}`;

          return (
            <div key={field.key} className="grid gap-2">
              <Label htmlFor={inputId}>
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </Label>
              {field.type === 'textarea' ? (
                <Textarea
                  id={inputId}
                  value={fieldValue}
                  onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  placeholder={field.placeholder}
                  disabled={isSaving}
                />
              ) : field.type === 'number' ? (
                <Input
                  id={inputId}
                  type="number"
                  value={fieldValue}
                  onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  placeholder={field.placeholder}
                  min={field.validation?.min}
                  max={field.validation?.max}
                  disabled={isSaving}
                />
              ) : (
                <Input
                  id={inputId}
                  type={field.type === 'password' ? 'password' : 'text'}
                  value={fieldValue}
                  onChange={(e) => handleFieldChange(field.key, e.target.value)}
                  placeholder={field.placeholder}
                  disabled={isSaving}
                />
              )}
              {field.description && (
                <p className="text-xs text-muted-foreground">{field.description}</p>
              )}
            </div>
          );
        })}
      </div>

      <Button
        onClick={handleSave}
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
            Save Configuration
          </>
        )}
      </Button>
    </div>
  );
}

// Main page component
export default function ProvidersConfigPage() {
  const [activeProvider, setActiveProvider] = useState('ollama');

  // Get provider categories
  const providersByCategory = Object.entries(AI_PROVIDERS).reduce((acc, [, provider]) => {
    if (!acc[provider.category]) acc[provider.category] = [];
    acc[provider.category].push(provider);
    return acc;
  }, {} as Record<string, Array<ProviderDefinition>>);

  const providerCategories = {
    'local': 'Local',
    'cloud': 'Cloud', 
    'enterprise': 'Enterprise'
  };

  const activeProviderData = AI_PROVIDERS[activeProvider];

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-3xl font-bold">AI Provider Configuration</h1>
        <p className="text-muted-foreground">
          Configure your AI providers for text generation and embeddings
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

        <div className="lg:col-span-2">
          <Card>
            <CardContent className="p-6">
              {activeProviderData ? (
                <SimpleProviderForm provider={activeProviderData} />
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