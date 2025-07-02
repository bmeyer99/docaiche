"""
Data Models for External Search Providers
==========================================

Models for search operations, health monitoring, and provider capabilities.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class HealthStatus(str, Enum):
    """Provider health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class SearchResultType(str, Enum):
    """Types of search results."""
    WEB_PAGE = "web_page"
    DOCUMENTATION = "documentation"
    CODE_REPOSITORY = "code_repository"
    FORUM = "forum"
    BLOG_POST = "blog_post"
    TUTORIAL = "tutorial"
    VIDEO = "video"
    OTHER = "other"


class ProviderType(str, Enum):
    """Supported search provider types."""
    BRAVE = "brave"
    GOOGLE = "google"
    SEARXNG = "searxng"
    PERPLEXITY = "perplexity"
    KAGI = "kagi"
    CUSTOM = "custom"


class SearchOptions(BaseModel):
    """
    Options for search requests across all providers.
    
    Provides a unified interface for search parameters that
    providers can adapt to their specific APIs.
    """
    
    query: str = Field(
        description="Search query string"
    )
    
    max_results: int = Field(
        default=20,
        description="Maximum number of results to return",
        ge=1,
        le=100
    )
    
    language: Optional[str] = Field(
        default="en",
        description="Language code for results (ISO 639-1)"
    )
    
    country: Optional[str] = Field(
        default=None,
        description="Country code for localized results (ISO 3166-1)"
    )
    
    date_range: Optional[str] = Field(
        default=None,
        description="Date range filter (e.g., 'day', 'week', 'month', 'year')"
    )
    
    safe_search: bool = Field(
        default=True,
        description="Enable safe search filtering"
    )
    
    include_types: Optional[List[SearchResultType]] = Field(
        default=None,
        description="Specific result types to include"
    )
    
    exclude_domains: Optional[List[str]] = Field(
        default=None,
        description="Domains to exclude from results"
    )
    
    site_search: Optional[str] = Field(
        default=None,
        description="Limit search to specific site/domain"
    )
    
    timeout_seconds: float = Field(
        default=5.0,
        description="Request timeout",
        ge=1.0,
        le=30.0
    )
    
    custom_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific parameters"
    )


class SearchResult(BaseModel):
    """
    Standardized search result across all providers.
    
    Provides consistent format regardless of source provider.
    """
    
    title: str = Field(
        description="Result title"
    )
    
    url: str = Field(
        description="Result URL"
    )
    
    snippet: str = Field(
        description="Text snippet/description"
    )
    
    content_type: SearchResultType = Field(
        default=SearchResultType.WEB_PAGE,
        description="Type of content"
    )
    
    source_domain: str = Field(
        description="Source domain extracted from URL"
    )
    
    published_date: Optional[datetime] = Field(
        default=None,
        description="Publication date if available"
    )
    
    author: Optional[str] = Field(
        default=None,
        description="Author if available"
    )
    
    language: Optional[str] = Field(
        default=None,
        description="Content language"
    )
    
    relevance_score: float = Field(
        default=1.0,
        description="Provider relevance score normalized to 0-1",
        ge=0.0,
        le=1.0
    )
    
    provider_rank: int = Field(
        description="Original ranking from provider"
    )
    
    thumbnail_url: Optional[str] = Field(
        default=None,
        description="Thumbnail image URL if available"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider-specific metadata"
    )
    
    @validator('source_domain', pre=True, always=True)
    def extract_domain(cls, v, values):
        """Extract domain from URL if not provided."""
        if v:
            return v
        if 'url' in values:
            from urllib.parse import urlparse
            parsed = urlparse(values['url'])
            return parsed.netloc
        return "unknown"


