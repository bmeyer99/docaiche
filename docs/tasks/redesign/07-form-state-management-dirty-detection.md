# Task 07: Form State Management & Dirty Detection

## Overview
Implement the form state management system with dirty detection that tracks changes across all configuration forms and enables the global save/revert functionality.

## Reference Specification Sections
- Section 4.3: State Management Flow
- Section 6.2: UI States & Loading Behavior
- Section 3.4: Fallback Default Values

## Task Requirements

### 1. Form State Hook Implementation
- [ ] Create `src/hooks/useFormState.ts` with:
  - State management for current configuration values
  - Dirty state detection using deep comparison
  - Form validation state tracking
  - Error state management

### 2. Configuration Hook Implementation  
- [ ] Create `src/hooks/useConfiguration.ts` with:
  - API state management for configuration loading/saving
  - Initial configuration state storage
  - Loading states for API operations
  - Error handling for API failures

### 3. State Management Flow Implementation
- [ ] **Initial Load Flow**:
  - Fetch configuration from API on component mount
  - Store as `initialConfig` state
  - Copy to `currentConfig` for form editing
  - Populate form fields with current values
- [ ] **User Edit Flow**:
  - Update `currentConfig` on field changes
  - Trigger dirty detection comparison
  - Update validation state
- [ ] **Dirty Detection Logic**:
  - Deep comparison between `initialConfig` and `currentConfig`
  - Return boolean `isDirty` state
  - Track specific field changes for targeted validation

### 4. Fallback Defaults Integration
- [ ] Implement fallback defaults from Section 3.4:
  - Use fallback values when API fails to load
  - Ensure form remains functional with defaults
  - Clear error states when fallbacks are applied

### 5. Form Validation Integration
- [ ] Implement debounced validation (400ms after typing stops)
- [ ] Track validation errors per field
- [ ] Provide overall form validation state
- [ ] Support real-time validation feedback

### 6. State Persistence Logic
- [ ] **Save Flow**:
  - Validate all form data before save
  - Send `currentConfig` to API
  - Update `initialConfig` with saved values on success
  - Clear dirty state after successful save
- [ ] **Revert Flow**:
  - Reset `currentConfig` to `initialConfig` values
  - Clear all validation errors
  - Reset dirty state

### 7. State Change Logging Integration
- [ ] Implement logging for state changes from Section 10.2:
  - Log all form field changes with old/new values
  - Log user actions (save, revert, field changes)
  - Log validation events and errors
  - Include user session context and component names
  - Ensure sensitive data (API keys) is properly redacted

## Acceptance Criteria
- [ ] Form state hooks manage configuration data correctly
- [ ] Dirty detection accurately identifies changes
- [ ] Deep comparison works for nested configuration objects
- [ ] API loading and error states are properly managed
- [ ] Fallback defaults work when API is unavailable
- [ ] Form validation integrates with state management
- [ ] Save and revert operations function correctly
- [ ] State updates trigger proper re-renders

## Evidence of Completion
To mark this task complete, provide:
1. Code snippet showing the useFormState hook implementation
2. Code snippet showing the useConfiguration hook implementation
3. Screenshot/demo showing dirty detection working (form shows as dirty when fields change)
4. Screenshot showing fallback defaults loading when API fails
5. Screenshot showing form validation errors appearing after the 400ms delay
6. Code snippet demonstrating the save/revert state management flow

## Dependencies
- Task 06: Provider Configuration Card Component

## Next Task
After completion, proceed to Task 08: Advanced Settings Toggle Implementation