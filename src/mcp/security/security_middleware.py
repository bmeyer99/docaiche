"""
Security Middleware for MCP Server
==================================

Middleware implementation that integrates security manager with
MCP request/response flow for comprehensive security enforcement.
"""

import time
import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from functools import wraps

from ..schemas import MCPRequest, MCPResponse, MCPError, ErrorCode
from ..exceptions import (
    SecurityError, AuthorizationError, RateLimitError,
    MCPException, ValidationError
)
from .security_manager import SecurityManager

logger = logging.getLogger(__name__)


class SecurityMiddleware:
    """
    Security middleware for MCP server.
    
    Intercepts all requests and responses to enforce security policies
    including authentication, authorization, rate limiting, and threat detection.
    """
    
    def __init__(self, security_manager: SecurityManager):
        self.security_manager = security_manager
        self.bypass_methods = {
            "initialize",  # Allow initialization without auth
            "health/check"  # Allow health checks
        }
        
        logger.info("Security middleware initialized")
    
    async def process_request(
        self,
        request: MCPRequest,
        auth_context: Dict[str, Any],
        handler: Callable[[MCPRequest], Awaitable[MCPResponse]]
    ) -> MCPResponse:
        """
        Process request through security validation.
        
        Args:
            request: The MCP request
            auth_context: Authentication context with client info
            handler: The actual request handler
            
        Returns:
            MCPResponse with result or error
        """
        start_time = time.time()
        client_id = auth_context.get("client_id", "anonymous")
        
        try:
            # Skip security for bypass methods
            if request.method not in self.bypass_methods:
                # Validate request security
                await self.security_manager.validate_request(
                    request=request,
                    client_id=client_id,
                    auth_context=auth_context
                )
            
            # Process request
            response = await handler(request)
            
            # Validate response
            if request.method not in self.bypass_methods:
                response = await self.security_manager.validate_response(
                    response=response,
                    request=request,
                    client_id=client_id
                )
            
            # Add security headers
            if not response.metadata:
                response.metadata = {}
            
            response.metadata.update({
                "security": {
                    "validated": True,
                    "client_id": client_id,
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
            })
            
            return response
            
        except RateLimitError as e:
            logger.warning(
                f"Rate limit exceeded for client {client_id}",
                extra={
                    "client_id": client_id,
                    "method": request.method,
                    "retry_after": e.retry_after
                }
            )
            
            return MCPResponse(
                id=request.id,
                error=MCPError(
                    code=ErrorCode.RATE_LIMIT_EXCEEDED,
                    message=str(e),
                    data={
                        "retry_after": e.retry_after,
                        "client_id": client_id
                    }
                ),
                metadata={
                    "security": {
                        "rate_limited": True,
                        "retry_after": e.retry_after
                    }
                }
            )
            
        except (SecurityError, AuthorizationError) as e:
            logger.error(
                f"Security violation for client {client_id}: {e}",
                extra={
                    "client_id": client_id,
                    "method": request.method,
                    "error_code": getattr(e, 'error_code', 'SECURITY_ERROR')
                }
            )
            
            return MCPResponse(
                id=request.id,
                error=MCPError(
                    code=ErrorCode.FORBIDDEN,
                    message=str(e),
                    data=getattr(e, 'details', {})
                ),
                metadata={
                    "security": {
                        "violation": True,
                        "client_id": client_id
                    }
                }
            )
            
        except Exception as e:
            logger.exception(
                f"Unexpected error in security middleware",
                extra={
                    "client_id": client_id,
                    "method": request.method
                }
            )
            
            return MCPResponse(
                id=request.id,
                error=MCPError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message="Internal security error",
                    data={"type": type(e).__name__}
                )
            )
    
    def wrap_handler(
        self,
        handler: Callable[[MCPRequest, Dict[str, Any]], Awaitable[MCPResponse]]
    ) -> Callable[[MCPRequest, Dict[str, Any]], Awaitable[MCPResponse]]:
        """
        Wrap a request handler with security middleware.
        
        Args:
            handler: The original handler
            
        Returns:
            Wrapped handler with security enforcement
        """
        @wraps(handler)
        async def wrapped(request: MCPRequest, auth_context: Dict[str, Any]) -> MCPResponse:
            return await self.process_request(
                request=request,
                auth_context=auth_context,
                handler=lambda req: handler(req, auth_context)
            )
        
        return wrapped
    
    async def handle_auth_event(
        self,
        event_type: str,
        client_id: str,
        details: Dict[str, Any]
    ) -> None:
        """
        Handle authentication events.
        
        Args:
            event_type: Type of auth event (success, failure)
            client_id: Client identifier
            details: Event details
        """
        if event_type == "auth_failure":
            await self.security_manager.handle_auth_failure(
                client_id=client_id,
                reason=details.get("reason", "Unknown")
            )
        elif event_type == "auth_success":
            await self.security_manager.handle_auth_success(client_id)
    
    async def grant_consent(
        self,
        client_id: str,
        operation: str,
        duration_hours: Optional[int] = None
    ) -> str:
        """
        Grant consent for an operation.
        
        Args:
            client_id: Client identifier
            operation: Operation requiring consent
            duration_hours: Consent duration
            
        Returns:
            Consent ID
        """
        return await self.security_manager.grant_consent(
            client_id=client_id,
            operation=operation,
            duration_hours=duration_hours
        )
    
    async def revoke_consent(self, client_id: str, operation: str) -> None:
        """Revoke consent for an operation."""
        await self.security_manager.revoke_consent(
            client_id=client_id,
            operation=operation
        )
    
    async def get_security_status(self, client_id: str) -> Dict[str, Any]:
        """Get security status for a client."""
        return await self.security_manager.get_security_status(client_id)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get security metrics."""
        return await self.security_manager.get_metrics()


def create_security_decorator(
    security_middleware: SecurityMiddleware
) -> Callable:
    """
    Create a decorator for securing individual handlers.
    
    Args:
        security_middleware: The security middleware instance
        
    Returns:
        Decorator function
    """
    def security_required(
        require_consent: bool = False,
        threat_threshold: Optional[float] = None
    ):
        """
        Decorator to enforce security on a handler.
        
        Args:
            require_consent: Whether explicit consent is required
            threat_threshold: Custom threat score threshold
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(
                request: MCPRequest,
                auth_context: Dict[str, Any],
                *args,
                **kwargs
            ) -> MCPResponse:
                # Additional security checks can be added here
                if require_consent:
                    # Mark method as requiring consent
                    if hasattr(request, '_requires_consent'):
                        request._requires_consent = True
                
                if threat_threshold is not None:
                    # Set custom threat threshold
                    if hasattr(request, '_threat_threshold'):
                        request._threat_threshold = threat_threshold
                
                # Process through middleware
                return await security_middleware.process_request(
                    request=request,
                    auth_context=auth_context,
                    handler=lambda req: func(req, auth_context, *args, **kwargs)
                )
            
            return wrapper
        return decorator
    
    return security_required