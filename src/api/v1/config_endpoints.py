"""
Configuration API Endpoints - PRD-001: HTTP API Foundation
Configuration management and collections endpoints
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request

from .schemas import (
    ConfigurationResponse, ConfigurationItem, ConfigurationUpdateRequest,
    Collection, CollectionsResponse
)
from .middleware import limiter
from .dependencies import get_anythingllm_client
from src.clients.anythingllm import AnythingLLMClient
from src.core.config import get_settings

logger = logging.getLogger(__name__)

# Create router for configuration endpoints
router = APIRouter()


@router.get("/config", response_model=ConfigurationResponse, tags=["config"])
@limiter.limit("10/minute")
async def get_configuration(
    request: Request
) -> ConfigurationResponse:
    """
    GET /api/v1/config - Retrieves the current system configuration
    
    Args:
        request: FastAPI request object (required for rate limiting)
        
    Returns:
        ConfigurationResponse with current configuration items
    """
    try:
        config = get_settings()
        
        # Return non-sensitive configuration items
        items = [
            ConfigurationItem(
                key="app.environment",
                value=config.app.environment,
                description="Application environment"
            ),
            ConfigurationItem(
                key="app.debug",
                value=config.app.debug,
                description="Debug mode enabled"
            ),
            ConfigurationItem(
                key="content.chunk_size_default",
                value=config.content.chunk_size_default,
                description="Default content chunk size"
            ),
            ConfigurationItem(
                key="redis.host",
                value=config.redis.host,
                description="Redis host address"
            )
        ]
        
        return ConfigurationResponse(
            items=items,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Configuration retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Configuration unavailable")


@router.post("/config", status_code=202, tags=["config"])
@limiter.limit("5/minute")
async def update_configuration(
    request: Request,
    config_request: ConfigurationUpdateRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """
    POST /api/v1/config - Updates a specific part of the system configuration
    
    Args:
        request: FastAPI request object (required for rate limiting)
        config_request: Configuration update request
        background_tasks: FastAPI background tasks for processing
        
    Returns:
        Confirmation message with HTTP 202
    """
    try:
        logger.info(f"Configuration update request: {config_request.key}")
        
        # Add background task to update configuration (placeholder)
        def update_config():
            logger.info(f"Updating configuration: {config_request.key} = {config_request.value}")
            # TODO: Implement configuration update logic
        
        background_tasks.add_task(update_config)
        
        return {"message": f"Configuration update for {config_request.key} queued"}
        
    except Exception as e:
        logger.error(f"Configuration update failed: {e}")
        raise HTTPException(status_code=500, detail="Configuration update failed")


@router.get("/collections", response_model=CollectionsResponse, tags=["search"])
@limiter.limit("30/minute")
async def get_collections(
    request: Request,
    anythingllm_client: AnythingLLMClient = Depends(get_anythingllm_client)
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
        # Mock collections data conforming to schema
        collections = [
            Collection(
                slug="python-docs",
                name="Python Documentation",
                technology="python",
                document_count=1234,
                last_updated=datetime.utcnow(),
                is_active=True
            ),
            Collection(
                slug="react-docs",
                name="React Documentation",
                technology="react",
                document_count=567,
                last_updated=datetime.utcnow(),
                is_active=True
            ),
            Collection(
                slug="fastapi-docs",
                name="FastAPI Documentation",
                technology="python",
                document_count=234,
                last_updated=datetime.utcnow(),
                is_active=True
            )
        ]
        
        return CollectionsResponse(
            collections=collections,
            total_count=len(collections)
        )
        
    except Exception as e:
        logger.error(f"Collections retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Collections unavailable")