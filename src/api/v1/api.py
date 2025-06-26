"""
API v1 router for AI Documentation Cache System
PRD-001: HTTP API Foundation - Main API Router

This module contains the main API router that integrates all PRD-001 endpoints
with comprehensive middleware, error handling, and rate limiting.
"""

import logging
from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded

from .search_endpoints import router as search_router
from .admin_endpoints import router as admin_router
from .config_endpoints import router as config_router
from .health_endpoints import router as health_router
from .enrichment import enrichment_router
from .ingestion import ingestion_router
from .middleware import limiter, rate_limit_handler
from .exceptions import (
    validation_exception_handler,
    http_exception_handler,
    global_exception_handler
)

logger = logging.getLogger(__name__)

# Create the main API router
api_router = APIRouter()

# Include all endpoint routers with proper prefixes
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(config_router, prefix="/config", tags=["config"])
api_router.include_router(health_router, prefix="/health", tags=["health"])
api_router.include_router(enrichment_router, prefix="/enrichment", tags=["enrichment"])
api_router.include_router(ingestion_router, prefix="/ingestion", tags=["ingestion"])
from .mcp_endpoints import router as mcp_router
api_router.include_router(mcp_router)

# Add rate limiter state to router
api_router.state = type('State', (), {'limiter': limiter})()


def setup_exception_handlers(app):
    """
    Setup all exception handlers for the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # API-004: Custom RequestValidationError handler
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Rate limiting exception handler for API-005
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    
    # HTTP exception handler for structured error responses
    app.add_exception_handler(Exception, http_exception_handler)
    
    # API-009: Global exception handler (fallback)
    app.add_exception_handler(Exception, global_exception_handler)
    
    logger.info("Exception handlers configured successfully")