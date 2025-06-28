"""
Custom Exceptions for AnythingLLM Client - PRD-004 ALM-001
Exception hierarchy for comprehensive error handling and proper HTTP status mapping

These exceptions provide structured error handling for the AnythingLLM client
with proper categorization for different failure modes and circuit breaker integration.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AnythingLLMError(Exception):
    """
    Base exception for AnythingLLM client errors.

    Provides common structure for all AnythingLLM-related exceptions
    with optional HTTP status code mapping and detailed error context.
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_context: Optional[dict] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_context = error_context or {}

    def __str__(self) -> str:
        if self.status_code:
            return f"AnythingLLM Error ({self.status_code}): {self.message}"
        return f"AnythingLLM Error: {self.message}"


class AnythingLLMConnectionError(AnythingLLMError):
    """
    Connection-related errors for AnythingLLM service.

    Raised when the client cannot establish or maintain a connection
    to the AnythingLLM service, including network timeouts and connection failures.
    """

    def __init__(self, message: str, error_context: Optional[dict] = None):
        super().__init__(
            message=f"Connection failed: {message}",
            status_code=503,  # Service Unavailable
            error_context=error_context,
        )


class AnythingLLMAuthenticationError(AnythingLLMError):
    """
    Authentication failures for AnythingLLM API.

    Raised when API key authentication fails or when the client
    receives authentication-related HTTP error responses.
    """

    def __init__(self, message: str, error_context: Optional[dict] = None):
        super().__init__(
            message=f"Authentication failed: {message}",
            status_code=401,  # Unauthorized
            error_context=error_context,
        )


class AnythingLLMRateLimitError(AnythingLLMError):
    """
    Rate limiting errors from AnythingLLM API.

    Raised when the client exceeds the API rate limits imposed
    by the AnythingLLM service, including retry-after information.
    """

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        error_context: Optional[dict] = None,
    ):
        super().__init__(
            message=f"Rate limit exceeded: {message}",
            status_code=429,  # Too Many Requests
            error_context=error_context,
        )
        self.retry_after = retry_after


class AnythingLLMWorkspaceError(AnythingLLMError):
    """
    Workspace-related errors for AnythingLLM operations.

    Raised when workspace operations fail, including workspace
    not found, creation failures, or access permission issues.
    """

    def __init__(self, message: str, workspace_slug: Optional[str] = None):
        super().__init__(
            message=f"Workspace error: {message}",
            status_code=404 if "not found" in message.lower() else 400,
            error_context=(
                {"workspace_slug": workspace_slug} if workspace_slug else None
            ),
        )
        self.workspace_slug = workspace_slug


class AnythingLLMDocumentError(AnythingLLMError):
    """
    Document upload and management errors.

    Raised when document operations fail, including upload failures,
    document processing errors, or document deletion issues.
    """

    def __init__(
        self,
        message: str,
        document_id: Optional[str] = None,
        chunk_id: Optional[str] = None,
    ):
        super().__init__(
            message=f"Document error: {message}",
            status_code=400,  # Bad Request
            error_context=(
                {"document_id": document_id, "chunk_id": chunk_id}
                if document_id or chunk_id
                else None
            ),
        )
        self.document_id = document_id
        self.chunk_id = chunk_id


class AnythingLLMCircuitBreakerError(AnythingLLMError):
    """
    Circuit breaker state errors.

    Raised when the circuit breaker is open and requests are being
    rejected to prevent cascading failures to the AnythingLLM service.
    """

    def __init__(self, message: str = "Circuit breaker is open"):
        super().__init__(
            message=f"Circuit breaker: {message}",
            status_code=503,  # Service Unavailable
            error_context={"circuit_breaker_open": True},
        )


class WebScrapingError(Exception):
    """
    Exception for web scraping errors (PRD-007).
    Includes HTTP status code and error context for structured error handling.
    """

    def __init__(
        self, message: str, status_code: int = 500, error_context: dict = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_context = error_context or {}

    def __str__(self):
        return f"WebScrapingError({self.status_code}): {self.message}"


class GitHubClientError(Exception):
    """
    Exception for GitHub API client errors (PRD-006).
    Includes HTTP status code and error context for structured error handling.
    """

    def __init__(
        self, message: str, status_code: int = 500, error_context: dict = None
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_context = error_context or {}

    def __str__(self):
        return f"GitHubClientError({self.status_code}): {self.message}"


class CircuitBreakerError(Exception):
    """
    Exception for open circuit breaker state (PRD-006).
    Raised when the circuit breaker is open and API calls are blocked.
    """

    def __init__(self, message: str = "Circuit breaker is open"):
        super().__init__(message)
        self.message = message
        self.status_code = 503

    def __str__(self):
        return f"CircuitBreakerError({self.status_code}): {self.message}"
