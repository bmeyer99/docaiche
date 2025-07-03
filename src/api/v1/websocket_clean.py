"""
Clean, simple WebSocket implementation for analytics.
Sends data in 3 predictable phases instead of fragmented sections.
"""

import asyncio
import json
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .websocket_endpoints import (
    check_system_health, 
    get_basic_analytics_stats, 
    get_detailed_analytics_data,
    get_service_metrics,
    get_redis_metrics,
    get_weaviate_metrics
)

logger = logging.getLogger(__name__)
router = APIRouter()

class AnalyticsConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info("Analytics WebSocket connected")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info("Analytics WebSocket disconnected")

manager = AnalyticsConnectionManager()

async def send_phase_data(websocket: WebSocket, phase: str, data: dict):
    """Send data for a specific phase"""
    message = {
        "type": "analytics_update",
        "phase": phase,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data
    }
    await websocket.send_json(message)

async def get_phase_1_data():
    """Phase 1: Essential data that must load fast (< 1 second)"""
    try:
        # Get only the fastest, most essential data
        basic_stats = await get_basic_analytics_stats()
        
        # Get core system health (just the essentials)
        core_health = {}
        
        # Essential infrastructure checks only
        from .dependencies import get_database_manager, get_cache_manager
        import time
        
        # Ultra-quick DB check - just connectivity
        try:
            db_manager = await get_database_manager()
            # Skip detailed health check, just test the connection pool
            if hasattr(db_manager, 'engine') and db_manager.engine:
                core_health["database"] = {
                    "status": "healthy",
                    "message": "Database connected",
                    "group": "infrastructure"
                }
            else:
                raise Exception("No engine")
        except Exception:
            core_health["database"] = {
                "status": "unhealthy",
                "message": "Database unavailable",
                "group": "infrastructure"
            }
        
        # Ultra-quick cache check - just connectivity
        try:
            cache_manager = await get_cache_manager()
            # Skip detailed health check, just test if manager exists
            if hasattr(cache_manager, 'redis_client'):
                core_health["cache"] = {
                    "status": "healthy",
                    "message": "Cache connected",
                    "group": "infrastructure"
                }
            else:
                raise Exception("No redis client")
        except Exception:
            core_health["cache"] = {
                "status": "unhealthy",
                "message": "Cache unavailable",
                "group": "infrastructure"
            }
        
        # API core status
        db_status = core_health.get("database", {}).get("status")
        cache_status = core_health.get("cache", {}).get("status")
        
        if db_status == "healthy" and cache_status == "healthy":
            core_health["api_core"] = {
                "status": "healthy",
                "message": "API core services operational",
                "group": "infrastructure"
            }
        else:
            core_health["api_core"] = {
                "status": "degraded",
                "message": "API running with limited functionality",
                "group": "infrastructure"
            }
        
        return {
            "systemHealth": core_health,
            "stats": basic_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting Phase 1 data: {e}")
        return {
            "systemHealth": {"error": "Core data unavailable"},
            "stats": {"error": "Stats unavailable"}
        }

async def get_phase_2_data():
    """Phase 2: Extended system data (< 3 seconds)"""
    try:
        # Import quick health functions and API endpoint checker
        from .websocket_progressive import get_search_ai_services_quick, get_monitoring_services_quick, send_progressive_api_endpoints
        
        # Get search/AI and monitoring services health in parallel (but quick)
        search_ai_task = asyncio.create_task(get_search_ai_services_quick())
        monitoring_task = asyncio.create_task(get_monitoring_services_quick())
        api_endpoints_task = asyncio.create_task(get_api_endpoints_quick())
        
        search_ai_health, monitoring_health, api_endpoints_health = await asyncio.gather(
            search_ai_task, 
            monitoring_task,
            api_endpoints_task,
            return_exceptions=True
        )
        
        # Combine results
        extended_health = {}
        
        if not isinstance(search_ai_health, Exception):
            extended_health.update(search_ai_health)
            
        if not isinstance(monitoring_health, Exception):
            extended_health.update(monitoring_health)
            
        if not isinstance(api_endpoints_health, Exception):
            extended_health.update(api_endpoints_health)
        
        return {
            "systemHealth": extended_health
        }
        
    except Exception as e:
        logger.error(f"Error getting Phase 2 data: {e}")
        return {
            "systemHealth": {"error": "Extended health data unavailable"}
        }

async def get_api_endpoints_quick():
    """Get API endpoint health checks quickly for the 5 essential endpoints"""
    import aiohttp
    import time
    
    api_endpoints = [
        {"path": "/api/v1/health", "name": "Health Check"},
        {"path": "/api/v1/search/content", "name": "Search Content"},
        {"path": "/api/v1/mcp", "name": "MCP Tools"},
        {"path": "/api/v1/providers", "name": "Providers"},
        {"path": "/api/v1/analytics", "name": "Analytics"},
    ]
    
    endpoint_health = {}
    
    try:
        # Quick parallel check of all endpoints with short timeout
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=1)) as session:
            tasks = []
            
            for endpoint in api_endpoints:
                async def check_endpoint(ep):
                    start_time = time.time()
                    endpoint_key = f"api_endpoint_{ep['path'].replace('/', '_').replace('-', '_')}"
                    
                    try:
                        async with session.get(f"http://127.0.0.1:4000{ep['path']}") as response:
                            response_time_ms = int((time.time() - start_time) * 1000)
                            return endpoint_key, {
                                "status": "healthy",
                                "message": f"HTTP {response.status}",
                                "response_time": response_time_ms,
                                "group": "infrastructure",
                                "name": ep['name'],
                                "path": ep['path']
                            }
                    except Exception as e:
                        response_time_ms = int((time.time() - start_time) * 1000)
                        return endpoint_key, {
                            "status": "unhealthy",
                            "message": f"Error: {str(e)[:30]}",
                            "response_time": response_time_ms,
                            "group": "infrastructure",
                            "name": ep['name'],
                            "path": ep['path']
                        }
                
                tasks.append(check_endpoint(endpoint))
            
            # Run all endpoint checks in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if not isinstance(result, Exception) and len(result) == 2:
                    endpoint_key, health_data = result
                    endpoint_health[endpoint_key] = health_data
    
    except Exception as e:
        logger.error(f"Error checking API endpoints: {e}")
        endpoint_health["api_endpoints_error"] = {
            "status": "unhealthy", 
            "message": f"API endpoint monitoring failed: {str(e)[:50]}",
            "group": "infrastructure"
        }
    
    return endpoint_health

