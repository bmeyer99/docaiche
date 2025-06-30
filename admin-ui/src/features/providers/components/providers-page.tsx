'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { 
  ProvidersPageState, 
  ProviderConfig, 
  Model,
  ModelSelection as LocalModelSelection,
  ProviderCategory 
} from '../types'
import { ProviderCards } from './provider-cards'
import { ConfigurationPanel } from './configuration-panel'
import { ModelSelectionPanel } from './model-selection-panel'
import { CurrentConfiguration } from './current-configuration'
import { ProgressTracker } from './progress-tracker'
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
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<ProviderCategory>('cloud')
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
    return Object.entries(globalProviders).map(([id, config]) => ({
      id,
      name: config.name,
      category: config.category as ProviderCategory,
      description: config.description || '',
      requiresApiKey: config.requiresApiKey || false,
      supportsEmbedding: config.supportsEmbedding || false,
      supportsChat: config.supportsChat || false,
      isQueryable: ['ollama', 'lmstudio', 'openrouter'].includes(id),
      status: config.status as 'configured' | 'not_configured' | 'failed',
      lastTested: config.lastTested,
      configured: config.configured || false,
      enabled: config.enabled || false
    }))
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
    useSharedProvider: globalModelSelection.useSharedProvider || false
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

  // Load models for configured providers
  useEffect(() => {
    let mounted = true
    
    const loadModels = async () => {
      const configuredProviders = providers.filter(p => p.configured && p.status === 'configured')
      const newAvailableModels = new Map<string, Model[]>()
      
      // Batch load models to improve performance
      const modelPromises = configuredProviders.map(async (provider) => {
        try {
          const models = await getProviderModels(provider.id)
          return { providerId: provider.id, models }
        } catch {
          return { providerId: provider.id, models: [] }
        }
      })
      
      const modelResults = await Promise.all(modelPromises)
      
      if (!mounted) return
      
      for (const result of modelResults) {
        newAvailableModels.set(result.providerId, result.models)
      }
      
      setAvailableModels(newAvailableModels)
    }
    
    loadModels()
    
    return () => {
      mounted = false
    }
  }, [providers, getProviderModels])

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
      setIsTestingConnection(false)
      setActiveStep(result.success ? 'models' : 'test')
      
      // Load models if test was successful and provider is queryable
      if (result.success && result.availableModels) {
        setAvailableModels(prev => new Map(prev).set(
          selectedProvider, 
          result.availableModels!
        ))
      }
      
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
      textGeneration: selection.textGeneration,
      embeddings: selection.embeddings,
      useSharedProvider: selection.useSharedProvider
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
      
      {/* Progress Tracker */}
      <ProgressTracker
        activeStep={activeStep}
        completedSteps={completedSteps}
        onStepClick={handleStepClick}
      />
      
      {/* Current Configuration Summary */}
      <CurrentConfiguration
        modelSelection={modelSelection}
        providers={providers}
        onEditConfiguration={handleEditConfiguration}
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
      
      {/* Model Selection */}
      {(activeStep === 'models' || completedSteps.has('test')) && (
        <ModelSelectionPanel
          providers={providers}
          availableModels={availableModels}
          modelSelection={modelSelection}
          onModelSelectionChange={handleModelSelectionChange}
          onAddCustomModel={handleAddCustomModel}
          onRemoveCustomModel={handleRemoveCustomModel}
          onSaveModelSelection={handleSaveModelSelection}
          isSaving={isGlobalSaving}
        />
      )}
    </div>
  )
}