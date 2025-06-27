"""Custom exception hierarchy for Web UI Service."""

class WebUIError(Exception):
    """Base exception for all Web UI Service errors."""

class ConfigurationError(WebUIError):
    """Raised when there is a configuration-related error."""

class DatabaseError(WebUIError):
    """Raised when a database operation fails."""

class AuthenticationError(WebUIError):
    """Raised when authentication fails."""

class AuthorizationError(WebUIError):
    """Raised when authorization fails."""

class ValidationError(WebUIError):
    """Raised when input validation fails."""

class NotFoundError(WebUIError):
    """Raised when a requested resource is not found."""

class ServiceUnavailableError(WebUIError):
    """Raised when a dependent service is unavailable."""

class RateLimitError(WebUIError):
    """Raised when a rate limit is exceeded."""

# TODO: IMPLEMENTATION ENGINEER - Add additional exceptions as needed