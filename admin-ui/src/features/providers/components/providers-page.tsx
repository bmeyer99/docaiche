'use client'

import React, { useState, useEffect, useMemo, useRef } from 'react'
import { 
  ProvidersPageState, 
  ProviderConfig, 
  Model,
  ModelSelection as LocalModelSelection,
  ProviderCategory 
} from '../types'
import { ProviderCards } from './provider-cards'
import { ConfigurationPanel } from './configuration-panel'
import { useProvidersApi } from '../hooks/use-providers-api'
import { useProviderSettings } from '@/lib/hooks/use-provider-settings'
import { LoadingSkeleton } from '@/components/ui/loading-skeleton'
import '../styles/transitions.css'

/**
 * ProvidersPage - Main container component for AI Provider configuration
 * 
 * This component orchestrates the provider configuration flow while delegating
 * state management to the global ProviderSettingsProvider.
 */
export function ProvidersPage() {
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
  
  // Local UI state only
  const [activeStep, setActiveStep] = useState<ProvidersPageState['activeStep']>('select')
  const [selectedProvider, setSelectedProvider] = useState<string | null>('ollama')
  const [selectedCategory, setSelectedCategory] = useState<ProviderCategory>('local')
  const [isTestingConnection, setIsTestingConnection] = useState(false)
  const [testResults, setTestResults] = useState<Map<string, any>>(new Map())
  const [availableModels, setAvailableModels] = useState<Map<string, Model[]>>(new Map())
  const [showAddCustomModel, setShowAddCustomModel] = useState(false)

  // API hooks for provider-specific operations
  const {
    testProviderConnection,
    getProviderModels,
    addCustomModel,
    removeCustomModel
  } = useProvidersApi()

  // Transform global providers to match local format
  const providers = useMemo(() => {
    const transformed = Object.entries(globalProviders).map(([id, config]) => {
      // Map status properly based on backend values
      let localStatus: 'configured' | 'not_configured' | 'failed' = 'not_configured'
      if (config.status === 'connected' || config.status === 'tested') {
        localStatus = 'configured'
      } else if (config.status === 'error' || config.status === 'failed') {
        localStatus = 'failed'
      }
      
      const result = {
        id,
        name: config.name,
        category: config.category as ProviderCategory,
        description: config.description || '',
        requiresApiKey: config.requiresApiKey || false,
        supportsEmbedding: config.supportsEmbedding || false,
        supportsChat: config.supportsChat || false,
        isQueryable: ['ollama', 'lmstudio', 'openrouter'].includes(id),
        status: localStatus,
        lastTested: config.lastTested,
        configured: config.status === 'connected' || config.status === 'tested',
        enabled: config.enabled || false
      }
      
      return result
    })
    
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
        apiKey: globalProviders[selectedProvider].config?.apiKey,
        baseUrl: globalProviders[selectedProvider].config?.baseUrl,
        ...globalProviders[selectedProvider].config
      }
    : undefined
  const selectedProviderTestResult = selectedProvider 
    ? testResults.get(selectedProvider) 
    : undefined
  const completedSteps = new Set<ProvidersPageState['activeStep']>()
  if (selectedProvider) completedSteps.add('select')
  if (selectedProviderConfig) completedSteps.add('configure')
  if (selectedProviderTestResult?.success) completedSteps.add('test')
  if (modelSelection.textGeneration.model) completedSteps.add('models')

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
    setActiveStep('configure')
  }

  const handleCategoryChange = (category: ProviderCategory) => {
    setSelectedCategory(category)
  }

  const handleConfigurationChange = (config: ProviderConfig) => {
    // Update global provider configuration
    updateProvider(config.id, {
      config: {
        apiKey: config.apiKey,
        baseUrl: config.baseUrl,
        ...config
      }
    })
  }

  const handleTestConnection = async () => {
    if (!selectedProvider) return
    
    setIsTestingConnection(true)
    
    try {
      const result = await testProviderConnection(selectedProvider)
      
      setTestResults(prev => new Map(prev).set(selectedProvider, result))
      
      // Backend automatically saves configuration and models on successful test
      if (result.success) {
        setActiveStep('models')
        console.log('✅ Test successful - backend auto-saved configuration and models')
      } else {
        setActiveStep('test')
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
    } catch (error) {
      throw error // Re-throw to be handled by ConfigurationPanel
    }
  }

  const handleModelSelectionChange = (selection: LocalModelSelection) => {
    // Update global model selection
    updateModelSelection({
      textGeneration: {
        provider: selection.textGeneration.provider || '',
        model: selection.textGeneration.model || ''
      },
      embeddings: {
        provider: selection.embeddings.provider || '',
        model: selection.embeddings.model || ''
      },
      sharedProvider: selection.useSharedProvider
    })
  }

  const handleSaveModelSelection = async () => {
    // Save through global provider
    await saveAllChanges()
  }

  const handleAddCustomModel = async (providerId: string, model: Model) => {
    await addCustomModel(providerId, model.name)
    
    // Refresh models
    const models = await getProviderModels(providerId)
    setAvailableModels(prev => new Map(prev).set(providerId, models))
  }

  const handleRemoveCustomModel = async (providerId: string, modelId: string) => {
    await removeCustomModel(providerId, modelId)
    
    // Refresh models
    const models = await getProviderModels(providerId)
    setAvailableModels(prev => new Map(prev).set(providerId, models))
  }

  const handleStepClick = (step: ProvidersPageState['activeStep']) => {
    setActiveStep(step)
  }

  const handleEditConfiguration = () => {
    setActiveStep('models')
  }

  if (isGlobalLoading) {
    return <LoadingSkeleton variant="dashboard" />
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Page Header */}
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">AI Provider Configuration</h1>
        <p className="text-muted-foreground">Configure and test AI providers for your system</p>
      </div>
      
      {/* Main Content Area */}
      <div className="flex gap-6">
        {/* Test Button - Remove this in production */}
        
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