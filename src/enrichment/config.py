"""
Knowledge Enrichment Configuration Integration - PRD-010
Configuration management integration for the Knowledge Enrichment Pipeline.

Implements proper integration between EnrichmentConfig and the existing
configuration system with hot-reload capability and validation.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime

from src.core.config import get_system_configuration, reload_configuration
from src.core.config.models import EnrichmentConfig as CoreEnrichmentConfig
from .models import EnrichmentConfig as LocalEnrichmentConfig
from .exceptions import EnrichmentError

logger = logging.getLogger(__name__)


class EnrichmentConfigManager:
    """
    Configuration manager for enrichment pipeline with hot-reload support.
    
    Bridges the core configuration system with enrichment-specific configuration,
    providing validation, hot-reload, and environment-specific overrides.
    """
    
    def __init__(self):
        """Initialize enrichment configuration manager."""
        self._config: Optional[LocalEnrichmentConfig] = None
        self._last_updated: Optional[datetime] = None
        self._reload_callbacks: Dict[str, Callable[[LocalEnrichmentConfig], Awaitable[None]]] = {}
        self._validation_enabled = True
        
        logger.info("EnrichmentConfigManager initialized")
    
    async def get_config(self, force_reload: bool = False) -> LocalEnrichmentConfig:
        """
        Get enrichment configuration with optional force reload.
        
        Args:
            force_reload: Force configuration reload from source
            
        Returns:
            Current enrichment configuration
            
        Raises:
            EnrichmentError: If configuration loading fails
        """
        try:
            if self._config is None or force_reload:
                await self._load_config()
            
            return self._config
            
        except Exception as e:
            logger.error(f"Failed to get enrichment configuration: {e}")
            raise EnrichmentError(f"Configuration loading failed: {str(e)}")
    
    async def _load_config(self) -> None:
        """
        Load configuration from core system configuration.
        
        Converts CoreEnrichmentConfig to LocalEnrichmentConfig with validation.
        """
        try:
            # Get system configuration
            system_config = get_system_configuration()
            core_enrichment_config = system_config.enrichment
            
            # Convert core config to local enrichment config
            self._config = LocalEnrichmentConfig(
                max_concurrent_tasks=core_enrichment_config.max_concurrent_tasks,
                task_timeout_seconds=core_enrichment_config.task_timeout_seconds,
                retry_delay_seconds=core_enrichment_config.retry_delay_seconds,
                queue_poll_interval=core_enrichment_config.queue_poll_interval,
                batch_size=core_enrichment_config.batch_size,
                enable_relationship_mapping=core_enrichment_config.enable_relationship_mapping,
                enable_tag_generation=core_enrichment_config.enable_tag_generation,
                enable_quality_assessment=core_enrichment_config.enable_quality_assessment,
                min_confidence_threshold=core_enrichment_config.min_confidence_threshold
            )
            
            # Validate configuration if enabled
            if self._validation_enabled:
                await self._validate_config(self._config)
            
            self._last_updated = datetime.utcnow()
            
            logger.info(
                "Enrichment configuration loaded successfully",
                extra={
                    "max_concurrent_tasks": self._config.max_concurrent_tasks,
                    "task_timeout_seconds": self._config.task_timeout_seconds,
                    "features_enabled": {
                        "relationship_mapping": self._config.enable_relationship_mapping,
                        "tag_generation": self._config.enable_tag_generation,
                        "quality_assessment": self._config.enable_quality_assessment
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to load enrichment configuration: {e}")
            raise EnrichmentError(f"Configuration load failed: {str(e)}")
    
    async def _validate_config(self, config: LocalEnrichmentConfig) -> None:
        """
        Validate enrichment configuration settings.
        
        Args:
            config: Configuration to validate
            
        Raises:
            EnrichmentError: If validation fails
        """
        try:
            validation_errors = []
            
            # Validate concurrent tasks
            if config.max_concurrent_tasks < 1 or config.max_concurrent_tasks > 50:
                validation_errors.append(
                    f"max_concurrent_tasks must be between 1 and 50, got {config.max_concurrent_tasks}"
                )
            
            # Validate timeout
            if config.task_timeout_seconds < 10 or config.task_timeout_seconds > 3600:
                validation_errors.append(
                    f"task_timeout_seconds must be between 10 and 3600, got {config.task_timeout_seconds}"
                )
            
            # Validate retry delay
            if config.retry_delay_seconds < 1 or config.retry_delay_seconds > 300:
                validation_errors.append(
                    f"retry_delay_seconds must be between 1 and 300, got {config.retry_delay_seconds}"
                )
            
            # Validate poll interval
            if config.queue_poll_interval < 1 or config.queue_poll_interval > 60:
                validation_errors.append(
                    f"queue_poll_interval must be between 1 and 60, got {config.queue_poll_interval}"
                )
            
            # Validate batch size
            if config.batch_size < 1 or config.batch_size > 1000:
                validation_errors.append(
                    f"batch_size must be between 1 and 1000, got {config.batch_size}"
                )
            
            # Validate confidence threshold
            if config.min_confidence_threshold < 0.0 or config.min_confidence_threshold > 1.0:
                validation_errors.append(
                    f"min_confidence_threshold must be between 0.0 and 1.0, got {config.min_confidence_threshold}"
                )
            
            if validation_errors:
                error_message = "Configuration validation failed: " + "; ".join(validation_errors)
                logger.error(error_message)
                raise EnrichmentError(error_message)
            
            logger.debug("Enrichment configuration validation passed")
            
        except EnrichmentError:
            raise
        except Exception as e:
            logger.error(f"Configuration validation error: {e}")
            raise EnrichmentError(f"Validation failed: {str(e)}")
    
    async def reload_config(self) -> LocalEnrichmentConfig:
        """
        Reload configuration from source and notify callbacks.
        
        Returns:
            Reloaded configuration
            
        Raises:
            EnrichmentError: If reload fails
        """
        try:
            logger.info("Reloading enrichment configuration")
            
            # Reload core system configuration
            reload_configuration()
            
            # Load enrichment config
            await self._load_config()
            
            # Notify registered callbacks
            await self._notify_reload_callbacks()
            
            logger.info("Enrichment configuration reloaded successfully")
            return self._config
            
        except Exception as e:
            logger.error(f"Failed to reload enrichment configuration: {e}")
            raise EnrichmentError(f"Configuration reload failed: {str(e)}")
    
    async def _notify_reload_callbacks(self) -> None:
        """Notify all registered reload callbacks."""
        if not self._reload_callbacks or not self._config:
            return
        
        try:
            # Execute all callbacks concurrently
            tasks = []
            for callback_name, callback in self._reload_callbacks.items():
                task = asyncio.create_task(
                    self._execute_callback(callback_name, callback, self._config)
                )
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error notifying reload callbacks: {e}")
    
    async def _execute_callback(
        self,
        callback_name: str,
        callback: Callable[[LocalEnrichmentConfig], Awaitable[None]],
        config: LocalEnrichmentConfig
    ) -> None:
        """Execute a single reload callback."""
        try:
            await callback(config)
            logger.debug(f"Reload callback '{callback_name}' executed successfully")
            
        except Exception as e:
            logger.error(f"Reload callback '{callback_name}' failed: {e}")
    
    def register_reload_callback(
        self,
        name: str,
        callback: Callable[[LocalEnrichmentConfig], Awaitable[None]]
    ) -> None:
        """
        Register a callback for configuration reload events.
        
        Args:
            name: Unique callback name
            callback: Async callback function
        """
        self._reload_callbacks[name] = callback
        logger.debug(f"Reload callback '{name}' registered")
    
    def unregister_reload_callback(self, name: str) -> None:
        """
        Unregister a reload callback.
        
        Args:
            name: Callback name to remove
        """
        if name in self._reload_callbacks:
            del self._reload_callbacks[name]
            logger.debug(f"Reload callback '{name}' unregistered")
    
    async def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate current configuration and return status.
        
        Returns:
            Validation status and details
        """
        try:
            config = await self.get_config()
            
            validation_result = {
                "valid": True,
                "last_updated": self._last_updated.isoformat() if self._last_updated else None,
                "issues": [],
                "warnings": [],
                "config_summary": {
                    "max_concurrent_tasks": config.max_concurrent_tasks,
                    "task_timeout_seconds": config.task_timeout_seconds,
                    "enabled_features": {
                        "relationship_mapping": config.enable_relationship_mapping,
                        "tag_generation": config.enable_tag_generation,
                        "quality_assessment": config.enable_quality_assessment
                    }
                }
            }
            
            # Add warnings for potentially problematic settings
            if config.max_concurrent_tasks > 20:
                validation_result["warnings"].append(
                    f"High concurrent task count ({config.max_concurrent_tasks}) may impact performance"
                )
            
            if config.task_timeout_seconds < 30:
                validation_result["warnings"].append(
                    f"Short task timeout ({config.task_timeout_seconds}s) may cause premature failures"
                )
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return {
                "valid": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get configuration manager status.
        
        Returns:
            Status information
        """
        return {
            "initialized": self._config is not None,
            "last_updated": self._last_updated.isoformat() if self._last_updated else None,
            "validation_enabled": self._validation_enabled,
            "registered_callbacks": list(self._reload_callbacks.keys()),
            "callback_count": len(self._reload_callbacks)
        }


# Global configuration manager instance
_config_manager: Optional[EnrichmentConfigManager] = None


async def get_enrichment_config(force_reload: bool = False) -> LocalEnrichmentConfig:
    """
    Get enrichment configuration with caching and reload support.
    
    Args:
        force_reload: Force configuration reload
        
    Returns:
        Current enrichment configuration
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = EnrichmentConfigManager()
    
    return await _config_manager.get_config(force_reload=force_reload)


async def reload_enrichment_config() -> LocalEnrichmentConfig:
    """
    Reload enrichment configuration from source.
    
    Returns:
        Reloaded configuration
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = EnrichmentConfigManager()
    
    return await _config_manager.reload_config()


def register_config_reload_callback(
    name: str,
    callback: Callable[[LocalEnrichmentConfig], Awaitable[None]]
) -> None:
    """
    Register callback for configuration reload events.
    
    Args:
        name: Unique callback name
        callback: Async callback function
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = EnrichmentConfigManager()
    
    _config_manager.register_reload_callback(name, callback)


async def validate_enrichment_config() -> Dict[str, Any]:
    """
    Validate enrichment configuration.
    
    Returns:
        Validation results
    """
    global _config_manager
    
    if _config_manager is None:
        _config_manager = EnrichmentConfigManager()
    
    return await _config_manager.validate_configuration()


def get_config_manager_status() -> Dict[str, Any]:
    """
    Get configuration manager status.
    
    Returns:
        Manager status information
    """
    global _config_manager
    
    if _config_manager is None:
        return {
            "initialized": False,
            "message": "Configuration manager not initialized"
        }
    
    return _config_manager.get_status()