sequenceDiagram
    autonumber
    participant User
    participant Browser
    participant Backend
    participant Database
    participant Provider
    
    %% Initial Page Load
    Note over User,Provider: Initial Page Load
    Browser->>Backend: Request configuration page
    Backend->>Database: Get configurations
    Database-->>Backend: Return provider & model data
    Backend-->>Browser: Send configurations
    Browser->>Browser: Update state & render UI
    Browser-->>User: Display available providers & settings
    
    %% Provider Configuration & Testing
    Note over User,Provider: Provider Configuration & Testing
    User->>Browser: Select provider
    User->>Browser: Enter connection details
    User->>Browser: Click "Test Connection" button
    Browser->>Backend: Send test request with provider config
    Backend->>Provider: Send test query
    Provider-->>Backend: Return response
    
    alt Test Successful
        Backend->>Database: Save provider configuration
        Database-->>Backend: Confirm save
        Backend-->>Browser: Send success with available models
        Browser->>Browser: Display success toast
        Browser->>Browser: Update model selection dropdowns
    else Test Failed
        Backend-->>Browser: Send error message
        Browser-->>User: Display error message
    end
    
    %% Model Selection & Saving
    Note over User,Provider: Model Selection & Saving
    User->>Browser: Select text & embedding models
    User->>Browser: Click "Save Configuration" button
    Browser->>Browser: Display saving toast
    Browser->>Backend: Send model configuration
    Backend->>Database: Save model configuration
    Database-->>Backend: Confirm save
    Backend-->>Browser: Send confirmation & updated config
    Browser->>Browser: Display success toast
    Browser->>Browser: Update configuration display
    
    %% Service Updates
    par Service Updates
        Backend->>Database: Get saved configuration
        Database-->>Backend: Return configuration
        Backend->>Backend: Update services
        Backend->>Backend: Restart services if needed
        Backend->>Backend: Log operations
    end
    
    %% Page Reload (Future)
    Note over User,Provider: Page Reload (Later)
    User->>Browser: Reload page
    Browser->>Backend: Request configuration
    Backend->>Database: Get configurations
    Database-->>Backend: Return provider & model data
    Backend-->>Browser: Send configurations
    Browser->>Browser: Update state & render UI
    Browser-->>User: Display providers & current settings