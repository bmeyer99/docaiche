"""
Configuration management for AI Documentation Cache System
PRD-003: Configuration Management System - CFG-001 Implementation
"""

import logging

logger = logging.getLogger(__name__)

# Mark this module as deprecated
logger.warning(
    "src.core.config module is deprecated. "
    "Import directly from 'src.core.config' package instead."
)

# Import everything from the config package to maintain compatibility
from src.core.config import *

# Explicit re-exports for IDE support
__all__ = [
    "SystemConfiguration",
    "AppConfig",
    "ContentConfig",
    "AnythingLLMConfig",
    "GitHubConfig",
    "ScrapingConfig",
    "RedisConfig",
    "AIConfig",
    "OllamaConfig",
    "OpenAIConfig",
    "CircuitBreakerConfig",
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
]