# Configuration Page Redesign Specification (V6 - Complete Implementation Blueprint)

## 1. Overview & Definition of Done

This document provides the complete, final technical specification for the System Configuration page redesign. It is intended to be a direct blueprint for a developer using a React/TypeScript/TailwindCSS stack.

**Definition of Done:** The feature is complete when all requirements in this document, including API contracts, component behaviors, styling, and testing, are implemented and verified.

---

## 2. Information Architecture

The new design replaces the accordion layout with a two-level tabbed navigation system. To streamline the initial setup, the **LLM Providers** tab is prioritized as the default view.

```
Configuration Page
├── LLM Providers (Primary Tab - Default)
│   ├── Text Generation (Secondary Tab)
│   │   └── Configuration for the primary text generation provider.
│   └── Embedding (Secondary Tab)
│       └── Configuration for the embedding provider.
│
├── General Settings (Primary Tab)
│   └── System-wide settings like environment, logging, and debug mode.
│
├── Connection Settings (Primary Tab)
│   └── Network and service settings like API host, ports, and worker processes.
│
├── Cache Settings (Primary Tab)
│   └── All settings related to the Redis cache (connection, TTL, size).
│
└── Advanced Settings (Primary Tab)
    └── Fine-grained technical settings like content chunking and processing thresholds.
```

---

## 3. API Contracts & Data Models

### 3.1. Endpoints

**1. Fetch Configuration:** `GET /api/v1/config`
- **Description:** Retrieves the current system configuration.
- **Success Response (200 OK):**
  ```json
  {
    "data": {
      "llm_providers": {
        "text_generation": {
          "provider": "ollama",
          "base_url": "http://ollama:11434",
          "api_key": null,
          "model": "llama3",
          "temperature": 0.7,
          "max_tokens": 4096
        },
        "embedding": {
          "use_text_generation_config": true,
          "provider": "ollama",
          "base_url": "http://ollama:11434",
          "api_key": null,
          "model": "llama3"
        }
      }
    },
    "status": "success"
  }
  ```

**2. Update Configuration:** `POST /api/v1/config`
- **Description:** Saves the updated system configuration.
- **Request Body:** The `SystemConfiguration` object (see 3.2).
- **Success Response (200 OK):**
  ```json
  {
    "message": "Configuration saved successfully.",
    "status": "success"
  }
  ```

**3. Test Connection:** `POST /api/v1/config/test-connection`
- **Description:** Validates a provider's connection details and returns available models.
- **Request Body:** `TestConnectionRequest`
- **Success Response (200 OK):** `TestConnectionResponse`

### 3.2. Data Models (TypeScript Interfaces)

```typescript
// file: src/types/configuration.ts

interface ModelSettings {
  temperature?: number;
  max_tokens?: number;
}

interface ProviderConfig {
  provider: 'ollama' | 'openai' | 'custom';
  base_url: string;
  api_key: string | null;
  model: string;
  advanced_settings?: ModelSettings;
}

interface EmbeddingProviderConfig extends ProviderConfig {
  use_text_generation_config: boolean;
}

export interface SystemConfiguration {
  llm_providers: {
    text_generation: ProviderConfig;
    embedding: EmbeddingProviderConfig;
  };
  // Define other config sections as needed
}

export interface TestConnectionRequest {
  provider: 'ollama' | 'openai' | 'custom';
  base_url: string;
  api_key?: string;
}

export interface TestConnectionResponse {
  status: 'success' | 'error';
  models?: string[];
  error?: string;
}
```

### 3.3. API Error Handling Matrix

| HTTP Status | User Message                  | UI Behavior                                     |
|-------------|-------------------------------|-------------------------------------------------|
| 400         | "Invalid configuration data." | Highlight specific fields with validation errors. |
| 401         | "Authentication failed."      | Redirect user to the login page.                |
| 422         | "Validation Error."           | Show field-specific errors from API response.   |
| 500         | "An unexpected server error occurred." | Show a global error toast with a retry option.  |
| Timeout     | "The server is not responding." | Show a global error toast with a retry option.  |

### 3.4. Fallback Default Values

If the API fails to load the initial configuration, the UI must populate the form with these fallback defaults to ensure functionality:

