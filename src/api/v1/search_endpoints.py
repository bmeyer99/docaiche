"""
Search API Endpoints - PRD-001: HTTP API Foundation
Search, feedback, and signals endpoints
"""

import logging
from typing import Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request

from .schemas import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    FeedbackRequest,
    SignalRequest,
)
from .middleware import limiter
from .dependencies import get_database_manager, get_search_orchestrator
from src.database.connection import DatabaseManager
from src.search.orchestrator import SearchOrchestrator

logger = logging.getLogger(__name__)

# Create router for search endpoints
router = APIRouter()


@router.post("/search", response_model=SearchResponse, tags=["search"])
@limiter.limit("30/minute")
async def search_documents_post(
    request: Request,
    search_request: SearchRequest,
    background_tasks: BackgroundTasks,
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator),
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
    try:
        logger.info(f"Search request: {search_request.query[:100]}...")

        # For now, return mock data until search orchestrator integration is complete
        mock_results = [
            SearchResult(
                content_id="doc_001",
                title="Getting Started with FastAPI",
                snippet="FastAPI is a modern, fast web framework for building APIs with Python 3.7+ based on standard Python type hints...",
                source_url="https://fastapi.tiangolo.com/tutorial/",
                technology="python",
                relevance_score=0.95,
                content_type="documentation",
                workspace="python-docs",
            ),
            SearchResult(
                content_id="doc_002",
                title="FastAPI Request Body",
                snippet="When you need to send data from a client to your API, you send it as a request body...",
                source_url="https://fastapi.tiangolo.com/tutorial/body/",
                technology="python",
                relevance_score=0.87,
                content_type="documentation",
                workspace="python-docs",
            ),
        ]

        return SearchResponse(
            results=mock_results[: search_request.limit],
            total_count=len(mock_results),
            query=search_request.query,
            technology_hint=search_request.technology_hint,
            execution_time_ms=45,
            cache_hit=False,
            enrichment_triggered=False,
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
    request: Request, signal_request: SignalRequest, background_tasks: BackgroundTasks
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
