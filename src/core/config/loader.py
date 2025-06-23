"""
Hierarchical Configuration Loader - PRD-003 CFG-003
Implements hierarchical loading logic: Environment variables > config.yaml > database

Provides the exact loading workflow specified in PRD-003 with proper priority handling
and integration with all configuration sources.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

import yaml
from pydantic import ValidationError

from .defaults import get_environment_overrides, apply_nested_override
from .models import SystemConfiguration

logger = logging.getLogger(__name__)


class ConfigurationLoader:
    """
    Hierarchical Configuration Loader implementing CFG-003
    
    Loads configuration from multiple sources with correct priority:
    1. Environment variables (highest priority)
    2. config.yaml file (medium priority)  
    3. Database overrides (lowest priority)
    """
    
    def __init__(self, config_file_path: str = "config.yaml"):
        """
        Initialize configuration loader
        
        Args:
            config_file_path: Path to YAML configuration file
        """
        self.config_file_path = config_file_path
        self._db_manager: Optional[Any] = None
    
    async def set_database_manager(self, db_manager: Any) -> None:
        """
        Set database manager for loading configuration overrides
        
        Args:
            db_manager: DatabaseManager instance from PRD-002
        """
        self._db_manager = db_manager
    
    async def load_hierarchical_configuration(self) -> SystemConfiguration:
        """
        Load configuration from all sources with correct hierarchy
        
        CFG-003: Hierarchical Configuration Loading
        Priority order: Environment variables > config.yaml > database
        
        Returns:
            SystemConfiguration: Complete validated configuration
            
        Raises:
            ValueError: If configuration validation fails
        """
        try:
            # Step 1: Load base configuration from database (lowest priority)
            config_dict = await self._load_database_configuration()
            
            # Step 2: Load and merge YAML configuration (medium priority)
            yaml_config = await self._load_yaml_configuration()
            if yaml_config:
                self._deep_merge_dictionaries(config_dict, yaml_config)
            
            # Step 3: Load and merge environment variables (highest priority)
            env_config = self._load_environment_configuration()
            if env_config:
                for key, value in env_config.items():
                    apply_nested_override(config_dict, key, value)
            
            # Validate and build final configuration
            system_config = self._build_system_configuration(config_dict)
            
            logger.info("Hierarchical configuration loading completed successfully")
            return system_config
            
        except Exception as e:
            logger.error(f"Hierarchical configuration loading failed: {e}")
            raise ValueError(f"Configuration loading failed: {e}")
    
    async def _load_database_configuration(self) -> Dict[str, Any]:
        """
        Load configuration from database (lowest priority)
        
        Returns:
            Dict containing database configuration values
        """
        config_dict = {}
        
        if not self._db_manager:
            logger.debug("No database manager available for configuration loading")
            return config_dict
        
        try:
            # Create system_config table if it doesn't exist
            await self._ensure_system_config_table()
            
            # Load active configuration entries
            rows = await self._db_manager.fetch_all(
                "SELECT config_key, config_value FROM system_config WHERE is_active = :param_0",
                (True,)
            )
            
            for row in rows:
                try:
                    # Try to parse as JSON first
                    value = json.loads(row.config_value)
                except (json.JSONDecodeError, TypeError):
                    # Use as string value
                    value = row.config_value
                
                # Apply nested configuration using dot notation
                apply_nested_override(config_dict, row.config_key, value)
            
            if config_dict:
                logger.info(f"Loaded {len(rows)} configuration entries from database")
            
        except Exception as e:
            logger.warning(f"Failed to load database configuration: {e}")
        
        return config_dict
    
    async def _load_yaml_configuration(self) -> Optional[Dict[str, Any]]:
        """
        Load configuration from YAML file (medium priority)
        
        Returns:
            Dict containing YAML configuration or None if file not found
        """
        config_path = Path(self.config_file_path)
        
        if not config_path.exists():
            logger.info(f"Configuration file {config_path} not found")
            return None
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                yaml_content = yaml.safe_load(f)
            
            if yaml_content is None:
                logger.warning("YAML configuration file is empty")
                return {}
            
            logger.info(f"Loaded configuration from {config_path}")
            return yaml_content
            
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML syntax in {config_path}: {e}")
            raise ValueError(f"Configuration file contains invalid YAML: {e}")
        except Exception as e:
            logger.error(f"Failed to read configuration file {config_path}: {e}")
            raise ValueError(f"Cannot read configuration file: {e}")
    
    def _load_environment_configuration(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables (highest priority)
        
        CFG-004: Environment Variable Parsing
        
        Returns:
            Dict containing environment variable configuration
        """
        try:
            env_overrides = get_environment_overrides()
            
            if env_overrides:
                logger.info(f"Loaded {len(env_overrides)} environment variable overrides")
            
            return env_overrides
            
        except Exception as e:
            logger.error(f"Failed to load environment configuration: {e}")
            return {}
    
    def _deep_merge_dictionaries(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """
        Deep merge two configuration dictionaries
        
        Args:
            base: Base dictionary (modified in-place)
            override: Override dictionary values
        """
        for key, value in override.items():
            if (key in base and 
                isinstance(base[key], dict) and 
                isinstance(value, dict)):
                # Recursively merge nested dictionaries
                self._deep_merge_dictionaries(base[key], value)
            else:
                # Override or add new key
                base[key] = value
    
    def _build_system_configuration(self, config_dict: Dict[str, Any]) -> SystemConfiguration:
        """
        Build SystemConfiguration from merged configuration dictionary
        
        Args:
            config_dict: Merged configuration from all sources
            
        Returns:
            SystemConfiguration: Validated configuration object
            
        Raises:
            ValueError: If configuration validation fails
        """
        try:
            # Import configuration models
            from .models import (
                AppConfig, ContentConfig, AnythingLLMConfig, GitHubConfig,
                ScrapingConfig, RedisConfig, AIConfig, OllamaConfig, OpenAIConfig
            )
            
            # Build individual configuration sections with fallback defaults
            app_config = AppConfig(**config_dict.get("app", {}))
            content_config = ContentConfig(**config_dict.get("content", {}))
            anythingllm_config = AnythingLLMConfig(**config_dict.get("anythingllm", {}))
            github_config = GitHubConfig(**config_dict.get("github", {}))
            scraping_config = ScrapingConfig(**config_dict.get("scraping", {}))
            redis_config = RedisConfig(**config_dict.get("redis", {}))
            
            # Build AI configuration with nested providers
            ai_dict = config_dict.get("ai", {})
            ollama_config = OllamaConfig(**ai_dict.get("ollama", {}))
            # Only instantiate OpenAIConfig if openai is enabled/selected
            openai_config = None
            if (
                ai_dict.get("primary_provider") == "openai"
                or ai_dict.get("fallback_provider") == "openai"
            ):
                openai_section = ai_dict.get("openai", {})
                if openai_section:
                    openai_config = OpenAIConfig(**openai_section)
                else:
                    openai_config = OpenAIConfig()
            
            ai_config = AIConfig(
                primary_provider=ai_dict.get("primary_provider", "ollama"),
                fallback_provider=ai_dict.get("fallback_provider", "openai"),
                enable_failover=ai_dict.get("enable_failover", True),
                cache_ttl_seconds=ai_dict.get("cache_ttl_seconds", 3600),
                ollama=ollama_config,
                openai=openai_config,
            )
            
            # Create complete system configuration
            return SystemConfiguration(
                app=app_config,
                content=content_config,
                anythingllm=anythingllm_config,
                github=github_config,
                scraping=scraping_config,
                redis=redis_config,
                ai=ai_config,
            )
            
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise ValueError(f"Invalid configuration structure: {e}")
        except Exception as e:
            logger.error(f"Failed to build configuration: {e}")
            raise ValueError(f"Configuration build error: {e}")
    
    async def _ensure_system_config_table(self) -> None:
        """
        Ensure system_config table exists for database configuration storage
        
        Creates the table if it doesn't exist with proper schema
        """
        if not self._db_manager:
            return
        
        try:
            await self._db_manager.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    config_key TEXT PRIMARY KEY,
                    config_value TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # Create index for active configurations
            await self._db_manager.execute("""
                CREATE INDEX IF NOT EXISTS idx_system_config_active 
                ON system_config(is_active) WHERE is_active = TRUE
            """)
            
            logger.debug("System configuration table ensured")
            
        except Exception as e:
            logger.error(f"Failed to ensure system_config table: {e}")
            raise
    
    async def validate_configuration_sources(self) -> Dict[str, Any]:
        """
        Validate all configuration sources and return status
        
        Returns:
            Dict containing validation status for each source
        """
        validation_result = {
            "database": {"available": False, "entries": 0},
            "yaml_file": {"available": False, "path": self.config_file_path},
            "environment": {"variables": 0}
        }
        
        # Check database availability
        if self._db_manager:
            try:
                rows = await self._db_manager.fetch_all(
                    "SELECT COUNT(*) as count FROM system_config WHERE is_active = :param_0",
                    (True,)
                )
                validation_result["database"]["available"] = True
                validation_result["database"]["entries"] = rows[0].count if rows else 0
            except Exception as e:
                logger.warning(f"Database validation failed: {e}")
        
        # Check YAML file availability
        config_path = Path(self.config_file_path)
        validation_result["yaml_file"]["available"] = config_path.exists()
        
        # Check environment variables
        env_vars = get_environment_overrides()
        validation_result["environment"]["variables"] = len(env_vars)
        
        return validation_result


async def create_configuration_loader(
    config_file_path: str = "config.yaml",
    db_manager: Optional[Any] = None
) -> ConfigurationLoader:
    """
    Factory function to create configured ConfigurationLoader
    
    Args:
        config_file_path: Path to YAML configuration file
        db_manager: Optional DatabaseManager instance
        
    Returns:
        ConfigurationLoader: Configured loader instance
    """
    loader = ConfigurationLoader(config_file_path)
    
    if db_manager:
        await loader.set_database_manager(db_manager)
    
    return loader