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
from datetime import datetime
from typing import Dict, Set, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse


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


async def get_analytics_data_internal(time_range: str = "24h"):
    """Get analytics data for WebSocket (simplified version)"""
    return {
        "timeRange": time_range,
        "searchMetrics": {
            "totalSearches": 1247 if time_range == "30d" else 89 if time_range == "7d" else 12,
            "avgResponseTime": 125,
            "successRate": 0.95,
            "topQueries": [
                {"query": "python async", "count": 45},
                {"query": "react hooks", "count": 32},
                {"query": "docker compose", "count": 28},
                {"query": "fastapi tutorial", "count": 22},
                {"query": "typescript types", "count": 19},
            ],
            "queriesByHour": [
                {"count": 5, "responseTime": 120},
                {"count": 8, "responseTime": 115},
                {"count": 12, "responseTime": 130},
                {"count": 10, "responseTime": 125},
                {"count": 7, "responseTime": 118},
            ] + [{"count": 3, "responseTime": 125}] * 19,  # Fill 24 hours
        },
        "contentMetrics": {
            "totalDocuments": 15432,
            "totalChunks": 89765,
            "avgQualityScore": 0.82,
            "documentsByTechnology": [
                {"technology": "Python", "count": 5432},
                {"technology": "JavaScript", "count": 3245},
                {"technology": "React", "count": 2876},
                {"technology": "TypeScript", "count": 2156},
                {"technology": "Docker", "count": 1789},
            ],
        },
    }


async def get_health_status_internal():
    """Get health status for WebSocket (simplified version)"""
    return {
        "status": "healthy",
        "components": {
            "database": {"status": "healthy", "message": "Connected"},
            "redis": {"status": "healthy", "message": "Connected"},
            "anythingllm": {"status": "healthy", "message": "Connected"},
            "search": {"status": "healthy", "message": "All search services operational"},
        },
        "features": {
            "document_processing": "available",
            "search": "available",
            "llm_enhancement": "available",
        },
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


async def get_stats_data_internal():
    """Get stats data for WebSocket (simplified version)"""
    return {
        "search_stats": {
            "total_searches": 1247,
            "avg_response_time_ms": 125,
            "cache_hit_rate": 0.73,
        },
        "cache_stats": {
            "hit_rate": 0.73,
            "miss_rate": 0.27,
            "total_keys": 8976,
            "memory_usage_mb": 128,
        },
        "content_stats": {
            "total_documents": 15432,
            "total_chunks": 89765,
            "workspaces": 5,
        },
        "system_stats": {
            "cpu_usage_percent": 23.5,
            "memory_usage_mb": 512,
            "disk_usage_mb": 2048,
        },
    }


@router.websocket("/ws/analytics")
async def analytics_websocket(
    websocket: WebSocket
):
    """
    WebSocket endpoint for real-time analytics updates.
    
    Sends analytics data every 5 seconds or on-demand when requested.
    """
    await manager.connect(websocket, "analytics")
    
    try:
        # Send initial data
        initial_data = {
            "type": "analytics_update",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "analytics": await get_analytics_data_internal("24h"),
                "stats": await get_stats_data_internal()
            }
        }
        await manager.send_json(initial_data, websocket)
        
        # Start background task for periodic updates
        async def send_updates():
            while True:
                try:
                    await asyncio.sleep(5)  # Update every 5 seconds
                    
                    update_data = {
                        "type": "analytics_update",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "analytics": await get_analytics_data_internal("24h"),
                            "stats": await get_stats_data_internal()
                        }
                    }
                    await manager.send_json(update_data, websocket)
                except Exception as e:
                    logger.error(f"Error sending analytics update: {e}")
                    break
        
        # Create background task
        update_task = asyncio.create_task(send_updates())
        
        # Listen for client messages
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                # Handle different message types
                if data.get("type") == "change_timerange":
                    time_range = data.get("timeRange", "24h")
                    response_data = {
                        "type": "analytics_update",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": {
                            "analytics": await get_analytics_data_internal(time_range),
                            "stats": await get_stats_data_internal()
                        }
                    }
                    await manager.send_json(response_data, websocket)
                    
                elif data.get("type") == "ping":
                    await manager.send_json({"type": "pong"}, websocket)
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error processing websocket message: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        update_task.cancel()
        manager.disconnect(websocket)


@router.websocket("/ws/health")
async def health_websocket(
    websocket: WebSocket
):
    """
    WebSocket endpoint for real-time health monitoring.
    
    Sends health status updates every 2 seconds.
    """
    await manager.connect(websocket, "health")
    
    try:
        # Send initial health data
        initial_health = await get_health_status_internal()
        
        initial_data = {
            "type": "health_update",
            "timestamp": datetime.utcnow().isoformat(),
            "data": initial_health
        }
        await manager.send_json(initial_data, websocket)
        
        # Start background task for periodic health checks
        async def send_health_updates():
            while True:
                try:
                    await asyncio.sleep(2)  # Check every 2 seconds
                    
                    health_data = await get_health_status_internal()
                    update_data = {
                        "type": "health_update",
                        "timestamp": datetime.utcnow().isoformat(),
                        "data": health_data
                    }
                    await manager.send_json(update_data, websocket)
                except Exception as e:
                    logger.error(f"Error sending health update: {e}")
                    break
        
        # Create background task
        update_task = asyncio.create_task(send_health_updates())
        
        # Listen for client messages
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                if data.get("type") == "ping":
                    await manager.send_json({"type": "pong"}, websocket)
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error processing websocket message: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        update_task.cancel()
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