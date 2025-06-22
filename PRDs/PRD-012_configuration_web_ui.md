# PRD-012: Configuration Web UI

## Overview
Specifies a simple, unauthenticated web interface for system administration. Provides a dashboard for monitoring health, viewing/updating configuration, and managing content.

## Technical Boundaries
- Standalone web application, served by FastAPI.
- Built with Jinja2 templates and minimal JavaScript.
- Interacts with backend exclusively through REST API endpoints.

## Success Criteria
- All specified pages and features are implemented and functional.
- UI accurately reflects real-time system status.
- Configuration changes are applied and persisted.

## Dependencies
| Component/PRD | Purpose |
|---------------|---------|
| PRD-001: HTTP API Foundation | Exposes API endpoints for UI |
| PRD-003: Configuration Management | Provides config data |
| PRD-002: Database & Caching Layer | Provides content and stats |
| PRD-011: Feedback Collection System | Provides feedback data |

## Cross-References
- Calls endpoints defined in [HTTP API Foundation](PRD-001_HTTP_API_Foundation.md) for health, stats, config, and content management.
- Displays configuration from [Configuration Management](PRD-003_Config_Mgmt_System.md).
- Shows content and feedback from [Database & Caching Layer](PRD-002_DB_and_Caching_Layer.md) and [Feedback Collection System](PRD-011_feedback_collection_system.md).

## UI Pages and Features

| Page      | Features                                                                                   |
|-----------|-------------------------------------------------------------------------------------------|
| Dashboard | Health status (from /api/v1/health), key metrics (/api/v1/stats), recent queries table     |
| Config    | View and update system configuration (/api/v1/config)                                      |
| Content   | List collections (/api/v1/collections), search content, flag for removal                   |

## Implementation Tasks

| Task ID | Description |
|---------|-------------|
| UI-001  | Configure FastAPI to serve static files and Jinja2Templates |
| UI-002  | Create base HTML template with Tailwind CSS and navigation  |
| UI-003  | Implement Dashboard page with auto-refreshing stats         |
| UI-004  | Implement Configuration page with config view/update form   |
| UI-005  | Implement Content Management page with search and flagging  |
| UI-006  | Implement "Flag for Removal" button with JS event listener  |
| UI-007  | Ensure responsive design with Tailwind CSS                  |
| UI-008  | Add /api/v1/admin/search-content endpoint for admin lookup  |

## Integration Contracts
- Produces standard HTML, CSS, and JavaScript.
- Interacts with system exclusively through /api/v1/* endpoints.

## Summary Tables

### Endpoints Table

| Method | Endpoint                    | Description                        |
|--------|-----------------------------|------------------------------------|
| GET    | /api/v1/health              | System health status               |
| GET    | /api/v1/stats               | Usage and performance stats        |
| GET    | /api/v1/collections         | List documentation collections     |
| GET    | /api/v1/config              | Get current configuration          |
| POST   | /api/v1/config              | Update configuration               |
| DELETE | /api/v1/content/{content_id}| Flag content for removal           |
| GET    | /api/v1/admin/search-content| Admin content search               |

### Implementation Tasks Table
(see Implementation Tasks above)

---