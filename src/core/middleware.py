"""
Essential middleware for the simplified Docaiche API.

Includes only the necessary middleware for logging and request tracking.
"""

import time
import uuid
from datetime import datetime
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Simple logging middleware for request/response tracking.

    Adds trace IDs and logs basic request information without excessive complexity.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate trace ID for request correlation
        trace_id = str(uuid.uuid4())[:8]
        request.state.trace_id = trace_id

        # Record start time
        start_time = time.time()

        # Log incoming request
        print(
            f"[{datetime.utcnow().isoformat()}] [{trace_id}] "
            f"{request.method} {request.url.path} - Started"
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Add trace ID to response headers
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Process-Time"] = str(process_time)

            # Log response
            print(
                f"[{datetime.utcnow().isoformat()}] [{trace_id}] "
                f"{request.method} {request.url.path} - "
                f"Completed {response.status_code} in {process_time:.3f}s"
            )

            return response

        except Exception as e:
            # Calculate processing time even for errors
            process_time = time.time() - start_time

            # Log error
            print(
                f"[{datetime.utcnow().isoformat()}] [{trace_id}] "
                f"{request.method} {request.url.path} - "
                f"Error after {process_time:.3f}s: {str(e)}"
            )

            # Re-raise the exception
            raise
