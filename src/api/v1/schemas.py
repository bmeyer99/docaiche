"""
API v1 Pydantic Schemas - PRD-001: HTTP API Foundation
API-002: Implement all Pydantic request/response schemas

This module contains all Pydantic models for API request/response validation
exactly as specified in PRD-001 Data Models section.
"""

import logging
from typing import List, Optional, Dict, Literal, Any
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(__name__)

# Error Response Schema (RFC 7807 Problem Details)
class ProblemDetail(BaseModel):
    """RFC 7807 Problem Details format for error responses"""
    type: str = Field(..., description="URI reference identifying the problem type")
    title: str = Field(..., description="Human-readable summary")
    status: int = Field(..., description="HTTP status code")
    detail: Optional[str] = Field(None, description="Human-readable explanation")
    instance: Optional[str] = Field(None, description="URI reference identifying specific occurrence")
    error_code: Optional[str] = Field(None, description="Internal error code")
    trace_id: Optional[str] = Field(None, description="Request trace identifier")

# Search Request/Response Models
class SearchRequest(BaseModel):
    """Search query request body for POST /api/v1/search"""
    query: str = Field(..., min_length=1, max_length=500, description="Search query string")
    technology_hint: Optional[str] = Field(None, description="Optional technology filter (e.g., 'python', 'react')")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of results to return")
    session_id: Optional[str] = Field(None, description="User session identifier for tracking")

class SearchResult(BaseModel):
    """Individual search result item"""
    content_id: str = Field(..., description="Unique identifier for the content")
    title: str = Field(..., description="Title of the document or section")
    snippet: str = Field(..., description="Relevant excerpt from the content")
    source_url: str = Field(..., description="Original source URL")
    technology: str = Field(..., description="Associated technology or framework")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score for the query")
    content_type: str = Field(..., description="Type of content (documentation, code, example, etc.)")
    workspace: str = Field(..., description="AnythingLLM workspace containing this content")

class SearchResponse(BaseModel):
    """Response body for search queries"""
    results: List[SearchResult] = Field(..., description="List of search results")
    total_count: int = Field(..., description="Total number of matching results")
    query: str = Field(..., description="Original search query")
    technology_hint: Optional[str] = Field(None, description="Technology filter applied")
    execution_time_ms: int = Field(..., description="Time taken to execute the search")
    cache_hit: bool = Field(..., description="Whether results were served from cache")
    enrichment_triggered: bool = Field(False, description="Whether knowledge enrichment was triggered")

# Feedback Models
class FeedbackRequest(BaseModel):
    """Request body for user feedback submission"""
    content_id: str = Field(..., description="ID of the content being rated")
    feedback_type: Literal['helpful', 'not_helpful', 'outdated', 'incorrect', 'flag'] = Field(..., description="Type of feedback")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Optional 1-5 star rating")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional feedback comment")
    query_context: Optional[str] = Field(None, description="Search query that led to this content")
    session_id: Optional[str] = Field(None, description="User session identifier")

# Signal Models
class SignalRequest(BaseModel):
    """Request body for implicit user interaction signals"""
    query_id: str = Field(..., description="The unique ID of the search query session.")
    session_id: str = Field(..., description="The user's session ID.")
    signal_type: Literal['click', 'dwell', 'abandon', 'refine', 'copy']
    content_id: Optional[str] = Field(None, description="The ID of the document that was interacted with.")
    result_position: Optional[int] = Field(None, description="The 0-based index of the clicked result.")
    dwell_time_ms: Optional[int] = Field(None, description="Time in milliseconds spent on a result.")

# Health Check Models
class HealthStatus(BaseModel):
    """Health status of individual service components"""
    service: str = Field(..., description="Name of the service component")
    status: Literal['healthy', 'degraded', 'unhealthy'] = Field(..., description="Current health status")
    response_time_ms: Optional[int] = Field(None, description="Response time in milliseconds")
    last_check: datetime = Field(..., description="Timestamp of last health check")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional status details")

class HealthResponse(BaseModel):
    """Response body for system health checks"""
    overall_status: Literal['healthy', 'degraded', 'unhealthy'] = Field(..., description="Overall system health")
    services: List[HealthStatus] = Field(..., description="Individual service health statuses")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")

# Statistics Models
class StatsResponse(BaseModel):
    """Response body for system usage statistics"""
    search_stats: Dict[str, Any] = Field(..., description="Search performance and usage statistics")
    cache_stats: Dict[str, Any] = Field(..., description="Cache hit rates and performance")
    content_stats: Dict[str, Any] = Field(..., description="Content collection and quality statistics")
    system_stats: Dict[str, Any] = Field(..., description="System resource and performance statistics")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Statistics timestamp")

# Collections Models
class Collection(BaseModel):
    """Individual collection/workspace information"""
    slug: str = Field(..., description="Unique collection identifier")
    name: str = Field(..., description="Human-readable collection name")
    technology: str = Field(..., description="Primary technology or framework")
    document_count: int = Field(..., description="Number of documents in collection")
    last_updated: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(True, description="Whether collection is actively maintained")

class CollectionsResponse(BaseModel):
    """Response body for available collections listing"""
    collections: List[Collection] = Field(..., description="Available documentation collections")
    total_count: int = Field(..., description="Total number of collections")

# Configuration Models
class ConfigurationItem(BaseModel):
    """Individual configuration key-value item"""
    key: str = Field(..., description="Configuration key")
    value: Any = Field(..., description="Configuration value")
    schema_version: str = Field("1.0", description="Configuration schema version")
    description: Optional[str] = Field(None, description="Human-readable description")
    is_sensitive: bool = Field(False, description="Whether value contains sensitive data")

class ConfigurationResponse(BaseModel):
    """Response body for system configuration retrieval"""
    items: List[ConfigurationItem] = Field(..., description="Configuration items")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Configuration timestamp")

class ConfigurationUpdateRequest(BaseModel):
    """Request body for configuration updates"""
    key: str = Field(..., description="Configuration key to update")
    value: Any = Field(..., description="New configuration value")
    description: Optional[str] = Field(None, description="Optional description of the change")

# Admin Models
class AdminContentItem(BaseModel):
    """Individual content item with metadata for admin management"""
    content_id: str = Field(..., description="Unique identifier for the content item.")
    title: str = Field(..., description="Title of the content item.")
    content_type: str = Field(..., description="Type of content (e.g., 'documentation', 'code', 'readme').")
    technology: Optional[str] = Field(None, description="Associated technology or framework.")
    source_url: Optional[str] = Field(None, description="Original source URL of the content.")
    collection_name: str = Field(..., description="Name of the collection this content belongs to.")
    created_at: datetime = Field(..., description="Timestamp when content was indexed.")
    last_updated: datetime = Field(..., description="Timestamp when content was last modified.")
    size_bytes: Optional[int] = Field(None, description="Size of the content in bytes.")
    status: Literal['active', 'flagged', 'removed'] = Field(..., description="Current status of the content.")

class AdminSearchResponse(BaseModel):
    """Response body for admin content search"""
    items: List[AdminContentItem] = Field(..., description="List of matching content items.")
    total_count: int = Field(..., description="Total number of items matching the search criteria.")
    page: int = Field(..., description="Current page number (1-based).")
    page_size: int = Field(..., description="Number of items per page.")
    has_more: bool = Field(..., description="Whether there are more pages available.")

class LLMProviderTestRequest(BaseModel):
    provider: str
    base_url: str
    api_key: Optional[str] = None