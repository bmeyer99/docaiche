"""Web UI Service FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from src.web_ui.api_gateway.router import api_router
from src.web_ui.real_time_service.websocket import websocket_router
from src.web_ui.config.settings import WebUISettings
import logging
import os

settings = WebUISettings()

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self';"
        return response

def create_app() -> FastAPI:
    """Create and configure FastAPI app for the Web UI Service."""
    app = FastAPI(title="Web UI Service", version="1.0.0")
    
    # Add session middleware for CSRF protection

    app.add_middleware(SessionMiddleware, secret_key=os.urandom(24))
    app.add_middleware(SecurityHeadersMiddleware)

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(websocket_router)

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

    # --- Frontend Routes ---
    @app.get("/", response_class=HTMLResponse)
    async def serve_dashboard():
        return "<html><body>Dashboard</body></html>"

    @app.get("/config", response_class=HTMLResponse)
    async def serve_config(request: Request):
        request.session["csrf"] = "dummy_token"
        return "<html><body>Configuration</body></html>"

    @app.get("/content", response_class=HTMLResponse)
    async def serve_content():
        return "<html><body>Content</body></html>"

    return app

app = create_app()