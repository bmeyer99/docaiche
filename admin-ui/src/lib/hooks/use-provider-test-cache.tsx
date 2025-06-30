/**
 * Provider Test Cache Hook
 * Manages tested provider configurations and discovered models
 * This provides a shared state between provider configuration and model selection
 */

import { createContext, useContext, useCallback, useState, ReactNode } from 'react';

export interface TestedProvider {
  id: string;
  status: 'tested' | 'testing' | 'failed' | 'untested';
  models: string[];
  lastTested: Date;
  config: {
    base_url?: string;
    api_key?: string;
    [key: string]: any;
  };
  error?: string;
}

interface ProviderTestContextValue {
  testedProviders: Record<string, TestedProvider>;
  
  // Actions
  setProviderTesting: (providerId: string, config: TestedProvider['config']) => void;
  setProviderTested: (providerId: string, models: string[], config: TestedProvider['config']) => void;
  setProviderFailed: (providerId: string, error: string, config: TestedProvider['config']) => void;
  clearProvider: (providerId: string) => void;
  isProviderTested: (providerId: string) => boolean;
  getProviderModels: (providerId: string) => string[];
  getProviderStatus: (providerId: string) => TestedProvider['status'];
}

const ProviderTestContext = createContext<ProviderTestContextValue | null>(null);

export function ProviderTestProvider({ children }: { children: ReactNode }) {
  const [testedProviders, setTestedProviders] = useState<Record<string, TestedProvider>>({});

  const setProviderTesting = useCallback((providerId: string, config: TestedProvider['config']) => {
    setTestedProviders(prev => ({
      ...prev,
      [providerId]: {
        id: providerId,
        status: 'testing',
        models: [],
        lastTested: new Date(),
        config,
      },
    }));
  }, []);

  const setProviderTested = useCallback((providerId: string, models: string[], config: TestedProvider['config']) => {
    setTestedProviders(prev => ({
      ...prev,
      [providerId]: {
        id: providerId,
        status: 'tested',
        models,
        lastTested: new Date(),
        config,
        error: undefined,
      },
    }));
  }, []);

  const setProviderFailed = useCallback((providerId: string, error: string, config: TestedProvider['config']) => {
    setTestedProviders(prev => ({
      ...prev,
      [providerId]: {
        id: providerId,
        status: 'failed',
        models: [],
        lastTested: new Date(),
        config,
        error,
      },
    }));
  }, []);

  const clearProvider = useCallback((providerId: string) => {
    setTestedProviders(prev => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { [providerId]: _removed, ...rest } = prev;
      return rest;
    });
  }, []);

  const isProviderTested = useCallback((providerId: string) => {
    const provider = testedProviders[providerId];
    return provider?.status === 'tested';
  }, [testedProviders]);

  const getProviderModels = useCallback((providerId: string) => {
    const provider = testedProviders[providerId];
    return provider?.models || [];
  }, [testedProviders]);

  const getProviderStatus = useCallback((providerId: string) => {
    const provider = testedProviders[providerId];
    return provider?.status || 'untested';
  }, [testedProviders]);

  const value: ProviderTestContextValue = {
    testedProviders,
    setProviderTesting,
    setProviderTested,
    setProviderFailed,
    clearProvider,
    isProviderTested,
    getProviderModels,
    getProviderStatus,
  };

  return (
    <ProviderTestContext.Provider value={value}>
      {children}
    </ProviderTestContext.Provider>
  );
}

export function useProviderTestCache(): ProviderTestContextValue {
  const context = useContext(ProviderTestContext);
  if (!context) {
    throw new Error('useProviderTestCache must be used within a ProviderTestProvider');
  }
  return context;
}

/**
 * Hook to test a provider connection
 * This is a convenience wrapper that integrates with the API client
 */
export function useProviderConnectionTest() {
  const { setProviderTesting, setProviderTested, setProviderFailed } = useProviderTestCache();
  
  const testProviderConnection = useCallback(async (
    providerId: string, 
    config: Record<string, any>
  ): Promise<{ success: boolean; models?: string[]; error?: string }> => {
    // Lazy import to avoid circular dependencies
    const { apiClient } = await import('../utils/api-client');
    
    setProviderTesting(providerId, config);
    
    try {
      const result = await apiClient.testProviderConnection(providerId, config);
      
      if (result.success && result.models) {
        setProviderTested(providerId, result.models, config);
        return { success: true, models: result.models };
      } else {
        const error = result.message || 'Connection failed';
        setProviderFailed(providerId, error, config);
        return { success: false, error };
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setProviderFailed(providerId, errorMessage, config);
      return { success: false, error: errorMessage };
    }
  }, [setProviderTesting, setProviderTested, setProviderFailed]);
  
  return { testProviderConnection };
}