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
from typing import Any, Dict, Optional, Type, TypeVar

from .models import EvaluationResult, EnrichmentStrategy, QualityAssessment
from .json_parser import parse_llm_response, JSONParsingError, JSONValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", EvaluationResult, EnrichmentStrategy, QualityAssessment)


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
    Abstract base class for LLM providers implementing PRD-005 requirements.

    Defines common interface for Ollama and OpenAI providers with circuit breaker
    integration, structured logging, and error handling patterns.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, cache_manager=None):
        """
        Initialize base LLM provider.

        Args:
            config: Provider-specific configuration (optional)
            cache_manager: Optional cache manager for response caching
        """
        self.config = config or {}
        self.cache_manager = cache_manager
        self.provider_name = self.__class__.__name__.replace("Provider", "").lower()

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
            validated_response = parse_llm_response(response_text, response_model)

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

        except (JSONParsingError, JSONValidationError) as e:
            logger.error(
                "LLM response parsing failed",
                extra={
                    "provider": self.provider_name,
                    "prompt_hash": prompt_hash,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

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
