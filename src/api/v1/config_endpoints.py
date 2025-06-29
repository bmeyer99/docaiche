"""
Configuration API Endpoints - PRD-003 CFG-009: API Endpoints Integration
Configuration management endpoints integrated with PRD-001 HTTP API Foundation

Implements /api/v1/config GET and POST endpoints with ConfigurationManager integration
as specified in CFG-009 requirements.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request

from .schemas import (
    ConfigurationResponse,
    ConfigurationItem,
    ConfigurationUpdateRequest,
    Collection,
    CollectionsResponse,
)
from .middleware import limiter, get_trace_id
from .dependencies import get_anythingllm_client
from src.clients.anythingllm import AnythingLLMClient
from src.core.config import get_settings, get_configuration_manager

logger = logging.getLogger(__name__)

# Import enhanced logging for configuration security monitoring
try:
    from src.logging_config import SecurityLogger
    _security_logger = SecurityLogger(logger)
except ImportError:
    _security_logger = None
    logger.warning("Enhanced configuration security logging not available")

# Create router for configuration endpoints
router = APIRouter()


@router.get("/config", response_model=ConfigurationResponse, tags=["config"])
@limiter.limit("10/minute")
async def get_configuration(request: Request) -> ConfigurationResponse:
    """
    GET /api/v1/config - Retrieves the current system configuration

    CFG-009: API Endpoints Integration
    Integrates with ConfigurationManager for comprehensive configuration access

    Args:
        request: FastAPI request object (required for rate limiting)

    Returns:
        ConfigurationResponse with current configuration items
    """
    try:
        # Use ConfigurationManager for hierarchical configuration access
        try:
            config_manager = await get_configuration_manager()
            config = config_manager.get_configuration()
        except Exception:
            # Fall back to legacy method for compatibility
            config = get_settings()

        # Return non-sensitive configuration items with comprehensive coverage
        items = [
            # Application configuration
            ConfigurationItem(
                key="app.environment",
                value=config.app.environment,
                description="Application environment (development/production/testing)",
            ),
            ConfigurationItem(
                key="app.debug",
                value=config.app.debug,
                description="Debug mode enabled",
            ),
            ConfigurationItem(
                key="app.log_level",
                value=config.app.log_level,
                description="Logging level",
            ),
            ConfigurationItem(
                key="app.api_port",
                value=config.app.api_port,
                description="API service port",
            ),
            ConfigurationItem(
                key="app.workers",
                value=config.app.workers,
                description="Number of worker processes",
            ),
            # Content processing configuration
            ConfigurationItem(
                key="content.chunk_size_default",
                value=config.content.chunk_size_default,
                description="Default content chunk size in characters",
            ),
            ConfigurationItem(
                key="content.chunk_size_max",
                value=config.content.chunk_size_max,
                description="Maximum content chunk size in characters",
            ),
            ConfigurationItem(
                key="content.quality_threshold",
                value=config.content.quality_threshold,
                description="Minimum quality score for content processing",
            ),
            # Redis configuration (non-sensitive)
            ConfigurationItem(
                key="redis.host",
                value=config.redis.host,
                description="Redis cache server host",
            ),
            ConfigurationItem(
                key="redis.port",
                value=config.redis.port,
                description="Redis cache server port",
            ),
            ConfigurationItem(
                key="redis.db",
                value=config.redis.db,
                description="Redis database number",
            ),
            ConfigurationItem(
                key="redis.max_connections",
                value=config.redis.max_connections,
                description="Maximum Redis connections in pool",
            ),
            # AI configuration (non-sensitive)
            ConfigurationItem(
                key="ai.primary_provider",
                value=config.ai.primary_provider,
                description="Primary AI/LLM provider",
            ),
            ConfigurationItem(
                key="ai.enable_failover",
                value=config.ai.enable_failover,
                description="Enable AI provider failover",
            ),
            ConfigurationItem(
                key="ai.cache_ttl_seconds",
                value=config.ai.cache_ttl_seconds,
                description="AI response cache TTL in seconds",
            ),
            # Service endpoints (non-sensitive)
            ConfigurationItem(
                key="anythingllm.endpoint",
                value=config.anythingllm.endpoint,
                description="AnythingLLM service endpoint",
            ),
        ]

        return ConfigurationResponse(items=items, timestamp=datetime.utcnow())

    except Exception as e:
        logger.error(f"Configuration retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Configuration unavailable")


@router.post("/config", status_code=202, tags=["config"])
@limiter.limit("5/minute")
async def update_configuration(
    request: Request,
    config_request: ConfigurationUpdateRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, str]:
    """
    POST /api/v1/config - Updates a specific part of the system configuration

    CFG-009: API Endpoints Integration
    Updates configuration using ConfigurationManager with database persistence

    Args:
        request: FastAPI request object (required for rate limiting)
        config_request: Configuration update request
        background_tasks: FastAPI background tasks for processing

    Returns:
        Confirmation message with HTTP 202
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    trace_id = get_trace_id(request)
    
    try:
        logger.info(
            f"Configuration update request: {config_request.key} = {config_request.value}"
        )

        # Validate configuration key format
        if not config_request.key or "." not in config_request.key:
            raise HTTPException(
                status_code=400,
                detail="Configuration key must be in dot notation format (e.g., 'app.debug')",
            )

        # Add background task to update configuration using ConfigurationManager
        async def update_config():
            try:
                config_manager = await get_configuration_manager()

                # Update configuration in database with runtime reload
                await config_manager.update_in_db(
                    config_request.key, config_request.value
                )

                logger.info(f"Configuration updated successfully: {config_request.key}")

            except Exception as e:
                logger.error(f"Configuration update failed: {config_request.key} - {e}")

        background_tasks.add_task(update_config)
        duration_ms = (time.time() - start_time) * 1000
        
        # Log successful initiation of config update
        if _security_logger:
            _security_logger.log_admin_action(
                action="configuration_update_initiated",
                target=config_request.key,
                impact_level="high",
                client_ip=client_ip,
                duration_ms=duration_ms,
                trace_id=trace_id,
                status="accepted"
            )

        return {
            "message": f"Configuration update for '{config_request.key}' queued",
            "key": config_request.key,
            "status": "accepted",
        }

    except HTTPException:
        # Log validation errors
        if _security_logger:
            _security_logger.log_admin_action(
                action="configuration_update_validation_failed",
                target=config_request.key,
                impact_level="low",
                client_ip=client_ip,
                trace_id=trace_id,
                error_message="Validation failed"
            )
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Log configuration update system failure
        if _security_logger:
            _security_logger.log_admin_action(
                action="configuration_update_system_failed",
                target=config_request.key,
                impact_level="medium",
                client_ip=client_ip,
                error_message=str(e),
                duration_ms=duration_ms,
                trace_id=trace_id,
                requires_review=True
            )
        
        logger.error(f"Configuration update failed: {e}")
        raise HTTPException(status_code=500, detail="Configuration update failed")


