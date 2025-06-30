# Task 11: API Integration & Connection Testing

## Overview
Implement the complete API integration for configuration management including fetching, saving, and connection testing functionality with proper error handling.

## Reference Specification Sections
- Section 3.1: Endpoints (API contracts)
- Section 3.3: API Error Handling Matrix
- Section 6.2: UI States & Loading Behavior

## Task Requirements

### 1. Configuration API Service
- [ ] Create `src/services/configurationApi.ts` with:
  - `fetchConfiguration()` - GET /api/v1/config
  - `saveConfiguration(config)` - POST /api/v1/config
  - `testConnection(request)` - POST /api/v1/config/test-connection
  - Proper TypeScript interfaces for all requests/responses
  - Error handling for all HTTP status codes

### 2. API Integration in useConfiguration Hook
- [ ] Update `useConfiguration.ts` hook to:
  - Fetch initial configuration on mount
  - Handle loading states during API calls
  - Implement proper error handling with fallback defaults
  - Manage API response states (success, error, loading)

### 3. Connection Testing Implementation
- [ ] **Test Connection Flow**:
  - Validate form data before testing
  - Display "Testing..." state with animated spinner
  - Show "Still trying to connect..." after 8 seconds
  - Handle success response with available models
  - Handle error responses with appropriate messages
- [ ] **Model Loading Logic**:
  - Populate model dropdown on successful connection test
  - Clear model field when connection details change
  - Show "Loading models..." option during test

### 4. API Error Handling Implementation
- [ ] Implement error handling matrix from Section 3.3:
  - **400 Bad Request**: Show field-specific validation errors
  - **401 Unauthorized**: Redirect to login (placeholder for now)
  - **422 Validation Error**: Display API validation errors on fields
  - **500 Server Error**: Show global error toast with retry option
  - **Timeout**: Show timeout message with retry option

### 5. Loading States Integration
- [ ] **Page Initial Load**:
  - Show skeleton cards during initial configuration fetch
  - Display loading spinners in form fields
  - Handle failed loads with retry mechanism
- [ ] **Save Operation**:
  - Disable form during save
  - Show progress in global save bar
  - Display success/error toasts
- [ ] **Connection Testing**:
  - Button shows spinner and "Testing..." text
  - Disable form fields during test
  - Show connection status indicators

### 6. Fallback Defaults Integration
- [ ] Implement fallback defaults from Section 3.4:
  - Use defaults when initial API call fails
  - Show warning toast when fallbacks are used
  - Allow retry of initial configuration load

### 7. Toast Notifications Integration
- [ ] **Success Messages**:
  - "Configuration saved successfully"
  - "Connection successful! Models have been loaded"
- [ ] **Error Messages**:
  - API-specific error messages
  - Network timeout messages
  - Validation error summaries
- [ ] **Warning Messages**:
  - "Using fallback defaults due to connection issue"

### 8. Request/Response Validation
- [ ] Validate all outgoing requests match API schemas
- [ ] Handle malformed API responses gracefully
- [ ] Implement request timeout handling (30 seconds)

### 9. API Request/Response Logging Implementation
- [ ] Implement comprehensive API logging from Section 10.2:
  - Log all API requests with endpoint, method, and sanitized request body
  - Log API responses with status codes, response times, and sizes
  - Log API errors with full context and error recovery actions
  - Ensure sensitive data (API keys) is properly redacted in logs
  - Include request IDs for correlation and debugging
  - Log connection test results and model loading events

## Acceptance Criteria
- [ ] Configuration loads correctly on page initialization
- [ ] Save functionality works with proper success/error handling
- [ ] Connection testing works for all provider types
- [ ] Model loading populates dropdowns correctly
- [ ] All error scenarios display appropriate user messages
- [ ] Loading states show during all API operations
- [ ] Fallback defaults work when API is unavailable
- [ ] Toast notifications display for all API operations
- [ ] API timeouts are handled gracefully
- [ ] Retry mechanisms work for failed operations

## Evidence of Completion
To mark this task complete, provide:
1. Screenshot of successful configuration loading with real API data
2. Screenshot/video of connection testing flow (testing → success → models loaded)
3. Screenshot showing error handling for different HTTP status codes
4. Screenshot of fallback defaults loading when API fails
5. Screenshot of loading states during API operations
6. Code snippet showing the API service implementation

## Dependencies
- Task 10: Embedding Provider Toggle Implementation

## Next Task
After completion, proceed to Task 12: Loading States & Error Handling Polish