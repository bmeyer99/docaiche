"""
API Schemas - Consolidated from v1 schemas with additions for missing types
"""

from typing import List, Optional, Dict, Literal, Any
from pydantic import BaseModel, Field
from datetime import datetime


# Search Models
class SearchRequest(BaseModel):
    """Search query request"""

    query: str = Field(
        ..., min_length=1, max_length=500, regex=r'^[^<>&"\'\x00-\x1f]+$'
    )  # Prevent XSS and control chars
    technology_hint: Optional[str] = Field(None, regex=r"^[a-zA-Z0-9\-_]+$")
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)  # Added for pagination
    session_id: Optional[str] = Field(None, regex=r"^[a-zA-Z0-9\-_]+$")
    # Added missing fields referenced in SearchService
    content_type_filter: Optional[str] = Field(None, regex=r"^[a-zA-Z0-9\-_]+$")
    source_filter: Optional[str] = Field(None, regex=r"^[a-zA-Z0-9\-_.]+$")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


class SearchResult(BaseModel):
    """Individual search result"""

    content_id: str
    title: str
    snippet: str  # Standardized name
    source_url: str
    technology: str
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    content_type: str
    workspace: str
    # Added fields for better compatibility
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class SearchResponse(BaseModel):
    """Search response"""

    results: List[SearchResult]
    total_count: int
    query: str
    technology_hint: Optional[str] = None
    execution_time_ms: int
    cache_hit: bool
    enrichment_triggered: bool
    error: Optional[str] = None  # Added for error reporting


# Configuration Models
class ConfigurationItem(BaseModel):
    """Configuration item"""

    key: str
    value: Any
    description: Optional[str] = None
    is_sensitive: bool = False


class ConfigurationResponse(BaseModel):
    """Configuration response"""

    items: List[ConfigurationItem]
    timestamp: datetime


class ConfigurationUpdateRequest(BaseModel):
    """Configuration update request"""

    key: str
    value: Any
    description: Optional[str] = None


# Health Models
class HealthStatus(BaseModel):
    """Health status"""

    service: str
    status: Literal["healthy", "degraded", "unhealthy"]
    response_time_ms: Optional[int] = None
    last_check: datetime
    detail: Optional[str] = None  # Simplified from details dict


class HealthResponse(BaseModel):
    """Health response"""

    overall_status: Literal["healthy", "degraded", "unhealthy"]
    services: List[HealthStatus]
    timestamp: datetime


# Feedback Models
class FeedbackRequest(BaseModel):
    """Feedback request"""

    content_id: str = Field(..., regex=r"^[a-zA-Z0-9\-_]+$")
    feedback_type: str = Field(
        ..., regex=r"^[a-zA-Z0-9_]+$"
    )  # Changed from Literal for flexibility
    rating: Optional[int] = Field(None, ge=1, le=5)
    comment: Optional[str] = Field(
        None, max_length=1000, regex=r'^[^<>&"\'\x00-\x1f]*$'
    )
    user_id: Optional[str] = Field(None, regex=r"^[a-zA-Z0-9\-_]+$")
    session_id: Optional[str] = Field(None, regex=r"^[a-zA-Z0-9\-_]+$")
    metadata: Optional[Dict[str, Any]] = None


class FeedbackResponse(BaseModel):
    """Feedback response - was missing"""

    feedback_id: str
    status: str
    message: str


# Signal/Usage Models
class SignalRequest(BaseModel):
    """Signal request"""

    content_id: str
    signal_type: str
    signal_value: Optional[float] = None  # Added for compatibility
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class UsageSignalRequest(BaseModel):
    """Usage signal request - was missing"""

    content_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    signal_type: str
    signal_strength: float = 1.0
    metadata: Optional[Dict[str, Any]] = None


# Content Models - were missing
class ContentIngestionRequest(BaseModel):
    """Content ingestion request"""

    source_url: str
    title: Optional[str] = None
    content: Optional[str] = None
    content_type: str = "document"
    technology: Optional[str] = None
    workspace: str = "default"
    metadata: Optional[Dict[str, Any]] = None


class ContentIngestionResponse(BaseModel):
    """Content ingestion response"""

    content_id: str
    status: str
    message: str


class ContentMetadata(BaseModel):
    """Content metadata"""

    content_id: str
    title: str
    source_url: str
    technology: Optional[str] = None
    content_type: str
    workspace: str
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContentCollection(BaseModel):
    """Content collection"""

    collection_id: str
    name: str
    description: str
    item_count: int
    created_at: datetime
    updated_at: datetime


class ContentStatsResponse(BaseModel):
    """Content statistics response"""

    total_documents: int
    by_technology: Dict[str, int]
    by_content_type: Dict[str, int]
    by_workspace: Dict[str, int]
    last_updated: datetime


class FeedbackStatsResponse(BaseModel):
    """Feedback statistics response"""

    total_feedback: int
    average_rating: float
    by_type: Dict[str, int]
    by_rating: Dict[str, int]
    recent_feedback: List[Dict[str, Any]]


# Upload Models
class UploadResponse(BaseModel):
    """Upload response"""

    upload_id: str
    status: str
    message: str


# Stats Models
class StatsResponse(BaseModel):
    """Stats response"""

    search_stats: Dict[str, Any]
    cache_stats: Dict[str, Any]
    content_stats: Dict[str, Any]
    system_stats: Dict[str, Any]
    timestamp: datetime


# Collection Models
class Collection(BaseModel):
    """Collection info"""

    slug: str
    name: str
    technology: str
    document_count: int
    last_updated: datetime
    is_active: bool = True


class CollectionsResponse(BaseModel):
    """Collections response"""

    collections: List[Collection]
    total_count: int


# Admin Models
class AdminContentItem(BaseModel):
    """Admin content item"""

    content_id: str
    title: str
    content_type: str
    technology: Optional[str] = None
    source_url: Optional[str] = None
    collection_name: str
    created_at: datetime
    last_updated: datetime
    size_bytes: Optional[int] = None
    status: str = "active"


class AdminSearchResponse(BaseModel):
    """Admin search response"""

    items: List[AdminContentItem]
    total_count: int
    page: int
    page_size: int
    has_more: bool
