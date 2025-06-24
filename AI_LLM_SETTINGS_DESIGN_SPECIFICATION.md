# AI/LLM Settings Enhanced Design Specification

## Executive Summary
This document specifies design improvements for the AI/LLM configuration interface, transforming the current basic text input system into a dynamic, intelligent configuration system similar to Roo Code's implementation.

## Current State Analysis

### Issues with Existing Implementation
- **Static Model Input**: Current [`config.html:189-192`](src/web_ui/templates/config.html:189) uses simple text input for model selection
- **No Endpoint Configuration**: Missing base URL configuration for different providers
- **No Model Discovery**: No dynamic querying of available models from endpoints
- **Limited Provider Support**: Basic dropdown without endpoint-specific behavior
- **Poor User Experience**: Users must manually know model names and endpoints

### Current Code Structure
```html
<!-- Current AI/LLM Settings (Lines 167-205) -->
<div class="bg-white shadow-sm rounded-lg border border-gray-200">
    <div class="grid grid-cols-1 gap-6 sm:grid-cols-2">
        <select id="llm_provider" name="llm_provider">
            <option value="ollama">Ollama</option>
            <option value="openai">OpenAI</option>
            <option value="anthropic">Anthropic</option>
        </select>
        <input type="text" id="llm_model" name="llm_model" placeholder="llama2">
    </div>
</div>
```

## Enhanced Design Specifications

### 1. Component Layout Structure
```
┌─ AI/LLM Settings ────────────────────────────────────────────────────────┐
│ ┌─ Provider Configuration ──────────────────────────────────────────────┐ │
│ │                                                                       │ │
│ │  Provider Type: [Ollama            ▼] [●] Connected                   │ │
│ │                                                                       │ │
│ │  Base URL: [http://localhost:11434/api        ] [Test Connection]     │ │
│ │                                                                       │ │
│ │  API Key:  [********************************** ] [👁] (Optional)     │ │
│ │                                                                       │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│ ┌─ Model Selection ─────────────────────────────────────────────────────┐ │
│ │                                                                       │ │
│ │  Available Models:                                                    │ │
│ │  [Select a model...                    ▼] [🔄 Refresh Models]        │ │
│ │                                                                       │ │
│ │  Model Info: llama3.2:3b (3.2B parameters, Instruct-tuned)          │ │
│ │                                                                       │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│ ┌─ Advanced Parameters ─────────────────────────────────────────────────┐ │
│ │  ▼ Show Advanced Settings                                             │ │
│ │                                                                       │ │
│ │  Max Tokens:    [2048      ] │ Temperature: [0.7    ]                │ │
│ │  Top-P:         [1.0       ] │ Top-K:       [40     ]                │ │
│ │  Timeout (sec): [30        ] │ Retries:     [3      ]                │ │
│ │                                                                       │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  [Test Model Response] [Save Configuration]                              │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

### 2. Component Specifications

#### 2.1 Provider Type Dropdown
```css
/* Component: provider-dropdown */
.provider-dropdown {
    width: 200px;
    height: 40px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    background: white;
    font-size: 14px;
}

.provider-option {
    display: flex;
    align-items: center;
    padding: 8px 12px;
}

.provider-icon {
    width: 16px;
    height: 16px;
    margin-right: 8px;
}
```

**Provider Options:**
- **Ollama**: Icon + "Ollama (Local)" 
  - Default URL: `http://localhost:11434/api`
  - Models endpoint: `/api/tags`
- **OpenAI**: Icon + "OpenAI"
  - Default URL: `https://api.openai.com/v1`
  - Models endpoint: `/models`
- **OpenAI Compatible**: Icon + "OpenAI Compatible"
  - Default URL: (user configured)
  - Models endpoint: `/models`
- **Anthropic**: Icon + "Anthropic Claude"
  - Default URL: `https://api.anthropic.com`
  - Models endpoint: Custom implementation
- **Custom**: Icon + "Custom Endpoint"
  - Default URL: (user configured)
  - Models endpoint: (user configured)

#### 2.2 Connection Status Indicator
```css
/* Component: connection-status */
.connection-status {
    display: inline-flex;
    align-items: center;
    margin-left: 12px;
    font-size: 12px;
    font-weight: 500;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 6px;
}

.status-connected { background-color: #10b981; }
.status-testing { 
    background-color: #f59e0b; 
    animation: pulse 1.5s infinite;
}
.status-error { background-color: #ef4444; }
.status-disconnected { background-color: #6b7280; }
```

**Status States:**
- 🟢 **Connected**: "Connected" (green)
- 🟡 **Testing**: "Testing..." (amber, pulsing)
- 🔴 **Error**: "Connection Failed" (red)
- ⚫ **Not Configured**: "Not Configured" (gray)

