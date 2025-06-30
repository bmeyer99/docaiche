/**
 * Hook to manage model selection with dirty tracking
 */

import { useContext } from 'react';
import { ProviderSettingsContext } from '../context';
import type { ModelSelectionHookReturn } from '../types';

export function useModelSelection(): ModelSelectionHookReturn {
  const context = useContext(ProviderSettingsContext);
  
  if (!context) {
    throw new Error('useModelSelection must be used within a ProviderSettingsProvider');
  }
  
  const { modelSelection, updateModelSelection, isFieldDirty } = context;
  
  const isDirty = isFieldDirty('modelSelection.textGeneration') || 
                  isFieldDirty('modelSelection.embeddings') || 
                  isFieldDirty('modelSelection.sharedProvider');
  
  return {
    modelSelection,
    updateModelSelection,
    isDirty,
  };
}