```javascript
const fallbackDefaults = {
  text_generation: {
    provider: "ollama",
    base_url: "http://localhost:11434",
    model: "llama3",
    temperature: 0.7,
    max_tokens: 4096
  },
  embedding: {
    use_text_generation_config: true,
    provider: "ollama",
    base_url: "http://localhost:11434",
    model: "llama3"
  }
};
```

---

## 4. Component Architecture & Props

### 4.1. Code Organization

```
src/
├── components/
│   ├── configuration/
│   │   ├── ConfigurationPage.tsx
│   │   ├── ProviderConfigCard.tsx
│   │   ├── GlobalSaveBar.tsx
│   │   └── ConfirmationModal.tsx
│   └── ui/
│       ├── Button.tsx
│       ├── Input.tsx
│       └── Tabs.tsx
├── hooks/
│   ├── useConfiguration.ts // Manages API state
│   └── useFormState.ts   // Manages form dirty state & values
└── types/
    └── configuration.ts
```

### 4.2. Component Props Interfaces

```typescript
// ProviderConfigCard.tsx
interface ProviderConfigCardProps {
  title: string;
  value: ProviderConfig;
  onChange: (config: ProviderConfig) => void;
  disabled?: boolean;
}

// GlobalSaveBar.tsx
interface GlobalSaveBarProps {
  isDirty: boolean;
  onSave: () => void;
  onRevert: () => void;
  isSaving: boolean;
  errorCount: number;
}

// ConfirmationModal.tsx
interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText: string;
  cancelText: string;
}
```

### 4.3. State Management Flow

1.  **Initial Load:** `GET /api/config` → `initialConfig` state → `currentConfig` state → Populate Form Fields.
2.  **User Edit:** User interacts with Form Field → `onChange` updates `currentConfig` state.
3.  **Dirty Check:** A `useMemo` hook deep-compares `currentConfig` and `initialConfig` to set `isDirty` boolean.
4.  **Save:** `Save` button click → `onSave` triggers validation → If valid, `POST /api/config` with `currentConfig` payload → On success, update `initialConfig` with `currentConfig`.
5.  **Revert:** `Revert` button click → Reset `currentConfig` to `initialConfig`.

---

## 5. Styling & Visual Implementation (TailwindCSS)

