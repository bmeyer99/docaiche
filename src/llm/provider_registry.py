"""
Provider Registry System - AI Providers Implementation
Central registry for managing all LLM providers dynamically
"""

import logging
from typing import Dict, List, Optional, Type, Any, Set
from datetime import datetime
import asyncio
from functools import wraps

from .models import (
    ProviderInfo, ProviderCapabilities, ProviderCategory,
    TestResult, ProviderHealth, HealthStatus, ModelDiscoveryResult
)

logger = logging.getLogger(__name__)


class ProviderRegistrationError(Exception):
    """Raised when provider registration fails"""
    pass


class ProviderNotFoundError(Exception):
    """Raised when requested provider is not found"""
    pass


# Global registry instance
_registry_instance: Optional["ProviderRegistry"] = None


def register_provider(provider_id: str, category: ProviderCategory = None):
    """
    Decorator to automatically register a provider class
    
    Usage:
        @register_provider("anthropic", ProviderCategory.CLOUD)
        class AnthropicProvider(BaseProvider):
            pass
    """
    def decorator(provider_class):
        # Get the global registry and register the provider
        registry = get_provider_registry()
        registry.register(provider_id, provider_class, category)
        return provider_class
    return decorator


class ProviderRegistry:
    """
    Central registry for all LLM providers
    
    Manages provider discovery, registration, and lifecycle
    """
    
    def __init__(self):
        self._providers: Dict[str, Type] = {}
        self._provider_info: Dict[str, ProviderInfo] = {}
        self._health_status: Dict[str, ProviderHealth] = {}
        self._provider_instances: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        
        logger.info("Provider registry initialized")
    
    def register(self, provider_id: str, provider_class: Type, category: ProviderCategory = None):
        """
        Register a new provider class
        
        Args:
            provider_id: Unique identifier for the provider
            provider_class: Provider class implementing BaseProvider interface
            category: Provider category (auto-detected if not provided)
        """
        try:
            # Validate provider class
            if not hasattr(provider_class, 'get_static_capabilities'):
                raise ProviderRegistrationError(
                    f"Provider {provider_id} must implement get_static_capabilities()"
                )
            
            if not hasattr(provider_class, 'get_config_schema'):
                raise ProviderRegistrationError(
                    f"Provider {provider_id} must implement get_config_schema()"
                )
            
            # Get capabilities and schema from provider
            capabilities = provider_class.get_static_capabilities()
            config_schema = provider_class.get_config_schema()
            
            # Auto-detect category if not provided
            if category is None:
                category = getattr(provider_class, '_category', ProviderCategory.CLOUD)
            
            # Get display name and description
            display_name = getattr(provider_class, '_display_name', provider_id.title())
            description = getattr(provider_class, '_description', f"{display_name} provider")
            
            # Store provider information
            self._providers[provider_id] = provider_class
            self._provider_info[provider_id] = ProviderInfo(
                provider_id=provider_id,
                display_name=display_name,
                description=description,
                category=category,
                capabilities=capabilities,
                enabled=True,
                config_schema=config_schema
            )
            
            # Initialize health status
            self._health_status[provider_id] = ProviderHealth(
                provider_id=provider_id,
                status=HealthStatus.UNKNOWN,
                last_check=datetime.utcnow()
            )
            
            logger.info(f"Registered provider: {provider_id} ({category.value})")
            
        except Exception as e:
            raise ProviderRegistrationError(f"Failed to register provider {provider_id}: {e}")
    
    def unregister(self, provider_id: str):
        """
        Unregister a provider
        
        Args:
            provider_id: Provider to unregister
        """
        if provider_id in self._providers:
            del self._providers[provider_id]
            del self._provider_info[provider_id]
            if provider_id in self._health_status:
                del self._health_status[provider_id]
            if provider_id in self._provider_instances:
                del self._provider_instances[provider_id]
            
            logger.info(f"Unregistered provider: {provider_id}")
        else:
            logger.warning(f"Attempted to unregister unknown provider: {provider_id}")
    
    def get_provider_class(self, provider_id: str) -> Optional[Type]:
        """
        Get provider class by ID
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Provider class or None if not found
        """
        return self._providers.get(provider_id)
    
    def get_provider_info(self, provider_id: str) -> Optional[ProviderInfo]:
        """
        Get provider information by ID
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Provider info or None if not found
        """
        return self._provider_info.get(provider_id)
    
    def list_providers(self, category: Optional[ProviderCategory] = None, 
                      enabled_only: bool = False) -> List[ProviderInfo]:
        """
        List all registered providers
        
        Args:
            category: Filter by category (optional)
            enabled_only: Only return enabled providers
            
        Returns:
            List of provider information
        """
        providers = list(self._provider_info.values())
        
        # Filter by category
        if category:
            providers = [p for p in providers if p.category == category]
        
        # Filter by enabled status
        if enabled_only:
            providers = [p for p in providers if p.enabled]
        
        return providers
    
    def get_providers_by_capability(self, capability: str) -> List[str]:
        """
        Get providers that support a specific capability
        
        Args:
            capability: Capability name (e.g., 'text_generation', 'embeddings')
            
        Returns:
            List of provider IDs that support the capability
        """
        matching_providers = []
        
        for provider_id, info in self._provider_info.items():
            if hasattr(info.capabilities, capability):
                if getattr(info.capabilities, capability):
                    matching_providers.append(provider_id)
        
        return matching_providers
    
    async def get_provider_instance(self, provider_id: str, config: Dict[str, Any]):
        """
        Get or create a provider instance with configuration
        
        Args:
            provider_id: Provider identifier
            config: Provider configuration
            
        Returns:
            Configured provider instance
            
        Raises:
            ProviderNotFoundError: If provider is not registered
        """
        async with self._lock:
            provider_class = self._providers.get(provider_id)
            if not provider_class:
                raise ProviderNotFoundError(f"Provider {provider_id} not found")
            
            # Create instance key based on provider and config hash
            config_hash = hash(str(sorted(config.items())))
            instance_key = f"{provider_id}_{config_hash}"
            
            # Return existing instance if available
            if instance_key in self._provider_instances:
                return self._provider_instances[instance_key]
            
            # Create new instance
            try:
                instance = provider_class(config)
                self._provider_instances[instance_key] = instance
                logger.debug(f"Created new instance for provider {provider_id}")
                return instance
            except Exception as e:
                logger.error(f"Failed to create instance for provider {provider_id}: {e}")
                raise
    
    async def test_provider(self, provider_id: str, config: Dict[str, Any], 
                           test_mode: str = "connection") -> TestResult:
        """
        Test a provider with given configuration
        
        Args:
            provider_id: Provider to test
            config: Configuration to test with
            test_mode: Type of test ('connection', 'text', 'embedding')
            
        Returns:
            Test result
        """
        try:
            provider_class = self._providers.get(provider_id)
            if not provider_class:
                return TestResult(
                    success=False,
                    error_message=f"Provider {provider_id} not found",
                    capabilities=ProviderCapabilities()
                )
            
            # Get capabilities
            capabilities = provider_class.get_static_capabilities()
            
            # Create temporary instance for testing
            instance = provider_class(config)
            
            start_time = datetime.utcnow()
            
            # Perform connection test
            await instance.test_connection(config)
            
            latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Perform specific capability tests
            models = None
            if test_mode in ["text", "embedding"] or capabilities.model_discovery:
                try:
                    models = await instance.discover_models(config)
                except Exception as e:
                    logger.warning(f"Model discovery failed for {provider_id}: {e}")
            
            return TestResult(
                success=True,
                latency_ms=latency_ms,
                models=models,
                capabilities=capabilities
            )
            
        except Exception as e:
            logger.error(f"Provider test failed for {provider_id}: {e}")
            return TestResult(
                success=False,
                error_message=str(e),
                capabilities=capabilities if 'capabilities' in locals() else ProviderCapabilities()
            )
    
    async def update_provider_health(self, provider_id: str, health: ProviderHealth):
        """
        Update health status for a provider
        
        Args:
            provider_id: Provider identifier
            health: New health status
        """
        self._health_status[provider_id] = health
        logger.debug(f"Updated health for {provider_id}: {health.status.value}")
    
    def get_provider_health(self, provider_id: str) -> Optional[ProviderHealth]:
        """
        Get current health status for a provider
        
        Args:
            provider_id: Provider identifier
            
        Returns:
            Provider health or None if not found
        """
        return self._health_status.get(provider_id)
    
    def get_healthy_providers(self, capability: Optional[str] = None) -> List[str]:
        """
        Get list of healthy providers, optionally filtered by capability
        
        Args:
            capability: Filter by capability (optional)
            
        Returns:
            List of healthy provider IDs
        """
        healthy_providers = []
        
        for provider_id, health in self._health_status.items():
            if health.status == HealthStatus.HEALTHY:
                # Check capability if specified
                if capability:
                    info = self._provider_info.get(provider_id)
                    if info and hasattr(info.capabilities, capability):
                        if getattr(info.capabilities, capability):
                            healthy_providers.append(provider_id)
                else:
                    healthy_providers.append(provider_id)
        
        return healthy_providers
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """
        Get registry statistics
        
        Returns:
            Dictionary with registry statistics
        """
        total_providers = len(self._providers)
        enabled_providers = len([p for p in self._provider_info.values() if p.enabled])
        healthy_providers = len([h for h in self._health_status.values() 
                               if h.status == HealthStatus.HEALTHY])
        
        # Count by category
        category_counts = {}
        for info in self._provider_info.values():
            category = info.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count by capability
        capability_counts = {}
        for info in self._provider_info.values():
            caps = info.capabilities
            for cap_name in ['text_generation', 'embeddings', 'streaming', 'function_calling']:
                if getattr(caps, cap_name, False):
                    capability_counts[cap_name] = capability_counts.get(cap_name, 0) + 1
        
        return {
            "total_providers": total_providers,
            "enabled_providers": enabled_providers,
            "healthy_providers": healthy_providers,
            "category_counts": category_counts,
            "capability_counts": capability_counts,
            "registered_providers": list(self._providers.keys())
        }
    
    def clear_instances(self):
        """Clear all cached provider instances (useful for config changes)"""
        self._provider_instances.clear()
        logger.info("Cleared all provider instances")


