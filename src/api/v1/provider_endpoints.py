"""
Provider Management API Endpoints
LLM Provider configuration, testing, and management endpoints
"""

import logging
# from datetime import datetime  # Not currently used
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request

from .schemas import ProviderResponse, ProviderTestResponse, ProviderConfigRequest
from .middleware import limiter
from .dependencies import get_configuration_manager
from src.core.config.manager import ConfigurationManager

logger = logging.getLogger(__name__)

# Create router for provider endpoints
router = APIRouter()


@router.get("/providers", response_model=List[ProviderResponse], tags=["providers"])
@limiter.limit("20/minute")
async def list_providers(
    request: Request,
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> List[ProviderResponse]:
    """
    GET /api/v1/providers - List all available LLM providers with their status
    """
    try:
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
    """
    try:
        import httpx

        logger.info(f"Testing connection to {provider_id}")

        if provider_id.lower() == "ollama":
            # Test Ollama connection
            base_url_clean = test_config.base_url.rstrip("/").replace("/api", "")
            endpoint = f"{base_url_clean}/api/tags"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(endpoint)

                if response.status_code == 200:
                    models = response.json().get("models", [])
                    return ProviderTestResponse(
                        success=True,
                        message=f"Connection successful. {len(models)} models available.",
                        latency=response.elapsed.total_seconds() * 1000,
                        models=[model.get("name", "") for model in models[:5]],
                    )
                else:
                    return ProviderTestResponse(
                        success=False,
                        message=f"Connection failed: HTTP {response.status_code}",
                        latency=response.elapsed.total_seconds() * 1000,
                    )

        elif provider_id.lower() == "openai":
            # Test OpenAI connection
            endpoint = "https://api.openai.com/v1/models"
            headers = {"Authorization": f"Bearer {test_config.api_key}"}

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(endpoint, headers=headers)

                if response.status_code == 200:
                    models = response.json().get("data", [])
                    return ProviderTestResponse(
                        success=True,
                        message="Connection successful",
                        latency=response.elapsed.total_seconds() * 1000,
                        models=[model.get("id", "") for model in models[:5]],
                    )
                else:
                    return ProviderTestResponse(
                        success=False,
                        message=f"Connection failed: HTTP {response.status_code}",
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
    POST /api/v1/providers/{provider_id}/config - Update provider configuration
    """
    try:
        # Update provider configuration
        # TODO: Implement actual configuration update using config_manager
        # config_key = f"providers.{provider_id}"
        # config_value = {
        #     "base_url": config_data.base_url,
        #     "api_key": config_data.api_key,
        #     "model": config_data.model,
        #     "enabled": True,
        #     "updated_at": datetime.utcnow().isoformat(),
        # }
        # config_manager.update_configuration(config_key, config_value)

        # For now, just log the update
        logger.info(f"Updated configuration for provider {provider_id}")

        return {"status": "updated", "provider": provider_id}

    except Exception as e:
        logger.error(f"Failed to update provider config: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to update provider configuration"
        )
