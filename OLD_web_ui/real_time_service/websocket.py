"""WebSocket router for real-time updates in Web UI Service."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any, List, Set
import json
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

websocket_router = APIRouter()


class WebSocketManager:
    """Manages WebSocket connections and broadcasts real-time updates."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        
    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Active connections: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Active connections: {len(self.active_connections)}")
            
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket) -> None:
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(websocket)
            
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connected WebSocket clients."""
        if not self.active_connections:
            logger.debug("No active WebSocket connections to broadcast to")
            return
            
        message_str = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Failed to send broadcast message: {e}")
                disconnected.append(connection)
                
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
            
        if disconnected:
            logger.info(f"Cleaned up {len(disconnected)} disconnected WebSocket connections")
            
    async def broadcast_llm_health(self, health_status: Dict[str, Any]) -> None:
        """Broadcast LLM health status update to all connected clients."""
        message = {
            "type": "llm_health",
            "data": health_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast(message)
        logger.debug(f"Broadcast LLM health status: {health_status}")
        
    async def broadcast_config_update(self, config_key: str, config_value: Any) -> None:
        """Broadcast configuration update to all connected clients."""
        message = {
            "type": "config_update",
            "data": {
                "key": config_key,
                "value": config_value
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast(message)
        logger.debug(f"Broadcast config update: {config_key} = {config_value}")


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


@websocket_router.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for pushing real-time updates to the UI.
    Handles connection, message sending, and disconnect events.
    """
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                # Try to parse as JSON for structured messages
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket_manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                        websocket
                    )
                elif message.get("type") == "subscribe":
                    # Handle subscription requests (for future use)
                    await websocket_manager.send_personal_message(
                        {"type": "subscribed", "data": message.get("data", {})},
                        websocket
                    )
                else:
                    # Echo back unknown structured messages
                    await websocket_manager.send_personal_message(
                        {"type": "echo", "data": message},
                        websocket
                    )
            except json.JSONDecodeError:
                # Handle plain text messages for backward compatibility
                if data.strip().lower() == "ping":
                    await websocket.send_text("pong")
                else:
                    await websocket.send_text("update")
                    
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info("WebSocket disconnected gracefully")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)