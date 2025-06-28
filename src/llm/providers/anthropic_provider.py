"""
Anthropic Claude Provider - Phase 2.2 Implementation
Access to Claude models with advanced reasoning capabilities
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


@register_provider("anthropic", ProviderCategory.CLOUD)
class AnthropicProvider(BaseLLMProvider):
    """
    Anthropic Claude provider implementation for advanced reasoning and analysis.
    """
    
    _provider_id = "anthropic"
    _display_name = "Anthropic Claude"
    _description = "Claude models for advanced reasoning and analysis"
    _category = ProviderCategory.CLOUD

    def __init__(self, config: Dict[str, Any], cache_manager=None):
        super().__init__(config, cache_manager)
        
        self.api_key = config.get("api_key")
        self.base_url = config.get("base_url", "https://api.anthropic.com")
        self.default_model = config.get("model", "claude-4-sonnet-20250515")
        self.timeout = config.get("timeout_seconds", 60)
        self.api_version = config.get("api_version", "2023-06-01")
        
        if not self.api_key:
            raise ValueError("Anthropic API key is required")
    
    @classmethod
    def get_static_capabilities(cls) -> ProviderCapabilities:
        """Anthropic supports text generation with advanced reasoning"""
        return ProviderCapabilities(
            text_generation=True,
            embeddings=False,  # Anthropic doesn't provide embedding models
            streaming=True,
            function_calling=True,  # Claude supports function calling
            local=False,
            model_discovery=False  # Static model list
        )
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """JSON schema for Anthropic configuration"""
        return {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "Anthropic API key",
                    "minLength": 10
                },
                "base_url": {
                    "type": "string",
                    "description": "Anthropic API base URL",
                    "default": "https://api.anthropic.com"
                },
                "model": {
                    "type": "string",
                    "description": "Default Claude model to use",
                    "default": "claude-4-sonnet-20250515",
                    "enum": [
                        "claude-4-sonnet-20250515",
                        "claude-4-opus-20250515",
                        "claude-3-5-sonnet-20241022",
                        "claude-3-sonnet-20240229",
                        "claude-3-opus-20240229",
                        "claude-3-haiku-20240307"
                    ]
                },
                "api_version": {
                    "type": "string",
                    "description": "API version to use",
                    "default": "2023-06-01"
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
        """Create Anthropic-specific circuit breaker"""
        # TODO: Implement circuit breaker logic
        pass
    
    async def _make_request(self, prompt: str, **kwargs) -> str:
        """Make request to Anthropic API"""
        headers = {
            "x-api-key": self.api_key,
            "content-type": "application/json",
            "anthropic-version": self.api_version
        }
        
        model = kwargs.get("model", self.default_model)
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 4096)
        
        # Claude uses a different message format
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/messages",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_msg = f"Anthropic API error: {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail.get('error', {}).get('message', 'Unknown error')}"
                    except:
                        error_msg += f" - {response.text}"
                    raise LLMProviderError(error_msg)
                
                result = response.json()
                
                if "content" not in result or not result["content"]:
                    raise LLMProviderError("No content returned from Anthropic")
                
                # Claude returns content as an array of content blocks
                content = result["content"]
                if isinstance(content, list) and len(content) > 0:
                    return content[0].get("text", "")
                else:
                    return str(content)
                
        except httpx.TimeoutException:
            raise LLMProviderError(f"Anthropic request timed out after {self.timeout}s")
        except httpx.RequestError as e:
            raise LLMProviderError(f"Anthropic request failed: {str(e)}")
        except Exception as e:
            raise LLMProviderError(f"Anthropic provider error: {str(e)}")
    
    async def generate_text(self, request: TextGenerationRequest) -> TextGenerationResponse:
        """Generate text using Anthropic Claude"""
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
                provider="anthropic",
                finish_reason="stop"
            )
            
        except Exception as e:
            logger.error(f"Anthropic text generation failed: {e}")
            raise LLMProviderError(f"Text generation failed: {str(e)}")
    
    async def generate_embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Anthropic doesn't support embeddings"""
        raise LLMProviderError("Anthropic does not support embedding generation")
    
    async def discover_models(self, config: Dict[str, Any]) -> ModelDiscoveryResult:
        """Return static list of Claude models"""
        return ModelDiscoveryResult(
            text_models=self._get_static_text_models(),
            embedding_models=[],
            source="static"
        )
    
    def _get_static_text_models(self) -> List[ModelInfo]:
        """Get static list of Claude models"""
        return [
            ModelInfo(
                id="claude-4-sonnet-20250515",
                name="Claude 4 Sonnet",
                description="Latest Claude model with superior coding and reasoning, 64K output tokens",
                context_window=200000,
                max_tokens=64000,
                cost_per_token=0.000003,
                capabilities=["text_generation", "chat", "function_calling", "reasoning", "coding", "extended_thinking"]
            ),
            ModelInfo(
                id="claude-4-opus-20250515",
                name="Claude 4 Opus",
                description="World's best coding model, leading on SWE-bench (72.5%), 32K output tokens",
                context_window=200000,
                max_tokens=32000,
                cost_per_token=0.000015,
                capabilities=["text_generation", "chat", "function_calling", "reasoning", "coding", "extended_thinking", "tools"]
            ),
            ModelInfo(
                id="claude-3-5-sonnet-20241022",
                name="Claude 3.5 Sonnet",
                description="Previous generation high-performance model for complex reasoning",
                context_window=200000,
                max_tokens=4096,
                cost_per_token=0.000003,
                capabilities=["text_generation", "chat", "function_calling", "reasoning"]
            ),
            ModelInfo(
                id="claude-3-opus-20240229",
                name="Claude 3 Opus",
                description="Previous generation most powerful model for complex tasks",
                context_window=200000,
                max_tokens=4096,
                cost_per_token=0.000015,
                capabilities=["text_generation", "chat", "function_calling", "reasoning"]
            ),
            ModelInfo(
                id="claude-3-sonnet-20240229",
                name="Claude 3 Sonnet",
                description="Balanced performance and speed for most tasks",
                context_window=200000,
                max_tokens=4096,
                cost_per_token=0.000003,
                capabilities=["text_generation", "chat", "function_calling", "reasoning"]
            ),
            ModelInfo(
                id="claude-3-haiku-20240307",
                name="Claude 3 Haiku",
                description="Fast and efficient model for simple tasks",
                context_window=200000,
                max_tokens=4096,
                cost_per_token=0.00000025,
                capabilities=["text_generation", "chat", "function_calling"]
            )
        ]