#### 2.3 Base URL Input Field
```css
/* Component: base-url-input */
.base-url-input {
    flex: 1;
    height: 40px;
    padding: 0 12px;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 13px;
}

.base-url-input:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.base-url-input.error {
    border-color: #ef4444;
    background-color: #fef2f2;
}
```

**Behavior:**
- Auto-populate when provider changes
- Real-time URL validation
- Show protocol (http/https) indicators
- Auto-complete from recent/common endpoints

#### 2.4 Model Selection Dropdown
```css
/* Component: model-dropdown */
.model-dropdown {
    position: relative;
    width: 100%;
}

.model-dropdown-button {
    width: 100%;
    height: 40px;
    padding: 0 12px;
    text-align: left;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    background: white;
    cursor: pointer;
}

.model-dropdown-content {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    max-height: 300px;
    overflow-y: auto;
    background: white;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    z-index: 1000;
}

.model-option {
    padding: 12px;
    cursor: pointer;
    border-bottom: 1px solid #f3f4f6;
}

.model-option:hover {
    background-color: #f9fafb;
}

.model-name {
    font-weight: 500;
    font-size: 14px;
    color: #111827;
}

.model-description {
    font-size: 12px;
    color: #6b7280;
    margin-top: 2px;
}
```

**Model Display Format:**
```
llama3.2:3b
├─ Name: "llama3.2:3b"
├─ Description: "3.2B parameters, Instruct-tuned"
├─ Size: "2.0 GB"
└─ Modified: "2 days ago"
```

#### 2.5 Advanced Settings Collapsible Section
```css
/* Component: advanced-settings */
.advanced-settings {
    margin-top: 24px;
}

.advanced-settings-toggle {
    display: flex;
    align-items: center;
    cursor: pointer;
    padding: 8px 0;
    font-weight: 500;
    color: #374151;
}

.advanced-settings-toggle:hover {
    color: #111827;
}

.toggle-icon {
    width: 16px;
    height: 16px;
    margin-right: 8px;
    transition: transform 0.2s ease;
}

.toggle-icon.expanded {
    transform: rotate(90deg);
}

.advanced-settings-content {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-top: 16px;
    padding: 16px;
    background-color: #f9fafb;
    border-radius: 6px;
}

@media (max-width: 768px) {
    .advanced-settings-content {
        grid-template-columns: 1fr;
    }
}
```

### 3. Interaction Flow Specifications

#### 3.1 Model Discovery Workflow
```
┌─ User Flow: Model Discovery ─────────────────────────────────────────────┐
│                                                                          │
│  1. User selects provider type                                          │
│     ↓                                                                    │
│  2. Auto-populate base URL for provider                                 │
│     ↓                                                                    │
│  3. Enable "Test Connection" button                                     │
│     ↓                                                                    │
│  4. User clicks "Test Connection"                                       │
│     ↓                                                                    │
│  5. Show loading state: "Testing connection..."                        │
│     ├─ Check endpoint accessibility                                     │
│     ├─ Validate API key (if required)                                   │
│     └─ Query available models                                           │
│     ↓                                                                    │
│  6. Connection successful?                                              │
│     ├─ YES: Show green status, populate models dropdown                 │
│     └─ NO: Show red status, display error message                       │
│     ↓                                                                    │
│  7. User selects model from dropdown                                    │
│     ↓                                                                    │
│  8. Display model information and enable "Save Configuration"          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

#### 3.2 Connection Testing States
```css
/* Loading State Animation */
@keyframes connection-test {
    0% { content: "Testing connection"; }
    25% { content: "Testing connection."; }
    50% { content: "Testing connection.."; }
    75% { content: "Testing connection..."; }
    100% { content: "Testing connection"; }
}

.connection-testing::after {
    animation: connection-test 1s infinite;
}
```

**Testing Steps Display:**
```
┌─ Connection Test Progress ──────────────────────────────────────────────┐
│                                                                         │
│  Testing connection to http://localhost:11434/api                      │
│  ████████████████████████████████████████████████████ 100%            │
│                                                                         │
│  ✓ Endpoint accessible                                                 │
│  ✓ API key validated                                                   │
│  ✓ Fetching available models...                                        │
│  ✓ Found 12 models                                                     │
│                                                                         │
│  Connection successful!                                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 4. Error Handling Design

