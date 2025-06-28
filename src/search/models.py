"""
Search Data Models - PRD-009
Pydantic models for search operations and orchestration workflow.

These models define the exact data structures specified in PRD-009 for search
queries, results, and orchestration coordination.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SearchStrategy(str, Enum):
    """Search strategy enumeration as specified in PRD-009"""

    VECTOR = "vector"
    METADATA = "metadata"
    HYBRID = "hybrid"
    FACETED = "faceted"


class SearchQuery(BaseModel):
    """
    Search query model with filtering and strategy options.

    Implements exact SearchQuery structure from PRD-009 with all specified fields.
    """

    query: str = Field(..., description="Search query string")
    filters: Optional[Dict[str, Any]] = Field(None, description="Search filters")
    strategy: SearchStrategy = Field(
        SearchStrategy.HYBRID, description="Search strategy to use"
    )
    limit: int = Field(20, ge=1, le=100, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Result offset for pagination")
    technology_hint: Optional[str] = Field(None, description="Technology filter hint")
    workspace_slugs: Optional[List[str]] = Field(None, description="Workspace filters")


class SearchResult(BaseModel):
    """
    Individual search result with relevance scoring.

    Implements exact SearchResult structure from PRD-009 with all metadata fields.
    """

    content_id: str = Field(..., description="Unique content identifier")
    title: str = Field(..., description="Document title")
    content_snippet: str = Field(..., description="Relevant content excerpt")
    source_url: str = Field(..., description="Original source URL")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance score (0.0-1.0)"
    )
    metadata: Dict[str, Any] = Field(..., description="Additional result metadata")
    technology: Optional[str] = Field(None, description="Technology/framework")
    quality_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Content quality score"
    )
    workspace_slug: Optional[str] = Field(None, description="Source workspace")
    chunk_index: Optional[int] = Field(None, description="Chunk index if applicable")


class SearchResults(BaseModel):
    """
    Complete search response with results and execution metadata.

    Implements exact SearchResults structure from PRD-009.
    """

    results: List[SearchResult] = Field(..., description="List of search results")
    total_count: int = Field(..., description="Total number of results found")
    query_time_ms: int = Field(..., description="Query execution time in milliseconds")
    strategy_used: SearchStrategy = Field(
        ..., description="Search strategy that was executed"
    )
    cache_hit: bool = Field(False, description="Whether results came from cache")
    workspaces_searched: List[str] = Field(
        default_factory=list, description="Workspaces included in search"
    )
    enrichment_triggered: bool = Field(
        False, description="Whether enrichment was triggered"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description="Additional metadata"
    )


class WorkspaceInfo(BaseModel):
    """
    Workspace information for multi-workspace search strategy.

    Implements exact WorkspaceInfo structure from PRD-009.
    """

    slug: str = Field(..., description="Workspace slug identifier")
    technology: str = Field(..., description="Primary technology/framework")
    relevance_score: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance score for query"
    )
    last_updated: datetime = Field(..., description="Last update timestamp")
    document_count: Optional[int] = Field(
        None, description="Number of documents in workspace"
    )


class EvaluationResult(BaseModel):
    """
    LLM evaluation result for search quality assessment.

    Used for enrichment decision making as specified in PRD-009.
    """

    overall_quality: float = Field(
        ..., ge=0.0, le=1.0, description="Overall result quality score"
    )
    relevance_assessment: float = Field(
        ..., ge=0.0, le=1.0, description="Relevance assessment score"
    )
    completeness_score: float = Field(
        ..., ge=0.0, le=1.0, description="Answer completeness score"
    )
    needs_enrichment: bool = Field(..., description="Whether enrichment is recommended")
    enrichment_topics: List[str] = Field(
        default_factory=list, description="Suggested enrichment topics"
    )
    confidence_level: float = Field(
        ..., ge=0.0, le=1.0, description="Evaluation confidence level"
    )
    reasoning: Optional[str] = Field(None, description="LLM reasoning for evaluation")


class SearchAnalytics(BaseModel):
    """
    Search analytics data for performance monitoring.

    Tracks search performance metrics as mentioned in PRD-009.
    """

    query_hash: str = Field(..., description="Query identifier hash")
    execution_time_ms: int = Field(..., description="Total execution time")
    vector_search_time_ms: Optional[int] = Field(None, description="Vector search time")
    metadata_search_time_ms: Optional[int] = Field(
        None, description="Metadata search time"
    )
    ranking_time_ms: Optional[int] = Field(None, description="Result ranking time")
    cache_hit: bool = Field(..., description="Whether cache was hit")
    result_count: int = Field(..., description="Number of results returned")
    workspaces_searched: int = Field(..., description="Number of workspaces searched")
    strategy_used: SearchStrategy = Field(..., description="Search strategy executed")
    enrichment_triggered: bool = Field(
        ..., description="Whether enrichment was triggered"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Analytics timestamp"
    )


class CachedSearchResult(BaseModel):
    """
    Cached search result structure for Redis storage.

    Optimized structure for search result caching.
    """

    query_hash: str = Field(..., description="Query identifier hash")
    results: SearchResults = Field(..., description="Complete search results")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Cache creation time"
    )
    expires_at: datetime = Field(..., description="Cache expiration time")
    access_count: int = Field(0, description="Number of times accessed from cache")
