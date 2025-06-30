"""
Correlation ID Middleware for distributed tracing.

This middleware ensures all requests have correlation IDs for tracking
across services and includes them in logs and downstream requests.
"""

import uuid
import logging
import contextvars
from typing import Optional, Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Context variables for correlation tracking
correlation_id_var = contextvars.ContextVar('correlation_id', default=None)
conversation_id_var = contextvars.ContextVar('conversation_id', default=None)
session_id_var = contextvars.ContextVar('session_id', default=None)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle correlation IDs for distributed tracing.
    
    Features:
    - Generates correlation ID if not provided
    - Extracts IDs from headers
    - Propagates IDs to context and response headers
    - Integrates with logging
    """
    
    def __init__(self, app, correlation_header: str = "X-Correlation-ID"):
        """
        Initialize correlation middleware.
        
        Args:
            app: ASGI application
            correlation_header: Header name for correlation ID
        """
        super().__init__(app)
        self.correlation_header = correlation_header
        self.conversation_header = "X-Conversation-ID"
        self.session_header = "X-Session-ID"
        
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation tracking."""
        # Extract or generate correlation ID
        correlation_id = request.headers.get(self.correlation_header)
        if not correlation_id:
            correlation_id = f"req-{uuid.uuid4().hex[:12]}"
            
        # Extract other tracking IDs
        conversation_id = request.headers.get(self.conversation_header)
        session_id = request.headers.get(self.session_header)
        
        # Extract from query params if not in headers (for WebSocket)
        if not conversation_id and "conversation_id" in request.query_params:
            conversation_id = request.query_params["conversation_id"]
        if not session_id and "session_id" in request.query_params:
            session_id = request.query_params["session_id"]
            
        # Set context variables
        correlation_id_var.set(correlation_id)
        if conversation_id:
            conversation_id_var.set(conversation_id)
        if session_id:
            session_id_var.set(session_id)
            
        # Add to request state for easy access
        request.state.correlation_id = correlation_id
        request.state.conversation_id = conversation_id
        request.state.session_id = session_id
        
        # Log request with correlation ID
        logger.info(
            f"Request started",
            extra={
                "correlation_id": correlation_id,
                "conversation_id": conversation_id,
                "session_id": session_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown"
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add correlation headers to response
            response.headers[self.correlation_header] = correlation_id
            if conversation_id:
                response.headers[self.conversation_header] = conversation_id
            if session_id:
                response.headers[self.session_header] = session_id
                
            # Log completion
            logger.info(
                f"Request completed",
                extra={
                    "correlation_id": correlation_id,
                    "status_code": response.status_code,
                    "method": request.method,
                    "path": request.url.path
                }
            )
            
            return response
            
        except Exception as e:
            # Log error with correlation ID
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e)
                },
                exc_info=True
            )
            raise
        finally:
            # Clear context variables
            correlation_id_var.set(None)
            conversation_id_var.set(None)
            session_id_var.set(None)


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id_var.get()


def get_conversation_id() -> Optional[str]:
    """Get current conversation ID from context."""
    return conversation_id_var.get()


def get_session_id() -> Optional[str]:
    """Get current session ID from context."""
    return session_id_var.get()


def get_correlation_context() -> dict:
    """Get all correlation context as a dictionary."""
    return {
        "correlation_id": get_correlation_id(),
        "conversation_id": get_conversation_id(),
        "session_id": get_session_id()
    }


class CorrelationLogFilter(logging.Filter):
    """
    Logging filter to add correlation IDs to log records.
    """
    
    def filter(self, record):
        """Add correlation context to log record."""
        record.correlation_id = get_correlation_id() or ""
        record.conversation_id = get_conversation_id() or ""
        record.session_id = get_session_id() or ""
        return True


def setup_correlation_logging():
    """Setup correlation ID logging for all loggers."""
    # Add filter to root logger
    root_logger = logging.getLogger()
    correlation_filter = CorrelationLogFilter()
    
    for handler in root_logger.handlers:
        handler.addFilter(correlation_filter)
        
    # Update formatter to include correlation IDs
    for handler in root_logger.handlers:
        if handler.formatter:
            # Get existing format
            fmt = handler.formatter._fmt if hasattr(handler.formatter, '_fmt') else None
            if fmt and 'correlation_id' not in fmt:
                # Add correlation fields to format
                new_fmt = fmt.replace(
                    '%(message)s',
                    '[%(correlation_id)s] %(message)s'
                )
                handler.setFormatter(logging.Formatter(new_fmt))
                
    logger.info("Correlation logging configured")


class CorrelationContextManager:
    """
    Context manager for setting correlation IDs in background tasks.
    """
    
    def __init__(self, 
                 correlation_id: Optional[str] = None,
                 conversation_id: Optional[str] = None,
                 session_id: Optional[str] = None):
        """Initialize context manager with IDs."""
        self.correlation_id = correlation_id or f"task-{uuid.uuid4().hex[:12]}"
        self.conversation_id = conversation_id
        self.session_id = session_id
        self._tokens = []
        
    def __enter__(self):
        """Set context variables."""
        self._tokens.append(correlation_id_var.set(self.correlation_id))
        if self.conversation_id:
            self._tokens.append(conversation_id_var.set(self.conversation_id))
        if self.session_id:
            self._tokens.append(session_id_var.set(self.session_id))
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Reset context variables."""
        for token in self._tokens:
            correlation_id_var.reset(token)
        self._tokens.clear()
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self.__enter__()
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        return self.__exit__(exc_type, exc_val, exc_tb)