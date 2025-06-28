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
    Parse environment variables dynamically to support nested configuration overrides.
    Supports patterns like:
    - APP_DEBUG=true -> app.debug
    - AI_OLLAMA_MODEL=llama3 -> ai.ollama.model
    - REDIS_HOST=redis-server -> redis.host
    """
    overrides = {}

    # Environment variable mapping patterns
    env_patterns = {
        # App configuration
        "APP_ENVIRONMENT": "app.environment",
        "APP_DEBUG": ("app.debug", lambda x: x.lower() == "true"),
        "APP_LOG_LEVEL": "app.log_level",
        "APP_API_PORT": ("app.api_port", int),
        "APP_WEB_PORT": ("app.web_port", int),
        "APP_WORKERS": ("app.workers", int),
        "APP_DATA_DIR": "app.data_dir",
        "DATA_DIR": "app.data_dir",  # Alternative env var name
        # Redis configuration
        "REDIS_HOST": "redis.host",
        "REDIS_PORT": ("redis.port", int),
        "REDIS_PASSWORD": "redis.password",
        "REDIS_DB": ("redis.db", int),
        "REDIS_MAX_CONNECTIONS": ("redis.max_connections", int),
        "REDIS_CONNECTION_TIMEOUT": ("redis.connection_timeout", int),
        "REDIS_SOCKET_TIMEOUT": ("redis.socket_timeout", int),
        "REDIS_MAXMEMORY": "redis.maxmemory",
        "REDIS_MAXMEMORY_POLICY": "redis.maxmemory_policy",
        "REDIS_APPENDONLY": ("redis.appendonly", lambda x: x.lower() == "true"),
        "REDIS_SSL": ("redis.ssl", lambda x: x.lower() == "true"),
        "REDIS_SSL_CERT_REQS": "redis.ssl_cert_reqs",
        # AnythingLLM configuration
        "ANYTHINGLLM_ENDPOINT": "anythingllm.endpoint",
        "ANYTHINGLLM_API_KEY": "anythingllm.api_key",
        # GitHub configuration
        "GITHUB_API_TOKEN": "github.api_token",
        # AI configuration
        "AI_PRIMARY_PROVIDER": "ai.primary_provider",
        "AI_FALLBACK_PROVIDER": "ai.fallback_provider",
        "AI_ENABLE_FAILOVER": ("ai.enable_failover", lambda x: x.lower() == "true"),
        "AI_CACHE_TTL_SECONDS": ("ai.cache_ttl_seconds", int),
        # Ollama configuration
        "AI_OLLAMA_ENDPOINT": "ai.ollama.endpoint",
        "AI_OLLAMA_MODEL": "ai.ollama.model",
        "AI_OLLAMA_TEMPERATURE": ("ai.ollama.temperature", float),
        "AI_OLLAMA_MAX_TOKENS": ("ai.ollama.max_tokens", int),
        "AI_OLLAMA_TIMEOUT": ("ai.ollama.timeout_seconds", int),
        # OpenAI configuration
        "AI_OPENAI_API_KEY": "ai.openai.api_key",
        "AI_OPENAI_MODEL": "ai.openai.model",
        "AI_OPENAI_TEMPERATURE": ("ai.openai.temperature", float),
        "AI_OPENAI_MAX_TOKENS": ("ai.openai.max_tokens", int),
        "AI_OPENAI_TIMEOUT": ("ai.openai.timeout_seconds", int),
        # Content processing configuration
        "CONTENT_CHUNK_SIZE_DEFAULT": ("content.chunk_size_default", int),
        "CONTENT_CHUNK_SIZE_MAX": ("content.chunk_size_max", int),
        "CONTENT_CHUNK_OVERLAP": ("content.chunk_overlap", int),
        "CONTENT_QUALITY_THRESHOLD": ("content.quality_threshold", float),
        "CONTENT_MIN_CONTENT_LENGTH": ("content.min_content_length", int),
        "CONTENT_MAX_CONTENT_LENGTH": ("content.max_content_length", int),
        # Enrichment configuration
        "ENRICHMENT_MAX_CONCURRENT_TASKS": ("enrichment.max_concurrent_tasks", int),
        "ENRICHMENT_TASK_TIMEOUT_SECONDS": ("enrichment.task_timeout_seconds", int),
        "ENRICHMENT_RETRY_DELAY_SECONDS": ("enrichment.retry_delay_seconds", int),
        "ENRICHMENT_QUEUE_POLL_INTERVAL": ("enrichment.queue_poll_interval", int),
        "ENRICHMENT_BATCH_SIZE": ("enrichment.batch_size", int),
        "ENRICHMENT_ENABLE_RELATIONSHIP_MAPPING": (
            "enrichment.enable_relationship_mapping",
            lambda x: x.lower() == "true",
        ),
        "ENRICHMENT_ENABLE_TAG_GENERATION": (
            "enrichment.enable_tag_generation",
            lambda x: x.lower() == "true",
        ),
        "ENRICHMENT_ENABLE_QUALITY_ASSESSMENT": (
            "enrichment.enable_quality_assessment",
            lambda x: x.lower() == "true",
        ),
        "ENRICHMENT_MIN_CONFIDENCE_THRESHOLD": (
            "enrichment.min_confidence_threshold",
            float,
        ),
    }

    # Process environment variables that are actually set
    for env_var, mapping in env_patterns.items():
        value = os.getenv(env_var)
        if value is not None:
            try:
                if isinstance(mapping, tuple):
                    config_key, converter = mapping
                    converted_value = converter(value)
                else:
                    config_key = mapping
                    converted_value = value

                overrides[config_key] = converted_value
                logger.debug(
                    f"Environment override: {env_var} -> {config_key} = {converted_value}"
                )

            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Failed to convert environment variable {env_var}={value}: {e}"
                )

    return overrides


def apply_nested_override(config_dict: Dict[str, Any], key: str, value: Any) -> None:
    """Apply a nested configuration override using dot notation"""
    keys = key.split(".")
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

    # Only require OpenAI API key if OpenAI is selected as provider
    if primary_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        missing_vars["OPENAI_API_KEY"] = "Required when OpenAI is primary provider"

    if fallback_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        missing_vars["OPENAI_API_KEY"] = "Required when OpenAI is fallback provider"

    return missing_vars
