/**
 * Main hook to use the provider settings context
 */

import { useContext } from 'react';
import { ProviderSettingsContext } from '../context';
import type { ProviderSettingsContextValue } from '../types';

export function useProviderSettings(): ProviderSettingsContextValue {
  const context = useContext(ProviderSettingsContext);
  if (!context) {
    throw new Error('useProviderSettings must be used within a ProviderSettingsProvider');
  }
  return context;
}