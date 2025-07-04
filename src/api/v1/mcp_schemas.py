"""
MCP Configuration API Schemas
=============================

Pydantic models for MCP (Model Context Protocol) configuration endpoints.
Integrates MCP provider management with existing API infrastructure.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Literal
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# MCP Provider Configuration Models
class ProviderConfig(BaseModel):
    """Configuration for an external search provider."""
    
    provider_id: str = Field(..., description="Unique provider identifier")
    provider_type: str = Field(..., description="Provider type (brave, google, duckduckgo, etc.)")
    enabled: bool = Field(True, description="Whether provider is enabled")
    api_key: Optional[str] = Field(None, description="API key for the provider")
    api_endpoint: Optional[str] = Field(None, description="Custom API endpoint URL")
    priority: int = Field(1, ge=1, le=10, description="Provider priority (1=highest)")
    max_results: int = Field(10, ge=1, le=50, description="Maximum results per request")
    timeout_seconds: float = Field(3.0, ge=0.5, le=10.0, description="Request timeout")
    rate_limit_per_minute: int = Field(60, ge=1, le=1000, description="Rate limit")
    custom_headers: Dict[str, str] = Field(default_factory=dict, description="Custom HTTP headers")
    custom_params: Dict[str, Any] = Field(default_factory=dict, description="Custom parameters")


class ProviderCapability(BaseModel):
    """Provider capability information."""
    
    feature: str = Field(..., description="Capability feature name")
    supported: bool = Field(..., description="Whether feature is supported")
    description: str = Field(..., description="Feature description")


class ProviderHealth(BaseModel):
    """Provider health status."""
    
    provider_id: str = Field(..., description="Provider identifier")
    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Health status")
    last_check: datetime = Field(..., description="Last health check timestamp")
    response_time_ms: Optional[int] = Field(None, description="Last response time")
    error_message: Optional[str] = Field(None, description="Error message if unhealthy")
    success_rate: Optional[float] = Field(None, ge=0.0, le=1.0, description="Recent success rate")


class ProviderStats(BaseModel):
    """Provider performance statistics."""
    
    provider_id: str = Field(..., description="Provider identifier")
    total_requests: int = Field(..., description="Total requests made")
    successful_requests: int = Field(..., description="Successful requests")
    failed_requests: int = Field(..., description="Failed requests")
    avg_response_time_ms: float = Field(..., description="Average response time")
    last_24h_requests: int = Field(..., description="Requests in last 24 hours")
    circuit_breaker_open: bool = Field(..., description="Circuit breaker status")


# MCP Search Configuration Models
class SearchConfig(BaseModel):
    """MCP search configuration settings."""
    
    enable_external_search: bool = Field(True, description="Enable external search providers")
    enable_hedged_requests: bool = Field(True, description="Enable hedged request pattern")
    hedged_delay_seconds: float = Field(0.2, ge=0.1, le=1.0, description="Hedged request delay")
    max_concurrent_providers: int = Field(3, ge=1, le=5, description="Max concurrent providers")
    external_search_threshold: float = Field(0.6, ge=0.0, le=1.0, description="Quality threshold for external search")
    cache_ttl_seconds: int = Field(3600, ge=300, le=86400, description="Cache TTL")
    enable_performance_monitoring: bool = Field(True, description="Enable performance monitoring")


class CacheConfig(BaseModel):
    """Cache configuration for MCP search."""
    
    l1_cache_size: int = Field(100, ge=10, le=1000, description="L1 cache size")
    l2_cache_ttl: int = Field(3600, ge=300, le=86400, description="L2 cache TTL")
    compression_threshold: int = Field(1024, ge=512, le=10240, description="Compression threshold bytes")
    enable_compression: bool = Field(True, description="Enable cache value compression")
    enable_stats: bool = Field(True, description="Enable cache statistics")


# Request/Response Models
class CreateProviderRequest(BaseModel):
    """Request to create a new external search provider."""
    
    config: ProviderConfig = Field(..., description="Provider configuration")


class UpdateProviderRequest(BaseModel):
    """Request to update an existing provider."""
    
    enabled: Optional[bool] = Field(None, description="Enable/disable provider")
    priority: Optional[int] = Field(None, ge=1, le=10, description="Provider priority")
    max_results: Optional[int] = Field(None, ge=1, le=50, description="Max results")
    timeout_seconds: Optional[float] = Field(None, ge=0.5, le=10.0, description="Timeout")
    custom_headers: Optional[Dict[str, str]] = Field(None, description="Custom headers")
    custom_params: Optional[Dict[str, Any]] = Field(None, description="Custom parameters")


class ProviderResponse(BaseModel):
    """Response containing provider information."""
    
    provider_id: str = Field(..., description="Provider identifier")
    config: ProviderConfig = Field(..., description="Provider configuration")
    capabilities: List[ProviderCapability] = Field(..., description="Provider capabilities")
    health: ProviderHealth = Field(..., description="Current health status")
    stats: ProviderStats = Field(..., description="Performance statistics")


class ProvidersListResponse(BaseModel):
    """Response containing list of all providers."""
    
    providers: List[ProviderResponse] = Field(..., description="List of providers")
    total_count: int = Field(..., description="Total number of providers")
    healthy_count: int = Field(..., description="Number of healthy providers")


class SearchConfigRequest(BaseModel):
    """Request to update search configuration."""
    
    config: SearchConfig = Field(..., description="Search configuration")


class SearchConfigResponse(BaseModel):
    """Response containing current search configuration."""
    
    config: SearchConfig = Field(..., description="Current search configuration")
    cache_config: CacheConfig = Field(..., description="Cache configuration")
    last_updated: datetime = Field(..., description="Last configuration update")


class PerformanceStats(BaseModel):
    """MCP search performance statistics."""
    
    total_searches: int = Field(..., description="Total external searches")
    cache_hits: int = Field(..., description="Cache hits")
    cache_misses: int = Field(..., description="Cache misses")
    avg_response_time_ms: float = Field(..., description="Average response time")
    hedged_requests: int = Field(..., description="Number of hedged requests")
    circuit_breaks: int = Field(..., description="Circuit breaker activations")
    provider_stats: List[ProviderStats] = Field(..., description="Per-provider statistics")


class PerformanceStatsResponse(BaseModel):
    """Response containing performance statistics."""
    
    stats: PerformanceStats = Field(..., description="Performance statistics")
    collection_period_hours: int = Field(..., description="Statistics collection period")
    last_reset: datetime = Field(..., description="Last statistics reset")


# Search Enhancement Models
class ExternalSearchRequest(BaseModel):
    """Request for external search enhancement."""
    
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    technology_hint: Optional[str] = Field(None, description="Technology context")
    max_results: int = Field(10, ge=1, le=50, description="Maximum results")
    provider_ids: Optional[List[str]] = Field(None, description="Specific providers to use")
    force_external: bool = Field(False, description="Force external search even with good internal results")


class ExternalSearchResult(BaseModel):
    """External search result item."""
    
    title: str = Field(..., description="Result title")
    url: str = Field(..., description="Result URL")
    snippet: str = Field(..., description="Content snippet")
    provider: str = Field(..., description="Source provider")
    content_type: str = Field(..., description="Content type")
    published_date: Optional[datetime] = Field(None, description="Publication date")
    relevance_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Relevance score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific metadata including TTL")


class ExternalSearchResponse(BaseModel):
    """Response from external search enhancement."""
    
    results: List[ExternalSearchResult] = Field(..., description="External search results")
    total_results: int = Field(..., description="Total results found")
    providers_used: List[str] = Field(..., description="Providers that returned results")
    execution_time_ms: int = Field(..., description="Total execution time")
    cache_hit: bool = Field(..., description="Whether results were cached")


# Test and Validation Models
class ProviderTestRequest(BaseModel):
    """Request to test a provider configuration."""
    
    provider_id: str = Field(..., description="Provider to test")
    test_query: str = Field("test", description="Test query to use")


class ProviderTestResponse(BaseModel):
    """Response from provider test."""
    
    provider_id: str = Field(..., description="Tested provider")
    success: bool = Field(..., description="Test success status")
    response_time_ms: int = Field(..., description="Test response time")
    results_count: int = Field(..., description="Number of results returned")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class ConfigValidationResponse(BaseModel):
    """Response from configuration validation."""
    
    valid: bool = Field(..., description="Configuration validity")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    providers_tested: int = Field(..., description="Number of providers tested")
    healthy_providers: int = Field(..., description="Number of healthy providers")