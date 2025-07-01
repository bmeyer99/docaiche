/**
 * Test utilities for provider settings tests
 */

import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { ProviderSettingsProvider } from '../context';
import { ApiClientProvider } from '@/components/providers/api-client-provider';

interface TestWrapperProps {
  children: React.ReactNode;
}

export function TestWrapper({ children }: TestWrapperProps) {
  return (
    <ApiClientProvider>
      <ProviderSettingsProvider>
        {children}
      </ProviderSettingsProvider>
    </ApiClientProvider>
  );
}

export function renderWithProviders(
  ui: React.ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, { wrapper: TestWrapper, ...options });
}

export const mockProviderConfig = {
  id: 'ollama',
  providerId: 'ollama',
  name: 'Ollama',
  enabled: true,
  config: {
    apiUrl: 'http://localhost:11434',
  },
  status: 'connected' as const,
  models: ['llama2', 'mistral'],
};

export const mockModelSelection = {
  textGeneration: { provider: 'ollama', model: 'llama2' },
  embeddings: { provider: 'ollama', model: 'llama2' },
  sharedProvider: true,
};