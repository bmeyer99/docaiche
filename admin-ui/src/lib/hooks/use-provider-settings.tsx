/**
 * Legacy export file for backward compatibility
 * All functionality has been moved to the provider-settings module
 */

export {
  ProviderSettingsProvider,
  useProviderSettings,
  useProviderConfig,
  useModelSelection,
} from './provider-settings';

export type {
  ModelSelection,
  ProviderSettings,
  ProviderSettingsContextValue,
  ProviderConfigHookReturn,
  ModelSelectionHookReturn,
} from './provider-settings';