# Search Configuration Integration Tests

This directory contains comprehensive integration tests for the Search Configuration feature.

## Overview

The integration tests verify that two main issues have been fixed:

1. **No warnings during initial load**: The system should not display "No AI providers configured" warnings while data is still loading.

2. **No unsaved changes when switching tabs**: The system should not mark the form as having unsaved changes when simply loading saved configuration or switching tabs without making changes.

## Running the Tests

From the admin-ui directory:

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run only the integration tests
npm test -- integration.test.tsx
```

## Test Structure

The tests are organized into the following sections:

### Issue 1: No warnings during initial load
- Verifies loading state is shown while data loads
- Ensures no validation warnings appear prematurely
- Confirms warnings only show for legitimate issues after data loads
- Validates proper behavior when providers are configured

### Issue 2: No unsaved changes when switching tabs
- Ensures no unsaved changes indicator appears on initial load
- Verifies tab switching doesn't trigger unsaved changes
- Confirms changes are only detected for actual user modifications
- Tests save and discard functionality
- Validates proper dirty state management

### Loading states
- Tests loading UI display
- Verifies error state handling

### Tab navigation
- Tests prevention of tab switching with unsaved changes
- Verifies confirmation dialog behavior

## Mock Strategy

The tests use comprehensive mocking to isolate the SearchConfigLayout component:

- **API Client**: Mocked to control configuration loading and saving
- **Provider Settings**: Mocked to control provider data and loading states
- **Model Selection**: Mocked to control AI model configurations
- **Search Config Context**: Mocked to control vector and embedding configurations
- **Form State**: Mocked to control dirty state tracking

## Key Testing Patterns

1. **Dynamic State Updates**: The tests use `rerender` to simulate state changes that would normally occur through user interactions.

2. **Loading State Simulation**: Tests start with loading states and transition to loaded states to verify proper handling.

3. **User Interaction Simulation**: Uses React Testing Library's `userEvent` for realistic user interactions.

4. **Validation Testing**: Ensures validation only runs after all data is loaded using the deferred validation system.

## Troubleshooting

If tests fail:

1. Check that all mocks are properly set up in the `beforeEach` hook
2. Ensure the component structure hasn't changed (e.g., role names, text content)
3. Verify that the mock data matches the expected component behavior
4. Check console for any unmocked dependencies

## Future Improvements

- Add tests for keyboard navigation
- Test accessibility features
- Add performance tests for large configurations
- Test WebSocket real-time updates