"""
Search Orchestration Exceptions - PRD-009
Structured exception hierarchy for search operations.

Provides comprehensive error handling for all search orchestration operations
as specified in PRD-009 with proper error context and recovery guidance.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class SearchOrchestrationError(Exception):
    """
    Base exception for all search orchestration errors.
    
    Provides common error context and logging for search operations.
    """
    
    def __init__(
        self, 
        message: str, 
        error_context: Optional[Dict[str, Any]] = None,
        recoverable: bool = True
    ):
        """
        Initialize search orchestration error.
        
        Args:
            message: Human-readable error message
            error_context: Additional context for debugging
            recoverable: Whether the error is recoverable
        """
        self.message = message
        self.error_context = error_context or {}
        self.recoverable = recoverable
        super().__init__(self.message)
        
        # Log error with context
        logger.error(
            f"SearchOrchestrationError: {message}",
            extra={
                "error_context": self.error_context,
                "recoverable": self.recoverable
            }
        )


class VectorSearchError(SearchOrchestrationError):
    """
    Exception for vector search operations via AnythingLLM.
    
    Handles errors from AnythingLLM client integration.
    """
    
    def __init__(
        self,
        message: str,
        workspace_slug: Optional[str] = None,
        query: Optional[str] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize vector search error.
        
        Args:
            message: Error message
            workspace_slug: Workspace where error occurred
            query: Search query that caused error
            error_context: Additional error context
        """
        context = {
            "workspace_slug": workspace_slug,
            "query": query[:100] if query else None,  # Truncate for logging
            **(error_context or {})
        }
        super().__init__(message, context, recoverable=True)


class MetadataSearchError(SearchOrchestrationError):
    """
    Exception for metadata-based search operations.
    
    Handles errors from database queries and metadata processing.
    """
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize metadata search error.
        
        Args:
            message: Error message
            query: Search query that caused error
            filters: Search filters applied
            error_context: Additional error context
        """
        context = {
            "query": query[:100] if query else None,  # Truncate for logging
            "filters": filters,
            **(error_context or {})
        }
        super().__init__(message, context, recoverable=True)


class ResultRankingError(SearchOrchestrationError):
    """
    Exception for result ranking and scoring operations.
    
    Handles errors during result aggregation and ranking.
    """
    
    def __init__(
        self,
        message: str,
        result_count: Optional[int] = None,
        ranking_strategy: Optional[str] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize result ranking error.
        
        Args:
            message: Error message
            result_count: Number of results being ranked
            ranking_strategy: Ranking strategy being used
            error_context: Additional error context
        """
        context = {
            "result_count": result_count,
            "ranking_strategy": ranking_strategy,
            **(error_context or {})
        }
        super().__init__(message, context, recoverable=True)


class SearchCacheError(SearchOrchestrationError):
    """
    Exception for search result caching operations.
    
    Handles errors from Redis cache operations during search.
    """
    
    def __init__(
        self,
        message: str,
        cache_key: Optional[str] = None,
        operation: Optional[str] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize search cache error.
        
        Args:
            message: Error message
            cache_key: Cache key involved in error
            operation: Cache operation (get, set, delete)
            error_context: Additional error context
        """
        context = {
            "cache_key": cache_key,
            "operation": operation,
            **(error_context or {})
        }
        # Cache errors are usually recoverable - system can continue without cache
        super().__init__(message, context, recoverable=True)


class WorkspaceSelectionError(SearchOrchestrationError):
    """
    Exception for workspace selection and multi-workspace search.
    
    Handles errors during intelligent workspace selection process.
    """
    
    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        technology_hint: Optional[str] = None,
        available_workspaces: Optional[int] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize workspace selection error.
        
        Args:
            message: Error message
            query: Search query
            technology_hint: Technology filter hint
            available_workspaces: Number of available workspaces
            error_context: Additional error context
        """
        context = {
            "query": query[:100] if query else None,  # Truncate for logging
            "technology_hint": technology_hint,
            "available_workspaces": available_workspaces,
            **(error_context or {})
        }
        super().__init__(message, context, recoverable=True)


class SearchTimeoutError(SearchOrchestrationError):
    """
    Exception for search operation timeouts.
    
    Handles timeout scenarios during search orchestration.
    """
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[float] = None,
        operation: Optional[str] = None,
        partial_results: Optional[int] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize search timeout error.
        
        Args:
            message: Error message
            timeout_seconds: Timeout duration
            operation: Operation that timed out
            partial_results: Number of partial results available
            error_context: Additional error context
        """
        context = {
            "timeout_seconds": timeout_seconds,
            "operation": operation,
            "partial_results": partial_results,
            **(error_context or {})
        }
        super().__init__(message, context, recoverable=False)


class LLMEvaluationError(SearchOrchestrationError):
    """
    Exception for LLM evaluation operations.
    
    Handles errors during AI evaluation of search results.
    """
    
    def __init__(
        self,
        message: str,
        result_count: Optional[int] = None,
        model_used: Optional[str] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize LLM evaluation error.
        
        Args:
            message: Error message
            result_count: Number of results being evaluated
            model_used: LLM model used for evaluation
            error_context: Additional error context
        """
        context = {
            "result_count": result_count,
            "model_used": model_used,
            **(error_context or {})
        }
        # LLM evaluation errors are recoverable - search can continue without evaluation
        super().__init__(message, context, recoverable=True)


class EnrichmentTriggerError(SearchOrchestrationError):
    """
    Exception for enrichment triggering operations.
    
    Handles errors when triggering background knowledge enrichment.
    """
    
    def __init__(
        self,
        message: str,
        enrichment_topics: Optional[List[str]] = None,
        trigger_reason: Optional[str] = None,
        error_context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize enrichment trigger error.
        
        Args:
            message: Error message
            enrichment_topics: Topics for enrichment
            trigger_reason: Reason for triggering enrichment
            error_context: Additional error context
        """
        context = {
            "enrichment_topics": enrichment_topics,
            "trigger_reason": trigger_reason,
            **(error_context or {})
        }
        # Enrichment trigger errors are recoverable - search results can still be returned
        super().__init__(message, context, recoverable=True)