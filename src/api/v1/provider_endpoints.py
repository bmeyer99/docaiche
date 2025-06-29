"""
Provider Management API Endpoints
LLM Provider configuration, testing, and management endpoints
"""

import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from .schemas import ProviderResponse, ProviderTestResponse, ProviderConfigRequest
from .middleware import limiter, get_trace_id
from .dependencies import get_configuration_manager
from src.core.config.manager import ConfigurationManager

# Import the new provider registry system
try:
    from src.llm import (
        get_provider_registry,
        ProviderRegistry,
        ProviderInfo,
        ProviderCapabilities,
        TestResult,
        ProviderHealth,
        HealthStatus
    )
    REGISTRY_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"Provider registry not available: {e}")
    REGISTRY_AVAILABLE = False

logger = logging.getLogger(__name__)

# Import enhanced logging for provider security monitoring
try:
    from src.logging_config import SecurityLogger, ExternalServiceLogger
    _security_logger = SecurityLogger(logger)
    _service_logger = ExternalServiceLogger(logger)
except ImportError:
    _security_logger = None
    _service_logger = None
    logger.warning("Enhanced provider security logging not available")

# Create router for provider endpoints
router = APIRouter()


def get_registry() -> Optional[ProviderRegistry]:
    """Dependency to get provider registry instance if available"""
    if REGISTRY_AVAILABLE:
        return get_provider_registry()
    return None


@router.get("/provider-registry-status", tags=["providers"])
@limiter.limit("30/minute")
async def get_provider_registry_stats(
    request: Request,
    registry: Optional[ProviderRegistry] = Depends(get_registry)
) -> Dict[str, Any]:
    """
    GET /api/v1/providers/registry/stats - Get provider registry statistics
    This endpoint tests if the new provider registry system is working
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    trace_id = get_trace_id(request)
    
    try:
        # Log access to provider registry status (sensitive operation)
        if _security_logger:
            _security_logger.log_sensitive_operation(
                operation="provider_registry_access",
                resource="provider_stats",
                client_ip=client_ip,
                trace_id=trace_id
            )
        
        if not registry or not REGISTRY_AVAILABLE:
            duration_ms = (time.time() - start_time) * 1000
            
            if _service_logger:
                _service_logger.log_service_call(
                    service="provider_registry",
                    endpoint="stats",
                    method="GET",
                    duration_ms=duration_ms,
                    status_code=503,
                    registry_available=False
                )
            
            return {
                "registry_available": False,
                "message": "Provider registry system not available",
                "fallback_mode": True,
                "static_providers_count": 2
            }
        
        stats = registry.get_registry_stats()
        duration_ms = (time.time() - start_time) * 1000
        
        if _service_logger:
            _service_logger.log_service_call(
                service="provider_registry",
                endpoint="stats",
                method="GET",
                duration_ms=duration_ms,
                status_code=200,
                registry_available=True,
                provider_count=stats.get("total_providers", 0)
            )
        
        return {
            "registry_available": True,
            "message": "Provider registry system operational",
            "fallback_mode": False,
            "stats": stats
        }
        
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        if _service_logger:
            _service_logger.log_service_call(
                service="provider_registry",
                endpoint="stats",
                method="GET",
                duration_ms=duration_ms,
                status_code=500,
                error_message=str(e)
            )
        
        logger.error(f"Failed to get registry stats: {e}")
        return {
            "registry_available": False,
            "message": f"Registry error: {str(e)}",
            "fallback_mode": True,
            "error": str(e)
        }


@router.get("/providers", response_model=List[ProviderResponse], tags=["providers"])
@limiter.limit("20/minute")
async def list_providers(
    request: Request,
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> List[ProviderResponse]:
    """
    GET /api/v1/providers - List all available LLM providers with their status
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    trace_id = get_trace_id(request)
    
    try:
        # Log access to provider list (sensitive operation)
        if _security_logger:
            _security_logger.log_sensitive_operation(
                operation="provider_list_access",
                resource="provider_configurations",
                client_ip=client_ip,
                trace_id=trace_id
            )
        
        # Get all configured providers - comprehensive list
        providers = [
            ProviderResponse(
                id="ollama",
                name="Ollama",
                type="text_generation",
                status="available",
                configured=False,
                category="local",
                description="Local LLM inference server with support for multiple models",
                requires_api_key=False,
                supports_embedding=True,
                supports_chat=True,
            ),
            ProviderResponse(
                id="openai",
                name="OpenAI",
                type="text_generation",
                status="available",
                configured=False,
                category="cloud",
                description="OpenAI GPT models and embeddings",
                requires_api_key=True,
                supports_embedding=True,
                supports_chat=True,
            ),
            ProviderResponse(
                id="openrouter",
                name="OpenRouter",
                type="text_generation",
                status="available",
                configured=False,
                category="cloud",
                description="Access to multiple LLM providers through one API",
                requires_api_key=True,
                supports_embedding=False,
                supports_chat=True,
            ),
            ProviderResponse(
                id="anthropic",
                name="Anthropic Claude",
                type="text_generation",
                status="available",
                configured=False,
                category="cloud",
                description="Anthropic Claude models for advanced reasoning",
                requires_api_key=True,
                supports_embedding=False,
                supports_chat=True,
            ),
            ProviderResponse(
                id="groq",
                name="Groq",
                type="text_generation",
                status="available",
                configured=False,
                category="cloud",
                description="Ultra-fast LLM inference with Groq chips",
                requires_api_key=True,
                supports_embedding=False,
                supports_chat=True,
            ),
            ProviderResponse(
                id="lmstudio",
                name="LM Studio",
                type="text_generation",
                status="available",
                configured=False,
                category="local",
                description="Local LLM inference with LM Studio",
                requires_api_key=False,
                supports_embedding=True,
                supports_chat=True,
            ),
            ProviderResponse(
                id="mistral",
                name="Mistral AI",
                type="text_generation",
                status="available",
                configured=False,
                category="cloud",
                description="Mistral AI models for efficient inference",
                requires_api_key=True,
                supports_embedding=True,
                supports_chat=True,
            ),
            ProviderResponse(
                id="litellm",
                name="LiteLLM",
                type="text_generation",
                status="available",
                configured=False,
                category="gateway",
                description="Universal proxy for 100+ LLM APIs with unified interface",
                requires_api_key=False,
                supports_embedding=True,
                supports_chat=True,
            ),
        ]

        return providers

    except Exception as e:
        logger.error(f"Failed to list providers: {e}")
        raise HTTPException(status_code=500, detail="Failed to list providers")


