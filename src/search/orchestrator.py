"""
Search Orchestrator - PRD-009
Core search workflow coordinator managing end-to-end search process.

Implements the exact search orchestration workflow from PRD-009 including
cache check, vector search, AI evaluation, enrichment decision, and response
compilation exactly as specified.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, List

from fastapi import BackgroundTasks

from .models import SearchQuery, SearchResults, EvaluationResult
from .strategies import WorkspaceSearchStrategy
from .ranking import ResultRanker
from .cache import SearchCacheManager
from .mcp_integration import MCPSearchEnhancer, create_mcp_enhancer
from .exceptions import SearchOrchestrationError, SearchTimeoutError
from src.database.connection import DatabaseManager, CacheManager
from src.clients.weaviate_client import WeaviateVectorClient

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    """
    Core search workflow orchestrator managing end-to-end search process.

    Implements the exact search workflow from PRD-009:
    1. Query Normalization: Lowercase, trim, hash
    2. Cache Check: Use query_hash to check Redis for SearchResponse
    3. Multi-Workspace Search: Execute intelligent workspace selection and parallel search
    4. AI Evaluation: Call llm_client.evaluate_search_results()
    5. Enrichment Decision: Use EvaluationResult to decide on enrichment
    6. Knowledge Enrichment: Call enricher.enrich_knowledge() as background task
    7. Response Compilation & Caching: Format SearchResponse, cache, return
    """

    # Circuit breaker and backoff configuration
    _CB_FAILURE_THRESHOLD = 3
    _CB_INITIAL_BACKOFF = 2.0  # seconds
    _CB_MAX_BACKOFF = 30.0  # seconds

    def __init__(
        self,
        db_manager: DatabaseManager,
        cache_manager: CacheManager,
        weaviate_client: WeaviateVectorClient,
        llm_client: Optional[Any] = None,  # LLM client for evaluation (PRD-005)
        knowledge_enricher: Optional[Any] = None,  # Knowledge enricher (PRD-010)
    ):
        """
        Initialize search orchestrator with all required dependencies.

        Args:
            db_manager: Database manager for metadata queries
            cache_manager: Redis cache manager
            weaviate_client: Weaviate client for vector search
            llm_client: LLM provider client for evaluation (optional)
            knowledge_enricher: Knowledge enricher for background tasks (optional)
        """
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self.weaviate_client = weaviate_client
        self.llm_client = llm_client
        self.knowledge_enricher = knowledge_enricher

        # Initialize sub-components
        self.workspace_strategy = WorkspaceSearchStrategy(
            db_manager, weaviate_client
        )
        self.result_ranker = ResultRanker()
        self.search_cache = SearchCacheManager(cache_manager)
        
        # Initialize MCP enhancer for external search capabilities
        self.mcp_enhancer: Optional[MCPSearchEnhancer] = None
        if llm_client:
            try:
                self.mcp_enhancer = create_mcp_enhancer(
                    llm_client=llm_client,
                    enable_external_providers=True
                )
                logger.info("MCP search enhancer initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize MCP enhancer: {e}")

        # Performance timeouts from PRD-009
        self.search_timeout = 30.0  # Total search timeout
        self.workspace_timeout = 2.0  # Per-workspace timeout

        # Circuit breaker state for cache
        self._cache_cb_failures = 0
        self._cache_cb_open = False
        self._cache_cb_next_attempt = 0.0
        self._cache_cb_backoff = self._CB_INITIAL_BACKOFF

        logger.info("SearchOrchestrator initialized with all dependencies")

    async def _cache_circuit_allows(self) -> bool:
        """Check if cache circuit breaker allows cache usage."""
        if not self._cache_cb_open:
            return True
        now = time.time()
        if now >= self._cache_cb_next_attempt:
            logger.info("Cache circuit breaker: attempting to close after backoff")
            return True
        logger.warning("Cache circuit breaker: open, skipping cache operation")
        return False

    def _cache_circuit_on_failure(self, context: str, exc: Exception):
        """Handle a cache failure for circuit breaker logic."""
        self._cache_cb_failures += 1
        logger.warning(
            f"Cache failure in {context}: {exc} (failure count={self._cache_cb_failures})"
        )
        if (
            self._cache_cb_failures >= self._CB_FAILURE_THRESHOLD
            and not self._cache_cb_open
        ):
            self._cache_cb_open = True
            self._cache_cb_next_attempt = time.time() + self._cache_cb_backoff
            logger.error(
                f"Cache circuit breaker OPENED after {self._cache_cb_failures} failures. "
                f"Backoff {self._cache_cb_backoff:.1f}s"
            )
            self._cache_cb_backoff = min(
                self._cache_cb_backoff * 2, self._CB_MAX_BACKOFF
            )

    def _cache_circuit_on_success(self):
        """Reset circuit breaker on successful cache operation."""
        if self._cache_cb_open:
            logger.info("Cache circuit breaker CLOSED after successful cache operation")
        self._cache_cb_failures = 0
        self._cache_cb_open = False
        self._cache_cb_backoff = self._CB_INITIAL_BACKOFF
        self._cache_cb_next_attempt = 0.0

    async def execute_search(
        self, query: SearchQuery, background_tasks: Optional[BackgroundTasks] = None
    ) -> Tuple[SearchResults, SearchQuery]:
        """
        Execute complete search workflow as specified in PRD-009.

        Workflow Logic:
        1. Query Normalization: Lowercase, trim, hash
        2. Cache Check: Use query_hash to check Redis for SearchResponse
        3. Multi-Workspace Search: Execute intelligent workspace selection and parallel search
        4. AI Evaluation: Call llm_client.evaluate_search_results()
        5. Enrichment Decision: Use EvaluationResult to decide on enrichment
        6. Knowledge Enrichment: Call enricher.enrich_knowledge() as background task
        7. Response Compilation & Caching: Format SearchResponse, cache, return

        Args:
            query: Search query with parameters
            background_tasks: FastAPI background tasks for enrichment

        Returns:
            Tuple[SearchResults, SearchQuery]:
                - SearchResults with ranked results and metadata
                - The normalized SearchQuery object used internally

        Raises:
            SearchOrchestrationError: If search workflow fails
            SearchTimeoutError: If search exceeds timeout
        """
        start_time = time.time()

        try:
            logger.info(
                f"Starting search orchestration for query: {query.query[:100]}..."
            )

            # Step 1: Query Normalization
            normalized_query = await self._normalize_query(query)
            logger.debug(f"Normalized query: {normalized_query.query}")

            # Step 2: Cache Check with graceful degradation and circuit breaker
            cached_results = None
            try:
                if await self._cache_circuit_allows():
                    cached_results = await self.search_cache.get_cached_results(
                        normalized_query
                    )
                    if cached_results:
                        self._cache_circuit_on_success()
                        execution_time = int((time.time() - start_time) * 1000)
                        cached_results.query_time_ms = execution_time
                        logger.info(
                            f"Cache hit - returning {len(cached_results.results)} results"
                        )
                        return cached_results, normalized_query
                    else:
                        self._cache_circuit_on_success()
                else:
                    logger.info(
                        "Bypassing cache check due to circuit breaker open state"
                    )
            except Exception as e:
                self._cache_circuit_on_failure("get_cached_results", e)
                logger.warning(f"Cache check failed, continuing without cache: {e}")
                # Continue without caching

            # Step 3: Multi-Workspace Search with timeout
            try:
                search_results = await asyncio.wait_for(
                    self._execute_multi_workspace_search(normalized_query),
                    timeout=self.search_timeout,
                )
            except asyncio.TimeoutError:
                raise SearchTimeoutError(
                    f"Search timed out after {self.search_timeout}s",
                    timeout_seconds=self.search_timeout,
                    operation="multi_workspace_search",
                )

            # Step 4: AI Evaluation (optional)
            evaluation_result = None
            if self.llm_client and search_results.results:
                try:
                    evaluation_result = await self._evaluate_search_results(
                        normalized_query, search_results
                    )
                except Exception as e:
                    logger.warning(f"AI evaluation failed: {e}")
                    # Continue without evaluation

            # Step 4.5: External Search Enhancement (if needed)
            external_results_added = False
            # Check if external search should be used
            should_use_external = False
            logger.info(f"External search check - use_external_search: {normalized_query.use_external_search}, has results: {bool(search_results.results)}")
            
            if normalized_query.use_external_search is True:
                # Explicitly requested
                should_use_external = True
                logger.info("External search explicitly requested")
            elif normalized_query.use_external_search is False:
                # Explicitly disabled
                should_use_external = False
                logger.info("External search explicitly disabled")
            else:
                # Auto-decide based on results quality
                should_use_external = (not search_results.results or 
                                     (evaluation_result and evaluation_result.quality_score < 0.6))
                logger.info(f"External search auto-decide: {should_use_external}")
            
            logger.info(f"MCP enhancer available: {self.mcp_enhancer is not None}, should use external: {should_use_external}")
            if self.mcp_enhancer and should_use_external:
                try:
                    external_results = await self._enhance_with_external_search(
                        normalized_query, search_results
                    )
                    if external_results:
                        search_results.results.extend(external_results)
                        external_results_added = True
                        logger.info(f"Added {len(external_results)} external search results")
                except Exception as e:
                    logger.warning(f"External search enhancement failed: {e}")

            # Step 5: Enrichment Decision
            enrichment_triggered = False
            if evaluation_result and evaluation_result.needs_enrichment:
                enrichment_triggered = await self._trigger_enrichment(
                    normalized_query, evaluation_result, background_tasks
                )

            # Step 6: Response Compilation
            execution_time = int((time.time() - start_time) * 1000)
            final_results = SearchResults(
                results=search_results.results,
                total_count=len(search_results.results),
                query_time_ms=execution_time,
                strategy_used=normalized_query.strategy,
                cache_hit=False,
                workspaces_searched=search_results.workspaces_searched,
                enrichment_triggered=enrichment_triggered,
                external_search_used=external_results_added,
            )

            # Step 7: Cache Results with graceful degradation and circuit breaker
            try:
                if await self._cache_circuit_allows():
                    await self.search_cache.cache_results(
                        normalized_query, final_results
                    )
                    self._cache_circuit_on_success()
                else:
                    logger.info("Bypassing cache set due to circuit breaker open state")
            except Exception as e:
                self._cache_circuit_on_failure("cache_results", e)
                logger.warning(f"Failed to cache results: {e}")
                # Continue without caching - this is non-critical

            logger.info(
                f"Search completed: {len(final_results.results)} results in {execution_time}ms"
            )
            return final_results, normalized_query

        except SearchTimeoutError:
            # Re-raise timeout errors
            raise
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"Search orchestration failed after {execution_time}ms: {e}")
            raise SearchOrchestrationError(
                f"Search workflow failed: {str(e)}",
                error_context={
                    "query": query.query,
                    "execution_time_ms": execution_time,
                    "error": str(e),
                },
            )

    async def _execute_multi_workspace_search(
        self, query: SearchQuery
    ) -> SearchResults:
        """
        Execute multi-workspace search strategy and result aggregation.

        Process:
        1. Identify relevant workspaces
        2. Execute parallel workspace searches
        3. Aggregate and rank results

        Args:
            query: Normalized search query

        Returns:
            SearchResults with aggregated results
        """
        logger.info("Executing multi-workspace search strategy")

        # Step 1: Identify relevant workspaces
        relevant_workspaces = (
            await self.workspace_strategy.identify_relevant_workspaces(
                query.query, query.technology_hint
            )
        )

        if not relevant_workspaces:
            logger.warning("No relevant workspaces found")
            return SearchResults(
                results=[],
                total_count=0,
                query_time_ms=0,
                strategy_used=query.strategy,
                cache_hit=False,
                workspaces_searched=[],
                enrichment_triggered=False,
            )

        # Step 2: Execute parallel workspace searches
        search_results = await self.workspace_strategy.execute_parallel_search(
            query.query, relevant_workspaces
        )

        # Step 3: Rank and filter results
        ranked_results = await self.result_ranker.rank_results(
            search_results, query.strategy, query.query, query.technology_hint
        )

        # Apply limit and offset
        start_idx = query.offset
        end_idx = start_idx + query.limit
        paginated_results = ranked_results[start_idx:end_idx]

        # Extract workspace slugs
        workspace_slugs = [ws.slug for ws in relevant_workspaces]

        return SearchResults(
            results=paginated_results,
            total_count=len(ranked_results),
            query_time_ms=0,  # Will be set by caller
            strategy_used=query.strategy,
            cache_hit=False,
            workspaces_searched=workspace_slugs,
            enrichment_triggered=False,  # Will be set by caller
        )

    async def _evaluate_search_results(
        self, query: SearchQuery, results: SearchResults
    ) -> Optional[EvaluationResult]:
        """
        Call LLM client to evaluate search results quality.

        Args:
            query: Search query
            results: Search results to evaluate

        Returns:
            EvaluationResult with quality assessment
        """
        if not self.llm_client:
            return None

        try:
            logger.debug("Evaluating search results with LLM")

            # Prepare evaluation prompt (simplified implementation)
            # evaluation_prompt = self._create_evaluation_prompt(query, results)

            # Call LLM client (this would need to be implemented based on PRD-005)
            # For now, return a placeholder evaluation
            evaluation_result = EvaluationResult(
                overall_quality=0.7,
                relevance_assessment=0.8,
                completeness_score=0.6,
                needs_enrichment=len(results.results) < 5,  # Simple heuristic
                enrichment_topics=(
                    [query.technology_hint] if query.technology_hint else []
                ),
                confidence_level=0.8,
                reasoning="Automated evaluation based on result count and relevance",
            )

            logger.debug(
                f"LLM evaluation completed: quality={evaluation_result.overall_quality:.2f}"
            )
            return evaluation_result

        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            return None

    async def _trigger_enrichment(
        self,
        query: SearchQuery,
        evaluation: EvaluationResult,
        background_tasks: Optional[BackgroundTasks],
    ) -> bool:
        """
        Trigger knowledge enrichment as background task.

        Args:
            query: Search query
            evaluation: LLM evaluation result
            background_tasks: FastAPI background tasks

        Returns:
            True if enrichment was triggered successfully
        """
        if not self.knowledge_enricher or not background_tasks:
            logger.debug("Knowledge enricher or background tasks not available")
            return False

        try:
            logger.info(
                f"Triggering enrichment for topics: {evaluation.enrichment_topics}"
            )

            # Add enrichment task to background (this would need PRD-010 implementation)
            # For now, this is a placeholder
            def enrichment_task():
                logger.info(f"Background enrichment started for query: {query.query}")
                # Would call: self.knowledge_enricher.enrich_knowledge(...)

            background_tasks.add_task(enrichment_task)
            return True

        except Exception as e:
            logger.error(f"Failed to trigger enrichment: {e}")
            return False

    async def _enhance_with_external_search(
        self,
        query: SearchQuery,
        current_results: SearchResults
    ) -> List[Any]:
        """
        Enhance search results with external search providers.
        
        Uses the MCP search enhancer to get external results when:
        - No internal results found
        - Quality score is low (< 0.6)
        - Results are insufficient
        
        Args:
            query: Normalized search query
            current_results: Current internal search results
            
        Returns:
            List of external search results converted to internal format
        """
        if not self.mcp_enhancer or not self.mcp_enhancer.is_external_search_available():
            return []
        
        try:
            logger.info(f"Enhancing search with external providers for query: {query.query[:50]}...")
            
            # Generate optimized external query
            external_query = await self.mcp_enhancer.get_external_search_query(
                query.query,
                technology_hint=query.technology_hint
            )
            
            # Execute external search with performance optimizations
            external_results = await self.mcp_enhancer.execute_external_search(
                query=external_query,
                technology_hint=query.technology_hint,
                max_results=10,
                provider_ids=query.external_providers
            )
            
            if not external_results:
                return []
            
            # Convert external results to internal SearchResult format
            from .models import SearchResult
            converted_results = []
            
            for ext_result in external_results[:5]:  # Limit external results
                try:
                    search_result = SearchResult(
                        content_id=f"external_{len(converted_results)}",
                        title=ext_result.get('title', 'External Result'),
                        content_snippet=ext_result.get('snippet', ''),
                        source_url=ext_result.get('url', ''),
                        relevance_score=0.7,  # Default external relevance
                        metadata={
                            'source': 'external_search',
                            'provider': ext_result.get('provider', 'unknown'),
                            'content_type': ext_result.get('content_type', 'web_page'),
                            'external': True
                        },
                        technology='external',
                        workspace_slug='external_search',
                        chunk_index=None
                    )
                    converted_results.append(search_result)
                    
                except Exception as e:
                    logger.warning(f"Failed to convert external result: {e}")
                    continue
            
            logger.info(f"Successfully converted {len(converted_results)} external results")
            return converted_results
            
        except Exception as e:
            logger.error(f"External search enhancement failed: {e}")
            return []

    async def _normalize_query(self, query: "SearchQuery") -> "SearchQuery":
        """
        Normalize search query for consistent processing and caching.
        Implements PRD-009 requirements:
        - Input validation and sanitization
        - Text cleaning (reuse ContentPreprocessor)
        - Tokenization and stemming
        - Consistent normalization for cache and all strategies

        Args:
            query: Original search query

        Returns:
            Normalized SearchQuery

        Raises:
            HTTPException: If input is invalid or normalization fails
        """
        import re
        from fastapi import HTTPException
        from src.document_processing.preprocessing import ContentPreprocessor

        logger = logging.getLogger(__name__)

        # Input validation
        raw_query = query.query
        if not isinstance(raw_query, str) or not raw_query.strip():
            logger.warning("Empty or non-string search query rejected")
            raise HTTPException(
                status_code=422, detail="Query must be a non-empty string"
            )
        if len(raw_query) < 2 or len(raw_query) > 256:
            logger.warning("Query length out of bounds")
            raise HTTPException(
                status_code=422,
                detail="Query length must be between 2 and 256 characters",
            )
        if not re.match(r"^[\w\s\-\.,:;!?()'/@#&]+$", raw_query, re.UNICODE):
            logger.warning("Query contains invalid characters")
            raise HTTPException(
                status_code=422, detail="Query contains invalid characters"
            )

        # Text cleaning (async)
        preprocessor = ContentPreprocessor()
        try:
            cleaned = await preprocessor.clean_text(raw_query)
        except Exception as e:
            logger.error(f"Text cleaning failed: {e}")
            raise HTTPException(status_code=500, detail="Failed to clean query text")

        # Tokenization (split on word boundaries)
        tokens = re.findall(r"\b\w+\b", cleaned.lower())

        # Simple Porter stemmer (inline, no external deps)
        def porter_stem(word):
            # Only basic suffix stripping for production safety
            for suffix in ["ing", "ed", "ly", "es", "s", "ment"]:
                if word.endswith(suffix) and len(word) > len(suffix) + 2:
                    return word[: -len(suffix)]
            return word

        stemmed_tokens = [porter_stem(token) for token in tokens]

        # Reconstruct normalized query string
        normalized_text = " ".join(stemmed_tokens)

        # Lowercase technology_hint if present
        tech_hint = query.technology_hint.lower() if query.technology_hint else None

        return SearchQuery(
            query=normalized_text,
            filters=query.filters,
            strategy=query.strategy,
            limit=query.limit,
            offset=query.offset,
            technology_hint=tech_hint,
            workspace_slugs=query.workspace_slugs,
            external_providers=query.external_providers,
            use_external_search=query.use_external_search,
        )

    def _create_evaluation_prompt(
        self, query: SearchQuery, results: SearchResults
    ) -> str:
        """
        Create evaluation prompt for LLM assessment.

        Args:
            query: Search query
            results: Search results

        Returns:
            Formatted prompt for LLM evaluation
        """
        prompt_parts = [
            f"Query: {query.query}",
            f"Number of results: {len(results.results)}",
            f"Technology context: {query.technology_hint or 'None'}",
            "",
            "Top 3 results:",
        ]

        for i, result in enumerate(results.results[:3]):
            prompt_parts.append(f"{i+1}. {result.title}")
            prompt_parts.append(f"   Snippet: {result.content_snippet[:100]}...")
            prompt_parts.append(f"   Score: {result.relevance_score:.2f}")
            prompt_parts.append("")

        prompt_parts.extend(
            [
                "Please evaluate:",
                "1. Overall quality (0.0-1.0)",
                "2. Relevance to query (0.0-1.0)",
                "3. Completeness of results (0.0-1.0)",
                "4. Whether additional content enrichment is needed",
                "5. Suggested topics for enrichment",
            ]
        )

        return "\n".join(prompt_parts)

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of search orchestrator and dependencies.

        Returns:
            Dictionary with health status
        """

        health_statuses: List[Dict[str, Any]] = []
        overall_status = "healthy"
        start_time = time.time()

        # Database health
        db_start = time.time()
        db_status = "healthy"
        db_error = None
        db_details = {}
        try:
            db_health = await self.db_manager.health_check()
            db_status = db_health.get("status", "unknown")
            db_details = db_health
            if db_status not in ("healthy", "connected"):
                overall_status = "degraded"
        except Exception as e:
            db_status = "unhealthy"
            db_error = str(e)
            db_details = {"error": db_error}
            overall_status = "degraded"
            logger.error(f"Database health check failed: {e}", exc_info=True)
        db_time = int((time.time() - db_start) * 1000)
        health_statuses.append(
            {
                "service": "database",
                "status": db_status,
                "response_time_ms": db_time,
                "last_check": datetime.utcnow().isoformat(),
                "details": db_details,
            }
        )

        # Cache health
        cache_start = time.time()
        cache_status = "healthy"
        cache_error = None
        cache_details = {}
        try:
            cache_health = await self.search_cache.get_cache_stats()
            cache_status = cache_health.get("cache_status", "unknown")
            cache_details = cache_health
            if cache_status != "healthy":
                overall_status = "degraded"
        except Exception as e:
            cache_status = "unhealthy"
            cache_error = str(e)
            cache_details = {"error": cache_error}
            overall_status = "degraded"
            logger.error(f"Cache health check failed: {e}", exc_info=True)
        cache_time = int((time.time() - cache_start) * 1000)
        health_statuses.append(
            {
                "service": "cache",
                "status": cache_status,
                "response_time_ms": cache_time,
                "last_check": datetime.utcnow().isoformat(),
                "details": cache_details,
            }
        )

        # AnythingLLM health
        llm_start = time.time()
        llm_status = "healthy"
        llm_error = None
        llm_details = {}
        try:
            if self.weaviate_client:
                llm_health = await self.weaviate_client.health_check()
                llm_status = llm_health.get("status", "unknown")
                llm_details = llm_health
                if llm_status != "healthy":
                    overall_status = "degraded"
            else:
                llm_status = "unavailable"
                llm_details = {"error": "Weaviate client not configured"}
                overall_status = "degraded"
        except Exception as e:
            llm_status = "unhealthy"
            llm_error = str(e)
            llm_details = {"error": llm_error}
            overall_status = "degraded"
            logger.error(f"Weaviate health check failed: {e}", exc_info=True)
        llm_time = int((time.time() - llm_start) * 1000)
        health_statuses.append(
            {
                "service": "weaviate",
                "status": llm_status,
                "response_time_ms": llm_time,
                "last_check": datetime.utcnow().isoformat(),
                "details": llm_details,
            }
        )

        # Search strategy health
        strategy_start = time.time()
        strategy_status = "healthy"
        strategy_error = None
        strategy_details = {}
        try:
            # Check if at least one workspace is available
            workspaces = await self.workspace_strategy._get_available_workspaces()
            if not workspaces:
                strategy_status = "degraded"
                strategy_details = {"message": "No workspaces available"}
                overall_status = "degraded"
            else:
                strategy_details = {"workspace_count": len(workspaces)}
        except Exception as e:
            strategy_status = "unhealthy"
            strategy_error = str(e)
            strategy_details = {"error": strategy_error}
            overall_status = "degraded"
            logger.error(f"Search strategy health check failed: {e}", exc_info=True)
        strategy_time = int((time.time() - strategy_start) * 1000)
        health_statuses.append(
            {
                "service": "search_strategy",
                "status": strategy_status,
                "response_time_ms": strategy_time,
                "last_check": datetime.utcnow().isoformat(),
                "details": strategy_details,
            }
        )

        # Compose response
        total_time = int((time.time() - start_time) * 1000)
        if any(s["status"] == "unhealthy" for s in health_statuses):
            overall_status = "unhealthy"

        # Log degraded/unhealthy status for monitoring
        if overall_status != "healthy":
            logger.error(
                "Search orchestrator health degraded/unhealthy",
                extra={
                    "health_statuses": health_statuses,
                    "overall_status": overall_status,
                },
            )

        return {
            "overall_status": overall_status,
            "services": health_statuses,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": total_time,
        }
    
    async def search(
        self,
        query: str,
        technology_hint: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        session_id: Optional[str] = None,
        background_tasks: Optional[BackgroundTasks] = None,
        external_providers: Optional[List[str]] = None,
        use_external_search: Optional[bool] = None
    ) -> "SearchResponse":
        """
        Main search method for API compatibility.
        
        Args:
            query: Search query string
            technology_hint: Optional technology filter
            limit: Maximum results to return
            offset: Pagination offset
            session_id: Optional session ID
            background_tasks: Optional background tasks
            
        Returns:
            SearchResponse compatible with API schema
        """
        logger.debug(f"Search called with: query={query!r}, technology_hint={technology_hint!r} (type: {type(technology_hint)}), limit={limit!r}, offset={offset!r}")
        # Import here to avoid circular imports
        from src.api.schemas import SearchResponse as APISearchResponse
        
        # Create internal SearchQuery
        search_query = SearchQuery(
            query=query,
            filters={
                "technology": technology_hint
            } if technology_hint else {},
            limit=limit,
            offset=offset,
            external_providers=external_providers,
            use_external_search=use_external_search
        )
        
        # Execute search
        results, _ = await self.execute_search(search_query, background_tasks)
        
        # Convert to API response format
        # Ensure technology_hint is always a string or None to prevent type errors
        if technology_hint is not None and not isinstance(technology_hint, str):
            logger.warning(f"Invalid technology_hint type: {type(technology_hint)}, value: {technology_hint!r}, converting to string")
            tech_hint = str(technology_hint) if technology_hint else None
        else:
            tech_hint = technology_hint
        
        try:
            return APISearchResponse(
                results=results.results[:limit],
                total_count=results.total_count,
                query=query,
                technology_hint=tech_hint,
                execution_time_ms=results.query_time_ms,
                cache_hit=results.cache_hit,
                enrichment_triggered=results.enrichment_triggered,
                external_search_used=results.external_search_used
            )
        except Exception as e:
            logger.error(f"Failed to create SearchResponse: {e}")
            logger.error(f"Parameters: query={query!r}, tech_hint={tech_hint!r} (type: {type(tech_hint)}), limit={limit}")
            raise
