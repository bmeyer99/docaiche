"""
Enrichment API Endpoints - PRD-010
REST API contracts for knowledge enrichment operations.

Implements standardized API patterns following system-wide conventions
with proper error handling and HTTP status code mapping.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, status
from pydantic import BaseModel, Field

from src.enrichment.enricher import KnowledgeEnricher
from src.enrichment.models import (
    EnrichmentType,
    EnrichmentPriority,
    EnrichmentResult,
    EnrichmentMetrics,
    ContentGap,
    EnrichmentAnalytics,
)
from src.enrichment.exceptions import (
    EnrichmentError,
    TaskProcessingError,
    EnrichmentTimeoutError,
    AnalysisError,
    InvalidTaskError,
)

logger = logging.getLogger(__name__)

# Create enrichment router
enrichment_router = APIRouter(prefix="/enrichment", tags=["enrichment"])


# Request/Response Models following system patterns
class EnrichmentRequest(BaseModel):
    """Request model for content enrichment operations."""

    content_id: str = Field(..., description="Content ID to enrich")
    enrichment_types: Optional[List[EnrichmentType]] = Field(
        None, description="Types of enrichment to perform"
    )
    priority: EnrichmentPriority = Field(
        EnrichmentPriority.NORMAL, description="Task priority"
    )


class BulkEnrichmentRequest(BaseModel):
    """Request model for bulk enrichment operations."""

    content_ids: List[str] = Field(..., description="List of content IDs to enrich")
    enrichment_type: EnrichmentType = Field(
        ..., description="Type of enrichment to perform"
    )
    priority: EnrichmentPriority = Field(
        EnrichmentPriority.LOW, description="Task priority"
    )


class GapAnalysisRequest(BaseModel):
    """Request model for content gap analysis."""

    query: str = Field(..., description="Query to analyze for content gaps")


class BulkImportRequest(BaseModel):
    """Request model for bulk technology import."""

    technology_name: str = Field(
        ..., description="Name of technology to import documentation for"
    )


class EnrichmentStatusResponse(BaseModel):
    """Response model for enrichment status."""

    content_id: str = Field(..., description="Content ID")
    status: str = Field(..., description="Enrichment status")
    title: Optional[str] = Field(None, description="Content title")
    quality_score: Optional[float] = Field(None, description="Quality score")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")
    enrichment_available: bool = Field(
        False, description="Whether enrichment is available"
    )
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if applicable")


class EnrichmentSubmissionResponse(BaseModel):
    """Response model for enrichment task submission."""

    task_ids: List[str] = Field(..., description="List of submitted task IDs")
    content_id: str = Field(..., description="Content ID being enriched")
    enrichment_types: List[str] = Field(
        ..., description="Types of enrichment submitted"
    )
    priority: str = Field(..., description="Task priority")
    submitted_at: datetime = Field(..., description="Submission timestamp")


class BulkEnrichmentResponse(BaseModel):
    """Response model for bulk enrichment operations."""

    total_submitted: int = Field(..., description="Total content items submitted")
    successful_submissions: int = Field(
        ..., description="Number of successful submissions"
    )
    failed_submissions: int = Field(..., description="Number of failed submissions")
    task_ids: List[str] = Field(..., description="List of submitted task IDs")
    failures: List[Dict[str, Any]] = Field(
        ..., description="List of failed submissions"
    )
    enrichment_type: str = Field(..., description="Type of enrichment")
    priority: str = Field(..., description="Task priority")


class ErrorResponse(BaseModel):
    """Standardized error response model."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Error timestamp"
    )


# Exception to HTTP status code mapping
def map_enrichment_exception_to_http_status(exc: Exception) -> int:
    """
    Map enrichment exceptions to appropriate HTTP status codes.

    Args:
        exc: Exception to map

    Returns:
        HTTP status code
    """
    if isinstance(exc, InvalidTaskError):
        return status.HTTP_400_BAD_REQUEST
    elif isinstance(exc, EnrichmentTimeoutError):
        return status.HTTP_408_REQUEST_TIMEOUT
    elif isinstance(exc, AnalysisError):
        return status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, TaskProcessingError):
        return status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, EnrichmentError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR
    else:
        return status.HTTP_500_INTERNAL_SERVER_ERROR


