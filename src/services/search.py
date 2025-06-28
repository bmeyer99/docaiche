"""
Search service implementation.

Connects the API layer to the SearchOrchestrator backend,
providing document search and retrieval functionality.
"""

from typing import Optional
import time

from src.api.schemas import SearchRequest, SearchResponse, SearchResult
from src.search.orchestrator import SearchOrchestrator
from src.search.models import SearchQuery


class SearchService:
    """
    Service for handling document search operations.

    This service connects the API layer to the SearchOrchestrator,
    translating between API schemas and internal search models.
    """

    def __init__(self, orchestrator: Optional[SearchOrchestrator] = None):
        """
        Initialize the search service.

        Args:
            orchestrator: Optional SearchOrchestrator instance. If not provided,
                         search functionality will return empty results.
        """
        self.orchestrator = orchestrator

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Perform a search operation using the SearchOrchestrator.

        Args:
            request: The search request with query and parameters

        Returns:
            SearchResponse with results and metadata
        """
        start_time = time.time()

        if not self.orchestrator:
            # Return empty results if orchestrator is not available
            return SearchResponse(
                results=[],
                total_count=0,
                query=request.query,
                technology_hint=request.technology_hint,
                execution_time_ms=0,
                cache_hit=False,
                enrichment_triggered=False,
            )

        try:
            # Convert API request to internal search query
            search_query = SearchQuery(
                query=request.query,
                filters={
                    "technology": request.technology_hint,
                    "content_type": request.content_type_filter,
                    "source": request.source_filter,
                    "date_from": request.date_from,
                    "date_to": request.date_to,
                },
                limit=request.limit,
                offset=request.offset,
            )

            # Execute search through orchestrator
            search_result = await self.orchestrator.search(search_query)

            # Convert internal search results to API response format
            api_results = []
            for result in search_result.results:
                api_results.append(
                    SearchResult(
                        content_id=result.content_id,
                        title=result.title,
                        snippet=result.snippet,
                        source_url=result.source_url,
                        technology=result.technology or "general",
                        relevance_score=result.relevance_score,
                        content_type=result.content_type,
                        workspace=result.workspace or "default",
                        created_at=result.created_at,
                        updated_at=result.updated_at,
                    )
                )

            execution_time_ms = int((time.time() - start_time) * 1000)

            return SearchResponse(
                results=api_results,
                total_count=search_result.total_count,
                query=request.query,
                technology_hint=request.technology_hint,
                execution_time_ms=execution_time_ms,
                cache_hit=search_result.cache_hit,
                enrichment_triggered=search_result.enrichment_triggered,
            )

        except Exception as e:
            # Log error internally but don't expose details to client
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Search failed for query '{request.query}': {str(e)}")

            execution_time_ms = int((time.time() - start_time) * 1000)
            return SearchResponse(
                results=[],
                total_count=0,
                query=request.query,
                technology_hint=request.technology_hint,
                execution_time_ms=execution_time_ms,
                cache_hit=False,
                enrichment_triggered=False,
                error="Search service temporarily unavailable",
            )

    async def get_document_by_id(self, content_id: str) -> Optional[dict]:
        """
        Retrieve a specific document by ID from the database.

        Args:
            content_id: The unique document identifier

        Returns:
            Document data if found, None otherwise
        """
        if not self.orchestrator:
            return None

        try:
            # Use orchestrator's database manager to fetch document
            if (
                hasattr(self.orchestrator, "db_manager")
                and self.orchestrator.db_manager
            ):
                query = """
                SELECT content_id, title, content, source_url, technology, 
                       content_type, workspace, created_at, updated_at, metadata
                FROM content_metadata
                WHERE content_id = :content_id
                """
                result = await self.orchestrator.db_manager.fetch_one(
                    query, {"content_id": content_id}
                )

                if result:
                    return {
                        "content_id": result["content_id"],
                        "title": result["title"],
                        "content": result["content"],
                        "source_url": result["source_url"],
                        "technology": result["technology"],
                        "content_type": result["content_type"],
                        "workspace": result["workspace"],
                        "created_at": (
                            result["created_at"].isoformat()
                            if result["created_at"]
                            else None
                        ),
                        "updated_at": (
                            result["updated_at"].isoformat()
                            if result["updated_at"]
                            else None
                        ),
                        "metadata": result["metadata"],
                    }

            return None

        except Exception:
            # Log error and return None
            return None
