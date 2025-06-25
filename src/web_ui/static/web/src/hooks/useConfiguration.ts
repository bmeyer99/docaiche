// useConfiguration.ts
import { useState, useEffect, useCallback } from 'react';
import { SystemConfiguration } from '../types/configuration';
import { Logger } from '../utils/logger';
import { useFormState } from './useFormState';
import * as configurationApi from '../services/configurationApi';

const FALLBACK_DEFAULTS: SystemConfiguration = {
  textGeneration: {
    provider: 'openai',
    baseUrl: '',
    apiKey: '',
    model: '',
    settings: {
      temperature: 0,
      maxTokens: 0,
    },
  },
  embedding: {
    use_text_generation_config: false,
    provider: 'openai',
    baseUrl: '',
    apiKey: '',
    model: '',
  },
};

interface UseConfigurationOptions {
  correlationId: string;
  validate: (config: SystemConfiguration) => { isValid: boolean; errors: Record<string, string> };
  notifyFallback: () => void;
}

export function useConfiguration(options: UseConfigurationOptions) {
  const {
    correlationId,
    validate,
    notifyFallback,
  } = options;

  const [initialConfig, setInitialConfig] = useState<SystemConfiguration | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [csrfToken, setCsrfToken] = useState<string>('');
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'success' | 'error'>('idle');
  const [saveError, setSaveError] = useState<string | null>(null);

  // Fetch config and CSRF token on mount
  useEffect(() => {
    let active = true;
    setLoading(true);
    configurationApi.fetchConfiguration()
      .then(cfg => {
        if (!active) return;
        setInitialConfig(cfg);
        setLoading(false);
        Logger.info('Loaded configuration', {
          category: 'api',
          correlationId,
          redactKeys: ['apiKey'],
          action: 'load_config',
          loadedConfig: cfg,
        });
      })
      .catch(err => {
        if (!active) return;
        setInitialConfig(FALLBACK_DEFAULTS);
        setLoading(false);
        setLoadError('Failed to load configuration. Using fallback defaults.');
        notifyFallback();
        Logger.warn('Failed to load config, using fallback', {
          category: 'api',
          correlationId,
          redactKeys: ['apiKey'],
          action: 'fallback_defaults',
          error: err?.message || String(err),
        });
      });
    // Simulate CSRF token fetch (replace with real API if needed)
    setCsrfToken('csrf-token-placeholder');
    return () => {
      active = false;
    };
  }, [correlationId, notifyFallback]);

  // Use form state management
  const form = useFormState(
    initialConfig || FALLBACK_DEFAULTS,
    { correlationId, validate }
  );

  // Save configuration
  const saveConfiguration = useCallback(async () => {
    Logger.info('Save attempt', {
      category: 'user',
      correlationId,
      redactKeys: ['apiKey'],
      action: 'save_attempt',
      config: form.currentConfig,
    });
    setSaveState('saving');
    setSaveError(null);
    const validation = validate(form.currentConfig);
    if (!validation.isValid) {
      setSaveState('error');
      setSaveError('Validation failed');
      Logger.warn('Save failed: validation error', {
        category: 'validation',
        correlationId,
        redactKeys: ['apiKey'],
        action: 'save_failure',
        errors: validation.errors,
      });
      return false;
    }
    try {
      await configurationApi.saveConfiguration(form.currentConfig, csrfToken);
      setInitialConfig(form.currentConfig);
      setSaveState('success');
      Logger.info('Save success', {
        category: 'user',
        correlationId,
        redactKeys: ['apiKey'],
        action: 'save_success',
        savedConfig: form.currentConfig,
      });
      return true;
    } catch (err: any) {
      setSaveState('error');
      setSaveError(err?.message || 'Failed to save configuration');
      Logger.error('Save failed: API error', {
        category: 'api',
        correlationId,
        redactKeys: ['apiKey'],
        action: 'save_failure',
        error: err?.message || String(err),
      });
      return false;
    }
  }, [form.currentConfig, csrfToken, validate, correlationId]);

  // Revert changes
  const revertChanges = useCallback(() => {
    form.resetConfig();
    Logger.info('Revert changes', {
      category: 'user',
      correlationId,
      redactKeys: ['apiKey'],
      action: 'revert_changes',
      revertedTo: initialConfig,
    });
  }, [form, correlationId, initialConfig]);

  return {
    ...form,
    loading,
    loadError,
    saveState,
    saveError,
    saveConfiguration,
    revertChanges,
    initialConfig,
  };
}