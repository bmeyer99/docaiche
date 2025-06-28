"""
Client modules for external service integrations - PRD-004 through PRD-007
External API clients for AnythingLLM, LLM providers, GitHub, and web scraping

This package contains all client implementations for external services
following async patterns with proper error handling and circuit breakers.
"""

from .anythingllm import AnythingLLMClient
from .github import GitHubClient
from .exceptions import (
    AnythingLLMError,
    AnythingLLMConnectionError,
    AnythingLLMAuthenticationError,
    AnythingLLMRateLimitError,
    AnythingLLMWorkspaceError,
    AnythingLLMDocumentError,
    AnythingLLMCircuitBreakerError,
)

__all__ = [
    "AnythingLLMClient",
    "GitHubClient",
    "AnythingLLMError",
    "AnythingLLMConnectionError",
    "AnythingLLMAuthenticationError",
    "AnythingLLMRateLimitError",
    "AnythingLLMWorkspaceError",
    "AnythingLLMDocumentError",
    "AnythingLLMCircuitBreakerError",
]
