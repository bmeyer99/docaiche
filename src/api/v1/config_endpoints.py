"""
Configuration API Endpoints - PRD-003 CFG-009: API Endpoints Integration
Configuration management endpoints integrated with PRD-001 HTTP API Foundation

Implements /api/v1/config GET and POST endpoints with ConfigurationManager integration
as specified in CFG-009 requirements.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Request, Body

from .schemas import (
    ConfigurationResponse, ConfigurationItem, ConfigurationUpdateRequest,
    Collection, CollectionsResponse, LLMProviderTestRequest
)
from .middleware import limiter
from .dependencies import get_anythingllm_client
from src.clients.anythingllm import AnythingLLMClient
from src.core.config import get_configuration_manager, get_system_configuration

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


@router.get("/", response_model=ConfigurationResponse)
@limiter.limit("10/minute")
async def get_configuration(
    request: Request
) -> ConfigurationResponse:
    """
    GET /api/v1/config - Retrieves the current system configuration dynamically from the database.
    
    This endpoint provides comprehensive configuration access by loading all items
    directly from the ConfigurationManager.
    
    Args:
        request: FastAPI request object (required for rate limiting)
        
    Returns:
        ConfigurationResponse with all current configuration items
    """
    try:
        config_manager = await get_configuration_manager()
        # Dynamically load all configuration items from the database
        all_items = await config_manager.get_all_from_db()
        
        # Convert database models to response items
        response_items = [
            ConfigurationItem(key=item.key, value=item.value, description=item.description)
            for item in all_items
        ]
        
        return ConfigurationResponse(
            items=response_items,
            timestamp=datetime.utcnow()
        )
        
    except Exception as e:
        logger.error(f"Dynamic configuration retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="Configuration unavailable")


@router.post("/", status_code=200)
@limiter.limit("30/minute") # Increased limit for real-time saving
async def update_configuration(
    request: Request,
    config_request: ConfigurationUpdateRequest
) -> Dict[str, Any]:
    """
    POST /api/v1/config - Updates a single configuration item and returns the saved value.
    
    This endpoint provides a synchronous, atomic update mechanism for individual settings.
    
    Args:
        request: FastAPI request object (for rate limiting and user auditing)
        config_request: The configuration key and value to update.
        
    Returns:
        A confirmation dictionary with the saved key-value pair.
    """
    try:
        logger.info(f"Sync configuration update: {config_request.key} = {config_request.value}")
        
        # Validate configuration key format
        if not config_request.key or '.' not in config_request.key:
            raise HTTPException(
                status_code=400,
                detail="Configuration key must be in dot notation format (e.g., 'app.debug')"
            )
        
        # Extract user from request for auditing
        user = "anonymous"
        if hasattr(request, "user") and getattr(request.user, "username", None):
            user = request.user.username
        elif request.headers.get("x-user"):
            user = request.headers.get("x-user")

        # Perform synchronous update in the database
        config_manager = await get_configuration_manager()
        await config_manager.update_in_db(config_request.key, config_request.value, user=user)
        
        logger.info(f"Configuration saved successfully: {config_request.key}")
        
        # Broadcast updates for relevant configuration changes
        if config_request.key.startswith(('ai.', 'llm.', 'ollama.', 'openai.')):
            await broadcast_llm_health_status()
            
        if WEBSOCKET_AVAILABLE:
            await websocket_manager.broadcast_config_update(
                config_request.key,
                config_request.value
            )
            
        # Return the successfully saved data
        return {
            "message": "Configuration updated successfully",
            "key": config_request.key,
            "value": config_request.value,
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Configuration update failed for key '{config_request.key}': {e}")
        raise HTTPException(status_code=500, detail=f"Update failed for {config_request.key}")


@router.get("/collections", response_model=CollectionsResponse)
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


@router.post("/llm/test-connection")
async def test_llm_provider_connection(req: LLMProviderTestRequest):
    """Test connection to a given LLM provider."""
    import httpx
    
    try:
        logger.info(f"Testing connection to {req.provider} at {req.base_url}")
        
        # Use a HEAD request for a lightweight connection test
        endpoint = req.base_url.rstrip('/')
        headers = {"Content-Type": "application/json"}
        if req.api_key:
            headers["Authorization"] = f"Bearer {req.api_key}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.head(endpoint, headers=headers)
            
            # Consider any 2xx or 3xx status as a successful connection
            if 200 <= response.status_code < 400:
                logger.info(f"Connection to {req.provider} successful with status {response.status_code}")
                return {"success": True, "message": "Connection successful"}
            else:
                logger.warning(f"Connection test to {req.provider} failed with status {response.status_code}")
                return {"success": False, "message": f"Connection failed: HTTP {response.status_code}"}

    except httpx.TimeoutException:
        logger.error(f"Connection timeout to {req.provider}")
        return {"success": False, "message": "Connection timeout"}
    except httpx.ConnectError as e:
        logger.error(f"Connection error to {req.provider}: {e}")
        return {"success": False, "message": f"Cannot reach endpoint at {req.base_url}"}
    except Exception as e:
        logger.error(f"LLM provider test failed: {e}")
        return {"success": False, "message": f"An unexpected error occurred: {str(e)}"}


@router.post("/llm/list-models")
async def list_llm_provider_models(req: LLMProviderTestRequest):
    """Fetches a list of available models from the specified LLM provider."""
    import httpx

    try:
        logger.info(f"Fetching models from {req.provider} at {req.base_url}")

        if req.provider.lower() == "ollama":
            base_url_clean = req.base_url.rstrip('/').replace('/api', '')
            endpoint = f"{base_url_clean}/api/tags"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(endpoint, headers={"Content-Type": "application/json"})
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    formatted_models = [{"name": m.get("name", ""), "size": m.get("size", 0), "modified_at": m.get("modified_at", "")} for m in models]
                    return {"success": True, "models": formatted_models, "model_count": len(formatted_models)}
                else:
                    return {"success": False, "message": f"Failed to fetch models: HTTP {response.status_code}", "models": []}

        elif req.provider.lower() == "openai":
            endpoint = "https://api.openai.com/v1/models"
            headers = {"Authorization": f"Bearer {req.api_key}", "Content-Type": "application/json"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(endpoint, headers=headers)
                if response.status_code == 200:
                    models = response.json().get("data", [])
                    formatted_models = [{"name": m.get("id", ""), "owned_by": m.get("owned_by", ""), "created": m.get("created", 0)} for m in models]
                    return {"success": True, "models": formatted_models, "model_count": len(formatted_models)}
                else:
                    return {"success": False, "message": f"Failed to fetch models: HTTP {response.status_code}", "models": []}

        elif req.provider.lower() == "anthropic":
            common_models = [
                {"name": "claude-3-sonnet-20240229"},
                {"name": "claude-3-haiku-20240307"},
                {"name": "claude-3-opus-20240229"}
            ]
            return {"success": True, "models": common_models, "model_count": len(common_models)}

        else:
            return {"success": False, "message": f"Unsupported provider: {req.provider}", "models": []}

    except httpx.TimeoutException:
        logger.error(f"Timeout fetching models from {req.provider}")
        return {"success": False, "message": "Connection timeout", "models": []}
    except httpx.ConnectError as e:
        logger.error(f"Connection error fetching models from {req.provider}: {e}")
        return {"success": False, "message": f"Cannot reach endpoint at {req.base_url}", "models": []}
    except Exception as e:
        logger.error(f"Failed to list LLM models: {e}")
        return {"success": False, "message": f"An unexpected error occurred: {str(e)}", "models": []}

