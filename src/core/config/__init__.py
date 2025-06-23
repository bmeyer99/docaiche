"""
Configuration Management System - PRD-003
Entry point for all configuration models and utilities

This module provides the complete Pydantic configuration schema for the AI Documentation Cache System.
All configuration models follow PRD-003 specifications exactly.
"""

from .models import (
    # Base configurations
    AppConfig,
    CircuitBreakerConfig,
    
    # Content processing
    ContentConfig,
    
    # External services
    AnythingLLMConfig,
    GitHubConfig,
    ScrapingConfig,
    
    # Database and caching
    RedisConfig,
    
    # AI providers
    OllamaConfig,
    OpenAIConfig,
    AIConfig,
    
    # Top-level configuration
    SystemConfiguration,
)

from .validation import ConfigurationValidators
from .defaults import get_environment_overrides, apply_nested_override
from .secrets import SecretsManager

# Configuration functions - implemented directly in this package
import logging
import os
from typing import Optional, Dict, Any
from pydantic import ValidationError

logger = logging.getLogger(__name__)

# Global configuration instance
_system_config: Optional[SystemConfiguration] = None

def get_system_configuration() -> SystemConfiguration:
    """
    Get the comprehensive system configuration from CFG-001.
    
    This is the primary configuration interface for all components.
    
    Returns:
        SystemConfiguration: Complete system configuration
        
    Raises:
        ValueError: If required configuration is missing or invalid
    """
    global _system_config
    if _system_config is None:
        try:
            # Build configuration from environment overrides and defaults
            from .defaults import get_default_configuration_dict
            config_dict = get_default_configuration_dict()
            
            # Ensure we have the basic structure even if no env vars are set
            if not config_dict:
                config_dict = _build_default_config_dict()
            
            # Build the comprehensive configuration
            _system_config = _build_system_configuration(config_dict)
            
            # Validate production secrets if in production
            if _system_config.app.environment == "production":
                SecretsManager.validate_production_secrets(_system_config)
            
            logger.info(f"System configuration loaded successfully for environment: {_system_config.app.environment}")
            
        except Exception as e:
            logger.error(f"Failed to load system configuration: {e}")
            raise ValueError(f"Configuration initialization failed: {e}")
    
    return _system_config

