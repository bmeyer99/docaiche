/**
 * Provider State Slice
 * Manages AI provider configurations, testing, and model selection
 */

import { StateCreator } from 'zustand';
import { ProviderConfiguration, ModelSelection } from '../types';

export interface ProviderState {
  providers: {
    configurations: Record<string, ProviderConfiguration>;
    modelSelection: ModelSelection;
    loading: boolean;
    error: string | null;
  };
}

export interface ProviderActions {
  // Provider configuration actions
  setProviderConfiguration: (providerId: string, config: Partial<ProviderConfiguration>) => void;
  setProviderConfigurations: (configurations: Record<string, ProviderConfiguration>) => void;
  
  // Provider testing actions
  setProviderTesting: (providerId: string) => void;
  setProviderTestResults: (
    providerId: string, 
    success: boolean, 
    models: string[], 
    error?: string
  ) => void;
  updateProviderTestStatus: (
    providerId: string, 
    status: ProviderConfiguration['testStatus']
  ) => void;
  
  // Model selection actions
  updateModelSelection: (selection: Partial<ModelSelection>) => void;
  setModelForProvider: (
    section: 'textGeneration' | 'embeddings',
    provider: string,
    model: string
  ) => void;
  toggleSharedProvider: (enabled: boolean) => void;
  
  // Loading and error states
  setProvidersLoading: (loading: boolean) => void;
  setProvidersError: (error: string | null) => void;
  
  // Computed selectors
  getConfiguredProviders: () => ProviderConfiguration[];
  getTestedProviders: () => ProviderConfiguration[];
  getProviderModels: (providerId: string) => string[];
  isProviderTested: (providerId: string) => boolean;
}

export type ProviderSlice = ProviderState & ProviderActions;

// Default state
const defaultModelSelection: ModelSelection = {
  textGeneration: { provider: '', model: '' },
  embeddings: { provider: '', model: '' },
  sharedProvider: false,
};

const defaultProviderState: ProviderState['providers'] = {
  configurations: {},
  modelSelection: defaultModelSelection,
  loading: false,
  error: null,
};

export const createProviderSlice: StateCreator<
  ProviderSlice,
  [["zustand/immer", never]],
  [],
  ProviderSlice
> = (set, get) => ({
  providers: defaultProviderState,

  // Provider configuration actions
  setProviderConfiguration: (providerId, config) =>
    set((state) => {
      if (!state.providers.configurations[providerId]) {
        state.providers.configurations[providerId] = {
          id: providerId,
          name: '',
          type: '',
          enabled: false,
          configured: false,
          config: {},
          testStatus: 'untested',
        };
      }
      Object.assign(state.providers.configurations[providerId], config);
    }),

  setProviderConfigurations: (configurations) =>
    set((state) => {
      state.providers.configurations = configurations;
    }),

  // Provider testing actions
  setProviderTesting: (providerId) =>
    set((state) => {
      if (state.providers.configurations[providerId]) {
        state.providers.configurations[providerId].testStatus = 'testing';
        // Clear previous test results
        if (state.providers.configurations[providerId].testResults) {
          delete state.providers.configurations[providerId].testResults;
        }
      }
    }),

  setProviderTestResults: (providerId, success, models, error) =>
    set((state) => {
      if (state.providers.configurations[providerId]) {
        const provider = state.providers.configurations[providerId];
        provider.testStatus = success ? 'tested' : 'failed';
        provider.testResults = {
          lastTested: new Date(),
          success,
          models,
          error,
        };
      }
    }),

  updateProviderTestStatus: (providerId, status) =>
    set((state) => {
      if (state.providers.configurations[providerId]) {
        state.providers.configurations[providerId].testStatus = status;
      }
    }),

  // Model selection actions
  updateModelSelection: (selection) =>
    set((state) => {
      Object.assign(state.providers.modelSelection, selection);
    }),

  setModelForProvider: (section, provider, model) =>
    set((state) => {
      state.providers.modelSelection[section] = { provider, model };
      
      // If shared provider is enabled, sync both sections
      if (state.providers.modelSelection.sharedProvider && section === 'textGeneration') {
        state.providers.modelSelection.embeddings = { provider, model };
      }
    }),

  toggleSharedProvider: (enabled) =>
    set((state) => {
      state.providers.modelSelection.sharedProvider = enabled;
      
      // If enabling shared provider, copy text generation to embeddings
      if (enabled) {
        state.providers.modelSelection.embeddings = {
          ...state.providers.modelSelection.textGeneration,
        };
      }
    }),

  // Loading and error states
  setProvidersLoading: (loading) =>
    set((state) => {
      state.providers.loading = loading;
    }),

  setProvidersError: (error) =>
    set((state) => {
      state.providers.error = error;
    }),

  // Computed selectors
  getConfiguredProviders: () => {
    const state = get();
    return Object.values(state.providers.configurations).filter(
      (provider) => provider.configured
    );
  },

  getTestedProviders: () => {
    const state = get();
    return Object.values(state.providers.configurations).filter(
      (provider) => provider.testStatus === 'tested'
    );
  },

  getProviderModels: (providerId) => {
    const state = get();
    const provider = state.providers.configurations[providerId];
    return provider?.testResults?.models || [];
  },

  isProviderTested: (providerId) => {
    const state = get();
    const provider = state.providers.configurations[providerId];
    return provider?.testStatus === 'tested';
  },
});