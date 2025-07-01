"""
External Search Providers Module
================================

Pluggable framework for external search providers with health
monitoring, circuit breakers, and standardized interfaces.
"""

from .base import SearchProvider
from .registry import ProviderRegistry
from .health import ProviderHealthMonitor
from .models import (
    SearchOptions,
    SearchResult,
    SearchResults,
    ProviderCapabilities,
    HealthStatus,
    RateLimitInfo,
    CostInfo,
    HealthCheck
)

__all__ = [
    "SearchProvider",
    "ProviderRegistry",
    "ProviderHealthMonitor",
    "SearchOptions",
    "SearchResult",
    "SearchResults",
    "ProviderCapabilities",
    "HealthStatus",
    "RateLimitInfo",
    "CostInfo",
    "HealthCheck"
]