"""
Provider Registry for Managing Search Providers
================================================

Central registry for registering, managing, and selecting
external search providers with priority and health awareness.
"""

from typing import Dict, List, Optional, Type, Any
import asyncio
import logging
from enum import Enum

from .base import SearchProvider
from .models import (
    ProviderType,
    ProviderCapabilities,
    HealthStatus,
    SearchOptions,
    SearchResults,
    ProviderConfig
)

logger = logging.getLogger(__name__)


class SelectionStrategy(str, Enum):
    """Provider selection strategies."""
    PRIORITY = "priority"  # Use priority order
    ROUND_ROBIN = "round_robin"  # Rotate through providers
    LEAST_LOADED = "least_loaded"  # Use provider with lowest load
    FASTEST = "fastest"  # Use provider with best latency
    RANDOM = "random"  # Random selection


class ProviderRegistry:
    """
    Central registry for managing multiple search providers.
    
    Handles provider registration, health-based filtering,
    selection algorithms, and failover chains.
    """
    
    def __init__(self):
        """Initialize empty registry."""
        self._providers: Dict[str, SearchProvider] = {}
        self._provider_classes: Dict[ProviderType, Type[SearchProvider]] = {}
        self._provider_order: List[str] = []
        self._round_robin_index = 0
        self._selection_strategy = SelectionStrategy.PRIORITY
        
        logger.info("ProviderRegistry initialized")
    
    def register_provider_class(
        self,
        provider_type: ProviderType,
        provider_class: Type[SearchProvider]
    ) -> None:
        """
        Register a provider class for dynamic instantiation.
        
        Args:
            provider_type: Type of provider
            provider_class: Provider class to register
        """
        self._provider_classes[provider_type] = provider_class
        logger.info(f"Registered provider class: {provider_type.value}")
    
    async def add_provider(
        self,
        provider_id: str,
        provider: SearchProvider,
        validate: bool = True
    ) -> None:
        """
        Add a provider instance to the registry.
        
        Args:
            provider_id: Unique identifier for provider
            provider: Provider instance
            validate: Whether to validate configuration
            
        Raises:
            ValueError: If provider_id already exists
            ConfigurationError: If validation fails
        """
        if provider_id in self._providers:
            raise ValueError(f"Provider {provider_id} already registered")
        
        if validate:
            is_valid = await provider.validate_config()
            if not is_valid:
                from ..core.exceptions import ConfigurationError
                raise ConfigurationError(
                    config_section="provider",
                    issue=f"Invalid configuration for {provider_id}",
                    current_value=provider.config,
                    expected_value="Valid API key and settings"
                )
        
        self._providers[provider_id] = provider
        self._update_provider_order()
        
        logger.info(f"Added provider: {provider_id}")
    
    async def remove_provider(self, provider_id: str) -> None:
        """
        Remove a provider from the registry.
        
        Args:
            provider_id: Provider to remove
        """
        if provider_id in self._providers:
            del self._providers[provider_id]
            self._update_provider_order()
            logger.info(f"Removed provider: {provider_id}")
    
    def get_provider(self, provider_id: str) -> Optional[SearchProvider]:
        """
        Get a specific provider by ID.
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Provider instance or None
        """
        return self._providers.get(provider_id)
    
    def list_providers(
        self,
        active_only: bool = True,
        healthy_only: bool = False
    ) -> List[str]:
        """
        List registered providers.
        
        Args:
            active_only: Only include enabled providers
            healthy_only: Only include healthy providers
            
        Returns:
            List of provider IDs
        """
        providers = []
        
        for provider_id, provider in self._providers.items():
            # Check if enabled
            if active_only and not provider.config.enabled:
                continue
            
            # Check health
            if healthy_only:
                health = provider.get_health_status()
                if not health.is_healthy():
                    continue
            
            providers.append(provider_id)
        
        return providers
    
    async def select_provider(
        self,
        query_context: Optional[Dict[str, Any]] = None,
        exclude_providers: Optional[List[str]] = None
    ) -> Optional[SearchProvider]:
        """
        Select a provider based on configured strategy.
        
        Args:
            query_context: Optional context for selection
            exclude_providers: Providers to exclude
            
        Returns:
            Selected provider or None
        """
        # Get available providers
        available = self._get_available_providers(exclude_providers)
        if not available:
            return None
        
        # Apply selection strategy
        if self._selection_strategy == SelectionStrategy.PRIORITY:
            return self._select_by_priority(available)
        elif self._selection_strategy == SelectionStrategy.ROUND_ROBIN:
            return self._select_round_robin(available)
        elif self._selection_strategy == SelectionStrategy.LEAST_LOADED:
            return self._select_least_loaded(available)
        elif self._selection_strategy == SelectionStrategy.FASTEST:
            return self._select_fastest(available)
        else:  # RANDOM
            import random
            return random.choice(available)
    
    def get_failover_chain(
        self,
        primary_provider: str,
        max_providers: int = 3
    ) -> List[SearchProvider]:
        """
        Get failover chain starting with primary provider.
        
        Args:
            primary_provider: Primary provider ID
            max_providers: Maximum providers in chain
            
        Returns:
            Ordered list of providers for failover
        """
        chain = []
        
        # Add primary if available
        primary = self.get_provider(primary_provider)
        if primary and primary.config.enabled:
            chain.append(primary)
        
        # Add others by priority
        for provider_id in self._provider_order:
            if len(chain) >= max_providers:
                break
            if provider_id == primary_provider:
                continue
            
            provider = self._providers[provider_id]
            if provider.config.enabled and provider.get_health_status().is_healthy():
                chain.append(provider)
        
        return chain
    
    async def execute_with_failover(
        self,
        options: SearchOptions,
        primary_provider: Optional[str] = None,
        max_attempts: int = 3
    ) -> SearchResults:
        """
        Execute search with automatic failover.
        
        Args:
            options: Search options
            primary_provider: Preferred provider
            max_attempts: Maximum providers to try
            
        Returns:
            Search results from first successful provider
            
        Raises:
            ProviderError: If all providers fail
        """
        # Get provider chain
        if primary_provider:
            chain = self.get_failover_chain(primary_provider, max_attempts)
        else:
            # Use selection strategy
            selected = await self.select_provider()
            if not selected:
                from ..core.exceptions import ProviderError
                raise ProviderError(
                    provider_name="none",
                    operation="search",
                    provider_error="No providers available"
                )
            chain = self.get_failover_chain(
                self._get_provider_id(selected),
                max_attempts
            )
        
        # Try each provider
        errors = []
        for i, provider in enumerate(chain):
            try:
                logger.info(f"Attempting search with {provider.__class__.__name__}")
                return await provider.search_with_circuit_breaker(options)
            except Exception as e:
                errors.append({
                    "provider": provider.__class__.__name__,
                    "error": str(e)
                })
                logger.warning(f"Provider {provider.__class__.__name__} failed: {e}")
                
                if i < len(chain) - 1:
                    logger.info(f"Failing over to next provider")
        
        # All failed
        from ..core.exceptions import ProviderError
        raise ProviderError(
            provider_name="all",
            operation="search",
            provider_error=f"All {len(errors)} providers failed",
            fallback_providers=[],
            status_code=503
        )
    
    def set_selection_strategy(self, strategy: SelectionStrategy) -> None:
        """
        Set provider selection strategy.
        
        Args:
            strategy: Selection strategy to use
        """
        self._selection_strategy = strategy
        logger.info(f"Set selection strategy to: {strategy.value}")
    
    def update_provider_priority(
        self,
        provider_priorities: Dict[str, int]
    ) -> None:
        """
        Update provider priorities (for UI drag-drop).
        
        Args:
            provider_priorities: Map of provider_id to priority
        """
        for provider_id, priority in provider_priorities.items():
            if provider_id in self._providers:
                self._providers[provider_id].config.priority = priority
        
        self._update_provider_order()
        logger.info(f"Updated provider priorities")
    
    async def warm_up_all(self) -> Dict[str, bool]:
        """
        Warm up all providers concurrently.
        
        Returns:
            Map of provider_id to success status
        """
        tasks = {}
        for provider_id, provider in self._providers.items():
            if provider.config.enabled:
                tasks[provider_id] = provider.warm_up()
        
        if not tasks:
            return {}
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        return {
            provider_id: result if isinstance(result, bool) else False
            for provider_id, result in zip(tasks.keys(), results)
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get performance summary across all providers.
        
        Returns:
            Performance metrics by provider
        """
        summary = {}
        
        for provider_id, provider in self._providers.items():
            health = provider.get_health_status()
            summary[provider_id] = {
                "status": health.status.value,
                "error_rate": health.error_rate_percent,
                "avg_latency_ms": health.response_time_ms,
                "circuit_state": health.circuit_breaker_state,
                "enabled": provider.config.enabled,
                "priority": provider.config.priority
            }
        
        return summary
    
    # Private helper methods
    
    def _update_provider_order(self) -> None:
        """Update provider order based on priorities."""
        self._provider_order = sorted(
            self._providers.keys(),
            key=lambda p: self._providers[p].config.priority
        )
    
    def _get_available_providers(
        self,
        exclude: Optional[List[str]] = None
    ) -> List[SearchProvider]:
        """Get list of available providers."""
        exclude = exclude or []
        available = []
        
        for provider_id in self._provider_order:
            if provider_id in exclude:
                continue
            
            provider = self._providers[provider_id]
            if provider.config.enabled:
                health = provider.get_health_status()
                if health.is_healthy():
                    available.append(provider)
        
        return available
    
    def _select_by_priority(
        self,
        providers: List[SearchProvider]
    ) -> Optional[SearchProvider]:
        """Select by priority order."""
        return providers[0] if providers else None
    
    def _select_round_robin(
        self,
        providers: List[SearchProvider]
    ) -> Optional[SearchProvider]:
        """Select using round-robin."""
        if not providers:
            return None
        
        selected = providers[self._round_robin_index % len(providers)]
        self._round_robin_index += 1
        return selected
    
    def _select_least_loaded(
        self,
        providers: List[SearchProvider]
    ) -> Optional[SearchProvider]:
        """Select provider with lowest load."""
        if not providers:
            return None
        
        # Sort by request count in rate limit window
        return min(
            providers,
            key=lambda p: p.get_rate_limits().requests_made
        )
    
    def _select_fastest(
        self,
        providers: List[SearchProvider]
    ) -> Optional[SearchProvider]:
        """Select provider with best latency."""
        if not providers:
            return None
        
        # Sort by average latency
        providers_with_latency = []
        for provider in providers:
            health = provider.get_health_status()
            if health.response_time_ms is not None:
                providers_with_latency.append((provider, health.response_time_ms))
        
        if not providers_with_latency:
            return providers[0]  # Fallback to first
        
        return min(providers_with_latency, key=lambda x: x[1])[0]
    
    def _get_provider_id(self, provider: SearchProvider) -> str:
        """Get provider ID from instance."""
        for provider_id, p in self._providers.items():
            if p == provider:
                return provider_id
        return "unknown"