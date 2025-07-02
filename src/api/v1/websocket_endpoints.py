"""
WebSocket endpoints for real-time data streaming.

Provides WebSocket connections for:
- Real-time analytics updates
- Activity feed streaming
- System health monitoring
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Set, Optional
import psutil
import docker
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse

from ...database.models import SearchCache, ContentMetadata, FeedbackEvents, UsageSignals
from .dependencies import get_database_manager, get_cache_manager, get_weaviate_client, get_search_orchestrator


logger = logging.getLogger(__name__)

router = APIRouter()

# Store active WebSocket connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.analytics_connections: Set[WebSocket] = set()
        self.health_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, connection_type: str = "general"):
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if connection_type == "analytics":
            self.analytics_connections.add(websocket)
        elif connection_type == "health":
            self.health_connections.add(websocket)
            
        logger.info(f"WebSocket connected: {connection_type}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        self.analytics_connections.discard(websocket)
        self.health_connections.discard(websocket)
        logger.info("WebSocket disconnected")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def send_json(self, data: dict, websocket: WebSocket):
        await websocket.send_json(data)

    async def broadcast_analytics(self, data: dict):
        """Broadcast analytics data to all connected analytics clients."""
        disconnected = set()
        for connection in self.analytics_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.error(f"Error broadcasting to websocket: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_health(self, data: dict):
        """Broadcast health data to all connected health monitoring clients."""
        disconnected = set()
        for connection in self.health_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                logger.error(f"Error broadcasting to websocket: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()


async def get_system_health_quick():
    """Get basic system health quickly - only essential checks."""
    import redis
    import aiohttp
    import time
    from src.core.config import get_system_configuration
    
    health_status = {}
    
    # Quick database check
    try:
        db_manager = await get_database_manager()
        start = time.time()
        db_health = await db_manager.health_check()
        response_time = int((time.time() - start) * 1000)
        
        health_status["database"] = {
            "status": "healthy" if db_health.get("status") == "healthy" else "unhealthy",
            "message": db_health.get("message", "Database operational"),
            "response_time": response_time,
            "group": "infrastructure"
        }
    except Exception as e:
        health_status["database"] = {
            "status": "unhealthy",
            "message": f"Connection failed",
            "group": "infrastructure"
        }
    
    # Quick Redis check
    try:
        cache_manager = await get_cache_manager()
        start = time.time()
        cache_health = await cache_manager.health_check()
        response_time = int((time.time() - start) * 1000)
        
        health_status["cache"] = {
            "status": "healthy" if cache_health.get("status") == "healthy" else "unhealthy",
            "message": cache_health.get("message", "Cache operational"),
            "response_time": response_time,
            "group": "infrastructure"
        }
    except Exception as e:
        health_status["cache"] = {
            "status": "unhealthy",
            "message": f"Cache unavailable",
            "group": "infrastructure"
        }
    
    # Quick API status based on db and cache
    db_status = health_status.get("database", {}).get("status")
    cache_status = health_status.get("cache", {}).get("status")
    
    if db_status == "healthy" and cache_status == "healthy":
        health_status["api_core"] = {
            "status": "healthy",
            "message": "API core services operational",
            "group": "infrastructure"
        }
    else:
        health_status["api_core"] = {
            "status": "degraded",
            "message": "API running with limited functionality",
            "group": "infrastructure"
        }
    
    return health_status


async def get_basic_analytics_stats():
    """Get basic statistics quickly."""
    db_manager = await get_database_manager()
    
    async with db_manager.session_factory() as session:
        # Get basic counts in parallel
        results = await asyncio.gather(
            session.scalar(select(func.count()).select_from(SearchCache)),
            session.scalar(select(func.avg(SearchCache.execution_time_ms)).select_from(SearchCache)),
            session.scalar(select(func.count()).select_from(ContentMetadata)),
            return_exceptions=True
        )
        
        total_searches = results[0] if not isinstance(results[0], Exception) else 0
        avg_response_time = results[1] if not isinstance(results[1], Exception) else 0
        total_documents = results[2] if not isinstance(results[2], Exception) else 0
        
        return {
            "search_stats": {
                "total_searches": total_searches or 0,
                "avg_response_time_ms": float(avg_response_time) if avg_response_time else 0,
            },
            "content_stats": {
                "total_documents": total_documents or 0,
                "total_chunks": (total_documents or 0) * 10,  # Estimate
            }
        }


async def get_detailed_analytics_data(time_range: str = "24h"):
    """Get detailed analytics data - may take longer."""
    now = datetime.utcnow()
    if time_range == "30d":
        start_time = now - timedelta(days=30)
    elif time_range == "7d":
        start_time = now - timedelta(days=7)
    else:  # 24h
        start_time = now - timedelta(hours=24)
    
    db_manager = await get_database_manager()
    async with db_manager.session_factory() as session:
        # Get search metrics
        search_count = await session.scalar(
            select(func.count()).select_from(SearchCache)
            .where(SearchCache.created_at >= start_time)
        ) or 0
        
        # Get top queries
        top_queries_result = await session.execute(
            select(
                SearchCache.original_query,
                func.count().label('count')
            )
            .where(SearchCache.created_at >= start_time)
            .group_by(SearchCache.original_query)
            .order_by(desc('count'))
            .limit(10)
        )
        top_queries = [
            {"query": row[0], "count": row[1]} 
            for row in top_queries_result
        ]
        
        # Get queries by hour (last 24 hours) - this is expensive
        hourly_stats = []
        for i in range(24):
            hour_start = now - timedelta(hours=i+1)
            hour_end = now - timedelta(hours=i)
            
            hour_data = await session.execute(
                select(
                    func.count().label('count'),
                    func.avg(SearchCache.execution_time_ms).label('avg_time')
                )
                .select_from(SearchCache)
                .where(and_(
                    SearchCache.created_at >= hour_start,
                    SearchCache.created_at < hour_end
                ))
            )
            row = hour_data.first()
            hourly_stats.append({
                "count": row.count if row else 0,
                "responseTime": float(row.avg_time) if row and row.avg_time else 0
            })
        
        # Get document distribution by technology
        tech_distribution = await session.execute(
            select(
                ContentMetadata.technology,
                func.count().label('count')
            )
            .group_by(ContentMetadata.technology)
            .order_by(desc('count'))
            .limit(10)
        )
        docs_by_tech = [
            {"technology": row[0] or "Unknown", "count": row[1]}
            for row in tech_distribution
        ]
        
        # Calculate success rate
        searches_with_results = await session.scalar(
            select(func.count()).select_from(SearchCache)
            .where(and_(
                SearchCache.created_at >= start_time,
                SearchCache.result_count > 0
            ))
        ) or 0
        
        success_rate = (searches_with_results / search_count) if search_count > 0 else 0
        
        return {
            "timeRange": time_range,
            "searchMetrics": {
                "totalSearches": search_count,
                "successRate": success_rate,
                "topQueries": top_queries,
                "queriesByHour": list(reversed(hourly_stats)),
            },
            "contentMetrics": {
                "documentsByTechnology": docs_by_tech,
            }
        }




async def get_core_infrastructure_health():
    """Get core infrastructure health - database, cache, API core."""
    import redis
    import time
    
    health_status = {}
    
    # Database Health Check
    try:
        db_manager = await get_database_manager()
        start = time.time()
        db_health = await db_manager.health_check()
        response_time = int((time.time() - start) * 1000)
        
        health_status["database"] = {
            "status": "healthy" if db_health.get("status") == "healthy" else "unhealthy",
            "message": db_health.get("message", "Database operational"),
            "response_time": response_time,
            "group": "infrastructure"
        }
    except Exception as e:
        health_status["database"] = {
            "status": "unhealthy",
            "message": f"Connection failed: {str(e)[:100]}",
            "group": "infrastructure"
        }
    
    # Redis/Cache Health Check
    try:
        cache_manager = await get_cache_manager()
        start = time.time()
        cache_health = await cache_manager.health_check()
        response_time = int((time.time() - start) * 1000)
        
        health_status["cache"] = {
            "status": "healthy" if cache_health.get("status") == "healthy" else "unhealthy",
            "message": cache_health.get("message", "Cache operational"),
            "response_time": response_time,
            "group": "infrastructure"
        }
    except Exception as e:
        health_status["cache"] = {
            "status": "unhealthy",
            "message": f"Cache unavailable: {str(e)[:50]}",
            "group": "infrastructure"
        }
    
    # API Core Health Check
    try:
        start_time = time.time()
        db_status = health_status.get("database", {}).get("status")
        cache_status = health_status.get("cache", {}).get("status") 
        response_time = int((time.time() - start_time) * 1000)
        
        if db_status == "healthy" and cache_status == "healthy":
            health_status["api_core"] = {
                "status": "healthy",
                "message": "All API endpoints responsive",
                "response_time": response_time,
                "group": "infrastructure"
            }
        else:
            health_status["api_core"] = {
                "status": "degraded",
                "message": "API running with limited functionality",
                "response_time": response_time,
                "group": "infrastructure"
            }
    except Exception as e:
        health_status["api_core"] = {
            "status": "unhealthy",
            "message": "API core services unavailable",
            "group": "infrastructure"
        }
    
    return health_status


async def get_search_ai_health():
    """Get search and AI services health - vector store, AI providers, search service."""
    import aiohttp
    import time
    from src.core.config import get_system_configuration
    
    health_status = {}
    
    # Vector Store (Weaviate) Health Check
    try:
        weaviate_client = await get_weaviate_client()
        weaviate_health = await weaviate_client.health_check()
        health_status["vector_store"] = {
            "status": "healthy" if weaviate_health.get("status") == "healthy" else "degraded",
            "message": weaviate_health.get("message", "Vector store operational"),
            "response_time": weaviate_health.get("response_time_ms"),
            "group": "search_ai"
        }
    except Exception as e:
        health_status["vector_store"] = {
            "status": "degraded",
            "message": "Vector store not configured or unreachable",
            "group": "search_ai"
        }
    
    # AI Text Providers Health Check
    try:
        config = get_system_configuration()
        ai_config = getattr(config, "ai", None)
        
        # Check if any AI providers are configured
        ollama_enabled = bool(ai_config and getattr(ai_config, "ollama", None))
        openai_enabled = bool(ai_config and getattr(ai_config, "openai", None))
        anthropic_enabled = bool(ai_config and getattr(ai_config, "anthropic", None))
        
        provider_count = sum([ollama_enabled, openai_enabled, anthropic_enabled])
        
        if provider_count > 0:
            health_status["text_ai_providers"] = {
                "status": "healthy",
                "message": f"{provider_count} AI provider(s) configured and available",
                "details": {
                    "ollama": "enabled" if ollama_enabled else "disabled",
                    "openai": "enabled" if openai_enabled else "disabled", 
                    "anthropic": "enabled" if anthropic_enabled else "disabled"
                },
                "group": "search_ai"
            }
        else:
            health_status["text_ai_providers"] = {
                "status": "degraded",
                "message": "No AI providers configured",
                "group": "search_ai"
            }
    except Exception as e:
        health_status["text_ai_providers"] = {
            "status": "degraded",
            "message": "Unable to check AI provider configuration",
            "group": "search_ai"
        }
    
    # Search Orchestrator Health Check
    try:
        search_orchestrator = await get_search_orchestrator()
        search_health = await search_orchestrator.health_check()
        
        # Determine overall search capability
        vector_status = health_status.get("vector_store", {}).get("status")
        ai_status = health_status.get("text_ai_providers", {}).get("status")
        
        if search_health.get("overall_status") == "healthy" and vector_status == "healthy" and ai_status == "healthy":
            health_status["search_service"] = {
                "status": "healthy",
                "message": "Full search capabilities available",
                "response_time": search_health.get("response_time_ms"),
                "group": "search_ai"
            }
        elif search_health.get("overall_status") == "healthy":
            health_status["search_service"] = {
                "status": "degraded", 
                "message": "Basic search available, limited AI enhancement",
                "group": "search_ai"
            }
        else:
            health_status["search_service"] = {
                "status": "unhealthy",
                "message": "Search service unavailable",
                "group": "search_ai"
            }
    except Exception as e:
        health_status["search_service"] = {
            "status": "unhealthy",
            "message": "Search orchestrator error",
            "group": "search_ai"
        }
    
    return health_status


async def get_monitoring_stack_health():
    """Get monitoring stack health - Grafana, Prometheus, Loki."""
    import aiohttp
    
    monitoring_services = []
    health_status = {}
    
    # Check Grafana
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
            async with session.get("http://grafana:3000/api/health") as response:
                if response.status == 200:
                    monitoring_services.append("Grafana")
    except Exception:
        pass
    
    # Check Prometheus  
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
            async with session.get("http://prometheus:9090/-/healthy") as response:
                if response.status == 200:
                    monitoring_services.append("Prometheus")
    except Exception:
        pass
    
    # Check Loki
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
            async with session.get("http://loki:3100/ready") as response:
                if response.status == 200:
                    monitoring_services.append("Loki")
    except Exception:
        pass
    
    if len(monitoring_services) >= 2:
        health_status["monitoring_stack"] = {
            "status": "healthy",
            "message": f"Monitoring active: {', '.join(monitoring_services)}",
            "details": {"active_services": monitoring_services},
            "group": "monitoring"
        }
    elif len(monitoring_services) == 1:
        health_status["monitoring_stack"] = {
            "status": "degraded",
            "message": f"Partial monitoring: {monitoring_services[0]} only",
            "details": {"active_services": monitoring_services},
            "group": "monitoring"
        }
    else:
        health_status["monitoring_stack"] = {
            "status": "degraded",
            "message": "Monitoring services not responding",
            "group": "monitoring"
        }
    
    return health_status


async def check_system_health():
    """Check health status of all system components - organized by service groups"""
    import redis
    import aiohttp
    import asyncio
    import time
    from src.core.config import get_system_configuration
    
    health_status = {}
    
    # ==============================================================================
    # CORE INFRASTRUCTURE - Essential services that everything depends on
    # ==============================================================================
    
    # Database Health Check
    try:
        db_manager = await get_database_manager()
        db_health = await db_manager.health_check()
        health_status["database"] = {
            "status": "healthy" if db_health.get("status") == "healthy" else "unhealthy",
            "message": db_health.get("message", "Database operational"),
            "response_time": db_health.get("response_time_ms"),
            "group": "infrastructure"
        }
    except Exception as e:
        health_status["database"] = {
            "status": "unhealthy",
            "message": f"Connection failed: {str(e)[:100]}",
            "action": {"label": "Check Configuration", "url": "/dashboard/search-config"},
            "group": "infrastructure"
        }
    
    # Redis/Cache Health Check
    try:
        cache_manager = await get_cache_manager()
        cache_health = await cache_manager.health_check()
        health_status["cache"] = {
            "status": "healthy" if cache_health.get("status") == "healthy" else "unhealthy",
            "message": cache_health.get("message", "Cache operational"),
            "response_time": cache_health.get("response_time_ms"),
            "group": "infrastructure"
        }
    except Exception as e:
        health_status["cache"] = {
            "status": "unhealthy",
            "message": f"Cache unavailable: {str(e)[:50]}",
            "action": {"label": "Check Redis", "url": "/dashboard/settings"},
            "group": "infrastructure"
        }
    
    # API Core Health Check
    try:
        # Test internal API responsiveness
        start_time = time.time()
        db_status = health_status.get("database", {}).get("status")
        cache_status = health_status.get("cache", {}).get("status") 
        response_time = int((time.time() - start_time) * 1000)
        
        if db_status == "healthy" and cache_status == "healthy":
            health_status["api_core"] = {
                "status": "healthy",
                "message": "All API endpoints responsive",
                "response_time": response_time,
                "group": "infrastructure"
            }
        else:
            health_status["api_core"] = {
                "status": "degraded",
                "message": "API running with limited functionality",
                "response_time": response_time,
                "group": "infrastructure"
            }
    except Exception as e:
        health_status["api_core"] = {
            "status": "unhealthy",
            "message": "API core services unavailable",
            "group": "infrastructure"
        }
    
    # ==============================================================================
    # SEARCH & AI SERVICES - Document search and AI enhancement capabilities  
    # ==============================================================================
    
    # Vector Store (Weaviate) Health Check
    try:
        weaviate_client = await get_weaviate_client()
        weaviate_health = await weaviate_client.health_check()
        health_status["vector_store"] = {
            "status": "healthy" if weaviate_health.get("status") == "healthy" else "degraded",
            "message": weaviate_health.get("message", "Vector store operational"),
            "response_time": weaviate_health.get("response_time_ms"),
            "group": "search_ai"
        }
    except Exception as e:
        health_status["vector_store"] = {
            "status": "degraded",
            "message": "Vector store not configured or unreachable",
            "action": {"label": "Configure Weaviate", "url": "/dashboard/search-config?tab=vector"},
            "group": "search_ai"
        }
    
    # AI Text Providers Health Check (OpenAI, Ollama, etc.)
    try:
        config = get_system_configuration()
        ai_config = getattr(config, "ai", None)
        
        # Check if any AI providers are configured
        ollama_enabled = bool(ai_config and getattr(ai_config, "ollama", None))
        openai_enabled = bool(ai_config and getattr(ai_config, "openai", None))
        anthropic_enabled = bool(ai_config and getattr(ai_config, "anthropic", None))
        
        provider_count = sum([ollama_enabled, openai_enabled, anthropic_enabled])
        
        if provider_count > 0:
            health_status["text_ai_providers"] = {
                "status": "healthy",
                "message": f"{provider_count} AI provider(s) configured and available",
                "details": {
                    "ollama": "enabled" if ollama_enabled else "disabled",
                    "openai": "enabled" if openai_enabled else "disabled", 
                    "anthropic": "enabled" if anthropic_enabled else "disabled"
                },
                "group": "search_ai"
            }
        else:
            health_status["text_ai_providers"] = {
                "status": "degraded",
                "message": "No AI providers configured",
                "action": {"label": "Configure Providers", "url": "/dashboard/providers"},
                "group": "search_ai"
            }
    except Exception as e:
        health_status["text_ai_providers"] = {
            "status": "degraded",
            "message": "Unable to check AI provider configuration",
            "action": {"label": "Configure Providers", "url": "/dashboard/providers"},
            "group": "search_ai"
        }
    
    # API Endpoints Health Check - Dynamically discover and monitor all endpoints
    try:
        # Import FastAPI app to get routes
        from ...main import app
        
        # Discover all API endpoints dynamically
        api_endpoints = []
        
        # Get all routes from the FastAPI app
        for route in app.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                # Skip WebSocket routes and internal routes
                if route.path.startswith('/ws/') or route.path == '/openapi.json' or route.path == '/docs' or route.path == '/redoc':
                    continue
                
                # Skip parameterized routes (containing {})
                if '{' in route.path or '}' in route.path:
                    continue
                    
                # Only monitor GET endpoints (health checks)
                if 'GET' in route.methods:
                    # Only include top-level API routes
                    if route.path.startswith('/api/v1/'):
                        # Extract a friendly name from the path
                        path_parts = route.path.strip('/').split('/')
                        if path_parts:
                            # Get the last meaningful part
                            name = path_parts[-1].replace('-', ' ').replace('_', ' ').title()
                            
                            # Special cases for better names
                            name_map = {
                                'V1': 'API Root',
                                'Health': 'Health Check',
                                'Mcp': 'MCP Tools',
                                'Recent': 'Recent Activity',
                                'Config': 'Configuration',
                                'Analytics': 'Analytics',
                                'Providers': 'Providers',
                                'Stats': 'Statistics',
                                'Metrics': 'Metrics',
                                'Search': 'Search',
                                'Logs': 'Logs',
                            }
                            
                            name = name_map.get(name, name)
                            
                            api_endpoints.append({
                                "path": route.path,
                                "name": name
                            })
        
        
        # Sort endpoints by path for consistent ordering
        api_endpoints.sort(key=lambda x: x['path'])
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            for endpoint in api_endpoints:
                start_time = time.time()
                endpoint_status = "healthy"
                endpoint_message = "Responsive"
                response_time_ms = 0
                
                try:
                    async with session.get(f"http://admin-ui:3000{endpoint['path']}") as response:
                        response_time_ms = int((time.time() - start_time) * 1000)
                        # Any response means the endpoint is reachable
                        endpoint_status = "healthy"
                        endpoint_message = f"HTTP {response.status}"
                                
                except asyncio.TimeoutError:
                    endpoint_status = "unhealthy"
                    endpoint_message = "Timeout"
                    response_time_ms = 3000
                except Exception as e:
                    endpoint_status = "unhealthy"
                    endpoint_message = f"Error: {str(e)[:50]}"
                    response_time_ms = int((time.time() - start_time) * 1000)
                
                # Create individual endpoint health status
                health_status[f"api_endpoint_{endpoint['path'].replace('/', '_').replace('-', '_')}"] = {
                    "status": endpoint_status,
                    "message": endpoint_message,
                    "response_time": response_time_ms,
                    "group": "infrastructure",
                    "name": endpoint['name'],
                    "path": endpoint['path']
                }
    
    except Exception as e:
        health_status["api_endpoints_error"] = {
            "status": "unhealthy",
            "message": f"API endpoint monitoring failed: {str(e)[:100]}",
            "group": "infrastructure"
        }

    # Search Orchestrator Health Check
    try:
        search_orchestrator = await get_search_orchestrator()
        search_health = await search_orchestrator.health_check()
        
        # Determine overall search capability
        vector_status = health_status.get("vector_store", {}).get("status")
        ai_status = health_status.get("text_ai_providers", {}).get("status")
        
        if search_health.get("overall_status") == "healthy" and vector_status == "healthy" and ai_status == "healthy":
            health_status["search_service"] = {
                "status": "healthy",
                "message": "Full search capabilities available",
                "response_time": search_health.get("response_time_ms"),
                "group": "search_ai"
            }
        elif search_health.get("overall_status") == "healthy":
            health_status["search_service"] = {
                "status": "degraded", 
                "message": "Basic search available, limited AI enhancement",
                "action": {"label": "Check AI Setup", "url": "/dashboard/providers"},
                "group": "search_ai"
            }
        else:
            health_status["search_service"] = {
                "status": "unhealthy",
                "message": "Search service unavailable",
                "action": {"label": "Check Configuration", "url": "/dashboard/search-config"},
                "group": "search_ai"
            }
    except Exception as e:
        health_status["search_service"] = {
            "status": "unhealthy",
            "message": "Search orchestrator error",
            "action": {"label": "Check Configuration", "url": "/dashboard/search-config"},
            "group": "search_ai"
        }
    
    # ==============================================================================
    # MONITORING & OPERATIONS - Observability and management tools
    # ==============================================================================
    
    # Admin UI Health Check
    try:
        # Check if we can reach the admin UI - try multiple endpoints
        admin_ui_healthy = False
        admin_ui_message = "Admin interface status unknown"
        
        # Try the Next.js health endpoint first
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                async with session.get("http://admin-ui:3000") as response:
                    if response.status == 200:
                        admin_ui_healthy = True
                        admin_ui_message = "Admin interface available"
        except Exception:
            pass
        
        # If that fails, try the internal API health
        if not admin_ui_healthy:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
                    async with session.get("http://admin-ui:3000/api/health") as response:
                        if response.status == 200:
                            admin_ui_healthy = True
                            admin_ui_message = "Admin interface available"
            except Exception:
                pass
        
        if admin_ui_healthy:
            health_status["admin_ui"] = {
                "status": "healthy", 
                "message": admin_ui_message,
                "group": "monitoring"
            }
        else:
            health_status["admin_ui"] = {
                "status": "degraded",
                "message": "Admin interface not responding on expected ports",
                "group": "monitoring"
            }
    except Exception:
        health_status["admin_ui"] = {
            "status": "degraded",
            "message": "Admin interface status unknown",
            "group": "monitoring"
        }
    
    # Monitoring Stack Health Check (Grafana, Prometheus, Loki)
    monitoring_services = []
    
    # Check Grafana
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
            async with session.get("http://grafana:3000/api/health") as response:
                if response.status == 200:
                    monitoring_services.append("Grafana")
    except Exception:
        pass
    
    # Check Prometheus  
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
            async with session.get("http://prometheus:9090/-/healthy") as response:
                if response.status == 200:
                    monitoring_services.append("Prometheus")
    except Exception:
        pass
    
    # Check Loki
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
            async with session.get("http://loki:3100/ready") as response:
                if response.status == 200:
                    monitoring_services.append("Loki")
    except Exception:
        pass
    
    if len(monitoring_services) >= 2:
        health_status["monitoring_stack"] = {
            "status": "healthy",
            "message": f"Monitoring active: {', '.join(monitoring_services)}",
            "details": {"active_services": monitoring_services},
            "action": {"label": "View Dashboards", "url": "/grafana"},
            "group": "monitoring"
        }
    elif len(monitoring_services) == 1:
        health_status["monitoring_stack"] = {
            "status": "degraded",
            "message": f"Partial monitoring: {monitoring_services[0]} only",
            "details": {"active_services": monitoring_services},
            "group": "monitoring"
        }
    else:
        health_status["monitoring_stack"] = {
            "status": "degraded",
            "message": "Monitoring services not responding",
            "action": {"label": "Check Services", "url": "/dashboard/logs"},
            "group": "monitoring"
        }
    
    return health_status




async def get_service_metrics():
    """Get per-service metrics - simplified version"""
    services_metrics = {}
    
    try:
        # Get basic system stats using psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        
        # Get real container metrics from Docker
        try:
            import docker
            client = docker.from_env()
            containers = client.containers.list()
            
            for container in containers:
                if container.name.startswith("docaiche-"):
                    service_name = container.name.replace("docaiche-", "").replace("-1", "")
                    stats = container.stats(stream=False)
                    
                    # Calculate CPU percentage
                    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
                    system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
                    cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100 if system_delta > 0 else 0
                    
                    # Calculate memory usage
                    memory_usage = stats['memory_stats']['usage']
                    memory_limit = stats['memory_stats']['limit']
                    memory_percent = (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0
                    
                    services_metrics[service_name] = {
                        "status": container.status,
                        "cpu_percent": round(cpu_percent, 2),
                        "memory_usage_mb": round(memory_usage / (1024 * 1024), 2),
                        "memory_percent": round(memory_percent, 2),
                        "network_rx_mb": 0,  # Real network stats require additional processing
                        "network_tx_mb": 0,
                        "uptime": container.attrs['State']['StartedAt']
                    }
        except Exception as docker_e:
            logger.warning(f"Docker metrics unavailable: {docker_e}")
            # Fall back to basic system metrics only
            services_metrics["system"] = {
                "status": "running",
                "cpu_percent": cpu_percent,
                "memory_usage_mb": round(memory_info.used / (1024 * 1024), 2),
                "memory_percent": round(memory_info.percent, 2),
                "network_rx_mb": 0,
                "network_tx_mb": 0,
                "uptime": "unknown"
            }
                
    except Exception as e:
        logger.error(f"Error getting service metrics: {e}")
        # Return empty metrics on failure
        services_metrics = {"error": f"Metrics unavailable: {str(e)}"}
    
    return services_metrics


async def get_redis_metrics():
    """Get detailed Redis metrics"""
    try:
        import redis
        r = redis.from_url("redis://redis:6379")
        info = r.info()
        
        return {
            "connected_clients": info.get('connected_clients', 0),
            "used_memory_mb": round(info.get('used_memory', 0) / (1024 * 1024), 2),
            "used_memory_rss_mb": round(info.get('used_memory_rss', 0) / (1024 * 1024), 2),
            "used_memory_peak_mb": round(info.get('used_memory_peak', 0) / (1024 * 1024), 2),
            "total_commands_processed": info.get('total_commands_processed', 0),
            "instantaneous_ops_per_sec": info.get('instantaneous_ops_per_sec', 0),
            "keyspace_hits": info.get('keyspace_hits', 0),
            "keyspace_misses": info.get('keyspace_misses', 0),
            "expired_keys": info.get('expired_keys', 0),
            "evicted_keys": info.get('evicted_keys', 0),
            "total_net_input_bytes": info.get('total_net_input_bytes', 0),
            "total_net_output_bytes": info.get('total_net_output_bytes', 0),
            "rejected_connections": info.get('rejected_connections', 0)
        }
    except Exception as e:
        logger.error(f"Error getting Redis metrics: {e}")
        return {}


async def get_weaviate_metrics():
    """Get Weaviate service metrics"""
    try:
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=2)  # 2 second timeout
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Try to get health info from Weaviate
            async with session.get('http://weaviate:8080/v1/.well-known/ready') as resp:
                if resp.status == 200:
                    # Get additional metrics
                    meta_resp = await session.get('http://weaviate:8080/v1/meta')
                    if meta_resp.status == 200:
                        meta_data = await meta_resp.json()
                        return {
                            "status": "healthy",
                            "version": meta_data.get('version', 'unknown'),
                            "nodes": meta_data.get('nodes', 1),
                            "tenants": len(meta_data.get('tenants', [])) if 'tenants' in meta_data else 'unknown'
                        }
                    else:
                        return {
                            "status": "healthy",
                            "version": "running",
                            "note": "Limited metrics available"
                        }
                else:
                    # Service responded but not ready
                    return {
                        "status": "unhealthy",
                        "version": "unknown",
                        "note": "Service not ready"
                    }
    except Exception as e:
        logger.error(f"Error getting Weaviate metrics: {e}")
        # Return reasonable defaults
        return {
            "status": "unknown",
            "version": "unknown",
            "note": "Service status unknown"
        }




@router.websocket("/ws/analytics")
async def analytics_websocket(
    websocket: WebSocket
):
    """
    Progressive WebSocket endpoint for real-time analytics updates.
    
    Sends data progressively as it becomes available instead of waiting
    for all data to be gathered first. Data is sent in logical sections:
    1. Connection acknowledgment
    2. System health (quick)
    3. Basic statistics (moderate)
    4. Detailed analytics (slower)
    5. Service metrics (optional)
    """
    await manager.connect(websocket, "analytics")
    update_task = None
    
    try:
        # Send immediate connection acknowledgment
        await manager.send_json({
            "type": "analytics_update",
            "section": "connection",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"status": "connected", "message": "Loading analytics data..."}
        }, websocket)
        
        # Progressive data loading function
        async def load_analytics_progressive(time_range: str = "24h"):
            """Load analytics data progressively, sending each section as it becomes available."""
            
            # 1. Send system health first (quickest to gather)
            try:
                health_data = await get_system_health_quick()
                await manager.send_json({
                    "type": "analytics_update",
                    "section": "health",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"systemHealth": health_data}
                }, websocket)
            except Exception as e:
                logger.error(f"Error getting health data: {e}")
                await manager.send_json({
                    "type": "analytics_update",
                    "section": "health",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"systemHealth": {"error": "Health data unavailable"}}
                }, websocket)
            
            # 2. Send basic stats (moderate speed)
            try:
                basic_stats = await get_basic_analytics_stats()
                await manager.send_json({
                    "type": "analytics_update",
                    "section": "basic_stats",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"stats": basic_stats}
                }, websocket)
            except Exception as e:
                logger.error(f"Error getting basic stats: {e}")
                await manager.send_json({
                    "type": "analytics_update",
                    "section": "basic_stats",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"stats": {"error": "Basic stats unavailable"}}
                }, websocket)
            
            # 3. Send detailed analytics (slower)
            try:
                detailed_analytics = await get_detailed_analytics_data(time_range)
                await manager.send_json({
                    "type": "analytics_update",
                    "section": "detailed_analytics",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"analytics": detailed_analytics}
                }, websocket)
            except Exception as e:
                logger.error(f"Error getting detailed analytics: {e}")
                await manager.send_json({
                    "type": "analytics_update",
                    "section": "detailed_analytics",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"analytics": {"error": "Detailed analytics unavailable"}}
                }, websocket)
            
            # 4. Send service metrics (optional, may be slow)
            try:
                service_metrics = await get_service_metrics()
                await manager.send_json({
                    "type": "analytics_update",
                    "section": "service_metrics",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"service_metrics": service_metrics}
                }, websocket)
            except Exception as e:
                logger.error(f"Error getting service metrics: {e}")
                # Service metrics are optional, don't send error for this
            
            # 5. Signal load complete
            await manager.send_json({
                "type": "analytics_update",
                "section": "complete",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {"loadComplete": True}
            }, websocket)
        
        # Load initial data progressively
        await load_analytics_progressive("24h")
        
        # Start background task for periodic updates
        async def send_progressive_updates():
            while True:
                try:
                    await asyncio.sleep(5)  # Update every 5 seconds
                    
                    # Send progressive updates - only essential data for performance
                    try:
                        # Health update (quick)
                        health_data = await get_system_health_quick()
                        await manager.send_json({
                            "type": "analytics_update",
                            "section": "health_update",
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": {"systemHealth": health_data}
                        }, websocket)
                        
                        # Basic stats update (moderate)
                        basic_stats = await get_basic_analytics_stats()
                        await manager.send_json({
                            "type": "analytics_update",
                            "section": "stats_update",
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": {"stats": basic_stats}
                        }, websocket)
                        
                    except Exception as data_error:
                        logger.error(f"Error generating progressive update data: {data_error}")
                        
                except asyncio.CancelledError:
                    logger.info("Progressive analytics update task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in progressive analytics update loop: {e}")
                    break
        
        # Create background task
        update_task = asyncio.create_task(send_progressive_updates())
        
        # Listen for client messages
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                # Handle different message types
                if data.get("type") == "change_timerange":
                    time_range = data.get("timeRange", "24h")
                    try:
                        # Send loading indicator
                        await manager.send_json({
                            "type": "analytics_update",
                            "section": "loading",
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": {"loading": True, "timeRange": time_range}
                        }, websocket)
                        
                        # Load new time range data progressively
                        await load_analytics_progressive(time_range)
                        
                    except Exception as e:
                        logger.error(f"Error handling timerange change: {e}")
                    
                elif data.get("type") == "ping":
                    await manager.send_json({"type": "pong"}, websocket)
                    
            except WebSocketDisconnect:
                logger.info("Progressive analytics WebSocket client disconnected")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from client: {e}")
                # Don't break connection for invalid JSON
            except Exception as e:
                logger.error(f"Error processing websocket message: {e}")
                break
                
    except Exception as e:
        logger.error(f"Progressive analytics WebSocket error: {e}")
    finally:
        if update_task:
            update_task.cancel()
            try:
                await update_task
            except asyncio.CancelledError:
                pass
        manager.disconnect(websocket)


@router.websocket("/ws/health")
async def health_websocket(
    websocket: WebSocket
):
    """
    Progressive WebSocket endpoint for real-time health monitoring.
    
    Sends health data progressively in logical sections:
    1. Connection acknowledgment
    2. Core infrastructure (database, cache, API)
    3. Search & AI services (vector store, AI providers)
    4. Service metrics (container stats)
    5. Monitoring stack (Grafana, Prometheus)
    """
    await manager.connect(websocket, "health")
    update_task = None
    
    try:
        # Send immediate connection acknowledgment
        await manager.send_json({
            "type": "health_update",
            "section": "connection",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"status": "connected", "message": "Loading health data..."}
        }, websocket)
        
        # Progressive health data loading function
        async def load_health_progressive():
            """Load health data progressively, sending each section as it becomes available."""
            
            # 1. Core infrastructure health (essential services)
            try:
                core_health = await get_core_infrastructure_health()
                await manager.send_json({
                    "type": "health_update",
                    "section": "core_infrastructure",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"core_infrastructure": core_health}
                }, websocket)
            except Exception as e:
                logger.error(f"Error getting core infrastructure health: {e}")
                await manager.send_json({
                    "type": "health_update",
                    "section": "core_infrastructure",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"core_infrastructure": {"error": "Core infrastructure status unavailable"}}
                }, websocket)
            
            # 2. Search & AI services health
            try:
                search_ai_health = await get_search_ai_health()
                await manager.send_json({
                    "type": "health_update",
                    "section": "search_ai",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"search_ai": search_ai_health}
                }, websocket)
            except Exception as e:
                logger.error(f"Error getting search & AI health: {e}")
                await manager.send_json({
                    "type": "health_update",
                    "section": "search_ai",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"search_ai": {"error": "Search & AI services status unavailable"}}
                }, websocket)
            
            # 3. Service metrics (may be slow)
            try:
                service_metrics = await get_service_metrics()
                await manager.send_json({
                    "type": "health_update",
                    "section": "service_metrics",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"service_metrics": service_metrics}
                }, websocket)
            except Exception as e:
                logger.error(f"Error getting service metrics: {e}")
                # Service metrics are optional, don't send error
            
            # 4. Monitoring stack health (optional)
            try:
                monitoring_health = await get_monitoring_stack_health()
                await manager.send_json({
                    "type": "health_update",
                    "section": "monitoring",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"monitoring": monitoring_health}
                }, websocket)
            except Exception as e:
                logger.error(f"Error getting monitoring stack health: {e}")
                # Monitoring is optional, don't send error
            
            # 5. Signal load complete
            await manager.send_json({
                "type": "health_update",
                "section": "complete",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {"loadComplete": True}
            }, websocket)
        
        # Load initial health data progressively
        await load_health_progressive()
        
        # Start background task for periodic health updates
        async def send_progressive_health_updates():
            while True:
                try:
                    await asyncio.sleep(5)  # Update every 5 seconds
                    
                    # Send progressive health updates - focus on essential data
                    try:
                        # Core infrastructure update (quick and essential)
                        core_health = await get_core_infrastructure_health()
                        await manager.send_json({
                            "type": "health_update",
                            "section": "core_update",
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": {"core_infrastructure": core_health}
                        }, websocket)
                        
                        # Search & AI services update (moderate priority)
                        search_ai_health = await get_search_ai_health()
                        await manager.send_json({
                            "type": "health_update",
                            "section": "search_ai_update",
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": {"search_ai": search_ai_health}
                        }, websocket)
                        
                    except Exception as data_error:
                        logger.error(f"Error generating progressive health update: {data_error}")
                        
                except asyncio.CancelledError:
                    logger.info("Progressive health update task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in progressive health update loop: {e}")
                    break
        
        # Create background task
        update_task = asyncio.create_task(send_progressive_health_updates())
        
        # Listen for client messages
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data.get("type") == "ping":
                    await manager.send_json({"type": "pong"}, websocket)
                elif data.get("type") == "refresh":
                    # Client requested a full health refresh
                    await load_health_progressive()
                    
            except WebSocketDisconnect:
                logger.info("Progressive health WebSocket client disconnected")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from client: {e}")
                # Don't break connection for invalid JSON
            except Exception as e:
                logger.error(f"Error processing websocket message: {e}")
                break
                
    except Exception as e:
        logger.error(f"Progressive health WebSocket error: {e}")
    finally:
        if update_task:
            update_task.cancel()
            try:
                await update_task
            except asyncio.CancelledError:
                pass
        manager.disconnect(websocket)


@router.get("/ws/test")
async def websocket_test_page():
    """Simple test page for WebSocket connections."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Test</title>
    </head>
    <body>
        <h1>WebSocket Test</h1>
        <h2>Analytics WebSocket</h2>
        <button onclick="connectAnalytics()">Connect Analytics</button>
        <button onclick="disconnectAnalytics()">Disconnect</button>
        <button onclick="changeTimeRange()">Change Time Range</button>
        <div id="analytics"></div>
        
        <h2>Health WebSocket</h2>
        <button onclick="connectHealth()">Connect Health</button>
        <button onclick="disconnectHealth()">Disconnect</button>
        <div id="health"></div>
        
        <script>
            let analyticsWs = null;
            let healthWs = null;
            
            function connectAnalytics() {
                analyticsWs = new WebSocket("ws://localhost:4080/api/v1/ws/analytics");
                
                analyticsWs.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    document.getElementById('analytics').innerHTML = 
                        '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                };
                
                analyticsWs.onopen = function(event) {
                    console.log("Analytics WebSocket connected");
                };
                
                analyticsWs.onclose = function(event) {
                    console.log("Analytics WebSocket disconnected");
                };
            }
            
            function disconnectAnalytics() {
                if (analyticsWs) {
                    analyticsWs.close();
                }
            }
            
            function changeTimeRange() {
                if (analyticsWs && analyticsWs.readyState === WebSocket.OPEN) {
                    analyticsWs.send(JSON.stringify({
                        type: "change_timerange",
                        timeRange: "7d"
                    }));
                }
            }
            
            function connectHealth() {
                healthWs = new WebSocket("ws://localhost:4080/api/v1/ws/health");
                
                healthWs.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    document.getElementById('health').innerHTML = 
                        '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
                };
                
                healthWs.onopen = function(event) {
                    console.log("Health WebSocket connected");
                };
                
                healthWs.onclose = function(event) {
                    console.log("Health WebSocket disconnected");
                };
            }
            
            function disconnectHealth() {
                if (healthWs) {
                    healthWs.close();
                }
            }
        </script>
    </body>
    </html>
    """)