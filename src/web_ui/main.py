"""Web UI Service FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.web_ui.api_gateway.router import api_router
from src.web_ui.real_time_service.websocket import websocket_router
from src.web_ui.config.settings import WebUISettings
import logging

settings = WebUISettings()

def create_app() -> FastAPI:
    """Create and configure FastAPI app for the Web UI Service."""
    app = FastAPI(title="Web UI Service", version="1.0.0")
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(websocket_router)

    # TODO: IMPLEMENTATION ENGINEER - Add middleware, error handlers, and startup/shutdown events

    # CORS middleware for web UI integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.allowed_origins] if settings.allowed_origins != "*" else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handler for generic exceptions
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logging.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # Startup event
    @app.on_event("startup")
    async def on_startup():
        logging.info("Web UI Service startup complete.")

    # Shutdown event
    @app.on_event("shutdown")
    async def on_shutdown():
        logging.info("Web UI Service shutdown complete.")

    return app

app = create_app()