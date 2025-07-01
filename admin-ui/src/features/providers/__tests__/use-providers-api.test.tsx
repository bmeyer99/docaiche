import { renderHook, waitFor } from '@testing-library/react'
import { useProvidersApi } from '../hooks/use-providers-api'
import React from 'react'

// Mock the API client
const mockGet = jest.fn()
const mockPost = jest.fn()
const mockDelete = jest.fn()

jest.mock('@/lib/hooks/use-api-client', () => ({
  useApiClient: () => ({
    get: mockGet,
    post: mockPost,
    delete: mockDelete
  })
}))

// Mock toast
const mockToast = jest.fn()
jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({ toast: mockToast })
}))

describe('useProvidersApi', () => {
  // No wrapper needed since we're mocking the hook directly
  const wrapper = ({ children }: { children: React.ReactNode }) => <>{children}</>

  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('fetchProviders', () => {
    it('fetches and transforms provider data correctly', async () => {
      const mockProviderData = [
        {
          id: 'openai',
          name: 'OpenAI',
          category: 'cloud',
          description: 'OpenAI API',
          requires_api_key: true,
          supports_embedding: true,
          supports_chat: true,
          status: 'configured',
          last_tested: '2024-01-01T00:00:00Z',
          configured: true,
          enabled: true
        }
      ]

      mockGet.mockResolvedValueOnce(mockProviderData)

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      const providers = await result.current.fetchProviders()

      expect(mockGet).toHaveBeenCalledWith('/api/v1/providers')
      expect(providers).toHaveLength(1)
      expect(providers[0]).toEqual({
        id: 'openai',
        name: 'OpenAI',
        category: 'cloud',
        description: 'OpenAI API',
        requiresApiKey: true,
        supportsEmbedding: true,
        supportsChat: true,
        isQueryable: false,
        status: 'configured',
        lastTested: '2024-01-01T00:00:00Z',
        configured: true,
        enabled: true
      })
    })

    it('handles fetch error gracefully', async () => {
      const error = new Error('Network error')
      mockGet.mockRejectedValueOnce(error)

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      await expect(result.current.fetchProviders()).rejects.toThrow('Network error')

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Failed to load providers',
        description: 'Network error',
        variant: 'destructive'
      })
    })
  })

  describe('saveProviderConfig', () => {
    it('saves provider configuration successfully', async () => {
      mockPost.mockResolvedValueOnce({})

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      const config = {
        id: 'openai',
        apiKey: 'test-key',
        baseUrl: 'https://api.openai.com'
      }

      await result.current.saveProviderConfig(config)

      expect(mockPost).toHaveBeenCalledWith('/api/v1/providers/openai/config', config)
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Configuration saved',
        description: 'Provider configuration has been updated successfully'
      })
    })

    it('handles save error gracefully', async () => {
      const error = new Error('Save failed')
      mockPost.mockRejectedValueOnce(error)

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      const config = {
        id: 'openai',
        apiKey: 'test-key'
      }

      await expect(result.current.saveProviderConfig(config)).rejects.toThrow('Save failed')

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Failed to save configuration',
        description: 'Save failed',
        variant: 'destructive'
      })
    })
  })

  describe('testProviderConnection', () => {
    it('tests connection successfully with models', async () => {
      const mockResponse = {
        success: true,
        message: 'Connection successful',
        models: ['gpt-4', 'gpt-3.5-turbo']
      }

      mockPost.mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      const testResult = await result.current.testProviderConnection('openai')

      expect(mockPost).toHaveBeenCalledWith('/api/v1/providers/openai/test', {})
      expect(testResult).toEqual({
        success: true,
        message: 'Connection successful',
        timestamp: expect.any(String),
        error: undefined,
        availableModels: [
          { id: 'gpt-4', name: 'gpt-4', displayName: 'gpt-4' },
          { id: 'gpt-3.5-turbo', name: 'gpt-3.5-turbo', displayName: 'gpt-3.5-turbo' }
        ]
      })

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Connection successful',
        description: 'Connection successful'
      })
    })

    it('handles connection failure', async () => {
      const mockResponse = {
        success: false,
        message: 'Invalid API key',
        error: 'Authentication failed'
      }

      mockPost.mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      const testResult = await result.current.testProviderConnection('openai')

      expect(testResult).toEqual({
        success: false,
        message: 'Invalid API key',
        timestamp: expect.any(String),
        error: 'Authentication failed',
        availableModels: undefined
      })

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Connection failed',
        description: 'Invalid API key',
        variant: 'destructive'
      })
    })

    it('handles network error during test', async () => {
      const error = new Error('Network timeout')
      mockPost.mockRejectedValueOnce(error)

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      const testResult = await result.current.testProviderConnection('openai')

      expect(testResult).toEqual({
        success: false,
        message: 'Network timeout',
        timestamp: expect.any(String),
        error: 'Network timeout'
      })

      expect(mockToast).toHaveBeenCalledWith({
        title: 'Test failed',
        description: 'Network timeout',
        variant: 'destructive'
      })
    })
  })

  describe('getProviderModels', () => {
    it('fetches and transforms models successfully', async () => {
      const mockModels = ['gpt-4', 'gpt-3.5-turbo']
      mockGet.mockResolvedValueOnce(mockModels)

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      const models = await result.current.getProviderModels('openai')

      expect(mockGet).toHaveBeenCalledWith('/api/v1/providers/openai/models')
      expect(models).toEqual([
        { id: 'gpt-4', name: 'gpt-4', displayName: 'gpt-4' },
        { id: 'gpt-3.5-turbo', name: 'gpt-3.5-turbo', displayName: 'gpt-3.5-turbo' }
      ])
    })

    it('returns empty array on error', async () => {
      const error = new Error('Failed to fetch models')
      mockGet.mockRejectedValueOnce(error)

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      const models = await result.current.getProviderModels('openai')

      expect(models).toEqual([])
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Failed to load models',
        description: 'Failed to fetch models',
        variant: 'destructive'
      })
    })
  })

  describe('custom model management', () => {
    it('adds custom model successfully', async () => {
      mockPost.mockResolvedValueOnce({})

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      await result.current.addCustomModel('openai', 'custom-model-1')

      expect(mockPost).toHaveBeenCalledWith('/api/v1/providers/openai/models', {
        model_name: 'custom-model-1'
      })
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Model added',
        description: 'Custom model "custom-model-1" has been added successfully'
      })
    })

    it('removes custom model successfully', async () => {
      mockDelete.mockResolvedValueOnce({})

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      await result.current.removeCustomModel('openai', 'custom-model-1')

      expect(mockDelete).toHaveBeenCalledWith('/api/v1/providers/openai/models/custom-model-1')
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Model removed',
        description: 'Custom model "custom-model-1" has been removed'
      })
    })
  })

  describe('model selection', () => {
    it('saves model selection successfully', async () => {
      mockPost.mockResolvedValueOnce({})

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      const config = {
        text_generation: {
          provider: 'openai',
          model: 'gpt-4'
        },
        embeddings: {
          provider: 'openai',
          model: 'text-embedding-3-small'
        },
        use_shared_provider: false
      }

      await result.current.saveModelSelection(config)

      expect(mockPost).toHaveBeenCalledWith('/api/v1/models/config', config)
      expect(mockToast).toHaveBeenCalledWith({
        title: 'Model selection saved',
        description: 'Your model preferences have been updated'
      })
    })

    it('gets model selection successfully', async () => {
      const mockConfig = {
        text_generation: {
          provider: 'openai',
          model: 'gpt-4'
        },
        embeddings: {
          provider: 'openai',
          model: 'text-embedding-3-small'
        },
        use_shared_provider: false
      }

      mockGet.mockResolvedValueOnce(mockConfig)

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      const config = await result.current.getModelSelection()

      expect(mockGet).toHaveBeenCalledWith('/api/v1/models/config')
      expect(config).toEqual(mockConfig)
    })

    it('returns null when no model selection exists', async () => {
      mockGet.mockRejectedValueOnce(new Error('Not found'))

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      const config = await result.current.getModelSelection()

      expect(config).toBeNull()
    })
  })

  describe('loading state', () => {
    it('manages loading state during fetchProviders', async () => {
      let resolvePromise: (value: any) => void
      const promise = new Promise(resolve => {
        resolvePromise = resolve
      })
      mockGet.mockReturnValueOnce(promise)

      const { result } = renderHook(() => useProvidersApi(), { wrapper })

      expect(result.current.isLoading).toBe(false)

      const fetchPromise = result.current.fetchProviders()
      
      await waitFor(() => {
        expect(result.current.isLoading).toBe(true)
      })

      await waitFor(async () => {
        resolvePromise!([])
        await fetchPromise
        expect(result.current.isLoading).toBe(false)
      })
    })
  })
})