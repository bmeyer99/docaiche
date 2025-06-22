"""
FastAPI application entry point for AI Documentation Cache System
PRD-001: HTTP API Foundation - Main Application

This module implements the FastAPI application initialization exactly as specified
in task API-001, including CORS middleware, security middleware, and basic health endpoint.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from core.security import SecurityMiddleware
from api.v1.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager for startup and shutdown logic.
    
    Args:
        app: The FastAPI application instance
        
    Yields:
        None: Control during application lifetime
    """
    # Startup logic
    logger.info("AI Documentation Cache System API starting up...")
    try:
        settings = get_settings()
        logger.info(f"Application starting in {settings.ENVIRONMENT} mode")
        yield
    finally:
        # Shutdown logic
        logger.info("AI Documentation Cache System API shutting down...")


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: The configured FastAPI application instance
    """
    settings = get_settings()
    
    # Create FastAPI application with exact specifications from task
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
        lifespan=lifespan
    )
    
    # Add CORS middleware as specified in task requirements
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    
    # Add security middleware as specified in task requirements
    if settings.SECURITY_HEADERS_ENABLED:
        application.add_middleware(SecurityMiddleware)
    
    # Include API router with v1 prefix
    application.include_router(api_router, prefix="/api/v1")
    
    logger.info("FastAPI application created and configured successfully")
    return application


# Create the application instance
app = create_application()


if __name__ == "__main__":
    """
    Run the application using uvicorn when executed directly.
    Configuration matches the task specification.
    """
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL
    )