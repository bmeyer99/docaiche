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
        # Weaviate configuration
        "WEAVIATE_ENDPOINT": "weaviate.endpoint",
        "WEAVIATE_API_KEY": "weaviate.api_key",
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
        # Context7 configuration
        "CONTEXT7_ENABLED": ("context7.enabled", lambda x: x.lower() == "true"),
        
        # Context7 TTL configuration
        "CONTEXT7_TTL_DEFAULT_DAYS": ("context7.ttl.default_days", int),
        "CONTEXT7_TTL_MIN_DAYS": ("context7.ttl.min_days", int),
        "CONTEXT7_TTL_MAX_DAYS": ("context7.ttl.max_days", int),
        "CONTEXT7_TTL_ENABLE_TECH_MULTIPLIERS": ("context7.ttl.enable_tech_multipliers", lambda x: x.lower() == "true"),
        "CONTEXT7_TTL_ENABLE_DOC_TYPE_ADJUSTMENTS": ("context7.ttl.enable_doc_type_adjustments", lambda x: x.lower() == "true"),
        "CONTEXT7_TTL_ENABLE_FRESHNESS_BOOST": ("context7.ttl.enable_freshness_boost", lambda x: x.lower() == "true"),
        "CONTEXT7_TTL_ENABLE_POPULARITY_BOOST": ("context7.ttl.enable_popularity_boost", lambda x: x.lower() == "true"),
        "CONTEXT7_TTL_FRESHNESS_BOOST_DAYS": ("context7.ttl.freshness_boost_days", int),
        "CONTEXT7_TTL_FRESHNESS_BOOST_MULTIPLIER": ("context7.ttl.freshness_boost_multiplier", float),
        "CONTEXT7_TTL_POPULARITY_THRESHOLD": ("context7.ttl.popularity_threshold", int),
        "CONTEXT7_TTL_POPULARITY_BOOST_MULTIPLIER": ("context7.ttl.popularity_boost_multiplier", float),
        
        # Context7 TTL Technology Multipliers (common ones)
        "CONTEXT7_TTL_TECH_REACT_MULTIPLIER": ("context7.ttl.tech_multipliers.react", float),
        "CONTEXT7_TTL_TECH_VUE_MULTIPLIER": ("context7.ttl.tech_multipliers.vue", float),
        "CONTEXT7_TTL_TECH_ANGULAR_MULTIPLIER": ("context7.ttl.tech_multipliers.angular", float),
        "CONTEXT7_TTL_TECH_PYTHON_MULTIPLIER": ("context7.ttl.tech_multipliers.python", float),
        "CONTEXT7_TTL_TECH_JAVASCRIPT_MULTIPLIER": ("context7.ttl.tech_multipliers.javascript", float),
        "CONTEXT7_TTL_TECH_TYPESCRIPT_MULTIPLIER": ("context7.ttl.tech_multipliers.typescript", float),
        "CONTEXT7_TTL_TECH_DOCKER_MULTIPLIER": ("context7.ttl.tech_multipliers.docker", float),
        "CONTEXT7_TTL_TECH_KUBERNETES_MULTIPLIER": ("context7.ttl.tech_multipliers.kubernetes", float),
        "CONTEXT7_TTL_TECH_AWS_MULTIPLIER": ("context7.ttl.tech_multipliers.aws", float),
        "CONTEXT7_TTL_TECH_NODE_MULTIPLIER": ("context7.ttl.tech_multipliers.node", float),
        
        # Context7 TTL Document Type Adjustments
        "CONTEXT7_TTL_DOC_API_ADJUSTMENT": ("context7.ttl.doc_type_adjustments.api", float),
        "CONTEXT7_TTL_DOC_TUTORIAL_ADJUSTMENT": ("context7.ttl.doc_type_adjustments.tutorial", float),
        "CONTEXT7_TTL_DOC_GUIDE_ADJUSTMENT": ("context7.ttl.doc_type_adjustments.guide", float),
        "CONTEXT7_TTL_DOC_REFERENCE_ADJUSTMENT": ("context7.ttl.doc_type_adjustments.reference", float),
        "CONTEXT7_TTL_DOC_CHANGELOG_ADJUSTMENT": ("context7.ttl.doc_type_adjustments.changelog", float),
        "CONTEXT7_TTL_DOC_BLOG_ADJUSTMENT": ("context7.ttl.doc_type_adjustments.blog", float),
        "CONTEXT7_TTL_DOC_NEWS_ADJUSTMENT": ("context7.ttl.doc_type_adjustments.news", float),
        
        # Context7 Ingestion configuration
        "CONTEXT7_INGESTION_BATCH_SIZE": ("context7.ingestion.batch_size", int),
        "CONTEXT7_INGESTION_MAX_CONCURRENT_BATCHES": ("context7.ingestion.max_concurrent_batches", int),
        "CONTEXT7_INGESTION_TIMEOUT_SECONDS": ("context7.ingestion.ingestion_timeout_seconds", int),
        "CONTEXT7_INGESTION_RETRY_ATTEMPTS": ("context7.ingestion.retry_attempts", int),
        "CONTEXT7_INGESTION_RETRY_DELAY_SECONDS": ("context7.ingestion.retry_delay_seconds", int),
        "CONTEXT7_INGESTION_SYNC_ENABLED": ("context7.ingestion.sync_enabled", lambda x: x.lower() == "true"),
        "CONTEXT7_INGESTION_SYNC_TIMEOUT_SECONDS": ("context7.ingestion.sync_timeout_seconds", int),
        "CONTEXT7_INGESTION_SYNC_BATCH_SIZE": ("context7.ingestion.sync_batch_size", int),
        "CONTEXT7_INGESTION_ENABLE_SMART_PIPELINE": ("context7.ingestion.enable_smart_pipeline", lambda x: x.lower() == "true"),
        "CONTEXT7_INGESTION_ENABLE_CONTENT_VALIDATION": ("context7.ingestion.enable_content_validation", lambda x: x.lower() == "true"),
        "CONTEXT7_INGESTION_ENABLE_DUPLICATE_DETECTION": ("context7.ingestion.enable_duplicate_detection", lambda x: x.lower() == "true"),
        "CONTEXT7_INGESTION_FALLBACK_STORAGE_ENABLED": ("context7.ingestion.fallback_storage_enabled", lambda x: x.lower() == "true"),
        "CONTEXT7_INGESTION_MAX_FALLBACK_ITEMS": ("context7.ingestion.max_fallback_items", int),
        "CONTEXT7_INGESTION_FALLBACK_CLEANUP_DAYS": ("context7.ingestion.fallback_cleanup_days", int),
        
        # Context7 Cache configuration
        "CONTEXT7_CACHE_ENABLED": ("context7.cache.enabled", lambda x: x.lower() == "true"),
        "CONTEXT7_CACHE_TTL_MULTIPLIER": ("context7.cache.ttl_multiplier", float),
        "CONTEXT7_CACHE_MAX_CACHE_SIZE": ("context7.cache.max_cache_size", int),
        "CONTEXT7_CACHE_EVICTION_POLICY": ("context7.cache.eviction_policy", str),
        "CONTEXT7_CACHE_CLEANUP_INTERVAL_SECONDS": ("context7.cache.cleanup_interval_seconds", int),
        "CONTEXT7_CACHE_ENABLE_PRELOAD": ("context7.cache.enable_preload", lambda x: x.lower() == "true"),
        "CONTEXT7_CACHE_PRELOAD_POPULAR_ITEMS": ("context7.cache.preload_popular_items", lambda x: x.lower() == "true"),
        "CONTEXT7_CACHE_PRELOAD_BATCH_SIZE": ("context7.cache.preload_batch_size", int),
        
        # Context7 Background Jobs configuration
        "CONTEXT7_BACKGROUND_TTL_CLEANUP_ENABLED": ("context7.background_jobs.ttl_cleanup_enabled", lambda x: x.lower() == "true"),
        "CONTEXT7_BACKGROUND_TTL_CLEANUP_INTERVAL_SECONDS": ("context7.background_jobs.ttl_cleanup_interval_seconds", int),
        "CONTEXT7_BACKGROUND_TTL_CLEANUP_BATCH_SIZE": ("context7.background_jobs.ttl_cleanup_batch_size", int),
        "CONTEXT7_BACKGROUND_METRICS_COLLECTION_ENABLED": ("context7.background_jobs.metrics_collection_enabled", lambda x: x.lower() == "true"),
        "CONTEXT7_BACKGROUND_METRICS_COLLECTION_INTERVAL_SECONDS": ("context7.background_jobs.metrics_collection_interval_seconds", int),
        "CONTEXT7_BACKGROUND_HEALTH_CHECK_ENABLED": ("context7.background_jobs.health_check_enabled", lambda x: x.lower() == "true"),
        "CONTEXT7_BACKGROUND_HEALTH_CHECK_INTERVAL_SECONDS": ("context7.background_jobs.health_check_interval_seconds", int),
        "CONTEXT7_BACKGROUND_MAINTENANCE_WINDOW_ENABLED": ("context7.background_jobs.maintenance_window_enabled", lambda x: x.lower() == "true"),
        "CONTEXT7_BACKGROUND_MAINTENANCE_WINDOW_START_HOUR": ("context7.background_jobs.maintenance_window_start_hour", int),
        "CONTEXT7_BACKGROUND_MAINTENANCE_WINDOW_DURATION_HOURS": ("context7.background_jobs.maintenance_window_duration_hours", int),
        
        # Context7 Integration settings
        "CONTEXT7_WEAVIATE_TTL_ENABLED": ("context7.weaviate_ttl_enabled", lambda x: x.lower() == "true"),
        "CONTEXT7_ENABLE_AUDIT_LOGGING": ("context7.enable_audit_logging", lambda x: x.lower() == "true"),
        "CONTEXT7_MAX_MEMORY_USAGE_MB": ("context7.max_memory_usage_mb", int),
        "CONTEXT7_ENABLE_PERFORMANCE_MONITORING": ("context7.enable_performance_monitoring", lambda x: x.lower() == "true"),
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
    environment = os.getenv("ENVIRONMENT", "production")
    
    # In development/lab environments, use defaults if not provided
    if environment == "production":
        if not os.getenv("ANYTHINGLLM_API_KEY"):
            missing_vars["ANYTHINGLLM_API_KEY"] = "Required for AnythingLLM integration"

        if not os.getenv("GITHUB_API_TOKEN"):
            missing_vars["GITHUB_API_TOKEN"] = "Required for GitHub repository access"
    else:
        # Set defaults for development/lab environments
        if not os.getenv("ANYTHINGLLM_API_KEY"):
            os.environ["ANYTHINGLLM_API_KEY"] = "docaiche-lab-default-key-2025"
        if not os.getenv("GITHUB_API_TOKEN"):
            os.environ["GITHUB_API_TOKEN"] = "github-lab-token-placeholder"

    # Check AI provider configuration
    primary_provider = os.getenv("AI_PRIMARY_PROVIDER", "ollama")
    fallback_provider = os.getenv("AI_FALLBACK_PROVIDER")

    # Only require OpenAI API key if OpenAI is selected as provider
    if primary_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        missing_vars["OPENAI_API_KEY"] = "Required when OpenAI is primary provider"

    if fallback_provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        missing_vars["OPENAI_API_KEY"] = "Required when OpenAI is fallback provider"

    return missing_vars
