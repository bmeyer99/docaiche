"""
MCP Exception Hierarchy
=======================

Comprehensive exception handling for MCP operations following structured
error patterns with proper error codes and context preservation.

This module implements RFC 7807 Problem Details format for consistent
error responses across all MCP operations.
"""

from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class MCPException(Exception):
    """
    Base exception for all MCP-related errors.
    
    Implements RFC 7807 Problem Details format with structured error information
    including error codes, context details, and correlation IDs for debugging.
    
    Attributes:
        message: Human-readable error description
        error_code: Machine-readable error identifier  
        status_code: HTTP status code equivalent
        details: Additional error context and debugging information
        correlation_id: Request correlation ID for tracing
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = None,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.status_code = status_code
        self.details = details or {}
        self.correlation_id = correlation_id
        
        # Log exception creation for debugging
        logger.warning(
            f"MCP Exception created: {self.error_code} - {message}",
            extra={
                "error_code": self.error_code,
                "status_code": self.status_code,
                "correlation_id": self.correlation_id,
                "details": self.details
            }
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to RFC 7807 Problem Details format.
        
        Returns:
            Dictionary containing structured error information
        """
        return {
            "type": f"urn:docaiche:mcp:error:{self.error_code.lower()}",
            "title": self.__class__.__name__,
            "status": self.status_code,
            "detail": self.message,
            "instance": f"urn:correlation:{self.correlation_id}" if self.correlation_id else None,
            "error_code": self.error_code,
            "trace_id": self.correlation_id,
            "details": self.details
        }


class AuthenticationError(MCPException):
    """
    Authentication-related errors for OAuth 2.1 and security violations.
    
    Raised when authentication fails, tokens are invalid, or security
    requirements are not met according to 2025 MCP security specifications.
    """
    
    def __init__(
        self,
        message: str = "Authentication failed",
        error_code: str = "AUTH_FAILED",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=401,
            details=details,
            correlation_id=correlation_id
        )


class AuthorizationError(MCPException):
    """
    Authorization-related errors for access control and permissions.
    
    Raised when authenticated users lack sufficient permissions for
    requested operations or violate resource access policies.
    """
    
    def __init__(
        self,
        message: str = "Access denied - insufficient permissions",
        error_code: str = "ACCESS_DENIED", 
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=403,
            details=details,
            correlation_id=correlation_id
        )


class ValidationError(MCPException):
    """
    Input validation and schema compliance errors.
    
    Raised when request data fails validation, violates MCP schemas,
    or contains malformed or dangerous content.
    """
    
    def __init__(
        self,
        message: str = "Input validation failed",
        error_code: str = "VALIDATION_FAILED",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=422,
            details=details,
            correlation_id=correlation_id
        )


class TransportError(MCPException):
    """
    Transport layer communication errors.
    
    Raised when MCP transport mechanisms fail, including HTTP streaming
    errors, connection failures, and protocol violations.
    """
    
    def __init__(
        self,
        message: str = "Transport communication failed",
        error_code: str = "TRANSPORT_ERROR",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=502,
            details=details,
            correlation_id=correlation_id
        )


class ToolExecutionError(MCPException):
    """
    MCP tool execution failures.
    
    Raised when MCP tools fail to execute properly, including search
    failures, ingestion errors, and tool-specific operational issues.
    """
    
    def __init__(
        self,
        message: str = "Tool execution failed",
        error_code: str = "TOOL_EXECUTION_FAILED",
        tool_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        enhanced_details = details or {}
        if tool_name:
            enhanced_details["tool_name"] = tool_name
            
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=500,
            details=enhanced_details,
            correlation_id=correlation_id
        )


