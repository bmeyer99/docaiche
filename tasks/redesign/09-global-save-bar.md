# Task 09: Global Save Bar Implementation

## Overview
Implement the global save bar component that appears at the bottom of the screen when forms have unsaved changes, providing save and revert functionality.

## Reference Specification Sections
- Section 4.2: Component Props Interfaces (`GlobalSaveBarProps`)
- Section 5.2: Component Class Specifications (Global Save Bar)
- Section 7.1: Complete Copy Catalog (Save Bar)
- Section 6.4: Animation & Timing Specifications

## Task Requirements

### 1. GlobalSaveBar Component
- [ ] Create `src/components/configuration/GlobalSaveBar.tsx` with:
  - Props interface matching `GlobalSaveBarProps` from Section 4.2
  - Fixed positioning using `saveBar` classes
  - Content container using `saveBarContent` classes
  - Slide-up animation on appear (200ms ease-in-out)

### 2. Save Bar Content Layout
- [ ] **Left Side Content**:
  - Unsaved changes message using `saveBarText` classes
  - Error count summary when validation errors exist
  - Loading state message during save operations
- [ ] **Right Side Actions**:
  - Save Changes button (primary style)
  - Revert All button (secondary style)
  - Button group using `saveBarActions` classes

### 3. State-Driven Display Logic
- [ ] **Show Conditions**:
  - `isDirty` is true (unsaved changes exist)
  - Form is not in initial loading state
- [ ] **Hide Conditions**:
  - No unsaved changes (`isDirty` is false)
  - User confirms revert action
  - After successful save operation

### 4. Dynamic Content Updates
- [ ] **Default State**: "You have unsaved changes."
- [ ] **Error State**: "Please fix {count} error(s) before saving."
- [ ] **Saving State**: "Saving..." with disabled buttons
- [ ] **Success State**: "All changes saved." (brief display before hiding)

### 5. Button State Management
- [ ] **Save Button**:
  - Disabled when form has validation errors
  - Disabled and shows spinner during save operation
  - Uses `buttonPrimary` classes
  - Text: "Save Changes"
- [ ] **Revert Button**:
  - Always enabled when save bar is visible
  - Uses `buttonSecondary` classes
  - Text: "Revert All"
  - Triggers confirmation modal

### 6. Animation Implementation
- [ ] **Slide Up Animation**:
  - Appears from bottom with `transform: translateY(100%)` to `translateY(0)`
  - 200ms ease-in-out transition
  - Z-index: 40 to appear above other content
- [ ] **Fade Out Animation**:
  - Smooth fade when hiding after save success
  - Slide down when dismissed

### 7. Responsive Behavior
- [ ] **Desktop**: Full width with proper max-width container
- [ ] **Mobile**: Stack buttons vertically on very small screens
- [ ] **Tablet**: Maintain horizontal layout with adjusted spacing

### 8. Accessibility Implementation
- [ ] **ARIA Labels**: Proper labeling for screen readers
- [ ] **Live Region**: Announce state changes with `aria-live="polite"`
- [ ] **Focus Management**: Maintain focus context when bar appears/disappears

## Acceptance Criteria
- [ ] Save bar appears smoothly when forms become dirty
- [ ] Save bar disappears after successful save or revert
- [ ] Button states change correctly based on form validation
- [ ] Error count displays accurately when validation errors exist
- [ ] Loading states show during save operations
- [ ] Responsive layout works on all screen sizes
- [ ] Animations are smooth and match timing specifications
- [ ] Accessibility requirements are met
- [ ] Revert button triggers confirmation modal

## Evidence of Completion
To mark this task complete, provide:
1. Screenshot/GIF showing save bar sliding up when form becomes dirty
2. Screenshot showing save bar with error count when validation fails
3. Screenshot showing save bar during save operation (loading state)
4. Screenshot of responsive layout on mobile devices
5. Video demonstration of save bar hiding after successful save
6. Code snippet showing the GlobalSaveBar component implementation

## Dependencies
- Task 08: Advanced Settings Toggle Implementation

## Next Task
After completion, proceed to Task 10: Embedding Provider Toggle Implementation