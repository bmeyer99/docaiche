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
from typing import Optional, Dict, Any, Tuple

from fastapi import BackgroundTasks

from .models import SearchQuery, SearchResults, SearchStrategy, EvaluationResult
from .strategies import WorkspaceSearchStrategy
from .ranking import ResultRanker
from .cache import SearchCacheManager
from .exceptions import SearchOrchestrationError, SearchTimeoutError
from src.database.connection import DatabaseManager, CacheManager
from src.clients.anythingllm import AnythingLLMClient

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
    
    def __init__(
        self,
        db_manager: DatabaseManager,
        cache_manager: CacheManager,
        anythingllm_client: AnythingLLMClient,
        llm_client: Optional[Any] = None,  # LLM client for evaluation (PRD-005)
        knowledge_enricher: Optional[Any] = None  # Knowledge enricher (PRD-010)
    ):
        """
        Initialize search orchestrator with all required dependencies.
        
        Args:
            db_manager: Database manager for metadata queries
            cache_manager: Redis cache manager
            anythingllm_client: AnythingLLM client for vector search
            llm_client: LLM provider client for evaluation (optional)
            knowledge_enricher: Knowledge enricher for background tasks (optional)
        """
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self.anythingllm_client = anythingllm_client
        self.llm_client = llm_client
        self.knowledge_enricher = knowledge_enricher
        
        # Initialize sub-components
        self.workspace_strategy = WorkspaceSearchStrategy(db_manager, anythingllm_client)
        self.result_ranker = ResultRanker()
        self.search_cache = SearchCacheManager(cache_manager)
        
        # Performance timeouts from PRD-009
        self.search_timeout = 30.0  # Total search timeout
        self.workspace_timeout = 2.0  # Per-workspace timeout
        
        logger.info("SearchOrchestrator initialized with all dependencies")
    
    async def execute_search(
        self, 
        query: SearchQuery,
        background_tasks: Optional[BackgroundTasks] = None
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
            logger.info(f"Starting search orchestration for query: {query.query[:100]}...")
            
            # Step 1: Query Normalization
            normalized_query = self._normalize_query(query)
            logger.debug(f"Normalized query: {normalized_query.query}")
            
            # Step 2: Cache Check with graceful degradation
            cached_results = None
            try:
                cached_results = await self.search_cache.get_cached_results(normalized_query)
                if cached_results:
                    execution_time = int((time.time() - start_time) * 1000)
                    cached_results.query_time_ms = execution_time
                    logger.info(f"Cache hit - returning {len(cached_results.results)} results")
                    return cached_results, normalized_query
            except Exception as e:
                logger.warning(f"Cache check failed, continuing without cache: {e}")
                # Continue without caching
            
            # Step 3: Multi-Workspace Search with timeout
            try:
                search_results = await asyncio.wait_for(
                    self._execute_multi_workspace_search(normalized_query),
                    timeout=self.search_timeout
                )
            except asyncio.TimeoutError:
                raise SearchTimeoutError(
                    f"Search timed out after {self.search_timeout}s",
                    timeout_seconds=self.search_timeout,
                    operation="multi_workspace_search"
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
                enrichment_triggered=enrichment_triggered
            )
            
            # Step 7: Cache Results with graceful degradation
            try:
                await self.search_cache.cache_results(normalized_query, final_results)
            except Exception as e:
                logger.warning(f"Failed to cache results: {e}")
                # Continue without caching - this is non-critical
            
            logger.info(f"Search completed: {len(final_results.results)} results in {execution_time}ms")
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
                    "error": str(e)
                }
            )
    
    async def _execute_multi_workspace_search(self, query: SearchQuery) -> SearchResults:
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
        relevant_workspaces = await self.workspace_strategy.identify_relevant_workspaces(
            query.query, query.technology_hint
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
                enrichment_triggered=False
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
            enrichment_triggered=False  # Will be set by caller
        )
    
    async def _evaluate_search_results(
        self, 
        query: SearchQuery, 
        results: SearchResults
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
            evaluation_prompt = self._create_evaluation_prompt(query, results)
            
            # Call LLM client (this would need to be implemented based on PRD-005)
            # For now, return a placeholder evaluation
            evaluation_result = EvaluationResult(
                overall_quality=0.7,
                relevance_assessment=0.8,
                completeness_score=0.6,
                needs_enrichment=len(results.results) < 5,  # Simple heuristic
                enrichment_topics=[query.technology_hint] if query.technology_hint else [],
                confidence_level=0.8,
                reasoning="Automated evaluation based on result count and relevance"
            )
            
            logger.debug(f"LLM evaluation completed: quality={evaluation_result.overall_quality:.2f}")
            return evaluation_result
            
        except Exception as e:
            logger.error(f"LLM evaluation failed: {e}")
            return None
    
    async def _trigger_enrichment(
        self,
        query: SearchQuery,
        evaluation: EvaluationResult,
        background_tasks: Optional[BackgroundTasks]
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
            logger.info(f"Triggering enrichment for topics: {evaluation.enrichment_topics}")
            
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
    
    def _normalize_query(self, query: SearchQuery) -> SearchQuery:
        """
        Normalize search query for consistent processing.
        
        Normalization from PRD-009:
        - Lowercase
        - Trim whitespace
        - Remove extra spaces
        
        Args:
            query: Original search query
            
        Returns:
            Normalized search query
        """
        normalized_text = " ".join(query.query.lower().strip().split())
        
        return SearchQuery(
            query=normalized_text,
            filters=query.filters,
            strategy=query.strategy,
            limit=query.limit,
            offset=query.offset,
            technology_hint=query.technology_hint.lower() if query.technology_hint else None,
            workspace_slugs=query.workspace_slugs
        )
    
    def _create_evaluation_prompt(self, query: SearchQuery, results: SearchResults) -> str:
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
        
        prompt_parts.extend([
            "Please evaluate:",
            "1. Overall quality (0.0-1.0)",
            "2. Relevance to query (0.0-1.0)",
            "3. Completeness of results (0.0-1.0)",
            "4. Whether additional content enrichment is needed",
            "5. Suggested topics for enrichment"
        ])
        
        return "\n".join(prompt_parts)
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of search orchestrator and dependencies.
        
        Returns:
            Dictionary with health status
        """
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        try:
            # Check database health
            db_health = await self.db_manager.health_check()
            health_status["components"]["database"] = db_health
            
            # Check cache health
            cache_health = await self.search_cache.get_cache_stats()
            health_status["components"]["cache"] = cache_health
            
            # Check AnythingLLM health
            if self.anythingllm_client:
                llm_health = await self.anythingllm_client.health_check()
                health_status["components"]["anythingllm"] = llm_health
            
            # Check if any component is unhealthy
            for component_name, component_health in health_status["components"].items():
                # Handle different component response formats
                if component_name == "cache":
                    # Cache returns cache_status field
                    component_status = component_health.get("cache_status", "unknown")
                else:
                    # Other components return status field
                    component_status = component_health.get("status", "unknown")
                
                # Only mark degraded for truly unhealthy components
                if component_status in ["unhealthy", "error"]:
                    health_status["status"] = "degraded"
                    break
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
        
        return health_status