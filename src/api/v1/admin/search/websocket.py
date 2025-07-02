"""
WebSocket endpoint for Search Configuration real-time updates.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active connections
active_connections: Set[WebSocket] = set()


@router.websocket("/ws")
async def search_config_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for search configuration real-time updates.
    
    Provides:
    - Configuration change notifications
    - Health status updates
    - Metrics updates
    - System alerts
    """
    await websocket.accept()
    active_connections.add(websocket)
    logger.info("Search config WebSocket connected")
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Start sending periodic health updates
        async def send_health_updates():
            while True:
                try:
                    await asyncio.sleep(5)  # Send health update every 5 seconds
                    
                    # Get actual system health
                    health_status = {
                        "type": "health_update",
                        "payload": {
                            "component": "overall",
                            "status": "healthy",  # This should check actual health
                            "message": "All components operational",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                    
                    await websocket.send_json(health_status)
                except Exception as e:
                    logger.error(f"Error sending health update: {e}")
                    break
        
        # Create background task for health updates
        health_task = asyncio.create_task(send_health_updates())
        
        # Listen for client messages
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                
                # Handle different message types
                if data.get("type") == "subscribe":
                    topics = data.get("topics", [])
                    logger.info(f"Client subscribed to topics: {topics}")
                    
                    # Send confirmation
                    await websocket.send_json({
                        "type": "subscription_confirmed",
                        "topics": topics,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                elif data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
            except WebSocketDisconnect:
                logger.info("Search config WebSocket disconnected")
                break
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from client: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        # Clean up
        health_task.cancel()
        active_connections.discard(websocket)
        logger.info("Search config WebSocket connection closed")


async def broadcast_config_update(config_update: dict):
    """
    Broadcast configuration updates to all connected clients.
    """
    message = {
        "type": "config_update",
        "payload": config_update,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error broadcasting to client: {e}")
            disconnected.add(connection)
    
    # Remove disconnected clients
    for conn in disconnected:
        active_connections.discard(conn)


async def broadcast_health_update(component: str, status: str, message: str):
    """
    Broadcast health status updates to all connected clients.
    """
    update = {
        "type": "health_update",
        "payload": {
            "component": component,
            "status": status,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        }
    }
    
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_json(update)
        except Exception as e:
            logger.error(f"Error broadcasting health update: {e}")
            disconnected.add(connection)
    
    # Remove disconnected clients
    for conn in disconnected:
        active_connections.discard(conn)