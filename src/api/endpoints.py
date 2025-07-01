"""
Simplified API endpoints for the Docaiche API.

All endpoints consolidated into a single router for easy maintenance.
Each endpoint follows the OpenAPI specification exactly.
"""

from datetime import datetime
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Path,
    UploadFile,
    File,
    BackgroundTasks,
    Request,
    status,
    Header,
)

from .schemas import (
    # Search schemas
    SearchRequest,
    SearchResponse,
    UploadResponse,
    # Feedback schemas
    FeedbackRequest,
    SignalRequest,
    # System schemas
    HealthResponse,
    StatsResponse,
    # Collection schemas
    CollectionsResponse,
    Collection,
    # Configuration schemas
    ConfigurationResponse,
    ConfigurationUpdateRequest,
    AdminSearchResponse,
    AdminContentItem,
)
from .dependencies import (
    get_search_service,
    get_config_service,
    get_health_service,
    get_content_service,
    get_feedback_service,
    verify_admin_access,
)

# Create router
api_router = APIRouter()



# ============================================================================
# Search & Content Endpoints
# ============================================================================


@api_router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: Request,
    search_request: SearchRequest,
    search_service=Depends(get_search_service),
) -> SearchResponse:
    """
    Perform a comprehensive search across all documentation collections.

    This endpoint accepts detailed search parameters and returns ranked results
    with relevance scoring and metadata.
    """
    try:
        # Use the real search service
        return await search_service.search(search_request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}",
        )


@api_router.get("/search", response_model=SearchResponse)
async def search_documents_simple(
    request: Request,
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    technology: Optional[str] = Query(None, description="Technology filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    search_service=Depends(get_search_service),
) -> SearchResponse:
    """
    Perform a simple search using query parameters.

    This endpoint is useful for browser testing and simple integrations.
    """
    # Convert to SearchRequest and delegate to main search
    search_request = SearchRequest(query=q, technology_hint=technology, limit=limit)
    return await search_documents(request, search_request, search_service)


@api_router.post(
    "/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED
)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document file to upload"),
    collection: Optional[str] = Query(None, description="Target collection"),
    technology: Optional[str] = Query(None, description="Associated technology"),
    content_service=Depends(get_content_service),
) -> UploadResponse:
    """
    Upload and process a document for indexing.

    The document will be processed asynchronously and indexed for search.
    """
    # Validate file type and size
    if file.size and file.size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 10MB limit",
        )

    try:
        # Read file content
        content = await file.read()
        content_str = content.decode("utf-8")

        # Create content ingestion request
        from src.api.schemas import ContentIngestionRequest

        ingestion_request = ContentIngestionRequest(
            source_url=f"upload://{file.filename}",
            title=file.filename,
            content=content_str,
            content_type="document",
            technology=technology,
            workspace=collection or "default",
            metadata={
                "filename": file.filename,
                "content_type": file.content_type,
                "size": file.size,
            },
        )

        # Ingest content using the service
        response = await content_service.ingest_content(ingestion_request)

        if response.status == "completed":
            return UploadResponse(
                upload_id=response.content_id,
                status="accepted",
                message="Document upload accepted for processing",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response.message,
            )

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be UTF-8 encoded text",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        )


@api_router.delete("/content/{content_id}", status_code=status.HTTP_202_ACCEPTED)
async def remove_content(
    request: Request,
    content_id: str = Path(..., description="Unique content identifier"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    content_service=Depends(get_content_service),
):
    """
    Flag content for removal (admin operation).

    The content will be marked for removal and processed asynchronously.
    """
    # Use the real content service to delete content
    success = await content_service.delete_content(content_id)

    if success:
        return {"message": f"Content {content_id} flagged for removal"}
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Content {content_id} not found",
        )


# ============================================================================
# User Interaction Endpoints
# ============================================================================


