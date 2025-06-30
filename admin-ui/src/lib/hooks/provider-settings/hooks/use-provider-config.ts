/**
 * Hook to get a specific provider's configuration
 */

import { useCallback, useContext } from 'react';
import { ProviderSettingsContext } from '../context';
import { ProviderConfiguration } from '@/lib/config/providers';
import type { ProviderConfigHookReturn } from '../types';

export function useProviderConfig(providerId: string): ProviderConfigHookReturn {
  const context = useContext(ProviderSettingsContext);
  
  if (!context) {
    throw new Error('useProviderConfig must be used within a ProviderSettingsProvider');
  }
  
  const { providers, updateProvider, dirtyFields } = context;
  
  const provider = providers[providerId];
  const isDirty = Array.from(dirtyFields).some(field => field.startsWith(`provider.${providerId}.`));
  
  const updateConfig = useCallback((config: Partial<ProviderConfiguration['config']>) => {
    updateProvider(providerId, config);
  }, [providerId, updateProvider]);
  
  return { provider, updateConfig, isDirty };
}