"""
Configuration Manager - PRD-003 CFG-002
Singleton ConfigurationManager class with hierarchical loading and database integration

Implements exactly as specified in PRD-003:
- Singleton pattern implementation
- Integration with PRD-002 DatabaseManager
- Thread-safe configuration access
- Runtime update capability
- Hierarchical loading: environment variables > config.yaml > database
"""

import asyncio
import json
import logging
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any, AsyncContextManager
from contextlib import asynccontextmanager

import yaml
from pydantic import ValidationError

from .models import SystemConfiguration
from .defaults import get_environment_overrides, apply_nested_override
from .secrets import SecretsManager

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Singleton Configuration Manager implementing CFG-002

    Provides thread-safe access to hierarchical configuration with:
    - Environment variables (highest priority)
    - config.yaml file (medium priority)
    - Database overrides (lowest priority)
    - Runtime updates without service restart
    - Hot-reloading of config.yaml changes
    """

    _instance: Optional["ConfigurationManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ConfigurationManager":
        """Ensure singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize configuration manager"""
        if self._initialized:
            return

        self._config: Optional[SystemConfiguration] = None
        self._config_file_path = "config.yaml"
        self._config_file_mtime: Optional[float] = None
        self._db_manager: Optional[Any] = None
        self._watch_config_file = True
        self._service_config_manager = None
        self._initialized = True
        logger.info("ConfigurationManager singleton initialized")

    async def initialize(
        self, config_file_path: str = "config.yaml", watch_file: bool = True
    ) -> None:
        """
        Initialize configuration manager with file path and database connection

        Args:
            config_file_path: Path to configuration YAML file
            watch_file: Enable file watching for hot-reload
        """
        self._config_file_path = config_file_path
        self._watch_config_file = watch_file

        # Initialize database manager for config overrides (CFG-005)
        try:
            from src.database.manager import create_database_manager

            self._db_manager = await create_database_manager()
            await self._db_manager.connect()
            logger.info("Database manager connected for configuration overrides")
        except ImportError:
            logger.warning("Database manager not available for configuration overrides")
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")

        # Load initial configuration
        await self.load_configuration()

    async def load_configuration(self) -> SystemConfiguration:
        """
        Load configuration from all sources with correct hierarchy

        CFG-003: Hierarchical Configuration Loading
        Priority order: Environment variables > config.yaml > database

        Returns:
            SystemConfiguration: Complete validated configuration
        """
        try:
            # Step 1: Load base configuration from database (lowest priority)
            config_dict = await self._load_from_database()

            # Step 2: Load and merge config.yaml (medium priority)
            yaml_config = await self._load_from_yaml()
            if yaml_config:
                self._merge_config_dict(config_dict, yaml_config)

            # Step 3: Load and merge environment variables (highest priority)
            env_overrides = get_environment_overrides()
            for key, value in env_overrides.items():
                apply_nested_override(config_dict, key, value)

            # Validate and create configuration object
            self._config = self._build_system_configuration(config_dict)

            # Validate production secrets if needed
            if self._config.app.environment == "production":
                SecretsManager.validate_production_secrets(self._config)

            logger.info(
                f"Configuration loaded successfully for environment: {self._config.app.environment}"
            )
            return self._config

        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            raise ValueError(f"Failed to load configuration: {e}")

    async def _load_from_database(self) -> Dict[str, Any]:
        """
        Load configuration overrides from database

        CFG-005: Database Integration
        Uses PRD-002 DatabaseManager for config retrieval

        Returns:
            Dict containing database configuration overrides
        """
        config_dict = {}

        if not self._db_manager:
            return config_dict

        try:
            # Query system_config table for configuration overrides
            rows = await self._db_manager.fetch_all(
                "SELECT key, value FROM system_config",
                (),
            )

            for row in rows:
                try:
                    # Parse JSON value
                    value = json.loads(row.value)
                    apply_nested_override(config_dict, row.key, value)
                except (json.JSONDecodeError, AttributeError):
                    # Treat as string value
                    apply_nested_override(config_dict, row.key, row.value)

            if config_dict:
                logger.info(f"Loaded {len(rows)} configuration overrides from database")

        except Exception as e:
            logger.warning(f"Failed to load configuration from database: {e}")

        return config_dict

    async def _load_from_yaml(self) -> Optional[Dict[str, Any]]:
        """
        Load configuration from YAML file

        CFG-008: Default Configuration File
        Loads config.yaml with production defaults

        Returns:
            Dict containing YAML configuration or None if file not found
        """
        config_path = Path(self._config_file_path)

        if not config_path.exists():
            logger.info(
                f"Configuration file {config_path} not found, using environment defaults"
            )
            return None

        try:
            # Check file modification time for hot-reload
            current_mtime = config_path.stat().st_mtime

            with open(config_path, "r") as f:
                yaml_content = yaml.safe_load(f)

            self._config_file_mtime = current_mtime
            logger.info(f"Configuration loaded from {config_path}")
            return yaml_content or {}

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in configuration file: {e}")
            raise ValueError(f"Configuration file contains invalid YAML: {e}")
        except Exception as e:
            logger.error(f"Failed to load configuration file: {e}")
            raise ValueError(f"Failed to read configuration file: {e}")

    def _build_system_configuration(
        self, config_dict: Dict[str, Any]
    ) -> SystemConfiguration:
        """
        Build SystemConfiguration from merged configuration dictionary

        Args:
            config_dict: Merged configuration from all sources

        Returns:
            SystemConfiguration: Validated configuration object
        """
        try:
            # Import models
            from .models import (
                AppConfig,
                ContentConfig,
                AnythingLLMConfig,
                GitHubConfig,
                ScrapingConfig,
                RedisConfig,
                AIConfig,
                OllamaConfig,
                OpenAIConfig,
            )

            # Build configuration sections with defaults
            app_config = AppConfig(**(config_dict.get("app", {})))
            content_config = ContentConfig(**(config_dict.get("content", {})))
            anythingllm_config = AnythingLLMConfig(
                **(config_dict.get("anythingllm", {}))
            )
            github_config = GitHubConfig(**(config_dict.get("github", {})))
            scraping_config = ScrapingConfig(**(config_dict.get("scraping", {})))
            redis_config = RedisConfig(**(config_dict.get("redis", {})))

            # Build AI configuration with nested providers
            ai_dict = config_dict.get("ai", {})
            ollama_config = OllamaConfig(**(ai_dict.get("ollama", {})))
            # Only instantiate OpenAIConfig if openai is enabled/selected
            openai_config = None
            if (
                ai_dict.get("primary_provider") == "openai"
                or ai_dict.get("fallback_provider") == "openai"
            ):
                openai_section = ai_dict.get("openai", {})
                if openai_section and any(openai_section.values()):
                    openai_config = OpenAIConfig(**openai_section)
                else:
                    openai_config = None

            ai_config = AIConfig(
                primary_provider=ai_dict.get("primary_provider", "ollama"),
                fallback_provider=ai_dict.get("fallback_provider", "openai"),
                enable_failover=ai_dict.get("enable_failover", True),
                cache_ttl_seconds=ai_dict.get("cache_ttl_seconds", 3600),
                ollama=ollama_config,
                openai=openai_config,
            )

            # Create complete system configuration
            system_config = SystemConfiguration(
                app=app_config,
                content=content_config,
                anythingllm=anythingllm_config,
                github=github_config,
                scraping=scraping_config,
                redis=redis_config,
                ai=ai_config,
            )

            return system_config

        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise ValueError(f"Invalid configuration: {e}")

    def _merge_config_dict(
        self, base: Dict[str, Any], override: Dict[str, Any]
    ) -> None:
        """
        Recursively merge configuration dictionaries

        Args:
            base: Base configuration dictionary (modified in-place)
            override: Override configuration dictionary
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config_dict(base[key], value)
            else:
                base[key] = value

    async def update_in_db(self, config_key: str, config_value: Any) -> None:
        """
        Update configuration value in database

        CFG-005: Database Integration
        Uses PRD-002 DatabaseManager for config updates

        Args:
            config_key: Configuration key in dot notation (e.g., "redis.host")
            config_value: Configuration value to store
        """
        if not self._db_manager:
            raise ValueError("Database manager not available for configuration updates")

        try:
            # Serialize value as JSON if it's not a string
            if isinstance(config_value, (dict, list, bool, int, float)):
                serialized_value = json.dumps(config_value)
            else:
                serialized_value = str(config_value)

            # Upsert configuration value
            await self._db_manager.execute(
                """
                INSERT OR REPLACE INTO system_config (key, value, updated_at)
                VALUES (:param_0, :param_1, :param_2)
                """,
                (config_key, serialized_value, int(time.time())),
            )

            logger.info(f"Configuration updated in database: {config_key}")

            # Reload configuration to reflect changes
            await self.load_configuration()
            
            # Trigger service restart if needed
            await self._handle_config_change(config_key, config_value)

        except Exception as e:
            logger.error(f"Failed to update configuration in database: {e}")
            raise

    async def get_from_db(self, config_key: str) -> Optional[Any]:
        """
        Get configuration value from database

        CFG-005: Database Integration

        Args:
            config_key: Configuration key in dot notation

        Returns:
            Configuration value or None if not found
        """
        if not self._db_manager:
            return None

        try:
            row = await self._db_manager.fetch_one(
                "SELECT value FROM system_config WHERE key = :param_0",
                (config_key,),
            )

            if row:
                try:
                    return json.loads(row.value)
                except json.JSONDecodeError:
                    return row.value

            return None

        except Exception as e:
            logger.error(f"Failed to get configuration from database: {e}")
            return None

    async def check_for_config_file_changes(self) -> bool:
        """
        Check if configuration file has been modified

        CFG-010: Hot-Reloading Mechanism

        Returns:
            True if file was modified and configuration reloaded
        """
        if not self._watch_config_file:
            return False

        config_path = Path(self._config_file_path)

        if not config_path.exists():
            return False

        try:
            current_mtime = config_path.stat().st_mtime

            if (
                self._config_file_mtime is None
                or current_mtime > self._config_file_mtime
            ):
                logger.info("Configuration file changed, reloading...")
                # Store the old mtime before reloading
                old_mtime = self._config_file_mtime
                await self.load_configuration()
                # Ensure the mtime was actually updated
                if old_mtime != self._config_file_mtime:
                    return True

        except Exception as e:
            logger.error(f"Error checking configuration file changes: {e}")

        return False

    def get_setting(self, config_key: str) -> Optional[Any]:
        """
        Get a specific configuration setting by key
        
        Supports dot notation for nested access (e.g., "ai.providers.ollama.base_url")
        First checks runtime configuration, then falls back to database
        
        Args:
            config_key: Configuration key in dot notation
            
        Returns:
            Configuration value or None if not found
        """
        # Try to get from runtime configuration first
        if self._config is not None:
            try:
                # Split the key by dots and traverse the configuration
                keys = config_key.split('.')
                current = self._config.model_dump()
                
                for key in keys:
                    if isinstance(current, dict) and key in current:
                        current = current[key]
                    else:
                        # Not found in runtime config, try database
                        break
                else:
                    # Successfully traversed all keys
                    return current
            except (AttributeError, KeyError, TypeError):
                # Error in traversing, fall back to database
                pass
        
        # Fall back to database lookup
        try:
            import asyncio
            return asyncio.run(self.get_from_db(config_key))
        except Exception as e:
            logger.warning(f"Failed to get setting '{config_key}': {e}")
            return None

    def get_configuration(self) -> SystemConfiguration:
        """
        Get current configuration object

        CFG-006: Singleton Dependency Injection
        Thread-safe configuration access

        Returns:
            SystemConfiguration: Current configuration

        Raises:
            ValueError: If configuration not loaded
        """
        if self._config is None:
            raise ValueError(
                "Configuration not loaded. Call load_configuration() first."
            )
        return self._config

    async def reload_configuration(self) -> SystemConfiguration:
        """
        Force reload configuration from all sources

        Returns:
            SystemConfiguration: Reloaded configuration
        """
        logger.info("Force reloading configuration...")
        return await self.load_configuration()

    @asynccontextmanager
    async def watch_config_changes(
        self, check_interval: float = 5.0
    ) -> AsyncContextManager[None]:
        """
        Context manager for watching configuration file changes

        CFG-010: Hot-Reloading Mechanism

        Args:
            check_interval: Seconds between file modification checks
        """

        async def watch_task():
            while True:
                try:
                    await self.check_for_config_file_changes()
                    await asyncio.sleep(check_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in config file watcher: {e}")
                    await asyncio.sleep(check_interval)

        task = asyncio.create_task(watch_task())
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _handle_config_change(self, config_key: str, config_value: Any) -> None:
        """
        Handle configuration changes and trigger service restarts if needed
        
        Args:
            config_key: Configuration key that was changed
            config_value: New configuration value
        """
        try:
            # Initialize service config manager if not already done
            if not self._service_config_manager:
                from src.core.services.config_manager import ServiceConfigManager
                self._service_config_manager = ServiceConfigManager(self)
            
            # Generate correlation ID for tracking
            correlation_id = f"config_{config_key}_{int(time.time() * 1000)}"
            
            logger.info(f"Processing configuration change for {config_key}", extra={
                "event": "config_change_detected",
                "correlation_id": correlation_id,
                "config_key": config_key,
                "has_service_manager": self._service_config_manager is not None
            })
            
            # Handle the configuration change and potential service restarts
            result = await self._service_config_manager.handle_config_change(
                config_key, 
                config_value,
                correlation_id
            )
            
            if result.get("services_restarted"):
                logger.info(f"Services restarted for config change: {result}", extra={
                    "event": "config_change_processed",
                    "correlation_id": correlation_id,
                    "config_key": config_key,
                    "services_restarted": len(result.get("services_restarted", {})),
                    "success": result.get("success", False)
                })
            
        except Exception as e:
            logger.error(f"Failed to handle configuration change for {config_key}: {e}", extra={
                "event": "config_change_error",
                "config_key": config_key,
                "error": str(e),
                "error_type": type(e).__name__
            })


# Singleton instance getter for dependency injection
_config_manager: Optional[ConfigurationManager] = None


async def get_configuration_manager() -> ConfigurationManager:
    """
    Get or create singleton ConfigurationManager instance

    CFG-006: Singleton Dependency Injection
    For use with FastAPI dependency system

    Returns:
        ConfigurationManager: Singleton instance
    """
    global _config_manager

    if _config_manager is None:
        _config_manager = ConfigurationManager()
        await _config_manager.initialize()

    return _config_manager


async def get_current_configuration() -> SystemConfiguration:
    """
    Get current system configuration

    Convenience function for components that need configuration

    Returns:
        SystemConfiguration: Current configuration
    """
    manager = await get_configuration_manager()
    return manager.get_configuration()


def reload_configuration():
    """
    Compatibility stub for FastAPI and enrichment imports.
    Calls the async reload_configuration on the ConfigurationManager singleton.
    """
    try:
        manager = ConfigurationManager()
        import asyncio

        return asyncio.run(manager.reload_configuration())
    except Exception as e:
        logger.warning(f"reload_configuration: failed due to {e}")
        return None
