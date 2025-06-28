"""
LiteLLM Provider - Phase 2.3 Implementation
Universal proxy for 100+ LLM APIs with unified interface
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


@register_provider("litellm", ProviderCategory.GATEWAY)
class LiteLLMProvider(BaseLLMProvider):
    """
    LiteLLM provider implementation providing universal access to 100+ LLM APIs
    through a unified OpenAI-compatible interface.
    """
    
    _provider_id = "litellm"
    _display_name = "LiteLLM"
    _description = "Universal proxy for 100+ LLM APIs with unified interface"
    _category = ProviderCategory.GATEWAY

    def __init__(self, config: Dict[str, Any], cache_manager=None):
        super().__init__(config, cache_manager)
        
        self.api_key = config.get("api_key", "")  # Optional for LiteLLM proxy
        self.base_url = config.get("base_url", "http://localhost:4000")
        self.default_model = config.get("model", "gpt-3.5-turbo")
        self.timeout = config.get("timeout_seconds", 60)
        
        # LiteLLM supports many providers through model prefixes
        self.supported_providers = [
            "openai", "anthropic", "cohere", "replicate", "bedrock", "vertex_ai",
            "azure", "palm", "together_ai", "openrouter", "huggingface", "ollama",
            "mistral", "groq", "deepinfra", "perplexity", "fireworks_ai", "anyscale"
        ]
    
    @classmethod
    def get_static_capabilities(cls) -> ProviderCapabilities:
        """LiteLLM supports comprehensive capabilities as a universal proxy"""
        return ProviderCapabilities(
            text_generation=True,
            embeddings=True,
            streaming=True,
            function_calling=True,
            local=False,  # Proxy service
            model_discovery=True
        )
    
    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """JSON schema for LiteLLM configuration"""
        return {
            "type": "object",
            "properties": {
                "api_key": {
                    "type": "string",
                    "description": "Optional API key for LiteLLM proxy",
                    "default": ""
                },
                "base_url": {
                    "type": "string",
                    "description": "LiteLLM proxy base URL",
                    "default": "http://localhost:4000"
                },
                "model": {
                    "type": "string",
                    "description": "Default model to use",
                    "default": "gpt-3.5-turbo"
                },
                "timeout_seconds": {
                    "type": "integer",
                    "description": "Request timeout in seconds",
                    "minimum": 10,
                    "maximum": 300,
                    "default": 60
                }
            },
            "required": ["base_url"],
            "additionalProperties": False
        }
    
    def _create_circuit_breaker(self):
        """Create LiteLLM-specific circuit breaker"""
        # TODO: Implement circuit breaker logic
        pass
    
    async def _make_request(self, prompt: str, **kwargs) -> str:
        """Make request to LiteLLM proxy using OpenAI-compatible API"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
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
                    f"{self.base_url}/v1/chat/completions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    error_msg = f"LiteLLM API error: {response.status_code}"
                    try:
                        error_detail = response.json()
                        error_msg += f" - {error_detail.get('error', {}).get('message', 'Unknown error')}"
                    except:
                        error_msg += f" - {response.text}"
                    raise LLMProviderError(error_msg)
                
                result = response.json()
                
                if "choices" not in result or not result["choices"]:
                    raise LLMProviderError("No response choices returned from LiteLLM")
                
                return result["choices"][0]["message"]["content"]
                
        except httpx.TimeoutException:
            raise LLMProviderError(f"LiteLLM request timed out after {self.timeout}s")
        except httpx.RequestError as e:
            raise LLMProviderError(f"LiteLLM request failed: {str(e)}")
        except Exception as e:
            raise LLMProviderError(f"LiteLLM provider error: {str(e)}")
    
    async def generate_text(self, request: TextGenerationRequest) -> TextGenerationResponse:
        """Generate text using LiteLLM proxy"""
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
                provider="litellm",
                finish_reason="stop"
            )
            
        except Exception as e:
            logger.error(f"LiteLLM text generation failed: {e}")
            raise LLMProviderError(f"Text generation failed: {str(e)}")
    
    async def generate_embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings using LiteLLM proxy"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": request.model,
            "input": request.text
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/embeddings",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code != 200:
                    raise LLMProviderError(f"LiteLLM embeddings error: {response.status_code}")
                
                result = response.json()
                
                if "data" not in result or not result["data"]:
                    raise LLMProviderError("No embedding data returned from LiteLLM")
                
                return EmbeddingResponse(
                    embeddings=[result["data"][0]["embedding"]],
                    model=request.model,
                    provider="litellm"
                )
                
        except Exception as e:
            logger.error(f"LiteLLM embedding generation failed: {e}")
            raise LLMProviderError(f"Embedding generation failed: {str(e)}")
    
    async def discover_models(self, config: Dict[str, Any]) -> ModelDiscoveryResult:
        """Discover available models from LiteLLM proxy"""
        headers = {
            "Content-Type": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.base_url}/v1/models",
                    headers=headers
                )
                
                if response.status_code != 200:
                    raise LLMProviderError(f"Model discovery failed: {response.status_code}")
                
                models_data = response.json()
                text_models = []
                embedding_models = []
                
                for model in models_data.get("data", []):
                    model_id = model["id"]
                    
                    # Determine if it's an embedding model
                    is_embedding = any(emb_keyword in model_id.lower() for emb_keyword in [
                        "embedding", "embed", "ada", "text-embedding"
                    ])
                    
                    model_info = ModelInfo(
                        id=model_id,
                        name=model.get("object", model_id),
                        description=f"Model via LiteLLM proxy: {model_id}",
                        context_window=model.get("context_window", 4096),
                        max_tokens=model.get("max_tokens", 4096),
                        cost_per_token=0.0,  # Varies by underlying provider
                        capabilities=["embeddings"] if is_embedding else ["text_generation", "chat"],
                        provider_specific=model
                    )
                    
                    if is_embedding:
                        embedding_models.append(model_info)
                    else:
                        text_models.append(model_info)
                
                logger.info(f"Discovered {len(text_models)} text models and {len(embedding_models)} embedding models from LiteLLM")
                
                return ModelDiscoveryResult(
                    text_models=text_models,
                    embedding_models=embedding_models,
                    source="api"
                )
                
        except Exception as e:
            logger.error(f"LiteLLM model discovery failed: {e}")
            # Return comprehensive static model list as fallback
            return ModelDiscoveryResult(
                text_models=self._get_static_text_models(),
                embedding_models=self._get_static_embedding_models(),
                source="static_fallback"
            )
    
    def _get_static_text_models(self) -> List[ModelInfo]:
        """Get static list of popular models available through LiteLLM"""
        return [
            # OpenAI models
            ModelInfo(
                id="gpt-4",
                name="GPT-4 via LiteLLM",
                description="OpenAI GPT-4 through LiteLLM proxy",
                context_window=8192,
                max_tokens=4096,
                cost_per_token=0.00003,
                capabilities=["text_generation", "chat", "function_calling"]
            ),
            ModelInfo(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo via LiteLLM",
                description="OpenAI GPT-3.5 Turbo through LiteLLM proxy",
                context_window=16384,
                max_tokens=4096,
                cost_per_token=0.000002,
                capabilities=["text_generation", "chat", "function_calling"]
            ),
            # Anthropic models
            ModelInfo(
                id="claude-3-sonnet-20240229",
                name="Claude 3 Sonnet via LiteLLM",
                description="Anthropic Claude 3 Sonnet through LiteLLM proxy",
                context_window=200000,
                max_tokens=4096,
                cost_per_token=0.000003,
                capabilities=["text_generation", "chat", "reasoning"]
            ),
            # Cohere models
            ModelInfo(
                id="command-r-plus",
                name="Cohere Command R+ via LiteLLM",
                description="Cohere Command R+ through LiteLLM proxy",
                context_window=128000,
                max_tokens=4096,
                cost_per_token=0.000003,
                capabilities=["text_generation", "chat", "reasoning"]
            ),
            # Google models
            ModelInfo(
                id="gemini-pro",
                name="Gemini Pro via LiteLLM",
                description="Google Gemini Pro through LiteLLM proxy",
                context_window=32768,
                max_tokens=8192,
                cost_per_token=0.0000005,
                capabilities=["text_generation", "chat", "multimodal"]
            ),
            # Mistral models
            ModelInfo(
                id="mistral-large-latest",
                name="Mistral Large via LiteLLM",
                description="Mistral Large through LiteLLM proxy",
                context_window=32768,
                max_tokens=8192,
                cost_per_token=0.000008,
                capabilities=["text_generation", "chat", "function_calling"]
            ),
            # Together AI models
            ModelInfo(
                id="meta-llama/Llama-2-70b-chat-hf",
                name="Llama 2 70B Chat via LiteLLM",
                description="Meta Llama 2 70B Chat through LiteLLM proxy",
                context_window=4096,
                max_tokens=4096,
                cost_per_token=0.0000009,
                capabilities=["text_generation", "chat"]
            ),
            # Groq models
            ModelInfo(
                id="llama3-70b-8192",
                name="Llama 3 70B via Groq/LiteLLM",
                description="Meta Llama 3 70B through Groq via LiteLLM proxy",
                context_window=8192,
                max_tokens=8192,
                cost_per_token=0.00000081,
                capabilities=["text_generation", "chat"]
            )
        ]
    
    def _get_static_embedding_models(self) -> List[ModelInfo]:
        """Get static list of embedding models available through LiteLLM"""
        return [
            ModelInfo(
                id="text-embedding-ada-002",
                name="OpenAI Ada 002 via LiteLLM",
                description="OpenAI text-embedding-ada-002 through LiteLLM proxy",
                context_window=8191,
                max_tokens=8191,
                cost_per_token=0.0000001,
                capabilities=["embeddings"]
            ),
            ModelInfo(
                id="text-embedding-3-small",
                name="OpenAI Embedding 3 Small via LiteLLM",
                description="OpenAI text-embedding-3-small through LiteLLM proxy",
                context_window=8191,
                max_tokens=8191,
                cost_per_token=0.00000002,
                capabilities=["embeddings"]
            ),
            ModelInfo(
                id="embed-english-v3.0",
                name="Cohere Embed English via LiteLLM",
                description="Cohere embed-english-v3.0 through LiteLLM proxy",
                context_window=512,
                max_tokens=512,
                cost_per_token=0.0000001,
                capabilities=["embeddings"]
            )
        ]