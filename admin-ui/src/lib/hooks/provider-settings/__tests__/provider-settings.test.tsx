/**
 * Tests for the provider settings system
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useProviderSettings, useProviderConfig, useModelSelection } from '../index';
import { TestWrapper, mockProviderConfig, mockModelSelection } from './test-utils';
import { apiClient } from '@/lib/utils/api-client';

// Mock the API client
jest.mock('@/lib/utils/api-client', () => ({
  apiClient: {
    getProviderConfigurations: jest.fn(),
    getModelSelection: jest.fn(),
    updateProviderConfiguration: jest.fn(),
    updateModelSelection: jest.fn(),
  },
}));

describe('Provider Settings System', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (apiClient.getProviderConfigurations as jest.Mock).mockResolvedValue([mockProviderConfig]);
    (apiClient.getModelSelection as jest.Mock).mockResolvedValue(mockModelSelection);
  });

  describe('useProviderSettings', () => {
    it('should load settings on mount', async () => {
      const { result } = renderHook(() => useProviderSettings(), {
        wrapper: TestWrapper,
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.providers.ollama).toBeDefined();
      expect(result.current.modelSelection).toEqual(mockModelSelection);
    });

    it('should track dirty fields when updating provider', async () => {
      const { result } = renderHook(() => useProviderSettings(), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      act(() => {
        result.current.updateProvider('ollama', { apiUrl: 'http://localhost:8080' });
      });

      expect(result.current.hasUnsavedChanges()).toBe(true);
      expect(result.current.isFieldDirty('provider.ollama.apiUrl')).toBe(true);
    });

    it('should save all changes', async () => {
      const { result } = renderHook(() => useProviderSettings(), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      act(() => {
        result.current.updateProvider('ollama', { apiUrl: 'http://localhost:8080' });
      });

      await act(async () => {
        await result.current.saveAllChanges();
      });

      expect(apiClient.updateProviderConfiguration).toHaveBeenCalledWith('ollama', {
        config: { apiUrl: 'http://localhost:8080' },
      });
      expect(result.current.hasUnsavedChanges()).toBe(false);
    });

    it('should reset to saved state', async () => {
      const { result } = renderHook(() => useProviderSettings(), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const originalApiUrl = result.current.providers.ollama.config.apiUrl;

      act(() => {
        result.current.updateProvider('ollama', { apiUrl: 'http://localhost:8080' });
      });

      expect(result.current.providers.ollama.config.apiUrl).toBe('http://localhost:8080');

      act(() => {
        result.current.resetToSaved();
      });

      expect(result.current.providers.ollama.config.apiUrl).toBe(originalApiUrl);
      expect(result.current.hasUnsavedChanges()).toBe(false);
    });
  });

  describe('useProviderConfig', () => {
    it('should return provider configuration and update function', async () => {
      const { result } = renderHook(() => useProviderConfig('ollama'), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.provider).toBeDefined();
      });

      expect(result.current.provider?.id).toBe('ollama');
      expect(result.current.isDirty).toBe(false);

      act(() => {
        result.current.updateConfig({ apiUrl: 'http://localhost:8080' });
      });

      expect(result.current.isDirty).toBe(true);
    });
  });

  describe('useModelSelection', () => {
    it('should return model selection and update function', async () => {
      const { result } = renderHook(() => useModelSelection(), {
        wrapper: TestWrapper,
      });

      await waitFor(() => {
        expect(result.current.modelSelection).toBeDefined();
      });

      expect(result.current.modelSelection).toEqual(mockModelSelection);
      expect(result.current.isDirty).toBe(false);

      act(() => {
        result.current.updateModelSelection({
          textGeneration: { provider: 'openai', model: 'gpt-4' },
        });
      });

      expect(result.current.isDirty).toBe(true);
      expect(result.current.modelSelection.textGeneration.provider).toBe('openai');
    });
  });
});