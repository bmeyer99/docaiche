"""
MCP Search Exception Hierarchy
==============================

Comprehensive exception framework for the MCP search system with
structured error codes and detailed context.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime


class MCPSearchError(Exception):
    """
    Base exception for all MCP search errors.
    
    Provides structured error information with codes, context,
    and recovery suggestions.
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "MCP_ERROR",
        details: Optional[Dict[str, Any]] = None,
        recovery_suggestion: Optional[str] = None
    ):
        """
        Initialize MCP search error.
        
        Args:
            message: Human-readable error message
            error_code: Structured error code for programmatic handling
            details: Additional error context and metadata
            recovery_suggestion: Suggested action for recovery
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.recovery_suggestion = recovery_suggestion
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "recovery_suggestion": self.recovery_suggestion,
            "timestamp": self.timestamp.isoformat()
        }
    
    def __str__(self) -> str:
        """String representation with error code."""
        return f"[{self.error_code}] {self.message}"


class QueueOverflowError(MCPSearchError):
    """
    Raised when search queue exceeds capacity.
    
    Indicates the system is at maximum queue depth and cannot
    accept new requests. Clients should retry with backoff.
    """
    
    def __init__(
        self,
        current_depth: int,
        max_depth: int,
        estimated_wait_seconds: Optional[int] = None
    ):
        """
        Initialize queue overflow error.
        
        Args:
            current_depth: Current queue depth
            max_depth: Maximum allowed depth
            estimated_wait_seconds: Estimated time until space available
        """
        details = {
            "current_depth": current_depth,
            "max_depth": max_depth,
            "estimated_wait_seconds": estimated_wait_seconds
        }
        
        recovery = "Please retry after a few seconds with exponential backoff"
        if estimated_wait_seconds:
            recovery = f"Please retry after {estimated_wait_seconds} seconds"
        
        super().__init__(
            message=f"Queue overflow: {current_depth}/{max_depth} requests",
            error_code="QUEUE_OVERFLOW",
            details=details,
            recovery_suggestion=recovery
        )


class RateLimitExceededError(MCPSearchError):
    """
    Raised when rate limits are exceeded.
    
    Can be per-user, per-workspace, or global rate limits.
    Includes retry-after information.
    """
    
    def __init__(
        self,
        limit_type: str,
        current_rate: int,
        limit: int,
        window_seconds: int,
        retry_after_seconds: int
    ):
        """
        Initialize rate limit error.
        
        Args:
            limit_type: Type of limit exceeded (user/workspace/global)
            current_rate: Current request rate
            limit: Rate limit threshold
            window_seconds: Rate limit window size
            retry_after_seconds: Seconds until retry allowed
        """
        details = {
            "limit_type": limit_type,
            "current_rate": current_rate,
            "limit": limit,
            "window_seconds": window_seconds,
            "retry_after_seconds": retry_after_seconds
        }
        
        super().__init__(
            message=f"{limit_type} rate limit exceeded: {current_rate}/{limit} per {window_seconds}s",
            error_code=f"RATE_LIMIT_{limit_type.upper()}",
            details=details,
            recovery_suggestion=f"Retry after {retry_after_seconds} seconds"
        )


class SearchTimeoutError(MCPSearchError):
    """
    Raised when search operations exceed timeout thresholds.
    
    Can occur at various stages: total search, workspace search,
    external search, or AI operations.
    """
    
    def __init__(
        self,
        operation: str,
        timeout_seconds: float,
        elapsed_seconds: float,
        partial_results: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize timeout error.
        
        Args:
            operation: Operation that timed out
            timeout_seconds: Configured timeout
            elapsed_seconds: Actual elapsed time
            partial_results: Any partial results obtained
        """
        details = {
            "operation": operation,
            "timeout_seconds": timeout_seconds,
            "elapsed_seconds": elapsed_seconds,
            "has_partial_results": partial_results is not None
        }
        if partial_results:
            details["partial_results"] = partial_results
        
        super().__init__(
            message=f"Search timeout in {operation}: {elapsed_seconds:.1f}s > {timeout_seconds}s",
            error_code="SEARCH_TIMEOUT",
            details=details,
            recovery_suggestion="Try a more specific query or reduce the search scope"
        )