def handle_enrichment_error(exc: Exception) -> HTTPException:
    """
    Convert enrichment exceptions to HTTPException with proper status codes.

    Args:
        exc: Exception to convert

    Returns:
        HTTPException with appropriate status code and message
    """
    status_code = map_enrichment_exception_to_http_status(exc)

    # Extract error context if available
    error_context = getattr(exc, "error_context", {})

    return HTTPException(
        status_code=status_code,
        detail={
            "error": exc.__class__.__name__,
            "message": str(exc),
            "details": error_context,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# Import the real dependency
from .dependencies import get_knowledge_enricher


@enrichment_router.post(
    "/enrich",
    response_model=EnrichmentSubmissionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        408: {"model": ErrorResponse, "description": "Request timeout"},
        422: {"model": ErrorResponse, "description": "Unprocessable entity"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
)
async def enrich_content(
    request: EnrichmentRequest,
    background_tasks: BackgroundTasks,
    enricher: KnowledgeEnricher = Depends(get_knowledge_enricher),
) -> EnrichmentSubmissionResponse:
    """
    Submit content for enrichment processing.

    Submits content for background enrichment with specified types and priority.
    Returns task IDs for tracking progress.

    Args:
        request: Enrichment request parameters
        background_tasks: FastAPI background tasks
        enricher: Knowledge enricher instance

    Returns:
        Enrichment submission response with task IDs

    Raises:
        HTTPException: For various error conditions with appropriate status codes
    """
    try:
        logger.info(f"Submitting enrichment for content: {request.content_id}")

        task_ids = await enricher.enrich_content(
            content_id=request.content_id,
            enrichment_types=request.enrichment_types,
            priority=request.priority,
        )

        response = EnrichmentSubmissionResponse(
            task_ids=task_ids,
            content_id=request.content_id,
            enrichment_types=(
                [t.value for t in request.enrichment_types]
                if request.enrichment_types
                else []
            ),
            priority=request.priority.value,
            submitted_at=datetime.utcnow(),
        )

        logger.info(
            f"Enrichment submitted: {len(task_ids)} tasks for content {request.content_id}"
        )
        return response

    except Exception as exc:
        logger.error(f"Content enrichment failed: {exc}")
        raise handle_enrichment_error(exc)


@enrichment_router.post(
    "/bulk-enrich",
    response_model=BulkEnrichmentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request parameters"},
        408: {"model": ErrorResponse, "description": "Request timeout"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
)
async def bulk_enrich_content(
    request: BulkEnrichmentRequest,
    background_tasks: BackgroundTasks,
    enricher: KnowledgeEnricher = Depends(get_knowledge_enricher),
) -> BulkEnrichmentResponse:
    """
    Submit multiple content items for bulk enrichment.

    Efficiently processes multiple content items with the same enrichment type.

    Args:
        request: Bulk enrichment request parameters
        background_tasks: FastAPI background tasks
        enricher: Knowledge enricher instance

    Returns:
        Bulk enrichment response with submission statistics

    Raises:
        HTTPException: For various error conditions with appropriate status codes
    """
    try:
        logger.info(f"Submitting bulk enrichment for {len(request.content_ids)} items")

        result = await enricher.trigger_bulk_enrichment(
            content_ids=request.content_ids,
            enrichment_type=request.enrichment_type,
            priority=request.priority,
        )

        response = BulkEnrichmentResponse(
            total_submitted=result["total_submitted"],
            successful_submissions=result["successful_submissions"],
            failed_submissions=result["failed_submissions"],
            task_ids=result["task_ids"],
            failures=result["failures"],
            enrichment_type=result["enrichment_type"],
            priority=result["priority"],
        )

        logger.info(
            f"Bulk enrichment submitted: {response.successful_submissions}/{response.total_submitted} successful"
        )
        return response

    except Exception as exc:
        logger.error(f"Bulk enrichment failed: {exc}")
        raise handle_enrichment_error(exc)


@enrichment_router.get(
    "/status/{content_id}",
    response_model=EnrichmentStatusResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Content not found"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def get_enrichment_status(
    content_id: str, enricher: KnowledgeEnricher = Depends(get_knowledge_enricher)
) -> EnrichmentStatusResponse:
    """
    Get enrichment status for specific content.

    Returns current enrichment status and metadata for the specified content ID.

    Args:
        content_id: Content identifier
        enricher: Knowledge enricher instance

    Returns:
        Enrichment status information

    Raises:
        HTTPException: If content not found or other errors occur
    """
    try:
        logger.debug(f"Getting enrichment status for content: {content_id}")

        status_data = await enricher.get_enrichment_status(content_id)

        if status_data.get("status") == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "ContentNotFound",
                    "message": f"Content with ID '{content_id}' not found",
                    "details": {"content_id": content_id},
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        response = EnrichmentStatusResponse(
            content_id=status_data["content_id"],
            status=status_data["status"],
            title=status_data.get("title"),
            quality_score=status_data.get("quality_score"),
            created_at=status_data.get("created_at"),
            updated_at=status_data.get("updated_at"),
            enrichment_available=status_data.get("enrichment_available", False),
            message=status_data.get("message"),
            error=status_data.get("error"),
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as exc:
        logger.error(f"Failed to get enrichment status: {exc}")
        raise handle_enrichment_error(exc)


@enrichment_router.post(
    "/gap-analysis",
    response_model=List[ContentGap],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query parameters"},
        422: {"model": ErrorResponse, "description": "Analysis failed"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
)
async def analyze_content_gaps(
    request: GapAnalysisRequest,
    enricher: KnowledgeEnricher = Depends(get_knowledge_enricher),
) -> List[ContentGap]:
    """
    Analyze content gaps for given query.

    Identifies areas where content coverage is insufficient and suggests
    enrichment strategies.

    Args:
        request: Gap analysis request with query
        enricher: Knowledge enricher instance

    Returns:
        List of identified content gaps

    Raises:
        HTTPException: For various error conditions with appropriate status codes
    """
    try:
        logger.info(f"Analyzing content gaps for query: {request.query}")

        # Execute gap analysis (this calls the new _execute_gap_analysis method)
        gap_strategies = await enricher._execute_gap_analysis(request.query)

        # Convert to ContentGap models
        gaps = []
        for strategy in gap_strategies:
            gap = ContentGap(
                query=strategy["query"],
                gap_type=strategy["gap_type"],
                confidence=strategy["confidence"],
                suggested_sources=strategy["suggested_sources"],
                priority=strategy["priority"],
                metadata=strategy.get("metadata", {}),
            )
            gaps.append(gap)

        logger.info(f"Gap analysis completed: {len(gaps)} gaps identified")
        return gaps

    except Exception as exc:
        logger.error(f"Gap analysis failed: {exc}")
        raise handle_enrichment_error(exc)


@enrichment_router.get(
    "/metrics",
    response_model=EnrichmentMetrics,
    responses={500: {"model": ErrorResponse, "description": "Internal server error"}},
)
async def get_enrichment_metrics(
    enricher: KnowledgeEnricher = Depends(get_knowledge_enricher),
) -> EnrichmentMetrics:
    """
    Get enrichment system performance metrics.

    Returns current system metrics including processing statistics,
    success rates, and performance data.

    Args:
        enricher: Knowledge enricher instance

    Returns:
        Current system metrics

    Raises:
        HTTPException: If metrics retrieval fails
    """
    try:
        logger.debug("Getting enrichment system metrics")

        metrics = await enricher.get_system_metrics()
        return metrics

    except Exception as exc:
        logger.error(f"Failed to get enrichment metrics: {exc}")
        raise handle_enrichment_error(exc)


@enrichment_router.get(
    "/analytics",
    response_model=EnrichmentAnalytics,
    responses={500: {"model": ErrorResponse, "description": "Internal server error"}},
)
async def get_enrichment_analytics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    enricher: KnowledgeEnricher = Depends(get_knowledge_enricher),
) -> EnrichmentAnalytics:
    """
    Get enrichment analytics for specified period.

    Returns detailed analytics data for performance monitoring and optimization.

    Args:
        start_date: Analytics period start (optional)
        end_date: Analytics period end (optional)
        enricher: Knowledge enricher instance

    Returns:
        Analytics data for the specified period

    Raises:
        HTTPException: If analytics retrieval fails
    """
    try:
        logger.debug(f"Getting enrichment analytics from {start_date} to {end_date}")

        analytics_data = await enricher.get_enrichment_analytics(start_date, end_date)

        # Convert to EnrichmentAnalytics model
        analytics = EnrichmentAnalytics(
            period_start=datetime.fromisoformat(
                analytics_data["period"]["start"].replace("Z", "+00:00")
            ),
            period_end=datetime.fromisoformat(
                analytics_data["period"]["end"].replace("Z", "+00:00")
            ),
            total_content_enriched=analytics_data["summary"]["total_tasks_processed"],
            tags_generated=0,  # Would be calculated from actual data
            relationships_identified=0,  # Would be calculated from actual data
            average_quality_improvement=0.0,  # Would be calculated from actual data
            processing_efficiency=1.0 - analytics_data["system_health"]["error_rate"],
            error_patterns={},  # Would be populated from actual error analysis
            performance_trends={},  # Would be populated from time-series data
        )

        return analytics

    except Exception as exc:
        logger.error(f"Failed to get enrichment analytics: {exc}")
        raise handle_enrichment_error(exc)


@enrichment_router.post(
    "/bulk-import",
    response_model=EnrichmentResult,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid technology name"},
        408: {"model": ErrorResponse, "description": "Import timeout"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
)
async def bulk_import_technology(
    request: BulkImportRequest,
    background_tasks: BackgroundTasks,
    enricher: KnowledgeEnricher = Depends(get_knowledge_enricher),
) -> EnrichmentResult:
    """
    Perform bulk import for an entire technology's documentation.

    Imports comprehensive documentation for a specific technology from
    multiple sources including GitHub repositories and official documentation.

    Args:
        request: Bulk import request with technology name
        background_tasks: FastAPI background tasks
        enricher: Knowledge enricher instance

    Returns:
        EnrichmentResult with bulk import outcomes

    Raises:
        HTTPException: For various error conditions with appropriate status codes
    """
    try:
        logger.info(f"Starting bulk import for technology: {request.technology_name}")

        result = await enricher.bulk_import_technology(request.technology_name)

        logger.info(f"Bulk import completed for {request.technology_name}")
        return result

    except Exception as exc:
        logger.error(f"Bulk import failed: {exc}")
        raise handle_enrichment_error(exc)


@enrichment_router.get(
    "/health",
    response_model=Dict[str, Any],
    responses={503: {"model": ErrorResponse, "description": "Service unhealthy"}},
)
async def enrichment_health_check(
    enricher: KnowledgeEnricher = Depends(get_knowledge_enricher),
) -> Dict[str, Any]:
    """
    Check health of enrichment system.

    Returns health status of enrichment components and dependencies.

    Args:
        enricher: Knowledge enricher instance

    Returns:
        Health status information

    Raises:
        HTTPException: If system is unhealthy
    """
    try:
        health_data = await enricher.health_check()

        if health_data.get("status") == "unhealthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=health_data
            )

        return health_data

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "error": str(exc),
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
