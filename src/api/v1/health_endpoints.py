"""
Health API Endpoints - PRD-001: HTTP API Foundation
Health check and statistics endpoints
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from fastapi import APIRouter, Depends, Request, Query

from .middleware import get_trace_id
from .schemas import StatsResponse
from .dependencies import (
    get_database_manager,
    get_cache_manager,
    get_weaviate_client,
    get_search_orchestrator,
)
from src.database.connection import DatabaseManager, CacheManager
from src.clients.weaviate_client import WeaviateVectorClient
from src.search.orchestrator import SearchOrchestrator
from src.core.config import get_system_configuration

logger = logging.getLogger(__name__)

# Import enhanced logging for health monitoring
try:
    from src.logging_config import ExternalServiceLogger, MetricsLogger
    _service_logger = ExternalServiceLogger(logger)
    _metrics_logger = MetricsLogger(logger)
except ImportError:
    _service_logger = None
    _metrics_logger = None
    logger.warning("Enhanced health monitoring logging not available")

# Create router for health endpoints
router = APIRouter()


@router.get("/health", tags=["health"])
async def health_check(
    db_manager: DatabaseManager = Depends(get_database_manager),
    cache_manager: CacheManager = Depends(get_cache_manager),
    weaviate_client: WeaviateVectorClient = Depends(get_weaviate_client),
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator),
):
    """
    GET /api/v1/health - Reports the health of the system and its dependencies

    Returns:
        JSON with overall status, component statuses, features, timestamp, and version.
    """
    # Always return HTTP 200
    services = []
    overall_status = "healthy"
    now = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()

    # Database
    try:
        db_health = await db_manager.health_check()
        db_status = "healthy" if db_health.get("status") == "healthy" else "unhealthy"
        db_msg = db_health.get(
            "message", "Connected" if db_status == "healthy" else "Unknown error"
        )
        services.append({
            "service": "database",
            "status": db_status,
            "response_time_ms": db_health.get("response_time_ms"),
            "last_check": now,
            "details": {"message": db_msg}
        })
        if db_status != "healthy":
            overall_status = "degraded"
    except Exception as e:
        error_msg = f"Connection failed: {e}"
        services.append({
            "service": "database",
            "status": "unhealthy",
            "last_check": now,
            "details": {"message": error_msg, "error": str(e)}
        })
        overall_status = "degraded"

    # Redis/Cache
    try:
        cache_health = await cache_manager.health_check()
        cache_status = (
            "healthy" if cache_health.get("status") == "healthy" else "unhealthy"
        )
        cache_msg = cache_health.get(
            "message", "Connected" if cache_status == "healthy" else "Unavailable"
        )
        services.append({
            "service": "redis",
            "status": cache_status,
            "response_time_ms": cache_health.get("response_time_ms"),
            "last_check": now,
            "details": {"message": cache_msg}
        })
        if cache_status != "healthy":
            overall_status = "degraded"
    except Exception as e:
        error_msg = f"Connection failed: {e}"
        services.append({
            "service": "redis",
            "status": "unhealthy", 
            "last_check": now,
            "details": {"message": error_msg, "error": str(e)}
        })
        overall_status = "degraded"

    # Weaviate
    try:
        weaviate_health = await weaviate_client.health_check()
        weaviate_status = (
            "healthy" if weaviate_health.get("status") == "healthy" else "unhealthy"
        )
        weaviate_msg = weaviate_health.get(
            "message",
            "Connected" if weaviate_status == "healthy" else "Service not configured",
        )
        services.append({
            "service": "weaviate",
            "status": weaviate_status,
            "response_time_ms": weaviate_health.get("response_time_ms"),
            "last_check": now,
            "details": {"message": weaviate_msg}
        })
        if weaviate_status != "healthy":
            overall_status = "degraded"
    except Exception as e:
        error_msg = "Service not configured"
        services.append({
            "service": "weaviate",
            "status": "unhealthy",
            "last_check": now,
            "details": {"message": error_msg, "error": str(e)}
        })
        overall_status = "degraded"

    # LLM Providers (Ollama/OpenAI/etc)
    try:
        config = get_system_configuration()
        ai_config = getattr(config, "ai", None)
        if ai_config and (
            getattr(ai_config, "ollama", None) or getattr(ai_config, "openai", None)
        ):
            provider_status = "healthy"
            provider_msg = "LLM providers enabled"
        else:
            provider_status = "degraded"
            provider_msg = "No LLM providers enabled"
        
        services.append({
            "service": "llm_providers",
            "status": provider_status,
            "last_check": now,
            "details": {"message": provider_msg}
        })
    except Exception as e:
        error_msg = "No LLM providers enabled"
        services.append({
            "service": "llm_providers", 
            "status": "degraded",
            "last_check": now,
            "details": {"message": error_msg, "error": str(e)}
        })

    # Search Orchestrator
    try:
        search_health = await search_orchestrator.health_check()
        search_status = (
            "healthy" if search_health.get("overall_status") == "healthy" else "degraded"
        )
        search_msg = search_health.get(
            "message", "Connected" if search_status == "healthy" else f"Status: {search_health.get('overall_status', 'unknown')}"
        )
        search_details = {"message": search_msg}
        if search_status == "degraded" and search_health:
            search_details.update(search_health)
            
        services.append({
            "service": "search_orchestrator",
            "status": search_status,
            "response_time_ms": search_health.get("response_time_ms"),
            "last_check": now,
            "details": search_details
        })
        
        if search_status != "healthy" and overall_status == "healthy":
            overall_status = "degraded"
    except Exception as e:
        error_msg = f"Error: {e}"
        services.append({
            "service": "search_orchestrator",
            "status": "unhealthy",
            "last_check": now,
            "details": {"message": error_msg, "error": str(e)}
        })
        if overall_status == "healthy":
            overall_status = "degraded"

    # If all major components are unavailable, mark as unhealthy
    unavailable_count = sum(
        1
        for service in services
        if service["service"] in ["database", "redis", "weaviate"] and 
           service["status"] in ["unavailable", "unhealthy"]
    )
    if unavailable_count == 3:
        overall_status = "unhealthy"

    # Return clean response matching frontend HealthResponse schema
    return {
        "overall_status": overall_status,
        "services": services,
        "timestamp": now,
    }


@router.get("/stats", tags=["health"])
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
            COUNT(DISTINCT weaviate_workspace) as workspaces,
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
            
            system_stats = {
                "uptime_seconds": int(time.time() - psutil.boot_time()),
                "cpu_usage_percent": psutil.cpu_percent(interval=0.1),
                "memory_usage_mb": psutil.virtual_memory().used / 1024 / 1024,
                "disk_usage_mb": psutil.disk_usage('/').used / 1024 / 1024,
            }
        except ImportError:
            # psutil not installed, return defaults
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
        # Import system health check function and get system health for dashboard
        try:
            from .websocket_endpoints import check_system_health
            system_health = await check_system_health()
            logger.info(f"System health keys in analytics: {list(system_health.keys())}")
        except Exception as e:
            logger.error(f"System health check failed in analytics: {e}")
            import traceback
            logger.error(traceback.format_exc())
            system_health = {}
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
        
        # Get search metrics from search_cache table
        search_query = """
        SELECT 
            COUNT(*) as total_searches,
            AVG(execution_time_ms) as avg_response_time,
            1.0 as success_rate  -- All cached searches are successful
        FROM search_cache
        WHERE created_at >= :start_date AND created_at <= :end_date
        """
        search_result = await db_manager.fetch_one(
            search_query, {"start_date": start_date, "end_date": end_date}
        )
        
        # Get top queries from search_cache
        top_queries_query = """
        SELECT original_query as query_text, SUM(access_count) as count
        FROM search_cache
        WHERE created_at >= :start_date AND created_at <= :end_date
        GROUP BY original_query
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
        
        # Get user metrics from usage_signals table
        user_query = """
        SELECT 
            COUNT(DISTINCT user_session_id) as active_users,
            COUNT(DISTINCT user_session_id) as total_sessions,
            0 as avg_session_duration  -- duration not tracked in current schema
        FROM usage_signals
        WHERE created_at >= :start_date AND created_at <= :end_date
        """
        user_result = await db_manager.fetch_one(
            user_query, {"start_date": start_date, "end_date": end_date}
        )
        
        return {
            "timeRange": timeRange,
            "systemHealth": system_health,
            "searchMetrics": {
                "totalSearches": search_result.get("total_searches", 0) if search_result else 0,
                "avgResponseTime": float(search_result.get("avg_response_time") or 0) if search_result else 0,
                "successRate": float(search_result.get("success_rate") or 0) if search_result else 0,
                "topQueries": [
                    {"query": q.get("query_text", ""), "count": q.get("count", 0)} 
                    for q in (top_queries or [])
                ],
            },
            "contentMetrics": {
                "totalDocuments": content_result.get("total_documents", 0) if content_result else 0,
                "totalChunks": content_result.get("total_chunks", 0) if content_result else 0,
                "avgQualityScore": float(content_result.get("avg_quality_score") or 0) if content_result else 0,
                "documentsByTechnology": [
                    {"technology": t.get("technology", ""), "count": t.get("count", 0)}
                    for t in (tech_docs or [])
                ],
            },
            "userMetrics": {
                "activeUsers": user_result.get("active_users", 0) if user_result else 0,
                "totalSessions": user_result.get("total_sessions", 0) if user_result else 0,
                "avgSessionDuration": float(user_result.get("avg_session_duration") or 0) if user_result else 0,
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


@router.get("/registry-test")
async def test_registry_route():
    """Simple test route to verify route registration works"""
    try:
        from src.llm import get_provider_registry, REGISTRY_AVAILABLE
        if hasattr(get_provider_registry, '__name__'):
            return {
                "route_registration": "working",
                "registry_import": "success",
                "registry_available": True
            }
    except Exception as e:
        return {
            "route_registration": "working", 
            "registry_import": "failed",
            "registry_available": False,
            "error": str(e)
        }


@router.get("/monitoring", tags=["health"])
async def get_monitoring_info():
    """
    GET /api/v1/monitoring - Get monitoring endpoints and dashboard information
    
    Returns:
        Information about available monitoring services and dashboards
    """
    return {
        "services": {
            "grafana": {
                "url": "/grafana",
                "default_credentials": {
                    "username": "admin",
                    "password": "admin"
                },
                "dashboards": [
                    {
                        "name": "DocAIche System Overview",
                        "uid": "docaiche-overview",
                        "description": "Overall system health and performance metrics",
                        "url": "/grafana/d/docaiche-overview/docaiche-system-overview"
                    }
                ]
            },
            "prometheus": {
                "url": "/prometheus",
                "metrics_endpoint": "/prometheus/api/v1/query",
                "targets": [
                    "docker",
                    "node-exporter",
                    "redis-exporter",
                    "loki",
                    "grafana"
                ]
            },
            "loki": {
                "url": "/loki",
                "query_endpoint": "/loki/loki/api/v1/query_range",
                "labels": [
                    "service_name",
                    "container_name",
                    "level",
                    "job"
                ]
            }
        },
        "internal_endpoints": {
            "logs": "/api/v1/logs",
            "containers": "/api/v1/containers",
            "metrics": "/api/v1/metrics",
            "alerts": "/api/v1/alerts"
        },
        "features": {
            "log_aggregation": True,
            "metrics_collection": True,
            "container_management": False,  # Not implemented yet
            "ssh_access": False,  # Not implemented yet
            "real_time_logs": False  # Not implemented yet
        },
        "timestamp": datetime.utcnow().isoformat()
    }
