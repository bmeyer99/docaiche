"""
LLM Provider Client - PRD-005 LLM-004
Main client class that instantiates correct provider based on configuration

Implements failover logic between primary/fallback providers, manages provider
selection and health monitoring as specified in PRD-005.
"""

import logging
from typing import Any, Dict, Optional, Type, TypeVar, List
from enum import Enum

from .base_provider import BaseLLMProvider, LLMProviderError
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .models import (
    EvaluationResult,
    EnrichmentStrategy,
    QualityAssessment,
    LLMProviderStatus,
    get_provider_status,
    LLMProviderUnavailableError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", EvaluationResult, EnrichmentStrategy, QualityAssessment)


class ProviderStatus(Enum):
    """Provider health status enumeration"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    RATE_LIMITED = "rate_limited"
    UNKNOWN = "unknown"


class LLMProviderClient:
    """
    Main LLM client implementing PRD-005 LLM-004 requirements.

    Manages multiple LLM providers with automatic failover logic, health monitoring,
    and provider selection based on configuration and availability.
    """

    def __init__(self, ai_config: Optional[Dict[str, Any]] = None, cache_manager=None):
        """
        Initialize LLM provider client with configuration.

        Args:
            ai_config: AI configuration from AIConfig (optional)
            cache_manager: Optional cache manager for response caching
        """
        self.config = ai_config or {}
        self.cache_manager = cache_manager

        # Provider configuration
        self.status: LLMProviderStatus = get_provider_status(self.config)
        self.primary_provider_name = getattr(self.status, "primary_provider", None)
        self.fallback_provider_name = getattr(self.status, "fallback_provider", None)
        self.enable_failover = self.config.get("enable_failover", True)

        # Provider instances
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.provider_status: Dict[str, ProviderStatus] = {}

        # Initialize providers only if enabled and available
        self._initialize_providers()

        # Store actual provider objects for patching/mocking
        self._primary_provider: Optional[BaseLLMProvider] = self.providers.get(
            self.primary_provider_name
        )
        self._fallback_provider: Optional[BaseLLMProvider] = self.providers.get(
            self.fallback_provider_name
        )

        # Health monitoring
        self._last_health_check = 0
        self._health_check_interval = 60  # seconds

    def _initialize_providers(self):
        """Initialize available LLM providers based on configuration."""
        # Ollama
        ollama_cfg = self.config.get("ollama") if self.config else None
        if (
            ollama_cfg
            and ollama_cfg.get("enabled", True)  # Default to enabled if not specified
            and ollama_cfg.get("endpoint")
            and ollama_cfg.get("model")
        ):
            try:
                self.providers["ollama"] = OllamaProvider(
                    ollama_cfg, self.cache_manager
                )
                self.provider_status["ollama"] = ProviderStatus.UNKNOWN
                logger.info("Ollama provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Ollama provider: {e}")
        # OpenAI
        openai_cfg = self.config.get("openai") if self.config else None
        if (
            openai_cfg
            and openai_cfg.get("enabled")
            and openai_cfg.get("api_key")
            and openai_cfg.get("model")
        ):
            try:
                self.providers["openai"] = OpenAIProvider(
                    openai_cfg, self.cache_manager
                )
                self.provider_status["openai"] = ProviderStatus.UNKNOWN
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI provider: {e}")

        if not self.providers:
            logger.warning("No LLM providers were successfully initialized")

    async def generate_structured(
        self, prompt: str, response_model: Type[T], **kwargs
    ) -> T:
        """
        Generate structured response with automatic failover.

        Implements LLM-007 failover logic: try primary provider first,
        then fallback to secondary provider if primary fails.

        Args:
            prompt: Formatted prompt text
            response_model: Expected Pydantic model type
            **kwargs: Additional provider-specific parameters

        Returns:
            Validated Pydantic model instance

        Raises:
            LLMProviderError: When all providers fail
            LLMProviderUnavailableError: When no providers are available
        """
        await self._maybe_check_health()

        providers_to_try = self._get_provider_order()

        if not providers_to_try:
            logger.warning("No LLM providers are available for structured generation")
            raise LLMProviderUnavailableError(
                "No LLM providers are configured or available"
            )

        last_error = None

        for provider_name in providers_to_try:
            provider = self.providers.get(provider_name)
            if not provider:
                continue

            # Skip unhealthy providers unless it's the last option
            if (
                self.provider_status.get(provider_name) == ProviderStatus.UNHEALTHY
                and provider_name != providers_to_try[-1]
            ):
                logger.debug(f"Skipping unhealthy provider: {provider_name}")
                continue

            try:
                logger.info(f"Attempting LLM generation with {provider_name}")

                # Make request with provider
                result = await provider.generate_structured(
                    prompt, response_model, **kwargs
                )

                # Mark provider as healthy on success
                self.provider_status[provider_name] = ProviderStatus.HEALTHY

                # Update _primary_provider and _fallback_provider object refs for patching/mocking
                if provider_name == self.primary_provider_name:
                    self._primary_provider = provider
                elif provider_name == self.fallback_provider_name:
                    self._fallback_provider = provider

                logger.info(f"LLM generation successful with {provider_name}")
                return result

            except LLMProviderUnavailableError as e:
                # Circuit breaker is open - mark as unhealthy
                self.provider_status[provider_name] = ProviderStatus.UNHEALTHY
                last_error = e
                logger.warning(f"Provider {provider_name} circuit breaker open: {e}")

                if not self.enable_failover:
                    raise

            except LLMProviderError as e:
                # Other provider errors - try to determine if it's rate limiting
                if "rate limit" in str(e).lower():
                    self.provider_status[provider_name] = ProviderStatus.RATE_LIMITED
                    logger.warning(f"Provider {provider_name} rate limited: {e}")
                else:
                    self.provider_status[provider_name] = ProviderStatus.UNHEALTHY
                    logger.warning(f"Provider {provider_name} failed: {e}")

                last_error = e

                if not self.enable_failover:
                    raise

            except Exception as e:
                # Unexpected errors
                self.provider_status[provider_name] = ProviderStatus.UNHEALTHY
                last_error = LLMProviderError(
                    f"Unexpected error from {provider_name}: {str(e)}"
                )
                logger.error(f"Unexpected error from {provider_name}: {e}")

                if not self.enable_failover:
                    raise last_error

        # All providers failed
        if last_error:
            raise last_error
        else:
            raise LLMProviderUnavailableError(
                "All LLM providers failed or are unavailable"
            )

    def _get_provider_order(self) -> List[str]:
        """
        Get ordered list of providers to try based on configuration and health.

        Returns:
            List of provider names in order of preference
        """
        providers_to_try = []
        if self.primary_provider_name and self.primary_provider_name in self.providers:
            providers_to_try.append(self.primary_provider_name)
        if (
            self.enable_failover
            and self.fallback_provider_name
            and self.fallback_provider_name in self.providers
            and self.fallback_provider_name != self.primary_provider_name
        ):
            providers_to_try.append(self.fallback_provider_name)
        return providers_to_try

    async def generate(self, prompt: str, **kwargs) -> str:
        """
        Simple text generation method for convenience.
        
        Args:
            prompt: Text prompt
            **kwargs: Additional provider parameters
            
        Returns:
            Generated text response
        """
        # Create a simple response model for text generation
        from pydantic import BaseModel, Field
        
        class TextResponse(BaseModel):
            text: str = Field(..., description="Generated text response")
        
        # Wrap prompt to request JSON response
        json_prompt = f"""{prompt}

Return your response as JSON in this format:
{{
    "text": "Your response here"
}}"""
        
        try:
            response = await self.generate_structured(json_prompt, TextResponse, **kwargs)
            return response.text
        except Exception as e:
            # Fallback: try to extract text from any response
            logger.warning(f"Structured generation failed, attempting direct generation: {e}")
            
            # Try direct generation with first available provider
            for provider_name, provider in self.providers.items():
                try:
                    raw_response = await provider._make_request(prompt, **kwargs)
                    return raw_response
                except Exception as provider_error:
                    logger.debug(f"Provider {provider_name} failed: {provider_error}")
                    continue
            
            raise LLMProviderError("Failed to generate response with any provider")
    
    async def _maybe_check_health(self):
        """Perform periodic health checks on providers."""
        import time

        current_time = time.time()

        if current_time - self._last_health_check > self._health_check_interval:
            await self._check_all_providers_health()
            self._last_health_check = current_time

    async def _check_all_providers_health(self):
        """Check health of all providers and update status."""
        for provider_name, provider in self.providers.items():
            try:
                health_result = await provider.health_check()

                if health_result.get("status") == "healthy":
                    self.provider_status[provider_name] = ProviderStatus.HEALTHY
                elif health_result.get("status") == "rate_limited":
                    self.provider_status[provider_name] = ProviderStatus.RATE_LIMITED
                else:
                    self.provider_status[provider_name] = ProviderStatus.UNHEALTHY

            except Exception as e:
                self.provider_status[provider_name] = ProviderStatus.UNHEALTHY
                logger.debug(f"Health check failed for {provider_name}: {e}")

    async def health_check(self) -> Dict[str, Any]:
        """
        Get comprehensive health status of all providers.

        Returns:
            Health status dictionary with provider details
        """
        # Force health check
        await self._check_all_providers_health()

        provider_health = {}
        for provider_name, provider in self.providers.items():
            try:
                health_result = await provider.health_check()
                provider_health[provider_name] = {
                    **health_result,
                    "status_enum": self.provider_status[provider_name].value,
                    "is_primary": provider_name == self.primary_provider_name,
                    "is_fallback": provider_name == self.fallback_provider_name,
                }
            except Exception as e:
                provider_health[provider_name] = {
                    "status": "error",
                    "error": str(e),
                    "status_enum": ProviderStatus.UNHEALTHY.value,
                    "is_primary": provider_name == self.primary_provider_name,
                    "is_fallback": provider_name == self.fallback_provider_name,
                }

        healthy_providers = [
            name
            for name, status in self.provider_status.items()
            if status == ProviderStatus.HEALTHY
        ]

        primary_health = provider_health.get(self.primary_provider_name, {})
        fallback_health = provider_health.get(self.fallback_provider_name, {})

        return {
            "overall_status": "healthy" if healthy_providers else "degraded",
            "providers": provider_health,
            "primary_provider": self.primary_provider_name,
            "fallback_provider": self.fallback_provider_name,
            "failover_enabled": self.enable_failover,
            "healthy_providers": healthy_providers,
            "provider_count": len(self.providers),
            "primary": primary_health,
            "fallback": fallback_health,
        }

    async def list_models(self, provider_name: Optional[str] = None) -> Dict[str, Any]:
        """
        List available models from specified provider or all providers.

        Args:
            provider_name: Specific provider name, or None for all

        Returns:
            Dictionary with model information
        """
        if provider_name:
            if provider_name not in self.providers:
                return {"error": f"Provider {provider_name} not found"}

            provider = self.providers[provider_name]
            return await provider.list_models()

        # Get models from all providers
        all_models = {}
        for name, provider in self.providers.items():
            try:
                models_info = await provider.list_models()
                all_models[name] = models_info
            except Exception as e:
                all_models[name] = {"error": str(e)}

        return all_models

    async def evaluate_search_result(
        self, query: str, results: list, context: str = ""
    ) -> Optional[EvaluationResult]:
        """
        Evaluate search results using the evaluation.prompt template.
        Args:
            query: User query string
            results: List of search result dicts
            context: Additional context string
        Returns:
            EvaluationResult model instance or None
        Raises:
            LLMProviderError: On provider or validation failure
            LLMProviderUnavailableError: When no providers are available
        """
        if not self.status.any_provider_available:
            logger.info("LLM evaluation unavailable: no providers enabled")
            raise LLMProviderUnavailableError(
                "No LLM providers are configured or available"
            )

        from .prompt_manager import get_prompt_manager, PromptTemplateError

        prompt_manager = get_prompt_manager()
        try:
            safe_query = self._sanitize_input(query)
            safe_results = self._sanitize_input(str(results))
            safe_context = self._sanitize_input(context)
            prompt = prompt_manager.format_template(
                "evaluation",
                query=safe_query,
                results=safe_results,
                context=safe_context,
            )
        except PromptTemplateError as e:
            logger.error(f"Prompt formatting error: {e}")
            raise LLMProviderError(f"Prompt formatting error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error formatting prompt: {e}")
            raise LLMProviderError("Unexpected error formatting prompt")

        try:
            return await self.generate_structured(prompt, EvaluationResult)
        except Exception as e:
            logger.error(f"LLM response parsing error: {e}")
            return None

    async def generate_enrichment_strategy(
        self,
        original_query: str,
        missing_aspects: list,
        current_results: str,
        domain: str,
    ) -> Optional[EnrichmentStrategy]:
        """
        Generate enrichment strategy using the strategy.prompt template.
        Args:
            original_query: The original user query
            missing_aspects: List of missing aspects
            current_results: Summary of current results
            domain: Domain string
        Returns:
            EnrichmentStrategy model instance or None
        Raises:
            LLMProviderError: On provider or validation failure
            LLMProviderUnavailableError: When no providers are available
        """
        if not self.status.any_provider_available:
            logger.info("LLM enrichment unavailable: no providers enabled")
            raise LLMProviderUnavailableError(
                "No LLM providers are configured or available"
            )

        from .prompt_manager import get_prompt_manager, PromptTemplateError

        prompt_manager = get_prompt_manager()
        try:
            safe_query = self._sanitize_input(original_query)
            safe_missing = self._sanitize_input(str(missing_aspects))
            safe_results = self._sanitize_input(current_results)
            safe_domain = self._sanitize_input(domain)
            prompt = prompt_manager.format_template(
                "strategy",
                original_query=safe_query,
                missing_aspects=safe_missing,
                current_results=safe_results,
                domain=safe_domain,
            )
        except PromptTemplateError as e:
            logger.error(f"Prompt formatting error: {e}")
            raise LLMProviderError(f"Prompt formatting error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error formatting prompt: {e}")
            raise LLMProviderError("Unexpected error formatting prompt")

        try:
            return await self.generate_structured(prompt, EnrichmentStrategy)
        except Exception as e:
            logger.error(f"LLM response parsing error: {e}")
            return None

    async def assess_content_quality(
        self, content: str, source_url: str, query_context: str, content_metadata: dict
    ) -> Optional[QualityAssessment]:
        """
        Assess content quality using the quality.prompt template.
        Args:
            content: Content string
            source_url: Source URL string
            query_context: Query context string
            content_metadata: Metadata dict
        Returns:
            QualityAssessment model instance or None
        Raises:
            LLMProviderError: On provider or validation failure
            LLMProviderUnavailableError: When no providers are available
        """
        if not self.status.any_provider_available:
            logger.info("LLM quality assessment unavailable: no providers enabled")
            raise LLMProviderUnavailableError(
                "No LLM providers are configured or available"
            )

        from .prompt_manager import get_prompt_manager, PromptTemplateError

        prompt_manager = get_prompt_manager()
        try:
            safe_content = self._sanitize_input(content)
            safe_url = self._sanitize_input(source_url)
            safe_context = self._sanitize_input(query_context)
            safe_metadata = self._sanitize_input(str(content_metadata))
            prompt = prompt_manager.format_template(
                "quality",
                content=safe_content,
                source_url=safe_url,
                query_context=safe_context,
                content_metadata=safe_metadata,
            )
        except PromptTemplateError as e:
            logger.error(f"Prompt formatting error: {e}")
            raise LLMProviderError(f"Prompt formatting error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error formatting prompt: {e}")
            raise LLMProviderError("Unexpected error formatting prompt")

        try:
            return await self.generate_structured(prompt, QualityAssessment)
        except Exception as e:
            logger.error(f"LLM response parsing error: {e}")
            return None

    def _sanitize_input(self, value: str) -> str:
        """
        Sanitize input to prevent prompt injection and unsafe content.
        Args:
            value: Input string
        Returns:
            Sanitized string
        """
        import re

        sanitized = re.sub(r"[{}]", "", value)
        sanitized = re.sub(r"[\x00-\x1f\x7f]", " ", sanitized)
        sanitized = sanitized.strip()
        if len(sanitized) > 4096:
            sanitized = sanitized[:4096]
        return sanitized

    async def close(self):
        """Close all provider sessions and cleanup resources."""
        for provider_name, provider in self.providers.items():
            try:
                await provider.close()
                logger.debug(f"Closed provider: {provider_name}")
            except Exception as e:
                logger.error(f"Error closing provider {provider_name}: {e}")

        logger.info("LLM provider client closed")


async def create_llm_client(
    ai_config: Optional[Dict[str, Any]] = None, cache_manager=None
) -> LLMProviderClient:
    """
    Factory function to create LLMProviderClient with configuration integration.

    Args:
        ai_config: AI configuration from AIConfig (optional)
        cache_manager: Optional cache manager

    Returns:
        Configured LLMProviderClient instance
    """
    client = LLMProviderClient(ai_config, cache_manager)

    # Perform initial health check
    try:
        await client._check_all_providers_health()
        logger.info("LLM client initialized and health checked")
    except Exception as e:
        logger.warning(f"Initial health check failed: {e}")

    return client
