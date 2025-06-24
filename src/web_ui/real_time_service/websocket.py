"""WebSocket router for real-time updates in Web UI Service."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging

websocket_router = APIRouter()

active_connections = set()

@websocket_router.websocket("/ws/updates")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for pushing real-time updates to the UI.
    Handles connection, message sending, and disconnect events.
    """
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Respond with "pong" if "ping", else "update"
            if data.strip().lower() == "ping":
                await websocket.send_text("pong")
            else:
                await websocket.send_text("update")
            # Broadcast received message to all clients (simple demo)
            for conn in active_connections:
                if conn is not websocket:
                    try:
                        await conn.send_text(f"Broadcast: {data}")
                    except Exception as e:
                        logging.error(f"Failed to send to client: {e}")
    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
        if websocket in active_connections:
            active_connections.remove(websocket)
        logging.info("Cleaned up WebSocket connection")
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)