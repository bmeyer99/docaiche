"""
OpenRouter LLM Provider - Phase 2.1 Implementation
Access to 100+ models through OpenRouter API with unified interface
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional

import httpx

from ..base_provider import BaseLLMProvider, LLMProviderError
from ..models import (
    ProviderCapabilities, ProviderCategory, ModelInfo, ModelDiscoveryResult,
    TextGenerationRequest, TextGenerationResponse,
    EmbeddingRequest, EmbeddingResponse
)
from ..provider_registry import register_provider

logger = logging.getLogger(__name__)


@register_provider("openrouter", ProviderCategory.CLOUD)
class OpenRouterProvider(BaseLLMProvider):
    """
    OpenRouter provider implementation providing access to 100+ models
    through a unified API interface.
    """
    
    _provider_id = "openrouter"
    _display_name = "OpenRouter"
    _description = "Access to 100+ LLM models through unified API"
    _category = ProviderCategory.CLOUD

    def __init__(self, config: Dict[str, Any], cache_manager=None):
        super().__init__(config, cache_manager)
        
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://openrouter.ai/api/v1")
        self.default_model = config.get("model", "meta-llama/llama-4-maverick")
        self.timeout = config.get("timeout_seconds", 60)
        
        if not self.api_key:
            raise ValueError("OpenRouter API key is required")
    
    @classmethod
    def get_static_capabilities(cls) -> ProviderCapabilities:
        """OpenRouter supports text generation and model discovery"""
        return ProviderCapabilities(
            text_generation=True,
            embeddings=False,  # OpenRouter doesn't provide embedding models
            streaming=True,
            function_calling=True,
            local=False,
            model_discovery=True
        )
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """JSON schema for OpenRouter configuration"""
        return {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "OpenRouter API key",
                    "minLength": 10
                },
                "base_url": {
                    "type": "string",
                    "description": "OpenRouter API base URL",
                    "default": "https://openrouter.ai/api/v1"
                },
                "model": {
                    "type": "string",
                    "description": "Default model to use",
                    "default": "meta-llama/llama-4-maverick"
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Request timeout in seconds",
                    "minimum": 10,
                    "maximum": 300,
                    "default": 60
                }
            },
            "required": ["api_key"],
            "additionalProperties": False
        }
    
    def _create_circuit_breaker(self):
        """Create OpenRouter-specific circuit breaker"""
        # TODO: Implement circuit breaker logic
        pass
    
    async def _make_request(self, prompt: str, **kwargs) -> str:
        """Make request to OpenRouter API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://docaiche.com",  # Required by OpenRouter
            "X-Title": "Docaiche - AI Documentation Cache"
        }
        
        model = kwargs.get("model", self.default_model)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 4096)
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_msg = f"OpenRouter API error: {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail.get('error', {}).get('message', 'Unknown error')}"
                    except:
                        error_msg += f" - {response.text}"
                    raise LLMProviderError(error_msg)
                
                result = response.json()
                
                if "choices" not in result or not result["choices"]:
                    raise LLMProviderError("No response choices returned from OpenRouter")
                
                return result["choices"][0]["message"]["content"]
                
        except httpx.TimeoutException:
            raise LLMProviderError(f"OpenRouter request timed out after {self.timeout}s")
        except httpx.RequestError as e:
            raise LLMProviderError(f"OpenRouter request failed: {str(e)}")
        except Exception as e:
            raise LLMProviderError(f"OpenRouter provider error: {str(e)}")
    
    async def generate_text(self, request: TextGenerationRequest) -> TextGenerationResponse:
        """Generate text using OpenRouter"""
        try:
            response_text = await self._make_request(
                request.prompt,
                model=request.model or self.default_model,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            return TextGenerationResponse(
                text=response_text,
                model=request.model or self.default_model,
                provider="openrouter",
                finish_reason="stop"
            )
            
        except Exception as e:
            logger.error(f"OpenRouter text generation failed: {e}")
            raise LLMProviderError(f"Text generation failed: {str(e)}")
    
    async def generate_embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """OpenRouter doesn't support embeddings"""
        raise LLMProviderError("OpenRouter does not support embedding generation")
    
    async def discover_models(self, config: Dict[str, Any]) -> ModelDiscoveryResult:
        """Discover available models from OpenRouter"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise LLMProviderError(f"Model discovery failed: {response.status_code}")
                
                models_data = response.json()
                text_models = []
                
                for model in models_data.get("data", []):
                    model_info = ModelInfo(
                        id=model["id"],
                        name=model.get("name", model["id"]),
                        description=model.get("description", ""),
                        context_window=model.get("context_length", 4096),
                        max_tokens=model.get("max_completion_tokens", 4096),
                        cost_per_token=model.get("pricing", {}).get("prompt", 0),
                        capabilities=["text_generation", "chat"],
                        provider_specific=model
                    )
                    text_models.append(model_info)
                
                logger.info(f"Discovered {len(text_models)} models from OpenRouter")
                
                return ModelDiscoveryResult(
                    text_models=text_models,
                    embedding_models=[],  # OpenRouter doesn't provide embeddings
                    source="api"
                )
                
        except Exception as e:
            logger.error(f"OpenRouter model discovery failed: {e}")
            # Return some latest models as fallback
            return ModelDiscoveryResult(
                text_models=[
                    ModelInfo(
                        id="meta-llama/llama-4-maverick",
                        name="Llama 4 Maverick",
                        description="Latest Llama 4 MoE model with 400B total parameters, 17B active",
                        context_window=256000,
                        max_tokens=8192,
                        cost_per_token=0.00001,
                        capabilities=["text_generation", "chat", "multimodal"]
                    ),
                    ModelInfo(
                        id="meta-llama/llama-4-scout",
                        name="Llama 4 Scout",
                        description="Llama 4 MoE model with 109B total parameters, 17B active",
                        context_window=512000,
                        max_tokens=8192,
                        cost_per_token=0.000008,
                        capabilities=["text_generation", "chat", "multimodal"]
                    ),
                    ModelInfo(
                        id="anthropic/claude-4-sonnet",
                        name="Claude 4 Sonnet",
                        description="Latest Claude 4 Sonnet via OpenRouter",
                        context_window=200000,
                        max_tokens=64000,
                        cost_per_token=0.000003,
                        capabilities=["text_generation", "chat", "reasoning", "coding"]
                    ),
                    ModelInfo(
                        id="anthropic/claude-4-opus",
                        name="Claude 4 Opus",
                        description="World's best coding model via OpenRouter",
                        context_window=200000,
                        max_tokens=32000,
                        cost_per_token=0.000015,
                        capabilities=["text_generation", "chat", "reasoning", "coding", "extended_thinking"]
                    ),
                    ModelInfo(
                        id="openai/gpt-4.1",
                        name="GPT-4.1",
                        description="Latest OpenAI model with 1M token context via OpenRouter",
                        context_window=1000000,
                        max_tokens=8192,
                        cost_per_token=0.000005,
                        capabilities=["text_generation", "chat", "function_calling", "coding"]
                    ),
                    ModelInfo(
                        id="google/gemini-2.5-pro",
                        name="Gemini 2.5 Pro",
                        description="Google's most intelligent AI model via OpenRouter",
                        context_window=1000000,
                        max_tokens=8192,
                        cost_per_token=0.0000025,
                        capabilities=["text_generation", "chat", "reasoning", "multimodal"]
                    )
                ],
                embedding_models=[],
                source="static_fallback"
            )
    
    def _get_static_text_models(self) -> List[ModelInfo]:
        """Get static list of popular OpenRouter models"""
        return [
            ModelInfo(
                id="meta-llama/llama-4-maverick",
                name="Llama 4 Maverick",
                description="Latest Llama 4 MoE model with 400B total parameters, 17B active",
                context_window=256000,
                max_tokens=8192,
                cost_per_token=0.00001,
                capabilities=["text_generation", "chat", "multimodal"]
            ),
            ModelInfo(
                id="meta-llama/llama-4-scout",
                name="Llama 4 Scout",
                description="Llama 4 MoE model with 109B total parameters, 17B active",
                context_window=512000,
                max_tokens=8192,
                cost_per_token=0.000008,
                capabilities=["text_generation", "chat", "multimodal"]
            ),
            ModelInfo(
                id="openai/gpt-4.1",
                name="GPT-4.1 via OpenRouter",
                description="Latest OpenAI model with 1M token context",
                context_window=1000000,
                max_tokens=8192,
                cost_per_token=0.000005,
                capabilities=["text_generation", "chat", "function_calling", "coding"]
            ),
            ModelInfo(
                id="openai/o3",
                name="OpenAI o3 via OpenRouter",
                description="OpenAI's most powerful reasoning model",
                context_window=200000,
                max_tokens=8192,
                cost_per_token=0.00002,
                capabilities=["text_generation", "chat", "reasoning", "math", "coding"]
            ),
            ModelInfo(
                id="anthropic/claude-4-sonnet",
                name="Claude 4 Sonnet",
                description="Latest Claude 4 Sonnet via OpenRouter",
                context_window=200000,
                max_tokens=64000,
                cost_per_token=0.000003,
                capabilities=["text_generation", "chat", "reasoning", "coding"]
            ),
            ModelInfo(
                id="anthropic/claude-4-opus",
                name="Claude 4 Opus",
                description="World's best coding model via OpenRouter",
                context_window=200000,
                max_tokens=32000,
                cost_per_token=0.000015,
                capabilities=["text_generation", "chat", "reasoning", "coding", "extended_thinking"]
            ),
            ModelInfo(
                id="google/gemini-2.5-pro",
                name="Gemini 2.5 Pro",
                description="Google's most intelligent AI model",
                context_window=1000000,
                max_tokens=8192,
                cost_per_token=0.0000025,
                capabilities=["text_generation", "chat", "reasoning", "multimodal"]
            ),
            ModelInfo(
                id="google/gemini-2.5-flash",
                name="Gemini 2.5 Flash",
                description="Efficient workhorse model with improved reasoning",
                context_window=1000000,
                max_tokens=8192,
                cost_per_token=0.000001,
                capabilities=["text_generation", "chat", "reasoning", "multimodal"]
            )
        ]