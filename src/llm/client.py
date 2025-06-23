"""
LLM Provider Client - PRD-005 LLM-004
Main client class that instantiates correct provider based on configuration

Implements failover logic between primary/fallback providers, manages provider
selection and health monitoring as specified in PRD-005.
"""

import logging
import asyncio
from typing import Any, Dict, Optional, Type, TypeVar, Union
from enum import Enum

from .base_provider import BaseLLMProvider, LLMProviderError, LLMProviderUnavailableError
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider
from .models import EvaluationResult, EnrichmentStrategy, QualityAssessment

logger = logging.getLogger(__name__)

T = TypeVar('T', EvaluationResult, EnrichmentStrategy, QualityAssessment)


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
    
    def __init__(self, ai_config: Dict[str, Any], cache_manager=None):
        """
        Initialize LLM provider client with configuration.
        
        Args:
            ai_config: AI configuration from AIConfig
            cache_manager: Optional cache manager for response caching
        """
        self.config = ai_config
        self.cache_manager = cache_manager
        
        # Provider configuration
        self.primary_provider_name = ai_config.get('primary_provider', 'ollama')
        self.fallback_provider_name = ai_config.get('fallback_provider', 'openai')
        self.enable_failover = ai_config.get('enable_failover', True)
        
        # Provider instances
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.provider_status: Dict[str, ProviderStatus] = {}
        
        # Initialize providers
        self._initialize_providers()
        
        # Health monitoring
        self._last_health_check = 0
        self._health_check_interval = 60  # seconds
    
    def _initialize_providers(self):
        """Initialize available LLM providers based on configuration."""
        # Initialize Ollama provider
        if 'ollama' in self.config:
            try:
                self.providers['ollama'] = OllamaProvider(
                    self.config['ollama'], 
                    self.cache_manager
                )
                self.provider_status['ollama'] = ProviderStatus.UNKNOWN
                logger.info("Ollama provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Ollama provider: {e}")
        
        # Initialize OpenAI provider
        if 'openai' in self.config:
            try:
                self.providers['openai'] = OpenAIProvider(
                    self.config['openai'], 
                    self.cache_manager
                )
                self.provider_status['openai'] = ProviderStatus.UNKNOWN
                logger.info("OpenAI provider initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI provider: {e}")
        
        if not self.providers:
            logger.warning("No LLM providers were successfully initialized")
    
    async def generate_structured(
        self, 
        prompt: str, 
        response_model: Type[T], 
        **kwargs
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
        """
        # Periodic health check
        await self._maybe_check_health()
        
        # Determine provider order
        providers_to_try = self._get_provider_order()
        
        if not providers_to_try:
            raise LLMProviderError("No LLM providers are available")
        
        last_error = None
        
        for provider_name in providers_to_try:
            provider = self.providers.get(provider_name)
            if not provider:
                continue
            
            # Skip unhealthy providers unless it's the last option
            if (self.provider_status.get(provider_name) == ProviderStatus.UNHEALTHY 
                and provider_name != providers_to_try[-1]):
                logger.debug(f"Skipping unhealthy provider: {provider_name}")
                continue
            
            try:
                logger.info(f"Attempting LLM generation with {provider_name}")
                
                # Make request with provider
                result = await provider.generate_structured(prompt, response_model, **kwargs)
                
                # Mark provider as healthy on success
                self.provider_status[provider_name] = ProviderStatus.HEALTHY
                
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
                last_error = LLMProviderError(f"Unexpected error from {provider_name}: {str(e)}")
                logger.error(f"Unexpected error from {provider_name}: {e}")
                
                if not self.enable_failover:
                    raise last_error
        
        # All providers failed
        if last_error:
            raise last_error
        else:
            raise LLMProviderError("All LLM providers failed or are unavailable")
    
    def _get_provider_order(self) -> list:
        """
        Get ordered list of providers to try based on configuration and health.
        
        Returns:
            List of provider names in order of preference
        """
        providers_to_try = []
        
        # Always try primary provider first if available
        if self.primary_provider_name in self.providers:
            providers_to_try.append(self.primary_provider_name)
        
        # Add fallback provider if failover is enabled and it's different from primary
        if (self.enable_failover 
            and self.fallback_provider_name 
            and self.fallback_provider_name in self.providers
            and self.fallback_provider_name != self.primary_provider_name):
            providers_to_try.append(self.fallback_provider_name)
        
        return providers_to_try
    
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
                
                if health_result.get('status') == 'healthy':
                    self.provider_status[provider_name] = ProviderStatus.HEALTHY
                elif health_result.get('status') == 'rate_limited':
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
                    'status_enum': self.provider_status[provider_name].value,
                    'is_primary': provider_name == self.primary_provider_name,
                    'is_fallback': provider_name == self.fallback_provider_name
                }
            except Exception as e:
                provider_health[provider_name] = {
                    'status': 'error',
                    'error': str(e),
                    'status_enum': ProviderStatus.UNHEALTHY.value,
                    'is_primary': provider_name == self.primary_provider_name,
                    'is_fallback': provider_name == self.fallback_provider_name
                }
        
        # Overall system health
        healthy_providers = [
            name for name, status in self.provider_status.items() 
            if status == ProviderStatus.HEALTHY
        ]
        
        return {
            'overall_status': 'healthy' if healthy_providers else 'degraded',
            'providers': provider_health,
            'primary_provider': self.primary_provider_name,
            'fallback_provider': self.fallback_provider_name,
            'failover_enabled': self.enable_failover,
            'healthy_providers': healthy_providers,
            'provider_count': len(self.providers)
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
                return {'error': f'Provider {provider_name} not found'}
            
            provider = self.providers[provider_name]
            return await provider.list_models()
        
        # Get models from all providers
        all_models = {}
        for name, provider in self.providers.items():
            try:
                models_info = await provider.list_models()
                all_models[name] = models_info
            except Exception as e:
                all_models[name] = {'error': str(e)}
        
        return all_models
    
    async def close(self):
        """Close all provider sessions and cleanup resources."""
        for provider_name, provider in self.providers.items():
            try:
                await provider.close()
                logger.debug(f"Closed provider: {provider_name}")
            except Exception as e:
                logger.error(f"Error closing provider {provider_name}: {e}")
        
        logger.info("LLM provider client closed")


async def create_llm_client(ai_config: Dict[str, Any], cache_manager=None) -> LLMProviderClient:
    """
    Factory function to create LLMProviderClient with configuration integration.
    
    Args:
        ai_config: AI configuration from AIConfig
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