# PRD-001: HTTP API Foundation

## Overview
Defines the foundational HTTP server using FastAPI. Responsible for all API endpoints, request/response schemas, validation, rate limiting, and error handling. No business logic; endpoints return mock data conforming to schemas.

## Technical Boundaries
- Entry point for all external interactions.
- Interfaces with reverse proxy (e.g., Nginx).
- Will eventually route requests to downstream services (e.g., Search Orchestrator, Feedback Collector).
- Self-contained for initial implementation.

## Success Criteria
- Fully functional API server passing all acceptance criteria.
- Schema validation, rate limiting, and correct error responses.
- Auto-generated OpenAPI documentation accurately reflects the API contract.

## Dependencies
| Component/PRD | Purpose |
|---------------|---------|
| PRD-002: Database & Caching Layer | For persistent storage and caching |
| PRD-003: Configuration Management | For loading API configuration |
| PRD-011: Feedback Collection System | For feedback endpoints |
| PRD-009: Search Orchestration Engine | For search workflow integration |

## Cross-References
- Uses `DatabaseManager` and `CacheManager` from PRD-002.
- Calls `feedback_collector` from PRD-011.
- Integrates with endpoints defined in PRD-009.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST   | /api/v1/search         | Initiates a search query |
| GET    | /api/v1/search         | GET alternative for simple queries and browser testing |
| POST   | /api/v1/feedback       | Submits explicit user feedback on a search result |
| POST   | /api/v1/signals        | Submits implicit user interaction signals (e.g., clicks) |
| DELETE | /api/v1/content/{id}   | Flags content for removal (admin action) |
| GET    | /api/v1/health         | Reports the health of the system and its dependencies |
| GET    | /api/v1/stats          | Provides usage and performance statistics |
| GET    | /api/v1/collections    | Lists available documentation collections (workspaces) |
| POST   | /api/v1/config         | Updates a specific part of the system configuration |
| GET    | /api/v1/config         | Retrieves the current system configuration |
| GET    | /api/v1/admin/search-content | Searches content metadata for admin management |
| GET    | /docs                  | Serves the auto-generated OpenAPI (Swagger UI) documentation |

## Error Response Schema

The API follows the RFC 7807 Problem Details format with additional custom fields:

```python
class ProblemDetail(BaseModel):
    type: str = Field(..., description="URI reference identifying the problem type")
    title: str = Field(..., description="Human-readable summary")
    status: int = Field(..., description="HTTP status code")
    detail: Optional[str] = Field(None, description="Human-readable explanation")
    instance: Optional[str] = Field(None, description="URI reference identifying specific occurrence")
    error_code: Optional[str] = Field(None, description="Internal error code")
    trace_id: Optional[str] = Field(None, description="Request trace identifier")
```

## Data Models

```python
from typing import List, Optional, Dict, Literal, Any
from pydantic import BaseModel, Field
from datetime import datetime

class SignalRequest(BaseModel):
    query_id: str = Field(..., description="The unique ID of the search query session.")
    session_id: str = Field(..., description="The user's session ID.")
    signal_type: Literal['click', 'dwell', 'abandon', 'refine', 'copy']
    content_id: Optional[str] = Field(None, description="The ID of the document that was interacted with.")
    result_position: Optional[int] = Field(None, description="The 0-based index of the clicked result.")
    dwell_time_ms: Optional[int] = Field(None, description="Time in milliseconds spent on a result.")

class AdminContentItem(BaseModel):
    content_id: str = Field(..., description="Unique identifier for the content item.")
    title: str = Field(..., description="Title of the content item.")
    content_type: str = Field(..., description="Type of content (e.g., 'documentation', 'code', 'readme').")
    technology: Optional[str] = Field(None, description="Associated technology or framework.")
    source_url: Optional[str] = Field(None, description="Original source URL of the content.")
    collection_name: str = Field(..., description="Name of the collection this content belongs to.")
    created_at: datetime = Field(..., description="Timestamp when content was indexed.")
    last_updated: datetime = Field(..., description="Timestamp when content was last modified.")
    size_bytes: Optional[int] = Field(None, description="Size of the content in bytes.")
    status: Literal['active', 'flagged', 'removed'] = Field(..., description="Current status of the content.")

class AdminSearchResponse(BaseModel):
    items: List[AdminContentItem] = Field(..., description="List of matching content items.")
    total_count: int = Field(..., description="Total number of items matching the search criteria.")
    page: int = Field(..., description="Current page number (1-based).")
    page_size: int = Field(..., description="Number of items per page.")
    has_more: bool = Field(..., description="Whether there are more pages available.")
```

## Implementation Tasks

| Task ID | Description |
|---------|-------------|
| API-001 | Initialize FastAPI application with CORS and security middleware |
| API-002 | Implement all Pydantic request/response schemas |
| API-003 | Implement all API endpoint stubs with mock data responses |
| API-004 | Add custom RequestValidationError exception handler |
| API-005 | Integrate slowapi for rate limiting on all endpoints |
| API-006 | Ensure FastAPI's automatic OpenAPI generation |
| API-007 | Implement structured logging middleware |
| API-008 | Implement the /api/v1/health endpoint |
| API-009 | Implement a global exception handler |
| API-010 | Implement a middleware for request/response logging |
| API-011 | Implement the /api/v1/signals endpoint (POST, validates SignalRequest, calls feedback_collector.record_implicit_signal as background task, returns HTTP 202) |
| API-012 | Implement the /api/v1/admin/search-content endpoint (GET, accepts query parameters: search_term, content_type, technology, limit, offset, returns AdminSearchResponse) |

## Integration Contracts
- Accepts and returns Pydantic models as defined above.
- Integrates with downstream services via stubs for now; future versions will connect to real implementations.

## Summary Tables

### Endpoints Table
(see API Endpoints above)

### Data Models Table

| Model Name                   | Description                                           | Used In Endpoint(s)              |
|------------------------------|-------------------------------------------------------|----------------------------------|
| SearchRequest                | Request body for search queries                      | POST /api/v1/search              |
| SearchResult                 | Individual search result item                        | Response data for search endpoints |
| SearchResponse               | Response body for search queries                     | POST/GET /api/v1/search          |
| FeedbackRequest              | Request body for user feedback submission           | POST /api/v1/feedback            |
| SignalRequest                | Request body for implicit user signals              | POST /api/v1/signals             |
| HealthStatus                 | Health status of individual service components      | Response data for health endpoint |
| HealthResponse               | Response body for system health checks              | GET /api/v1/health               |
| StatsResponse                | Response body for system usage statistics           | GET /api/v1/stats                |
| Collection                   | Individual collection/workspace information         | Response data for collections endpoint |
| CollectionsResponse          | Response body for available collections listing     | GET /api/v1/collections          |
| ConfigurationItem            | Individual configuration key-value item             | Response data for config endpoint |
| ConfigurationResponse        | Response body for system configuration retrieval   | GET /api/v1/config               |
| ConfigurationUpdateRequest   | Request body for configuration updates              | POST /api/v1/config              |
| AdminContentItem             | Individual content item with metadata for admin    | Response data for admin search endpoint |
| AdminSearchResponse          | Response body for admin content search              | GET /api/v1/admin/search-content |
| ProblemDetail                | Standard error response format (RFC 7807)          | All endpoints (error responses)  |

### Implementation Tasks Table
(see Implementation Tasks above)

---