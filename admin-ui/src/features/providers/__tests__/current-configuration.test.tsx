import React from 'react'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CurrentConfiguration } from '../components/current-configuration'
import { ProviderInfo, ModelSelection } from '../types'

describe('CurrentConfiguration', () => {
  const mockProviders: ProviderInfo[] = [
    {
      id: 'openai',
      name: 'OpenAI',
      category: 'cloud',
      description: 'OpenAI API',
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
      name: 'Anthropic Claude',
      category: 'cloud',
      description: 'Anthropic API',
      requiresApiKey: true,
      supportsEmbedding: false,
      supportsChat: true,
      isQueryable: false,
      status: 'configured',
      configured: true,
      enabled: true
    }
  ]

  const mockModelSelection: ModelSelection = {
    textGeneration: {
      provider: 'anthropic',
      model: 'claude-3-opus-20240229'
    },
    embeddings: {
      provider: 'openai',
      model: 'text-embedding-3-small'
    },
    useSharedProvider: false
  }

  const mockOnEditConfiguration = jest.fn()

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders current configuration when models are selected', () => {
    render(
      <CurrentConfiguration
        modelSelection={mockModelSelection}
        providers={mockProviders}
        onEditConfiguration={mockOnEditConfiguration}
      />
    )

    expect(screen.getByText('Current Configuration')).toBeInTheDocument()
    expect(screen.getByText('Your active AI model settings')).toBeInTheDocument()
    expect(screen.getByText('Text Generation')).toBeInTheDocument()
    expect(screen.getByText('Embeddings')).toBeInTheDocument()
    expect(screen.getByText('Anthropic Claude')).toBeInTheDocument()
    expect(screen.getByText('OpenAI')).toBeInTheDocument()
    expect(screen.getByText('claude-3-opus-20240229')).toBeInTheDocument()
    expect(screen.getByText('text-embedding-3-small')).toBeInTheDocument()
  })

  it('renders nothing when no models are configured', () => {
    const emptySelection: ModelSelection = {
      textGeneration: { provider: null, model: null },
      embeddings: { provider: null, model: null },
      useSharedProvider: false
    }

    const { container } = render(
      <CurrentConfiguration
        modelSelection={emptySelection}
        providers={mockProviders}
        onEditConfiguration={mockOnEditConfiguration}
      />
    )

    expect(container.firstChild).toBeNull()
  })

  it('shows shared provider indicator when enabled', () => {
    const sharedSelection = {
      ...mockModelSelection,
      useSharedProvider: true
    }

    render(
      <CurrentConfiguration
        modelSelection={sharedSelection}
        providers={mockProviders}
        onEditConfiguration={mockOnEditConfiguration}
      />
    )

    expect(screen.getByText('Using shared provider')).toBeInTheDocument()
  })

  it('handles partial configuration (only text generation)', () => {
    const partialSelection: ModelSelection = {
      textGeneration: {
        provider: 'anthropic',
        model: 'claude-3-opus-20240229'
      },
      embeddings: { provider: null, model: null },
      useSharedProvider: false
    }

    render(
      <CurrentConfiguration
        modelSelection={partialSelection}
        providers={mockProviders}
        onEditConfiguration={mockOnEditConfiguration}
      />
    )

    expect(screen.getByText('Anthropic Claude')).toBeInTheDocument()
    expect(screen.getByText('claude-3-opus-20240229')).toBeInTheDocument()
    expect(screen.getAllByText('Not configured')).toHaveLength(1)
  })

  it('calls onEditConfiguration when Change Models button is clicked', async () => {
    const user = userEvent.setup()

    render(
      <CurrentConfiguration
        modelSelection={mockModelSelection}
        providers={mockProviders}
        onEditConfiguration={mockOnEditConfiguration}
      />
    )

    await user.click(screen.getByText('Change Models'))
    expect(mockOnEditConfiguration).toHaveBeenCalledTimes(1)
  })

  it('handles unknown provider gracefully', () => {
    const unknownProviderSelection: ModelSelection = {
      textGeneration: {
        provider: 'unknown-provider',
        model: 'some-model'
      },
      embeddings: { provider: null, model: null },
      useSharedProvider: false
    }

    render(
      <CurrentConfiguration
        modelSelection={unknownProviderSelection}
        providers={mockProviders}
        onEditConfiguration={mockOnEditConfiguration}
      />
    )

    // Both text generation and embeddings should show "Not configured"
    // since the text generation provider is unknown
    const notConfiguredElements = screen.getAllByText('Not configured')
    expect(notConfiguredElements).toHaveLength(2)
  })
})