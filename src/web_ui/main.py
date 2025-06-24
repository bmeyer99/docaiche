"""Web UI Service FastAPI application entry point."""

from fastapi import FastAPI
from src.web_ui.api_gateway.router import api_router
from src.web_ui.real_time_service.websocket import websocket_router
import logging

def create_app() -> FastAPI:
    """Create and configure FastAPI app for the Web UI Service."""
    app = FastAPI(title="Web UI Service", version="1.0.0")
    app.include_router(api_router, prefix="/api")
    app.include_router(websocket_router)
    # TODO: IMPLEMENTATION ENGINEER - Add middleware, error handlers, and startup/shutdown events
    return app

app = create_app()