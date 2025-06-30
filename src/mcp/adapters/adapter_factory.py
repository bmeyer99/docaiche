"""
Adapter Factory for MCP to FastAPI Integration
=============================================

Factory for creating and managing MCP adapters with centralized
configuration and lifecycle management.
"""

import logging
from typing import Dict, Any, Optional, Type
from enum import Enum

from .base_adapter import BaseAdapter
from .search_adapter import SearchAdapter
from .ingestion_adapter import IngestionAdapter
from .logs_adapter import LogsAdapter
from .health_adapter import HealthAdapter
from .config_adapter import ConfigAdapter

logger = logging.getLogger(__name__)


class AdapterType(str, Enum):
    """Available adapter types."""
    SEARCH = "search"
    INGESTION = "ingestion"
    LOGS = "logs"
    HEALTH = "health"
    CONFIG = "config"


class AdapterFactory:
    """
    Factory for creating and managing MCP adapters.
    
    Provides centralized adapter creation with consistent configuration
    and lifecycle management across all adapter types.
    """
    
    # Adapter type to class mapping
    ADAPTER_CLASSES: Dict[AdapterType, Type[BaseAdapter]] = {
        AdapterType.SEARCH: SearchAdapter,
        AdapterType.INGESTION: IngestionAdapter,
        AdapterType.LOGS: LogsAdapter,
        AdapterType.HEALTH: HealthAdapter,
        AdapterType.CONFIG: ConfigAdapter
    }
    
    def __init__(
        self,
        base_url: str,
        api_version: str = "v1",
        default_timeout: int = 30,
        auth_token: Optional[str] = None
    ):
        """
        Initialize adapter factory.
        
        Args:
            base_url: Base URL for FastAPI service
            api_version: API version to use
            default_timeout: Default request timeout
            auth_token: Authentication token for API access
        """
        self.base_url = base_url
        self.api_version = api_version
        self.default_timeout = default_timeout
        self.auth_token = auth_token
        
        # Cache for adapter instances
        self._adapters: Dict[AdapterType, BaseAdapter] = {}
        
        logger.info(
            "Adapter factory initialized",
            extra={
                "base_url": base_url,
                "api_version": api_version
            }
        )
    
    def create_adapter(
        self,
        adapter_type: AdapterType,
        **kwargs
    ) -> BaseAdapter:
        """
        Create an adapter instance.
        
        Args:
            adapter_type: Type of adapter to create
            **kwargs: Additional adapter-specific configuration
            
        Returns:
            Configured adapter instance
            
        Raises:
            ValueError: If adapter type is unknown
        """
        if adapter_type not in self.ADAPTER_CLASSES:
            raise ValueError(f"Unknown adapter type: {adapter_type}")
        
        # Check cache first
        if adapter_type in self._adapters:
            logger.debug(f"Returning cached adapter: {adapter_type}")
            return self._adapters[adapter_type]
        
        # Get adapter class
        adapter_class = self.ADAPTER_CLASSES[adapter_type]
        
        # Merge default configuration with provided kwargs
        config = {
            'base_url': self.base_url,
            'api_version': self.api_version,
            'timeout': kwargs.get('timeout', self.default_timeout),
            'auth_token': kwargs.get('auth_token', self.auth_token),
            'max_retries': kwargs.get('max_retries', 3)
        }
        
        # Create adapter instance
        adapter = adapter_class(**config)
        
        # Cache the adapter
        self._adapters[adapter_type] = adapter
        
        logger.info(f"Created adapter: {adapter_type}")
        
        return adapter
    
    def get_adapter(self, adapter_type: AdapterType) -> Optional[BaseAdapter]:
        """
        Get a cached adapter instance.
        
        Args:
            adapter_type: Type of adapter to retrieve
            
        Returns:
            Cached adapter instance or None
        """
        return self._adapters.get(adapter_type)
    
    def get_or_create_adapter(
        self,
        adapter_type: AdapterType,
        **kwargs
    ) -> BaseAdapter:
        """
        Get existing adapter or create new one.
        
        Args:
            adapter_type: Type of adapter
            **kwargs: Configuration for new adapter
            
        Returns:
            Adapter instance
        """
        adapter = self.get_adapter(adapter_type)
        if not adapter:
            adapter = self.create_adapter(adapter_type, **kwargs)
        return adapter
    
    async def close_all(self) -> None:
        """Close all adapter connections."""
        for adapter_type, adapter in self._adapters.items():
            try:
                await adapter.close()
                logger.info(f"Closed adapter: {adapter_type}")
            except Exception as e:
                logger.error(
                    f"Error closing adapter {adapter_type}: {str(e)}",
                    exc_info=True
                )
        
        self._adapters.clear()
    
    async def close_adapter(self, adapter_type: AdapterType) -> None:
        """
        Close a specific adapter.
        
        Args:
            adapter_type: Type of adapter to close
        """
        if adapter_type in self._adapters:
            adapter = self._adapters.pop(adapter_type)
            try:
                await adapter.close()
                logger.info(f"Closed adapter: {adapter_type}")
            except Exception as e:
                logger.error(
                    f"Error closing adapter {adapter_type}: {str(e)}",
                    exc_info=True
                )
    
    def update_auth_token(self, auth_token: str) -> None:
        """
        Update authentication token for all adapters.
        
        Args:
            auth_token: New authentication token
        """
        self.auth_token = auth_token
        
        # Update existing adapters
        for adapter in self._adapters.values():
            adapter.auth_token = auth_token
        
        logger.info("Updated auth token for all adapters")
    
    def get_adapter_stats(self) -> Dict[str, Any]:
        """
        Get statistics for all active adapters.
        
        Returns:
            Dictionary of adapter statistics
        """
        stats = {
            'active_adapters': len(self._adapters),
            'adapters': {}
        }
        
        for adapter_type, adapter in self._adapters.items():
            stats['adapters'][adapter_type.value] = {
                'type': adapter.__class__.__name__,
                'base_url': adapter.base_url,
                'session_active': adapter._session is not None and not adapter._session.closed
            }
        
        return stats
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close_all()


def create_adapter_factory(
    config: Dict[str, Any]
) -> AdapterFactory:
    """
    Create adapter factory from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configured adapter factory
    """
    return AdapterFactory(
        base_url=config.get('base_url', 'http://localhost:8000'),
        api_version=config.get('api_version', 'v1'),
        default_timeout=config.get('timeout', 30),
        auth_token=config.get('auth_token')
    )


# Adapter factory complete with:
# ✓ Centralized adapter creation
# ✓ Adapter caching and reuse
# ✓ Lifecycle management
# ✓ Authentication updates
# ✓ Statistics collection
# ✓ Context manager support
# ✓ Configuration-based creation