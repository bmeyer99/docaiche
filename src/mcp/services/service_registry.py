"""
Service Registry for Dependency Injection
=========================================

Provides a centralized registry for managing service dependencies
and enabling dependency injection across the MCP server components.

This addresses the critical issue where tools and resources need
actual service implementations instead of None values.
"""

import logging
from typing import Dict, Any, Type, Optional, TypeVar, Generic
from abc import ABC

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceRegistry:
    """
    Centralized service registry for dependency injection.
    
    Manages registration and retrieval of service implementations,
    enabling loose coupling between components and facilitating
    testing and configuration.
    """
    
    def __init__(self):
        """Initialize service registry."""
        self._services: Dict[Type, Any] = {}
        self._service_names: Dict[str, Any] = {}
        logger.info("Service registry initialized")
    
    def register(
        self,
        interface: Type[T],
        implementation: T,
        name: Optional[str] = None
    ) -> None:
        """
        Register a service implementation.
        
        Args:
            interface: Service interface type
            implementation: Service implementation instance
            name: Optional service name for named lookups
        """
        self._services[interface] = implementation
        
        if name:
            self._service_names[name] = implementation
        
        logger.info(
            f"Service registered: {interface.__name__}",
            extra={"name": name} if name else {}
        )
    
    def get(self, interface: Type[T]) -> Optional[T]:
        """
        Get a service by interface type.
        
        Args:
            interface: Service interface type
            
        Returns:
            Service implementation or None if not found
        """
        return self._services.get(interface)
    
    def get_by_name(self, name: str) -> Optional[Any]:
        """
        Get a service by name.
        
        Args:
            name: Service name
            
        Returns:
            Service implementation or None if not found
        """
        return self._service_names.get(name)
    
    def require(self, interface: Type[T]) -> T:
        """
        Get a required service by interface type.
        
        Args:
            interface: Service interface type
            
        Returns:
            Service implementation
            
        Raises:
            ValueError: If service not found
        """
        service = self.get(interface)
        if not service:
            raise ValueError(f"Required service not found: {interface.__name__}")
        return service
    
    def has(self, interface: Type) -> bool:
        """
        Check if a service is registered.
        
        Args:
            interface: Service interface type
            
        Returns:
            True if service is registered
        """
        return interface in self._services
    
    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._service_names.clear()
        logger.info("Service registry cleared")


# Service interfaces for type safety
class SearchService(ABC):
    """Search service interface."""
    async def search(self, query: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError


class IngestionService(ABC):
    """Ingestion service interface."""
    async def ingest(self, content: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        raise NotImplementedError


class DocumentationService(ABC):
    """Documentation service interface."""
    async def get_documentation(self, doc_id: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError


class CollectionsService(ABC):
    """Collections service interface."""
    async def list_collections(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError


class HealthService(ABC):
    """Health check service interface."""
    async def check_health(self) -> Dict[str, Any]:
        raise NotImplementedError


class FeedbackService(ABC):
    """Feedback service interface."""
    async def submit_feedback(self, feedback: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        raise NotImplementedError


class MetricsCollector(ABC):
    """Metrics collection service interface."""
    async def collect_metrics(self) -> Dict[str, Any]:
        raise NotImplementedError


class AnalyticsEngine(ABC):
    """Analytics engine interface."""
    async def track_event(self, event: Dict[str, Any]) -> None:
        raise NotImplementedError


# Global service registry instance
_registry = ServiceRegistry()


def get_service_registry() -> ServiceRegistry:
    """Get the global service registry instance."""
    return _registry


def register_service(
    interface: Type[T],
    implementation: T,
    name: Optional[str] = None
) -> None:
    """
    Register a service in the global registry.
    
    Args:
        interface: Service interface type
        implementation: Service implementation instance
        name: Optional service name
    """
    _registry.register(interface, implementation, name)


def get_service(interface: Type[T]) -> Optional[T]:
    """
    Get a service from the global registry.
    
    Args:
        interface: Service interface type
        
    Returns:
        Service implementation or None
    """
    return _registry.get(interface)