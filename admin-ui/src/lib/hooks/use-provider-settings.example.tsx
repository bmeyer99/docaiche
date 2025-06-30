/**
 * Example usage of the Provider Settings Context
 * This demonstrates how to use the centralized provider settings management
 */

import React from 'react';
import { 
  useProviderSettings, 
  useProviderConfig, 
  useModelSelection 
} from './use-provider-settings';
import { useProviderConnectionTest } from './use-provider-test-cache';

/**
 * Example: Provider Configuration Component
 */
export function ProviderConfigExample({ providerId }: { providerId: string }) {
  const { provider, updateConfig, isDirty } = useProviderConfig(providerId);
  const { testProviderConnection } = useProviderConnectionTest();
  const { saveAllChanges, hasUnsavedChanges } = useProviderSettings();
  
  if (!provider) {
    return <div>Provider not found</div>;
  }
  
  const handleApiKeyChange = (apiKey: string) => {
    // Update only the API key - automatically tracked as dirty
    updateConfig({ api_key: apiKey });
  };
  
  const handleBaseUrlChange = (baseUrl: string) => {
    // Update only the base URL - automatically tracked as dirty
    updateConfig({ base_url: baseUrl });
  };
  
  const handleTestConnection = async () => {
    // Test connection updates the test cache automatically
    await testProviderConnection(providerId, provider.config);
  };
  
  const handleSave = async () => {
    try {
      // Save all changes across all providers and settings
      await saveAllChanges();
      alert('Settings saved successfully!');
    } catch (error) {
      alert('Failed to save settings');
    }
  };
  
  return (
    <div>
      <h3>{provider.name}</h3>
      
      <input
        type="text"
        value={provider.config.base_url || ''}
        onChange={(e) => handleBaseUrlChange(e.target.value)}
        placeholder="Base URL"
      />
      
      <input
        type="password"
        value={provider.config.api_key || ''}
        onChange={(e) => handleApiKeyChange(e.target.value)}
        placeholder="API Key"
      />
      
      <button onClick={handleTestConnection}>
        Test Connection
      </button>
      
      {isDirty && <span>Unsaved changes</span>}
      
      {hasUnsavedChanges() && (
        <button onClick={handleSave}>
          Save All Changes
        </button>
      )}
    </div>
  );
}

/**
 * Example: Model Selection Component
 */
export function ModelSelectionExample() {
  const { modelSelection, updateModelSelection, isDirty } = useModelSelection();
  const { providers, saveAllChanges, resetToSaved } = useProviderSettings();
  
  const handleProviderChange = (type: 'textGeneration' | 'embeddings', providerId: string) => {
    updateModelSelection({
      [type]: {
        provider: providerId,
        model: '', // Reset model when provider changes
      },
    });
  };
  
  const handleModelChange = (type: 'textGeneration' | 'embeddings', model: string) => {
    updateModelSelection({
      [type]: {
        ...modelSelection[type],
        model,
      },
    });
  };
  
  const handleSharedProviderToggle = () => {
    updateModelSelection({
      sharedProvider: !modelSelection.sharedProvider,
      // If enabling shared provider, sync embeddings to text generation
      ...((!modelSelection.sharedProvider) ? {
        embeddings: { ...modelSelection.textGeneration }
      } : {}),
    });
  };
  
  return (
    <div>
      <h3>Model Selection</h3>
      
      <label>
        <input
          type="checkbox"
          checked={modelSelection.sharedProvider}
          onChange={handleSharedProviderToggle}
        />
        Use same provider for text and embeddings
      </label>
      
      <div>
        <h4>Text Generation</h4>
        <select
          value={modelSelection.textGeneration.provider}
          onChange={(e) => handleProviderChange('textGeneration', e.target.value)}
        >
          {Object.values(providers).map(provider => (
            <option key={provider.id} value={provider.id}>
              {provider.name}
            </option>
          ))}
        </select>
        
        <select
          value={modelSelection.textGeneration.model}
          onChange={(e) => handleModelChange('textGeneration', e.target.value)}
        >
          <option value="">Select a model</option>
          {providers[modelSelection.textGeneration.provider]?.models.map(model => (
            <option key={model} value={model}>
              {model}
            </option>
          ))}
        </select>
      </div>
      
      {!modelSelection.sharedProvider && (
        <div>
          <h4>Embeddings</h4>
          <select
            value={modelSelection.embeddings.provider}
            onChange={(e) => handleProviderChange('embeddings', e.target.value)}
          >
            {Object.values(providers).filter(p => p.models.length > 0).map(provider => (
              <option key={provider.id} value={provider.id}>
                {provider.name}
              </option>
            ))}
          </select>
          
          <select
            value={modelSelection.embeddings.model}
            onChange={(e) => handleModelChange('embeddings', e.target.value)}
          >
            <option value="">Select a model</option>
            {providers[modelSelection.embeddings.provider]?.models.map(model => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        </div>
      )}
      
      {isDirty && (
        <div>
          <span>Unsaved changes</span>
          <button onClick={() => saveAllChanges()}>Save</button>
          <button onClick={() => resetToSaved()}>Cancel</button>
        </div>
      )}
    </div>
  );
}

/**
 * Example: Dashboard showing all provider states
 */
export function ProvidersDashboardExample() {
  const {
    providers,
    isLoading,
    loadError,
    isSaving,
    saveError,
    hasUnsavedChanges,
    saveAllChanges,
    resetToSaved,
    loadSettings,
  } = useProviderSettings();
  
  if (isLoading) {
    return <div>Loading provider settings...</div>;
  }
  
  if (loadError) {
    return (
      <div>
        <p>Error loading settings: {loadError}</p>
        <button onClick={loadSettings}>Retry</button>
      </div>
    );
  }
  
  return (
    <div>
      <h2>Provider Settings</h2>
      
      {saveError && (
        <div style={{ color: 'red' }}>
          Save failed: {saveError}
        </div>
      )}
      
      <div>
        {Object.values(providers).map(provider => (
          <ProviderConfigExample key={provider.id} providerId={provider.id} />
        ))}
      </div>
      
      <ModelSelectionExample />
      
      {hasUnsavedChanges() && (
        <div style={{ 
          position: 'fixed', 
          bottom: 20, 
          right: 20, 
          background: 'white', 
          padding: '10px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
        }}>
          <span>You have unsaved changes</span>
          <button onClick={saveAllChanges} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save All'}
          </button>
          <button onClick={resetToSaved} disabled={isSaving}>
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}