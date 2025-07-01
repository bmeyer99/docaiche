"""
API v1 Middleware Components - PRD-001: HTTP API Foundation
API-007: Implement structured logging middleware
API-010: Implement request/response logging middleware

This module implements middleware for structured logging,
and request/response logging with trace IDs for operational visibility.
"""

import json
import logging
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Import enhanced logging for security monitoring
try:
    from src.logging_config import SecurityLogger, MetricsLogger
    _security_logger = SecurityLogger(logger)
    _metrics_logger = MetricsLogger(logger)
except ImportError:
    _security_logger = None
    _metrics_logger = None
    logger.warning("Enhanced security logging not available")


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
        client_ip = request.client.host if request.client else "unknown"
        
        log_data = {
            "event": "request_started",
            "trace_id": trace_id,
            "method": request.method,
            "url": str(request.url),
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": client_ip,
            "user_agent": request.headers.get("user-agent"),
            "content_type": request.headers.get("content-type"),
            "content_length": request.headers.get("content-length"),
            "timestamp": time.time(),
        }
        
        # Log security-sensitive operations
        sensitive_paths = ["/admin", "/config", "/provider", "/analytics"]
        if any(sens_path in request.url.path for sens_path in sensitive_paths):
            if _security_logger:
                _security_logger.log_sensitive_operation(
                    operation="api_access",
                    resource=request.url.path,
                    client_ip=client_ip,
                    user_agent=request.headers.get("user-agent", "unknown"),
                    method=request.method,
                    trace_id=trace_id
                )
        
        # Use enhanced metrics logger if available
        if _metrics_logger:
            _metrics_logger.log_api_request(
                request_id=trace_id,
                method=request.method,
                path=request.url.path,
                status_code=0,  # Will be updated in response
                duration=0,  # Will be updated in response
                client_ip=client_ip,
                user_agent=request.headers.get("user-agent")
            )
        else:
            logger.info("Request started", extra={"structured_log": json.dumps(log_data)})

    def _log_response(
        self, request: Request, response: Response, trace_id: str, process_time: float
    ) -> None:
        """
        Log structured response information.

        Args:
            request: The original request
            response: The response object
            trace_id: Request trace identifier
            process_time: Request processing time in seconds
        """
        client_ip = request.client.host if request.client else "unknown"
        
        log_data = {
            "event": "request_completed",
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "process_time_ms": round(process_time * 1000, 2),
            "response_size": len(response.body) if hasattr(response, "body") else None,
            "timestamp": time.time(),
        }
        
        # Log security events for failed authentication attempts
        if response.status_code == 401:
            if _security_logger:
                _security_logger.log_sensitive_operation(
                    operation="authentication_failure",
                    resource=request.url.path,
                    client_ip=client_ip,
                    status_code=response.status_code,
                    trace_id=trace_id
                )
        
        # Log access to sensitive endpoints with detailed context
        sensitive_paths = ["/admin", "/config", "/provider", "/analytics"]
        if any(sens_path in request.url.path for sens_path in sensitive_paths):
            if _security_logger:
                _security_logger.log_admin_action(
                    action=f"{request.method}_{request.url.path.replace('/', '_')}",
                    target=request.url.path,
                    impact_level="medium" if response.status_code < 400 else "low",
                    client_ip=client_ip,
                    status_code=response.status_code,
                    duration_ms=round(process_time * 1000, 2),
                    trace_id=trace_id
                )
        
        # Use enhanced metrics logger if available
        if _metrics_logger:
            _metrics_logger.log_api_request(
                request_id=trace_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=process_time,
                client_ip=client_ip,
                response_size=len(response.body) if hasattr(response, "body") else None
            )
        else:
            # Determine log level based on status code
            if response.status_code >= 500:
                logger.error(
                    "Request completed with server error",
                    extra={"structured_log": json.dumps(log_data)},
                )
            elif response.status_code >= 400:
                logger.warning(
                    "Request completed with client error",
                    extra={"structured_log": json.dumps(log_data)},
                )
            else:
                logger.info(
                    "Request completed successfully",
                    extra={"structured_log": json.dumps(log_data)},
                )

    def _log_error(
        self, request: Request, error: Exception, trace_id: str, process_time: float
    ) -> None:
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
            "timestamp": time.time(),
        }

        logger.error(
            "Request failed with exception",
            extra={"structured_log": json.dumps(log_data)},
            exc_info=True,
        )


def get_trace_id(request: Request) -> str:
    """
    Get trace ID from request state.

    Args:
        request: FastAPI request object

    Returns:
        Trace ID string for the current request
    """
    return getattr(request.state, "trace_id", "unknown")
