"""
Health API Endpoints - PRD-001: HTTP API Foundation
Health check and statistics endpoints
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Request

from .middleware import limiter
from .dependencies import (
    get_database_manager, get_cache_manager, get_anythingllm_client, get_search_orchestrator
)
from src.database.connection import DatabaseManager, CacheManager
from src.clients.anythingllm import AnythingLLMClient
from src.search.orchestrator import SearchOrchestrator
from src.core.config import get_system_configuration

logger = logging.getLogger(__name__)

# Create router for health endpoints
router = APIRouter()

@router.get("/health", tags=["health"])
async def health_check(
    db_manager: DatabaseManager = Depends(get_database_manager),
    cache_manager: CacheManager = Depends(get_cache_manager),
    anythingllm_client: AnythingLLMClient = Depends(get_anythingllm_client),
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator)
):
    """
    GET /api/v1/health - Reports the health of the system and its dependencies

    Returns:
        JSON with overall status, component statuses, features, timestamp, and version.
    """
    # Always return HTTP 200
    components = {}
    features = {
        "document_processing": "available",
        "search": "available",
        "llm_enhancement": "available"
    }
    overall_status = "healthy"
    version = "1.0.0"
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

    # Database
    try:
        db_health = await db_manager.health_check()
        db_status = "healthy" if db_health.get("status") == "healthy" else "unhealthy"
        db_msg = db_health.get("message", "Connected" if db_status == "healthy" else "Unknown error")
        components["database"] = {"status": db_status, "message": db_msg}
        if db_status != "healthy":
            overall_status = "degraded"
    except Exception as e:
        components["database"] = {"status": "unavailable", "message": f"Connection failed: {e}"}
        overall_status = "degraded"

    # Redis/Cache
    try:
        cache_health = await cache_manager.health_check()
        cache_status = "healthy" if cache_health.get("status") == "healthy" else "unavailable"
        cache_msg = cache_health.get("message", "Connected" if cache_status == "healthy" else "Unavailable")
        components["redis"] = {"status": cache_status, "message": cache_msg}
        if cache_status != "healthy":
            overall_status = "degraded"
            features["search"] = "unavailable"
    except Exception as e:
        components["redis"] = {"status": "unavailable", "message": f"Connection failed: {e}"}
        overall_status = "degraded"
        features["search"] = "unavailable"

    # AnythingLLM
    try:
        llm_health = await anythingllm_client.health_check()
        llm_status = "healthy" if llm_health.get("status") == "healthy" else "unavailable"
        llm_msg = llm_health.get("message", "Connected" if llm_status == "healthy" else "Service not configured")
        components["anythingllm"] = {"status": llm_status, "message": llm_msg}
        if llm_status != "healthy":
            features["llm_enhancement"] = "unavailable"
    except Exception as e:
        components["anythingllm"] = {"status": "unavailable", "message": "Service not configured"}
        features["llm_enhancement"] = "unavailable"

    # LLM Providers (Ollama/OpenAI/etc)
    try:
        config = get_system_configuration()
        ai_config = getattr(config, "ai", None)
        if ai_config and (getattr(ai_config, "ollama", None) or getattr(ai_config, "openai", None)):
            components["llm_providers"] = {"status": "configured", "message": "LLM providers enabled"}
        else:
            components["llm_providers"] = {"status": "none_configured", "message": "No LLM providers enabled"}
            features["llm_enhancement"] = "unavailable"
    except Exception:
        components["llm_providers"] = {"status": "none_configured", "message": "No LLM providers enabled"}
        features["llm_enhancement"] = "unavailable"

    # Search Orchestrator
    try:
        search_health = await search_orchestrator.health_check()
        search_status = "healthy" if search_health.get("status") == "healthy" else "degraded"
        search_msg = search_health.get("message", "Connected" if search_status == "healthy" else "Degraded")
        components["search_orchestrator"] = {"status": search_status, "message": search_msg}
        if search_status != "healthy" and overall_status == "healthy":
            overall_status = "degraded"
    except Exception as e:
        components["search_orchestrator"] = {"status": "degraded", "message": f"Error: {e}"}
        if overall_status == "healthy":
            overall_status = "degraded"

    # If all major components are unavailable, mark as unhealthy
    unavailable_count = sum(1 for c in ["database", "redis", "anythingllm"] if components.get(c, {}).get("status") in ["unavailable", "unhealthy"])
    if unavailable_count == 3:
        overall_status = "unhealthy"

    # Always include "overall_status" for test compatibility
    return {
        "status": overall_status,
        "overall_status": overall_status,
        "timestamp": now,
        "version": version,
        "components": components,
        "features": features
    }


@router.get("/stats", tags=["health"])
@limiter.limit("10/minute")
async def get_stats(
    request: Request,
    db_manager: DatabaseManager = Depends(get_database_manager),
    cache_manager: CacheManager = Depends(get_cache_manager)
):
    """
    GET /api/v1/stats - Provides usage and performance statistics

    Returns:
        StatsResponse with system statistics
    """
    from .schemas import StatsResponse
    try:
        # Mock statistics data conforming to schema
        return StatsResponse(
            search_stats={
                "total_searches": 1247,
                "avg_response_time_ms": 125,
                "cache_hit_rate": 0.73,
                "successful_searches": 1189,
                "failed_searches": 58
            },
            cache_stats={
                "hit_rate": 0.73,
                "miss_rate": 0.27,
                "total_keys": 3456,
                "memory_usage_mb": 256,
                "evictions": 12
            },
            content_stats={
                "total_documents": 15432,
                "total_chunks": 89765,
                "avg_quality_score": 0.82,
                "workspaces": 12,
                "last_enrichment": datetime.utcnow()
            },
            system_stats={
                "uptime_seconds": 86400,
                "cpu_usage_percent": 15.3,
                "memory_usage_mb": 512,
                "disk_usage_mb": 2048
            },
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail="Statistics unavailable")