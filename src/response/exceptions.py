"""Custom exceptions for the Response Generation Engine (PRD-011).

Defines error types for response generation, template handling, and validation.
"""

class ResponseGenerationError(Exception):
    """Raised when response generation fails irrecoverably."""
    pass

class TemplateNotFoundError(Exception):
    """Raised when a requested template cannot be found."""
    pass

class TemplateRenderError(Exception):
    """Raised when template rendering fails."""
    pass

class ResponseValidationError(Exception):
    """Raised when response validation fails."""
    pass