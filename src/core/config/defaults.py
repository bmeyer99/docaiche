"""
Configuration Defaults and Environment Mapping - PRD-003
Environment variable parsing and nested configuration support

Implements hierarchical configuration loading with support for nested keys
through environment variables using dot notation.
"""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_environment_overrides() -> Dict[str, Any]:
    """
    Map environment variables to configuration fields.
    Follows the naming convention: COMPONENT_FIELD_NAME
    """
    env_mappings = {
        # App configuration
        "app.environment": os.getenv("APP_ENVIRONMENT", "production"),
        "app.debug": os.getenv("APP_DEBUG", "false").lower() == "true",
        "app.log_level": os.getenv("APP_LOG_LEVEL", "INFO"),
        "app.api_port": int(os.getenv("APP_API_PORT", "8080")),
        "app.web_port": int(os.getenv("APP_WEB_PORT", "8081")),
        "app.workers": int(os.getenv("APP_WORKERS", "4")),
        
        # Redis configuration
        "redis.host": os.getenv("REDIS_HOST", "redis"),
        "redis.port": int(os.getenv("REDIS_PORT", "6379")),
        "redis.password": os.getenv("REDIS_PASSWORD"),
        "redis.db": int(os.getenv("REDIS_DB", "0")),
        "redis.max_connections": int(os.getenv("REDIS_MAX_CONNECTIONS", "20")),
        "redis.maxmemory": os.getenv("REDIS_MAXMEMORY", "512mb"),
        "redis.ssl": os.getenv("REDIS_SSL", "false").lower() == "true",
        
        # AnythingLLM configuration
        "anythingllm.endpoint": os.getenv("ANYTHINGLLM_ENDPOINT", "http://anythingllm:3001"),
        "anythingllm.api_key": os.getenv("ANYTHINGLLM_API_KEY", "development-key"),
        
        # GitHub configuration
        "github.api_token": os.getenv("GITHUB_API_TOKEN", "development-token"),
        
        # AI configuration
        "ai.primary_provider": os.getenv("AI_PRIMARY_PROVIDER", "ollama"),
        "ai.enable_failover": os.getenv("AI_ENABLE_FAILOVER", "true").lower() == "true",
        
        # Ollama configuration
        "ai.ollama.endpoint": os.getenv("OLLAMA_ENDPOINT", "http://ollama:11434"),
        "ai.ollama.model": os.getenv("OLLAMA_MODEL", "llama2"),
        "ai.ollama.temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
        
        # OpenAI configuration
        "ai.openai.api_key": os.getenv("OPENAI_API_KEY", "development-key"),
        "ai.openai.model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        "ai.openai.temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.7")),
        
        # Content processing configuration
        "content.chunk_size_default": int(os.getenv("CONTENT_CHUNK_SIZE_DEFAULT", "1000")),
        "content.chunk_size_max": int(os.getenv("CONTENT_CHUNK_SIZE_MAX", "4000")),
        "content.quality_threshold": float(os.getenv("CONTENT_QUALITY_THRESHOLD", "0.3")),
    }
    
    # Filter out None values
    return {k: v for k, v in env_mappings.items() if v is not None}


def apply_nested_override(config_dict: Dict[str, Any], key: str, value: Any) -> None:
    """Apply a nested configuration override using dot notation"""
    keys = key.split('.')
    current = config_dict
    
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]
    
    current[keys[-1]] = value


def get_default_configuration_dict() -> Dict[str, Any]:
    """
    Generate default configuration dictionary with proper structure
    
    Returns:
        Dict containing default configuration values for all components
    """
    # Start with environment overrides
    env_overrides = get_environment_overrides()
    
    # Build configuration dictionary
    config_dict = {}
    
    # Apply all environment overrides using nested key notation
    for key, value in env_overrides.items():
        apply_nested_override(config_dict, key, value)
    
    logger.info("Default configuration generated with environment overrides")
    return config_dict


def validate_environment_variables() -> Dict[str, str]:
    """
    Validate required environment variables are present
    
    Returns:
        Dict of missing required environment variables with descriptions
    """
    missing_vars = {}
    
    # Check critical environment variables
    if not os.getenv("ANYTHINGLLM_API_KEY"):
        missing_vars["ANYTHINGLLM_API_KEY"] = "Required for AnythingLLM integration"
    
    if not os.getenv("GITHUB_API_TOKEN"):
        missing_vars["GITHUB_API_TOKEN"] = "Required for GitHub repository access"
    
    # Check AI provider configuration
    primary_provider = os.getenv("AI_PRIMARY_PROVIDER", "ollama")
    fallback_provider = os.getenv("AI_FALLBACK_PROVIDER")
    
    if primary_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        missing_vars["OPENAI_API_KEY"] = "Required when OpenAI is primary provider"
    
    if fallback_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        missing_vars["OPENAI_API_KEY"] = "Required when OpenAI is fallback provider"
    
    return missing_vars