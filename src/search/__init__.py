"""
Search Orchestration Engine - PRD-009
Intelligent search workflow coordinator managing end-to-end search process.

This module implements the core search orchestration system that coordinates between
vector search, metadata queries, result ranking, and enrichment triggering exactly
as specified in PRD-009.
"""

from .orchestrator import SearchOrchestrator
from .models import (
    SearchQuery,
    SearchResult,
    SearchResults,
    SearchStrategy,
    WorkspaceInfo,
    EvaluationResult,
)
from .strategies import WorkspaceSearchStrategy
from .ranking import ResultRanker
from .cache import SearchCacheManager
from .exceptions import (
    SearchOrchestrationError,
    VectorSearchError,
    MetadataSearchError,
    ResultRankingError,
    SearchCacheError,
    WorkspaceSelectionError,
)
from .factory import create_search_orchestrator

__all__ = [
    # Core classes
    "SearchOrchestrator",
    "WorkspaceSearchStrategy",
    "ResultRanker",
    "SearchCacheManager",
    # Data models
    "SearchQuery",
    "SearchResult",
    "SearchResults",
    "SearchStrategy",
    "WorkspaceInfo",
    "EvaluationResult",
    # Exceptions
    "SearchOrchestrationError",
    "VectorSearchError",
    "MetadataSearchError",
    "ResultRankingError",
    "SearchCacheError",
    "WorkspaceSelectionError",
    # Factory
    "create_search_orchestrator",
]