### 5.1. Tailwind Configuration

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        primary: '#2563EB',
        'primary-hover': '#1D4ED8',
        neutral: '#F9FAFB',
        surface: '#FFFFFF',
        border: '#E5E7EB',
        'text-primary': '#111827',
        'text-secondary': '#6B7280',
        success: '#16A34A',
        warning: '#FBBF24',
        error: '#DC2626',
        disabled: '#D1D5DB',
        'text-disabled': '#9CA3AF',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      }
    }
  }
};
```

### 5.2. Component Class Specifications

```javascript
const componentClasses = {
  // Buttons
  buttonPrimary: "h-10 px-6 bg-primary hover:bg-primary-hover text-white rounded-md font-medium transition-colors focus:ring-2 focus:ring-primary focus:ring-offset-2",
  buttonSecondary: "h-10 px-6 bg-surface border border-border text-text-secondary hover:bg-neutral rounded-md font-medium transition-colors",
  buttonDestructive: "h-10 px-6 bg-error hover:bg-red-700 text-white rounded-md font-medium transition-colors focus:ring-2 focus:ring-error focus:ring-offset-2",
  
  // Form Controls
  input: "h-10 px-3 border border-border rounded bg-surface focus:border-primary focus:ring-1 focus:ring-primary text-text-primary placeholder:text-text-secondary",
  inputError: "border-error focus:border-error focus:ring-error",
  inputDisabled: "bg-disabled text-text-disabled cursor-not-allowed",
  select: "h-10 px-3 border border-border rounded bg-surface focus:border-primary focus:ring-1 focus:ring-primary text-text-primary",
  selectError: "border-error focus:border-error focus:ring-error",
  label: "block text-sm font-medium text-text-primary mb-1",
  helperText: "text-xs text-text-secondary mt-1",
  errorText: "text-xs text-error mt-1",
  
  // Layout
  card: "bg-surface border border-border rounded-lg p-6 shadow-sm",
  pageContainer: "max-w-6xl mx-auto p-8",
  formGroup: "space-y-1",
  formRow: "grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6",
  
  // Status indicators
  statusConnected: "flex items-center gap-2 text-success text-sm font-medium",
  statusTesting: "flex items-center gap-2 text-warning text-sm font-medium",
  statusFailed: "flex items-center gap-2 text-error text-sm font-medium",
  
  // Tabs (Responsive)
  primaryTabs: "hidden md:flex space-x-1 border-b border-border mb-6",
  mobileTabSelect: "block md:hidden w-full mb-6",
  tabButton: "px-4 py-2 text-sm font-medium rounded-md transition-colors",
  tabButtonActive: "bg-primary text-white",
  tabButtonInactive: "text-text-secondary hover:text-text-primary hover:bg-neutral",
  secondaryTabs: "flex space-x-1 mb-6",
  
  // Toggle Switch
  toggleContainer: "flex items-center gap-3",
  toggle: "relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2",
  toggleActive: "bg-primary",
  toggleInactive: "bg-border",
  toggleButton: "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
  toggleButtonActive: "translate-x-6",
  toggleButtonInactive: "translate-x-1",
  
  // Advanced Settings
  advancedToggle: "flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors cursor-pointer",
  advancedContent: "mt-4 space-y-4 overflow-hidden transition-all duration-200",
  
  // Global Save Bar
  saveBar: "fixed bottom-0 left-0 right-0 bg-surface border-t border-border p-4 shadow-lg z-40",
  saveBarContent: "max-w-6xl mx-auto flex items-center justify-between",
  saveBarText: "text-sm text-text-secondary",
  saveBarActions: "flex items-center gap-3",
};
```

### 5.3. Icon Specifications

```javascript
const iconSpecs = {
  library: "lucide-react",
  defaultSize: "w-4 h-4", // 16px
  icons: {
    settings: "Settings", // ⚙️ for advanced settings toggle
    eye: "Eye", // Show password
    eyeOff: "EyeOff", // Hide password  
    checkCircle: "CheckCircle2", // Success status
    alertTriangle: "AlertTriangle", // Warning status
    xCircle: "XCircle", // Error status
    loader: "Loader2", // Loading spinner (add animate-spin)
    chevronDown: "ChevronDown", // Collapsed advanced settings
    chevronUp: "ChevronUp", // Expanded advanced settings
    x: "X", // Close/dismiss icons
  },
  sizes: {
    sm: "w-3 h-3", // 12px
    md: "w-4 h-4", // 16px (default)
    lg: "w-5 h-5", // 20px
  }
};
```

### 5.4. Toast Notification Implementation

```javascript
const toastClasses = {
  container: "fixed top-6 right-6 z-50 space-y-2 max-w-sm",
  success: "bg-surface border border-success text-text-primary p-4 rounded-lg shadow-lg flex items-center gap-3",
  error: "bg-surface border border-error text-text-primary p-4 rounded-lg shadow-lg flex items-center gap-3",
  warning: "bg-surface border border-warning text-text-primary p-4 rounded-lg shadow-lg flex items-center gap-3",
  dismissButton: "ml-auto text-text-secondary hover:text-text-primary"
};

