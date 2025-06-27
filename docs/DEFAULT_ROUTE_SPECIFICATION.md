# Default Route Specification

## 1. Change Overview
This document specifies a change to the application's default route. The **Configuration Page** will now be the primary entry point for the dashboard.

## 2. Requirement
- The default route (`/`) must render the `ConfigurationPage` component.

## 3. Implementation Guidance
- **Target File**: The main application router (likely `src/web_ui/static/web/src/App.tsx`).
- **Action**: Modify the routing configuration to map the path `/` to the `ConfigurationPage` component.

## 4. User Experience
- On initial application load, users will land directly on the system configuration interface.
- This prioritizes configuration as the primary user flow.