#### 4.1 Error Types and Messages
```css
/* Component: error-message */
.error-message {
    padding: 12px;
    background-color: #fef2f2;
    border: 1px solid #fecaca;
    border-radius: 6px;
    color: #991b1b;
    font-size: 14px;
    margin-top: 8px;
}

.error-icon {
    width: 16px;
    height: 16px;
    color: #dc2626;
    margin-right: 8px;
}

.error-details {
    margin-top: 8px;
    font-size: 12px;
    color: #7f1d1d;
}

.error-actions {
    margin-top: 12px;
    display: flex;
    gap: 8px;
}

.retry-button {
    padding: 4px 8px;
    background-color: #dc2626;
    color: white;
    border: none;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
}
```

**Error Messages:**
- **Network Error**: "Cannot reach endpoint. Check URL and network connection."
- **Authentication Error**: "Invalid API key. Please verify your credentials."
- **Timeout Error**: "Connection timeout. The endpoint may be slow or unavailable."
- **Invalid Response**: "Unexpected response format. Verify endpoint compatibility."
- **No Models Found**: "No models available at this endpoint."

#### 4.2 Error Display Pattern
```
┌─ Error State Example ───────────────────────────────────────────────────┐
│                                                                         │
│  ⚠️ Connection Failed                                                   │
│                                                                         │
│  Cannot reach endpoint at http://localhost:11434/api                   │
│                                                                         │
│  Details:                                                               │
│  • Network error: Connection refused                                   │
│  • Ensure Ollama is running on localhost:11434                        │
│  • Check firewall settings                                             │
│                                                                         │
│  [Retry Connection] [Check Documentation]                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5. Responsive Design Specifications

#### 5.1 Desktop Layout (1200px+)
```css
.ai-llm-settings-desktop {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
}

.provider-config-section {
    grid-column: 1 / -1;
}

.model-selection-section {
    grid-column: 1 / -1;
}