// Toast Behavior:
// - Auto-dismiss after 5 seconds
// - Manual dismiss with X button  
// - Stack vertically with 8px gap (space-y-2)
// - Slide in from right with transition-transform
// - Maximum 3 toasts visible at once
```

---

## 6. Detailed Behavior & State Management

### 6.1. Form Validation Rules

```javascript
const validationRules = {
  base_url: {
    required: true,
    pattern: /^https?:\/\/.+/,
    message: "Please enter a valid URL (e.g., http://localhost:11434)"
  },
  api_key: {
    required: false, // Becomes required based on provider logic
    minLength: 8,
    message: "API key must be at least 8 characters"
  },
  temperature: {
    min: 0.0,
    max: 2.0,
    step: 0.1,
    message: "Must be between 0.0 and 2.0"
  },
  max_tokens: {
    min: 1,
    max: 100000,
    message: "Must be between 1 and 100,000"
  },
  model: {
    required: true,
    message: "Please select or enter a model name"
  }
};
```

### 6.2. UI States & Loading Behavior

```javascript
const uiStates = {
  loading: {
    pageInitial: "Show skeleton cards with 'animate-pulse' class",
    testConnection: "Button text: 'Testing...', add 'animate-spin' to icon, disable button",
    saveConfig: "Button disabled with 'opacity-50' and shows spinner icon",
    modelSelect: "Show disabled option with text 'Loading models...'",
    longRequest: "After 8 seconds, show helper text: 'Still trying to connect...'"
  },
  
  empty: {
    noModels: "No models found at this endpoint. Please check your connection and try again.",
    noConnection: "Unable to connect. Please verify the Base URL and network connectivity.",
    loadFailed: "Failed to load configuration. [Retry] button with 'buttonSecondary' classes",
    apiUnreachable: "The API endpoint is not responding. Please check the URL and try again."
  },
  
  success: {
    connectionTest: "Success! Connection established.",
    configSaved: "Configuration saved successfully.",
    modelsLoaded: "Models loaded successfully."
  },
  
  error: {
    connectionFailed: "Connection failed. Please check your settings.",
    saveFailed: "Failed to save configuration. Please try again.",
    validationFailed: "Please fix the errors above before saving."
  }
};
```

### 6.3. Advanced Settings Toggle Behavior

```javascript
const advancedSettingsSpec = {
  initialState: "collapsed",
  toggleClasses: {
    button: "flex items-center gap-2 text-text-secondary hover:text-text-primary transition-colors",
    icon: "w-4 h-4 transition-transform duration-200", // Add 'rotate-180' when expanded
    content: "mt-4 space-y-4 overflow-hidden transition-all duration-200" // Use max-height for smooth animation
  },
  persistence: "State stored in sessionStorage, key: 'advancedSettings_[providerType]'",
  animation: "200ms ease-in-out height transition with max-height",
  behavior: {
    expand: "max-height grows from 0 to auto, icon rotates 180deg",
    collapse: "max-height shrinks to 0, icon rotates back to 0deg"
  }
};
```

### 6.4. Animation & Timing Specifications

```javascript
const animations = {
  tabSwitching: "150ms ease-in-out cross-fade between tab content",
  advancedToggle: "200ms ease-in-out height transition with max-height",
  validation: "Validate input fields 400ms after user stops typing (debounced)",
  toasts: "5 second auto-dismiss, 300ms slide-in from right",
  modalTransition: "150ms ease-in-out fade and scale",
  saveBarSlide: "200ms ease-in-out slide up from bottom",
  buttonHover: "150ms ease-in-out color transitions",
  focusRing: "150ms ease-in-out ring transitions"
};
```

---

## 7. Content & Copy Specifications

### 7.1. Complete Copy Catalog

```javascript
const copyText = {
  // Page & Navigation
  pageTitle: "System Configuration",
  primaryTabs: {
    llmProviders: "LLM Providers",
    general: "General Settings", 
    connections: "Connection Settings",
    cache: "Cache Settings",
    advanced: "Advanced Settings"
  },
  secondaryTabs: {
    textGeneration: "Text Generation",
    embedding: "Embedding"
  },
  
  // Buttons
  buttons: {
    saveChanges: "Save Changes",
    revertAll: "Revert All",
    testConnection: "Test Connection",
    cancel: "Cancel",
    yesRevert: "Yes, Revert",
    retry: "Retry",
    showAdvanced: "Advanced Settings",
    hideAdvanced: "Hide Advanced Settings"
  },
  
  // Form Labels
  labels: {
    provider: "Provider",
    baseUrl: "Base URL",
    apiKey: "API Key",
    model: "Model", 
    temperature: "Temperature",
    maxTokens: "Max Tokens",
    useTextGenConfig: "Use Text Generation Provider settings"
  },
  
  // Helper Text
  helperText: {
    baseUrl: "API endpoint for the provider (e.g., http://ollama:11434)",
    apiKey: "Authentication key for the provider (leave empty if not required)",
    model: "Select a model or enter a model name",
    temperature: "Controls randomness in responses (0.0 = deterministic, 2.0 = very random)",
    maxTokens: "Maximum number of tokens to generate in responses",
    useTextGenConfig: "When enabled, embedding provider will use the same settings as text generation"
  },
  
  // Placeholders
  placeholders: {
    baseUrl: "http://localhost:11434",
    apiKey: "Enter your API key",
    model: "Select a model",
    maxTokens: "4096",
    temperature: "0.7"
  },
  
  // Validation Messages
  validation: {
    required: "This field is required.",
    invalidUrl: "Please enter a valid URL (e.g., http://localhost:11434).",
    invalidNumber: "Please enter a valid number.",
    minLength: "Must be at least {min} characters.",
    outOfRange: "Must be between {min} and {max}.",
    apiKeyTooShort: "API key must be at least 8 characters."
  },
  
  // Status Messages
  status: {
    connected: "Connected",
    testing: "Testing...",
    failed: "Connection Failed",
    offline: "Offline",
    loading: "Loading...",
    noModels: "No models available",
    stillTrying: "Still trying to connect..."
  },
  
  // Modals
  modals: {
    revertTitle: "Revert all changes?",
    revertBody: "Are you sure you want to discard all unsaved changes? This action cannot be undone.",
    unsavedChanges: "You have unsaved changes."
  },
  
  // Global Save Bar
  saveBar: {
    unsavedChanges: "You have unsaved changes.",
    errorSummary: "Please fix {count} error(s) before saving.",
    saving: "Saving...",
    saved: "All changes saved."
  },
  
  // Provider Options
  providers: {
    ollama: "Ollama",
    openai: "OpenAI", 
    custom: "Custom"
  },
  
  // Success/Error Messages
  messages: {
    connectionSuccess: "Connection successful! Models have been loaded.",
    connectionError: "Connection failed. Please check your settings and try again.",
    saveSuccess: "Configuration saved successfully.",
    saveError: "Failed to save configuration. Please try again.",
    loadError: "Failed to load configuration. Please refresh the page.",
    validationError: "Please correct the errors above before saving."
  }
};
```

---

## 8. Accessibility & Responsive Design

### 8.1. Accessibility (A11y) Specifications

```javascript
const accessibilitySpecs = {
  focusManagement: {
    modalOpen: "Focus first interactive element within modal, trap focus inside modal bounds",
    modalClose: "Return focus to the element that triggered the modal (usually a button)",
    tabOrder: "Logical top-to-bottom, left-to-right flow through all interactive elements",
    skipLinks: "Provide skip-to-content link for keyboard users"
  },
  
  ariaRequirements: {
    statusUpdates: "Use aria-live='polite' for connection status changes and loading states",
    errors: "Use aria-live='assertive' for validation errors and critical failures", 
    labels: "All form inputs must have associated <label> or descriptive aria-label",
    descriptions: "Use aria-describedby to link helper text and error messages to inputs",
    expanded: "Use aria-expanded on collapsible sections (advanced settings)",
    roles: "Use appropriate ARIA roles: button, tab, tabpanel, alert, status"
  },
  
  keyboardSupport: {
    tabNavigation: "All interactive elements accessible via Tab/Shift+Tab",
    enterActivation: "Enter key activates buttons and toggles",
    escapeClose: "Escape key closes modals and dropdowns",
    arrowNavigation: "Arrow keys navigate through tab groups",
    spaceToggle: "Space bar toggles checkboxes and switches"
  },
  
  screenReaderSupport: {
    announcements: {
      connectionSuccess: "Connection successful. Model list has been updated.",
      saveSuccess: "Configuration has been saved successfully.",
      saveFailure: "Save failed. Please correct the errors and try again.",
      tabChange: "Switched to {tabName} tab.",
      validationError: "Error in {fieldName}: {errorMessage}"
    },
    landmarks: "Use semantic HTML5 landmarks: main, section, nav, form",
    headings: "Proper heading hierarchy (h1 > h2 > h3) for page structure"
  },
  
  colorContrast: {
    requirement: "All text meets WCAG 2.1 AA contrast ratios (4.5:1 for normal text, 3:1 for large text)",
    verification: "Test with automated tools (axe-core) and manual verification",
    alternatives: "Don't rely solely on color to convey information (use icons, text, patterns)"
  }
};
```

### 8.2. Responsive Design Specifications

```javascript
const responsiveSpecs = {
  breakpoints: {
    sm: "640px", // Small tablets and large phones
    md: "768px", // Tablets and small laptops  
    lg: "1024px", // Large tablets and laptops
    xl: "1280px" // Desktops
  },
  
  layoutBehavior: {
    mobile: {
      maxWidth: "767px",
      primaryTabs: "Transform into full-width <select> dropdown with proper styling",
      cards: "Stack vertically with 16px gaps instead of 24px",
      form: "Single-column layout for all form groups",
      saveBar: "Full-width sticky bar with stacked buttons on very small screens",
      padding: "Reduce page padding from 32px to 16px",
      typography: "Slightly smaller font sizes for space efficiency"
    },
    
    tablet: {
      minWidth: "768px",
      maxWidth: "1023px", 
      primaryTabs: "Maintain horizontal tab layout with adjusted spacing",
      cards: "Two-column grid where appropriate",
      form: "Mix of single and two-column layouts based on content",
      saveBar: "Maintain desktop layout with proper spacing"
    },
    
    desktop: {
      minWidth: "1024px",
      primaryTabs: "Full horizontal tab layout as specified",
      cards: "Optimal grid layouts with full spacing",
      form: "Two-column layouts where beneficial",
      saveBar: "Full desktop layout with optimal button positioning"
    }
  },
  
  touchTargets: {
    minimumSize: "44px x 44px for all interactive elements on touch devices",
    spacing: "Minimum 8px spacing between adjacent touch targets",
    feedback: "Clear visual feedback for touch interactions"
  },
  
  viewport: {
    meta: '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
    minWidth: "320px", // Minimum supported screen width
    maxWidth: "1920px" // Maximum optimized screen width
  }
};
```

---

## 9. Development Guidelines & Testing

### 9.1. Development Constraints

```javascript
const developmentConstraints = {
  framework: {
    primary: "React 18+ with TypeScript",
    buildTool: "Vite",
    styling: "TailwindCSS v3.x",
    icons: "Lucide React",
    stateManagement: "React hooks (useState, useReducer, useMemo)"
  },
  
  browserSupport: {
    chrome: "90+",
    firefox: "88+", 
    safari: "14+",
    edge: "91+",
    mobile: "iOS Safari 14+, Chrome Mobile 90+"
  },
  
  performance: {
    pageLoad: "Largest Contentful Paint (LCP) < 2.5 seconds",
    interactivity: "First Input Delay (FID) < 100ms",
    validation: "Form validation response < 100ms",
    bundleSize: "Main chunk < 250kB gzipped",
    renderTime: "Component render time < 16ms"
  },
  
  codeQuality: {
    typescript: "Strict mode enabled, no 'any' types",
    linting: "ESLint with React and TypeScript rules",
    formatting: "Prettier with consistent configuration",
    bundleAnalysis: "Monitor bundle size with each build"
  }
};
```

### 9.2. Testing Requirements

```javascript
const testingRequirements = {
  unitTests: {
    coverage: ">80% for hooks, utilities, and components",
    framework: "Jest + React Testing Library",
    focus: "useConfiguration hook, useFormState hook, validation functions, utility functions"
  },
  
  integrationTests: {
    userFlows: [
      "Load configuration data and populate form",
      "Edit form fields and observe dirty state changes", 
      "Test provider connection (success and failure scenarios)",
      "Save configuration and handle success/error responses",
      "Revert changes and confirm state reset",
      "Navigate between tabs and maintain form state",
      "Toggle advanced settings and persist preferences"
    ],
    apiMocking: "Mock all API endpoints with realistic success/error responses",
    stateValidation: "Verify state transitions and data flow integrity"
  },
  
  accessibilityTests: {
    automated: "axe-core integration with jest-axe for automated a11y testing",
    keyboard: "Manual testing of all keyboard navigation and interaction",
    screenReader: "Manual testing with VoiceOver (macOS) and NVDA (Windows)",
    colorContrast: "Automated and manual verification of WCAG 2.1 AA compliance",
    focusManagement: "Verify focus trap in modals and logical tab order"
  },
  
  visualTests: {
    responsive: "Test all breakpoints and layout adaptations",
    crossBrowser: "Verify appearance and functionality across supported browsers",
    darkMode: "If applicable, test dark mode color schemes",
    animations: "Verify smooth transitions and loading states"
  },
  
  performanceTests: {
    lighthouse: "Lighthouse CI with performance budgets",
    bundleSize: "Bundle analyzer to monitor code splitting and chunk sizes",
    memoryLeaks: "Test for memory leaks in long-running sessions",
    rendering: "React DevTools Profiler for render performance"
  }
};
```

### 9.3. Implementation Checklist

```markdown
## Development Phase
- [ ] **Project Setup**
  - [ ] Tailwind config with custom colors and fonts
  - [ ] TypeScript interfaces and types defined
  - [ ] Component class specifications implemented
  - [ ] Icon library integrated (Lucide React)