def _build_default_config_dict() -> Dict[str, Any]:
    """Build default configuration dictionary with fallback values"""
    return {
        "app": {
            "version": "1.0.0",
            "environment": os.getenv("APP_ENVIRONMENT", "development"),
            "debug": os.getenv("APP_DEBUG", "true").lower() == "true",
            "log_level": os.getenv("APP_LOG_LEVEL", "INFO"),
            "data_dir": os.getenv("APP_DATA_DIR", "/app/data"),
            "api_host": os.getenv("APP_API_HOST", "0.0.0.0"),
            "api_port": int(os.getenv("APP_API_PORT", "8080")),
            "web_port": int(os.getenv("APP_WEB_PORT", "8081")),
            "workers": int(os.getenv("APP_WORKERS", "4")),
        },
        "content": {
            "chunk_size_default": int(os.getenv("CONTENT_CHUNK_SIZE_DEFAULT", "1000")),
            "chunk_size_max": int(os.getenv("CONTENT_CHUNK_SIZE_MAX", "4000")),
            "chunk_overlap": int(os.getenv("CONTENT_CHUNK_OVERLAP", "100")),
            "quality_threshold": float(os.getenv("CONTENT_QUALITY_THRESHOLD", "0.3")),
            "min_content_length": int(os.getenv("CONTENT_MIN_LENGTH", "50")),
            "max_content_length": int(os.getenv("CONTENT_MAX_LENGTH", "1000000")),
        },
        "anythingllm": {
            "endpoint": os.getenv("ANYTHINGLLM_ENDPOINT", "http://anythingllm:3001"),
            "api_key": os.getenv("ANYTHINGLLM_API_KEY", "development-key"),
        },
        "github": {
            "api_token": os.getenv("GITHUB_API_TOKEN", "development-token"),
        },
        "scraping": {
            "user_agent": os.getenv("SCRAPING_USER_AGENT", "DocaicheBot/1.0"),
            "rate_limit_delay": float(os.getenv("SCRAPING_RATE_LIMIT_DELAY", "1.0")),
        },
        "redis": {
            "host": os.getenv("REDIS_HOST", "redis"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "password": os.getenv("REDIS_PASSWORD"),
            "db": int(os.getenv("REDIS_DB", "0")),
            "max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "20")),
            "connection_timeout": int(os.getenv("REDIS_CONNECTION_TIMEOUT", "5")),
            "socket_timeout": int(os.getenv("REDIS_SOCKET_TIMEOUT", "5")),
            "maxmemory": os.getenv("REDIS_MAXMEMORY", "512mb"),
            "maxmemory_policy": os.getenv("REDIS_MAXMEMORY_POLICY", "allkeys-lru"),
            "appendonly": os.getenv("REDIS_APPENDONLY", "true").lower() == "true",
            "ssl": os.getenv("REDIS_SSL", "false").lower() == "true",
        },
        "ai": {
            "primary_provider": os.getenv("AI_PRIMARY_PROVIDER", "ollama"),
            "fallback_provider": os.getenv("AI_FALLBACK_PROVIDER", "openai"),
            "enable_failover": os.getenv("AI_ENABLE_FAILOVER", "true").lower() == "true",
            "cache_ttl_seconds": int(os.getenv("AI_CACHE_TTL_SECONDS", "3600")),
            "ollama": {
                "endpoint": os.getenv("OLLAMA_ENDPOINT", "http://ollama:11434"),
                "model": os.getenv("OLLAMA_MODEL", "llama2"),
                "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
                "max_tokens": int(os.getenv("OLLAMA_MAX_TOKENS", "4096")),
                "timeout_seconds": int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60")),
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
                "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
                "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "4096")),
                "timeout_seconds": int(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
            },
        },
        "enrichment": {
            "max_concurrent_tasks": int(os.getenv("ENRICHMENT_MAX_CONCURRENT_TASKS", "5")),
            "task_timeout_seconds": int(os.getenv("ENRICHMENT_TASK_TIMEOUT_SECONDS", "300")),
            "retry_delay_seconds": int(os.getenv("ENRICHMENT_RETRY_DELAY_SECONDS", "60")),
            "queue_poll_interval": int(os.getenv("ENRICHMENT_QUEUE_POLL_INTERVAL", "10")),
            "batch_size": int(os.getenv("ENRICHMENT_BATCH_SIZE", "10")),
            "enable_relationship_mapping": os.getenv("ENRICHMENT_ENABLE_RELATIONSHIP_MAPPING", "true").lower() == "true",
            "enable_tag_generation": os.getenv("ENRICHMENT_ENABLE_TAG_GENERATION", "true").lower() == "true",
            "enable_quality_assessment": os.getenv("ENRICHMENT_ENABLE_QUALITY_ASSESSMENT", "true").lower() == "true",
            "min_confidence_threshold": float(os.getenv("ENRICHMENT_MIN_CONFIDENCE_THRESHOLD", "0.7")),
        },
    }

def _build_system_configuration(config_dict: Dict[str, Any]) -> SystemConfiguration:
    """
    Build SystemConfiguration from config dictionary
    
    Args:
        config_dict: Configuration dictionary with nested structure
        
    Returns:
        SystemConfiguration: Validated system configuration
        
    Raises:
        ValidationError: If configuration validation fails
    """
    try:
        # Extract and validate each configuration section
        app_config = AppConfig(**config_dict.get("app", {}))
        content_config = ContentConfig(**config_dict.get("content", {}))
        
        # Build AnythingLLM config
        anythingllm_dict = config_dict.get("anythingllm", {})
        anythingllm_config = AnythingLLMConfig(**anythingllm_dict)
        
        # Build GitHub config
        github_dict = config_dict.get("github", {})
        github_config = GitHubConfig(**github_dict)
        
        # Build scraping config
        scraping_dict = config_dict.get("scraping", {})
        scraping_config = ScrapingConfig(**scraping_dict)
        
        # Build Redis config
        redis_dict = config_dict.get("redis", {})
        redis_config = RedisConfig(**redis_dict)
        
        # Build AI config with nested providers
        ai_dict = config_dict.get("ai", {})
        ollama_config = OllamaConfig(**ai_dict.get("ollama", {}))
        openai_config = OpenAIConfig(**ai_dict.get("openai", {}))
        
        # Extract AI top-level config
        ai_config = AIConfig(
            primary_provider=ai_dict.get("primary_provider", "ollama"),
            fallback_provider=ai_dict.get("fallback_provider", "openai"),
            enable_failover=ai_dict.get("enable_failover", True),
            cache_ttl_seconds=ai_dict.get("cache_ttl_seconds", 3600),
            ollama=ollama_config,
            openai=openai_config,
        )
        
        # Build enrichment config
        enrichment_dict = config_dict.get("enrichment", {})
        from .models import EnrichmentConfig
        enrichment_config = EnrichmentConfig(**enrichment_dict)
        
        # Build complete system configuration
        system_config = SystemConfiguration(
            app=app_config,
            content=content_config,
            anythingllm=anythingllm_config,
            github=github_config,
            scraping=scraping_config,
            redis=redis_config,
            ai=ai_config,
            enrichment=enrichment_config,
        )
        
        logger.info("System configuration built and validated successfully")
        return system_config
        
    except ValidationError as e:
        logger.error(f"Configuration validation failed: {e}")
        raise ValueError(f"Invalid configuration: {e}")

def reload_configuration() -> SystemConfiguration:
    """
    Reload system configuration from environment.
    
    This clears the cached configuration and rebuilds it from current environment variables.
    
    Returns:
        SystemConfiguration: The reloaded system configuration
    """
    global _system_config
    _system_config = None
    logger.info("Configuration cache cleared, reloading...")
    return get_system_configuration()

def validate_configuration() -> Dict[str, Any]:
    """
    Validate current configuration and return status information.
    
    Returns:
        Dict containing validation status and any issues found
    """
    try:
        config = get_system_configuration()
        
        validation_status = {
            "valid": True,
            "environment": config.app.environment,
            "issues": [],
            "warnings": [],
        }
        
        # Check for missing required secrets in production
        if config.app.environment == "production":
            try:
                SecretsManager.validate_production_secrets(config)
            except ValueError as e:
                validation_status["issues"].append(str(e))
                validation_status["valid"] = False
        
        # Check Redis connection details
        if not config.redis.host:
            validation_status["issues"].append("Redis host not configured")
            validation_status["valid"] = False
        
        # Check AI provider configuration
        if config.ai.primary_provider == "openai" and not config.ai.openai.api_key:
            validation_status["issues"].append("OpenAI API key required when set as primary provider")
            validation_status["valid"] = False
        
        # Add warnings for non-critical issues
        if not config.redis.password and config.app.environment == "production":
            validation_status["warnings"].append("Redis password not set in production")
        
        return validation_status
        
    except Exception as e:
        return {
            "valid": False,
            "environment": "unknown",
            "issues": [f"Configuration load failed: {e}"],
            "warnings": [],
        }

# Convenience functions for common configuration access
def get_api_host() -> str:
    """Get API host from configuration"""
    return get_system_configuration().app.api_host

def get_api_port() -> int:
    """Get API port from configuration"""
    return get_system_configuration().app.api_port

def get_log_level() -> str:
    """Get log level from configuration"""
    return get_system_configuration().app.log_level

def is_debug_mode() -> bool:
    """Check if debug mode is enabled"""
    return get_system_configuration().app.debug

def get_environment() -> str:
    """Get current environment"""
    return get_system_configuration().app.environment

# Compatibility function for FastAPI integration
def get_settings() -> SystemConfiguration:
    """
    Compatibility function for existing FastAPI integration.
    Returns the same SystemConfiguration object as get_system_configuration().
    """
    return get_system_configuration()

__all__ = [
    "AppConfig",
    "CircuitBreakerConfig",
    "ContentConfig",
    "AnythingLLMConfig",
    "GitHubConfig",
    "ScrapingConfig",
    "RedisConfig",
    "OllamaConfig",
    "OpenAIConfig",
    "AIConfig",
    "SystemConfiguration",
    "ConfigurationValidators",
    "get_environment_overrides",
    "apply_nested_override",
    "SecretsManager",
    "get_system_configuration",
    "validate_configuration",
    "reload_configuration",
    "get_api_host",
    "get_api_port",
    "get_log_level",
    "is_debug_mode",
    "get_environment",
    "get_settings",  # Compatibility function
]