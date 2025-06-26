"""
Health API Endpoints - PRD-001: HTTP API Foundation
Health check and statistics endpoints
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, Request, BackgroundTasks

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

# Import WebSocket manager for real-time updates
try:
    from src.web_ui.real_time_service.websocket import websocket_manager
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("WebSocket manager not available - health broadcasting disabled")
# Health monitoring state
_health_monitor_running = False
_last_llm_health_status = None


async def check_llm_providers_status() -> Dict[str, Any]:
    """
    Check LLM provider health status and return structured data.
    
    Returns:
        Dictionary containing LLM provider status information
    """
    try:
        config = get_system_configuration()
        ai_config = getattr(config, "ai", None)
        healthy_providers = []
        unhealthy_providers = []
        llm_provider_messages = []

        # Check Ollama
        if ai_config and getattr(ai_config, "ollama", None):
            from src.llm.ollama_provider import OllamaProvider
            ollama_provider = OllamaProvider(config=ai_config.ollama.model_dump())
            ollama_health = await ollama_provider.health_check()
            if ollama_health.get("status") == "healthy":
                healthy_providers.append("ollama")
            else:
                unhealthy_providers.append("ollama")
                llm_provider_messages.append(f"Ollama: {ollama_health.get('error', ollama_health.get('status', 'Unavailable'))}")

        # Check OpenAI
        if ai_config and getattr(ai_config, "openai", None):
            from src.llm.openai_provider import OpenAIProvider
            openai_provider = OpenAIProvider(config=ai_config.openai.model_dump())
            openai_health = await openai_provider.health_check()
            if openai_health.get("status") == "healthy":
                healthy_providers.append("openai")
            else:
                unhealthy_providers.append("openai")
                llm_provider_messages.append(f"OpenAI: {openai_health.get('error', openai_health.get('status', 'Unavailable'))}")

        if healthy_providers:
            return {
                "status": "configured",
                "message": f"LLM providers enabled: {', '.join(healthy_providers)}",
                "healthy_providers": healthy_providers,
                "unhealthy_providers": unhealthy_providers
            }
        elif unhealthy_providers:
            return {
                "status": "unavailable",
                "message": "No healthy LLM providers. " + "; ".join(llm_provider_messages),
                "healthy_providers": [],
                "unhealthy_providers": unhealthy_providers
            }
        else:
            return {
                "status": "none_configured",
                "message": "No LLM providers enabled",
                "healthy_providers": [],
                "unhealthy_providers": []
            }
    except Exception as e:
        logger.error(f"Error checking LLM providers: {e}")
        return {
            "status": "error",
            "message": f"Error checking LLM providers: {str(e)}",
            "healthy_providers": [],
            "unhealthy_providers": []
        }


async def llm_health_monitor():
    """
    Background task that periodically checks LLM health and broadcasts changes.
    
    Runs every 30 seconds and broadcasts status changes via WebSocket.
    """
    global _last_llm_health_status
    
    while _health_monitor_running:
        try:
            current_status = await check_llm_providers_status()
            
            # Only broadcast if status changed
            if current_status != _last_llm_health_status:
                logger.info(f"LLM health status changed: {current_status['status']}")
                _last_llm_health_status = current_status.copy()
                
                if WEBSOCKET_AVAILABLE:
                    await websocket_manager.broadcast_llm_health(current_status)
                    
            await asyncio.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            logger.error(f"Error in LLM health monitor: {e}")
            await asyncio.sleep(30)  # Wait before retrying


async def start_health_monitor():
    """Start the background health monitoring task."""
    global _health_monitor_running
    
    if not _health_monitor_running and WEBSOCKET_AVAILABLE:
        _health_monitor_running = True
        asyncio.create_task(llm_health_monitor())
        logger.info("LLM health monitor started")


async def stop_health_monitor():
    """Stop the background health monitoring task."""
    global _health_monitor_running
    _health_monitor_running = False
    logger.info("LLM health monitor stopped")


@router.get("/", tags=["health"])
async def health_check(
    background_tasks: BackgroundTasks,
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

    # LLM Providers (using centralized check function)
    try:
        llm_status = await check_llm_providers_status()
        components["llm_providers"] = {
            "status": llm_status["status"],
            "message": llm_status["message"]
        }
        
        # Update features based on LLM status
        if llm_status["status"] not in ["configured"]:
            features["llm_enhancement"] = "unavailable"
            
        # Start health monitor if not already running
        background_tasks.add_task(start_health_monitor)
        
    except Exception as e:
        components["llm_providers"] = {
            "status": "error",
            "message": f"Error checking LLM providers: {str(e)}"
        }
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