@router.post(
    "/providers/{provider_id}/test",
    response_model=ProviderTestResponse,
    tags=["providers"],
)
@limiter.limit("10/minute")
async def test_provider_connection(
    request: Request, provider_id: str, test_config: ProviderConfigRequest
) -> ProviderTestResponse:
    """
    POST /api/v1/providers/{provider_id}/test - Test connection to LLM provider
    
    For providers that support model discovery (Ollama, LM Studio, OpenRouter),
    this will return available models. For others, it tests the connection only.
    """
    start_time = time.time()
    
    try:
        import httpx

        logger.info(f"Testing connection to {provider_id}")

        if provider_id.lower() == "ollama":
            # Test Ollama connection and get available models
            if not test_config.base_url:
                return ProviderTestResponse(
                    success=False,
                    message="Base URL is required for Ollama",
                    latency=0,
                )
            
            base_url_clean = test_config.base_url.rstrip("/").replace("/api", "")
            endpoint = f"{base_url_clean}/api/tags"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(endpoint)

                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model_names = [model.get("name", "") for model in models]
                    
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Log successful Ollama provider test
                    if _service_logger:
                        _service_logger.log_service_call(
                            service=provider_id,
                            endpoint=endpoint,
                            method="GET",
                            duration_ms=duration_ms,
                            status_code=200,
                            model_count=len(models)
                        )
                    
                    return ProviderTestResponse(
                        success=True,
                        message=f"Connection successful. {len(models)} models available.",
                        latency=response.elapsed.total_seconds() * 1000,
                        models=model_names,
                    )
                else:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Log failed Ollama provider test
                    if _service_logger:
                        _service_logger.log_service_call(
                            service=provider_id,
                            endpoint=endpoint,
                            method="GET",
                            duration_ms=duration_ms,
                            status_code=response.status_code
                        )
                    
                    return ProviderTestResponse(
                        success=False,
                        message=f"Connection failed: HTTP {response.status_code}",
                        latency=response.elapsed.total_seconds() * 1000,
                    )

        elif provider_id.lower() == "lmstudio":
            # Test LM Studio connection and get available models
            if not test_config.base_url:
                return ProviderTestResponse(
                    success=False,
                    message="Base URL is required for LM Studio",
                    latency=0,
                )
            
            base_url_clean = test_config.base_url.rstrip("/")
            endpoint = f"{base_url_clean}/v1/models"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(endpoint)

                if response.status_code == 200:
                    models = response.json().get("data", [])
                    model_names = [model.get("id", "") for model in models]
                    
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Log successful LM Studio provider test
                    if _service_logger:
                        _service_logger.log_service_call(
                            service=provider_id,
                            endpoint=endpoint,
                            method="GET",
                            duration_ms=duration_ms,
                            status_code=200,
                            model_count=len(models)
                        )
                    
                    return ProviderTestResponse(
                        success=True,
                        message=f"Connection successful. {len(models)} models available.",
                        latency=response.elapsed.total_seconds() * 1000,
                        models=model_names,
                    )
                else:
                    return ProviderTestResponse(
                        success=False,
                        message=f"Connection failed: HTTP {response.status_code}",
                        latency=response.elapsed.total_seconds() * 1000,
                    )

        elif provider_id.lower() == "openrouter":
            # Test OpenRouter connection and get available models
            if not test_config.api_key:
                return ProviderTestResponse(
                    success=False,
                    message="API key is required for OpenRouter",
                    latency=0,
                )
            
            endpoint = "https://openrouter.ai/api/v1/models"
            headers = {"Authorization": f"Bearer {test_config.api_key}"}

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(endpoint, headers=headers)

                if response.status_code == 200:
                    models = response.json().get("data", [])
                    # OpenRouter returns many models, filter to show most relevant
                    model_names = [model.get("id", "") for model in models[:50]]
                    
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Log successful OpenRouter provider test
                    if _service_logger:
                        _service_logger.log_service_call(
                            service=provider_id,
                            endpoint=endpoint,
                            method="GET",
                            duration_ms=duration_ms,
                            status_code=200,
                            model_count=len(models)
                        )
                    
                    return ProviderTestResponse(
                        success=True,
                        message=f"Connection successful. {len(models)} models available.",
                        latency=response.elapsed.total_seconds() * 1000,
                        models=model_names,
                    )
                else:
                    return ProviderTestResponse(
                        success=False,
                        message=f"Connection failed: HTTP {response.status_code}",
                        latency=response.elapsed.total_seconds() * 1000,
                    )

        elif provider_id.lower() in ["openai", "anthropic", "groq", "mistral"]:
            # For non-queryable providers, just test the connection
            # These providers don't support listing models via API
            if not test_config.api_key:
                return ProviderTestResponse(
                    success=False,
                    message=f"API key is required for {provider_id}",
                    latency=0,
                )
            
            # Simple connectivity test based on provider
            test_endpoints = {
                "openai": "https://api.openai.com/v1/models",
                "anthropic": "https://api.anthropic.com/v1/messages",
                "groq": "https://api.groq.com/openai/v1/models",
                "mistral": "https://api.mistral.ai/v1/models"
            }
            
            endpoint = test_endpoints.get(provider_id.lower())
            if not endpoint:
                return ProviderTestResponse(
                    success=False,
                    message=f"Provider {provider_id} not configured for testing",
                    latency=0,
                )
            
            headers = {"Authorization": f"Bearer {test_config.api_key}"}
            
            # For Anthropic, we need different headers
            if provider_id.lower() == "anthropic":
                headers = {
                    "x-api-key": test_config.api_key,
                    "anthropic-version": "2023-06-01"
                }

            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    # For Anthropic, we need to send a minimal request
                    if provider_id.lower() == "anthropic":
                        response = await client.post(
                            endpoint,
                            headers=headers,
                            json={
                                "model": "claude-3-opus-20240229",
                                "messages": [{"role": "user", "content": "Hi"}],
                                "max_tokens": 1
                            }
                        )
                        # For Anthropic, 200 is success, 401 is auth failure
                        success = response.status_code in [200, 400]  # 400 might be rate limit
                    else:
                        response = await client.get(endpoint, headers=headers)
                        success = response.status_code == 200

                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Log provider test
                    if _service_logger:
                        _service_logger.log_service_call(
                            service=provider_id,
                            endpoint=endpoint,
                            method="GET" if provider_id.lower() != "anthropic" else "POST",
                            duration_ms=duration_ms,
                            status_code=response.status_code
                        )
                    
                    if success:
                        return ProviderTestResponse(
                            success=True,
                            message="Connection successful. Models are not queryable for this provider.",
                            latency=response.elapsed.total_seconds() * 1000,
                            models=None,  # No model discovery for these providers
                        )
                    else:
                        error_msg = "Connection failed"
                        if response.status_code == 401:
                            error_msg = "Invalid API key"
                        elif response.status_code == 403:
                            error_msg = "Access forbidden - check API key permissions"
                        
                        return ProviderTestResponse(
                            success=False,
                            message=f"{error_msg}: HTTP {response.status_code}",
                            latency=response.elapsed.total_seconds() * 1000,
                        )
                except Exception as e:
                    return ProviderTestResponse(
                        success=False,
                        message=f"Connection test failed: {str(e)}",
                        latency=0,
                    )

        elif provider_id.lower() == "litellm":
            # Test LiteLLM proxy connection
            base_url_clean = test_config.base_url.rstrip("/")
            endpoint = f"{base_url_clean}/v1/models"
            headers = {"Content-Type": "application/json"}
            
            if test_config.api_key:
                headers["Authorization"] = f"Bearer {test_config.api_key}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(endpoint, headers=headers)

                if response.status_code == 200:
                    models = response.json().get("data", [])
                    return ProviderTestResponse(
                        success=True,
                        message=f"LiteLLM proxy connection successful. {len(models)} models available.",
                        latency=response.elapsed.total_seconds() * 1000,
                        models=[model.get("id", "") for model in models[:5]],
                    )
                else:
                    return ProviderTestResponse(
                        success=False,
                        message=f"LiteLLM proxy connection failed: HTTP {response.status_code}",
                        latency=response.elapsed.total_seconds() * 1000,
                    )

        else:
            return ProviderTestResponse(
                success=False,
                message=f"Provider {provider_id} not supported",
                latency=0,
            )

    except httpx.TimeoutException:
        return ProviderTestResponse(
            success=False, message="Connection timeout", latency=10000
        )
    except Exception as e:
        logger.error(f"Provider test failed: {e}")
        return ProviderTestResponse(
            success=False, message=f"Test failed: {str(e)}", latency=0
        )


