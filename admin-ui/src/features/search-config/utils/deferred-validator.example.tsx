/**
 * Example usage of the Deferred Validator
 * 
 * This example shows how to use the deferred validator in a component
 * to prevent false validation warnings during data loading.
 */

import React from 'react';
import { useDeferredValidation, hasRealValidationIssues } from './deferred-validator';
import { ConfigValidation } from '../components/config-validation';
import { useSearchConfig } from '../contexts/config-context';
import { useProviderSettings, useModelSelection } from '@/lib/hooks/use-provider-settings';

export function SearchConfigWithDeferredValidation() {
  const { 
    isLoading: configLoading, 
    vectorConfig, 
    embeddingConfig, 
    modelParameters 
  } = useSearchConfig();
  
  const { providers, isLoading: providersLoading } = useProviderSettings();
  const { modelSelection, isLoading: modelSelectionLoading } = useModelSelection();
  
  // Use deferred validation
  const validation = useDeferredValidation({
    vectorConfig,
    embeddingConfig,
    modelSelection,
    modelParameters,
    providers,
    isLoading: {
      providers: providersLoading,
      vectorConfig: configLoading,
      embeddingConfig: configLoading,
      modelSelection: modelSelectionLoading,
      modelParameters: configLoading
    }
  });

  // Example: Only show save button if there are real issues
  const canSave = !hasRealValidationIssues(validation);

  return (
    <div className="space-y-4">
      <h2>Search Configuration</h2>
      
      {/* Validation display - will show loading state instead of false warnings */}
      <ConfigValidation validation={validation} />
      
      {/* Save button example */}
      <button 
        disabled={!canSave}
        className={`px-4 py-2 rounded ${
          canSave ? 'bg-blue-500 text-white' : 'bg-gray-300 text-gray-500'
        }`}
      >
        Save Configuration
      </button>
      
      {/* Debug info (remove in production) */}
      <div className="text-xs text-gray-500">
        <p>Providers loading: {providersLoading ? 'Yes' : 'No'}</p>
        <p>Config loading: {configLoading ? 'Yes' : 'No'}</p>
        <p>Has real issues: {hasRealValidationIssues(validation) ? 'Yes' : 'No'}</p>
      </div>
    </div>
  );
}

/**
 * Example: Using the validator directly (non-React context)
 */
import { getDeferredValidator, DeferredValidator } from './deferred-validator';

export async function validateConfigManually() {
  const validator = getDeferredValidator();
  
  // Update loading states
  validator.updateLoadingState({
    providers: true,
    vectorConfig: true,
    embeddingConfig: true,
    modelSelection: true,
    modelParameters: true
  });
  
  // Start a validation request (will be queued)
  const validationPromise = validator.validate({
    vectorConfig: { enabled: true, base_url: 'http://localhost:8080' },
    embeddingConfig: { provider: 'openai', model: 'text-embedding-ada-002' },
    modelSelection: { textGeneration: { provider: 'openai', model: 'gpt-4' } },
    modelParameters: {},
    providers: {}
  });
  
  // Simulate data loading complete
  setTimeout(() => {
    validator.updateLoadingState({
      providers: false,
      vectorConfig: false,
      embeddingConfig: false,
      modelSelection: false,
      modelParameters: false
    });
  }, 1000);
  
  // Wait for validation result
  const result = await validationPromise;
  console.log('Validation result:', result);
}

/**
 * Example: Handling validation in a form
 */
export function ConfigForm() {
  const [formData, setFormData] = React.useState({
    provider: '',
    model: ''
  });
  
  const validator = React.useRef(getDeferredValidator());
  const [validation, setValidation] = React.useState(
    DeferredValidator.getLoadingResult()
  );
  
  // Validate on form change
  React.useEffect(() => {
    validator.current.validate({
      vectorConfig: {},
      embeddingConfig: {},
      modelSelection: {
        textGeneration: {
          provider: formData.provider,
          model: formData.model
        }
      },
      modelParameters: {},
      providers: {}
    }).then(setValidation);
  }, [formData]);
  
  return (
    <form className="space-y-4">
      <input
        type="text"
        value={formData.provider}
        onChange={(e) => setFormData(prev => ({ ...prev, provider: e.target.value }))}
        placeholder="Provider"
        className="border rounded px-2 py-1"
      />
      
      <input
        type="text"
        value={formData.model}
        onChange={(e) => setFormData(prev => ({ ...prev, model: e.target.value }))}
        placeholder="Model"
        className="border rounded px-2 py-1"
      />
      
      {validation.errors.length > 0 && (
        <div className="text-red-500">
          {validation.errors.map((error, i) => (
            <p key={i}>{error.message}</p>
          ))}
        </div>
      )}
    </form>
  );
}