async def get_phase_3_data(time_range: str = "24h"):
    """Phase 3: Detailed analytics and metrics (< 5 seconds)"""
    try:
        # Run these in parallel for speed
        detailed_analytics_task = asyncio.create_task(get_detailed_analytics_data(time_range))
        service_metrics_task = asyncio.create_task(get_service_metrics())
        redis_metrics_task = asyncio.create_task(get_redis_metrics())
        weaviate_metrics_task = asyncio.create_task(get_weaviate_metrics())
        
        # Wait for all with timeout
        results = await asyncio.gather(
            detailed_analytics_task,
            service_metrics_task, 
            redis_metrics_task,
            weaviate_metrics_task,
            return_exceptions=True
        )
        
        detailed_analytics = results[0] if not isinstance(results[0], Exception) else {}
        service_metrics = results[1] if not isinstance(results[1], Exception) else {}
        redis_metrics = results[2] if not isinstance(results[2], Exception) else {}
        weaviate_metrics = results[3] if not isinstance(results[3], Exception) else {}
        
        return {
            "analytics": detailed_analytics,
            "service_metrics": service_metrics,
            "redis_metrics": redis_metrics,
            "weaviate_metrics": weaviate_metrics
        }
        
    except Exception as e:
        logger.error(f"Error getting Phase 3 data: {e}")
        return {
            "analytics": {"error": "Detailed analytics unavailable"},
            "service_metrics": {},
            "redis_metrics": {},
            "weaviate_metrics": {}
        }

async def load_all_phases(websocket: WebSocket, time_range: str = "24h"):
    """Load all 3 phases of data progressively"""
    
    # Phase 1: Essential data (must be fast)
    phase1_data = await get_phase_1_data()
    await send_phase_data(websocket, "essential", phase1_data)
    
    # Phase 2: Extended system health
    phase2_data = await get_phase_2_data()
    await send_phase_data(websocket, "extended", phase2_data)
    
    # Phase 3: Detailed analytics
    phase3_data = await get_phase_3_data(time_range)
    await send_phase_data(websocket, "detailed", phase3_data)
    
    # Signal completion
    await send_phase_data(websocket, "complete", {"loadComplete": True})

@router.websocket("/ws/analytics/clean")
async def clean_analytics_websocket(websocket: WebSocket):
    """
    Clean analytics WebSocket with 3 simple phases:
    1. Essential data (< 1s): Core infrastructure + basic stats
    2. Extended data (< 3s): Full system health 
    3. Detailed data (< 5s): Analytics + metrics
    """
    await manager.connect(websocket)
    update_task = None
    current_time_range = "24h"
    
    try:
        # Initial load
        await load_all_phases(websocket, current_time_range)
        
        # Start periodic updates every 5 seconds
        async def periodic_updates():
            while True:
                try:
                    await asyncio.sleep(5)
                    await load_all_phases(websocket, current_time_range)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in periodic updates: {e}")
        
        update_task = asyncio.create_task(periodic_updates())
        
        # Handle client messages
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data.get("type") == "change_timerange":
                    current_time_range = data.get("timeRange", "24h")
                    # Reload phases with new time range
                    await load_all_phases(websocket, current_time_range)
                
                elif data.get("type") == "refresh_data":
                    # Fresh load when tab becomes visible
                    await load_all_phases(websocket, current_time_range)
                
                elif data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.error("Invalid JSON from client")
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                break
                
    except Exception as e:
        logger.error(f"Clean analytics WebSocket error: {e}")
    finally:
        if update_task:
            update_task.cancel()
        manager.disconnect(websocket)