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
            # TODO: IMPLEMENTATION ENGINEER - Implement real-time push logic
            data = await websocket.receive_text()
            # Broadcast received message to all clients (simple demo)
            for conn in active_connections:
                if conn is not websocket:
                    try:
                        await conn.send_text(f"Broadcast: {data}")
                    except Exception as e:
                        logging.error(f"Failed to send to client: {e}")
            # Echo for scaffolding
            await websocket.send_text(f"Received: {data}")
    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
        # TODO: IMPLEMENTATION ENGINEER - Handle disconnect cleanup
        if websocket in active_connections:
            active_connections.remove(websocket)
        logging.info("Cleaned up WebSocket connection")
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)