- [ ] **API Layer**
  - [ ] GET /api/v1/config endpoint integration
  - [ ] POST /api/v1/config endpoint integration  
  - [ ] POST /api/v1/config/test-connection endpoint integration
  - [ ] Error handling for all HTTP status codes
  - [ ] Fallback defaults implementation

- [ ] **Core Components**
  - [ ] ConfigurationPage with tab navigation
  - [ ] ProviderConfigCard with all states and interactions
  - [ ] GlobalSaveBar with dirty state detection
  - [ ] ConfirmationModal for revert actions
  - [ ] Toast notification system

- [ ] **State Management**
  - [ ] useConfiguration hook with API state management
  - [ ] useFormState hook with dirty detection
  - [ ] Form validation with debounced execution
  - [ ] Advanced settings toggle state persistence

- [ ] **UI/UX Features**
  - [ ] Responsive design for mobile, tablet, desktop
  - [ ] Loading states for all async operations
  - [ ] Empty states and error handling
  - [ ] Advanced settings toggle with animation
  - [ ] Connection testing with status indicators

## Testing Phase
- [ ] **Unit Tests**
  - [ ] All hooks tested with >80% coverage
  - [ ] Validation functions tested
  - [ ] Utility functions tested
  - [ ] Component rendering tested

- [ ] **Integration Tests**
  - [ ] Complete user flows tested
  - [ ] API integration tested with mocked responses
  - [ ] State transitions verified
  - [ ] Error scenarios covered

