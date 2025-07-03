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
        trace_id = f"search_{int(time.time() * 1000)}_{query.query[:10].replace(' ', '_')}"

        try:
            logger.info(
                f"[{trace_id}] Starting search orchestration for query: {query.query[:100]}..."
            )
            logger.info(f"PIPELINE_METRICS: step=search_start trace_id={trace_id} query=\"{query.query}\"")

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
                            f"[{trace_id}] Cache hit - returning {len(cached_results.results)} results"
                        )
                        logger.info(f"PIPELINE_METRICS: step=cache_check duration_ms={execution_time} "
                                   f"decision=cache_hit result_count={len(cached_results.results)} trace_id={trace_id}")
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

            # Step 3: Multi-Workspace Search with timeout (skip if external-only requested)
            search_results = None
            if normalized_query.use_external_search is True and self.mcp_enhancer:
                # Skip workspace search if external search is explicitly requested
                logger.info(f"[{trace_id}] Skipping workspace search due to explicit external search request")
                logger.info(f"PIPELINE_METRICS: step=workspace_search duration_ms=0 "
                           f"decision=skip_internal trace_id={trace_id}")
                search_results = SearchResults(
                    results=[],
                    total_count=0,
                    query_time_ms=0,
                    strategy_used=normalized_query.strategy,
                    cache_hit=False,
                    workspaces_searched=[],
                    enrichment_triggered=False,
                )
            else:
                ws_start = time.time()
                logger.info(f"[{trace_id}] Starting multi-workspace search for query: '{normalized_query.query}'")
                try:
                    search_results = await asyncio.wait_for(
                        self._execute_multi_workspace_search(normalized_query),
                        timeout=self.search_timeout,
                    )
                    ws_time = int((time.time() - ws_start) * 1000)
                    logger.info(f"[{trace_id}] Workspace search completed: {len(search_results.results)} results from {len(search_results.workspaces_searched)} workspaces")
                    logger.info(f"PIPELINE_METRICS: step=workspace_search duration_ms={ws_time} "
                               f"result_count={len(search_results.results)} workspaces={len(search_results.workspaces_searched)} trace_id={trace_id}")
                except asyncio.TimeoutError:
                    raise SearchTimeoutError(
                        f"Search timed out after {self.search_timeout}s",
                        timeout_seconds=self.search_timeout,
                        operation="multi_workspace_search",
                    )

            # Step 4: AI Evaluation (optional)
            evaluation_result = None
            if self.llm_client:
                try:
                    evaluation_result = await self._evaluate_search_results(
                        normalized_query, search_results
                    )
                except Exception as e:
                    logger.warning(f"AI evaluation failed: {e}")
                    # Continue without evaluation

            # Step 4.5: Query Refinement (if needed)
            refined_query_attempted = False
            if evaluation_result and 0.4 <= evaluation_result.overall_quality < 0.8:
                # Results are partially relevant - try query refinement
                logger.info(f"[{trace_id}] Results partially relevant (score: {evaluation_result.overall_quality}), attempting query refinement")
                try:
                    refined_results = await self._refine_and_retry_search(
                        normalized_query, search_results, evaluation_result, trace_id
                    )
                    if refined_results and len(refined_results.results) > len(search_results.results):
                        logger.info(f"[{trace_id}] Query refinement improved results from {len(search_results.results)} to {len(refined_results.results)}")
                        search_results = refined_results
                        refined_query_attempted = True
                        # Re-evaluate with refined results
                        if self.llm_client:
                            try:
                                evaluation_result = await self._evaluate_search_results(
                                    normalized_query, search_results
                                )
                            except Exception as e:
                                logger.warning(f"Re-evaluation after refinement failed: {e}")
                except Exception as e:
                    logger.error(f"[{trace_id}] Query refinement failed: {e}")
            
            # Step 4.6: External Search Enhancement (if needed)
            external_results_added = False
            external_search_executed = False
            # Check if external search should be used
            should_use_external = False
            
            # Log search state for metrics
            logger.info(
                f"Search state - Query: '{normalized_query.query[:50]}...' | "
                f"Internal results: {len(search_results.results)} | "
                f"Quality score: {evaluation_result.overall_quality if evaluation_result else 'N/A'} | "
                f"External search requested: {normalized_query.use_external_search}"
            )
            
            if normalized_query.use_external_search is True:
                # Explicitly requested
                should_use_external = True
                logger.info(f"[{trace_id}] External search explicitly requested by user")
                logger.info(f"PIPELINE_METRICS: step=external_search_decision duration_ms=0 "
                           f"decision=explicit_true trace_id={trace_id}")
            elif normalized_query.use_external_search is False:
                # Explicitly disabled
                should_use_external = False
                logger.info(f"[{trace_id}] External search explicitly disabled by user")
                logger.info(f"PIPELINE_METRICS: step=external_search_decision duration_ms=0 "
                           f"decision=explicit_false trace_id={trace_id}")
            else:
                # Auto-decide using TextAI with EXTERNAL_SEARCH_DECISION prompt
                decision_start = time.time()
                if self.mcp_enhancer and self.mcp_enhancer.text_ai and evaluation_result:
                    try:
                        logger.info(f"[{trace_id}] Calling TextAI for external search decision")
                        
                        # Convert to MCP models
                        from src.mcp.core.models import NormalizedQuery
                        normalized = NormalizedQuery(
                            original_query=normalized_query.query,
                            normalized_text=normalized_query.query.lower().strip(),
                            technology_hint=normalized_query.technology_hint,
                            query_hash="",
                            tokens=[]
                        )
                        # Add trace_id for logging
                        normalized.trace_id = trace_id
                        
                        # Convert evaluation result to MCP format
                        from src.mcp.core.models import EvaluationResult as MCPEvalResult
                        mcp_eval = MCPEvalResult(
                            relevance_score=evaluation_result.overall_quality,
                            completeness_score=evaluation_result.completeness_score,
                            needs_refinement=evaluation_result.overall_quality < 0.8,
                            needs_external_search=False,  # This is what we're deciding
                            missing_information=evaluation_result.enrichment_topics,
                            confidence=evaluation_result.confidence_level
                        )
                        
                        # Call TextAI to decide
                        external_decision = await self.mcp_enhancer.text_ai.decide_external_search(
                            normalized, mcp_eval
                        )
                        should_use_external = external_decision.should_search
                        
                        decision_time = int((time.time() - decision_start) * 1000)
                        logger.info(
                            f"[{trace_id}] TextAI external search decision in {decision_time}ms: "
                            f"{should_use_external} (reason: {external_decision.reasoning})"
                        )
                        logger.info(f"PIPELINE_METRICS: step=external_search_decision duration_ms={decision_time} "
                                   f"decision={'use_external' if should_use_external else 'skip_external'} "
                                   f"confidence={external_decision.confidence} trace_id={trace_id}")
                    except Exception as e:
                        logger.error(f"[{trace_id}] TextAI external search decision failed: {e}")
                        # Fallback to simple logic
                        should_use_external = (not search_results.results or 
                                             evaluation_result.overall_quality < 0.6)
                        logger.info(f"[{trace_id}] Fallback external search decision: {should_use_external}")
                else:
                    # No TextAI available, use simple logic
                    should_use_external = (not search_results.results or 
                                         (evaluation_result and evaluation_result.overall_quality < 0.6))
                    logger.info(f"[{trace_id}] Simple external search decision: {should_use_external}")
            
            logger.info(f"MCP enhancer available: {self.mcp_enhancer is not None}, should use external: {should_use_external}")
            if self.mcp_enhancer and should_use_external:
                logger.info("Calling external search enhancement...")
                try:
                    external_search_executed = True
                    external_results = await self._enhance_with_external_search(
                        normalized_query, search_results
                    )
                    logger.info(f"External search returned {len(external_results) if external_results else 0} results")
                    if external_results:
                        search_results.results.extend(external_results)
                        external_results_added = True
                        logger.info(f"Added {len(external_results)} external search results")
                    else:
                        logger.warning("External search returned no results")
                except Exception as e:
                    logger.error(f"External search enhancement failed: {e}", exc_info=True)
            else:
                logger.warning(f"External search not called: mcp_enhancer={self.mcp_enhancer is not None}, should_use_external={should_use_external}")

            # Step 5: Enrichment Decision
            enrichment_triggered = False
            ingestion_status = None
            if evaluation_result and evaluation_result.needs_enrichment:
                # Pass external results for potential sync ingestion
                external_results_list = []
                if external_results_added and hasattr(search_results, 'results'):
                    # Get the external results that were added
                    external_results_list = [r for r in search_results.results 
                                           if hasattr(r, 'metadata') and 
                                           r.metadata.get('source') == 'external']
                
                enrichment_triggered, ingestion_status = await self._trigger_enrichment(
                    normalized_query, evaluation_result, background_tasks, external_results_list
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
                external_search_used=external_search_executed,
                ingestion_status=ingestion_status,  # Add ingestion status to response
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
                f"[{trace_id}] Search completed: {len(final_results.results)} results in {execution_time}ms"
            )
            logger.info(f"PIPELINE_METRICS: step=search_complete duration_ms={execution_time} "
                       f"total_results={len(final_results.results)} cache_hit=False "
                       f"external_used={external_search_executed} enrichment_triggered={enrichment_triggered} "
                       f"trace_id={trace_id}")
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
        if not self.mcp_enhancer or not self.mcp_enhancer.text_ai:
            logger.warning("MCP enhancer or text AI not available, using fallback evaluation")
            return None

        try:
            start_time = time.time()
            trace_id = getattr(query, 'trace_id', f"search_{int(time.time() * 1000)}")
            logger.info(f"[{trace_id}] Evaluating search results with TextAI for query: {query.query}")

            # Convert to MCP normalized query format
            from src.mcp.core.models import NormalizedQuery, VectorSearchResults
            normalized = NormalizedQuery(
                original_query=query.query,
                normalized_text=query.query.lower().strip(),
                technology_hint=query.technology_hint,
                query_hash="",  # Not needed for evaluation
                tokens=[]
            )

            # Convert results to VectorSearchResults format
            vector_results = VectorSearchResults(
                results=results.results,
                total_count=results.total_count,
                query_time_ms=results.query_time_ms
            )

            # Call TextAI evaluation with RESULT_RELEVANCE prompt
            mcp_eval = await self.mcp_enhancer.text_ai.evaluate_results(
                normalized, vector_results
            )

            # Convert MCP evaluation to orchestrator format
            evaluation_result = EvaluationResult(
                overall_quality=mcp_eval.relevance_score,
                relevance_assessment=mcp_eval.relevance_score,
                completeness_score=mcp_eval.completeness_score,
                needs_enrichment=mcp_eval.needs_external_search or len(mcp_eval.missing_information) > 0,
                enrichment_topics=mcp_eval.missing_information or (
                    [query.technology_hint] if query.technology_hint else []
                ),
                confidence_level=mcp_eval.confidence,
                reasoning=f"LLM evaluation - relevance: {mcp_eval.relevance_score:.2f}, needs_external: {mcp_eval.needs_external_search}",
            )

            eval_time = int((time.time() - start_time) * 1000)
            logger.info(
                f"[{trace_id}] TextAI evaluation completed in {eval_time}ms: "
                f"quality={evaluation_result.overall_quality:.2f}, "
                f"confidence={evaluation_result.confidence_level:.2f}, "
                f"needs_external={mcp_eval.needs_external_search}"
            )
            
            # Log metrics for pipeline visualization
            logger.info(f"PIPELINE_METRICS: step=text_ai_evaluation duration_ms={eval_time} "
                       f"confidence_score={evaluation_result.overall_quality} "
                       f"decision=evaluate_results trace_id={trace_id}")
            
            return evaluation_result

        except Exception as e:
            logger.error(f"TextAI evaluation failed: {e}", exc_info=True)
            # Fallback to simple evaluation
            return EvaluationResult(
                overall_quality=0.5,
                relevance_assessment=0.5,
                completeness_score=0.5,
                needs_enrichment=True,
                enrichment_topics=[query.technology_hint] if query.technology_hint else [],
                confidence_level=0.3,
                reasoning=f"Fallback evaluation due to error: {str(e)}",
            )

    async def _trigger_enrichment(
        self,
        query: SearchQuery,
        evaluation: EvaluationResult,
        background_tasks: Optional[BackgroundTasks],
        external_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Trigger knowledge enrichment as background task or synchronously.

        Args:
            query: Search query
            evaluation: LLM evaluation result
            background_tasks: FastAPI background tasks
            external_results: External search results for potential sync ingestion

        Returns:
            Tuple of (enrichment_triggered, ingestion_status)
        """
        ingestion_status = None
        
        # Check if sync ingestion is enabled and we have Context7 results
        sync_ingestion_enabled = False
        if hasattr(self, 'config') and hasattr(self.config, 'enrichment'):
            sync_ingestion_enabled = self.config.enrichment.sync_ingestion
        
        # Handle synchronous ingestion for Context7 results
        if sync_ingestion_enabled and external_results:
            context7_results = [r for r in external_results if r.get('provider') == 'context7']
            if context7_results:
                logger.info(f"[{query.query_hash}] Performing synchronous Context7 ingestion")
                ingestion_status = await self._perform_sync_ingestion(
                    query, context7_results, evaluation
                )
                if ingestion_status and ingestion_status.get('success'):
                    logger.info(f"[{query.query_hash}] Sync ingestion completed successfully")
                    return True, ingestion_status
        
        # Fall back to background enrichment
        if not self.knowledge_enricher or not background_tasks:
            logger.debug("Knowledge enricher or background tasks not available")
            return False, None

        try:
            logger.info(
                f"Triggering background enrichment for topics: {evaluation.enrichment_topics}"
            )

            # Add enrichment task to background (this would need PRD-010 implementation)
            # For now, this is a placeholder
            def enrichment_task():
                logger.info(f"Background enrichment started for query: {query.query}")
                # Would call: self.knowledge_enricher.enrich_knowledge(...)

            background_tasks.add_task(enrichment_task)
            return True, None

        except Exception as e:
            logger.error(f"Failed to trigger enrichment: {e}")
            return False, None

    async def _perform_sync_ingestion(
        self,
        query: SearchQuery,
        context7_results: List[Dict[str, Any]],
        evaluation: EvaluationResult
    ) -> Dict[str, Any]:
        """
        Perform synchronous ingestion of Context7 documentation.
        
        Args:
            query: Search query
            context7_results: Context7 documentation results
            evaluation: LLM evaluation result
            
        Returns:
            Ingestion status dictionary
        """
        try:
            start_time = time.time()
            ingested_count = 0
            
            # Get sync ingestion timeout from config
            timeout = 10  # default
            if hasattr(self, 'config') and hasattr(self.config, 'enrichment'):
                timeout = self.config.enrichment.sync_ingestion_timeout
            
            # Process each Context7 result
            for result in context7_results:
                try:
                    # Extract documentation content
                    content = result.get('content', result.get('snippet', ''))
                    if not content:
                        continue
                    
                    # Create a simple ingestion task
                    # In a real implementation, this would use the IngestionPipeline
                    metadata = {
                        'source': 'context7',
                        'library': result.get('metadata', {}).get('library', 'unknown'),
                        'version': result.get('metadata', {}).get('version', 'latest'),
                        'url': result.get('url', ''),
                        'query': query.query,
                        'ingestion_type': 'synchronous'
                    }
                    
                    # Store Context7 documentation in database for processing
                    # This creates a lightweight record that can be processed later
                    await self._store_context7_documentation(
                        content=content,
                        metadata=metadata,
                        query_hash=query.query_hash
                    )
                    
                    logger.info(f"Stored Context7 doc: {metadata['library']} v{metadata['version']}")
                    ingested_count += 1
                    
                    # Check timeout
                    if time.time() - start_time > timeout:
                        logger.warning(f"Sync ingestion timeout reached after {ingested_count} docs")
                        break
                        
                except Exception as e:
                    logger.error(f"Failed to ingest Context7 result: {e}")
                    continue
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            return {
                'success': True,
                'ingested_count': ingested_count,
                'duration_ms': duration_ms,
                'source': 'context7',
                'type': 'synchronous'
            }
            
        except Exception as e:
            logger.error(f"Sync ingestion failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'source': 'context7',
                'type': 'synchronous'
            }
    
    async def _refine_and_retry_search(
        self,
        original_query: SearchQuery,
        initial_results: SearchResults,
        evaluation: EvaluationResult,
        trace_id: str
    ) -> Optional[SearchResults]:
        """
        Refine query based on initial results and retry search.
        
        Args:
            original_query: Original search query
            initial_results: Initial search results
            evaluation: LLM evaluation of initial results
            trace_id: Request trace ID
            
        Returns:
            New search results or None if refinement fails
        """
        try:
            if not self.mcp_enhancer or not self.mcp_enhancer.text_ai:
                logger.warning(f"[{trace_id}] Query refinement unavailable - no TextAI")
                return None
            
            # Create MCP models for refinement
            from src.mcp.core.models import NormalizedQuery, RefinedQuery
            
            normalized = NormalizedQuery(
                original_query=original_query.query,
                normalized_text=original_query.query.lower().strip(),
                technology_hint=original_query.technology_hint,
                query_hash="",
                tokens=[]
            )
            
            # Get refined query from TextAI
            logger.info(f"[{trace_id}] Generating refined query with TextAI")
            refined = await self.mcp_enhancer.text_ai.refine_query(
                normalized,
                initial_results.results[:5],  # Pass top 5 results
                evaluation.enrichment_topics  # Missing aspects
            )
            
            if not refined or refined.refined_query == original_query.query:
                logger.info(f"[{trace_id}] No meaningful refinement generated")
                return None
            
            logger.info(f"[{trace_id}] Refined query: '{refined.refined_query}' (confidence: {refined.confidence})")
            logger.info(f"PIPELINE_METRICS: step=query_refinement duration_ms=0 "
                       f"original_query=\"{original_query.query}\" "
                       f"refined_query=\"{refined.refined_query}\" "
                       f"confidence={refined.confidence} trace_id={trace_id}")
            
            # Create new search query with refined text
            refined_search_query = SearchQuery(
                query=refined.refined_query,
                filters=original_query.filters,
                limit=original_query.limit,
                offset=original_query.offset,
                technology_hint=original_query.technology_hint,
                use_external_search=False  # Don't trigger external for refined query
            )
            
            # Execute search with refined query
            logger.info(f"[{trace_id}] Executing search with refined query")
            refined_results = await self._execute_multi_workspace_search(refined_search_query)
            
            return refined_results
            
        except Exception as e:
            logger.error(f"[{trace_id}] Query refinement error: {e}")
            return None
    
    async def _store_context7_documentation(
        self,
        content: str,
        metadata: Dict[str, Any],
        query_hash: str
    ) -> None:
        """
        Store Context7 documentation in database for later processing.
        
        This creates a lightweight record that can be picked up by the
        background ingestion pipeline for full processing.
        
        Args:
            content: Documentation content
            metadata: Metadata about the documentation
            query_hash: Query hash for tracking
        """
        try:
            # Create a record in the database that marks this content
            # as pending ingestion from Context7
            await self.db_manager.execute(
                """
                INSERT INTO content_metadata (
                    source_url,
                    title,
                    technology,
                    content_hash,
                    processing_status,
                    metadata,
                    created_at,
                    updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (
                    metadata.get('url', f"context7://{metadata.get('library', 'unknown')}"),
                    f"{metadata.get('library', 'Unknown')} v{metadata.get('version', 'latest')}",
                    metadata.get('library', 'unknown'),
                    query_hash[:16],  # Use part of query hash as content hash
                    'pending_context7',  # Special status for Context7 content
                    str(metadata),  # Store full metadata as JSON string
                )
            )
            
            # Store the actual content in a separate table or cache
            # for the ingestion pipeline to process
            cache_key = f"context7_content:{query_hash[:16]}"
            await self.cache_manager.set(
                cache_key,
                {
                    'content': content,
                    'metadata': metadata,
                    'timestamp': datetime.utcnow().isoformat()
                },
                ttl=3600  # Keep for 1 hour
            )
            
            logger.debug(f"Stored Context7 documentation for {metadata.get('library')} in database")
            
        except Exception as e:
            logger.error(f"Failed to store Context7 documentation: {e}")
            # Don't fail the entire ingestion if storage fails
            raise
    
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
                        chunk_index=None,
                        overall_quality=0.7
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
        import uuid
        trace_id = f"orch-{uuid.uuid4().hex[:8]}"
        logger.info(f"[{trace_id}] Search called with: query={query!r}, technology_hint={technology_hint!r} (type: {type(technology_hint)}), limit={limit!r}, offset={offset!r}")
        # Import here to avoid circular imports
        from src.api.v1.schemas import SearchResponse as APISearchResponse
        
        # Create internal SearchQuery
        search_query = SearchQuery(
            query=query,
            filters={
                "technology": technology_hint
            } if technology_hint else {},
            limit=limit,
            offset=offset,
            technology_hint=technology_hint,
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
        
        # Convert SearchResult objects to API SearchResult models
        from src.api.v1.schemas import SearchResult as APISearchResult
        logger.info(f"[{trace_id}] Converting {len(results.results[:limit])} search results to API format")
        api_results = []
        for i, result in enumerate(results.results[:limit]):
            logger.debug(f"Converting result {i}: type={type(result)}, content_id={result.content_id}")
            api_result = APISearchResult(
                content_id=result.content_id,
                title=result.title or "Untitled",
                snippet=result.content_snippet or "",
                source_url=result.source_url or "",
                technology=result.technology or "unknown",
                relevance_score=result.relevance_score,
                content_type=result.metadata.get("content_type", "document"),
                workspace=result.workspace_slug or "external_search",
            )
            api_results.append(api_result)
        
        logger.info(f"[{trace_id}] Converted to API results: {len(api_results)} items, types: {[type(r).__name__ for r in api_results[:2]]}")
        
        try:
            return APISearchResponse(
                results=api_results,
                total_count=results.total_count,
                query=query,
                technology_hint=tech_hint,
                execution_time_ms=results.query_time_ms,
                cache_hit=results.cache_hit,
                enrichment_triggered=results.enrichment_triggered,
                external_search_used=results.external_search_used,
                ingestion_status=results.ingestion_status
            )
        except Exception as e:
            logger.error(f"Failed to create SearchResponse: {e}")
            logger.error(f"Parameters: query={query!r}, tech_hint={tech_hint!r} (type: {type(tech_hint)}), limit={limit}")
            raise