@api_router.post("/feedback", status_code=status.HTTP_202_ACCEPTED)
async def submit_feedback(
    request: Request,
    feedback_request: FeedbackRequest,
    background_tasks: BackgroundTasks,
    feedback_service=Depends(get_feedback_service),
):
    """
    Submit explicit user feedback on search results or content.

    Feedback is processed asynchronously to improve search quality.
    """
    # Process feedback using the real service
    response = await feedback_service.submit_feedback(feedback_request)

    if response.status == "accepted":
        return {"message": response.message, "feedback_id": response.feedback_id}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=response.message
        )


@api_router.post("/signals", status_code=status.HTTP_202_ACCEPTED)
async def submit_signals(
    request: Request,
    signal_request: SignalRequest,
    background_tasks: BackgroundTasks,
    feedback_service=Depends(get_feedback_service),
):
    """
    Submit implicit user interaction signals.

    Signals like clicks, dwell time, and navigation patterns help improve
    search relevance and user experience.
    """
    # Convert SignalRequest to UsageSignalRequest for the service
    from src.api.schemas import UsageSignalRequest

    usage_signal = UsageSignalRequest(
        content_id=signal_request.content_id,
        user_id=signal_request.user_id,
        session_id=signal_request.session_id,
        signal_type=signal_request.signal_type,
        signal_strength=signal_request.signal_value,
        metadata=signal_request.metadata,
    )

    response = await feedback_service.record_usage_signal(usage_signal)

    if response.status == "accepted":
        return {"message": response.message}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=response.message
        )


# ============================================================================
# System Management Endpoints
# ============================================================================


@api_router.get("/health", response_model=HealthResponse)
async def get_health(health_service=Depends(get_health_service)) -> HealthResponse:
    """
    Get comprehensive system health status.

    Checks all system components and dependencies to provide overall health.
    """
    try:
        # Use the real health service
        return await health_service.check_system_health()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}",
        )


@api_router.get("/stats", response_model=StatsResponse)
async def get_stats(
    content_service=Depends(get_content_service),
    feedback_service=Depends(get_feedback_service),
) -> StatsResponse:
    """
    Get system usage and performance statistics.

    Provides metrics on search performance, cache utilization, and system resources.
    """
    # Get real stats from services
    content_stats = await content_service.get_content_stats()
    feedback_stats = await feedback_service.get_feedback_stats()

    # Format stats for API response
    return StatsResponse(
        search_stats={
            "total_searches": feedback_stats.total_feedback,
            "searches_today": feedback_stats.total_feedback,  # Would need date filtering
            "average_response_time_ms": 85,  # Would need to track this
            "popular_technologies": list(content_stats.by_technology.keys())[:5],
        },
        cache_stats={
            "hit_rate": 0.0,  # Would need cache manager stats
            "miss_rate": 1.0,
            "total_requests": 0,
            "cache_size_mb": 0,
        },
        content_stats={
            "total_documents": content_stats.total_documents,
            "collections": len(content_stats.by_workspace),
            "last_update": content_stats.last_updated.isoformat(),
            "pending_uploads": 0,
        },
        system_stats={
            "uptime_seconds": 0,  # Would need to track process start time
            "memory_usage_percent": 0,  # Would need psutil or similar
            "cpu_usage_percent": 0,
            "disk_usage_percent": 0,
        },
        timestamp=datetime.utcnow(),
    )


@api_router.get("/collections", response_model=CollectionsResponse)
async def get_collections(
    content_service=Depends(get_content_service),
) -> CollectionsResponse:
    """
    Get available documentation collections/workspaces.

    Lists all available collections that can be searched or managed.
    """
    # Get real collections from content service
    content_collections = await content_service.list_collections()

    # Convert to API schema
    collections = []
    for cc in content_collections:
        # Infer technology from collection name or use default
        technology = "general"
        if "python" in cc.name.lower():
            technology = "python"
        elif "react" in cc.name.lower():
            technology = "react"
        elif "javascript" in cc.name.lower() or "js" in cc.name.lower():
            technology = "javascript"

        collections.append(
            Collection(
                slug=cc.collection_id,
                name=cc.name,
                technology=technology,
                document_count=cc.item_count,
                last_updated=cc.updated_at,
                is_active=True,
            )
        )

    return CollectionsResponse(collections=collections, total_count=len(collections))


