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

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query string")
    technology_hint: Optional[str] = Field(None, description="Optional technology filter (e.g., 'python', 'react')")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of results to return")
    session_id: Optional[str] = Field(None, description="User session identifier for tracking")

class SearchResult(BaseModel):
    content_id: str = Field(..., description="Unique identifier for the content")
    title: str = Field(..., description="Title of the document or section")
    snippet: str = Field(..., description="Relevant excerpt from the content")
    source_url: str = Field(..., description="Original source URL")
    technology: str = Field(..., description="Associated technology or framework")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score for the query")
    content_type: str = Field(..., description="Type of content (documentation, code, example, etc.)")
    workspace: str = Field(..., description="AnythingLLM workspace containing this content")

class SearchResponse(BaseModel):
    results: List[SearchResult] = Field(..., description="List of search results")
    total_count: int = Field(..., description="Total number of matching results")
    query: str = Field(..., description="Original search query")
    technology_hint: Optional[str] = Field(None, description="Technology filter applied")
    execution_time_ms: int = Field(..., description="Time taken to execute the search")
    cache_hit: bool = Field(..., description="Whether results were served from cache")
    enrichment_triggered: bool = Field(False, description="Whether knowledge enrichment was triggered")

class FeedbackRequest(BaseModel):
    content_id: str = Field(..., description="ID of the content being rated")
    feedback_type: Literal['helpful', 'not_helpful', 'outdated', 'incorrect', 'flag'] = Field(..., description="Type of feedback")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Optional 1-5 star rating")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional feedback comment")
    query_context: Optional[str] = Field(None, description="Search query that led to this content")
    session_id: Optional[str] = Field(None, description="User session identifier")

class HealthStatus(BaseModel):
    service: str = Field(..., description="Name of the service component")
    status: Literal['healthy', 'degraded', 'unhealthy'] = Field(..., description="Current health status")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    last_check: datetime = Field(..., description="Timestamp of last health check")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional status details")

class HealthResponse(BaseModel):
    overall_status: Literal['healthy', 'degraded', 'unhealthy'] = Field(..., description="Overall system health")
    services: List[HealthStatus] = Field(..., description="Individual service health statuses")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")

class StatsResponse(BaseModel):
    search_stats: Dict[str, Any] = Field(..., description="Search performance and usage statistics")
    cache_stats: Dict[str, Any] = Field(..., description="Cache hit rates and performance")
    content_stats: Dict[str, Any] = Field(..., description="Content collection and quality statistics")
    system_stats: Dict[str, Any] = Field(..., description="System resource and performance statistics")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Statistics timestamp")

class Collection(BaseModel):
    slug: str = Field(..., description="Unique collection identifier")
    name: str = Field(..., description="Human-readable collection name")
    technology: str = Field(..., description="Primary technology or framework")
    document_count: int = Field(..., description="Number of documents in collection")
    last_updated: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(True, description="Whether collection is actively maintained")

class CollectionsResponse(BaseModel):
    collections: List[Collection] = Field(..., description="Available documentation collections")
    total_count: int = Field(..., description="Total number of collections")

class ConfigurationItem(BaseModel):
    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value")
    schema_version: str = Field("1.0", description="Configuration schema version")
    description: Optional[str] = Field(None, description="Human-readable description")
    is_sensitive: bool = Field(False, description="Whether value contains sensitive data")

class ConfigurationResponse(BaseModel):
    items: List[ConfigurationItem] = Field(..., description="Configuration items")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Configuration timestamp")

class ConfigurationUpdateRequest(BaseModel):
    key: str = Field(..., description="Configuration key to update")
    value: Any = Field(..., description="New configuration value")
    description: Optional[str] = Field(None, description="Optional description of the change")

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