import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import '@testing-library/jest-dom'
import { ConfigurationPanel } from '../components/configuration-panel'
import { ProviderInfo, TestResult } from '../types'

// Mock the schema utilities
jest.mock('../utils/provider-schemas', () => ({
  getProviderSchema: jest.fn((providerId) => {
    // Return a simple schema for testing
    const z = require('zod')
    if (providerId === 'openai') {
      return z.object({
        apiKey: z.string().min(1, 'API key is required'),
        timeout: z.number().optional()
      })
    }
    return z.object({})
  }),
  getProviderDefaults: jest.fn((providerId) => {
    if (providerId === 'openai') {
      return { timeout: 30, maxRetries: 3 }
    }
    return {}
  }),
  getProviderFields: jest.fn((providerId) => {
    if (providerId === 'openai') {
      return [
        {
          name: 'apiKey',
          label: 'API Key',
          type: 'password',
          placeholder: 'sk-...',
          description: 'Your OpenAI API key',
          required: true
        },
        {
          name: 'timeout',
          label: 'Timeout (seconds)',
          type: 'number',
          placeholder: '30',
          description: 'Maximum time to wait for a response'
        }
      ]
    }
    return []
  })
}))

describe('ConfigurationPanel', () => {
  const mockProvider: ProviderInfo = {
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
  }

  const mockHandlers = {
    onConfigurationChange: jest.fn(),
    onTestConnection: jest.fn(),
    onSaveConfiguration: jest.fn().mockResolvedValue(undefined)
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('shows placeholder when no provider is selected', () => {
    render(
      <ConfigurationPanel
        provider={null}
        configuration={undefined}
        isTestingConnection={false}
        testResult={undefined}
        {...mockHandlers}
      />
    )

    expect(screen.getByText('Select a Provider')).toBeInTheDocument()
    expect(screen.getByText('Choose a provider from the left to begin configuration')).toBeInTheDocument()
  })

  it('renders provider configuration form', () => {
    render(
      <ConfigurationPanel
        provider={mockProvider}
        configuration={undefined}
        isTestingConnection={false}
        testResult={undefined}
        {...mockHandlers}
      />
    )

    expect(screen.getByText('Configure OpenAI')).toBeInTheDocument()
    expect(screen.getByText('OpenAI GPT models')).toBeInTheDocument()
    expect(screen.getByLabelText(/API Key/)).toBeInTheDocument()
    expect(screen.getByLabelText(/Timeout/)).toBeInTheDocument()
  })

  it('shows required field indicators', () => {
    render(
      <ConfigurationPanel
        provider={mockProvider}
        configuration={undefined}
        isTestingConnection={false}
        testResult={undefined}
        {...mockHandlers}
      />
    )

    const apiKeyLabel = screen.getByText('API Key')
    expect(apiKeyLabel.parentElement).toHaveTextContent('*')
  })

  it('loads existing configuration values', () => {
    const existingConfig = {
      id: 'openai',
      apiKey: 'sk-existing-key',
      timeout: 60
    }

    render(
      <ConfigurationPanel
        provider={mockProvider}
        configuration={existingConfig}
        isTestingConnection={false}
        testResult={undefined}
        {...mockHandlers}
      />
    )

    expect(screen.getByDisplayValue('sk-existing-key')).toBeInTheDocument()
    expect(screen.getByDisplayValue('60')).toBeInTheDocument()
  })

  it('validates required fields', async () => {
    const user = userEvent.setup()
    
    render(
      <ConfigurationPanel
        provider={mockProvider}
        configuration={undefined}
        isTestingConnection={false}
        testResult={undefined}
        {...mockHandlers}
      />
    )

    // Try to save without filling required field
    const saveButton = screen.getByRole('button', { name: 'Save Configuration' })
    await user.click(saveButton)

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText('API key is required')).toBeInTheDocument()
    })
  })

  it('handles form submission', async () => {
    const user = userEvent.setup()
    
    render(
      <ConfigurationPanel
        provider={mockProvider}
        configuration={undefined}
        isTestingConnection={false}
        testResult={undefined}
        {...mockHandlers}
      />
    )

    // Fill in the form
    await user.type(screen.getByLabelText(/API Key/), 'sk-test-key-123')
    await user.clear(screen.getByLabelText(/Timeout/))
    await user.type(screen.getByLabelText(/Timeout/), '45')

    // Submit form
    await user.click(screen.getByRole('button', { name: 'Save Configuration' }))

    await waitFor(() => {
      expect(mockHandlers.onConfigurationChange).toHaveBeenCalledWith({
        id: 'openai',
        apiKey: 'sk-test-key-123',
        timeout: 45,
        maxRetries: 3
      })
      expect(mockHandlers.onSaveConfiguration).toHaveBeenCalled()
    })
  })

  it('shows test connection button and handles testing', async () => {
    const user = userEvent.setup()
    
    render(
      <ConfigurationPanel
        provider={mockProvider}
        configuration={{ id: 'openai', apiKey: 'sk-test' }}
        isTestingConnection={false}
        testResult={undefined}
        {...mockHandlers}
      />
    )

    const testButton = screen.getByRole('button', { name: 'Test Connection' })
    await user.click(testButton)

    expect(mockHandlers.onTestConnection).toHaveBeenCalled()
  })

  it('shows loading state during connection test', () => {
    render(
      <ConfigurationPanel
        provider={mockProvider}
        configuration={{ id: 'openai', apiKey: 'sk-test' }}
        isTestingConnection={true}
        testResult={undefined}
        {...mockHandlers}
      />
    )

    expect(screen.getByText('Testing...')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Testing/ })).toBeDisabled()
  })

  it('displays successful test results', () => {
    const successResult: TestResult = {
      success: true,
      message: 'Connection successful! Found 3 models.',
      timestamp: new Date().toISOString()
    }

    render(
      <ConfigurationPanel
        provider={mockProvider}
        configuration={{ id: 'openai', apiKey: 'sk-test' }}
        isTestingConnection={false}
        testResult={successResult}
        {...mockHandlers}
      />
    )

    expect(screen.getByText('Connection successful! Found 3 models.')).toBeInTheDocument()
    // Check for success icon
    expect(screen.getByRole('img', { hidden: true })).toHaveClass('h-4 w-4')
  })

  it('displays failed test results', () => {
    const failedResult: TestResult = {
      success: false,
      message: 'Connection failed: Invalid API key',
      timestamp: new Date().toISOString(),
      error: 'Invalid API key'
    }

    render(
      <ConfigurationPanel
        provider={mockProvider}
        configuration={{ id: 'openai', apiKey: 'sk-test' }}
        isTestingConnection={false}
        testResult={failedResult}
        {...mockHandlers}
      />
    )

    expect(screen.getByText('Connection failed: Invalid API key')).toBeInTheDocument()
  })

  it('disables buttons when form is invalid', async () => {
    render(
      <ConfigurationPanel
        provider={mockProvider}
        configuration={undefined}
        isTestingConnection={false}
        testResult={undefined}
        {...mockHandlers}
      />
    )

    // Initially, test button should be disabled (no API key)
    const testButton = screen.getByRole('button', { name: 'Test Connection' })
    expect(testButton).toBeDisabled()
  })

  it('updates form when provider changes', async () => {
    const { rerender } = render(
      <ConfigurationPanel
        provider={mockProvider}
        configuration={undefined}
        isTestingConnection={false}
        testResult={undefined}
        {...mockHandlers}
      />
    )

    // Change to a different provider
    const newProvider: ProviderInfo = {
      ...mockProvider,
      id: 'anthropic',
      name: 'Anthropic'
    }

    rerender(
      <ConfigurationPanel
        provider={newProvider}
        configuration={undefined}
        isTestingConnection={false}
        testResult={undefined}
        {...mockHandlers}
      />
    )

    expect(screen.getByText('Configure Anthropic')).toBeInTheDocument()
  })
})