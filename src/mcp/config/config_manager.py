"""
Configuration Manager for MCP Server
===================================

Centralized configuration management with environment-aware settings,
dynamic reloading, validation, and deployment integration.
"""

import os
import json
import yaml
import logging
from typing import Dict, Any, Optional, List, Union, Set
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
import asyncio
from enum import Enum
import hashlib

from ..exceptions import ConfigurationError, ValidationError
from ..security.validator import SecurityValidator, ValidationLevel

logger = logging.getLogger(__name__)


class ConfigSource(Enum):
    """Configuration source types."""
    FILE = "file"
    ENVIRONMENT = "environment"
    REMOTE = "remote"
    DEFAULT = "default"


class ConfigFormat(Enum):
    """Supported configuration formats."""
    JSON = "json"
    YAML = "yaml"
    ENV = "env"


@dataclass
class ConfigValue:
    """Configuration value with metadata."""
    key: str
    value: Any
    source: ConfigSource
    timestamp: datetime
    version: Optional[str] = None
    checksum: Optional[str] = None
    
    def calculate_checksum(self) -> str:
        """Calculate checksum of value."""
        value_str = json.dumps(self.value, sort_keys=True)
        return hashlib.sha256(value_str.encode()).hexdigest()


class ConfigurationManager:
    """
    Centralized configuration management for MCP server.
    
    Features:
    - Multi-source configuration (files, env vars, remote)
    - Environment-aware settings (dev, staging, prod)
    - Dynamic configuration reloading
    - Configuration validation and type checking
    - Secret management with encryption
    - Audit trail for configuration changes
    """
    
    def __init__(
        self,
        base_path: str = "config",
        environment: str = "development",
        auto_reload: bool = False,
        reload_interval: int = 60
    ):
        self.base_path = Path(base_path)
        self.environment = environment
        self.auto_reload = auto_reload
        self.reload_interval = reload_interval
        
        # Configuration storage
        self._config: Dict[str, ConfigValue] = {}
        self._config_lock = asyncio.Lock()
        
        # Watchers and validators
        self._change_callbacks: List[callable] = []
        self._validators: Dict[str, callable] = {}
        self._security_validator = SecurityValidator(ValidationLevel.STRICT)
        
        # File tracking for reloading
        self._loaded_files: Dict[str, float] = {}  # file -> mtime
        self._reload_task: Optional[asyncio.Task] = None
        
        # Configuration schema
        self._schema: Dict[str, Any] = {}
        
        # Secrets handling
        self._secret_keys: Set[str] = {
            "oauth_client_secret",
            "jwt_secret",
            "api_key",
            "database_password",
            "encryption_key"
        }
        
        logger.info(f"Configuration manager initialized for environment: {environment}")
    
    async def initialize(self) -> None:
        """Initialize configuration manager and load configurations."""
        # Create config directory if needed
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Load configuration in order of precedence
        await self._load_defaults()
        await self._load_environment_config()
        await self._load_file_configs()
        await self._load_env_vars()
        
        # Validate configuration
        await self._validate_configuration()
        
        # Start auto-reload if enabled
        if self.auto_reload:
            self._reload_task = asyncio.create_task(self._reload_loop())
        
        logger.info(f"Configuration loaded: {len(self._config)} settings")
    
    async def close(self) -> None:
        """Close configuration manager and cleanup."""
        if self._reload_task:
            self._reload_task.cancel()
            try:
                await self._reload_task
            except asyncio.CancelledError:
                pass
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        # Handle nested keys
        if '.' in key:
            parts = key.split('.')
            value = self._config.get(parts[0])
            if value:
                result = value.value
                for part in parts[1:]:
                    if isinstance(result, dict):
                        result = result.get(part)
                    else:
                        return default
                return result if result is not None else default
            return default
        
        # Direct key lookup
        config_value = self._config.get(key)
        return config_value.value if config_value else default
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return {
            key: value.value
            for key, value in self._config.items()
        }
    
    async def set(
        self,
        key: str,
        value: Any,
        source: ConfigSource = ConfigSource.REMOTE,
        persist: bool = False
    ) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
            source: Source of configuration
            persist: Whether to persist to file
        """
        # Validate value
        if key in self._validators:
            if not await self._validators[key](value):
                raise ValidationError(f"Invalid value for {key}")
        
        # Security validation for sensitive keys
        if any(secret in key.lower() for secret in ['key', 'secret', 'password']):
            validation_result = await self._security_validator.validate_input(
                str(value),
                input_type="identifier"
            )
            if not validation_result.is_valid:
                raise ValidationError(f"Security validation failed for {key}")
        
        # Create config value
        config_value = ConfigValue(
            key=key,
            value=value,
            source=source,
            timestamp=datetime.utcnow()
        )
        config_value.checksum = config_value.calculate_checksum()
        
        # Store value
        async with self._config_lock:
            old_value = self._config.get(key)
            self._config[key] = config_value
            
            # Notify callbacks
            await self._notify_change(key, old_value, config_value)
        
        # Persist if requested
        if persist:
            await self._persist_config(key, value)
        
        logger.info(f"Configuration updated: {key} (source: {source.value})")
    
    def register_validator(self, key: str, validator: callable) -> None:
        """Register a validator for a configuration key."""
        self._validators[key] = validator
    
    def register_change_callback(self, callback: callable) -> None:
        """Register a callback for configuration changes."""
        self._change_callbacks.append(callback)
    
    def is_secret(self, key: str) -> bool:
        """Check if a configuration key is a secret."""
        return any(secret in key.lower() for secret in self._secret_keys)
    
    async def reload(self) -> None:
        """Reload configuration from all sources."""
        logger.info("Reloading configuration...")
        
        # Track changes
        changes = []
        
        # Reload file configs
        for file_path, old_mtime in self._loaded_files.items():
            path = Path(file_path)
            if path.exists():
                new_mtime = path.stat().st_mtime
                if new_mtime > old_mtime:
                    await self._load_config_file(path)
                    self._loaded_files[file_path] = new_mtime
                    changes.append(file_path)
        
        # Reload environment variables
        await self._load_env_vars()
        
        # Validate configuration
        await self._validate_configuration()
        
        if changes:
            logger.info(f"Configuration reloaded from: {changes}")
    
    async def export_config(
        self,
        format: ConfigFormat = ConfigFormat.JSON,
        include_secrets: bool = False
    ) -> str:
        """
        Export configuration to string.
        
        Args:
            format: Export format
            include_secrets: Whether to include secret values
            
        Returns:
            Configuration as string
        """
        config_dict = {}
        
        for key, config_value in self._config.items():
            value = config_value.value
            
            # Mask secrets if needed
            if not include_secrets and self.is_secret(key):
                value = "***REDACTED***"
            
            config_dict[key] = {
                "value": value,
                "source": config_value.source.value,
                "timestamp": config_value.timestamp.isoformat()
            }
        
        if format == ConfigFormat.JSON:
            return json.dumps(config_dict, indent=2)
        elif format == ConfigFormat.YAML:
            return yaml.dump(config_dict, default_flow_style=False)
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    async def validate_deployment_config(self) -> Dict[str, Any]:
        """
        Validate configuration for deployment readiness.
        
        Returns:
            Validation report
        """
        report = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "environment": self.environment,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Check required settings
        required_keys = {
            "server_host",
            "server_port",
            "database_url",
            "redis_url",
            "log_level"
        }
        
        for key in required_keys:
            if not self.get(key):
                report["errors"].append(f"Missing required configuration: {key}")
                report["valid"] = False
        
        # Check production settings
        if self.environment == "production":
            # Security settings
            if not self.get("ssl_enabled", False):
                report["warnings"].append("SSL is not enabled for production")
            
            if self.get("debug_mode", False):
                report["errors"].append("Debug mode enabled in production")
                report["valid"] = False
            
            # Authentication
            if not self.get("require_authentication", True):
                report["errors"].append("Authentication not required in production")
                report["valid"] = False
            
            # Secrets
            for secret_key in self._secret_keys:
                value = self.get(secret_key)
                if value and value == "changeme":
                    report["errors"].append(f"Default secret used for: {secret_key}")
                    report["valid"] = False
        
        return report
    
    # Private methods
    
    async def _load_defaults(self) -> None:
        """Load default configuration values."""
        defaults = {
            "server_host": "0.0.0.0",
            "server_port": 8080,
            "log_level": "INFO",
            "max_connections": 100,
            "request_timeout": 30,
            "rate_limit_enabled": True,
            "rate_limit_requests": 60,
            "cache_enabled": True,
            "cache_ttl": 3600
        }
        
        for key, value in defaults.items():
            if key not in self._config:
                await self.set(key, value, ConfigSource.DEFAULT)
    
    async def _load_environment_config(self) -> None:
        """Load environment-specific configuration."""
        env_file = self.base_path / f"{self.environment}.yaml"
        if env_file.exists():
            await self._load_config_file(env_file)
    
    async def _load_file_configs(self) -> None:
        """Load all configuration files."""
        # Load base config
        base_config = self.base_path / "config.yaml"
        if base_config.exists():
            await self._load_config_file(base_config)
        
        # Load additional configs
        for config_file in self.base_path.glob("*.yaml"):
            if config_file.name not in ["config.yaml", f"{self.environment}.yaml"]:
                await self._load_config_file(config_file)
    
    async def _load_config_file(self, file_path: Path) -> None:
        """Load configuration from file."""
        try:
            with open(file_path, 'r') as f:
                if file_path.suffix == '.yaml':
                    data = yaml.safe_load(f)
                elif file_path.suffix == '.json':
                    data = json.load(f)
                else:
                    return
            
            if data:
                for key, value in self._flatten_dict(data).items():
                    await self.set(key, value, ConfigSource.FILE)
            
            # Track file for reloading
            self._loaded_files[str(file_path)] = file_path.stat().st_mtime
            
            logger.info(f"Loaded configuration from: {file_path}")
            
        except Exception as e:
            logger.error(f"Error loading config file {file_path}: {e}")
    
    async def _load_env_vars(self) -> None:
        """Load configuration from environment variables."""
        prefix = "MCP_"
        
        for env_key, env_value in os.environ.items():
            if env_key.startswith(prefix):
                # Convert env var to config key
                config_key = env_key[len(prefix):].lower()
                
                # Parse value
                try:
                    # Try to parse as JSON for complex types
                    value = json.loads(env_value)
                except:
                    # Use as string
                    value = env_value
                
                await self.set(config_key, value, ConfigSource.ENVIRONMENT)
    
    async def _validate_configuration(self) -> None:
        """Validate entire configuration."""
        errors = []
        
        # Type validation
        type_checks = {
            "server_port": int,
            "max_connections": int,
            "request_timeout": (int, float),
            "rate_limit_enabled": bool,
            "cache_enabled": bool
        }
        
        for key, expected_type in type_checks.items():
            value = self.get(key)
            if value is not None and not isinstance(value, expected_type):
                errors.append(f"{key} must be of type {expected_type}")
        
        # Range validation
        if self.get("server_port", 0) < 1 or self.get("server_port", 0) > 65535:
            errors.append("server_port must be between 1 and 65535")
        
        if self.get("max_connections", 0) < 1:
            errors.append("max_connections must be positive")
        
        if errors:
            raise ConfigurationError(f"Configuration validation failed: {errors}")
    
    async def _persist_config(self, key: str, value: Any) -> None:
        """Persist configuration to file."""
        persist_file = self.base_path / f"{self.environment}_override.yaml"
        
        # Load existing overrides
        overrides = {}
        if persist_file.exists():
            with open(persist_file, 'r') as f:
                overrides = yaml.safe_load(f) or {}
        
        # Update with new value
        overrides[key] = value
        
        # Write back
        with open(persist_file, 'w') as f:
            yaml.dump(overrides, f, default_flow_style=False)
        
        logger.info(f"Persisted configuration: {key} to {persist_file}")
    
    async def _notify_change(
        self,
        key: str,
        old_value: Optional[ConfigValue],
        new_value: ConfigValue
    ) -> None:
        """Notify callbacks of configuration change."""
        for callback in self._change_callbacks:
            try:
                await callback(key, old_value, new_value)
            except Exception as e:
                logger.error(f"Error in config change callback: {e}")
    
    async def _reload_loop(self) -> None:
        """Background task for auto-reloading configuration."""
        while True:
            try:
                await asyncio.sleep(self.reload_interval)
                await self.reload()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in reload loop: {e}")
    
    def _flatten_dict(self, d: dict, parent_key: str = '') -> dict:
        """Flatten nested dictionary with dot notation."""
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}.{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key).items())
            else:
                items.append((new_key, v))
        return dict(items)