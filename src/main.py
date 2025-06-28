"""
Simplified Docaiche API

A clean, maintainable FastAPI application that consolidates all functionality
into a single service with essential middleware and clear error handling.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api.v1.api import api_router, setup_exception_handlers
from src.core.middleware import LoggingMiddleware


# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"🚀 Docaiche API starting up at {datetime.utcnow()}")

    # Initialize configuration manager
    try:
        from src.core.config.manager import ConfigurationManager

        config_manager = ConfigurationManager()
        await config_manager.initialize()
        await config_manager.load_configuration()
        print("✅ Configuration manager initialized and loaded")
    except Exception as e:
        print(f"⚠️ Configuration manager initialization failed: {e}")

    yield

    # Shutdown
    print(f"🛑 Docaiche API shutting down at {datetime.utcnow()}")

    # Cleanup dependencies
    try:
        from src.api.v1.dependencies import cleanup_dependencies

        await cleanup_dependencies()
        print("✅ Dependencies cleaned up")
    except Exception as e:
        print(f"⚠️ Dependency cleanup failed: {e}")


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
