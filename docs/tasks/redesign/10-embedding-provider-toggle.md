# Task 10: Embedding Provider Toggle Implementation

## Overview
Implement the special "Use Text Generation Provider settings" toggle in the Embedding tab that allows the embedding provider to inherit configuration from the text generation provider.

## Reference Specification Sections
- Section 3.2: Data Models (`EmbeddingProviderConfig` interface)
- Section 5.2: Component Class Specifications (Toggle Switch)
- Section 7.1: Complete Copy Catalog (useTextGenConfig)

## Task Requirements

### 1. Toggle Switch Component
- [ ] Create `src/components/ui/ToggleSwitch.tsx` with:
  - Classes from Section 5.2: `toggle`, `toggleActive`, `toggleInactive`
  - Button classes: `toggleButton`, `toggleButtonActive`, `toggleButtonInactive`
  - Smooth transition animations
  - Proper accessibility attributes

### 2. Embedding Provider Configuration Logic
- [ ] Update `EmbeddingTab.tsx` to include:
  - Toggle switch for "Use Text Generation Provider settings"
  - Conditional form field display based on toggle state
  - Dynamic form validation based on toggle state

### 3. Conditional Form Display
- [ ] **When Toggle is ON** (`use_text_generation_config: true`):
  - Hide all provider configuration fields
  - Show informational message: "Using Text Generation Provider settings"
  - Display current text generation provider info (read-only)
- [ ] **When Toggle is OFF** (`use_text_generation_config: false`):
  - Show full provider configuration form
  - Enable all form fields for editing
  - Apply standard validation rules

### 4. State Management Integration
- [ ] Update form state to handle the toggle properly:
  - Include `use_text_generation_config` in form state
  - Clear embedding provider fields when toggle is enabled
  - Restore embedding provider fields when toggle is disabled
  - Handle dirty detection correctly with toggle changes

### 5. Form Validation Logic
- [ ] **Toggle ON**: Skip validation for embedding provider fields
- [ ] **Toggle OFF**: Apply full validation to embedding provider fields
- [ ] Update dirty detection to account for toggle state changes

### 6. Visual Feedback Implementation
- [ ] **Toggle Container**: Use `toggleContainer` classes for layout
- [ ] **Active State**: Green background with white toggle button on right
- [ ] **Inactive State**: Gray background with white toggle button on left
- [ ] **Label**: "Use Text Generation Provider settings" from Section 7.1
- [ ] **Helper Text**: From Section 7.1 when toggle is displayed

### 7. Accessibility Implementation
- [ ] **ARIA Attributes**:
  - `role="switch"` on toggle element
  - `aria-checked` for current state
  - `aria-labelledby` linking to label
  - `aria-describedby` for helper text
- [ ] **Keyboard Support**:
  - Space bar to toggle
  - Enter key to toggle
  - Tab navigation to/from toggle

### 8. Animation and Transitions
- [ ] Toggle button smooth slide transition (150ms ease-in-out)
- [ ] Background color transition for toggle track
- [ ] Form field fade in/out when toggle changes

## Acceptance Criteria
- [ ] Toggle switch displays correctly with proper styling
- [ ] Toggle state changes update the form display appropriately
- [ ] Form fields hide/show based on toggle state
- [ ] Form validation works correctly in both toggle states
- [ ] State management handles toggle changes properly
- [ ] Dirty detection works with toggle state changes
- [ ] Accessibility requirements are met
- [ ] Visual transitions are smooth and match specifications
- [ ] Toggle integrates properly with save/revert functionality

## Evidence of Completion
To mark this task complete, provide:
1. Screenshot of toggle switch in both ON and OFF states
2. Screenshot showing form fields hidden when toggle is ON
3. Screenshot showing full form when toggle is OFF
4. Video/GIF demonstrating smooth toggle transitions
5. Screenshot showing proper accessibility attributes in browser dev tools
6. Code snippet showing the embedding provider configuration logic

## Dependencies
- Task 09: Global Save Bar Implementation

## Next Task
After completion, proceed to Task 11: API Integration & Connection Testing