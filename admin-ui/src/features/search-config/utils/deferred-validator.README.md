# Deferred Validator

The Deferred Validator is a validation system that waits for all required data to be loaded before running validation. This prevents false warnings like "No AI providers configured" from appearing during the initial loading phase.

## Problem it Solves

When the Search Configuration UI loads, different data sources (providers, vector config, model selection, etc.) load asynchronously at different times. Running validation immediately can result in false warnings because some data hasn't loaded yet.

For example:
- Providers might still be loading when validation runs
- This causes "No AI providers configured" warning to appear
- The warning disappears once providers finish loading
- This creates a poor user experience with flickering warnings

## How it Works

The DeferredValidator:
1. **Queues validation requests** instead of running them immediately
2. **Tracks loading states** for all data sources
3. **Waits for all data to load** before processing the queue
4. **Caches results** to avoid redundant validation
5. **Provides loading states** while data is being fetched

## Usage

### In React Components

```tsx
import { useDeferredValidation } from '@/features/search-config/utils/deferred-validator';

function MyComponent() {
  const { providers, isLoading: providersLoading } = useProviderSettings();
  const { modelSelection, isLoading: modelLoading } = useModelSelection();
  
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
      modelSelection: modelLoading,
      modelParameters: configLoading
    }
  });
  
  return <ConfigValidation validation={validation} />;
}
```

### Direct Usage

```tsx
import { getDeferredValidator } from '@/features/search-config/utils/deferred-validator';

const validator = getDeferredValidator();

// Update loading states
validator.updateLoadingState({
  providers: false,  // false = loaded, true = loading
  vectorConfig: false
});

// Request validation (returns a promise)
const result = await validator.validate({
  vectorConfig,
  embeddingConfig,
  modelSelection,
  modelParameters,
  providers
});
```

## Key Features

### 1. Automatic Deferral
Validation requests are automatically queued if data is still loading.

### 2. Result Caching
Results are cached for 1 second to avoid redundant validation when multiple components request validation with the same data.

### 3. Loading States
Shows appropriate loading messages instead of validation errors while data loads.

### 4. Batch Processing
Multiple validation requests are batched and processed together for efficiency.

## API Reference

### `useDeferredValidation(options)`
React hook for deferred validation.

**Parameters:**
- `vectorConfig`: Vector search configuration
- `embeddingConfig`: Embedding configuration  
- `modelSelection`: Selected models
- `modelParameters`: Model parameters
- `providers`: Provider configurations
- `isLoading`: Object with loading states for each data source

**Returns:** `ValidationResult`

### `getDeferredValidator()`
Get the singleton validator instance.

### `DeferredValidator.getLoadingResult()`
Get a default loading validation result.

### `DeferredValidator.getLoadingMessage()`
Get a validation result with a loading message.

### `hasRealValidationIssues(validation)`
Check if validation has real issues (not just loading states).

## Implementation Details

### Loading State Tracking
The validator tracks loading states for:
- `providers`
- `vectorConfig`
- `embeddingConfig`
- `modelSelection`
- `modelParameters`

All must be `false` (loaded) before validation runs.

### Cache Key Generation
Cache keys are generated based on:
- Provider IDs and statuses
- Vector search enabled state and URL
- Selected embedding provider and model
- Selected text generation provider and model

### Queue Processing
- Requests are queued with a unique ID
- Processing is scheduled with a 100ms delay to batch requests
- All queued requests are processed when data loads

### Error Handling
- Components unmounting are handled gracefully
- Validation errors are caught and reported
- Cancelled validations don't update component state

## Best Practices

1. **Always provide loading states** - Pass accurate loading states to ensure validation waits appropriately
2. **Use the hook in components** - Prefer `useDeferredValidation` over direct usage in React components
3. **Check for real issues** - Use `hasRealValidationIssues()` to distinguish between loading states and actual problems
4. **Don't cache too long** - The 1-second cache TTL balances performance with data freshness