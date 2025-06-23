"""
Health API Endpoints - PRD-001: HTTP API Foundation
Health check and statistics endpoints
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request

from .schemas import HealthResponse, HealthStatus, StatsResponse
from .middleware import limiter
from .dependencies import (
    get_database_manager, get_cache_manager, get_anythingllm_client, get_search_orchestrator
)
from src.database.connection import DatabaseManager, CacheManager
from src.clients.anythingllm import AnythingLLMClient
from src.search.orchestrator import SearchOrchestrator

logger = logging.getLogger(__name__)

# Create router for health endpoints
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check(
    db_manager: DatabaseManager = Depends(get_database_manager),
    cache_manager: CacheManager = Depends(get_cache_manager),
    anythingllm_client: AnythingLLMClient = Depends(get_anythingllm_client),
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator)
) -> HealthResponse:
    """
    GET /api/v1/health - Reports the health of the system and its dependencies
    
    Enhanced health endpoint with HealthResponse schema integration.
    
    Args:
        db_manager: Database manager dependency
        cache_manager: Cache manager dependency
        anythingllm_client: AnythingLLM client dependency
        search_orchestrator: Search orchestrator dependency
        
    Returns:
        HealthResponse with overall status and service details
    """
    try:
        services = []
        overall_status = "healthy"
        
        # Check database health
        try:
            db_health = await db_manager.health_check()
            services.append(HealthStatus(
                service="database",
                status="healthy" if db_health.get("status") == "healthy" else "unhealthy",
                response_time_ms=None,
                last_check=datetime.utcnow(),
                details=db_health
            ))
        except Exception as e:
            services.append(HealthStatus(
                service="database",
                status="unhealthy",
                response_time_ms=None,
                last_check=datetime.utcnow(),
                details={"error": str(e)}
            ))
            overall_status = "degraded"
        
        # Check cache health
        try:
            cache_health = await cache_manager.health_check()
            cache_status = "healthy" if cache_health.get("status") == "healthy" else "degraded"
            services.append(HealthStatus(
                service="cache",
                status=cache_status,
                response_time_ms=None,
                last_check=datetime.utcnow(),
                details=cache_health
            ))
            # Cache degradation doesn't affect overall status severely
        except Exception as e:
            services.append(HealthStatus(
                service="cache",
                status="degraded",
                response_time_ms=None,
                last_check=datetime.utcnow(),
                details={"error": str(e)}
            ))
        
        # Check AnythingLLM health
        try:
            llm_health = await anythingllm_client.health_check()
            services.append(HealthStatus(
                service="anythingllm",
                status="healthy" if llm_health.get("status") == "healthy" else "unhealthy",
                response_time_ms=None,
                last_check=datetime.utcnow(),
                details=llm_health
            ))
        except Exception as e:
            services.append(HealthStatus(
                service="anythingllm",
                status="unhealthy",
                response_time_ms=None,
                last_check=datetime.utcnow(),
                details={"error": str(e)}
            ))
            overall_status = "degraded"
        
        # Check search orchestrator health
        try:
            search_health = await search_orchestrator.health_check()
            services.append(HealthStatus(
                service="search_orchestrator",
                status="healthy" if search_health.get("status") == "healthy" else "degraded",
                response_time_ms=None,
                last_check=datetime.utcnow(),
                details=search_health
            ))
        except Exception as e:
            services.append(HealthStatus(
                service="search_orchestrator",
                status="degraded",
                response_time_ms=None,
                last_check=datetime.utcnow(),
                details={"error": str(e)}
            ))
            if overall_status == "healthy":
                overall_status = "degraded"
        
        return HealthResponse(
            overall_status=overall_status,
            services=services,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            overall_status="unhealthy",
            services=[],
            timestamp=datetime.utcnow()
        )


@router.get("/stats", response_model=StatsResponse, tags=["health"])
@limiter.limit("10/minute")
async def get_stats(
    request: Request,
    db_manager: DatabaseManager = Depends(get_database_manager),
    cache_manager: CacheManager = Depends(get_cache_manager)
) -> StatsResponse:
    """
    GET /api/v1/stats - Provides usage and performance statistics
    
    Args:
        request: FastAPI request object (required for rate limiting)
        db_manager: Database manager dependency
        cache_manager: Cache manager dependency
        
    Returns:
        StatsResponse with system statistics
    """
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
        raise HTTPException(status_code=500, detail="Statistics unavailable")