@router.get("/collections", response_model=CollectionsResponse, tags=["search"])
@limiter.limit("30/minute")
async def get_collections(
    request: Request,
    anythingllm_client: AnythingLLMClient = Depends(get_anythingllm_client),
) -> CollectionsResponse:
    """
    GET /api/v1/collections - Lists available documentation collections (workspaces)

    Args:
        request: FastAPI request object (required for rate limiting)
        anythingllm_client: AnythingLLM client dependency

    Returns:
        CollectionsResponse with available collections
    """
    try:
        # Get workspaces from AnythingLLM
        workspaces = await anythingllm_client.list_workspaces()
        
        # Convert to Collection objects
        collections = []
        for ws in workspaces:
            # Count documents in workspace
            try:
                docs = await anythingllm_client.list_documents(ws["slug"])
                doc_count = len(docs)
            except:
                doc_count = 0
                
            collections.append(
                Collection(
                    slug=ws["slug"],
                    name=ws["name"],
                    technology="unknown",  # AnythingLLM doesn't track technology
                    document_count=doc_count,
                    last_updated=datetime.utcnow(),  # Not tracked by AnythingLLM
                    is_active=True,
                )
            )

        return CollectionsResponse(
            collections=collections, total_count=len(collections)
        )

    except Exception as e:
        logger.error(f"Collections retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Collections unavailable")
