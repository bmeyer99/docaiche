'use client';

/**
 * Providers configuration tab
 * Configure and test AI providers
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
import { useProvidersApi } from '@/features/providers/hooks/use-providers-api';
import { useToast } from '@/hooks/use-toast';
import { AI_PROVIDERS } from '@/lib/config/providers';
import { ProviderCards } from '@/features/providers/components/provider-cards';
import { ConfigurationPanel } from '@/features/providers/components/configuration-panel';
import { CurrentConfiguration } from '@/features/providers/components/current-configuration';
import type { 
  ProviderCategory,
  Model,
  ModelSelection as LocalModelSelection,
  ProviderConfig
} from '@/features/providers/types';

interface ProvidersConfigProps {
  onChangeDetected?: () => void;
}

export function ProvidersConfig({ onChangeDetected }: ProvidersConfigProps) {
  // Global provider settings
  const {
    providers: globalProviders,
    modelSelection: globalModelSelection,
    updateProvider,
    updateModelSelection,
    saveAllChanges,
    hasUnsavedChanges,
    isLoading: isGlobalLoading,
    isSaving: isGlobalSaving
  } = useProviderSettings()
  
  // Local UI state
  const [selectedProvider, setSelectedProvider] = useState<string | null>('ollama')
  const [selectedCategory, setSelectedCategory] = useState<ProviderCategory>('local')
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  const [testResults, setTestResults] = useState<Map<string, any>>(new Map())
  const [availableModels, setAvailableModels] = useState<Map<string, Model[]>>(new Map())

  // API hooks for provider-specific operations
  const {
    testProviderConnection,
    getProviderModels,
    addCustomModel,
    removeCustomModel
  } = useProvidersApi()

  const { toast } = useToast()

  // Transform global providers to match local format
  const providers = useMemo(() => {
    const transformed = Object.entries(globalProviders)
      .map(([id, config]) => {
        // Get provider definition from AI_PROVIDERS
        const providerDef = AI_PROVIDERS[id]
        if (!providerDef) {
          console.warn(`Provider definition not found for: ${id}`)
          return null
        }
        
        // Map status properly based on backend values
        let localStatus: 'configured' | 'not_configured' | 'failed' = 'not_configured'
        if (config.status === 'connected' || config.status === 'tested') {
          localStatus = 'configured'
        } else if (config.status === 'error' || config.status === 'failed') {
          localStatus = 'failed'
        }
        
        return {
          id,
          name: providerDef.displayName,
          category: providerDef.category as ProviderCategory,
          description: providerDef.description,
          requiresApiKey: providerDef.requiresApiKey,
          supportsEmbedding: providerDef.supportsEmbedding,
          supportsChat: providerDef.supportsChat,
          isQueryable: ['ollama', 'lmstudio', 'openrouter'].includes(id),
          status: localStatus,
          lastTested: config.lastTested,
          configured: config.status === 'connected' || config.status === 'tested',
          enabled: config.enabled || false
        }
      })
      .filter((provider): provider is NonNullable<typeof provider> => provider !== null)
    
    return transformed
  }, [globalProviders])
  
  // Transform global model selection to local format
  const modelSelection: LocalModelSelection = useMemo(() => ({
    textGeneration: {
      provider: globalModelSelection.textGeneration?.provider || null,
      model: globalModelSelection.textGeneration?.model || null
    },
    embeddings: {
      provider: globalModelSelection.embeddings?.provider || null,
      model: globalModelSelection.embeddings?.model || null
    },
    useSharedProvider: globalModelSelection.sharedProvider || false
  }), [globalModelSelection])
  
  // Computed values
  const selectedProviderInfo = providers.find(p => p.id === selectedProvider)
  const selectedProviderConfig = selectedProvider && globalProviders[selectedProvider]
    ? {
        id: selectedProvider,
        api_key: globalProviders[selectedProvider].config?.api_key,
        base_url: globalProviders[selectedProvider].config?.base_url,
        ...globalProviders[selectedProvider].config
      }
    : undefined
  const selectedProviderTestResult = selectedProvider 
    ? testResults.get(selectedProvider) 
    : undefined

  // Load models only for the selected provider when it changes
  useEffect(() => {
    if (!selectedProvider || !selectedProviderInfo?.isQueryable) {
      return
    }
    
    const abortController = new AbortController()
    
    const loadModels = async () => {
      try {
        const models = await getProviderModels(selectedProvider)
        if (!abortController.signal.aborted) {
          setAvailableModels(prev => new Map(prev).set(selectedProvider, models))
        }
      } catch (error) {
        if (error instanceof Error && error.name !== 'AbortError') {
          console.error(`Failed to load models for provider ${selectedProvider}:`, error)
        }
      }
    }
    
    loadModels()
    
    return () => {
      abortController.abort()
    }
  }, [selectedProvider, selectedProviderInfo?.isQueryable, getProviderModels])

  // Handlers
  const handleProviderSelect = (providerId: string) => {
    setSelectedProvider(providerId)
  }

  const handleCategoryChange = (category: ProviderCategory) => {
    setSelectedCategory(category)
  }

  const handleConfigurationChange = (config: ProviderConfig) => {
    // Update global provider configuration
    updateProvider(config.id, {
      config: {
        api_key: config.api_key,
        base_url: config.base_url,
        ...config
      }
    })
    onChangeDetected?.()
  }

  const handleTestConnection = async () => {
    if (!selectedProvider) return
    
    setIsTestingConnection(true)
    
    try {
      const result = await testProviderConnection(selectedProvider)
      
      setTestResults(prev => new Map(prev).set(selectedProvider, result))
      
      // Backend automatically saves configuration and models on successful test
      if (result.success) {
        console.log('✅ Test successful - backend auto-saved configuration and models')
        toast({
          title: "Connection Successful",
          description: `Found ${result.availableModels?.length || 0} models`
        })
      } else {
        toast({
          title: "Connection Failed",
          description: result.message || "Unable to connect to provider",
          variant: "destructive"
        })
      }
      
      // Load models if test was successful and provider is queryable
      if (result.success && result.availableModels) {
        setAvailableModels(prev => new Map(prev).set(
          selectedProvider, 
          result.availableModels!
        ))
      }
      
      setIsTestingConnection(false)
      
      // Update provider status in global state
      updateProvider(selectedProvider, {
        status: result.success ? 'configured' : 'failed',
        lastTested: new Date().toISOString()
      })
    } catch (error) {
      setIsTestingConnection(false)
      toast({
        title: "Test Failed",
        description: "Failed to test provider connection",
        variant: "destructive"
      })
    }
  }

  const handleSaveConfiguration = async () => {
    if (!selectedProvider || !selectedProviderConfig) return
    
    try {
      // Save all changes through global provider
      await saveAllChanges()
      
      // Update provider status
      updateProvider(selectedProvider, {
        configured: true
      })

      onChangeDetected?.()
      
      toast({
        title: "Configuration Saved",
        description: "Provider configuration updated successfully"
      })
    } catch (error) {
      toast({
        title: "Save Failed",
        description: "Failed to save configuration",
        variant: "destructive"
      })
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Page Header */}
      <div className="space-y-1">
        <h2 className="text-2xl font-bold">AI Provider Configuration</h2>
        <p className="text-muted-foreground">Configure and test AI providers for your system</p>
      </div>
      
      {/* Current Configuration Summary */}
      <CurrentConfiguration
        modelSelection={modelSelection}
        providers={providers}
        onEditConfiguration={() => {}}
      />
      
      {/* Main Content Area */}
      <div className="flex gap-6">
        {/* Provider Selection */}
        <ProviderCards
          providers={providers}
          selectedProvider={selectedProvider}
          selectedCategory={selectedCategory}
          onProviderSelect={handleProviderSelect}
          onCategoryChange={handleCategoryChange}
        />
        
        {/* Configuration Panel */}
        <ConfigurationPanel
          provider={selectedProviderInfo || null}
          configuration={selectedProviderConfig}
          isTestingConnection={isTestingConnection}
          testResult={selectedProviderTestResult}
          onConfigurationChange={handleConfigurationChange}
          onTestConnection={handleTestConnection}
          onSaveConfiguration={handleSaveConfiguration}
          isSaving={isGlobalSaving}
        />
      </div>
    </div>
  )
}