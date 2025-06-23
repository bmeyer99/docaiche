"""
API v1 Middleware Components - PRD-001: HTTP API Foundation
API-007: Implement structured logging middleware
API-010: Implement request/response logging middleware

This module implements middleware for structured logging, rate limiting,
and request/response logging with trace IDs for operational visibility.
"""

import json
import logging
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# Create rate limiter instance for API-005
limiter = Limiter(key_func=get_remote_address)

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Structured logging middleware with trace IDs - API-007 and API-010
    
    Provides request/response logging with trace ID for correlation and
    structured JSON logging for container environments.
    """
    
    def __init__(self, app):
        """Initialize logging middleware"""
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and response with structured logging.
        
        Args:
            request: The incoming request
            call_next: The next middleware or endpoint
            
        Returns:
            Response: The response with trace ID header
        """
        # Generate trace ID for request correlation
        trace_id = str(uuid.uuid4())
        
        # Add trace ID to request state for use in endpoints
        request.state.trace_id = trace_id
        
        # Record request start time
        start_time = time.time()
        
        # Log structured request information
        self._log_request(request, trace_id)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate response time
            process_time = time.time() - start_time
            
            # Add trace ID to response headers
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Process-Time"] = f"{process_time:.3f}s"
            
            # Log structured response information
            self._log_response(request, response, trace_id, process_time)
            
            return response
            
        except Exception as e:
            # Calculate error response time
            process_time = time.time() - start_time
            
            # Log error with trace ID
            self._log_error(request, e, trace_id, process_time)
            
            # Re-raise exception for FastAPI error handling
            raise
    
    def _log_request(self, request: Request, trace_id: str) -> None:
        """
        Log structured request information.
        
        Args:
            request: The incoming request
            trace_id: Request trace identifier
        """
        log_data = {
            "event": "request_started",
            "trace_id": trace_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
            "timestamp": time.time()
        }
        
        logger.info("Request started", extra={"structured_log": json.dumps(log_data)})
    
    def _log_response(self, request: Request, response: Response, trace_id: str, process_time: float) -> None:
        """
        Log structured response information.
        
        Args:
            request: The original request
            response: The response object
            trace_id: Request trace identifier
            process_time: Request processing time in seconds
        """
        log_data = {
            "event": "request_completed",
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
            "response_size": len(response.body) if hasattr(response, 'body') else None,
            "timestamp": time.time()
        }
        
        # Determine log level based on status code
        if response.status_code >= 500:
            logger.error("Request completed with server error", extra={"structured_log": json.dumps(log_data)})
        elif response.status_code >= 400:
            logger.warning("Request completed with client error", extra={"structured_log": json.dumps(log_data)})
        else:
            logger.info("Request completed successfully", extra={"structured_log": json.dumps(log_data)})
    
    def _log_error(self, request: Request, error: Exception, trace_id: str, process_time: float) -> None:
        """
        Log structured error information.
        
        Args:
            request: The original request
            error: The exception that occurred
            trace_id: Request trace identifier
            process_time: Request processing time before error
        """
        log_data = {
            "event": "request_error",
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "process_time_ms": round(process_time * 1000, 2),
            "timestamp": time.time()
        }
        
        logger.error("Request failed with exception", extra={"structured_log": json.dumps(log_data)}, exc_info=True)


def get_trace_id(request: Request) -> str:
    """
    Get trace ID from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Trace ID string for the current request
    """
    return getattr(request.state, 'trace_id', 'unknown')


# Rate limiting exception handler for API-005
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Custom rate limit exceeded handler that returns proper error format.
    
    Args:
        request: The rate-limited request
        exc: Rate limit exception
        
    Returns:
        JSONResponse with RFC 7807 error format
    """
    from fastapi.responses import JSONResponse
    from .schemas import ProblemDetail
    
    trace_id = get_trace_id(request)
    
    problem_detail = ProblemDetail(
        type="https://docs.example.com/errors/rate-limit-exceeded",
        title="Rate Limit Exceeded",
        status=429,
        detail=f"Rate limit exceeded: {exc.detail}",
        instance=str(request.url.path),
        error_code="RATE_LIMIT_EXCEEDED",
        trace_id=trace_id
    )
    
    return JSONResponse(
        status_code=429,
        content=problem_detail.dict(),
        headers={"Retry-After": str(exc.retry_after) if exc.retry_after else "60"}
    )