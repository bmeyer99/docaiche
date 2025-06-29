"""
Search API Endpoints - PRD-001: HTTP API Foundation
Search, feedback, and signals endpoints
"""

import logging
import time
from typing import Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request

from .schemas import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    FeedbackRequest,
    SignalRequest,
)
from .middleware import limiter, get_trace_id
from .dependencies import get_database_manager, get_search_orchestrator, get_configuration_manager
from src.database.connection import DatabaseManager
from src.search.orchestrator import SearchOrchestrator
from src.core.config.manager import ConfigurationManager
logger = logging.getLogger(__name__)

# Import enhanced logging for search security monitoring
try:
    from src.logging_config import MetricsLogger, SecurityLogger, ExternalServiceLogger
    metrics = MetricsLogger(logger)
    _security_logger = SecurityLogger(logger)
    _service_logger = ExternalServiceLogger(logger)
except ImportError:
    metrics = None
    _security_logger = None
    _service_logger = None
    logger.warning("Enhanced search security logging not available")

# Create router for search endpoints
router = APIRouter()


@router.post("/search", response_model=SearchResponse, tags=["search"])
@limiter.limit("30/minute")
async def search_documents_post(
    request: Request,
    search_request: SearchRequest,
    background_tasks: BackgroundTasks,
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator),
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> SearchResponse:
    """
    POST /api/v1/search - Initiates a search query

    Executes search through the search orchestrator with background enrichment.

    Args:
        request: FastAPI request object (required for rate limiting)
        search_request: Search request with query and parameters
        background_tasks: FastAPI background tasks for enrichment
        search_orchestrator: Search orchestrator dependency

    Returns:
        SearchResponse with results and metadata

    Raises:
        HTTPException: If search execution fails
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    trace_id = get_trace_id(request)
    
    try:
        
        logger.info(f"Search request: query={search_request.query!r}, tech_hint={search_request.technology_hint!r} (type: {type(search_request.technology_hint)}), limit={search_request.limit!r}")
        
        # Execute real search through the orchestrator
        search_response = await search_orchestrator.search(
            query=search_request.query,
            technology_hint=search_request.technology_hint,
            limit=search_request.limit,
            offset=0,  # Default offset as it's not in SearchRequest
            session_id=search_request.session_id
        )
        
        # Convert orchestrator results to API schema
        results = []
        for result in search_response.results[:search_request.limit]:
            results.append(SearchResult(
                content_id=result.content_id,
                title=result.title or "Untitled",
                snippet=result.snippet or "",
                source_url=result.source_url or "",
                technology=result.technology or "unknown",
                relevance_score=result.relevance_score,
                content_type=result.content_type or "document",
                workspace=result.workspace or "default",
            ))
        
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        cache_hit = getattr(search_response, 'cache_hit', False)
        
        # Log search metrics
        if metrics:
            metrics.log_search_query(
                query=search_request.query,
                result_count=len(results),
                cache_hit=cache_hit,
                duration=execution_time / 1000,  # Convert back to seconds for logging
                technology_hint=search_request.technology_hint,
                session_id=search_request.session_id
            )

        logger.debug(f"Creating SearchResponse with technology_hint={search_request.technology_hint!r} (type: {type(search_request.technology_hint)})")
        
        return SearchResponse(
            results=results,
            total_count=len(search_response.results),
            query=search_request.query,
            technology_hint=search_request.technology_hint,
            execution_time_ms=int(execution_time),
            cache_hit=cache_hit,
            enrichment_triggered=getattr(search_response, 'enrichment_triggered', False),
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search execution failed")


@router.get("/search", response_model=SearchResponse, tags=["search"])
@limiter.limit("60/minute")
async def search_documents_get(
    request: Request,
    q: str = Query(..., description="Search query string"),
    technology_hint: Optional[str] = Query(None, description="Technology filter"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    session_id: Optional[str] = Query(None, description="Session identifier"),
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator),
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> SearchResponse:
    """
    GET /api/v1/search - GET alternative for simple queries and browser testing

    Args:
        request: FastAPI request object (required for rate limiting)
        q: Search query string
        technology_hint: Optional technology filter
        limit: Maximum number of results
        session_id: Optional session identifier
        search_orchestrator: Search orchestrator dependency

    Returns:
        SearchResponse with results and metadata
    """
    # Convert GET parameters to SearchRequest
    search_request = SearchRequest(
        query=q, technology_hint=technology_hint, limit=limit, session_id=session_id
    )

    # Use the same logic as POST endpoint
    return await search_documents_post(
        request, search_request, BackgroundTasks(), search_orchestrator
    )


@router.post("/feedback", status_code=202, tags=["feedback"])
@limiter.limit("20/minute")
async def submit_feedback(
    request: Request,
    feedback_request: FeedbackRequest,
    background_tasks: BackgroundTasks,
    db_manager: DatabaseManager = Depends(get_database_manager),
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> Dict[str, str]:
    """
    POST /api/v1/feedback - Submits explicit user feedback on a search result

    Args:
        request: FastAPI request object (required for rate limiting)
        feedback_request: Feedback request with content ID and feedback details
        background_tasks: FastAPI background tasks for processing
        db_manager: Database manager dependency

    Returns:
        Confirmation message with HTTP 202
    """
    try:
        logger.info(
            f"Feedback received for content {feedback_request.content_id}: {feedback_request.feedback_type}"
        )

        # Add background task to process feedback (placeholder)
        def process_feedback():
            logger.info(
                f"Processing feedback: {feedback_request.content_id} - {feedback_request.feedback_type}"
            )
            # TODO: Implement feedback processing when PRD-011 is available

        background_tasks.add_task(process_feedback)

        return {"message": "Feedback received and will be processed"}

    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        raise HTTPException(status_code=500, detail="Feedback submission failed")


@router.post("/signals", status_code=202, tags=["feedback"])
@limiter.limit("100/minute")
async def submit_signal(
    request: Request, 
    signal_request: SignalRequest, 
    background_tasks: BackgroundTasks,
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> Dict[str, str]:
    """
    POST /api/v1/signals - Submits implicit user interaction signals

    Validates SignalRequest and calls feedback_collector.record_implicit_signal
    as background task, returns HTTP 202.

    Args:
        request: FastAPI request object (required for rate limiting)
        signal_request: Signal request with interaction details
        background_tasks: FastAPI background tasks for processing

    Returns:
        Confirmation message with HTTP 202
    """
    try:
        logger.info(
            f"Signal received: {signal_request.signal_type} for query {signal_request.query_id}"
        )

        # Add background task to record signal (placeholder)
        def record_signal():
            logger.info(
                f"Recording signal: {signal_request.signal_type} - {signal_request.query_id}"
            )
            # TODO: Call feedback_collector.record_implicit_signal when PRD-011 is available

        background_tasks.add_task(record_signal)

        return {"message": "Signal received and will be processed"}

    except Exception as e:
        logger.error(f"Signal submission failed: {e}")
        raise HTTPException(status_code=500, detail="Signal submission failed")
