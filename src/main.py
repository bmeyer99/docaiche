"""
Simplified Docaiche API

A clean, maintainable FastAPI application that consolidates all functionality
into a single service with essential middleware and clear error handling.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from api.endpoints import api_router
from api.schemas import ProblemDetail
from core.middleware import LoggingMiddleware
from core.exceptions import setup_exception_handlers


# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"🚀 Docaiche API starting up at {datetime.utcnow()}")
    
    yield
    
    # Shutdown
    print(f"🛑 Docaiche API shutting down at {datetime.utcnow()}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title="Docaiche Simplified API",
        description="Simplified documentation search and content management API",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Custom logging middleware
    app.add_middleware(LoggingMiddleware)
    
    # Rate limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # Exception handlers
    setup_exception_handlers(app)
    
    # API routes
    app.include_router(api_router, prefix="/api/v1")
    
    # Static files (for frontend)
    try:
        app.mount("/static", StaticFiles(directory="static"), name="static")
    except RuntimeError:
        # Static directory doesn't exist - that's ok for API-only deployments
        pass
    
    # Health check endpoint (outside versioning for monitoring)
    @app.get("/health")
    async def root_health():
        """Basic health check endpoint."""
        return {"status": "healthy", "timestamp": datetime.utcnow()}
    
    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )