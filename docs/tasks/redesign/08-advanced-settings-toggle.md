# Task 08: Advanced Settings Toggle Implementation

## Overview
Implement the advanced settings toggle feature within provider configuration cards, including collapsible content, animations, and state persistence.

## Reference Specification Sections
- Section 6.3: Advanced Settings Toggle Behavior
- Section 5.2: Component Class Specifications (Advanced Settings)
- Section 7.1: Complete Copy Catalog (Advanced Settings)
- Section 6.4: Animation & Timing Specifications

## Task Requirements

### 1. Advanced Settings Toggle Component
- [ ] Create `src/components/ui/AdvancedSettingsToggle.tsx` with:
  - Toggle button using `advancedToggle` classes
  - ChevronDown/ChevronUp icons from Section 5.3
  - Text: "Advanced Settings" / "Hide Advanced Settings"
  - Proper click handling and accessibility

### 2. Collapsible Content Implementation
- [ ] Create collapsible content area using `advancedContent` classes
- [ ] Implement smooth height transition animation (200ms ease-in-out)
- [ ] Use max-height technique for smooth expand/collapse
- [ ] Handle overflow hidden during animations

### 3. Advanced Form Fields
- [ ] **Temperature Field**:
  - Number input with range 0.0 to 2.0, step 0.1
  - Label: "Temperature"
  - Helper text from Section 7.1
  - Default value: 0.7
- [ ] **Max Tokens Field**:
  - Number input with range 1 to 100,000
  - Label: "Max Tokens" 
  - Helper text from Section 7.1
  - Default value: 4096

### 4. State Management Integration
- [ ] Add advanced settings fields to form state management
- [ ] Include in dirty detection and validation
- [ ] Integrate with save/revert functionality
- [ ] Handle field validation according to Section 6.1

### 5. Toggle State Persistence
- [ ] Store toggle state in sessionStorage with key pattern: `advancedSettings_[providerType]`
- [ ] Restore toggle state on component mount
- [ ] Maintain separate state for text generation vs embedding providers

### 6. Animation Implementation
- [ ] Icon rotation animation (180 degrees) using `transition-transform duration-200`
- [ ] Content height transition using max-height from 0 to auto equivalent
- [ ] Smooth transition timing: 200ms ease-in-out
- [ ] Prevent content flicker during animations

### 7. Copy Integration
- [ ] Use exact copy from Section 7.1:
  - Toggle button text: "Advanced Settings" / "Hide Advanced Settings"
  - Field labels and helper text
  - Validation messages

## Acceptance Criteria
- [ ] Advanced settings toggle button displays correctly with proper styling
- [ ] Click toggles the content area with smooth animation
- [ ] Icon rotates properly during toggle (chevron up/down)
- [ ] Advanced form fields (temperature, max tokens) display correctly
- [ ] Toggle state persists across browser sessions
- [ ] Animation timing matches specification (200ms)
- [ ] Advanced fields integrate with form validation
- [ ] Separate state management for different provider types
- [ ] Accessibility requirements met (ARIA attributes, keyboard support)

## Evidence of Completion
To mark this task complete, provide:
1. Screenshot/GIF showing smooth toggle animation working
2. Screenshot of advanced settings expanded with temperature and max tokens fields
3. Screenshot showing icon rotation during toggle
4. Demonstration of state persistence (refresh page, toggle state maintained)
5. Screenshot showing form validation working on advanced fields
6. Code snippet showing the AdvancedSettingsToggle component implementation

## Dependencies
- Task 07: Form State Management & Dirty Detection

## Next Task
After completion, proceed to Task 09: Global Save Bar Implementation