def get_provider_registry() -> ProviderRegistry:
    """
    Get the global provider registry instance (singleton)
    
    Returns:
        Global provider registry
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ProviderRegistry()
    return _registry_instance


def reset_provider_registry():
    """Reset the global provider registry (useful for testing)"""
    global _registry_instance
    _registry_instance = None


# Auto-discovery utilities

def discover_providers_in_module(module):
    """
    Discover and register providers in a module
    
    Args:
        module: Python module to scan for providers
    """
    registry = get_provider_registry()
    
    for name in dir(module):
        obj = getattr(module, name)
        if (isinstance(obj, type) and 
            hasattr(obj, 'get_static_capabilities') and
            hasattr(obj, 'get_config_schema')):
            
            # Auto-generate provider ID from class name
            provider_id = name.lower().replace('provider', '')
            
            try:
                registry.register(provider_id, obj)
                logger.info(f"Auto-discovered provider: {provider_id}")
            except ProviderRegistrationError as e:
                logger.warning(f"Failed to auto-register {provider_id}: {e}")


def register_builtin_providers():
    """Register built-in providers from the providers module"""
    try:
        from . import providers
        discover_providers_in_module(providers)
        logger.info("Registered built-in providers")
    except ImportError:
        logger.warning("No built-in providers module found")