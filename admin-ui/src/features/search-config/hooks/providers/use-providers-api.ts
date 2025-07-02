import { useState, useCallback } from 'react'
import { useApiClient } from '@/lib/hooks/use-api-client'
import { useToast } from '@/hooks/use-toast'
import { 
  ProviderInfo, 
  ProviderConfig, 
  TestResult, 
  Model,
  ProviderResponse,
  ModelSelectionConfig 
} from '../../types/providers'

// Transform API response to frontend format
function transformProviderResponse(response: ProviderResponse): ProviderInfo {
  return {
    id: response.id,
    name: response.name,
    category: response.category as ProviderInfo['category'],
    description: response.description,
    requiresApiKey: response.requires_api_key,
    supportsEmbedding: response.supports_embedding,
    supportsChat: response.supports_chat,
    isQueryable: ['ollama', 'lmstudio', 'openrouter'].includes(response.id),
    status: response.status as ProviderInfo['status'],
    lastTested: response.last_tested,
    configured: response.configured,
    enabled: response.enabled
  }
}

export function useProvidersApi() {
  const apiClient = useApiClient()
  const { toast } = useToast()
  const [isLoading, setIsLoading] = useState(false)

  // Fetch all provider configurations
  const fetchProviders = useCallback(async (): Promise<ProviderInfo[]> => {
    try {
      setIsLoading(true)
      const response = await apiClient.get<ProviderResponse[]>('/providers')
      return response.map(transformProviderResponse)
    } catch (error) {
      toast({
        title: 'Failed to load providers',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive'
      })
      throw error
    } finally {
      setIsLoading(false)
    }
  }, [apiClient, toast])

  // Save provider configuration
  const saveProviderConfig = useCallback(async (config: ProviderConfig): Promise<void> => {
    try {
      await apiClient.post(`/providers/${config.id}/config`, config)
      toast({
        title: 'Configuration saved',
        description: 'Provider configuration has been updated successfully'
      })
    } catch (error) {
      toast({
        title: 'Failed to save configuration',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive'
      })
      throw error
    }
  }, [apiClient, toast])

  // Test provider connection
  const testProviderConnection = useCallback(async (providerId: string, config?: Record<string, any>): Promise<TestResult> => {
    try {
      // Filter config to only include fields expected by backend
      // The backend expects: base_url, api_key, and model
      const filteredConfig: Record<string, any> = {}
      
      if (config) {
        // Always include these if present
        if (config.base_url !== undefined) filteredConfig.base_url = config.base_url
        if (config.api_key !== undefined) filteredConfig.api_key = config.api_key
        if (config.model !== undefined) filteredConfig.model = config.model
        
        // Provider-specific fields
        switch (providerId) {
          case 'vertex':
            if (config.vertex_project_id) filteredConfig.vertex_project_id = config.vertex_project_id
            if (config.vertex_region) filteredConfig.vertex_region = config.vertex_region
            if (config.vertex_json_credentials) filteredConfig.vertex_json_credentials = config.vertex_json_credentials
            break
          case 'bedrock':
            if (config.aws_region) filteredConfig.aws_region = config.aws_region
            if (config.aws_access_key) filteredConfig.aws_access_key = config.aws_access_key
            if (config.aws_secret_key) filteredConfig.aws_secret_key = config.aws_secret_key
            break
          case 'openrouter':
            if (config.site_url) filteredConfig.site_url = config.site_url
            if (config.app_name) filteredConfig.app_name = config.app_name
            break
          case 'openai':
            if (config.organization) filteredConfig.organization = config.organization
            break
        }
      }
      
      const response = await apiClient.post<{
        success: boolean
        message: string
        models?: string[]
        error?: string
      }>(`/providers/${providerId}/test`, filteredConfig)
      
      const result: TestResult = {
        success: response.success,
        message: response.message,
        timestamp: new Date().toISOString(),
        error: response.error,
        availableModels: response.models?.map(name => ({
          id: name,
          name: name,
          displayName: name
        }))
      }
      
      if (response.success) {
        toast({
          title: 'Connection successful',
          description: response.message
        })
      } else {
        toast({
          title: 'Connection failed',
          description: response.message,
          variant: 'destructive'
        })
      }
      
      return result
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Connection test failed'
      toast({
        title: 'Test failed',
        description: message,
        variant: 'destructive'
      })
      return {
        success: false,
        message,
        timestamp: new Date().toISOString(),
        error: message
      }
    }
  }, [apiClient, toast])

  // Get available models for a provider
  const getProviderModels = useCallback(async (providerId: string): Promise<Model[]> => {
    try {
      const response = await apiClient.get<{
        provider: string
        models: string[]
        queryable: boolean
        default_count?: number
        custom_count?: number
      }>(`/providers/${providerId}/models`)
      
      // Extract models array from response object
      const models = response.models || []
      return models.map(name => ({
        id: name,
        name: name,
        displayName: name
      }))
    } catch (error) {
      toast({
        title: 'Failed to load models',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive'
      })
      return []
    }
  }, [apiClient, toast])

  // Add custom model to provider
  const addCustomModel = useCallback(async (providerId: string, modelName: string): Promise<void> => {
    try {
      await apiClient.post(`/providers/${providerId}/models`, { model_name: modelName })
      toast({
        title: 'Model added',
        description: `Custom model "${modelName}" has been added successfully`
      })
    } catch (error) {
      toast({
        title: 'Failed to add model',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive'
      })
      throw error
    }
  }, [apiClient, toast])

  // Remove custom model from provider
  const removeCustomModel = useCallback(async (providerId: string, modelName: string): Promise<void> => {
    try {
      await apiClient.delete(`/providers/${providerId}/models/${modelName}`)
      toast({
        title: 'Model removed',
        description: `Custom model "${modelName}" has been removed`
      })
    } catch (error) {
      toast({
        title: 'Failed to remove model',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive'
      })
      throw error
    }
  }, [apiClient, toast])

  // Save model selection configuration
  const saveModelSelection = useCallback(async (config: ModelSelectionConfig): Promise<void> => {
    try {
      await apiClient.post('/models/config', config)
      toast({
        title: 'Model selection saved',
        description: 'Your model preferences have been updated'
      })
    } catch (error) {
      toast({
        title: 'Failed to save model selection',
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: 'destructive'
      })
      throw error
    }
  }, [apiClient, toast])

  // Get current model selection
  const getModelSelection = useCallback(async (): Promise<ModelSelectionConfig | null> => {
    try {
      const response = await apiClient.get<ModelSelectionConfig>('/models/config')
      return response
    } catch (error) {
      // Model selection might not exist yet
      return null
    }
  }, [apiClient])

  return {
    isLoading,
    fetchProviders,
    saveProviderConfig,
    testProviderConnection,
    getProviderModels,
    addCustomModel,
    removeCustomModel,
    saveModelSelection,
    getModelSelection
  }
}