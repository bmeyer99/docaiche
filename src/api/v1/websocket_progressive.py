"""
Progressive WebSocket implementation for analytics data.

This module provides a WebSocket endpoint that sends analytics data progressively
instead of waiting for all data to be gathered before sending. Data is sent in
the following order:
1. Initial connection acknowledgment
2. System health data (quick to gather)
3. Basic statistics 
4. Detailed analytics data

Each section is sent as soon as it's ready, improving perceived performance.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import psutil
import docker
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ...database.models import SearchCache, ContentMetadata, FeedbackEvents, UsageSignals
from .dependencies import get_database_manager, get_cache_manager, get_weaviate_client, get_search_orchestrator
from .websocket_endpoints import check_system_health

logger = logging.getLogger(__name__)

router = APIRouter()


async def send_progressive_message(websocket: WebSocket, message_type: str, data: dict, section: str):
    """Send a progressive update message with section information."""
    message = {
        "type": "analytics_update",
        "section": section,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }
    await websocket.send_json(message)


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


async def get_basic_stats():
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


async def get_detailed_analytics(time_range: str = "24h"):
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


async def get_service_metrics_async():
    """Get service metrics asynchronously."""
    services_metrics = {}
    
    try:
        # Get basic system stats
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        
        # Try to get Docker container metrics
        try:
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
                    }
        except Exception as e:
            logger.warning(f"Docker metrics unavailable: {e}")
            # Fallback to system metrics
            services_metrics["system"] = {
                "status": "running",
                "cpu_percent": cpu_percent,
                "memory_usage_mb": round(memory_info.used / (1024 * 1024), 2),
                "memory_percent": round(memory_info.percent, 2),
            }
    except Exception as e:
        logger.error(f"Error getting service metrics: {e}")
    
    return services_metrics


async def send_progressive_api_endpoints(websocket: WebSocket):
    """Send API endpoint health checks progressively as each one completes."""
    import aiohttp
    import time
    
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
        
        # Check each endpoint and send results progressively
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            for endpoint in api_endpoints:
                start_time = time.time()
                endpoint_status = "healthy"
                endpoint_message = "Responsive"
                response_time_ms = 0
                
                try:
                    async with session.get(f"http://admin-ui:3000{endpoint['path']}") as response:
                        response_time_ms = int((time.time() - start_time) * 1000)
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
                
                # Send individual endpoint result immediately
                endpoint_key = f"api_endpoint_{endpoint['path'].replace('/', '_').replace('-', '_')}"
                endpoint_data = {
                    endpoint_key: {
                        "status": endpoint_status,
                        "message": endpoint_message,
                        "response_time": response_time_ms,
                        "group": "infrastructure",
                        "name": endpoint['name'],
                        "path": endpoint['path']
                    }
                }
                
                await send_progressive_message(
                    websocket,
                    "analytics_update",
                    {"systemHealth": endpoint_data},
                    "api_endpoint"
                )
                
    except Exception as e:
        logger.error(f"Error in progressive API endpoint checking: {e}")
        await send_progressive_message(
            websocket,
            "analytics_update",
            {"systemHealth": {"api_endpoints_error": {
                "status": "unhealthy",
                "message": f"API endpoint monitoring failed: {str(e)[:100]}",
                "group": "infrastructure"
            }}},
            "api_endpoint_error"
        )


@router.websocket("/ws/analytics/progressive")
async def progressive_analytics_websocket(websocket: WebSocket):
    """
    Progressive WebSocket endpoint for analytics data.
    
    Sends data progressively as it becomes available instead of waiting
    for all data to be gathered first.
    """
    await websocket.accept()
    update_task = None
    
    try:
        # Send initial connection acknowledgment immediately
        await send_progressive_message(
            websocket,
            "connection",
            {"status": "connected", "message": "Loading analytics data..."},
            "init"
        )
        
        # Send basic system health first (fast - just database, cache, API core)
        try:
            basic_health_data = await get_system_health_quick()
            await send_progressive_message(
                websocket,
                "analytics_update",
                {"systemHealth": basic_health_data},
                "health"
            )
        except Exception as e:
            logger.error(f"Error getting basic health data: {e}")
            await send_progressive_message(
                websocket,
                "analytics_update",
                {"systemHealth": {"error": "Basic health data unavailable"}},
                "health"
            )
        
        # Send basic stats next (relatively quick)
        try:
            basic_stats = await get_basic_stats()
            await send_progressive_message(
                websocket,
                "analytics_update", 
                {"stats": basic_stats},
                "basic_stats"
            )
        except Exception as e:
            logger.error(f"Error getting basic stats: {e}")
            await send_progressive_message(
                websocket,
                "analytics_update",
                {"stats": {"error": "Stats unavailable"}},
                "basic_stats"
            )
        
        # Send detailed analytics (may take longer)
        try:
            detailed_analytics = await get_detailed_analytics("24h")
            await send_progressive_message(
                websocket,
                "analytics_update",
                {"analytics": detailed_analytics},
                "detailed_analytics"
            )
        except Exception as e:
            logger.error(f"Error getting detailed analytics: {e}")
            await send_progressive_message(
                websocket,
                "analytics_update",
                {"analytics": {"error": "Detailed analytics unavailable"}},
                "detailed_analytics"
            )
        
        # Send detailed system health with progressive API endpoint checks
        try:
            await send_progressive_api_endpoints(websocket)
        except Exception as e:
            logger.error(f"Error getting progressive API endpoints: {e}")
        
        # Send service metrics last (optional, may be slow)
        try:
            service_metrics = await get_service_metrics_async()
            await send_progressive_message(
                websocket,
                "analytics_update",
                {"service_metrics": service_metrics},
                "service_metrics"
            )
        except Exception as e:
            logger.error(f"Error getting service metrics: {e}")
        
        # Signal that initial load is complete
        await send_progressive_message(
            websocket,
            "analytics_update",
            {"loadComplete": True},
            "complete"
        )
        
        # Start periodic updates (progressive as well)
        async def send_periodic_updates():
            while True:
                try:
                    await asyncio.sleep(5)  # Update every 5 seconds
                    
                    # Send updates progressively
                    tasks = []
                    
                    # Health update
                    async def update_health():
                        try:
                            health_data = await check_system_health()
                            await send_progressive_message(
                                websocket,
                                "analytics_update",
                                {"systemHealth": health_data},
                                "health_update"
                            )
                        except Exception as e:
                            logger.error(f"Error updating health: {e}")
                    
                    # Basic stats update
                    async def update_stats():
                        try:
                            basic_stats = await get_basic_stats()
                            await send_progressive_message(
                                websocket,
                                "analytics_update",
                                {"stats": basic_stats},
                                "stats_update"
                            )
                        except Exception as e:
                            logger.error(f"Error updating stats: {e}")
                    
                    # Run updates concurrently
                    tasks.append(asyncio.create_task(update_health()))
                    tasks.append(asyncio.create_task(update_stats()))
                    
                    # Wait for all updates to complete
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
                except asyncio.CancelledError:
                    logger.info("Progressive analytics update task cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in progressive update loop: {e}")
                    break
        
        # Create background update task
        update_task = asyncio.create_task(send_periodic_updates())
        
        # Listen for client messages
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                # Handle time range changes
                if data.get("type") == "change_timerange":
                    time_range = data.get("timeRange", "24h")
                    
                    # Send progressive update for new time range
                    try:
                        # Send loading indicator
                        await send_progressive_message(
                            websocket,
                            "analytics_update",
                            {"loading": True, "timeRange": time_range},
                            "loading"
                        )
                        
                        # Get and send detailed analytics for new time range
                        detailed_analytics = await get_detailed_analytics(time_range)
                        await send_progressive_message(
                            websocket,
                            "analytics_update",
                            {"analytics": detailed_analytics, "timeRange": time_range},
                            "timerange_update"
                        )
                    except Exception as e:
                        logger.error(f"Error handling timerange change: {e}")
                
                elif data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                
            except WebSocketDisconnect:
                logger.info("Progressive analytics WebSocket client disconnected")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from client: {e}")
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
        try:
            await websocket.close()
        except Exception:
            pass