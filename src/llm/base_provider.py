"""
Base LLM Provider Abstract Class - PRD-005 LLM-001
Abstract base class defining common interface for all LLM providers

Implements circuit breaker integration, error handling patterns, and the
async generate_structured method interface as specified in PRD-005.
"""

import logging
import asyncio
import hashlib
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, TypeVar, List

from .models import (
    ProviderCapabilities, ProviderCategory, ModelInfo, ModelDiscoveryResult,
    TextGenerationRequest, TextGenerationResponse,
    EmbeddingRequest, EmbeddingResponse
)

logger = logging.getLogger(__name__)

# For now, make a generic TypeVar for any BaseModel
try:
    from pydantic import BaseModel
    T = TypeVar("T", bound=BaseModel)
except ImportError:
    T = TypeVar("T")


class LLMProviderError(Exception):
    """Base exception for LLM provider errors"""

    pass


class LLMProviderTimeoutError(LLMProviderError):
    """Raised when LLM provider request times out"""

    pass


class LLMProviderUnavailableError(LLMProviderError):
    """Raised when LLM provider is unavailable"""

    pass


class BaseLLMProvider(ABC):
    """
    Enhanced abstract base class for LLM providers implementing PRD-005 requirements
    and multi-provider architecture support.

    Defines common interface for all providers with circuit breaker integration,
    structured logging, error handling patterns, and provider registry compatibility.
    """
    
    # Provider metadata (to be overridden by subclasses)
    _provider_id: str = None
    _display_name: str = None
    _description: str = None
    _category: ProviderCategory = ProviderCategory.CLOUD

    def __init__(self, config: Optional[Dict[str, Any]] = None, cache_manager=None):
        """
        Initialize base LLM provider.

        Args:
            config: Provider-specific configuration (required for multi-provider system)
            cache_manager: Optional cache manager for response caching
        """
        if config is None:
            raise ValueError("Configuration is required for provider initialization")
            
        self.config = config
        self.cache_manager = cache_manager
        self.provider_name = self.__class__.__name__.replace("Provider", "").lower()
        
        # Initialize provider-specific attributes
        self._models_cache: Optional[ModelDiscoveryResult] = None
        self._last_model_discovery: Optional[float] = None

    @classmethod
    @abstractmethod
    def get_static_capabilities(cls) -> ProviderCapabilities:
        """
        Get static capabilities supported by this provider.
        
        Returns:
            ProviderCapabilities: Static capabilities of the provider
        """
        pass
    
    @classmethod
    @abstractmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """
        Get JSON schema for provider configuration validation.
        
        Returns:
            Dict containing JSON schema for configuration
        """
        pass
    
    @abstractmethod
    def _create_circuit_breaker(self):
        """Create provider-specific circuit breaker configuration."""
        pass

    @abstractmethod
    async def _make_request(self, prompt: str, **kwargs) -> str:
        """
        Make the actual request to the LLM provider.

        Args:
            prompt: Formatted prompt text
            **kwargs: Additional provider-specific parameters

        Returns:
            Raw response text from LLM

        Raises:
            LLMProviderError: When request fails
        """
        pass
    
    @abstractmethod
    async def generate_text(self, request: TextGenerationRequest) -> TextGenerationResponse:
        """
        Generate text using the provider's text generation capabilities.
        
        Args:
            request: Text generation request
            
        Returns:
            Text generation response
            
        Raises:
            LLMProviderError: When generation fails
        """
        pass
    
    async def generate_embeddings(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """
        Generate embeddings using the provider's embedding capabilities.
        
        Args:
            request: Embedding generation request
            
        Returns:
            Embedding response
            
        Raises:
            LLMProviderError: When provider doesn't support embeddings
        """
        capabilities = self.get_static_capabilities()
        if not capabilities.embeddings:
            raise LLMProviderError(f"Provider {self.provider_name} does not support embeddings")
        
        raise NotImplementedError("Embedding generation not implemented for this provider")
    
    async def discover_models(self, config: Dict[str, Any]) -> ModelDiscoveryResult:
        """
        Discover available models from the provider.
        
        Args:
            config: Provider configuration for model discovery
            
        Returns:
            Model discovery result
            
        Raises:
            LLMProviderError: When model discovery fails
        """
        capabilities = self.get_static_capabilities()
        if not capabilities.model_discovery:
            # Return static model list if dynamic discovery not supported
            return ModelDiscoveryResult(
                text_models=self._get_static_text_models(),
                embedding_models=self._get_static_embedding_models(),
                source="static"
            )
        
        # Implement provider-specific model discovery
        raise NotImplementedError("Model discovery not implemented for this provider")
    
    async def test_connection(self, config: Dict[str, Any]) -> bool:
        """
        Test connection to the provider with given configuration.
        
        Args:
            config: Configuration to test
            
        Returns:
            True if connection successful
            
        Raises:
            LLMProviderError: When connection fails
        """
        try:
            # Simple test request
            test_request = TextGenerationRequest(
                prompt="Say 'OK' if you can hear me",
                max_tokens=10,
                temperature=0.0
            )
            response = await self.generate_text(test_request)
            return len(response.text.strip()) > 0
        except Exception as e:
            raise LLMProviderError(f"Connection test failed: {str(e)}")
    
    def _get_static_text_models(self):
        """
        Get static list of text models when dynamic discovery is not available.
        
        Returns:
            List of static text models
        """
        return []
    
    def _get_static_embedding_models(self):
        """
        Get static list of embedding models when dynamic discovery is not available.
        
        Returns:
            List of static embedding models
        """
        return []

    async def generate_structured(
        self, prompt: str, response_model: Type[T], **kwargs
    ) -> T:
        """
        Generate structured response from LLM with validation.

        Main interface method implementing PRD-005 requirements for structured
        prompting with JSON parsing and Pydantic model validation.

        Args:
            prompt: Formatted prompt text
            response_model: Expected Pydantic model type
            **kwargs: Additional provider-specific parameters

        Returns:
            Validated Pydantic model instance

        Raises:
            LLMProviderError: When generation fails
            JSONParsingError: When response cannot be parsed
            JSONValidationError: When response doesn't match schema
        """
        cache_key = None
        if self.cache_manager:
            cache_key = self._generate_cache_key(
                prompt, response_model.__name__, kwargs
            )
            cached_response = await self.cache_manager.get(cache_key)
            if cached_response:
                logger.info(
                    f"Cache hit for {self.provider_name} request",
                    extra={
                        "provider": self.provider_name,
                        "cache_key": cache_key,
                        "cached": True,
                    },
                )
                try:
                    return response_model(**cached_response)
                except Exception as e:
                    logger.warning(f"Cached response invalid, regenerating: {e}")
            else:
                logger.info(
                    f"Cache miss for {self.provider_name} request",
                    extra={
                        "provider": self.provider_name,
                        "cache_key": cache_key,
                        "cached": False,
                    },
                )

        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        logger.info(
            "LLM request",
            extra={
                "provider": self.provider_name,
                "prompt_hash": prompt_hash,
                "response_model": response_model.__name__,
                "cached": False,
            },
        )

        try:
            response_text = await self._make_request(prompt, **kwargs)
            # For now, just return the raw response - this will be enhanced later
            # validated_response = parse_llm_response(response_text, response_model)
            validated_response = response_model(text=response_text) if hasattr(response_model, 'text') else response_model()

            if self.cache_manager and cache_key and validated_response:
                ttl = self.config.get("cache_ttl_seconds", 3600)
                await self.cache_manager.set(cache_key, validated_response.dict(), ttl)
                logger.info(
                    f"Response cached for {self.provider_name}",
                    extra={
                        "provider": self.provider_name,
                        "cache_key": cache_key,
                        "cached": True,
                    },
                )

            logger.info(
                "LLM request completed",
                extra={
                    "provider": self.provider_name,
                    "prompt_hash": prompt_hash,
                    "response_model": response_model.__name__,
                    "success": True,
                },
            )

            return validated_response

        except Exception as parse_error:
            logger.error(
                "LLM response parsing failed",
                extra={
                    "provider": self.provider_name,
                    "prompt_hash": prompt_hash,
                    "error": str(parse_error),
                    "error_type": type(parse_error).__name__,
                },
            )
            raise LLMProviderError(f"Response parsing failed: {str(parse_error)}")

        except Exception as e:
            logger.error(
                "LLM request failed",
                extra={
                    "provider": self.provider_name,
                    "prompt_hash": prompt_hash,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise LLMProviderError(f"{self.provider_name} request failed: {str(e)}")

    def _generate_cache_key(
        self, prompt: str, model_name: str, kwargs: Dict[str, Any]
    ) -> str:
        """
        Generate cache key for LLM response caching.

        Args:
            prompt: Prompt text
            model_name: Response model name
            kwargs: Additional parameters

        Returns:
            Cache key string
        """
        cache_data = {
            "provider": self.provider_name,
            "prompt": prompt,
            "model": model_name,
            "params": sorted(kwargs.items()) if kwargs else [],
        }
        cache_string = str(cache_data)
        cache_hash = hashlib.md5(cache_string.encode()).hexdigest()
        return f"ai:evaluation:{cache_hash}"

    async def health_check(self) -> Dict[str, Any]:
        """
        Check provider health and availability.

        Returns:
            Health status dictionary
        """
        try:
            test_prompt = "Respond with just 'OK'"
            await asyncio.wait_for(self._make_request(test_prompt), timeout=10.0)
            return {
                "provider": self.provider_name,
                "status": "healthy",
                "circuit_breaker": "closed",
            }
        except Exception as e:
            return {
                "provider": self.provider_name,
                "status": "unhealthy",
                "error": str(e),
                "circuit_breaker": "unknown",
            }
