"""
Configuration API Endpoints - PRD-003 CFG-009: API Endpoints Integration
Configuration management endpoints integrated with PRD-001 HTTP API Foundation

Implements /api/v1/config GET and POST endpoints with ConfigurationManager integration
as specified in CFG-009 requirements.
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
from src.core.config import get_settings, get_configuration_manager, get_system_configuration

logger = logging.getLogger(__name__)

# Create router for configuration endpoints
router = APIRouter()

# Import WebSocket manager for real-time updates
try:
    from src.web_ui.real_time_service.websocket import websocket_manager
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    logger.warning("WebSocket manager not available - real-time updates disabled")


async def broadcast_llm_health_status() -> None:
    """
    Check LLM provider health status and broadcast updates via WebSocket.
    
    This function performs the same health checks as the health endpoint
    and broadcasts the status to all connected WebSocket clients.
    """
    if not WEBSOCKET_AVAILABLE:
        return
        
    try:
        config = get_system_configuration()
        ai_config = getattr(config, "ai", None)
        healthy_providers = []
        unhealthy_providers = []
        llm_provider_messages = []
        
        # Check Ollama
        if ai_config and getattr(ai_config, "ollama", None):
            from src.llm.ollama_provider import OllamaProvider
            ollama_provider = OllamaProvider(config=ai_config.ollama.model_dump())
            ollama_health = await ollama_provider.health_check()
            if ollama_health.get("status") == "healthy":
                healthy_providers.append("ollama")
            else:
                unhealthy_providers.append("ollama")
                llm_provider_messages.append(f"Ollama: {ollama_health.get('error', ollama_health.get('status', 'Unavailable'))}")
        
        # Check OpenAI
        if ai_config and getattr(ai_config, "openai", None):
            from src.llm.openai_provider import OpenAIProvider
            openai_provider = OpenAIProvider(config=ai_config.openai.model_dump())
            openai_health = await openai_provider.health_check()
            if openai_health.get("status") == "healthy":
                healthy_providers.append("openai")
            else:
                unhealthy_providers.append("openai")
                llm_provider_messages.append(f"OpenAI: {openai_health.get('error', openai_health.get('status', 'Unavailable'))}")
        
        # Determine overall LLM provider status
        if healthy_providers:
            llm_status = {
                "status": "configured",
                "message": f"LLM providers enabled: {', '.join(healthy_providers)}",
                "healthy_providers": healthy_providers,
                "unhealthy_providers": unhealthy_providers
            }
        elif unhealthy_providers:
            llm_status = {
                "status": "unavailable",
                "message": "No healthy LLM providers. " + "; ".join(llm_provider_messages),
                "healthy_providers": [],
                "unhealthy_providers": unhealthy_providers
            }
        else:
            llm_status = {
                "status": "none_configured",
                "message": "No LLM providers enabled",
                "healthy_providers": [],
                "unhealthy_providers": []
            }
        
        # Broadcast the LLM health status
        await websocket_manager.broadcast_llm_health(llm_status)
        logger.debug(f"Broadcast LLM health status: {llm_status['status']}")
        
    except Exception as e:
        logger.error(f"Error broadcasting LLM health status: {e}")
        # Broadcast error status
        error_status = {
            "status": "error",
            "message": f"Error checking LLM providers: {str(e)}",
            "healthy_providers": [],
            "unhealthy_providers": []
        }
        await websocket_manager.broadcast_llm_health(error_status)


@router.get("/config", response_model=ConfigurationResponse, tags=["config"])
@limiter.limit("10/minute")
async def get_configuration(
    request: Request
) -> ConfigurationResponse:
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
                description="Application environment (development/production/testing)"
            ),
            ConfigurationItem(
                key="app.debug",
                value=config.app.debug,
                description="Debug mode enabled"
            ),
            ConfigurationItem(
                key="app.log_level",
                value=config.app.log_level,
                description="Logging level"
            ),
            ConfigurationItem(
                key="app.api_port",
                value=config.app.api_port,
                description="API service port"
            ),
            ConfigurationItem(
                key="app.workers",
                value=config.app.workers,
                description="Number of worker processes"
            ),
            
            # Content processing configuration
            ConfigurationItem(
                key="content.chunk_size_default",
                value=config.content.chunk_size_default,
                description="Default content chunk size in characters"
            ),
            ConfigurationItem(
                key="content.chunk_size_max",
                value=config.content.chunk_size_max,
                description="Maximum content chunk size in characters"
            ),
            ConfigurationItem(
                key="content.quality_threshold",
                value=config.content.quality_threshold,
                description="Minimum quality score for content processing"
            ),
            
            # Redis configuration (non-sensitive)
            ConfigurationItem(
                key="redis.host",
                value=config.redis.host,
                description="Redis cache server host"
            ),
            ConfigurationItem(
                key="redis.port",
                value=config.redis.port,
                description="Redis cache server port"
            ),
            ConfigurationItem(
                key="redis.db",
                value=config.redis.db,
                description="Redis database number"
            ),
            ConfigurationItem(
                key="redis.max_connections",
                value=config.redis.max_connections,
                description="Maximum Redis connections in pool"
            ),
            
            # AI configuration (non-sensitive)
            ConfigurationItem(
                key="ai.primary_provider",
                value=config.ai.primary_provider,
                description="Primary AI/LLM provider"
            ),
            ConfigurationItem(
                key="ai.enable_failover",
                value=config.ai.enable_failover,
                description="Enable AI provider failover"
            ),
            ConfigurationItem(
                key="ai.cache_ttl_seconds",
                value=config.ai.cache_ttl_seconds,
                description="AI response cache TTL in seconds"
            ),
            
            # Service endpoints (non-sensitive)
            ConfigurationItem(
                key="anythingllm.endpoint",
                value=config.anythingllm.endpoint,
                description="AnythingLLM service endpoint"
            ),
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
    
    CFG-009: API Endpoints Integration
    Updates configuration using ConfigurationManager with database persistence
    
    Args:
        request: FastAPI request object (required for rate limiting)
        config_request: Configuration update request
        background_tasks: FastAPI background tasks for processing
        
    Returns:
        Confirmation message with HTTP 202
    """
    try:
        logger.info(f"Configuration update request: {config_request.key} = {config_request.value}")
        
        # Validate configuration key format
        if not config_request.key or '.' not in config_request.key:
            raise HTTPException(
                status_code=400,
                detail="Configuration key must be in dot notation format (e.g., 'app.debug')"
            )
        
        # Add background task to update configuration using ConfigurationManager
        async def update_config():
            try:
                config_manager = await get_configuration_manager()
                
                # Update configuration in database with runtime reload
                await config_manager.update_in_db(config_request.key, config_request.value)
                
                logger.info(f"Configuration updated successfully: {config_request.key}")
                
                # Check if this config change affects LLM providers and broadcast health status
                if config_request.key.startswith(('ai.', 'llm.', 'ollama.', 'openai.')):
                    await broadcast_llm_health_status()
                    
                # Broadcast configuration update
                if WEBSOCKET_AVAILABLE:
                    await websocket_manager.broadcast_config_update(
                        config_request.key,
                        config_request.value
                    )
                
            except Exception as e:
                logger.error(f"Configuration update failed: {config_request.key} - {e}")
        
        background_tasks.add_task(update_config)
        
        return {
            "message": f"Configuration update for '{config_request.key}' queued",
            "key": config_request.key,
            "status": "accepted"
        }
        
    except HTTPException:
        raise
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