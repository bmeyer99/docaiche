"""
Simplified Docaiche API

A clean, maintainable FastAPI application that consolidates all functionality
into a single service with essential middleware and clear error handling.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api.v1.api import api_router, setup_exception_handlers
from src.core.middleware.correlation_middleware import CorrelationIDMiddleware, setup_correlation_logging
from src.logging_config import setup_structured_logging, MetricsLogger


# Setup structured logging
setup_structured_logging()
logger = logging.getLogger(__name__)
metrics = MetricsLogger(logger)

# Rate limiter setup
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print(f"🚀 DocAIche API starting up at {datetime.utcnow()}")

    # Initialize configuration manager
    try:
        from src.core.config.manager import ConfigurationManager

        config_manager = ConfigurationManager()
        await config_manager.initialize()
        await config_manager.load_configuration()
        print("✅ Configuration manager initialized and loaded")
        
        # Initialize provider configurations in database
        try:
            from src.startup.init_providers import initialize_providers
            success = await initialize_providers()
            if success:
                print("✅ Provider database initialization completed")
            else:
                print("⚠️ Provider database initialization failed")
        except Exception as e:
            print(f"⚠️ Provider database initialization error: {e}")
            
        # Initialize default AnythingLLM workspace - ALWAYS RUN THIS
        # This is independent of provider initialization
        try:
            from src.database.init_workspace import init_workspace
            import asyncio
            
            # Run the sync function in a thread
            workspace_success = await asyncio.to_thread(init_workspace)
            if workspace_success:
                print("✅ Default workspace initialization completed")
            else:
                print("⚠️ Default workspace initialization failed")
        except Exception as e:
            print(f"⚠️ Default workspace initialization error: {e}")
            
        # Don't close the config manager here - it will be used throughout the app lifecycle
        
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
        title="DocAIche API",
        description="""
        ## DocAIche - AI-Powered Documentation Search and Analysis Platform

        Comprehensive API for AI documentation management with advanced logging, monitoring, and troubleshooting capabilities.

        ### Features
        - **Intelligent Document Search**: AI-powered semantic search across multiple documentation sources
        - **Real-time AI Logs**: Advanced logging system with correlation tracking and pattern detection
        - **Content Management**: Document ingestion, processing, and enrichment pipelines
        - **Workspace Management**: Multi-tenant workspace isolation and analytics
        - **Monitoring & Analytics**: Comprehensive metrics, health checks, and performance monitoring

        ### AI Logs API
        The AI Logs API provides specialized endpoints for AI agents and developers:
        - Query logs with intelligent filtering and optimization
        - Real-time streaming with WebSocket connections
        - Correlation analysis across distributed services
        - Pattern detection and anomaly identification
        - Multi-format export capabilities

        ### Authentication
        API endpoints require authentication via API key in the Authorization header:
        ```
        Authorization: Bearer your_api_key_here
        ```

        ### Rate Limiting
        All endpoints implement rate limiting for fair usage. Limits vary by endpoint type:
        - Standard endpoints: 60 requests/minute
        - AI Logs queries: 60 requests/minute
        - WebSocket connections: 10 concurrent connections
        - Export operations: 10 requests/minute
        """,
        version="2.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        contact={
            "name": "DocAIche API Support",
            "email": "api-support@docaiche.com",
            "url": "https://docs.docaiche.com"
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT"
        },
        openapi_tags=[
            {
                "name": "Health Checks",
                "description": "System health and status endpoints"
            },
            {
                "name": "AI Logs Query",
                "description": "Query and filter logs with AI optimization"
            },
            {
                "name": "AI Logs Analysis",
                "description": "Correlation analysis and pattern detection"
            },
            {
                "name": "AI Logs Streaming",
                "description": "Real-time log streaming via WebSocket"
            },
            {
                "name": "AI Logs Tracking",
                "description": "Conversation and workspace tracking"
            },
            {
                "name": "AI Logs Export",
                "description": "Export logs in various formats"
            },
            {
                "name": "Search",
                "description": "Document search and retrieval"
            },
            {
                "name": "Admin",
                "description": "Administrative operations"
            },
            {
                "name": "Configuration",
                "description": "System configuration management"
            },
            {
                "name": "Workspaces",
                "description": "Multi-tenant workspace management"
            }
        ]
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Correlation ID middleware
    app.add_middleware(CorrelationIDMiddleware)
    
    # Setup correlation logging
    setup_correlation_logging()

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