class ProviderError(MCPSearchError):
    """
    Raised when external search provider operations fail.
    
    Includes provider-specific error information and fallback
    suggestions.
    """
    
    def __init__(
        self,
        provider_name: str,
        operation: str,
        provider_error: Optional[str] = None,
        status_code: Optional[int] = None,
        fallback_providers: Optional[List[str]] = None
    ):
        """
        Initialize provider error.
        
        Args:
            provider_name: Name of the failing provider
            operation: Operation that failed
            provider_error: Provider's error message
            status_code: HTTP status code if applicable
            fallback_providers: Available fallback providers
        """
        details = {
            "provider": provider_name,
            "operation": operation,
            "provider_error": provider_error,
            "status_code": status_code,
            "fallback_providers": fallback_providers or []
        }
        
        recovery = "Search will continue with internal results"
        if fallback_providers:
            recovery = f"Falling back to: {', '.join(fallback_providers)}"
        
        super().__init__(
            message=f"Provider '{provider_name}' failed during {operation}",
            error_code="PROVIDER_ERROR",
            details=details,
            recovery_suggestion=recovery
        )


class TextAIError(MCPSearchError):
    """
    Raised when Text AI service operations fail.
    
    Covers all AI decision-making failures with fallback to
    default behaviors.
    """
    
    def __init__(
        self,
        decision_type: str,
        ai_model: Optional[str] = None,
        error_message: Optional[str] = None,
        fallback_action: Optional[str] = None
    ):
        """
        Initialize Text AI error.
        
        Args:
            decision_type: Type of AI decision that failed
            ai_model: AI model that failed
            error_message: Specific error from AI service
            fallback_action: Action taken as fallback
        """
        details = {
            "decision_type": decision_type,
            "ai_model": ai_model,
            "error_message": error_message,
            "fallback_action": fallback_action
        }
        
        recovery = fallback_action or "Using default search behavior"
        
        super().__init__(
            message=f"AI decision '{decision_type}' failed",
            error_code="TEXT_AI_ERROR",
            details=details,
            recovery_suggestion=recovery
        )


class ConfigurationError(MCPSearchError):
    """
    Raised when configuration is invalid or conflicts detected.
    
    Helps identify misconfiguration issues that prevent proper
    operation.
    """
    
    def __init__(
        self,
        config_section: str,
        issue: str,
        current_value: Any,
        expected_value: Optional[Any] = None,
        conflicts: Optional[List[str]] = None
    ):
        """
        Initialize configuration error.
        
        Args:
            config_section: Configuration section with issue
            issue: Description of the issue
            current_value: Current invalid value
            expected_value: Expected valid value/range
            conflicts: List of conflicting settings
        """
        details = {
            "config_section": config_section,
            "issue": issue,
            "current_value": current_value,
            "expected_value": expected_value,
            "conflicts": conflicts or []
        }
        
        recovery = f"Update {config_section} configuration"
        if expected_value:
            recovery += f" to {expected_value}"
        
        super().__init__(
            message=f"Configuration error in {config_section}: {issue}",
            error_code="CONFIG_ERROR",
            details=details,
            recovery_suggestion=recovery
        )


class WorkspaceError(MCPSearchError):
    """
    Raised when workspace operations fail.
    
    Covers workspace unavailability, permission issues, or
    connection failures.
    """
    
    def __init__(
        self,
        workspace_id: str,
        operation: str,
        reason: str,
        available_workspaces: Optional[List[str]] = None
    ):
        """
        Initialize workspace error.
        
        Args:
            workspace_id: Workspace that failed
            operation: Operation attempted
            reason: Failure reason
            available_workspaces: Other available workspaces
        """
        details = {
            "workspace_id": workspace_id,
            "operation": operation,
            "reason": reason,
            "available_workspaces": available_workspaces or []
        }
        
        recovery = "Search will continue with available workspaces"
        if not available_workspaces:
            recovery = "No alternative workspaces available"
        
        super().__init__(
            message=f"Workspace '{workspace_id}' {operation} failed: {reason}",
            error_code="WORKSPACE_ERROR",
            details=details,
            recovery_suggestion=recovery
        )


class CacheError(MCPSearchError):
    """
    Raised when cache operations fail.
    
    Non-critical error that allows search to continue without
    caching benefits.
    """
    
    def __init__(
        self,
        operation: str,
        cache_backend: str,
        error_message: Optional[str] = None,
        circuit_breaker_open: bool = False
    ):
        """
        Initialize cache error.
        
        Args:
            operation: Cache operation that failed
            cache_backend: Cache backend type
            error_message: Specific error message
            circuit_breaker_open: Whether circuit breaker is open
        """
        details = {
            "operation": operation,
            "cache_backend": cache_backend,
            "error_message": error_message,
            "circuit_breaker_open": circuit_breaker_open
        }
        
        recovery = "Search continuing without cache"
        if circuit_breaker_open:
            recovery = "Cache disabled temporarily due to failures"
        
        super().__init__(
            message=f"Cache {operation} failed",
            error_code="CACHE_ERROR",
            details=details,
            recovery_suggestion=recovery
        )