- [ ] **Accessibility Tests**
  - [ ] Automated axe-core tests passing
  - [ ] Keyboard navigation verified
  - [ ] Screen reader compatibility tested
  - [ ] Focus management verified
  - [ ] ARIA attributes implemented correctly

- [ ] **Cross-Browser Tests**
  - [ ] Chrome 90+ verified
  - [ ] Firefox 88+ verified
  - [ ] Safari 14+ verified
  - [ ] Edge 91+ verified
  - [ ] Mobile browsers tested

## Quality Assurance
- [ ] **Performance Verification**
  - [ ] Lighthouse score >90 for performance
  - [ ] Bundle size within constraints
  - [ ] Form validation under 100ms
  - [ ] Page load under 2.5s

- [ ] **Visual Verification**
  - [ ] All component classes applied correctly
  - [ ] Responsive breakpoints working
  - [ ] Animations smooth and performant
  - [ ] Color contrast meets WCAG AA

- [ ] **Functional Verification**
  - [ ] All copy text implemented from catalog
  - [ ] Form validation rules working correctly
  - [ ] Connection testing functioning
  - [ ] Save/revert operations working
  - [ ] Toast notifications displaying properly
```

---

## 10. Definition of Done

The Configuration Page Redesign is considered **complete** when:

1. **All implementation checklist items are verified** ✅
2. **All automated tests are passing** in the CI/CD pipeline ✅
3. **Manual accessibility testing** confirms WCAG 2.1 AA compliance ✅
4. **Cross-browser compatibility** verified on all supported browsers ✅
5. **Performance metrics meet specified targets** (LCP < 2.5s, bundle < 250kB) ✅
6. **Code review completed** with no blocking issues ✅
7. **QA sign-off** after manual testing of all user flows ✅
8. **Product owner approval** after reviewing against original requirements ✅

**Final Validation:** The feature must be manually verified against every section of this specification document to ensure no requirements were missed or misimplemented.