class SearchResults(BaseModel):
    """
    Collection of search results with metadata.
    
    Contains results and execution information.
    """
    
    results: List[SearchResult] = Field(
        default_factory=list,
        description="List of search results"
    )
    
    total_results: Optional[int] = Field(
        default=None,
        description="Total results available (if provided by API)"
    )
    
    execution_time_ms: int = Field(
        description="Search execution time in milliseconds"
    )
    
    provider: str = Field(
        description="Provider that generated results"
    )
    
    query: str = Field(
        description="Original search query"
    )
    
    error: Optional[str] = Field(
        default=None,
        description="Error message if search failed"
    )
    
    truncated: bool = Field(
        default=False,
        description="Whether results were truncated to max_results"
    )
    
    api_calls_made: int = Field(
        default=1,
        description="Number of API calls made"
    )
    
    cache_hit: bool = Field(
        default=False,
        description="Whether results came from provider cache"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional provider metadata"
    )


class ProviderCapabilities(BaseModel):
    """
    Describes what a search provider supports.
    
    Used for provider selection and feature availability.
    """
    
    provider_type: ProviderType = Field(
        description="Type of provider"
    )
    
    supports_date_filtering: bool = Field(
        default=False,
        description="Supports date range filtering"
    )
    
    supports_site_search: bool = Field(
        default=False,
        description="Supports limiting to specific sites"
    )
    
    supports_safe_search: bool = Field(
        default=True,
        description="Supports safe search filtering"
    )
    
    supports_pagination: bool = Field(
        default=False,
        description="Supports result pagination"
    )
    
    supports_language_filter: bool = Field(
        default=True,
        description="Supports language filtering"
    )
    
    supports_country_filter: bool = Field(
        default=False,
        description="Supports country-specific results"
    )
    
    max_results_per_request: int = Field(
        default=50,
        description="Maximum results in single request"
    )
    
    rate_limit_requests_per_minute: Optional[int] = Field(
        default=None,
        description="API rate limit if known"
    )
    
    requires_api_key: bool = Field(
        default=True,
        description="Whether API key is required"
    )
    
    supports_batch_queries: bool = Field(
        default=False,
        description="Can handle multiple queries in one request"
    )
    
    result_types: List[SearchResultType] = Field(
        default_factory=lambda: [SearchResultType.WEB_PAGE],
        description="Types of results this provider returns"
    )
    
    special_features: List[str] = Field(
        default_factory=list,
        description="Provider-specific special features"
    )
    
    estimated_latency_ms: int = Field(
        default=500,
        description="Typical response latency"
    )
    
    reliability_score: float = Field(
        default=0.95,
        description="Historical reliability (0-1)",
        ge=0.0,
        le=1.0
    )


class RateLimitInfo(BaseModel):
    """
    Current rate limit status for a provider.
    
    Tracks API usage and limits.
    """
    
    requests_made: int = Field(
        default=0,
        description="Requests made in current window"
    )
    
    requests_limit: Optional[int] = Field(
        default=None,
        description="Maximum requests allowed"
    )
    
    window_start: datetime = Field(
        default_factory=datetime.utcnow,
        description="Start of current rate limit window"
    )
    
    window_duration_seconds: int = Field(
        default=60,
        description="Rate limit window duration"
    )
    
    retry_after: Optional[datetime] = Field(
        default=None,
        description="When to retry if rate limited"
    )
    
    is_limited: bool = Field(
        default=False,
        description="Currently rate limited"
    )
    
    def remaining_requests(self) -> Optional[int]:
        """Calculate remaining requests in window."""
        if self.requests_limit is None:
            return None
        return max(0, self.requests_limit - self.requests_made)
    
    def reset_time(self) -> datetime:
        """Calculate when rate limit window resets."""
        from datetime import timedelta
        return self.window_start + timedelta(seconds=self.window_duration_seconds)


