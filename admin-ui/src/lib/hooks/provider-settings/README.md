# Provider Settings System

A modular system for managing AI provider configurations and settings in the admin UI.

## Directory Structure

```
provider-settings/
├── index.ts                          # Public exports
├── types.ts                          # All TypeScript interfaces and types
├── constants.ts                      # Constants and enums
├── context.tsx                       # Main context provider
├── hooks/
│   ├── use-provider-settings.ts     # Main hook for accessing context
│   ├── use-provider-config.ts       # Provider-specific configuration hook
│   ├── use-model-selection.ts       # Model selection management hook
│   ├── use-provider-loader.ts       # Loading logic hook
│   └── use-provider-saver.ts        # Saving logic hook
├── utils/
│   ├── validation.ts                 # Input validation functions
│   ├── state-helpers.ts              # State manipulation helpers
│   ├── api-helpers.ts                # API integration helpers
│   └── field-path.ts                 # Field path utilities for dirty tracking
└── __tests__/
    ├── provider-settings.test.tsx    # Main tests
    └── test-utils.tsx                # Test utilities and mocks

## Usage

### Basic Setup

```tsx
import { ProviderSettingsProvider } from '@/lib/hooks/provider-settings';

// Wrap your app with the provider
function App() {
  return (
    <ProviderSettingsProvider>
      {/* Your app content */}
    </ProviderSettingsProvider>
  );
}
```

### Using the Main Hook

```tsx
import { useProviderSettings } from '@/lib/hooks/provider-settings';

function MyComponent() {
  const {
    providers,
    modelSelection,
    isLoading,
    isSaving,
    loadSettings,
    updateProvider,
    updateModelSelection,
    saveAllChanges,
    hasUnsavedChanges,
  } = useProviderSettings();

  // Use the settings...
}
```

### Using Provider-Specific Hook

```tsx
import { useProviderConfig } from '@/lib/hooks/provider-settings';

function ProviderConfig({ providerId }: { providerId: string }) {
  const { provider, updateConfig, isDirty } = useProviderConfig(providerId);
  
  // Use provider config...
}
```

### Using Model Selection Hook

```tsx
import { useModelSelection } from '@/lib/hooks/provider-settings';

function ModelSelector() {
  const { modelSelection, updateModelSelection, isDirty } = useModelSelection();
  
  // Use model selection...
}
```

## Features

- **Centralized State Management**: All provider configurations in one place
- **Dirty State Tracking**: Track which fields have been modified
- **Batch Saving**: Save all changes in a single operation
- **Integration with Test Cache**: Syncs with provider test results
- **TypeScript Support**: Full type safety with no `any` types
- **Modular Architecture**: Clear separation of concerns

## Architecture

The system is built around a React Context that manages:

1. **Provider Configurations**: Settings for each AI provider
2. **Model Selection**: Which models to use for text generation and embeddings
3. **Dirty State**: Tracks which fields have been modified
4. **Loading/Saving States**: UI feedback for async operations

The modular structure separates:
- **Types**: All TypeScript interfaces in one place
- **Constants**: Shared constants and default values
- **Hooks**: Specialized hooks for different use cases
- **Utils**: Helper functions for common operations
- **Context**: Core state management logic