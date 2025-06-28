# Detailed 10-Pass Plan for `admin-ui` Overhaul

This document outlines a comprehensive 10-pass plan to refactor and enhance the `admin-ui` of the Docaiche project. The primary goals are to simplify the user interface, streamline the AI provider configuration, and align the frontend with a backend-centric communication model.

## Pass 1: Project Cleanup and Dependency Consolidation

**Objective:** Remove unused components, pages, and dependencies inherited from the original template to create a clean and maintainable codebase.

1.  **Analyze `package.json`:** Identify and remove any unused or unnecessary npm packages.
2.  **Audit Components:** Review all components in `src/components` and delete those that are not relevant to the Docaiche application.
3.  **Purge Unused Pages:** Delete all pages and associated components within `src/app/dashboard` that are not needed for the final application (e.g., `analytics`, `kanban`, `product`, `profile`).
4.  **Review `src/lib` and `src/hooks`:** Remove any utility functions or hooks that are no longer in use after the component and page cleanup.
5.  **Clean up `public` directory:** Remove any unnecessary images, icons, or other assets.

## Pass 2: Navigation and Layout Simplification

**Objective:** Implement a single-level left-side navigation menu and a simplified layout.

1.  **Modify `src/app/dashboard/layout.tsx`:** Update the layout to support a single-level navigation structure.
2.  **Refactor Navigation Components:** Create or modify the navigation components to render a single-level menu. The menu items should be:
    *   Overview
    *   Content Management
    *   AI Configuration
    *   Health Check
3.  **Update Routing:** Ensure the routing in `src/app/dashboard` reflects the new simplified navigation.
4.  **Consolidate Styles:** Review and refactor the CSS (`globals.css`, `theme.css`, and component-specific styles) to remove any styles related to the old multi-level menu.

## Pass 3: API Client and Backend Communication

**Objective:** Establish a robust and centralized API client for all frontend-to-backend communication, ensuring no direct calls are made to external providers from the client.

1.  **Create an API Client:** Implement a dedicated API client (e.g., using `axios` or `fetch`) to handle all requests to the backend. This client should be easily configurable to use the backend's base URL.
2.  **Define API Contracts:** Create TypeScript types or interfaces for all API requests and responses to ensure type safety and consistency.
3.  **Proxy All External Calls:** Ensure that all interactions with AI providers are proxied through the backend. The frontend should only ever call the Docaiche backend.
4.  **Implement Error Handling:** Create a centralized error handling mechanism in the API client to manage different types of errors (e.g., network errors, server errors, validation errors) and provide appropriate feedback to the user.

## Pass 4: AI Configuration Page - Initial Setup

**Objective:** Create the initial structure and layout for the new AI Configuration page.

1.  **Create the Page:** Create a new page at `src/app/dashboard/ai-configuration/page.tsx`.
2.  **Design the Layout:** Design a two-section layout for the page:
    *   **Text Generation Configuration:** A section for configuring the text generation model.
    *   **Embedding Configuration:** A section for configuring the embedding model.
3.  **Component Scaffolding:** Create placeholder components for the provider connection, model selection, and configuration options for both sections.

## Pass 5: AI Configuration Page - Provider Connection

**Objective:** Implement the provider connection functionality, including testing the connection and fetching available models.

1.  **Provider Connection Component:** Create a reusable component for connecting to an AI provider. This component should include:
    *   A dropdown to select the provider (e.g., OpenAI, Anthropic, Google).
    *   An input field for the API key.
    *   A "Test Connection" button.
2.  **Backend API Endpoints:** Create the necessary backend API endpoints to:
    *   Test the connection to the provider.
    *   Fetch a list of available models from the provider.
3.  **Frontend Logic:** Implement the frontend logic to:
    *   Call the backend to test the connection when the "Test Connection" button is clicked.
    *   On a successful connection, call the backend to fetch the list of available models.
    *   Populate the model selection dropdown with the fetched models.

## Pass 6: AI Configuration Page - Text and Embedding Configuration

**Objective:** Implement the separate configuration sections for text generation and embedding models.

1.  **Shared Provider Logic:** Implement a mechanism to allow both the text and embedding configurations to use the same provider connection if desired. This could be a checkbox or a dropdown to select an already configured provider.
2.  **Text Generation Configuration:**
    *   A dropdown to select the text generation model from the list of available models.
    *   Input fields for any specific configuration options for the text generation model (e.g., temperature, max tokens).
3.  **Embedding Configuration:**
    *   A dropdown to select the embedding model from the list of available models.
    *   Input fields for any specific configuration options for the embedding model.
4.  **Save Configuration:**
    *   A "Save" button to save the entire AI configuration.
    *   A backend API endpoint to save the configuration to the database.

## Pass 7: State Management

**Objective:** Implement a robust state management solution for the `admin-ui`.

1.  **Choose a State Management Library:** Select and integrate a state management library (e.g., Zustand, Redux Toolkit) to manage the application's state.
2.  **Global State:** Create a global store for managing user authentication, navigation state, and other application-wide state.
3.  **AI Configuration State:** Create a dedicated store for managing the AI configuration page's state, including provider connections, model lists, and configuration settings.
4.  **API State:** Manage the state of API requests (e.g., loading, success, error) within the state management solution.

## Pass 8: UI Polishing and Theming

**Objective:** Refine the user interface, ensuring a consistent and polished look and feel.

1.  **Component Library:** Utilize a component library (e.g., Shadcn/UI, Material-UI) to ensure a consistent design system across the application.
2.  **Theming:** Implement a theming solution that allows for easy customization of colors, fonts, and other design tokens.
3.  **Responsive Design:** Ensure that all pages and components are fully responsive and work well on different screen sizes.
4.  **Accessibility:** Ensure that the application is accessible to all users by following best practices for accessibility (e.g., proper use of semantic HTML, ARIA attributes).

## Pass 9: Health Check Page

**Objective:** Create a page to display the health of the system and its components.

1.  **Create the Page:** Create a new page at `src/app/dashboard/health/page.tsx`.
2.  **Backend API Endpoint:** Create a backend API endpoint that returns the health status of the system, including the database, AI providers, and other critical services.
3.  **Display Health Status:** Display the health status of each component in a clear and easy-to-understand format. Use icons and colors to indicate the status (e.g., green for healthy, red for unhealthy).

## Pass 10: Final Review and Testing

**Objective:** Perform a final review of the entire `admin-ui` to ensure it meets all requirements and is free of bugs.

1.  **Code Review:** Conduct a thorough code review of the entire `admin-ui` codebase.
2.  **End-to-End Testing:** Perform end-to-end testing of all features, including:
    *   Navigation and routing.
    *   AI provider configuration.
    *   Content management.
    *   Health checks.
3.  **User Acceptance Testing (UAT):** If possible, have a user test the application to provide feedback and identify any usability issues.
4.  **Documentation:** Update the `README.md` file with instructions on how to set up and run the `admin-ui`.
