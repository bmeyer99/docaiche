"""
Consolidated Pydantic schemas for the Docaiche API.

All request/response models in one place for easy maintenance and consistency.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Literal, Union
from pydantic import BaseModel, Field


# ============================================================================
# Error Schemas (RFC 7807 Problem Details)
# ============================================================================

class ProblemDetail(BaseModel):
    """Standard error response format following RFC 7807."""
    type: str = Field(..., description="URI reference identifying the problem type")
    title: str = Field(..., description="Human-readable summary")
    status: int = Field(..., description="HTTP status code")
    detail: Optional[str] = Field(None, description="Human-readable explanation")
    instance: Optional[str] = Field(None, description="URI reference identifying specific occurrence")
    error_code: Optional[str] = Field(None, description="Internal error code")
    trace_id: Optional[str] = Field(None, description="Request trace identifier")


# ============================================================================
# Search Schemas
# ============================================================================

class SearchRequest(BaseModel):
    """Request body for search operations."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query string")
    technology_hint: Optional[str] = Field(None, description="Optional technology filter")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of results")
    session_id: Optional[str] = Field(None, description="User session identifier")


class SearchResult(BaseModel):
    """Individual search result item."""
    content_id: str = Field(..., description="Unique content identifier")
    title: str = Field(..., description="Document or section title")
    snippet: str = Field(..., description="Relevant content excerpt")
    source_url: str = Field(..., description="Original source URL")
    technology: str = Field(..., description="Associated technology/framework")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score for the query")
    content_type: str = Field(..., description="Type of content")
    workspace: str = Field(..., description="AnythingLLM workspace")


class SearchResponse(BaseModel):
    """Response body for search operations."""
    results: List[SearchResult] = Field(..., description="Search results list")
    total_count: int = Field(..., description="Total matching results")
    query: str = Field(..., description="Original search query")
    technology_hint: Optional[str] = Field(None, description="Applied technology filter")
    execution_time_ms: int = Field(..., description="Search execution time")
    cache_hit: bool = Field(..., description="Whether served from cache")
    enrichment_triggered: bool = Field(False, description="Whether knowledge enrichment was triggered")


# ============================================================================
# Upload Schemas
# ============================================================================

class UploadResponse(BaseModel):
    """Response for document upload operations."""
    upload_id: str = Field(..., description="Unique upload identifier")
    status: Literal["accepted", "processing", "completed", "failed"] = Field(..., description="Upload processing status")
    message: Optional[str] = Field(None, description="Status message")


# ============================================================================
# Feedback Schemas
# ============================================================================

class FeedbackRequest(BaseModel):
    """Request body for user feedback submission."""
    content_id: str = Field(..., description="Content being rated")
    feedback_type: Literal["helpful", "not_helpful", "outdated", "incorrect", "flag"] = Field(..., description="Type of feedback")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Optional star rating")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional feedback comment")
    query_context: Optional[str] = Field(None, description="Search query that led to content")
    session_id: Optional[str] = Field(None, description="User session identifier")


class SignalRequest(BaseModel):
    """Request body for implicit user interaction signals."""
    query_id: str = Field(..., description="Search query session ID")
    session_id: str = Field(..., description="User session ID")
    signal_type: Literal["click", "dwell", "abandon", "refine", "copy"] = Field(..., description="Type of interaction signal")
    content_id: Optional[str] = Field(None, description="Interacted content ID")
    result_position: Optional[int] = Field(None, ge=0, description="Result position (0-based)")
    dwell_time_ms: Optional[int] = Field(None, ge=0, description="Time spent on result (milliseconds)")


# ============================================================================
# System Health & Stats Schemas
# ============================================================================

class HealthStatus(BaseModel):
    """Health status of individual service components."""
    service: str = Field(..., description="Service component name")
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Current health status")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    last_check: datetime = Field(..., description="Last health check timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional status details")


class HealthResponse(BaseModel):
    """Response body for system health checks."""
    overall_status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Overall system health")
    services: List[HealthStatus] = Field(..., description="Individual service statuses")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")


class StatsResponse(BaseModel):
    """Response body for system usage statistics."""
    search_stats: Dict[str, Any] = Field(..., description="Search performance and usage statistics")
    cache_stats: Dict[str, Any] = Field(..., description="Cache hit rates and performance")
    content_stats: Dict[str, Any] = Field(..., description="Content collection and quality statistics")
    system_stats: Dict[str, Any] = Field(..., description="System resource and performance statistics")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Statistics timestamp")


# ============================================================================
# Collections Schemas
# ============================================================================

class Collection(BaseModel):
    """Individual collection/workspace information."""
    slug: str = Field(..., description="Unique collection identifier")
    name: str = Field(..., description="Human-readable collection name")
    technology: str = Field(..., description="Primary technology or framework")
    document_count: int = Field(..., description="Number of documents in collection")
    last_updated: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(True, description="Whether collection is actively maintained")


class CollectionsResponse(BaseModel):
    """Response body for available collections listing."""
    collections: List[Collection] = Field(..., description="Available documentation collections")
    total_count: int = Field(..., description="Total number of collections")


# ============================================================================
# Configuration Schemas
# ============================================================================

class ConfigurationItem(BaseModel):
    """Individual configuration key-value item."""
    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value")
    schema_version: str = Field("1.0", description="Configuration schema version")
    description: Optional[str] = Field(None, description="Human-readable description")
    is_sensitive: bool = Field(False, description="Whether value contains sensitive data")


class ConfigurationResponse(BaseModel):
    """Response body for system configuration retrieval."""
    items: List[ConfigurationItem] = Field(..., description="Configuration items")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Configuration timestamp")


class ConfigurationUpdateRequest(BaseModel):
    """Request body for configuration updates."""
    key: str = Field(..., description="Configuration key to update")
    value: Any = Field(..., description="New configuration value")
    description: Optional[str] = Field(None, description="Optional description of change")


# ============================================================================
# Admin Schemas
# ============================================================================

class AdminContentItem(BaseModel):
    """Individual content item with metadata for admin interface."""
    content_id: str = Field(..., description="Unique content identifier")
    title: str = Field(..., description="Content title")
    content_type: str = Field(..., description="Type of content")
    technology: Optional[str] = Field(None, description="Associated technology/framework")
    source_url: Optional[str] = Field(None, description="Original source URL")
    collection_name: str = Field(..., description="Collection this content belongs to")
    created_at: datetime = Field(..., description="Content creation timestamp")
    last_updated: datetime = Field(..., description="Last modification timestamp")
    size_bytes: Optional[int] = Field(None, description="Content size in bytes")
    status: Literal["active", "flagged", "removed"] = Field(..., description="Current content status")


class AdminSearchResponse(BaseModel):
    """Response body for admin content search."""
    items: List[AdminContentItem] = Field(..., description="Matching content items")
    total_count: int = Field(..., description="Total matching items")
    page: int = Field(..., ge=1, description="Current page number (1-based)")
    page_size: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether more pages available")