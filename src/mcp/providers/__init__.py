"""
External Search Providers Module
================================

Pluggable framework for external search providers with health
monitoring, circuit breakers, and standardized interfaces.
"""

from .base import SearchProvider
from .registry import ProviderRegistry, SelectionStrategy
from .health import ProviderHealthMonitor, HealthTrend
from .models import (
    SearchOptions,
    SearchResult,
    SearchResults,
    ProviderCapabilities,
    HealthStatus,
    HealthCheck,
    RateLimitInfo,
    CostInfo,
    ProviderConfig,
    ProviderType,
    SearchResultType
)
from .schemas import (
    get_provider_schema,
    validate_provider_config,
    PROVIDER_SCHEMAS
)

# Import implementations
from .implementations import (
    BraveSearchProvider,
    GoogleSearchProvider,
    BingSearchProvider,
    DuckDuckGoSearchProvider,
    SearXNGSearchProvider,
    PROVIDER_CLASSES
)

__all__ = [
    # Base classes
    "SearchProvider",
    "ProviderRegistry",
    "ProviderHealthMonitor",
    
    # Models
    "SearchOptions",
    "SearchResult",
    "SearchResults",
    "ProviderCapabilities",
    "HealthStatus",
    "HealthCheck",
    "RateLimitInfo",
    "CostInfo",
    "ProviderConfig",
    "ProviderType",
    "SearchResultType",
    
    # Enums
    "SelectionStrategy",
    "HealthTrend",
    
    # Schema functions
    "get_provider_schema",
    "validate_provider_config",
    "PROVIDER_SCHEMAS",
    
    # Implementations
    "BraveSearchProvider",
    "GoogleSearchProvider",
    "BingSearchProvider",
    "DuckDuckGoSearchProvider",
    "SearXNGSearchProvider",
    "PROVIDER_CLASSES"
]