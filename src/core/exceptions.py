"""
Exception handlers for the simplified Docaiche API.

Provides clean error responses following RFC 7807 Problem Details format.
"""

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.api.schemas import ProblemDetail


# Custom exceptions for processing errors
class ProcessingError(Exception):
    """Base exception for processing errors"""
    pass


class DocumentProcessingError(ProcessingError):
    """Exception for document processing errors"""
    pass


class EnrichmentError(ProcessingError):
    """Exception for enrichment processing errors"""
    pass


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    trace_id = getattr(request.state, "trace_id", "unknown")

    error_detail = ProblemDetail(
        type="https://docaiche.com/problems/validation-error",
        title="Validation Error",
        status=status.HTTP_400_BAD_REQUEST,
        detail=f"Request validation failed: {str(exc)}",
        instance=str(request.url),
        error_code="VALIDATION_ERROR",
        trace_id=trace_id,
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST, content=error_detail.model_dump()
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    trace_id = getattr(request.state, "trace_id", "unknown")

    error_detail = ProblemDetail(
        type="https://docaiche.com/problems/http-error",
        title=exc.detail if isinstance(exc.detail, str) else "HTTP Error",
        status=exc.status_code,
        detail=str(exc.detail),
        instance=str(request.url),
        error_code=f"HTTP_{exc.status_code}",
        trace_id=trace_id,
    )

    return JSONResponse(status_code=exc.status_code, content=error_detail.model_dump())


async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    trace_id = getattr(request.state, "trace_id", "unknown")

    # Log the full exception for debugging
    print(f"[ERROR] [{trace_id}] Unhandled exception: {type(exc).__name__}: {str(exc)}")

    error_detail = ProblemDetail(
        type="https://docaiche.com/problems/internal-error",
        title="Internal Server Error",
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred. Please try again later.",
        instance=str(request.url),
        error_code="INTERNAL_ERROR",
        trace_id=trace_id,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_detail.model_dump(),
    )


def setup_exception_handlers(app: FastAPI):
    """Setup all exception handlers for the application."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
