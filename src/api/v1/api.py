"""
API v1 router for AI Documentation Cache System
PRD-001: HTTP API Foundation - Main API Router

This module contains the main API router that integrates all PRD-001 endpoints
with comprehensive middleware, error handling, and rate limiting.
"""

import logging
from fastapi import APIRouter
from fastapi.exceptions import RequestValidationError

from .search_endpoints import router as search_router
from .admin_endpoints import router as admin_router
from .config_endpoints import router as config_router
from .health_endpoints import router as health_router
from .enrichment import enrichment_router
from .ingestion import ingestion_router
from .provider_endpoints import router as provider_router
from .activity_endpoints import router as activity_router
from .websocket_endpoints import router as websocket_router
from .websocket_progressive import router as websocket_progressive_router
from .websocket_clean import router as websocket_clean_router
from .logs_endpoints import router as logs_router
from .containers_endpoints import router as containers_router
from .metrics_endpoints import router as metrics_router
from .workspace_endpoints import router as workspace_router
from .browser_logs_endpoint import router as browser_logs_router
from .ai_logs_endpoints import router as ai_logs_router
from .mcp import router as mcp_router
from .mcp_endpoints import router as mcp_management_router
from .service_endpoints import router as service_router
from .admin.search import router as admin_search_router
from .weaviate_endpoints import router as weaviate_router
from .exceptions import (
    validation_exception_handler,
    http_exception_handler,
    global_exception_handler,
)

logger = logging.getLogger(__name__)

# Create the main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(search_router)
api_router.include_router(admin_router)
api_router.include_router(config_router)
api_router.include_router(health_router)
api_router.include_router(enrichment_router)
api_router.include_router(ingestion_router)
api_router.include_router(provider_router)
api_router.include_router(activity_router)
api_router.include_router(websocket_router)
api_router.include_router(websocket_progressive_router)
api_router.include_router(websocket_clean_router)
api_router.include_router(logs_router)
api_router.include_router(containers_router)
api_router.include_router(metrics_router)
api_router.include_router(workspace_router)
api_router.include_router(browser_logs_router)
api_router.include_router(ai_logs_router)
api_router.include_router(mcp_router)
api_router.include_router(mcp_management_router)
api_router.include_router(service_router)
api_router.include_router(admin_search_router)
api_router.include_router(weaviate_router)



def setup_exception_handlers(app):
    """
    Setup all exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    # API-004: Custom RequestValidationError handler
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # HTTP exception handler for structured error responses
    app.add_exception_handler(Exception, http_exception_handler)

    # API-009: Global exception handler (fallback)
    app.add_exception_handler(Exception, global_exception_handler)

    logger.info("Exception handlers configured successfully")
