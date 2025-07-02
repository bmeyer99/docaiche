"""
Search System Admin API
=======================

Main router that integrates all search system management endpoints.

This module provides the complete admin API for the MCP search system,
including configuration, vector search, Text AI, providers, and monitoring.
"""

from fastapi import APIRouter
import logging

# Import all sub-routers
from .config import router as config_router
from .vector import router as vector_router
from .text_ai import router as text_ai_router
from .providers import router as providers_router
from .monitoring import router as monitoring_router
from .websocket import router as websocket_router

logger = logging.getLogger(__name__)

# Create main router with common prefix
router = APIRouter(
    prefix="/admin/search",
    tags=["search-admin"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Include all sub-routers
router.include_router(
    config_router,
    tags=["configuration"],
    responses={
        400: {"description": "Bad request - Invalid configuration"},
        403: {"description": "Forbidden - Insufficient permissions"}
    }
)

router.include_router(
    vector_router,
    tags=["vector-search"],
    responses={
        400: {"description": "Bad request - Invalid parameters"},
        503: {"description": "Service unavailable - AnythingLLM connection failed"}
    }
)

router.include_router(
    text_ai_router,
    tags=["text-ai"],
    responses={
        400: {"description": "Bad request - Invalid parameters"},
        503: {"description": "Service unavailable - LLM connection failed"}
    }
)

router.include_router(
    providers_router,
    tags=["providers"],
    responses={
        400: {"description": "Bad request - Invalid provider configuration"},
        404: {"description": "Provider not found"}
    }
)

router.include_router(
    monitoring_router,
    tags=["monitoring"],
    responses={
        400: {"description": "Bad request - Invalid query parameters"}
    }
)

# Include WebSocket router (no prefix needed as it's already /ws)
router.include_router(
    websocket_router,
    tags=["websocket"]
)


# Root endpoint for API info
@router.get("")
async def get_search_admin_info():
    """
    Get search system admin API information.
    
    Returns basic information about the search admin API including:
    - API version
    - Available endpoints
    - System status
    - Documentation links
    """
    return {
        "name": "MCP Search System Admin API",
        "version": "1.0.0",
        "description": "Administrative API for managing the MCP search system",
        "endpoints": {
            "configuration": "/admin/search/config",
            "vector_search": "/admin/search/vector",
            "text_ai": "/admin/search/text-ai",
            "providers": "/admin/search/providers",
            "monitoring": "/admin/search/monitoring"
        },
        "documentation": {
            "api": "/docs#/search-admin",
            "system": "/docs/MCP/PLAN.md"
        },
        "status": "active"
    }


# Health check endpoint
@router.get("/health")
async def health_check():
    """
    Check health of all search system components.
    
    Returns aggregated health status from:
    - Configuration service
    - Vector search (AnythingLLM)
    - Text AI (LLM)
    - External providers
    - Queue system
    """
    try:
        # TODO: Phase 2 - Implement actual health checks
        health_status = {
            "overall": "healthy",
            "components": {
                "configuration": {
                    "status": "healthy",
                    "message": "Configuration service operational"
                },
                "vector_search": {
                    "status": "healthy",
                    "message": "AnythingLLM connected"
                },
                "text_ai": {
                    "status": "healthy",
                    "message": "LLM service available"
                },
                "providers": {
                    "status": "healthy",
                    "message": "2 of 3 providers active"
                },
                "queue": {
                    "status": "healthy",
                    "message": "Queue depth: 12/100"
                }
            },
            "timestamp": "2024-01-01T12:00:00Z"
        }
        
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "overall": "unhealthy",
            "error": str(e),
            "timestamp": "2024-01-01T12:00:00Z"
        }


# Statistics endpoint
@router.get("/stats")
async def get_search_statistics():
    """
    Get high-level search system statistics.
    
    Returns summary statistics including:
    - Total searches today
    - Active providers
    - Queue status
    - Cache hit rate
    - Error rate
    """
    try:
        # TODO: Phase 2 - Load actual statistics
        return {
            "period": "24h",
            "searches": {
                "total": 6250,
                "successful": 6125,
                "failed": 125,
                "cached": 4062
            },
            "providers": {
                "total": 5,
                "active": 3,
                "healthy": 3
            },
            "performance": {
                "avg_latency_ms": 485,
                "p95_latency_ms": 1250,
                "cache_hit_rate": 0.65
            },
            "queue": {
                "current_depth": 12,
                "max_depth": 100,
                "processing_rate": 8.5
            },
            "timestamp": "2024-01-01T12:00:00Z"
        }
    except Exception as e:
        logger.error(f"Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Export all endpoints for documentation
__all__ = [
    "router",
    "config_router",
    "vector_router", 
    "text_ai_router",
    "providers_router",
    "monitoring_router"
]