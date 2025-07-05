/**
 * Integration tests for Search Configuration feature
 * 
 * These tests verify that both issues are fixed:
 * 1. No warnings during initial load
 * 2. No unsaved changes when switching tabs
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SearchConfigLayout } from '../index';
import { useApiClient } from '@/lib/hooks/use-api-client';
import { useProviderSettings, useModelSelection } from '@/lib/hooks/use-provider-settings';
import { useSearchConfig } from '../contexts/config-context';

// Mock the modules
jest.mock('@/lib/hooks/use-api-client');
jest.mock('@/lib/hooks/use-provider-settings');
jest.mock('../contexts/config-context');
jest.mock('@/hooks/use-toast', () => ({
  useToast: () => ({
    toast: jest.fn()
  })
}));

// Mock AI_PROVIDERS
jest.mock('@/lib/config/providers', () => ({
  AI_PROVIDERS: {
    openai: {
      id: 'openai',
      displayName: 'OpenAI',
      icon: '🤖',
      supportsChat: true,
      supportsEmbedding: true
    },
    ollama: {
      id: 'ollama',
      displayName: 'Ollama',
      icon: '🦙',
      supportsChat: true,
      supportsEmbedding: true
    }
  }
}));

// Mock the form hook with dynamic state
let mockFormState = {
  isDirty: false,
  saveForm: jest.fn(),
  resetForm: jest.fn()
};

jest.mock('../hooks/use-search-config-form', () => ({
  useSearchConfigForm: () => mockFormState
}));

// Mock child components to simplify testing
jest.mock('../components/system-prompts-manager', () => ({
  SystemPromptsManager: () => <div>System Prompts Manager</div>
}));

// Mock the config validator
jest.mock('@/lib/utils/config-validator', () => ({
  validateSearchConfig: jest.fn(() => ({
    isValid: true,
    errors: [],
    warnings: []
  }))
}));

// Mock data
const mockProviders = {
  openai: {
    status: 'tested',
    configured: true,
    models: ['gpt-4', 'gpt-3.5-turbo', 'text-embedding-ada-002']
  },
  ollama: {
    status: 'connected',
    configured: true,
    models: ['llama2', 'mistral', 'nomic-embed-text:latest']
  }
};

const mockModelSelection = {
  textGeneration: {
    provider: 'openai',
    model: 'gpt-4'
  },
  embedding: {
    provider: 'openai',
    model: 'text-embedding-ada-002'
  }
};

const mockVectorConfig = {
  enabled: true,
  base_url: 'http://localhost:8080'
};

const mockEmbeddingConfig = {
  provider: 'openai',
  model: 'text-embedding-ada-002'
};

const mockModelParameters = {
  openai: {
    'gpt-4': {
      temperature: 0.7,
      topP: 0.9,
      maxTokens: 2048,
      presencePenalty: 0,
      frequencyPenalty: 0
    }
  }
};

// Helper to setup mocks
const setupMocks = (overrides = {}) => {
  const mockApiClient = {
    getConfiguration: jest.fn().mockResolvedValue({
      items: [
        {
          key: 'ai.model_selection',
          value: mockModelSelection
        }
      ]
    }),
    getModelParameters: jest.fn().mockResolvedValue(mockModelParameters.openai['gpt-4']),
    updateModelParameters: jest.fn().mockResolvedValue({}),
    updateConfiguration: jest.fn().mockResolvedValue({}),
    ...overrides.apiClient
  };

  (useApiClient as jest.Mock).mockReturnValue(mockApiClient);

  (useProviderSettings as jest.Mock).mockReturnValue({
    providers: mockProviders,
    isLoading: false,
    ...overrides.providerSettings
  });

  (useModelSelection as jest.Mock).mockReturnValue({
    modelSelection: mockModelSelection,
    isLoading: false,
    updateModelSelection: jest.fn(),
    ...overrides.modelSelection
  });

  (useSearchConfig as jest.Mock).mockReturnValue({
    isLoading: false,
    loading: { loadError: null },
    vectorConfig: mockVectorConfig,
    embeddingConfig: mockEmbeddingConfig,
    modelParameters: mockModelParameters,
    updateModelParameters: jest.fn(),
    ...overrides.searchConfig
  });

  return { mockApiClient };
};

describe('SearchConfigLayout Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Reset form state
    mockFormState.isDirty = false;
    mockFormState.saveForm = jest.fn();
    mockFormState.resetForm = jest.fn();
  });

  describe('Issue 1: No warnings during initial load', () => {
    it('should show loading state while data is being loaded', async () => {
      setupMocks({
        providerSettings: { isLoading: true },
        searchConfig: { isLoading: true }
      });

      render(<SearchConfigLayout />);

      // Should show loading UI
      expect(screen.getByText('Loading configurations...')).toBeInTheDocument();
      
      // Should not show any validation warnings
      expect(screen.queryByText(/No AI providers configured/i)).not.toBeInTheDocument();
    });

    it('should not show validation warnings immediately after load', async () => {
      // Start with loading state
      const { rerender } = render(<SearchConfigLayout />);
      
      setupMocks({
        providerSettings: { isLoading: true },
        searchConfig: { isLoading: true }
      });

      rerender(<SearchConfigLayout />);

      // Now simulate data loaded
      setupMocks({
        providerSettings: { isLoading: false },
        searchConfig: { isLoading: false }
      });

      rerender(<SearchConfigLayout />);

      await waitFor(() => {
        // Should show the main content
        expect(screen.getByText('Search Configuration')).toBeInTheDocument();
        
        // Should not show any warnings about missing providers
        expect(screen.queryByText(/No AI providers configured/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/No providers available/i)).not.toBeInTheDocument();
      });
    });

    it('should show validation warnings only for real issues after data loads', async () => {
      // Setup with no providers configured
      setupMocks({
        providerSettings: {
          providers: {},
          isLoading: false
        },
        searchConfig: {
          isLoading: false
        }
      });

      render(<SearchConfigLayout />);

      await waitFor(() => {
        // Now it's appropriate to show the warning
        expect(screen.getByText(/No AI providers configured/i)).toBeInTheDocument();
      });
    });

    it('should properly validate when providers are configured', async () => {
      setupMocks();

      render(<SearchConfigLayout />);

      await waitFor(() => {
        // Should show content without warnings
        expect(screen.getByText('Search Configuration')).toBeInTheDocument();
        
        // Should show validation success message
        expect(screen.getByText(/Configuration is valid and complete/i)).toBeInTheDocument();
        
        // Should not show any provider warnings
        expect(screen.queryByText(/No AI providers configured/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('Issue 2: No unsaved changes when switching tabs', () => {
    it('should not show unsaved changes immediately after loading saved configuration', async () => {
      setupMocks();

      render(<SearchConfigLayout />);

      await waitFor(() => {
        // Should not show save/discard buttons initially
        expect(screen.queryByText('Save Changes')).not.toBeInTheDocument();
        expect(screen.queryByText('Discard')).not.toBeInTheDocument();
      });
    });

    it('should not trigger unsaved changes when switching tabs without modifications', async () => {
      setupMocks();
      const user = userEvent.setup();

      render(<SearchConfigLayout />);

      await waitFor(() => {
        expect(screen.getByText('Search Configuration')).toBeInTheDocument();
      });

      // Switch to Text AI tab
      const textAITab = screen.getByRole('tab', { name: /Text AI/i });
      await user.click(textAITab);

      // Should not show unsaved changes
      expect(screen.queryByText('Save Changes')).not.toBeInTheDocument();
      expect(screen.queryByText('Discard')).not.toBeInTheDocument();

      // Switch to Vector Search tab
      const vectorTab = screen.getByRole('tab', { name: /Vector Search/i });
      await user.click(vectorTab);

      // Still should not show unsaved changes
      expect(screen.queryByText('Save Changes')).not.toBeInTheDocument();
      expect(screen.queryByText('Discard')).not.toBeInTheDocument();
    });

    it('should show unsaved changes only when user makes actual modifications', async () => {
      setupMocks();
      const user = userEvent.setup();

      const { rerender } = render(<SearchConfigLayout />);

      await waitFor(() => {
        expect(screen.getByText('Search Configuration')).toBeInTheDocument();
      });

      // Navigate to Text AI tab
      const textAITab = screen.getByRole('tab', { name: /Text AI/i });
      await user.click(textAITab);

      // Simulate onChangeDetected being called - this would happen in the actual component
      // In the real app, changing the slider would trigger onChangeDetected callback
      expect(screen.getByRole('tabpanel', { name: /Text AI/i })).toBeInTheDocument();
      
      // Mock the change detection - in real app this happens through the onChangeDetected callback
      mockFormState.isDirty = true;
      
      // Force re-render to show save/discard buttons
      rerender(<SearchConfigLayout />);

      // Now should show unsaved changes
      await waitFor(() => {
        expect(screen.getByText('Save Changes')).toBeInTheDocument();
        expect(screen.getByText('Discard')).toBeInTheDocument();
      });
    });

    it('should not mark as dirty when loading saved values', async () => {
      const { mockApiClient } = setupMocks();

      render(<SearchConfigLayout />);

      await waitFor(() => {
        expect(screen.getByText('Search Configuration')).toBeInTheDocument();
      });

      // Verify API was called to load saved configuration
      expect(mockApiClient.getConfiguration).toHaveBeenCalled();

      // Should not show unsaved changes after loading saved values
      expect(screen.queryByText('Save Changes')).not.toBeInTheDocument();
      expect(screen.queryByText('Discard')).not.toBeInTheDocument();
    });

    it('should correctly detect changes when comparing with saved state', async () => {
      setupMocks();
      const user = userEvent.setup();

      render(<SearchConfigLayout />);

      await waitFor(() => {
        expect(screen.getByText('Search Configuration')).toBeInTheDocument();
      });

      // Go to Text AI tab
      const textAITab = screen.getByRole('tab', { name: /Text AI/i });
      await user.click(textAITab);

      // Change model selection
      const modelSelect = screen.getByRole('combobox', { name: /model/i });
      await user.click(modelSelect);
      
      const gpt35Option = screen.getByRole('option', { name: /gpt-3.5-turbo/i });
      await user.click(gpt35Option);

      // Should show unsaved changes
      await waitFor(() => {
        expect(screen.getByText('Save Changes')).toBeInTheDocument();
      });
    });

    it('should handle save and clear unsaved state', async () => {
      const { mockApiClient } = setupMocks();
      const user = userEvent.setup();

      const { rerender } = render(<SearchConfigLayout />);

      await waitFor(() => {
        expect(screen.getByText('Search Configuration')).toBeInTheDocument();
      });

      // Make a change
      const textAITab = screen.getByRole('tab', { name: /Text AI/i });
      await user.click(textAITab);

      // Simulate change detection
      mockFormState.isDirty = true;
      rerender(<SearchConfigLayout />);

      // Save changes
      const saveButton = await screen.findByText('Save Changes');
      
      // Mock the save operation to clear isDirty
      mockFormState.saveForm.mockImplementation(() => {
        mockFormState.isDirty = false;
        return Promise.resolve();
      });
      
      await user.click(saveButton);

      // Re-render after save
      rerender(<SearchConfigLayout />);

      await waitFor(() => {
        // Save API should be called
        expect(mockFormState.saveForm).toHaveBeenCalled();
        
        // Unsaved changes indicators should disappear
        expect(screen.queryByText('Save Changes')).not.toBeInTheDocument();
        expect(screen.queryByText('Discard')).not.toBeInTheDocument();
      });
    });

    it('should handle discard and reset to saved state', async () => {
      setupMocks();
      const user = userEvent.setup();

      const { rerender } = render(<SearchConfigLayout />);

      await waitFor(() => {
        expect(screen.getByText('Search Configuration')).toBeInTheDocument();
      });

      // Make a change
      const textAITab = screen.getByRole('tab', { name: /Text AI/i });
      await user.click(textAITab);

      // Simulate change detection
      mockFormState.isDirty = true;
      rerender(<SearchConfigLayout />);

      // Discard changes
      const discardButton = await screen.findByText('Discard');
      
      // Mock window.confirm
      window.confirm = jest.fn(() => true);
      
      // Mock the reset operation to clear isDirty
      mockFormState.resetForm.mockImplementation(() => {
        mockFormState.isDirty = false;
      });
      
      await user.click(discardButton);

      // Re-render after discard
      rerender(<SearchConfigLayout />);

      await waitFor(() => {
        // Confirm dialog should have been shown
        expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to discard all changes?');
        
        // Reset should have been called
        expect(mockFormState.resetForm).toHaveBeenCalled();
        
        // Unsaved changes indicators should disappear
        expect(screen.queryByText('Save Changes')).not.toBeInTheDocument();
        expect(screen.queryByText('Discard')).not.toBeInTheDocument();
      });
    });
  });

  describe('Loading states', () => {
    it('should show loading UI while any data is loading', async () => {
      setupMocks({
        searchConfig: { isLoading: true }
      });

      render(<SearchConfigLayout />);

      expect(screen.getByText('Loading configurations...')).toBeInTheDocument();
    });

    it('should show error state when loading fails', async () => {
      setupMocks({
        searchConfig: {
          isLoading: false,
          loading: { loadError: 'Failed to load configuration' }
        }
      });

      render(<SearchConfigLayout />);

      expect(screen.getByText('Failed to load configuration')).toBeInTheDocument();
      expect(screen.getByText('Retry')).toBeInTheDocument();
    });
  });

  describe('Tab navigation', () => {
    it('should prevent tab switching with unsaved changes unless confirmed', async () => {
      setupMocks();
      const user = userEvent.setup();

      const { rerender } = render(<SearchConfigLayout />);

      await waitFor(() => {
        expect(screen.getByText('Search Configuration')).toBeInTheDocument();
      });

      // Navigate to Text AI tab first
      const textAITab = screen.getByRole('tab', { name: /Text AI/i });
      await user.click(textAITab);

      // Simulate having unsaved changes
      mockFormState.isDirty = true;
      // Also set hasUnsavedChanges in the component state
      // This requires us to trigger the onChangeDetected callback
      rerender(<SearchConfigLayout />);

      // Try to switch tabs - should show confirm dialog
      window.confirm = jest.fn(() => false);
      
      const vectorTab = screen.getByRole('tab', { name: /Vector Search/i });
      await user.click(vectorTab);

      expect(window.confirm).toHaveBeenCalledWith('You have unsaved changes. Are you sure you want to switch tabs?');
      
      // Should still be on Text AI tab since we cancelled
      expect(screen.getByRole('tabpanel', { name: /Text AI/i })).toBeInTheDocument();
    });

    it('should allow tab switching with unsaved changes if confirmed', async () => {
      setupMocks();
      const user = userEvent.setup();

      const { rerender } = render(<SearchConfigLayout />);

      await waitFor(() => {
        expect(screen.getByText('Search Configuration')).toBeInTheDocument();
      });

      // Navigate to Text AI tab first
      const textAITab = screen.getByRole('tab', { name: /Text AI/i });
      await user.click(textAITab);

      // Simulate having unsaved changes
      mockFormState.isDirty = true;
      rerender(<SearchConfigLayout />);

      // Try to switch tabs - confirm this time
      window.confirm = jest.fn(() => true);
      
      const vectorTab = screen.getByRole('tab', { name: /Vector Search/i });
      await user.click(vectorTab);

      expect(window.confirm).toHaveBeenCalled();
      
      // Should now be on Vector Search tab
      await waitFor(() => {
        expect(screen.getByRole('tabpanel', { name: /Vector Search/i })).toBeInTheDocument();
      });
    });
  });
});