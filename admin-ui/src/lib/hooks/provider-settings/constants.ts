/**
 * Constants for the provider settings system
 */

import type { ModelSelection } from './types';

export const DEFAULT_MODEL_SELECTION = {
  textGeneration: { provider: 'ollama', model: '' } as ModelSelection,
  embeddings: { provider: 'ollama', model: '' } as ModelSelection,
  sharedProvider: true,
};

export const FIELD_PATH_PREFIXES = {
  PROVIDER: 'provider.',
  MODEL_SELECTION: 'modelSelection.',
} as const;

export const PROVIDER_STATUS = {
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  TESTING: 'testing',
  ERROR: 'error',
} as const;

export type ProviderStatus = typeof PROVIDER_STATUS[keyof typeof PROVIDER_STATUS];