class ResourceError(MCPException):
    """
    MCP resource access and management errors.
    
    Raised when MCP resources cannot be accessed, are unavailable,
    or fail to provide expected data.
    """
    
    def __init__(
        self,
        message: str = "Resource access failed",
        error_code: str = "RESOURCE_ERROR",
        resource_uri: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        enhanced_details = details or {}
        if resource_uri:
            enhanced_details["resource_uri"] = resource_uri
            
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=500,
            details=enhanced_details,
            correlation_id=correlation_id
        )


class ConfigurationError(MCPException):
    """
    Configuration and setup errors.
    
    Raised when MCP server configuration is invalid, missing required
    settings, or contains incompatible configuration values.
    """
    
    def __init__(
        self,
        message: str = "Configuration error",
        error_code: str = "CONFIG_ERROR",
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        enhanced_details = details or {}
        if config_key:
            enhanced_details["config_key"] = config_key
            
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=500,
            details=enhanced_details,
            correlation_id=correlation_id
        )


class ServiceError(MCPException):
    """
    External service integration errors.
    
    Raised when external services (HTTP APIs, databases, etc.) fail
    or are unavailable during MCP operations.
    """
    
    def __init__(
        self,
        message: str = "Service integration error",
        error_code: str = "SERVICE_ERROR",
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        enhanced_details = details or {}
        if service_name:
            enhanced_details["service_name"] = service_name
            
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=503,
            details=enhanced_details,
            correlation_id=correlation_id
        )


class RateLimitError(MCPException):
    """
    Rate limiting and quota exceeded errors.
    
    Raised when clients exceed configured rate limits or quotas
    for MCP operations, tools, or resources.
    """
    
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        error_code: str = "RATE_LIMIT_EXCEEDED",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        enhanced_details = details or {}
        if retry_after:
            enhanced_details["retry_after_seconds"] = retry_after
            
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=429,
            details=enhanced_details,
            correlation_id=correlation_id
        )


class ConsentError(MCPException):
    """
    User consent and permission errors.
    
    Raised when operations require user consent that has not been
    obtained or when consent validation fails.
    """
    
    def __init__(
        self,
        message: str = "User consent required",
        error_code: str = "CONSENT_REQUIRED",
        required_consent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        enhanced_details = details or {}
        if required_consent:
            enhanced_details["required_consent"] = required_consent
            
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=403,
            details=enhanced_details,
            correlation_id=correlation_id
        )


# TODO: IMPLEMENTATION ENGINEER - Add specialized exception handlers for:
# 1. Circuit breaker states and fallback mechanisms
# 2. External service timeout and retry logic
# 3. Content ingestion and processing errors
# 4. Vector database and search infrastructure failures
# 5. Audit logging and compliance validation errors

def create_error_response(
    exception: MCPException,
    include_stack_trace: bool = False
) -> Dict[str, Any]:
    """
    Create standardized error response from MCP exception.
    
    Args:
        exception: MCP exception to convert
        include_stack_trace: Whether to include stack trace (dev environments only)
        
    Returns:
        RFC 7807 compliant error response dictionary
    """
    response = exception.to_dict()
    
    if include_stack_trace:
        import traceback
        response["stack_trace"] = traceback.format_exc()
        
    return response


def handle_unexpected_error(
    error: Exception,
    operation: str,
    correlation_id: Optional[str] = None
) -> MCPException:
    """
    Convert unexpected errors to structured MCP exceptions.
    
    Args:
        error: Original exception
        operation: Description of failed operation
        correlation_id: Request correlation ID
        
    Returns:
        Structured MCP exception with error context
    """
    logger.error(
        f"Unexpected error in {operation}: {str(error)}",
        extra={
            "operation": operation,
            "error_type": type(error).__name__,
            "correlation_id": correlation_id
        },
        exc_info=True
    )
    
    return MCPException(
        message=f"Unexpected error in {operation}: {str(error)}",
        error_code="UNEXPECTED_ERROR",
        status_code=500,
        details={
            "operation": operation,
            "original_error": str(error),
            "error_type": type(error).__name__
        },
        correlation_id=correlation_id
    )