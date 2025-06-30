# Task: API-002 - Implement All Pydantic Request/Response Schemas

**PRD Reference**: [PRD-001: HTTP API Foundation](../PRDs/PRD-001_HTTP_API_Foundation.md#data-models)

## Overview
Implement all Pydantic request and response schemas as defined in PRD-001, ensuring type safety, validation, and proper OpenAPI documentation generation.

## Detailed Requirements

### 1. Search-Related Models
```python
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
```

### 2. Feedback Models
```python
class FeedbackRequest(BaseModel):
    content_id: str = Field(..., description="ID of the content being rated")
    feedback_type: Literal['helpful', 'not_helpful', 'outdated', 'incorrect', 'flag'] = Field(..., description="Type of feedback")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Optional 1-5 star rating")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional feedback comment")
    query_context: Optional[str] = Field(None, description="Search query that led to this content")
    session_id: Optional[str] = Field(None, description="User session identifier")

class SignalRequest(BaseModel):
    query_id: str = Field(..., description="The unique ID of the search query session.")
    session_id: str = Field(..., description="The user's session ID.")
    signal_type: Literal['click', 'dwell', 'abandon', 'refine', 'copy']
    content_id: Optional[str] = Field(None, description="The ID of the document that was interacted with.")
    result_position: Optional[int] = Field(None, description="The 0-based index of the clicked result.")
    dwell_time_ms: Optional[int] = Field(None, description="Time in milliseconds spent on a result.")
```

### 3. Health and Stats Models
```python
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
```

### 4. Configuration Models
```python
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
```

### 5. Collection Models
```python
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
```

### 6. Admin Models
```python
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

### 7. Error Models
```python
class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details format with additional custom fields"""
    type: str = Field(..., description="URI reference identifying the problem type")
    title: str = Field(..., description="Human-readable summary")
    status: int = Field(..., description="HTTP status code")
    detail: Optional[str] = Field(None, description="Human-readable explanation")
    instance: Optional[str] = Field(None, description="URI reference identifying specific occurrence")
    error_code: Optional[str] = Field(None, description="Internal error code")
    trace_id: Optional[str] = Field(None, description="Request trace identifier")
```

## Implementation Details

### File Structure
```
src/models/
├── __init__.py
├── schemas.py          # All request/response models
├── base.py            # Base model classes
└── validators.py      # Custom validators
```

### Custom Validators
```python
from pydantic import validator

class SearchRequest(BaseModel):
    # ... field definitions ...
    
    @validator('technology_hint')
    def validate_technology_hint(cls, v):
        if v:
            # Normalize technology names
            return v.lower().strip()
        return v
    
    @validator('query')
    def validate_query(cls, v):
        # Basic query sanitization
        return v.strip()
```

### Model Configuration
```python
class BaseAPIModel(BaseModel):
    """Base model with common configuration"""
    
    class Config:
        # Use enum values for OpenAPI docs
        use_enum_values = True
        # Allow population by field name
        allow_population_by_field_name = True
        # JSON encoders for datetime
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

## Acceptance Criteria
- [ ] All models defined exactly as specified in PRD-001
- [ ] Proper field validation with min/max constraints
- [ ] Descriptive field descriptions for OpenAPI docs
- [ ] Custom validators for data normalization
- [ ] Type hints for all fields
- [ ] Default values where appropriate
- [ ] Literal types for enums
- [ ] Models generate clean OpenAPI schemas
- [ ] All imports resolve correctly
- [ ] Code passes type checking with mypy

## Dependencies
- pydantic >= 2.0.0
- typing_extensions (for Python < 3.10)

## Files to Create/Modify
- `src/models/schemas.py` (create)
- `src/models/base.py` (create)
- `src/models/validators.py` (create)
- `src/models/__init__.py` (update with exports)

## Testing
- Validate field constraints work correctly
- Test custom validators
- Verify OpenAPI schema generation
- Test serialization/deserialization
- Validate error handling for invalid data

## Integration Notes
- These models will be imported by all API endpoint modules
- Models must be consistent with database schemas in PRD-002
- Error models will be used by exception handlers in API-004
- Configuration models integrate with PRD-003 config management