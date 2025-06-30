# Provider Settings Context

The Provider Settings Context provides centralized management for all AI provider configurations and settings in the Docaiche admin interface.

## Features

- **Centralized State Management**: All provider configurations stored in one place
- **Dirty State Tracking**: Automatically tracks which fields have been modified
- **Batch Updates**: Save all changes across providers in a single operation
- **Integration with Test Cache**: Seamlessly works with the ProviderTestCache for connection testing
- **Optimistic Updates**: UI updates immediately while saving in the background
- **Error Handling**: Comprehensive error handling for load and save operations

## Setup

The context providers are already configured in the main providers wrapper:

```tsx
// Already set up in /components/layout/providers.tsx
<ProviderTestProvider>
  <ProviderSettingsProvider>
    {children}
  </ProviderSettingsProvider>
</ProviderTestProvider>
```

## Basic Usage

### 1. Access All Provider Settings

```tsx
import { useProviderSettings } from '@/lib/hooks/use-provider-settings';

function MyComponent() {
  const {
    providers,           // All provider configurations
    modelSelection,      // Current model selections
    isLoading,          // Loading state
    hasUnsavedChanges,  // Check for unsaved changes
    saveAllChanges,     // Save all changes
    resetToSaved        // Reset to last saved state
  } = useProviderSettings();
  
  // Use the settings...
}
```

### 2. Manage Individual Provider Configuration

```tsx
import { useProviderConfig } from '@/lib/hooks/use-provider-settings';

function ProviderConfig({ providerId }: { providerId: string }) {
  const { provider, updateConfig, isDirty } = useProviderConfig(providerId);
  
  const handleApiKeyChange = (apiKey: string) => {
    // This automatically marks the field as dirty
    updateConfig({ api_key: apiKey });
  };
  
  return (
    <input
      type="password"
      value={provider?.config.api_key || ''}
      onChange={(e) => handleApiKeyChange(e.target.value)}
    />
  );
}
```

### 3. Manage Model Selection

```tsx
import { useModelSelection } from '@/lib/hooks/use-provider-settings';

function ModelSelector() {
  const { modelSelection, updateModelSelection, isDirty } = useModelSelection();
  
  const handleProviderChange = (provider: string) => {
    updateModelSelection({
      textGeneration: {
        provider,
        model: '' // Reset model when provider changes
      }
    });
  };
  
  return (
    <select
      value={modelSelection.textGeneration.provider}
      onChange={(e) => handleProviderChange(e.target.value)}
    >
      {/* Options */}
    </select>
  );
}
```

## Advanced Usage

### Testing Provider Connections

```tsx
import { useProviderConfig } from '@/lib/hooks/use-provider-settings';
import { useProviderConnectionTest } from '@/lib/hooks/use-provider-test-cache';

function ProviderTester({ providerId }: { providerId: string }) {
  const { provider } = useProviderConfig(providerId);
  const { testProviderConnection } = useProviderConnectionTest();
  
  const handleTest = async () => {
    if (!provider) return;
    
    const result = await testProviderConnection(providerId, provider.config);
    
    if (result.success) {
      console.log('Available models:', result.models);
    } else {
      console.error('Test failed:', result.error);
    }
  };
  
  return <button onClick={handleTest}>Test Connection</button>;
}
```

### Implementing Save with Confirmation

```tsx
function SaveButton() {
  const { hasUnsavedChanges, saveAllChanges, isSaving } = useProviderSettings();
  
  const handleSave = async () => {
    if (!hasUnsavedChanges()) return;
    
    if (window.confirm('Save all provider settings?')) {
      try {
        await saveAllChanges();
        toast.success('Settings saved successfully');
      } catch (error) {
        toast.error('Failed to save settings');
      }
    }
  };
  
  return (
    <button 
      onClick={handleSave} 
      disabled={!hasUnsavedChanges() || isSaving}
    >
      {isSaving ? 'Saving...' : 'Save Changes'}
    </button>
  );
}
```

### Tracking Specific Field Changes

```tsx
function FieldWithDirtyIndicator({ providerId }: { providerId: string }) {
  const { isFieldDirty, markFieldClean } = useProviderSettings();
  const fieldPath = `provider.${providerId}.api_key`;
  
  return (
    <div>
      <input type="password" />
      {isFieldDirty(fieldPath) && (
        <span>
          Unsaved
          <button onClick={() => markFieldClean(fieldPath)}>×</button>
        </span>
      )}
    </div>
  );
}
```

## State Structure

### Provider Configuration
```typescript
interface ProviderConfiguration {
  id: string;
  providerId: string;
  name: string;
  enabled: boolean;
  config: Record<string, any>;  // Provider-specific settings
  status: 'connected' | 'disconnected' | 'testing' | 'error';
  lastTested?: string;
  models?: string[];
}
```

### Model Selection
```typescript
interface ModelSelection {
  textGeneration: {
    provider: string;
    model: string;
  };
  embeddings: {
    provider: string;
    model: string;
  };
  sharedProvider: boolean;  // Use same provider for both
}
```

## Best Practices

1. **Always Check Loading States**: Show appropriate UI during loading
2. **Handle Errors Gracefully**: Both load and save operations can fail
3. **Confirm Before Reset**: Ask users before discarding unsaved changes
4. **Batch Updates**: Make multiple changes then save once
5. **Test Before Save**: Test provider connections before saving configurations

## Integration with Backend

The context automatically handles:
- Loading configurations from `/api/v1/providers`
- Saving configurations via `POST /api/v1/providers/{id}/config`
- Model selection via configuration API
- Syncing with the ProviderTestCache for model discovery

## Error Handling

```tsx
function ErrorBoundary() {
  const { loadError, saveError, loadSettings } = useProviderSettings();
  
  if (loadError) {
    return (
      <ErrorMessage 
        message={loadError}
        onRetry={loadSettings}
      />
    );
  }
  
  if (saveError) {
    return <ErrorMessage message={saveError} />;
  }
  
  return null;
}
```