"""Web UI Service FastAPI application entry point."""

from fastapi import FastAPI, Request, Form, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from src.web_ui.api_gateway.router import api_router
from src.web_ui.real_time_service.websocket import websocket_router
from src.web_ui.config.settings import WebUISettings
from fastapi import APIRouter

# Placeholder MCP router for future endpoint support
mcp_router = APIRouter()

@mcp_router.get("/status")
async def mcp_status():
    return {"status": "MCP endpoint ready"}

import logging
import os
import httpx
import secrets

settings = WebUISettings()

# Initialize templates
templates = Jinja2Templates(directory="src/web_ui/templates")

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; style-src 'self' 'unsafe-inline';"
        return response

def create_app() -> FastAPI:
    """Create and configure FastAPI app for the Web UI Service."""
    app = FastAPI(title="Web UI Service", version="1.0.0")

    # Add session middleware for CSRF protection
    app.add_middleware(SessionMiddleware, secret_key=os.urandom(24))
    app.add_middleware(SecurityHeadersMiddleware)

    # Mount static files
    app.mount("/static", StaticFiles(directory="src/web_ui/static"), name="static")

    app.include_router(api_router, prefix="/api/v1")
    app.include_router(websocket_router)
    app.include_router(mcp_router, prefix="/mcp")

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

    @app.get("/", response_class=HTMLResponse)
    async def serve_dashboard(request: Request):
        """Serve the main dashboard page."""
        # Generate CSRF token for session
        if "csrf" not in request.session:
            request.session["csrf"] = secrets.token_urlsafe(32)
        
        return templates.TemplateResponse("dashboard.html", {"request": request})

    @app.get("/config", response_class=HTMLResponse)
    async def serve_config(request: Request):
        """Serve the configuration management page."""
        # Generate CSRF token for session
        if "csrf" not in request.session:
            request.session["csrf"] = secrets.token_urlsafe(32)
        
        return templates.TemplateResponse("config.html", {"request": request})

    @app.post("/config")
    async def config_post(
        request: Request,
        setting1: str = Form(None),
        setting2: str = Form(None),
        csrf: str = Form(None)
    ):
        """
        Handle config form POST with CSRF and input validation.
        Returns 400/403 for CSRF/method errors, 400/422 for invalid input, 200 for success.
        """
        try:
            # CSRF validation
            session_csrf = request.session.get("csrf")
            req_csrf = csrf or request.headers.get("x-csrf-token") or request.cookies.get("csrf")
            if not session_csrf or not req_csrf or session_csrf != req_csrf:
                logging.warning("CSRF validation failed on /config POST")
                return JSONResponse(status_code=403, content={"error": "CSRF validation failed"})
            # Input validation
            errors = []
            if setting1 is None or not isinstance(setting1, str):
                errors.append("Invalid value for setting1")
            if setting2 not in ("true", "false", True, False, None):
                errors.append("Invalid value for setting2")
            if errors:
                return JSONResponse(status_code=422, content={"error": "; ".join(errors)})
            # Simulate config update (in-memory, real logic in API)
            # Redirect to config page on success
            return RedirectResponse(url="/config", status_code=status.HTTP_303_SEE_OTHER)
        except Exception as e:
            logging.error(f"Error in /config POST: {e}")
            return JSONResponse(status_code=500, content={"error": "Internal server error"})

    @app.get("/content", response_class=HTMLResponse)
    async def serve_content(request: Request):
        """Serve the content management page."""
        # Generate CSRF token for session
        if "csrf" not in request.session:
            request.session["csrf"] = secrets.token_urlsafe(32)
        
        return templates.TemplateResponse("content.html", {"request": request})

    return app

app = create_app()