class CostInfo(BaseModel):
    """
    Usage and cost tracking for paid providers.
    
    Monitors API usage costs and budgets.
    """
    
    requests_this_month: int = Field(
        default=0,
        description="Total requests this month"
    )
    
    cost_per_request: Optional[float] = Field(
        default=None,
        description="Cost per API request in USD"
    )
    
    monthly_budget: Optional[float] = Field(
        default=None,
        description="Monthly budget limit in USD"
    )
    
    total_cost_this_month: float = Field(
        default=0.0,
        description="Total cost this month in USD"
    )
    
    free_tier_remaining: Optional[int] = Field(
        default=None,
        description="Free tier requests remaining"
    )
    
    billing_period_start: datetime = Field(
        default_factory=lambda: datetime.utcnow().replace(day=1),
        description="Start of billing period"
    )
    
    overage_allowed: bool = Field(
        default=False,
        description="Whether to allow exceeding budget"
    )
    
    def budget_remaining(self) -> Optional[float]:
        """Calculate remaining budget."""
        if self.monthly_budget is None:
            return None
        return max(0.0, self.monthly_budget - self.total_cost_this_month)
    
    def is_budget_exceeded(self) -> bool:
        """Check if budget is exceeded."""
        if self.monthly_budget is None:
            return False
        return self.total_cost_this_month > self.monthly_budget


class HealthCheck(BaseModel):
    """
    Health check result for a provider.
    
    Contains detailed health status information.
    """
    
    status: HealthStatus = Field(
        description="Overall health status"
    )
    
    response_time_ms: Optional[int] = Field(
        default=None,
        description="Health check response time"
    )
    
    last_success: Optional[datetime] = Field(
        default=None,
        description="Last successful request"
    )
    
    last_failure: Optional[datetime] = Field(
        default=None,
        description="Last failed request"
    )
    
    consecutive_failures: int = Field(
        default=0,
        description="Number of consecutive failures"
    )
    
    error_rate_percent: float = Field(
        default=0.0,
        description="Error rate in last hour",
        ge=0.0,
        le=100.0
    )
    
    circuit_breaker_state: str = Field(
        default="closed",
        description="Circuit breaker state (closed/open/half-open)"
    )
    
    rate_limit_status: Optional[RateLimitInfo] = Field(
        default=None,
        description="Current rate limit information"
    )
    
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional health details"
    )
    
    checked_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When health check was performed"
    )
    
    def is_healthy(self) -> bool:
        """Check if provider is healthy enough to use."""
        return self.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
    
    def should_circuit_break(self, threshold: int = 5) -> bool:
        """Check if circuit breaker should open."""
        return self.consecutive_failures >= threshold


class ProviderConfig(BaseModel):
    """
    Base configuration for search providers.
    
    Common configuration fields across all providers.
    """
    
    provider_id: str = Field(
        description="Unique identifier for this provider instance"
    )
    
    provider_type: ProviderType = Field(
        description="Type of provider (brave, google, etc.)"
    )
    
    enabled: bool = Field(
        default=True,
        description="Whether provider is enabled"
    )
    
    api_key: Optional[str] = Field(
        default=None,
        description="API key for authentication"
    )
    
    base_url: Optional[str] = Field(
        default=None,
        description="Base URL for API (if customizable)"
    )
    
    timeout_seconds: float = Field(
        default=5.0,
        description="Default request timeout",
        ge=1.0,
        le=30.0
    )
    
    max_retries: int = Field(
        default=2,
        description="Maximum retry attempts",
        ge=0,
        le=5
    )
    
    priority: int = Field(
        default=100,
        description="Provider priority (lower = higher priority)",
        ge=0
    )
    
    custom_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Custom HTTP headers"
    )
    
    proxy_url: Optional[str] = Field(
        default=None,
        description="HTTP proxy URL if needed"
    )
    
    circuit_breaker_threshold: int = Field(
        default=3,
        description="Failures before circuit opens",
        ge=1,
        le=10
    )
    
    circuit_breaker_timeout: int = Field(
        default=60,
        description="Seconds before circuit breaker resets",
        ge=10,
        le=600
    )
    
    @validator('api_key')
    def validate_api_key(cls, v):
        """Ensure API key is not empty if provided."""
        if v is not None and not v.strip():
            raise ValueError("API key cannot be empty")
        return v