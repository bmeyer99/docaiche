// useFormState.ts
import { useState, useCallback } from 'react';
import type { SystemConfiguration } from '../types/configuration';
import { Logger } from '../utils/logger';

type ValidationResult = {
  isValid: boolean;
  errors: Record<string, string>;
};

interface UseFormStateOptions {
  correlationId: string;
  validate: (config: SystemConfiguration) => ValidationResult;
}

export function useFormState(
  initialConfig: SystemConfiguration,
  options: UseFormStateOptions
) {
  const { correlationId, validate } = options;
  const [currentConfig, setCurrentConfig] = useState<SystemConfiguration>(
    JSON.parse(JSON.stringify(initialConfig))
  );
  const [validation, setValidation] = useState<ValidationResult>(
    validate(initialConfig)
  );

  // Deep equality check (performs well for config objects)
  const deepEqual = useCallback((a: any, b: any): boolean => {
    if (a === b) return true;
    if (typeof a !== typeof b) return false;
    if (typeof a !== 'object' || a === null || b === null) return false;
    if (Array.isArray(a) !== Array.isArray(b)) return false;
    if (Array.isArray(a)) {
      if (a.length !== b.length) return false;
      for (let i = 0; i < a.length; i++) {
        if (!deepEqual(a[i], b[i])) return false;
      }
      return true;
    }
    const aKeys = Object.keys(a);
    const bKeys = Object.keys(b);
    if (aKeys.length !== bKeys.length) return false;
    for (const key of aKeys) {
      if (!bKeys.includes(key)) return false;
      if (!deepEqual(a[key], b[key])) return false;
    }
    return true;
  }, []);

  const isDirty = !deepEqual(initialConfig, currentConfig);

  // Log dirty state transitions
  if (isDirty) {
    Logger.info('Form dirty', {
      category: 'state',
      correlationId,
      redactKeys: ['apiKey'],
      action: 'form_dirty',
      currentConfig,
    });
  }

  // Update config and revalidate
  const updateConfig = useCallback(
    (updater: (prev: SystemConfiguration) => SystemConfiguration) => {
      setCurrentConfig(prev => {
        const updated = updater(prev);
        const result = validate(updated);
        setValidation(result);
        Logger.debug('Config updated', {
          category: 'state',
          correlationId,
          redactKeys: ['apiKey'],
          action: 'update_config',
          updatedConfig: updated,
          validation: result,
        });
        return updated;
      });
    },
    [validate, correlationId]
  );

  // Reset config to initial
  const resetConfig = useCallback(() => {
    setCurrentConfig(JSON.parse(JSON.stringify(initialConfig)));
    setValidation(validate(initialConfig));
    Logger.info('Revert changes', {
      category: 'state',
      correlationId,
      redactKeys: ['apiKey'],
      action: 'revert_changes',
      revertedTo: initialConfig,
    });
  }, [initialConfig, validate, correlationId]);

  return {
    currentConfig,
    setCurrentConfig: updateConfig,
    isDirty,
    validation,
    resetConfig,
  };
}