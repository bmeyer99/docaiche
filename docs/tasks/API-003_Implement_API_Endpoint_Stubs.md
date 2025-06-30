# Task: API-003 - Implement All API Endpoint Stubs with Mock Data

**PRD Reference**: [PRD-001: HTTP API Foundation](../PRDs/PRD-001_HTTP_API_Foundation.md#api-endpoints)

## Overview
Implement all API endpoint stubs as defined in PRD-001 with mock data responses that conform to the Pydantic schemas. This provides a functional API for testing while business logic is developed separately.

## Detailed Requirements

### 1. Search Endpoints
```python
# POST /api/v1/search
@router.post("/search", response_model=SearchResponse, tags=["search"])
async def search_documents(request: SearchRequest) -> SearchResponse:
    """Execute a search query against the documentation cache"""
    # Mock search results
    mock_results = [
        SearchResult(
            content_id="doc_001",
            title="FastAPI Documentation - Getting Started",
            snippet="FastAPI is a modern, fast web framework for building APIs with Python 3.6+",
            source_url="https://fastapi.tiangolo.com/tutorial/",
            technology="fastapi",
            relevance_score=0.95,
            content_type="documentation",
            workspace="python-web-frameworks"
        ),
        SearchResult(
            content_id="doc_002", 
            title="FastAPI Advanced Features",
            snippet="Learn about dependency injection, middleware, and background tasks",
            source_url="https://fastapi.tiangolo.com/advanced/",
            technology="fastapi",
            relevance_score=0.87,
            content_type="tutorial",
            workspace="python-web-frameworks"
        )
    ]
    
    # Simulate search execution time
    execution_time = random.randint(50, 200)
    
    return SearchResponse(
        results=mock_results[:request.limit],
        total_count=len(mock_results),
        query=request.query,
        technology_hint=request.technology_hint,
        execution_time_ms=execution_time,
        cache_hit=random.choice([True, False]),
        enrichment_triggered=False
    )

# GET /api/v1/search (for browser testing)
@router.get("/search", response_model=SearchResponse, tags=["search"])
async def search_documents_get(
    q: str = Query(..., description="Search query"),
    technology_hint: Optional[str] = Query(None, description="Technology filter"),
    limit: int = Query(20, ge=1, le=100, description="Result limit")
) -> SearchResponse:
    """GET version of search for browser testing"""
    request = SearchRequest(query=q, technology_hint=technology_hint, limit=limit)
    return await search_documents(request)
```

### 2. Feedback Endpoints
```python
# POST /api/v1/feedback
@router.post("/feedback", status_code=201, tags=["feedback"])
async def submit_feedback(request: FeedbackRequest) -> Dict[str, str]:
    """Submit explicit user feedback on search results"""
    # Mock feedback processing
    logger.info(f"Received feedback: {request.feedback_type} for content {request.content_id}")
    return {"status": "success", "message": "Feedback recorded successfully"}

# POST /api/v1/signals
@router.post("/signals", status_code=202, tags=["feedback"])
async def submit_signals(request: SignalRequest) -> Dict[str, str]:
    """Submit implicit user interaction signals"""
    # Mock signal processing - would normally be background task
    logger.info(f"Received signal: {request.signal_type} for query {request.query_id}")
    return {"status": "accepted", "message": "Signal queued for processing"}
```

### 3. Health and Stats Endpoints
```python
# GET /api/v1/health
@router.get("/health", response_model=HealthResponse, tags=["health"])
async def get_health_status() -> HealthResponse:
    """Get system health status"""
    services = [
        HealthStatus(
            service="api", 
            status="healthy",
            response_time_ms=5,
            last_check=datetime.utcnow(),
            details={"version": "1.0.0", "uptime": "1h 30m"}
        ),
        HealthStatus(
            service="database",
            status="healthy", 
            response_time_ms=12,
            last_check=datetime.utcnow(),
            details={"connection_pool": "5/10", "last_query": "1s ago"}
        ),
        HealthStatus(
            service="cache",
            status="healthy",
            response_time_ms=3,
            last_check=datetime.utcnow(), 
            details={"memory_usage": "45%", "hit_rate": "78%"}
        ),
        HealthStatus(
            service="anythingllm",
            status="healthy",
            response_time_ms=150,
            last_check=datetime.utcnow(),
            details={"workspaces": 3, "documents": 1247}
        )
    ]
    
    return HealthResponse(
        overall_status="healthy",
        services=services,
        timestamp=datetime.utcnow()
    )

# GET /api/v1/stats
@router.get("/stats", response_model=StatsResponse, tags=["health"])
async def get_statistics() -> StatsResponse:
    """Get system usage and performance statistics"""
    return StatsResponse(
        search_stats={
            "total_searches": 15420,
            "searches_last_24h": 342,
            "avg_response_time_ms": 145,
            "cache_hit_rate": 0.78
        },
        cache_stats={
            "redis_memory_usage": "156MB",
            "redis_hit_rate": 0.82,
            "cache_entries": 8934,
            "evicted_keys": 145
        },
        content_stats={
            "total_documents": 1247,
            "total_collections": 12,
            "avg_quality_score": 0.73,
            "last_enrichment": "2h ago"
        },
        system_stats={
            "cpu_usage": 0.23,
            "memory_usage": 0.67,
            "disk_usage": 0.45,
            "uptime_seconds": 5430
        },
        timestamp=datetime.utcnow()
    )
```

### 4. Configuration Endpoints
```python
# GET /api/v1/config
@router.get("/config", response_model=ConfigurationResponse, tags=["config"])
async def get_configuration() -> ConfigurationResponse:
    """Get current system configuration"""
    mock_config_items = [
        ConfigurationItem(
            key="search.default_limit",
            value=20,
            description="Default number of search results to return",
            is_sensitive=False
        ),
        ConfigurationItem(
            key="cache.ttl_seconds",
            value=3600,
            description="Cache time-to-live in seconds",
            is_sensitive=False
        ),
        ConfigurationItem(
            key="llm.provider",
            value="ollama",
            description="Primary LLM provider",
            is_sensitive=False
        )
    ]
    
    return ConfigurationResponse(
        items=mock_config_items,
        timestamp=datetime.utcnow()
    )

# POST /api/v1/config
@router.post("/config", status_code=200, tags=["config"])
async def update_configuration(request: ConfigurationUpdateRequest) -> Dict[str, str]:
    """Update system configuration"""
    logger.info(f"Config update: {request.key} = {request.value}")
    return {"status": "success", "message": f"Configuration {request.key} updated"}
```

### 5. Collections Endpoint
```python
# GET /api/v1/collections
@router.get("/collections", response_model=CollectionsResponse, tags=["collections"])
async def get_collections() -> CollectionsResponse:
    """Get available documentation collections"""
    mock_collections = [
        Collection(
            slug="python-web-frameworks",
            name="Python Web Frameworks",
            technology="python",
            document_count=456,
            last_updated=datetime.utcnow() - timedelta(hours=2),
            is_active=True
        ),
        Collection(
            slug="react-ecosystem",
            name="React Ecosystem",
            technology="react",
            document_count=782,
            last_updated=datetime.utcnow() - timedelta(hours=6),
            is_active=True
        ),
        Collection(
            slug="docker-containers",
            name="Docker and Containers",
            technology="docker",
            document_count=234,
            last_updated=datetime.utcnow() - timedelta(days=1),
            is_active=True
        )
    ]
    
    return CollectionsResponse(
        collections=mock_collections,
        total_count=len(mock_collections)
    )
```

### 6. Admin Endpoints
```python
# DELETE /api/v1/content/{content_id}
@router.delete("/content/{content_id}", status_code=200, tags=["admin"])
async def flag_content(content_id: str) -> Dict[str, str]:
    """Flag content for removal (admin action)"""
    logger.info(f"Content flagged for removal: {content_id}")
    return {"status": "success", "message": f"Content {content_id} flagged for removal"}

# GET /api/v1/admin/search-content
@router.get("/admin/search-content", response_model=AdminSearchResponse, tags=["admin"])
async def search_content_admin(
    search_term: Optional[str] = Query(None, description="Search term"),
    content_type: Optional[str] = Query(None, description="Content type filter"),
    technology: Optional[str] = Query(None, description="Technology filter"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Results offset")
) -> AdminSearchResponse:
    """Search content metadata for admin management"""
    mock_items = [
        AdminContentItem(
            content_id="doc_001",
            title="FastAPI Getting Started Guide",
            content_type="documentation",
            technology="fastapi",
            source_url="https://fastapi.tiangolo.com/tutorial/",
            collection_name="python-web-frameworks",
            created_at=datetime.utcnow() - timedelta(days=30),
            last_updated=datetime.utcnow() - timedelta(days=5),
            size_bytes=15420,
            status="active"
        ),
        AdminContentItem(
            content_id="doc_002",
            title="FastAPI Advanced Features",
            content_type="tutorial",
            technology="fastapi", 
            source_url="https://fastapi.tiangolo.com/advanced/",
            collection_name="python-web-frameworks",
            created_at=datetime.utcnow() - timedelta(days=25),
            last_updated=datetime.utcnow() - timedelta(days=3),
            size_bytes=23150,
            status="active"
        )
    ]
    
    # Apply filters (mock implementation)
    filtered_items = mock_items
    if search_term:
        filtered_items = [item for item in filtered_items if search_term.lower() in item.title.lower()]
    if content_type:
        filtered_items = [item for item in filtered_items if item.content_type == content_type]
    if technology:
        filtered_items = [item for item in filtered_items if item.technology == technology]
    
    # Apply pagination
    page_items = filtered_items[offset:offset + limit]
    
    return AdminSearchResponse(
        items=page_items,
        total_count=len(filtered_items),
        page=(offset // limit) + 1,
        page_size=limit,
        has_more=offset + limit < len(filtered_items)
    )
```

## File Structure
```
src/api/v1/
├── __init__.py
├── api.py              # Main router
└── endpoints/
    ├── __init__.py
    ├── search.py       # Search endpoints
    ├── feedback.py     # Feedback endpoints
    ├── health.py       # Health and stats
    ├── config.py       # Configuration
    ├── collections.py  # Collections
    └── admin.py        # Admin endpoints
```

## Implementation Details

### Main API Router (`src/api/v1/api.py`)
```python
from fastapi import APIRouter
from .endpoints import search, feedback, health, config, collections, admin

api_router = APIRouter()

api_router.include_router(search.router, tags=["search"])
api_router.include_router(feedback.router, tags=["feedback"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(config.router, tags=["config"])
api_router.include_router(collections.router, tags=["collections"])
api_router.include_router(admin.router, tags=["admin"])
```

### Common Dependencies
```python
# src/api/dependencies.py
from fastapi import Depends, HTTPException, Header
from typing import Optional
import uuid

def get_trace_id(x_trace_id: Optional[str] = Header(None)) -> str:
    """Generate or extract trace ID for request tracing"""
    return x_trace_id or str(uuid.uuid4())

def get_session_id(x_session_id: Optional[str] = Header(None)) -> Optional[str]:
    """Extract session ID from headers"""
    return x_session_id
```

## Acceptance Criteria
- [ ] All endpoints defined exactly as specified in PRD-001
- [ ] Proper HTTP methods and status codes
- [ ] Mock responses conform to Pydantic schemas
- [ ] Proper OpenAPI tags for organization
- [ ] Query parameters properly validated
- [ ] Path parameters properly validated
- [ ] Consistent error handling structure
- [ ] Proper logging for all endpoints
- [ ] OpenAPI documentation generates correctly
- [ ] All endpoints return realistic mock data

## Dependencies
- fastapi
- python-multipart (for form data)
- python-logging

## Files to Create/Modify
- `src/api/v1/api.py` (create)
- `src/api/v1/endpoints/search.py` (create)
- `src/api/v1/endpoints/feedback.py` (create)
- `src/api/v1/endpoints/health.py` (create)
- `src/api/v1/endpoints/config.py` (create)
- `src/api/v1/endpoints/collections.py` (create)
- `src/api/v1/endpoints/admin.py` (create)
- `src/api/dependencies.py` (create)

## Testing
- Test all endpoints return expected status codes
- Validate response schemas match Pydantic models
- Test query parameter validation
- Test path parameter validation
- Verify OpenAPI schema generation
- Test endpoint routing works correctly

## Integration Notes
- These endpoint stubs will be replaced with real business logic implementations in later tasks
- Mock data should be realistic enough for frontend development and testing
- Error handling will be enhanced in API-004 task
- Rate limiting will be added in API-005 task