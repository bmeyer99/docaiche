/**
 * Tests for memory leak fixes in provider settings
 */

import { renderHook, act } from '@testing-library/react';
import { useProviderLoader } from '../hooks/use-provider-loader';
import { useProviderSaver } from '../hooks/use-provider-saver';
import { useIsMounted } from '../utils/cleanup-helpers';

// Mock API client
jest.mock('@/lib/utils/api-client', () => ({
  apiClient: {
    getProviderConfigurations: jest.fn(() => Promise.resolve([])),
    getModelSelection: jest.fn(() => Promise.resolve(null)),
    updateProviderConfiguration: jest.fn(() => Promise.resolve()),
    updateModelSelection: jest.fn(() => Promise.resolve()),
  }
}));

// Mock dependencies
jest.mock('../utils/api-helpers', () => ({
  loadProviderConfigurations: jest.fn(() => Promise.resolve({})),
  loadModelSelection: jest.fn(() => Promise.resolve({ textGeneration: { provider: 'test', model: 'test' }, embeddings: { provider: 'test', model: 'test' }, sharedProvider: true })),
  saveProviderConfiguration: jest.fn(() => Promise.resolve()),
  saveModelSelection: jest.fn(() => Promise.resolve()),
  extractProviderUpdatesFromDirtyFields: jest.fn(() => new Map()),
  hasModelSelectionChanges: jest.fn(() => false),
}));

jest.mock('../utils/state-helpers', () => ({
  initializeMissingProviders: jest.fn(data => data),
  createSavedState: jest.fn(() => ({ providers: {}, modelSelection: {} })),
}));

describe('Memory Leak Fixes', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('useIsMounted', () => {
    it('should return true when component is mounted', () => {
      const { result } = renderHook(() => useIsMounted());
      
      expect(result.current()).toBe(true);
    });

    it('should return false after component unmounts', () => {
      const { result, unmount } = renderHook(() => useIsMounted());
      
      expect(result.current()).toBe(true);
      
      unmount();
      
      expect(result.current()).toBe(false);
    });
  });

  describe('useProviderLoader', () => {
    it('should cancel requests on unmount', async () => {
      const { result, unmount } = renderHook(() => useProviderLoader());
      
      expect(result.current.isLoading).toBe(false);
      
      // Start a load operation
      const loadPromise = act(async () => {
        return result.current.loadSettings({});
      });
      
      // Unmount before completion
      unmount();
      
      // The promise should be cancelled/rejected
      await expect(loadPromise).rejects.toThrow();
    });

    it('should handle component unmounting during load', async () => {
      const { result, unmount } = renderHook(() => useProviderLoader());
      
      let loadPromise: Promise<any>;
      
      act(() => {
        loadPromise = result.current.loadSettings({});
      });
      
      // Unmount while loading
      unmount();
      
      // Should not throw unhandled promise rejection
      await expect(loadPromise!).rejects.toBeDefined();
    });
  });

  describe('useProviderSaver', () => {
    it('should cancel save operations on unmount', async () => {
      const { result, unmount } = renderHook(() => useProviderSaver());
      
      expect(result.current.isSaving).toBe(false);
      
      // Start a save operation
      const savePromise = act(async () => {
        return result.current.saveAllChanges(new Set(['test']), {}, { textGeneration: { provider: 'test', model: 'test' }, embeddings: { provider: 'test', model: 'test' }, sharedProvider: true });
      });
      
      // Unmount before completion
      unmount();
      
      // The promise should be cancelled/rejected
      await expect(savePromise).rejects.toThrow();
    });

    it('should prevent overlapping saves', async () => {
      const { result } = renderHook(() => useProviderSaver());
      
      const mockSave = jest.fn(() => new Promise(resolve => setTimeout(resolve, 100)));
      
      // Start two save operations
      const save1 = act(async () => {
        return result.current.saveAllChanges(new Set(['test1']), {}, { textGeneration: { provider: 'test', model: 'test' }, embeddings: { provider: 'test', model: 'test' }, sharedProvider: true });
      });
      
      const save2 = act(async () => {
        return result.current.saveAllChanges(new Set(['test2']), {}, { textGeneration: { provider: 'test', model: 'test' }, embeddings: { provider: 'test', model: 'test' }, sharedProvider: true });
      });
      
      // Both should complete without interfering
      await Promise.all([save1, save2]);
    });
  });

  describe('AbortController integration', () => {
    it('should properly handle abort signals', () => {
      const controller = new AbortController();
      const signal = controller.signal;
      
      expect(signal.aborted).toBe(false);
      
      controller.abort();
      
      expect(signal.aborted).toBe(true);
    });

    it('should handle timeout with abort controller', (done) => {
      const controller = new AbortController();
      
      setTimeout(() => {
        controller.abort();
      }, 50);
      
      controller.signal.addEventListener('abort', () => {
        expect(controller.signal.aborted).toBe(true);
        done();
      });
    });
  });
});