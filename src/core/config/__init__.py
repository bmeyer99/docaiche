"""
Unified configuration access for the AI Documentation Cache System.
This package provides a centralized, hierarchical configuration system.
"""

from .manager import get_configuration_manager, get_system_configuration, reload_configuration
from .models import (
    SystemConfiguration,
    AppConfig,
    ContentConfig,
    AnythingLLMConfig,
    GitHubConfig,
    ScrapingConfig,
    RedisConfig,
    AIConfig,
    OllamaConfig,
    OpenAIConfig,
    CircuitBreakerConfig,
)
from .secrets import SecretsManager
from .validation import validate_configuration_schema

__all__ = [
    "get_configuration_manager",
    "get_system_configuration",
    "reload_configuration",
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
    "SecretsManager",
    "validate_configuration_schema",
]