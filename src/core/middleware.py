"""
Essential middleware for the simplified Docaiche API.

Includes only the necessary middleware for logging and request tracking.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.logging_config import MetricsLogger

logger = logging.getLogger(__name__)
metrics = MetricsLogger(logger)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Simple logging middleware for request/response tracking.

    Adds trace IDs and logs basic request information without excessive complexity.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate trace ID for request correlation
        trace_id = str(uuid.uuid4())[:8]
        request.state.trace_id = trace_id
        
        # Get correlation IDs from request state (set by CorrelationIDMiddleware)
        correlation_id = getattr(request.state, 'correlation_id', None)
        conversation_id = getattr(request.state, 'conversation_id', None)
        session_id = getattr(request.state, 'session_id', None)

        # Record start time
        start_time = time.time()

        # Log request start (for debugging)
        logger.debug(
            f"Request started",
            extra={
                'request_id': trace_id,
                'correlation_id': correlation_id,
                'conversation_id': conversation_id,
                'session_id': session_id,
                'method': request.method,
                'path': request.url.path,
            }
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Add trace ID to response headers
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Process-Time"] = str(process_time)

            # Log structured metrics with correlation IDs
            metrics.log_api_request(
                request_id=trace_id,
                correlation_id=correlation_id,
                conversation_id=conversation_id,
                session_id=session_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=process_time,
                user_agent=request.headers.get("user-agent", "unknown"),
                remote_addr=request.client.host if request.client else "unknown"
            )

            return response

        except Exception as e:
            # Calculate processing time even for errors
            process_time = time.time() - start_time

            # Log error with structured format
            metrics.log_error(
                error_type=type(e).__name__,
                error_message=str(e),
                request_id=trace_id,
                method=request.method,
                path=request.url.path,
                duration=process_time
            )

            # Re-raise the exception
            raise
