import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { ModelSelectionPanel } from '../components/model-selection-panel'
import { ProviderInfo, Model, ModelSelection } from '../types'

describe('ModelSelectionPanel', () => {
  const mockProviders: ProviderInfo[] = [
    {
      id: 'openai',
      name: 'OpenAI',
      category: 'cloud',
      description: 'OpenAI GPT models',
      requiresApiKey: true,
      supportsEmbedding: true,
      supportsChat: true,
      isQueryable: false,
      status: 'configured',
      configured: true,
      enabled: true
    },
    {
      id: 'anthropic',
      name: 'Anthropic',
      category: 'cloud',
      description: 'Claude AI models',
      requiresApiKey: true,
      supportsEmbedding: false,
      supportsChat: true,
      isQueryable: false,
      status: 'configured',
      configured: true,
      enabled: true
    },
    {
      id: 'ollama',
      name: 'Ollama',
      category: 'local',
      description: 'Local AI models',
      requiresApiKey: false,
      supportsEmbedding: true,
      supportsChat: true,
      isQueryable: true,
      status: 'configured',
      configured: true,
      enabled: true
    }
  ]

  const mockModels: Map<string, Model[]> = new Map([
    ['openai', [
      { id: 'gpt-4', name: 'gpt-4', displayName: 'GPT-4' },
      { id: 'gpt-3.5-turbo', name: 'gpt-3.5-turbo', displayName: 'GPT-3.5 Turbo' },
      { id: 'text-embedding-ada-002', name: 'text-embedding-ada-002', displayName: 'Ada Embeddings' }
    ]],
    ['anthropic', [
      { id: 'claude-3-opus', name: 'claude-3-opus', displayName: 'Claude 3 Opus' },
      { id: 'claude-3-sonnet', name: 'claude-3-sonnet', displayName: 'Claude 3 Sonnet' }
    ]],
    ['ollama', [
      { id: 'llama2', name: 'llama2', displayName: 'Llama 2' },
      { id: 'mistral', name: 'mistral', displayName: 'Mistral' }
    ]]
  ])

  const defaultModelSelection: ModelSelection = {
    textGeneration: { provider: null, model: null },
    embeddings: { provider: null, model: null },
    useSharedProvider: false
  }

  const mockHandlers = {
    onModelSelectionChange: jest.fn(),
    onAddCustomModel: jest.fn().mockResolvedValue(undefined),
    onRemoveCustomModel: jest.fn().mockResolvedValue(undefined),
    onSaveModelSelection: jest.fn().mockResolvedValue(undefined)
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders with no configured providers message', () => {
    render(
      <ModelSelectionPanel
        providers={[]}
        availableModels={new Map()}
        modelSelection={defaultModelSelection}
        {...mockHandlers}
      />
    )

    expect(screen.getByText(/No providers have been configured/)).toBeInTheDocument()
  })

  it('renders model selection interface when providers are configured', () => {
    render(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={defaultModelSelection}
        {...mockHandlers}
      />
    )

    expect(screen.getByText('Model Selection')).toBeInTheDocument()
    expect(screen.getByText('Text Generation Model')).toBeInTheDocument()
    expect(screen.getByLabelText(/Use the same provider/)).toBeInTheDocument()
  })

  it('handles shared provider toggle', async () => {
    const user = userEvent.setup()
    
    render(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={{
          ...defaultModelSelection,
          textGeneration: { provider: 'openai', model: 'gpt-4' }
        }}
        {...mockHandlers}
      />
    )

    const toggle = screen.getByRole('switch')
    await user.click(toggle)

    expect(mockHandlers.onModelSelectionChange).toHaveBeenCalledWith({
      textGeneration: { provider: 'openai', model: 'gpt-4' },
      embeddings: { provider: 'openai', model: 'gpt-4' },
      useSharedProvider: true
    })
  })

  it('shows only embedding providers for embedding selection', () => {
    render(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={defaultModelSelection}
        {...mockHandlers}
      />
    )

    // Click on embeddings provider dropdown
    const embeddingSelects = screen.getAllByRole('combobox')
    fireEvent.click(embeddingSelects[2]) // Third select is embeddings provider

    // Anthropic shouldn't appear as it doesn't support embeddings
    expect(screen.queryByText('Anthropic')).not.toBeInTheDocument()
  })

  it('disables model selection when no provider is selected', () => {
    render(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={defaultModelSelection}
        {...mockHandlers}
      />
    )

    const modelSelects = screen.getAllByRole('combobox')
    expect(modelSelects[1]).toBeDisabled() // Text generation model select
    expect(modelSelects[3]).toBeDisabled() // Embeddings model select
  })

  it('enables save button only when both models are selected', () => {
    const { rerender } = render(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={defaultModelSelection}
        {...mockHandlers}
      />
    )

    const saveButton = screen.getByRole('button', { name: /Save Model Configuration/i })
    expect(saveButton).toBeDisabled()

    // Select text generation model
    rerender(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={{
          ...defaultModelSelection,
          textGeneration: { provider: 'openai', model: 'gpt-4' }
        }}
        {...mockHandlers}
      />
    )

    expect(saveButton).toBeDisabled()

    // Select embeddings model
    rerender(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={{
          textGeneration: { provider: 'openai', model: 'gpt-4' },
          embeddings: { provider: 'openai', model: 'text-embedding-ada-002' },
          useSharedProvider: false
        }}
        {...mockHandlers}
      />
    )

    expect(saveButton).toBeEnabled()
  })

  it('shows add custom model button for non-queryable providers', () => {
    render(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={{
          ...defaultModelSelection,
          textGeneration: { provider: 'openai', model: null }
        }}
        {...mockHandlers}
      />
    )

    const addButtons = screen.getAllByRole('button', { name: '' })
    const addButton = addButtons.find(btn => btn.querySelector('svg'))
    expect(addButton).toBeEnabled()
  })

  it('disables add custom model button for queryable providers', () => {
    render(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={{
          ...defaultModelSelection,
          textGeneration: { provider: 'ollama', model: null }
        }}
        {...mockHandlers}
      />
    )

    const addButtons = screen.getAllByRole('button', { name: '' })
    const addButton = addButtons.find(btn => btn.querySelector('svg'))
    expect(addButton).toBeDisabled()
  })

  it('opens custom model dialog when add button is clicked', async () => {
    const user = userEvent.setup()
    
    render(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={{
          ...defaultModelSelection,
          textGeneration: { provider: 'openai', model: null }
        }}
        {...mockHandlers}
      />
    )

    const addButtons = screen.getAllByRole('button', { name: '' })
    const addButton = addButtons.find(btn => btn.querySelector('svg'))!
    await user.click(addButton)

    expect(screen.getByText('Add Custom Model')).toBeInTheDocument()
    expect(screen.getByLabelText('Model Name')).toBeInTheDocument()
  })

  it('adds custom model when dialog is submitted', async () => {
    const user = userEvent.setup()
    
    render(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={{
          ...defaultModelSelection,
          textGeneration: { provider: 'openai', model: null }
        }}
        {...mockHandlers}
      />
    )

    // Open dialog
    const addButtons = screen.getAllByRole('button', { name: '' })
    const addButton = addButtons.find(btn => btn.querySelector('svg'))!
    await user.click(addButton)

    // Enter model name
    const input = screen.getByLabelText('Model Name')
    await user.type(input, 'gpt-4-turbo')

    // Submit
    const submitButton = screen.getByRole('button', { name: 'Add Model' })
    await user.click(submitButton)

    expect(mockHandlers.onAddCustomModel).toHaveBeenCalledWith('openai', {
      id: 'gpt-4-turbo',
      name: 'gpt-4-turbo',
      displayName: 'gpt-4-turbo',
      isCustom: true
    })
  })

  it('hides embeddings selection when shared provider is enabled', () => {
    render(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={{
          ...defaultModelSelection,
          useSharedProvider: true
        }}
        {...mockHandlers}
      />
    )

    expect(screen.queryByText('Embeddings Model')).not.toBeInTheDocument()
  })

  it('calls save handler when save button is clicked', async () => {
    const user = userEvent.setup()
    
    render(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={{
          textGeneration: { provider: 'openai', model: 'gpt-4' },
          embeddings: { provider: 'openai', model: 'text-embedding-ada-002' },
          useSharedProvider: false
        }}
        {...mockHandlers}
      />
    )

    const saveButton = screen.getByRole('button', { name: /Save Model Configuration/i })
    await user.click(saveButton)

    expect(mockHandlers.onSaveModelSelection).toHaveBeenCalled()
  })

  it('shows saving state when save is in progress', async () => {
    const user = userEvent.setup()
    
    // Mock slow save
    mockHandlers.onSaveModelSelection.mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    )
    
    render(
      <ModelSelectionPanel
        providers={mockProviders}
        availableModels={mockModels}
        modelSelection={{
          textGeneration: { provider: 'openai', model: 'gpt-4' },
          embeddings: { provider: 'openai', model: 'text-embedding-ada-002' },
          useSharedProvider: false
        }}
        {...mockHandlers}
      />
    )

    const saveButton = screen.getByRole('button', { name: /Save Model Configuration/i })
    await user.click(saveButton)

    expect(screen.getByText('Saving...')).toBeInTheDocument()
    
    await waitFor(() => {
      expect(screen.getByText('Save Model Configuration')).toBeInTheDocument()
    })
  })
})