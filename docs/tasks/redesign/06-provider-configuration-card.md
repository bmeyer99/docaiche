# Task 06: Provider Configuration Card Component

## Overview
Create the main ProviderConfigCard component that handles all provider configuration forms, including form fields, validation states, and connection testing functionality.

## Reference Specification Sections
- Section 4.2: Component Props Interfaces (`ProviderConfigCardProps`)
- Section 6.1: Form Validation Rules
- Section 7.1: Complete Copy Catalog (Form Labels, Helper Text, Placeholders)
- Section 5.2: Component Class Specifications (Form controls)

## Task Requirements

### 1. ProviderConfigCard Component
- [ ] Create `src/components/configuration/ProviderConfigCard.tsx` with:
  - Props interface matching `ProviderConfigCardProps` from Section 4.2
  - Card layout using `card` classes from Section 5.2
  - Form layout using `formGroup` and `formRow` classes

### 2. Form Fields Implementation
- [ ] **Provider Selection Dropdown**:
  - Options: "Ollama", "OpenAI", "Custom" (from Section 7.1)
  - Uses `select` classes with proper styling
- [ ] **Base URL Input Field**:
  - Label: "Base URL", Helper text from Section 7.1
  - Placeholder: "http://localhost:11434"
  - URL validation pattern from Section 6.1
- [ ] **API Key Input Field**:
  - Label: "API Key", Helper text from Section 7.1
  - Password input type with show/hide toggle
  - Eye/EyeOff icons from Section 5.3
- [ ] **Model Selection**:
  - Dropdown when models are loaded
  - Text input when no models available
  - Loading state: "Loading models..." option

### 3. Form Validation Integration
- [ ] Implement all validation rules from Section 6.1:
  - Base URL: Required, valid URL pattern
  - API Key: Conditional requirement, min 8 characters
  - Model: Required field
- [ ] Display validation errors using `errorText` classes
- [ ] Show validation states on form fields (`inputError` classes)

### 4. Connection Testing Feature
- [ ] Add "Test Connection" button using `buttonSecondary` classes
- [ ] Implement connection status display:
  - Connected: `statusConnected` with CheckCircle icon
  - Testing: `statusTesting` with Loader icon (animated)
  - Failed: `statusFailed` with XCircle icon
- [ ] Handle loading states during connection test

### 5. Copy Integration
- [ ] Use exact copy from Section 7.1 for:
  - All form labels and helper text
  - Button text and placeholders
  - Validation messages
  - Status messages

### 6. Responsive Layout
- [ ] Desktop: Two-column form layout (`formRow` classes)
- [ ] Mobile: Single-column stacked layout
- [ ] Proper field spacing and alignment

## Acceptance Criteria
- [ ] Provider card displays with proper styling and layout
- [ ] All form fields render correctly with proper labels and helper text
- [ ] Form validation works according to specification rules
- [ ] Connection testing button and status indicators function
- [ ] API key field has working show/hide toggle
- [ ] Responsive layout adapts correctly to screen sizes
- [ ] All copy text matches specification exactly
- [ ] Component accepts and uses props correctly

## Evidence of Completion
To mark this task complete, provide:
1. Screenshot of complete provider configuration card on desktop
2. Screenshot showing form validation errors in action
3. Screenshot of connection testing states (testing, success, failure)
4. Screenshot of API key show/hide functionality working
5. Screenshot of mobile responsive layout
6. Code snippet showing the ProviderConfigCard component with proper TypeScript props

## Dependencies
- Task 05: LLM Providers Secondary Tab Structure

## Next Task
After completion, proceed to Task 07: Form State Management & Dirty Detection