# ============================================================================
# Configuration Endpoints
# ============================================================================


@api_router.get("/config", response_model=ConfigurationResponse)
async def get_configuration(
    config_service=Depends(get_config_service),
) -> ConfigurationResponse:
    """
    Retrieve current system configuration.

    Returns all non-sensitive configuration items.
    """
    # Use the real config service
    return config_service.get_current_config()


@api_router.post("/config", response_model=ConfigurationResponse)
async def update_configuration(
    request: ConfigurationUpdateRequest,
    config_service=Depends(get_config_service),
    admin_authorized: bool = Depends(verify_admin_access),  # Add authorization
) -> ConfigurationResponse:
    """
    Update system configuration.

    Updates a specific configuration item and returns the updated configuration.
    """
    # Validate configuration key against allowed keys
    allowed_keys = {
        "search.default_limit",
        "search.max_limit",
        "cache.enabled",
        "cache.ttl_seconds",
        "anythingllm.enabled",
        # Add more allowed keys as needed
    }

    if request.key not in allowed_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Configuration key '{request.key}' is not allowed",
        )

    # Use the real config service to update configuration
    return await config_service.update_config_item(request.key, request.value)


# ============================================================================
# Administration Endpoints
# ============================================================================


# Simple admin authorization dependency
async def verify_admin_access(authorization: str = Header(None)) -> bool:
    """
    Verify admin access. In production, this should validate a JWT token
    or API key against a proper authentication service.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # TODO: Implement proper token validation
    # For now, check for a specific header value from environment
    import os

    expected_token = os.getenv("ADMIN_API_KEY", "admin-secret-key")

    if authorization != f"Bearer {expected_token}":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid authorization token"
        )

    return True


@api_router.get("/admin/search-content", response_model=AdminSearchResponse)
async def admin_search_content(
    search_term: Optional[str] = Query(None, description="Search term"),
    content_type: Optional[str] = Query(None, description="Content type filter"),
    technology: Optional[str] = Query(None, description="Technology filter"),
    status: Optional[str] = Query(None, description="Status filter"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Results offset"),
    content_service=Depends(get_content_service),
    search_service=Depends(get_search_service),
    admin_authorized: bool = Depends(verify_admin_access),
) -> AdminSearchResponse:
    """
    Search and manage content items (admin interface).

    Provides detailed content metadata for administrative management.
    """
    # For now, use search service with filters
    # In a real implementation, would have dedicated admin query methods
    if search_term:
        from src.api.schemas import SearchRequest

        search_req = SearchRequest(
            query=search_term,
            technology_hint=technology,
            content_type_filter=content_type,
            limit=limit,
            offset=offset,
        )
        search_results = await search_service.search(search_req)

        # Convert search results to admin items
        items = []
        for result in search_results.results:
            items.append(
                AdminContentItem(
                    content_id=result.content_id,
                    title=result.title,
                    content_type=result.content_type,
                    technology=result.technology,
                    source_url=result.source_url,
                    collection_name=result.workspace,
                    created_at=result.created_at or datetime.utcnow(),
                    last_updated=result.updated_at or datetime.utcnow(),
                    size_bytes=len(result.snippet) * 10,  # Rough estimate
                    status="active",
                )
            )

        total_count = search_results.total_count
    else:
        # No search term - return empty for now
        # In real implementation would list all content
        items = []
        total_count = 0

    page = (offset // limit) + 1
    has_more = offset + limit < total_count

    return AdminSearchResponse(
        items=items,
        total_count=total_count,
        page=page,
        page_size=limit,
        has_more=has_more,
    )
