"""
API v1 Exception Handlers - PRD-001: HTTP API Foundation
API-004: Add custom RequestValidationError exception handler
API-009: Implement global exception handler

This module implements custom exception handlers that return RFC 7807
Problem Details format for all API errors with proper HTTP status codes.
"""

import logging
from typing import Union

from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .schemas import ProblemDetail
from .middleware import get_trace_id

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Custom RequestValidationError handler - API-004
    
    Handles Pydantic validation errors and returns RFC 7807 format.
    
    Args:
        request: The request that caused validation error
        exc: The validation exception
        
    Returns:
        JSONResponse with RFC 7807 Problem Details format
    """
    trace_id = get_trace_id(request)
    
    # Extract validation error details
    errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        errors.append(f"{field_path}: {error['msg']}")
    
    error_detail = f"Validation failed for {len(errors)} field(s): {'; '.join(errors)}"
    
    problem_detail = ProblemDetail(
        type="https://docs.example.com/errors/validation-error",
        title="Request Validation Error",
        status=422,
        detail=error_detail,
        instance=str(request.url.path),
        error_code="VALIDATION_ERROR",
        trace_id=trace_id
    )
    
    # Log validation error with context
    logger.warning(
        f"Request validation failed for {request.method} {request.url.path}",
        extra={
            "trace_id": trace_id,
            "validation_errors": exc.errors(),
            "request_body": await _get_request_body_safely(request)
        }
    )
    
    return JSONResponse(
        status_code=422,
        content=problem_detail.dict()
    )


async def http_exception_handler(request: Request, exc: Union[HTTPException, StarletteHTTPException]) -> JSONResponse:
    """
    Custom HTTP exception handler for FastAPI and Starlette HTTP exceptions.
    
    Args:
        request: The request that caused the exception
        exc: The HTTP exception
        
    Returns:
        JSONResponse with RFC 7807 Problem Details format
    """
    trace_id = get_trace_id(request)
    
    # Map common HTTP status codes to error types
    error_type_map = {
        400: "https://docs.example.com/errors/bad-request",
        401: "https://docs.example.com/errors/unauthorized",
        403: "https://docs.example.com/errors/forbidden",
        404: "https://docs.example.com/errors/not-found",
        405: "https://docs.example.com/errors/method-not-allowed",
        409: "https://docs.example.com/errors/conflict",
        429: "https://docs.example.com/errors/rate-limit-exceeded",
        500: "https://docs.example.com/errors/internal-server-error",
        502: "https://docs.example.com/errors/bad-gateway",
        503: "https://docs.example.com/errors/service-unavailable",
        504: "https://docs.example.com/errors/gateway-timeout"
    }
    
    # Map status codes to titles
    title_map = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        409: "Conflict",
        429: "Rate Limit Exceeded",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout"
    }
    
    status_code = exc.status_code
    error_type = error_type_map.get(status_code, "https://docs.example.com/errors/http-error")
    title = title_map.get(status_code, "HTTP Error")
    
    problem_detail = ProblemDetail(
        type=error_type,
        title=title,
        status=status_code,
        detail=str(exc.detail),
        instance=str(request.url.path),
        error_code=f"HTTP_{status_code}",
        trace_id=trace_id
    )
    
    # Log based on severity
    if status_code >= 500:
        logger.error(
            f"Server error {status_code} for {request.method} {request.url.path}: {exc.detail}",
            extra={"trace_id": trace_id, "status_code": status_code}
        )
    elif status_code >= 400:
        logger.warning(
            f"Client error {status_code} for {request.method} {request.url.path}: {exc.detail}",
            extra={"trace_id": trace_id, "status_code": status_code}
        )
    
    return JSONResponse(
        status_code=status_code,
        content=problem_detail.dict()
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler - API-009
    
    Catches all unhandled exceptions and returns RFC 7807 format.
    Never exposes internal error details to clients.
    
    Args:
        request: The request that caused the exception
        exc: The unhandled exception
        
    Returns:
        JSONResponse with RFC 7807 Problem Details format
    """
    trace_id = get_trace_id(request)
    
    # Log the full exception with stack trace for debugging
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}",
        extra={
            "trace_id": trace_id,
            "exception_type": type(exc).__name__,
            "exception_message": str(exc)
        },
        exc_info=True
    )
    
    # Return generic error response without exposing internal details
    problem_detail = ProblemDetail(
        type="https://docs.example.com/errors/internal-server-error",
        title="Internal Server Error",
        status=500,
        detail="An unexpected error occurred while processing your request",
        instance=str(request.url.path),
        error_code="INTERNAL_SERVER_ERROR",
        trace_id=trace_id
    )
    
    return JSONResponse(
        status_code=500,
        content=problem_detail.dict()
    )


async def _get_request_body_safely(request: Request) -> Union[str, None]:
    """
    Safely extract request body for logging without consuming it.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Request body as string or None if not available
    """
    try:
        # Only try to get body for POST/PUT/PATCH requests with content
        if request.method in ["POST", "PUT", "PATCH"] and "content-length" in request.headers:
            content_length = int(request.headers.get("content-length", 0))
            if 0 < content_length < 1024:  # Only log small request bodies
                body = await request.body()
                return body.decode("utf-8", errors="ignore")[:500]  # Truncate for logging
    except Exception:
        pass  # Ignore errors when extracting body
    
    return None