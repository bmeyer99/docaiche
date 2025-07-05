# Search Config State Management Solution

## Overview
This document outlines the comprehensive solution to fix the configuration warnings and unsaved changes issues in the Search Config page.

## Core Problems
1. **Race Conditions**: Validation runs before provider data is loaded
2. **False Change Detection**: Loading saved values triggers "unsaved changes"
3. **Inconsistent State**: Multiple state sources not properly synchronized

## Solution Architecture

### 1. Loading State Management
```typescript
interface ConfigLoadingState {
  isLoading: boolean;
  providersLoaded: boolean;
  configLoaded: boolean;
  modelsLoaded: boolean;
}
```

### 2. Change Detection System
```typescript
interface ChangeDetection {
  source: 'user' | 'system';
  timestamp: number;
  fieldPath: string;
}
```

### 3. Deferred Validation
- Validation only runs after all required data is loaded
- Loading states prevent premature validation
- Validation results cached until actual changes occur

### 4. Centralized Form State Hook
```typescript
interface UseSearchConfigForm {
  formState: FormState;
  isDirty: boolean;
  isLoading: boolean;
  updateField: (path: string, value: any, source: 'user' | 'system') => void;
  resetForm: () => void;
  saveForm: () => Promise<void>;
}
```

## Implementation Plan

### Phase 1: Core Infrastructure (Parallel Tasks)
- Task 3: Implement loading states in ConfigProvider
- Task 5: Implement deferred validation
- Task 7: Create change detection system
- Task 13: Create centralized form hook

### Phase 2: Component Refactoring (Parallel Tasks)
- Task 9: Refactor text-ai.tsx
- Task 10: Refactor vector-ai.tsx
- Task 11: Refactor embedding-ai.tsx

### Phase 3: Integration
- Task 15: Update search-config-layout.tsx
- Task 17: Create integration tests

## Key Implementation Details

### Loading State Implementation
1. Add loading flags to ConfigProvider
2. Track individual data source loading states
3. Expose composite loading state

### Change Detection Implementation
1. Wrap all setState calls with source tracking
2. Differentiate between user actions and system updates
3. Only mark form as dirty on user changes

### Validation Deferral
1. Create validation queue
2. Only process when all data loaded
3. Cache results until actual changes

### Form State Management
1. Single source of truth for form state
2. Automatic dirty tracking
3. Proper state synchronization

## Success Criteria
1. No warnings shown during initial load
2. No "unsaved changes" when switching tabs without edits
3. Proper warnings when configuration is actually invalid
4. Accurate dirty state detection