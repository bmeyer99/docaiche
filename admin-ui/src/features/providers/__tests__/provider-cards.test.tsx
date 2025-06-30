import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import { ProviderCards } from '../components/provider-cards'
import { ProviderInfo } from '../types'

describe('ProviderCards', () => {
  const mockProviders: ProviderInfo[] = [
    {
      id: 'ollama',
      name: 'Ollama',
      category: 'local',
      description: 'Local AI models with Ollama',
      requiresApiKey: false,
      supportsEmbedding: true,
      supportsChat: true,
      isQueryable: true,
      status: 'configured',
      configured: true,
      enabled: true
    },
    {
      id: 'openai',
      name: 'OpenAI',
      category: 'cloud',
      description: 'OpenAI GPT models',
      requiresApiKey: true,
      supportsEmbedding: true,
      supportsChat: true,
      isQueryable: false,
      status: 'not_configured',
      configured: false,
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
      status: 'failed',
      configured: true,
      enabled: true
    }
  ]

  const mockHandlers = {
    onProviderSelect: jest.fn(),
    onCategoryChange: jest.fn()
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders provider categories tabs', () => {
    render(
      <ProviderCards
        providers={mockProviders}
        selectedProvider={null}
        selectedCategory="cloud"
        {...mockHandlers}
      />
    )

    expect(screen.getByRole('tab', { name: 'Local' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Cloud' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Enterprise' })).toBeInTheDocument()
  })

  it('displays providers in correct categories', () => {
    render(
      <ProviderCards
        providers={mockProviders}
        selectedProvider={null}
        selectedCategory="cloud"
        {...mockHandlers}
      />
    )

    // Cloud tab should be active
    expect(screen.getByText('OpenAI')).toBeInTheDocument()
    expect(screen.getByText('Anthropic')).toBeInTheDocument()
    expect(screen.queryByText('Ollama')).not.toBeInTheDocument()
  })

  it('shows correct status badges', () => {
    render(
      <ProviderCards
        providers={mockProviders}
        selectedProvider={null}
        selectedCategory="cloud"
        {...mockHandlers}
      />
    )

    expect(screen.getByText('Not Configured')).toBeInTheDocument()
    expect(screen.getByText('Failed')).toBeInTheDocument()
  })

  it('shows provider capabilities', () => {
    render(
      <ProviderCards
        providers={mockProviders}
        selectedProvider={null}
        selectedCategory="local"
        {...mockHandlers}
      />
    )

    // Switch to local tab
    fireEvent.click(screen.getByRole('tab', { name: 'Local' }))

    // Check Ollama capabilities
    expect(screen.getByText('Chat')).toBeInTheDocument()
    expect(screen.getByText('Embeddings')).toBeInTheDocument()
    expect(screen.getByText('Auto-detect')).toBeInTheDocument()
  })

  it('handles provider selection', () => {
    render(
      <ProviderCards
        providers={mockProviders}
        selectedProvider={null}
        selectedCategory="cloud"
        {...mockHandlers}
      />
    )

    const openaiCard = screen.getByText('OpenAI').closest('div[class*="cursor-pointer"]')
    fireEvent.click(openaiCard!)

    expect(mockHandlers.onProviderSelect).toHaveBeenCalledWith('openai')
  })

  it('handles category change', () => {
    render(
      <ProviderCards
        providers={mockProviders}
        selectedProvider={null}
        selectedCategory="cloud"
        {...mockHandlers}
      />
    )

    fireEvent.click(screen.getByRole('tab', { name: 'Local' }))

    expect(mockHandlers.onCategoryChange).toHaveBeenCalledWith('local')
  })

  it('highlights selected provider', () => {
    render(
      <ProviderCards
        providers={mockProviders}
        selectedProvider="openai"
        selectedCategory="cloud"
        {...mockHandlers}
      />
    )

    const openaiCard = screen.getByText('OpenAI').closest('div[class*="cursor-pointer"]')
    expect(openaiCard).toHaveClass('ring-2', 'ring-primary', 'border-primary')
  })

  it('shows empty state when no providers in category', () => {
    render(
      <ProviderCards
        providers={mockProviders}
        selectedProvider={null}
        selectedCategory="enterprise"
        {...mockHandlers}
      />
    )

    expect(screen.getByText('No enterprise providers available')).toBeInTheDocument()
  })

  it('groups providers correctly by category', () => {
    render(
      <ProviderCards
        providers={mockProviders}
        selectedProvider={null}
        selectedCategory="local"
        {...mockHandlers}
      />
    )

    // Check local tab
    fireEvent.click(screen.getByRole('tab', { name: 'Local' }))
    expect(screen.getByText('Ollama')).toBeInTheDocument()
    expect(screen.queryByText('OpenAI')).not.toBeInTheDocument()

    // Check cloud tab
    fireEvent.click(screen.getByRole('tab', { name: 'Cloud' }))
    expect(screen.getByText('OpenAI')).toBeInTheDocument()
    expect(screen.getByText('Anthropic')).toBeInTheDocument()
    expect(screen.queryByText('Ollama')).not.toBeInTheDocument()
  })
})