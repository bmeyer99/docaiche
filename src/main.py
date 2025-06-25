"""
FastAPI application entry point for AI Documentation Cache System
PRD-001: HTTP API Foundation - Main Application

This module implements the comprehensive FastAPI application with all PRD-001
components: middleware, exception handlers, rate limiting, and complete API endpoints.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.core.config import get_settings
from src.core.config.manager import get_current_configuration
from src.core.security import SecurityMiddleware
from src.api.v1.api import api_router, setup_exception_handlers
from src.api.v1.middleware import LoggingMiddleware, limiter, rate_limit_handler
from src.api.v1.dependencies import cleanup_dependencies

# Configure structured logging for container environments
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager for startup and shutdown logic.
    
    Manages dependency initialization and cleanup as specified in PRD-001.
    
    Args:
        app: The FastAPI application instance
        
    Yields:
        None: Control during application lifetime
    """
    # Startup logic
    logger.info("AI Documentation Cache System API starting up...")
    try:
        # Initialize configuration system first
        logger.info("Initializing configuration system...")
        config = await get_current_configuration()
        logger.info(f"Configuration initialized - Environment: {config.app.environment}")
        
        # Initialize rate limiter state
        app.state.limiter = limiter
        
        logger.info("Application startup completed successfully")
        yield
        
    except Exception as startup_error:
        logger.error(f"Startup failed: {startup_error}")
        # Still yield to prevent application crash - use default config
        logger.warning("Continuing with default configuration due to startup failure")
        app.state.limiter = limiter
        yield
        
    finally:
        # Shutdown logic
        logger.info("AI Documentation Cache System API shutting down...")
        try:
            await cleanup_dependencies()
            logger.info("Dependency cleanup completed")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        logger.info("AI Documentation Cache System API shutdown complete")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application with all PRD-001 components.
    
    Returns:
        FastAPI: The fully configured FastAPI application instance
    """
    # Use default settings during application creation
    # Real configuration will be loaded during startup in lifespan
    try:
        settings = get_settings()
        logger.info(f"Creating application with environment: {settings.app.environment}")
    except Exception as e:
        logger.warning(f"Failed to load settings during app creation: {e}")
        # Create with minimal defaults if config system fails
        class DefaultSettings:
            class App:
                environment = "development"
                api_host = "0.0.0.0"
                api_port = 8080
                debug = True
                log_level = "INFO"
            app = App()
        settings = DefaultSettings()
    
    # Create FastAPI application with comprehensive OpenAPI configuration
    application = FastAPI(
        title="AI Documentation Cache System API",
        version="1.0.0",
        description="Intelligent documentation cache with AI-powered search and enrichment",
        openapi_tags=[
            {"name": "search", "description": "Search operations"},
            {"name": "feedback", "description": "User feedback collection"},
            {"name": "admin", "description": "Administrative operations"},
            {"name": "config", "description": "Configuration management"},
            {"name": "health", "description": "System health monitoring"},
        ],
        lifespan=lifespan,
        docs_url="/docs",  # API-006: Auto-generated OpenAPI documentation
        redoc_url="/redoc"
    )
    
    # Add CORS middleware with development-friendly defaults
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Development mode - allow all origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # API-005: Add rate limiting middleware
    application.state.limiter = limiter
    application.add_middleware(SlowAPIMiddleware)
    
    # API-007 & API-010: Add structured logging middleware
    application.add_middleware(LoggingMiddleware)
    
    # Add security middleware for production environments
    if hasattr(settings, 'app') and hasattr(settings.app, 'environment'):
        if settings.app.environment == "production":
            application.add_middleware(SecurityMiddleware)
    
    # Setup all exception handlers (API-004, API-009)
    setup_exception_handlers(application)
    
    # Include API router with v1 prefix
    application.include_router(api_router, prefix="/api/v1")
    
    # Serve React static files
    static_dir = Path(__file__).parent / "web_ui" / "static"
    if static_dir.exists():
        # Mount static files
        application.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info(f"Static files mounted from {static_dir}")
        
        # Build path for React app
        react_build_dir = static_dir / "web" / "dist"
        if react_build_dir.exists():
            # Serve React app for non-API routes (SPA fallback)
            @application.get("/{full_path:path}")
            async def serve_react_app(request: Request, full_path: str):
                """
                Serve React app for all non-API routes to support client-side routing.
                This acts as a fallback for React Router.
                """
                # Don't interfere with API routes
                if full_path.startswith("api/"):
                    return {"error": "API route not found"}
                
                # Serve index.html for all other routes
                index_file = react_build_dir / "index.html"
                if index_file.exists():
                    return FileResponse(index_file)
                else:
                    return {"error": "React app not built"}
            
            logger.info(f"React SPA fallback configured for {react_build_dir}")
        else:
            logger.warning(f"React build directory not found: {react_build_dir}")
    else:
        logger.warning(f"Static directory not found: {static_dir}")
    
    logger.info("FastAPI application created and configured successfully")
    return application


# Create the application instance
app = create_application()


if __name__ == "__main__":
    """
    Run the application using uvicorn when executed directly.
    Configuration matches the task specification.
    """
    try:
        settings = get_settings()
        host = settings.app.api_host
        port = settings.app.api_port
        debug = settings.app.debug
        log_level = settings.app.log_level.lower()
    except Exception as e:
        logger.warning(f"Failed to load settings for uvicorn: {e}")
        # Use defaults if config fails
        host = "0.0.0.0"
        port = 8080
        debug = True
        log_level = "info"
    
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level=log_level
    )