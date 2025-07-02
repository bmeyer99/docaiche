"""
Client modules for external service integrations - PRD-004 through PRD-007
External API clients for Weaviate, LLM providers, GitHub, and web scraping

This package contains all client implementations for external services
following async patterns with proper error handling and circuit breakers.
"""

from .weaviate_client import WeaviateVectorClient
from .github import GitHubClient
from .exceptions import (
    WeaviateError,
    WeaviateConnectionError,
    WeaviateAuthenticationError,
    WeaviateRateLimitError,
    WeaviateWorkspaceError,
    WeaviateDocumentError,
    WeaviateCircuitBreakerError,
)

__all__ = [
    "WeaviateVectorClient",
    "GitHubClient",
    "WeaviateError",
    "WeaviateConnectionError",
    "WeaviateAuthenticationError",
    "WeaviateRateLimitError",
    "WeaviateWorkspaceError",
    "WeaviateDocumentError",
    "WeaviateCircuitBreakerError",
]
