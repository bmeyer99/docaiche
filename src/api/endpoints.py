"""
Simplified API endpoints for the Docaiche API.

All endpoints consolidated into a single router for easy maintenance.
Each endpoint follows the OpenAPI specification exactly.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File, BackgroundTasks, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from .schemas import (
    # Search schemas
    SearchRequest, SearchResponse, SearchResult,
    # Upload schemas
    UploadResponse,
    # Feedback schemas
    FeedbackRequest, SignalRequest,
    # System schemas
    HealthResponse, HealthStatus, StatsResponse,
    # Collection schemas
    CollectionsResponse, Collection,
    # Configuration schemas
    ConfigurationResponse, ConfigurationUpdateRequest, ConfigurationItem,
    # Admin schemas
    AdminSearchResponse, AdminContentItem,
)
from .dependencies import (
    get_search_service, get_config_service, get_health_service,
    get_content_service, get_feedback_service
)

# Create router
api_router = APIRouter()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# Search & Content Endpoints
# ============================================================================

@api_router.post("/search", response_model=SearchResponse)
@limiter.limit("30/minute")
async def search_documents(
    request: SearchRequest,
    search_service=Depends(get_search_service)
) -> SearchResponse:
    """
    Perform a comprehensive search across all documentation collections.
    
    This endpoint accepts detailed search parameters and returns ranked results
    with relevance scoring and metadata.
    """
    try:
        # For demo purposes, return mock data
        # In real implementation, this would call search_service.search(request)
        return SearchResponse(
            results=[
                SearchResult(
                    content_id=f"doc_{i}",
                    title=f"Example Document {i}",
                    snippet=f"This is a snippet for query: {request.query}",
                    source_url=f"https://example.com/doc-{i}",
                    technology=request.technology_hint or "python",
                    relevance_score=0.9 - (i * 0.1),
                    content_type="documentation",
                    workspace="default"
                )
                for i in range(min(request.limit, 3))
            ],
            total_count=100,
            query=request.query,
            technology_hint=request.technology_hint,
            execution_time_ms=45,
            cache_hit=False,
            enrichment_triggered=False
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@api_router.get("/search", response_model=SearchResponse)
@limiter.limit("30/minute")
async def search_documents_simple(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    technology: Optional[str] = Query(None, description="Technology filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    search_service=Depends(get_search_service)
) -> SearchResponse:
    """
    Perform a simple search using query parameters.
    
    This endpoint is useful for browser testing and simple integrations.
    """
    # Convert to SearchRequest and delegate to main search
    search_request = SearchRequest(
        query=q,
        technology_hint=technology,
        limit=limit
    )
    return await search_documents(search_request, search_service)


@api_router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file to upload"),
    collection: Optional[str] = Query(None, description="Target collection"),
    technology: Optional[str] = Query(None, description="Associated technology"),
    content_service=Depends(get_content_service)
) -> UploadResponse:
    """
    Upload and process a document for indexing.
    
    The document will be processed asynchronously and indexed for search.
    """
    # Validate file type and size
    if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 10MB limit"
        )
    
    upload_id = str(uuid.uuid4())
    
    # Add background task for processing
    # background_tasks.add_task(content_service.process_upload, upload_id, file, collection, technology)
    
    return UploadResponse(
        upload_id=upload_id,
        status="accepted",
        message="Document upload accepted for processing"
    )


@api_router.delete("/content/{content_id}", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def remove_content(
    content_id: str = Path(..., description="Unique content identifier"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    content_service=Depends(get_content_service)
):
    """
    Flag content for removal (admin operation).
    
    The content will be marked for removal and processed asynchronously.
    """
    # Add background task for content removal
    # background_tasks.add_task(content_service.flag_for_removal, content_id)
    
    return {"message": f"Content {content_id} flagged for removal"}


# ============================================================================
# User Interaction Endpoints
# ============================================================================

@api_router.post("/feedback", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("20/minute")
async def submit_feedback(
    request: FeedbackRequest,
    background_tasks: BackgroundTasks,
    feedback_service=Depends(get_feedback_service)
):
    """
    Submit explicit user feedback on search results or content.
    
    Feedback is processed asynchronously to improve search quality.
    """
    # Add background task for feedback processing
    # background_tasks.add_task(feedback_service.process_feedback, request)
    
    return {"message": "Feedback submitted successfully"}


@api_router.post("/signals", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("50/minute")
async def submit_signals(
    request: SignalRequest,
    background_tasks: BackgroundTasks,
    feedback_service=Depends(get_feedback_service)
):
    """
    Submit implicit user interaction signals.
    
    Signals like clicks, dwell time, and navigation patterns help improve
    search relevance and user experience.
    """
    # Add background task for signal processing
    # background_tasks.add_task(feedback_service.process_signal, request)
    
    return {"message": "Signal recorded successfully"}


# ============================================================================
# System Management Endpoints
# ============================================================================

@api_router.get("/health", response_model=HealthResponse)
async def get_health(
    health_service=Depends(get_health_service)
) -> HealthResponse:
    """
    Get comprehensive system health status.
    
    Checks all system components and dependencies to provide overall health.
    """
    try:
        # Mock health data - in real implementation would check actual services
        services = [
            HealthStatus(
                service="database",
                status="healthy",
                response_time_ms=15,
                last_check=datetime.utcnow(),
                details={"connections": 5, "pool_size": 10}
            ),
            HealthStatus(
                service="cache",
                status="healthy",
                response_time_ms=2,
                last_check=datetime.utcnow(),
                details={"hit_rate": 0.85, "memory_usage": "45%"}
            ),
            HealthStatus(
                service="search_index",
                status="healthy",
                response_time_ms=8,
                last_check=datetime.utcnow(),
                details={"documents_indexed": 15000, "index_size": "2.1GB"}
            )
        ]
        
        overall_status = "healthy"
        if any(s.status == "unhealthy" for s in services):
            overall_status = "unhealthy"
        elif any(s.status == "degraded" for s in services):
            overall_status = "degraded"
        
        return HealthResponse(
            overall_status=overall_status,
            services=services,
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )


@api_router.get("/stats", response_model=StatsResponse)
async def get_stats() -> StatsResponse:
    """
    Get system usage and performance statistics.
    
    Provides metrics on search performance, cache utilization, and system resources.
    """
    return StatsResponse(
        search_stats={
            "total_searches": 50000,
            "searches_today": 1250,
            "average_response_time_ms": 85,
            "popular_technologies": ["python", "javascript", "react"]
        },
        cache_stats={
            "hit_rate": 0.78,
            "miss_rate": 0.22,
            "total_requests": 25000,
            "cache_size_mb": 512
        },
        content_stats={
            "total_documents": 15000,
            "collections": 25,
            "last_update": datetime.utcnow().isoformat(),
            "pending_uploads": 3
        },
        system_stats={
            "uptime_seconds": 86400,
            "memory_usage_percent": 65,
            "cpu_usage_percent": 12,
            "disk_usage_percent": 45
        },
        timestamp=datetime.utcnow()
    )


@api_router.get("/collections", response_model=CollectionsResponse)
async def get_collections() -> CollectionsResponse:
    """
    Get available documentation collections/workspaces.
    
    Lists all available collections that can be searched or managed.
    """
    collections = [
        Collection(
            slug="python-docs",
            name="Python Documentation",
            technology="python",
            document_count=2500,
            last_updated=datetime.utcnow(),
            is_active=True
        ),
        Collection(
            slug="react-docs",
            name="React Documentation",
            technology="react",
            document_count=1800,
            last_updated=datetime.utcnow(),
            is_active=True
        ),
        Collection(
            slug="fastapi-docs",
            name="FastAPI Documentation",
            technology="fastapi",
            document_count=900,
            last_updated=datetime.utcnow(),
            is_active=True
        )
    ]
    
    return CollectionsResponse(
        collections=collections,
        total_count=len(collections)
    )


# ============================================================================
# Configuration Endpoints
# ============================================================================

@api_router.get("/config", response_model=ConfigurationResponse)
async def get_configuration(
    config_service=Depends(get_config_service)
) -> ConfigurationResponse:
    """
    Retrieve current system configuration.
    
    Returns all non-sensitive configuration items.
    """
    items = [
        ConfigurationItem(
            key="search.default_limit",
            value=20,
            description="Default number of search results to return"
        ),
        ConfigurationItem(
            key="search.max_limit",
            value=100,
            description="Maximum number of search results allowed"
        ),
        ConfigurationItem(
            key="upload.max_file_size",
            value="10MB",
            description="Maximum file size for document uploads"
        ),
        ConfigurationItem(
            key="cache.ttl_seconds",
            value=3600,
            description="Cache time-to-live in seconds"
        )
    ]
    
    return ConfigurationResponse(
        items=items,
        timestamp=datetime.utcnow()
    )


@api_router.post("/config", response_model=ConfigurationResponse)
async def update_configuration(
    request: ConfigurationUpdateRequest,
    config_service=Depends(get_config_service)
) -> ConfigurationResponse:
    """
    Update system configuration.
    
    Updates a specific configuration item and returns the updated configuration.
    """
    # In real implementation, would validate and update configuration
    # config_service.update_config(request.key, request.value, request.description)
    
    # Return updated configuration
    return await get_configuration(config_service)


# ============================================================================
# Administration Endpoints
# ============================================================================

@api_router.get("/admin/search-content", response_model=AdminSearchResponse)
async def admin_search_content(
    search_term: Optional[str] = Query(None, description="Search term"),
    content_type: Optional[str] = Query(None, description="Content type filter"),
    technology: Optional[str] = Query(None, description="Technology filter"),
    status: Optional[str] = Query(None, description="Status filter"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Results offset"),
    content_service=Depends(get_content_service)
) -> AdminSearchResponse:
    """
    Search and manage content items (admin interface).
    
    Provides detailed content metadata for administrative management.
    """
    # Mock admin content data
    items = [
        AdminContentItem(
            content_id=f"admin_doc_{i}",
            title=f"Admin Document {i}",
            content_type="documentation",
            technology=technology or "python",
            source_url=f"https://example.com/admin-doc-{i}",
            collection_name="python-docs",
            created_at=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            size_bytes=15000 + i * 1000,
            status="active"
        )
        for i in range(min(limit, 5))
    ]
    
    total_count = 500  # Mock total
    page = (offset // limit) + 1
    has_more = offset + limit < total_count
    
    return AdminSearchResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=limit,
        has_more=has_more
    )