"""
Search Orchestrator Abstract Base Class
=======================================

Core orchestration interface for the MCP search workflow implementing
all phases from PLAN.md with configurable behavior.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import hashlib
import logging

from .configuration import SearchConfiguration
from .models import (
    NormalizedQuery,
    SearchRequest,
    VectorSearchResults,
    EvaluationResult,
    SearchResponse,
    UserContext
)

logger = logging.getLogger(__name__)


class SearchOrchestrator(ABC):
    """
    Abstract base class for MCP search orchestration.
    
    Implements the complete MCP workflow with methods for each phase:
    1. Query normalization and hashing
    2. Cache checking with circuit breaker
    3. AI-driven workspace selection
    4. Parallel vector search execution
    5. AI result evaluation
    6. Query refinement when needed
    7. External search fallback
    8. Content extraction from sources
    9. Knowledge ingestion for learning
    10. Response formatting
    11. Result caching
    """
    
    def __init__(self, config: SearchConfiguration):
        """
        Initialize orchestrator with configuration.
        
        Args:
            config: Search configuration with all parameters
        """
        self.config = config
        self._query_cache = {}
        logger.info("SearchOrchestrator initialized with configuration")
    
    async def search(
        self,
        query: str,
        technology_hint: Optional[str] = None,
        response_type: str = "raw",
        user_context: Optional[UserContext] = None
    ) -> SearchResponse:
        """
        Main entry point for MCP search workflow.
        
        Executes the complete search pipeline with all decision points
        and optimizations as specified in PLAN.md.
        
        Args:
            query: Raw search query from user
            technology_hint: Optional technology context
            response_type: Response format - "raw" or "answer"
            user_context: User session and permission context
            
        Returns:
            SearchResponse with results and execution metadata
            
        Raises:
            MCPSearchError: Base exception for search failures
            QueueOverflowError: When queue is at capacity
            RateLimitExceededError: When rate limits exceeded
            SearchTimeoutError: When operation times out
        """
        logger.info(f"Starting MCP search: query='{query[:50]}...', tech={technology_hint}")
        
        # Step 1: Normalize query
        normalized_query = await self._normalize_query(query, technology_hint)
        
        # Step 2: Check cache
        cached_response = await self._check_cache(normalized_query)
        if cached_response:
            logger.info("Cache hit - returning cached results")
            return cached_response
        
        # Step 3: Select workspaces using AI
        selected_workspaces = await self._select_workspaces(normalized_query)
        
        # Step 4: Execute vector search in parallel
        vector_results = await self._execute_vector_search(
            normalized_query, 
            selected_workspaces
        )
        
        # Step 5: Evaluate results with AI
        evaluation = await self._evaluate_results(normalized_query, vector_results)
        
        # Step 6: Check if refinement needed
        if evaluation.needs_refinement and self.config.enable_query_refinement:
            refined_query = await self._refine_query(normalized_query, evaluation)
            # Re-execute search with refined query
            vector_results = await self._execute_vector_search(
                refined_query,
                selected_workspaces
            )
            # Re-evaluate refined results
            evaluation = await self._evaluate_results(refined_query, vector_results)
        
        # Step 7: Check if external search needed
        if evaluation.needs_external_search and self.config.enable_external_search:
            external_results = await self._execute_external_search(
                normalized_query,
                evaluation
            )
            # Merge external results
            vector_results = self._merge_results(vector_results, external_results)
        
        # Step 8: Extract content if needed
        if response_type == "answer":
            extracted_content = await self._extract_content(
                normalized_query,
                vector_results
            )
        else:
            extracted_content = None
        
        # Step 9: Trigger knowledge ingestion if gaps found
        if self.config.enable_knowledge_ingestion:
            await self._ingest_knowledge(normalized_query, evaluation)
        
        # Step 10: Format response
        response = await self._format_response(
            normalized_query,
            vector_results,
            evaluation,
            response_type,
            extracted_content
        )
        
        # Step 11: Update cache
        await self._update_cache(normalized_query, response)
        
        return response
    
    @abstractmethod
    async def _normalize_query(
        self, 
        query: str, 
        technology_hint: Optional[str]
    ) -> NormalizedQuery:
        """
        Normalize and hash query for consistent processing.
        
        Must implement:
        - Query cleaning and sanitization
        - Lowercasing and trimming
        - Consistent hashing for cache keys
        - Technology hint normalization
        
        Args:
            query: Raw query string
            technology_hint: Optional technology context
            
        Returns:
            NormalizedQuery with hash and cleaned text
        """
        pass
    
    @abstractmethod
    async def _check_cache(self, query: NormalizedQuery) -> Optional[SearchResponse]:
        """
        Check cache for existing results with circuit breaker.
        
        Must implement:
        - Cache lookup by query hash
        - Circuit breaker pattern for failures
        - TTL expiration checking
        - Cache statistics update
        
        Args:
            query: Normalized query with hash
            
        Returns:
            Cached SearchResponse or None if miss
        """
        pass
    
    @abstractmethod
    async def _select_workspaces(self, query: NormalizedQuery) -> List[str]:
        """
        Select relevant workspaces using AI analysis.
        
        Must implement:
        - AI-driven workspace selection
        - Technology hint consideration
        - Workspace availability checking
        - Maximum workspace limit enforcement
        
        Args:
            query: Normalized query
            
        Returns:
            List of selected workspace IDs
        """
        pass
    
    @abstractmethod
    async def _execute_vector_search(
        self,
        query: NormalizedQuery,
        workspaces: List[str]
    ) -> VectorSearchResults:
        """
        Execute parallel vector searches across workspaces.
        
        Must implement:
        - Parallel AnythingLLM queries
        - Per-workspace timeout enforcement
        - Result aggregation
        - Error handling per workspace
        
        Args:
            query: Normalized query
            workspaces: Selected workspace IDs
            
        Returns:
            Aggregated vector search results
        """
        pass
    
    @abstractmethod
    async def _evaluate_results(
        self,
        query: NormalizedQuery,
        results: VectorSearchResults
    ) -> EvaluationResult:
        """
        Evaluate search results quality using AI.
        
        Must implement:
        - Relevance scoring
        - Completeness assessment
        - Refinement need detection
        - External search need detection
        
        Args:
            query: Normalized query
            results: Vector search results
            
        Returns:
            AI evaluation of result quality
        """
        pass
    
    @abstractmethod
    async def _refine_query(
        self,
        query: NormalizedQuery,
        evaluation: EvaluationResult
    ) -> NormalizedQuery:
        """
        Refine query using AI when results are insufficient.
        
        Must implement:
        - AI-powered query improvement
        - Missing information identification
        - Query expansion strategies
        - Refinement validation
        
        Args:
            query: Original normalized query
            evaluation: Result evaluation
            
        Returns:
            Refined normalized query
        """
        pass
    
    @abstractmethod
    async def _execute_external_search(
        self,
        query: NormalizedQuery,
        evaluation: EvaluationResult
    ) -> VectorSearchResults:
        """
        Execute external search when vector search insufficient.
        
        Must implement:
        - Provider selection logic
        - External API calls
        - Result standardization
        - Fallback chain execution
        
        Args:
            query: Normalized query
            evaluation: Result evaluation
            
        Returns:
            External search results in standard format
        """
        pass
    
    @abstractmethod
    async def _extract_content(
        self,
        query: NormalizedQuery,
        results: VectorSearchResults
    ) -> Dict[str, Any]:
        """
        Extract relevant content using AI for answer generation.
        
        Must implement:
        - AI content extraction
        - Code snippet identification
        - Summary generation
        - Citation formatting
        
        Args:
            query: Normalized query
            results: Search results
            
        Returns:
            Extracted content for answer formatting
        """
        pass
    
    @abstractmethod
    async def _ingest_knowledge(
        self,
        query: NormalizedQuery,
        evaluation: EvaluationResult
    ) -> None:
        """
        Trigger knowledge ingestion for identified gaps.
        
        Must implement:
        - Learning opportunity identification
        - Ingestion queue submission
        - Priority calculation
        - Duplicate detection
        
        Args:
            query: Normalized query
            evaluation: Result evaluation with gaps
        """
        pass
    
    @abstractmethod
    async def _format_response(
        self,
        query: NormalizedQuery,
        results: VectorSearchResults,
        evaluation: EvaluationResult,
        response_type: str,
        extracted_content: Optional[Dict[str, Any]]
    ) -> SearchResponse:
        """
        Format final response based on requested type.
        
        Must implement:
        - Raw result formatting
        - Answer generation
        - Metadata inclusion
        - Performance metrics
        
        Args:
            query: Normalized query
            results: Search results
            evaluation: Result evaluation
            response_type: "raw" or "answer"
            extracted_content: AI-extracted content
            
        Returns:
            Formatted SearchResponse
        """
        pass
    
    @abstractmethod
    async def _update_cache(
        self,
        query: NormalizedQuery,
        response: SearchResponse
    ) -> None:
        """
        Update cache with new results.
        
        Must implement:
        - Cache write with TTL
        - Circuit breaker handling
        - Cache size management
        - Statistics update
        
        Args:
            query: Normalized query with hash
            response: Search response to cache
        """
        pass
    
    def _merge_results(
        self,
        vector_results: VectorSearchResults,
        external_results: VectorSearchResults
    ) -> VectorSearchResults:
        """
        Merge vector and external search results.
        
        Default implementation can be overridden for custom merging.
        
        Args:
            vector_results: Results from vector search
            external_results: Results from external search
            
        Returns:
            Merged results with deduplication
        """
        # Default implementation - can be overridden
        merged = VectorSearchResults(
            results=vector_results.results + external_results.results,
            total_count=vector_results.total_count + external_results.total_count,
            execution_time_ms=max(
                vector_results.execution_time_ms,
                external_results.execution_time_ms
            ),
            workspaces_searched=vector_results.workspaces_searched,
            external_providers_used=external_results.external_providers_used
        )
        
        # Simple deduplication by content_id
        seen_ids = set()
        deduplicated_results = []
        for result in merged.results:
            if result.content_id not in seen_ids:
                seen_ids.add(result.content_id)
                deduplicated_results.append(result)
        
        merged.results = deduplicated_results
        merged.total_count = len(deduplicated_results)
        
        return merged
    
    def _compute_query_hash(self, normalized_text: str, technology_hint: Optional[str]) -> str:
        """
        Compute consistent hash for cache key.
        
        Args:
            normalized_text: Normalized query text
            technology_hint: Optional technology context
            
        Returns:
            SHA256 hash as hex string
        """
        # Include technology hint in hash if present
        cache_key = f"{normalized_text}:{technology_hint or ''}"
        return hashlib.sha256(cache_key.encode()).hexdigest()