@router.post("/providers/{provider_id}/config", tags=["providers"])
@limiter.limit("10/minute")
async def update_provider_config(
    request: Request,
    provider_id: str,
    config_data: ProviderConfigRequest,
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
):
    """
    POST /api/v1/providers/{provider_id}/config - Update provider configuration (supports partial updates)
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    trace_id = get_trace_id(request)
    
    try:
        # Validate that at least one field is provided
        provided_fields = {k: v for k, v in config_data.dict().items() if v is not None}
        if not provided_fields:
            raise HTTPException(
                status_code=400, 
                detail="At least one configuration field must be provided"
            )

        # Log the partial update attempt
        if _security_logger:
            _security_logger.log_admin_action(
                action="provider_config_partial_update",
                target=f"provider_{provider_id}",
                impact_level="medium",
                client_ip=client_ip,
                trace_id=trace_id,
                fields_updated=list(provided_fields.keys())
            )

        # Get existing configuration or create new one
        config_key = f"ai.providers.{provider_id}"
        try:
            existing_config = config_manager.get_setting(config_key) or {}
        except Exception:
            existing_config = {}

        # Merge provided fields with existing configuration
        updated_config = {**existing_config}
        for field, value in provided_fields.items():
            updated_config[field] = value
        
        # Add metadata
        updated_config["enabled"] = updated_config.get("enabled", True)
        updated_config["updated_at"] = datetime.utcnow().isoformat()

        # Update configuration in database
        await config_manager.update_in_db(config_key, updated_config)

        duration_ms = (time.time() - start_time) * 1000
        
        # Log successful update
        if _service_logger:
            _service_logger.log_service_call(
                service="config_manager",
                endpoint=f"update_provider_{provider_id}",
                method="POST",
                duration_ms=duration_ms,
                status_code=200,
                fields_updated=list(provided_fields.keys())
            )

        logger.info(f"Partial configuration update for provider {provider_id}: {list(provided_fields.keys())}")

        return {
            "status": "updated", 
            "provider": provider_id,
            "fields_updated": list(provided_fields.keys()),
            "config": updated_config
        }

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        
        # Log configuration update failure
        if _security_logger:
            _security_logger.log_admin_action(
                action="provider_config_update_failed",
                target=f"provider_{provider_id}",
                impact_level="medium",
                client_ip=client_ip,
                trace_id=trace_id,
                error_message=str(e),
                duration_ms=duration_ms
            )

        logger.error(f"Failed to update provider config for {provider_id}: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update provider configuration"
        )


@router.get("/providers/{provider_id}/models", tags=["providers"])
@limiter.limit("30/minute")
async def get_provider_models(
    request: Request,
    provider_id: str,
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
):
    """
    GET /api/v1/providers/{provider_id}/models - Get available models for a provider
    
    For queryable providers (Ollama, LM Studio, OpenRouter), this returns live data.
    For non-queryable providers (OpenAI, Anthropic, etc.), this returns a default list
    plus any custom models the user has added.
    """
    # Define which providers support model querying
    queryable_providers = ["ollama", "lmstudio", "openrouter"]
    
    # Default models for non-queryable providers
    default_models = {
        "openai": [
            "gpt-4-turbo-preview",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ],
        "anthropic": [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
        ],
        "groq": [
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma-7b-it",
        ],
        "mistral": [
            "mistral-large-latest",
            "mistral-medium-latest",
            "mistral-small-latest",
            "mistral-embed",
        ],
    }
    
    provider_lower = provider_id.lower()
    
    if provider_lower in queryable_providers:
        # For queryable providers, return empty list - frontend should query after test
        return {
            "provider": provider_id,
            "models": [],
            "queryable": True,
            "message": "Use the test endpoint to discover available models"
        }
    else:
        # For non-queryable providers, return default + custom models
        models = default_models.get(provider_lower, []).copy()
        
        # Get custom models from configuration
        config_key = f"ai.providers.{provider_id}.custom_models"
        custom_models = config_manager.get_setting(config_key) or []
        
        # Combine default and custom models, removing duplicates
        all_models = list(dict.fromkeys(models + custom_models))
        
        return {
            "provider": provider_id,
            "models": all_models,
            "queryable": False,
            "default_count": len(models),
            "custom_count": len(custom_models)
        }


@router.post("/providers/{provider_id}/models", tags=["providers"])
@limiter.limit("20/minute")
async def add_custom_model(
    request: Request,
    provider_id: str,
    body: Dict[str, str],
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
):
    """
    POST /api/v1/providers/{provider_id}/models - Add a custom model to a provider
    
    This is only applicable for non-queryable providers (OpenAI, Anthropic, etc.)
    """
    queryable_providers = ["ollama", "lmstudio", "openrouter"]
    
    if provider_id.lower() in queryable_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot add custom models to {provider_id} - models are discovered automatically"
        )
    
    model_name = body.get("model_name", "").strip()
    if not model_name:
        raise HTTPException(status_code=400, detail="Model name cannot be empty")
    
    # Get existing custom models
    config_key = f"ai.providers.{provider_id}.custom_models"
    custom_models = config_manager.get_setting(config_key) or []
    
    # Check if model already exists
    if model_name in custom_models:
        raise HTTPException(status_code=409, detail="Model already exists")
    
    # Add the new model
    custom_models.append(model_name)
    
    # Update configuration
    await config_manager.update_in_db(config_key, custom_models)
    
    logger.info(f"Added custom model '{model_name}' to provider {provider_id}")
    
    return {
        "status": "added",
        "provider": provider_id,
        "model": model_name,
        "custom_models": custom_models
    }


@router.delete("/providers/{provider_id}/models/{model_name}", tags=["providers"])
@limiter.limit("20/minute")
async def remove_custom_model(
    request: Request,
    provider_id: str,
    model_name: str,
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
):
    """
    DELETE /api/v1/providers/{provider_id}/models/{model_name} - Remove a custom model
    
    This only removes custom models, not default ones.
    """
    queryable_providers = ["ollama", "lmstudio", "openrouter"]
    
    if provider_id.lower() in queryable_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot manage custom models for {provider_id} - models are discovered automatically"
        )
    
    # Get existing custom models
    config_key = f"ai.providers.{provider_id}.custom_models"
    custom_models = config_manager.get_setting(config_key) or []
    
    # Check if model exists in custom models
    if model_name not in custom_models:
        raise HTTPException(status_code=404, detail="Custom model not found")
    
    # Remove the model
    custom_models.remove(model_name)
    
    # Update configuration
    await config_manager.update_in_db(config_key, custom_models)
    
    logger.info(f"Removed custom model '{model_name}' from provider {provider_id}")
    
    return {
        "status": "removed",
        "provider": provider_id,
        "model": model_name,
        "custom_models": custom_models
    }
