"""
Health API Endpoints - PRD-001: HTTP API Foundation
Health check and statistics endpoints
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, Request, Query

from .middleware import limiter
from .dependencies import (
    get_database_manager,
    get_cache_manager,
    get_anythingllm_client,
    get_search_orchestrator,
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
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator),
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
        "llm_enhancement": "available",
    }
    overall_status = "healthy"
    version = "1.0.0"
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

    # Database
    try:
        db_health = await db_manager.health_check()
        db_status = "healthy" if db_health.get("status") == "healthy" else "unhealthy"
        db_msg = db_health.get(
            "message", "Connected" if db_status == "healthy" else "Unknown error"
        )
        components["database"] = {"status": db_status, "message": db_msg}
        if db_status != "healthy":
            overall_status = "degraded"
    except Exception as e:
        components["database"] = {
            "status": "unavailable",
            "message": f"Connection failed: {e}",
        }
        overall_status = "degraded"

    # Redis/Cache
    try:
        cache_health = await cache_manager.health_check()
        cache_status = (
            "healthy" if cache_health.get("status") == "healthy" else "unavailable"
        )
        cache_msg = cache_health.get(
            "message", "Connected" if cache_status == "healthy" else "Unavailable"
        )
        components["redis"] = {"status": cache_status, "message": cache_msg}
        if cache_status != "healthy":
            overall_status = "degraded"
            features["search"] = "unavailable"
    except Exception as e:
        components["redis"] = {
            "status": "unavailable",
            "message": f"Connection failed: {e}",
        }
        overall_status = "degraded"
        features["search"] = "unavailable"

    # AnythingLLM
    try:
        llm_health = await anythingllm_client.health_check()
        llm_status = (
            "healthy" if llm_health.get("status") == "healthy" else "unavailable"
        )
        llm_msg = llm_health.get(
            "message",
            "Connected" if llm_status == "healthy" else "Service not configured",
        )
        components["anythingllm"] = {"status": llm_status, "message": llm_msg}
        if llm_status != "healthy":
            features["llm_enhancement"] = "unavailable"
    except Exception:
        components["anythingllm"] = {
            "status": "unavailable",
            "message": "Service not configured",
        }
        features["llm_enhancement"] = "unavailable"

    # LLM Providers (Ollama/OpenAI/etc)
    try:
        config = get_system_configuration()
        ai_config = getattr(config, "ai", None)
        if ai_config and (
            getattr(ai_config, "ollama", None) or getattr(ai_config, "openai", None)
        ):
            components["llm_providers"] = {
                "status": "configured",
                "message": "LLM providers enabled",
            }
        else:
            components["llm_providers"] = {
                "status": "none_configured",
                "message": "No LLM providers enabled",
            }
            features["llm_enhancement"] = "unavailable"
    except Exception:
        components["llm_providers"] = {
            "status": "none_configured",
            "message": "No LLM providers enabled",
        }
        features["llm_enhancement"] = "unavailable"

    # Search Orchestrator
    try:
        search_health = await search_orchestrator.health_check()
        search_status = (
            "healthy" if search_health.get("status") == "healthy" else "degraded"
        )
        search_msg = search_health.get(
            "message", "Connected" if search_status == "healthy" else "Degraded"
        )
        components["search_orchestrator"] = {
            "status": search_status,
            "message": search_msg,
        }
        if search_status != "healthy" and overall_status == "healthy":
            overall_status = "degraded"
    except Exception as e:
        components["search_orchestrator"] = {
            "status": "degraded",
            "message": f"Error: {e}",
        }
        if overall_status == "healthy":
            overall_status = "degraded"

    # If all major components are unavailable, mark as unhealthy
    unavailable_count = sum(
        1
        for c in ["database", "redis", "anythingllm"]
        if components.get(c, {}).get("status") in ["unavailable", "unhealthy"]
    )
    if unavailable_count == 3:
        overall_status = "unhealthy"

    # Always include "overall_status" for test compatibility
    return {
        "status": overall_status,
        "overall_status": overall_status,
        "timestamp": now,
        "version": version,
        "components": components,
        "features": features,
    }


@router.get("/stats", tags=["health"])
@limiter.limit("10/minute")
async def get_stats(
    request: Request,
    db_manager: DatabaseManager = Depends(get_database_manager),
    cache_manager: CacheManager = Depends(get_cache_manager),
):
    """
    GET /api/v1/stats - Provides usage and performance statistics

    Returns:
        StatsResponse with system statistics
    """
    from .schemas import StatsResponse

    try:
        # Get real search statistics from database
        # Using search_cache table which is what we have in our schema
        search_stats_query = """
        SELECT 
            COUNT(*) as total_searches
        FROM search_cache
        """
        try:
            search_result = await db_manager.fetch_one(search_stats_query)
        except Exception as e:
            logger.warning(f"Failed to query search_cache table: {e}")
            search_result = None
        
        search_stats = {
            "total_searches": search_result.get("total_searches", 0) if search_result else 0,
            "avg_response_time_ms": 0,  # Not available in current schema
            "cache_hit_rate": 0,  # Would need to be calculated from cache_entries
            "successful_searches": search_result.get("total_searches", 0) if search_result else 0,  # Assume all are successful
            "failed_searches": 0,  # Not tracked in current schema
        }
        
        # Get real cache statistics
        cache_stats = {}
        if cache_manager:
            try:
                cache_info = await cache_manager.get_stats()
                cache_stats = {
                    "hit_rate": cache_info.get("hit_rate", 0),
                    "miss_rate": cache_info.get("miss_rate", 0),
                    "total_keys": cache_info.get("total_keys", 0),
                    "memory_usage_mb": cache_info.get("memory_usage_mb", 0),
                    "evictions": cache_info.get("evictions", 0),
                }
            except:
                cache_stats = {
                    "hit_rate": 0,
                    "miss_rate": 0,
                    "total_keys": 0,
                    "memory_usage_mb": 0,
                    "evictions": 0,
                }
        
        # Get real content statistics using correct field names from our schema
        content_stats_query = """
        SELECT 
            COUNT(DISTINCT content_id) as total_documents,
            SUM(chunk_count) as total_chunks,
            AVG(quality_score) as avg_quality_score,
            COUNT(DISTINCT anythingllm_workspace) as workspaces,
            MAX(updated_at) as last_enrichment
        FROM content_metadata
        """
        try:
            content_result = await db_manager.fetch_one(content_stats_query)
        except Exception as e:
            logger.warning(f"Failed to query content_metadata table: {e}")
            content_result = None
        
        content_stats = {
            "total_documents": content_result.get("total_documents", 0) if content_result else 0,
            "total_chunks": content_result.get("total_chunks", 0) if content_result else 0,
            "avg_quality_score": float(content_result.get("avg_quality_score", 0)) if content_result and content_result.get("avg_quality_score") is not None else 0,
            "workspaces": content_result.get("workspaces", 0) if content_result else 0,
            "last_enrichment": content_result.get("last_enrichment") or datetime.utcnow() if content_result else datetime.utcnow(),
        }
        
        # Get real system statistics
        try:
            import psutil
            import time
            
            system_stats = {
                "uptime_seconds": int(time.time() - psutil.boot_time()),
                "cpu_usage_percent": psutil.cpu_percent(interval=0.1),
                "memory_usage_mb": psutil.virtual_memory().used / 1024 / 1024,
                "disk_usage_mb": psutil.disk_usage('/').used / 1024 / 1024,
            }
        except ImportError:
            # psutil not installed, return defaults
            import time
            system_stats = {
                "uptime_seconds": int(time.time()),
                "cpu_usage_percent": 0,
                "memory_usage_mb": 0,
                "disk_usage_mb": 0,
            }
        
        return StatsResponse(
            search_stats=search_stats,
            cache_stats=cache_stats,
            content_stats=content_stats,
            system_stats=system_stats,
            timestamp=datetime.utcnow(),
        )
    except Exception as e:
        logger.error(f"Stats retrieval failed: {e}")
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail="Statistics unavailable")


@router.get("/analytics", tags=["analytics"])
@limiter.limit("30/minute")
async def get_analytics(
    request: Request,
    timeRange: str = Query(
        "24h", description="Time range for analytics (24h, 7d, 30d)"
    ),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> Dict[str, Any]:
    """
    GET /api/v1/analytics - Get system analytics data
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow()
        if timeRange == "24h":
            start_date = end_date - timedelta(hours=24)
        elif timeRange == "7d":
            start_date = end_date - timedelta(days=7)
        elif timeRange == "30d":
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(hours=24)
        
        # Get search metrics
        search_query = """
        SELECT 
            COUNT(*) as total_searches,
            AVG(response_time_ms) as avg_response_time,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as success_rate
        FROM search_queries
        WHERE created_at >= :start_date AND created_at <= :end_date
        """
        search_result = await db_manager.fetch_one(
            search_query, {"start_date": start_date, "end_date": end_date}
        )
        
        # Get top queries
        top_queries_query = """
        SELECT query_text, COUNT(*) as count
        FROM search_queries
        WHERE created_at >= :start_date AND created_at <= :end_date
        GROUP BY query_text
        ORDER BY count DESC
        LIMIT 5
        """
        top_queries = await db_manager.fetch_all(
            top_queries_query, {"start_date": start_date, "end_date": end_date}
        )
        
        # Get content metrics
        content_query = """
        SELECT 
            COUNT(DISTINCT content_id) as total_documents,
            COUNT(*) as total_chunks,
            AVG(quality_score) as avg_quality_score
        FROM content_metadata
        WHERE created_at >= :start_date AND created_at <= :end_date
        """
        content_result = await db_manager.fetch_one(
            content_query, {"start_date": start_date, "end_date": end_date}
        )
        
        # Get documents by technology
        tech_query = """
        SELECT technology, COUNT(*) as count
        FROM content_metadata
        WHERE created_at >= :start_date AND created_at <= :end_date
        GROUP BY technology
        ORDER BY count DESC
        LIMIT 5
        """
        tech_docs = await db_manager.fetch_all(
            tech_query, {"start_date": start_date, "end_date": end_date}
        )
        
        # Get user metrics (from usage_signals table)
        user_query = """
        SELECT 
            COUNT(DISTINCT user_id) as active_users,
            COUNT(DISTINCT session_id) as total_sessions,
            AVG(duration_ms) as avg_session_duration
        FROM usage_signals
        WHERE timestamp >= :start_date AND timestamp <= :end_date
        """
        user_result = await db_manager.fetch_one(
            user_query, {"start_date": start_date, "end_date": end_date}
        )
        
        return {
            "timeRange": timeRange,
            "searchMetrics": {
                "totalSearches": search_result.get("total_searches", 0) if search_result else 0,
                "avgResponseTime": float(search_result.get("avg_response_time", 0)) if search_result else 0,
                "successRate": float(search_result.get("success_rate", 0)) if search_result else 0,
                "topQueries": [
                    {"query": q.get("query_text", ""), "count": q.get("count", 0)} 
                    for q in (top_queries or [])
                ],
            },
            "contentMetrics": {
                "totalDocuments": content_result.get("total_documents", 0) if content_result else 0,
                "totalChunks": content_result.get("total_chunks", 0) if content_result else 0,
                "avgQualityScore": float(content_result.get("avg_quality_score", 0)) if content_result else 0,
                "documentsByTechnology": [
                    {"technology": t.get("technology", ""), "count": t.get("count", 0)}
                    for t in (tech_docs or [])
                ],
            },
            "userMetrics": {
                "activeUsers": user_result.get("active_users", 0) if user_result else 0,
                "totalSessions": user_result.get("total_sessions", 0) if user_result else 0,
                "avgSessionDuration": float(user_result.get("avg_session_duration", 0)) if user_result else 0,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to get analytics: {e}")
        return {
            "error": "Failed to get analytics data",
            "timeRange": timeRange,
            "timestamp": datetime.utcnow().isoformat(),
        }
