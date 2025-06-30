'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { 
  ProvidersPageState, 
  ProviderInfo, 
  ProviderConfig, 
  TestResult, 
  Model,
  ModelSelection,
  ProviderCategory 
} from '../types'
import { ProviderCards } from './provider-cards'
import { ConfigurationPanel } from './configuration-panel'
import { ModelSelectionPanel } from './model-selection-panel'
import { CurrentConfiguration } from './current-configuration'
import { ProgressTracker } from './progress-tracker'
import { useProvidersApi } from '../hooks/use-providers-api'
import { LoadingSkeleton } from '@/components/ui/loading-skeleton'

/**
 * ProvidersPage - Main container component for AI Provider configuration
 * 
 * This component manages the overall state and orchestrates the provider
 * configuration flow including selection, configuration, testing, and model selection.
 */
export function ProvidersPage() {
  // Initialize state
  const [state, setState] = useState<ProvidersPageState>({
    activeStep: 'select',
    selectedProvider: null,
    selectedCategory: 'cloud',
    isTestingConnection: false,
    isSavingConfig: false,
    showAddCustomModel: false,
    providers: [],
    configurations: new Map(),
    testResults: new Map(),
    availableModels: new Map(),
    modelSelection: {
      textGeneration: { provider: null, model: null },
      embeddings: { provider: null, model: null },
      useSharedProvider: false
    },
    errors: new Map()
  })

  // API hooks
  const {
    isLoading,
    fetchProviders,
    saveProviderConfig,
    testProviderConnection,
    getProviderModels,
    addCustomModel,
    removeCustomModel,
    saveModelSelection,
    getModelSelection
  } = useProvidersApi()

  // Computed values
  const selectedProviderInfo = state.providers.find(p => p.id === state.selectedProvider)
  const selectedProviderConfig = state.selectedProvider 
    ? state.configurations.get(state.selectedProvider) 
    : undefined
  const selectedProviderTestResult = state.selectedProvider 
    ? state.testResults.get(state.selectedProvider) 
    : undefined
  const completedSteps = new Set<ProvidersPageState['activeStep']>()
  if (state.selectedProvider) completedSteps.add('select')
  if (selectedProviderConfig) completedSteps.add('configure')
  if (selectedProviderTestResult?.success) completedSteps.add('test')
  if (state.modelSelection.textGeneration.model) completedSteps.add('models')

  // Load initial data
  useEffect(() => {
    const loadData = async () => {
      try {
        // Fetch providers
        const providers = await fetchProviders()
        
        // Fetch current model selection
        const modelSelection = await getModelSelection()
        
        setState(prev => ({
          ...prev,
          providers,
          modelSelection: modelSelection || prev.modelSelection
        }))
        
        // Load models for configured providers
        for (const provider of providers) {
          if (provider.configured && provider.status === 'configured') {
            const models = await getProviderModels(provider.id)
            setState(prev => ({
              ...prev,
              availableModels: new Map(prev.availableModels).set(provider.id, models)
            }))
          }
        }
      } catch (error) {
        console.error('Failed to load initial data:', error)
      }
    }
    
    loadData()
  }, [fetchProviders, getModelSelection, getProviderModels])

  // Handlers
  const handleProviderSelect = (providerId: string) => {
    setState(prev => ({
      ...prev,
      selectedProvider: providerId,
      activeStep: 'configure'
    }))
  }

  const handleCategoryChange = (category: ProviderCategory) => {
    setState(prev => ({
      ...prev,
      selectedCategory: category
    }))
  }

  const handleConfigurationChange = (config: ProviderConfig) => {
    setState(prev => ({
      ...prev,
      configurations: new Map(prev.configurations).set(config.id, config)
    }))
  }

  const handleTestConnection = async () => {
    if (!state.selectedProvider) return
    
    setState(prev => ({ ...prev, isTestingConnection: true }))
    
    try {
      const result = await testProviderConnection(state.selectedProvider)
      
      setState(prev => ({
        ...prev,
        testResults: new Map(prev.testResults).set(state.selectedProvider!, result),
        isTestingConnection: false,
        activeStep: result.success ? 'models' : 'test'
      }))
      
      // Load models if test was successful and provider is queryable
      if (result.success && result.availableModels) {
        setState(prev => ({
          ...prev,
          availableModels: new Map(prev.availableModels).set(
            state.selectedProvider!, 
            result.availableModels!
          )
        }))
      }
      
      // Update provider status
      setState(prev => ({
        ...prev,
        providers: prev.providers.map(p => 
          p.id === state.selectedProvider 
            ? { ...p, status: result.success ? 'configured' : 'failed' }
            : p
        )
      }))
    } catch (error) {
      setState(prev => ({ ...prev, isTestingConnection: false }))
    }
  }

  const handleSaveConfiguration = async () => {
    if (!state.selectedProvider || !selectedProviderConfig) return
    
    setState(prev => ({ ...prev, isSavingConfig: true }))
    
    try {
      await saveProviderConfig(selectedProviderConfig)
      
      // Update provider status
      setState(prev => ({
        ...prev,
        providers: prev.providers.map(p => 
          p.id === state.selectedProvider 
            ? { ...p, configured: true }
            : p
        ),
        isSavingConfig: false
      }))
    } catch (error) {
      setState(prev => ({ ...prev, isSavingConfig: false }))
      throw error // Re-throw to be handled by ConfigurationPanel
    }
  }

  const handleModelSelectionChange = (selection: ModelSelection) => {
    setState(prev => ({
      ...prev,
      modelSelection: selection
    }))
  }

  const handleSaveModelSelection = async () => {
    const config = {
      text_generation: {
        provider: state.modelSelection.textGeneration.provider || '',
        model: state.modelSelection.textGeneration.model || ''
      },
      embeddings: {
        provider: state.modelSelection.embeddings.provider || '',
        model: state.modelSelection.embeddings.model || ''
      },
      use_shared_provider: state.modelSelection.useSharedProvider
    }
    
    await saveModelSelection(config)
  }

  const handleAddCustomModel = async (providerId: string, model: Model) => {
    await addCustomModel(providerId, model.name)
    
    // Refresh models
    const models = await getProviderModels(providerId)
    setState(prev => ({
      ...prev,
      availableModels: new Map(prev.availableModels).set(providerId, models)
    }))
  }

  const handleRemoveCustomModel = async (providerId: string, modelId: string) => {
    await removeCustomModel(providerId, modelId)
    
    // Refresh models
    const models = await getProviderModels(providerId)
    setState(prev => ({
      ...prev,
      availableModels: new Map(prev.availableModels).set(providerId, models)
    }))
  }

  const handleStepClick = (step: ProvidersPageState['activeStep']) => {
    setState(prev => ({ ...prev, activeStep: step }))
  }

  const handleEditConfiguration = () => {
    setState(prev => ({ ...prev, activeStep: 'models' }))
  }

  if (isLoading) {
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
        activeStep={state.activeStep}
        completedSteps={completedSteps}
        onStepClick={handleStepClick}
      />
      
      {/* Current Configuration Summary */}
      <CurrentConfiguration
        modelSelection={state.modelSelection}
        providers={state.providers}
        onEditConfiguration={handleEditConfiguration}
      />
      
      {/* Main Content Area */}
      <div className="flex gap-6">
        {/* Provider Selection */}
        <ProviderCards
          providers={state.providers}
          selectedProvider={state.selectedProvider}
          selectedCategory={state.selectedCategory}
          onProviderSelect={handleProviderSelect}
          onCategoryChange={handleCategoryChange}
        />
        
        {/* Configuration Panel */}
        <ConfigurationPanel
          provider={selectedProviderInfo || null}
          configuration={selectedProviderConfig}
          isTestingConnection={state.isTestingConnection}
          testResult={selectedProviderTestResult}
          onConfigurationChange={handleConfigurationChange}
          onTestConnection={handleTestConnection}
          onSaveConfiguration={handleSaveConfiguration}
        />
      </div>
      
      {/* Model Selection */}
      {(state.activeStep === 'models' || completedSteps.has('test')) && (
        <ModelSelectionPanel
          providers={state.providers}
          availableModels={state.availableModels}
          modelSelection={state.modelSelection}
          onModelSelectionChange={handleModelSelectionChange}
          onAddCustomModel={handleAddCustomModel}
          onRemoveCustomModel={handleRemoveCustomModel}
          onSaveModelSelection={handleSaveModelSelection}
        />
      )}
    </div>
  )
}