.advanced-settings-section {
    grid-column: 1 / -1;
}
```

#### 5.2 Tablet Layout (768px-1199px)
```css
.ai-llm-settings-tablet {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.provider-row {
    display: flex;
    gap: 12px;
    align-items: center;
}

.base-url-input {
    flex: 1;
}

.test-button {
    width: 120px;
}
```

#### 5.3 Mobile Layout (320px-767px)
```css
.ai-llm-settings-mobile {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.provider-config-section,
.model-selection-section,
.advanced-settings-section {
    padding: 16px;
}

.provider-row {
    flex-direction: column;
    gap: 12px;
}

.base-url-input,
.test-button {
    width: 100%;
}

.advanced-settings-content {
    grid-template-columns: 1fr;
}
```

### 6. API Integration Requirements

#### 6.1 Required API Endpoints
```javascript
// API Endpoints for LLM Configuration
const API_ENDPOINTS = {
    // Test connection to LLM endpoint
    testConnection: 'POST /api/v1/llm/test-connection',
    
    // Get available models from endpoint
    getModels: 'GET /api/v1/llm/models',
    
    // Save LLM configuration
    saveConfig: 'POST /api/v1/llm/config',
    
    // Get current LLM configuration
    getConfig: 'GET /api/v1/llm/config',
    
    // Test model response
    testModel: 'POST /api/v1/llm/test-model'
};
```

#### 6.2 API Request/Response Formats
```javascript
// Test Connection Request
{
    "provider": "ollama",
    "base_url": "http://localhost:11434/api",
    "api_key": "optional_key",
    "timeout": 30
}

// Test Connection Response
{
    "success": true,
    "status": "connected",
    "response_time": 150,
    "models_available": 12,
    "endpoint_info": {
        "version": "0.1.47",
        "type": "ollama"
    }
}

// Get Models Response
{
    "models": [
        {
            "name": "llama3.2:3b",
            "size": "2.0GB",
            "modified": "2024-01-15T10:30:00Z",
            "description": "3.2B parameters, Instruct-tuned",
            "parameters": "3.2B",
            "family": "llama"
        }
    ]
}
```

### 7. Implementation Priorities

#### Phase 1: Core Functionality (Week 1-2)
1. ✅ Enhanced provider selection dropdown
2. ✅ Base URL configuration with validation
3. ✅ Connection testing mechanism
4. ✅ Basic model discovery and selection
5. ✅ Connection status indicators

#### Phase 2: Advanced Features (Week 3-4)
1. ✅ Advanced parameter configuration
2. ✅ Model information display
3. ✅ Connection status monitoring
4. ✅ Error handling and retry mechanisms
5. ✅ Responsive design implementation

#### Phase 3: Polish & Integration (Week 5)
1. ✅ Model testing functionality
2. ✅ Configuration import/export
3. ✅ Real-time status updates via WebSocket
4. ✅ Usage analytics integration
5. ✅ Documentation and help system

### 8. Accessibility Requirements

#### 8.1 Screen Reader Support
```html
<!-- ARIA Labels and Descriptions -->
<select id="llm_provider" 
        aria-label="Select LLM Provider"
        aria-describedby="provider-help">
    <option value="ollama">Ollama (Local)</option>
</select>

<div id="provider-help" class="sr-only">
    Choose your preferred LLM provider. Local providers like Ollama 
    don't require API keys.
</div>

<div class="connection-status" 
     role="status" 
     aria-live="polite"
     aria-label="Connection status">
    <span class="status-dot status-connected"></span>
    Connected
</div>
```

#### 8.2 Keyboard Navigation
```css
/* Focus Management */
.focusable:focus {
    outline: 2px solid #3b82f6;
    outline-offset: 2px;
}

/* Skip Links */
.skip-to-model-selection {
    position: absolute;
    left: -9999px;
}

.skip-to-model-selection:focus {
    position: static;
    left: auto;
}
```

**Tab Order:**
1. Provider Type Dropdown
2. Base URL Input
3. Test Connection Button
4. API Key Input (if visible)
5. Model Selection Dropdown
6. Refresh Models Button
7. Advanced Settings Toggle
8. Advanced Parameter Inputs (if expanded)
9. Test Model Response Button
10. Save Configuration Button

### 9. Performance Considerations

#### 9.1 Loading States
```css
/* Skeleton Loading for Model List */
.model-skeleton {
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 12px;
}

.skeleton-line {
    height: 16px;
    background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
    background-size: 200% 100%;
    animation: loading 1.5s infinite;
    border-radius: 4px;
}

@keyframes loading {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
}
```

#### 9.2 Caching Strategy
```javascript
// Model caching to avoid repeated API calls
const ModelCache = {
    cache: new Map(),
    TTL: 5 * 60 * 1000, // 5 minutes
    
    get(endpoint) {
        const cached = this.cache.get(endpoint);
        if (cached && Date.now() - cached.timestamp < this.TTL) {
            return cached.models;
        }
        return null;
    },
    
    set(endpoint, models) {
        this.cache.set(endpoint, {
            models,
            timestamp: Date.now()
        });
    }
};
```

### 10. Testing & Validation

#### 10.1 Component Testing Checklist
- [ ] Provider selection updates base URL correctly
- [ ] Connection testing shows appropriate loading states
- [ ] Model dropdown populates after successful connection
- [ ] Error messages display for various failure scenarios
- [ ] Advanced settings expand/collapse smoothly
- [ ] Form validation prevents invalid configurations
- [ ] Responsive design works across all breakpoints
- [ ] Keyboard navigation follows logical tab order
- [ ] Screen readers announce status changes

#### 10.2 Integration Testing Scenarios
- [ ] Test with Ollama local instance
- [ ] Test with OpenAI API
- [ ] Test with custom OpenAI-compatible endpoints
- [ ] Test connection timeout scenarios
- [ ] Test API key validation
- [ ] Test model selection persistence
- [ ] Test configuration save/load

### 11. Documentation Requirements

#### 11.1 User Help System
```html
<!-- Contextual Help -->
<div class="help-tooltip" data-tooltip="Base URL is the API endpoint for your LLM provider. For Ollama, this is typically http://localhost:11434/api">
    <svg class="help-icon" width="16" height="16">...</svg>
</div>
```

#### 11.2 Setup Guides
- **Ollama Setup**: Step-by-step guide for local Ollama installation
- **OpenAI Configuration**: API key setup and model selection
- **Custom Endpoints**: Guide for configuring custom OpenAI-compatible APIs
- **Troubleshooting**: Common issues and solutions

## Implementation Handoff Notes

### Frontend Developer Requirements
1. **JavaScript Framework**: Vanilla JS or lightweight framework (Alpine.js recommended)
2. **CSS Framework**: Tailwind CSS (already in use)
3. **API Client**: Fetch API with proper error handling
4. **State Management**: Component-level state for form data
5. **WebSocket Integration**: For real-time status updates

### Backend Developer Requirements
1. **API Endpoints**: Implement the 5 required endpoints
2. **Error Handling**: Standardized error response format
3. **Validation**: Server-side validation for all configuration data
4. **Security**: API key encryption and secure storage
5. **Logging**: Request/response logging for debugging

### Quality Assurance Requirements
1. **Cross-browser Testing**: Chrome, Firefox, Safari, Edge
2. **Responsive Testing**: Multiple device sizes and orientations
3. **Accessibility Testing**: Screen reader and keyboard navigation
4. **Performance Testing**: Load times and API response handling
5. **Security Testing**: API key handling and validation

This specification provides a complete blueprint for transforming the AI/LLM settings interface into a professional, user-friendly configuration system that matches modern standards while maintaining consistency with the existing dashboard design.