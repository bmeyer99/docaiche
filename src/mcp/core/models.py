"""
Data Models for MCP Search System
==================================

Core data structures used throughout the MCP search workflow.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class SearchStrategy(str, Enum):
    """Search strategy options."""
    RELEVANCE = "relevance"
    RECENCY = "recency"
    HYBRID = "hybrid"


class ResponseType(str, Enum):
    """Response format options."""
    RAW = "raw"
    ANSWER = "answer"


class ContentType(str, Enum):
    """Content type classification."""
    DOCUMENTATION = "documentation"
    API_REFERENCE = "api_reference"
    TUTORIAL = "tutorial"
    CODE_EXAMPLE = "code_example"
    GUIDE = "guide"
    FAQ = "faq"
    BLOG = "blog"
    OTHER = "other"


class NormalizedQuery(BaseModel):
    """
    Normalized and processed query with metadata.
    
    Contains the cleaned query text, hash for caching,
    and extracted metadata for search optimization.
    """
    
    original_query: str = Field(
        description="Original user query before normalization"
    )
    
    normalized_text: str = Field(
        description="Cleaned and normalized query text"
    )
    
    query_hash: str = Field(
        description="SHA256 hash for cache key"
    )
    
    technology_hint: Optional[str] = Field(
        default=None,
        description="Technology context from user or AI detection"
    )
    
    detected_intent: Optional[str] = Field(
        default=None,
        description="AI-detected query intent"
    )
    
    extracted_entities: List[str] = Field(
        default_factory=list,
        description="Entities extracted from query"
    )
    
    suggested_workspaces: List[str] = Field(
        default_factory=list,
        description="AI-suggested relevant workspaces"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Query normalization timestamp"
    )


class SearchRequest(BaseModel):
    """
    Complete search request with context and metadata.
    
    Includes user context, priority, and tracking information
    for queue management and analytics.
    """
    
    query: NormalizedQuery = Field(
        description="Normalized query object"
    )
    
    user_context: "UserContext" = Field(
        description="User session and permission context"
    )
    
    response_type: ResponseType = Field(
        default=ResponseType.RAW,
        description="Requested response format"
    )
    
    strategy: SearchStrategy = Field(
        default=SearchStrategy.HYBRID,
        description="Search strategy to use"
    )
    
    request_id: str = Field(
        description="Unique request identifier for tracking"
    )
    
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for context continuity"
    )
    
    priority_score: float = Field(
        default=1.0,
        description="Calculated priority for queue ordering",
        ge=0.0,
        le=10.0
    )
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Request creation timestamp"
    )
    
    enqueued_at: Optional[datetime] = Field(
        default=None,
        description="Queue entry timestamp"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional request metadata"
    )


class SearchResult(BaseModel):
    """Individual search result with metadata."""
    
    content_id: str = Field(
        description="Unique content identifier"
    )
    
    title: str = Field(
        description="Result title"
    )
    
    snippet: str = Field(
        description="Content snippet with query highlights"
    )
    
    content: Optional[str] = Field(
        default=None,
        description="Full content if available"
    )
    
    source_url: str = Field(
        description="Original source URL"
    )
    
    workspace: str = Field(
        description="Source workspace identifier"
    )
    
    technology: Optional[str] = Field(
        default=None,
        description="Associated technology/framework"
    )
    
    content_type: ContentType = Field(
        description="Type of content"
    )
    
    relevance_score: float = Field(
        description="Relevance score (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    recency_score: float = Field(
        default=0.5,
        description="Recency score (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    quality_score: float = Field(
        default=0.5,
        description="Content quality score (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional result metadata"
    )
    
    created_at: Optional[datetime] = Field(
        default=None,
        description="Content creation date"
    )
    
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Content last update date"
    )


class VectorSearchResults(BaseModel):
    """
    Results from vector search operations.
    
    Contains aggregated results from multiple workspaces
    with execution metadata.
    """
    
    results: List[SearchResult] = Field(
        default_factory=list,
        description="List of search results"
    )
    
    total_count: int = Field(
        default=0,
        description="Total results found (before pagination)"
    )
    
    execution_time_ms: int = Field(
        description="Total execution time in milliseconds"
    )
    
    workspaces_searched: List[str] = Field(
        default_factory=list,
        description="Workspaces included in search"
    )
    
    workspace_errors: Dict[str, str] = Field(
        default_factory=dict,
        description="Errors by workspace if any"
    )
    
    external_providers_used: List[str] = Field(
        default_factory=list,
        description="External providers used if any"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional search metadata"
    )


class EvaluationResult(BaseModel):
    """
    AI evaluation of search results quality.
    
    Determines if results are sufficient or if additional
    actions (refinement, external search) are needed.
    """
    
    overall_quality: float = Field(
        description="Overall result quality (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    relevance_assessment: float = Field(
        description="Relevance to query (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    completeness_score: float = Field(
        description="Answer completeness (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    needs_refinement: bool = Field(
        default=False,
        description="Whether query refinement would help"
    )
    
    needs_external_search: bool = Field(
        default=False,
        description="Whether external search is recommended"
    )
    
    missing_information: List[str] = Field(
        default_factory=list,
        description="Identified information gaps"
    )
    
    suggested_refinements: List[str] = Field(
        default_factory=list,
        description="Suggested query refinements"
    )
    
    recommended_providers: List[str] = Field(
        default_factory=list,
        description="Recommended external providers"
    )
    
    confidence_level: float = Field(
        description="AI confidence in evaluation (0.0-1.0)",
        ge=0.0,
        le=1.0
    )
    
    reasoning: str = Field(
        description="AI reasoning for evaluation"
    )
    
    knowledge_gaps: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Identified gaps for knowledge ingestion"
    )


class SearchResponse(BaseModel):
    """
    Final search response with results and metadata.
    
    Complete response structure returned to clients with
    all execution details and performance metrics.
    """
    
    request_id: str = Field(
        description="Original request ID for tracking"
    )
    
    query: str = Field(
        description="Original user query"
    )
    
    normalized_query: str = Field(
        description="Normalized query used for search"
    )
    
    results: List[SearchResult] = Field(
        default_factory=list,
        description="Final ranked search results"
    )
    
    total_count: int = Field(
        description="Total results found"
    )
    
    returned_count: int = Field(
        description="Number of results returned"
    )
    
    response_type: ResponseType = Field(
        description="Response format used"
    )
    
    formatted_answer: Optional[str] = Field(
        default=None,
        description="AI-generated answer if requested"
    )
    
    execution_time_ms: int = Field(
        description="Total execution time"
    )
    
    cache_hit: bool = Field(
        default=False,
        description="Whether results were from cache"
    )
    
    workspaces_searched: List[str] = Field(
        default_factory=list,
        description="Workspaces included in search"
    )
    
    external_search_used: bool = Field(
        default=False,
        description="Whether external search was used"
    )
    
    external_providers: List[str] = Field(
        default_factory=list,
        description="External providers used"
    )
    
    refinement_applied: bool = Field(
        default=False,
        description="Whether query refinement was applied"
    )
    
    refined_query: Optional[str] = Field(
        default=None,
        description="Refined query if used"
    )
    
    knowledge_gaps_identified: int = Field(
        default=0,
        description="Number of knowledge gaps found"
    )
    
    evaluation_summary: Optional[Dict[str, Any]] = Field(
        default=None,
        description="AI evaluation summary"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Response timestamp"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional response metadata"
    )


class UserContext(BaseModel):
    """
    User session and permission context.
    
    Contains user identification, workspace access, and
    rate limiting information.
    """
    
    user_id: str = Field(
        description="Unique user identifier"
    )
    
    session_id: Optional[str] = Field(
        default=None,
        description="Session identifier for context"
    )
    
    workspace_access: List[str] = Field(
        default_factory=list,
        description="Workspaces user can access"
    )
    
    rate_limit_tier: str = Field(
        default="standard",
        description="User's rate limit tier"
    )
    
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="User preferences and settings"
    )
    
    request_count_minute: int = Field(
        default=0,
        description="Requests in current minute window"
    )
    
    request_count_hour: int = Field(
        default=0,
        description="Requests in current hour window"
    )
    
    last_request_at: Optional[datetime] = Field(
        default=None,
        description="Last request timestamp"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional user metadata"
    )


class QueueStats(BaseModel):
    """
    Queue statistics and monitoring metrics.
    
    Provides comprehensive view of queue health and performance.
    """
    
    current_depth: int = Field(
        description="Current total queue depth"
    )
    
    max_depth: int = Field(
        description="Maximum configured depth"
    )
    
    depth_by_priority: Dict[str, int] = Field(
        default_factory=dict,
        description="Queue depth by priority level"
    )
    
    average_wait_time_ms: float = Field(
        description="Average wait time in queue"
    )
    
    wait_time_by_priority: Dict[str, float] = Field(
        default_factory=dict,
        description="Average wait time by priority"
    )
    
    overflow_count_minute: int = Field(
        default=0,
        description="Queue overflows in last minute"
    )
    
    overflow_count_hour: int = Field(
        default=0,
        description="Queue overflows in last hour"
    )
    
    rate_limit_hits_minute: int = Field(
        default=0,
        description="Rate limit hits in last minute"
    )
    
    processing_rate_per_second: float = Field(
        description="Current processing rate"
    )
    
    oldest_request_age_ms: Optional[int] = Field(
        default=None,
        description="Age of oldest queued request"
    )
    
    user_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Queue depth by user (top 10)"
    )
    
    workspace_distribution: Dict[str, int] = Field(
        default_factory=dict,
        description="Queue depth by workspace"
    )
    
    status: str = Field(
        description="Queue health status"
    )
    
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Stats update timestamp"
    )