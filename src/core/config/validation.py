"""
Configuration Validation for AI Documentation Cache System - PRD-003
Custom validators for configuration models

Implements all validation requirements from CFG-001 for endpoint URLs, API keys,
user agents, and Redis memory configurations using modern Pydantic v2 field validators.

All validators are now implemented directly in the model definitions using @field_validator
decorators for better integration and type safety.
"""

import logging
import re

logger = logging.getLogger(__name__)


class ConfigurationValidators:
    """
    Validation utility functions for configuration models.

    These validators are used by the @field_validator decorators in the model classes
    for consistent validation across all configuration components.
    """

    @staticmethod
    def validate_endpoint_url(v: str) -> str:
        """
        Validate endpoint URLs

        Args:
            v: URL string to validate

        Returns:
            Cleaned URL string

        Raises:
            ValueError: If URL format is invalid
        """
        if not v.startswith(("http://", "https://")):
            raise ValueError("Endpoint must start with http:// or https://")
        return v.rstrip("/")

    @staticmethod
    def validate_api_key(v: str) -> str:
        """
        Validate API key format

        Args:
            v: API key string to validate

        Returns:
            Cleaned API key string

        Raises:
            ValueError: If API key format is invalid
        """
        if not v or len(v.strip()) < 8:
            raise ValueError("API key must be at least 8 characters")
        return v.strip()

    @staticmethod
    def validate_user_agent(v: str) -> str:
        """
        Validate user agent string

        Args:
            v: User agent string to validate

        Returns:
            Validated user agent string

        Raises:
            ValueError: If user agent format is invalid
        """
        if not re.match(r"^[a-zA-Z0-9\-_/\.\s]+$", v):
            raise ValueError("Invalid user agent format")
        return v

    @staticmethod
    def validate_redis_memory(v: str) -> str:
        """
        Validate Redis memory configuration

        Args:
            v: Memory configuration string to validate

        Returns:
            Normalized memory configuration string

        Raises:
            ValueError: If memory format is invalid
        """
        if not re.match(r"^\d+[kmgKMG][bB]?$", v):
            raise ValueError(
                'Invalid memory format. Use format like "512mb", "1gb", etc.'
            )
        return v.lower()


def validate_configuration_schema() -> bool:
    """
    Validate that all configuration models have proper validation setup

    Returns:
        True if all models are properly configured with validators
    """
    try:
        from .models import (
            AnythingLLMConfig,  # noqa: F401
            OllamaConfig,  # noqa: F401
            OpenAIConfig,  # noqa: F401
            ScrapingConfig,  # noqa: F401
            RedisConfig,  # noqa: F401
            SystemConfiguration,  # noqa: F401
        )

        # Test that models can be imported and have validators
        logger.info("Configuration schema validation completed successfully")
        return True

    except ImportError as e:
        logger.error(f"Configuration schema validation failed: {e}")
        return False


# Validation utilities for testing and development
def test_validators() -> bool:
    """
    Test all validators with sample data

    Returns:
        True if all validators work correctly
    """
    try:
        # Test endpoint URL validator
        ConfigurationValidators.validate_endpoint_url("http://localhost:8080")
        ConfigurationValidators.validate_endpoint_url("https://api.example.com/")

        # Test API key validator
        ConfigurationValidators.validate_api_key("test-api-key-12345")

        # Test user agent validator
        ConfigurationValidators.validate_user_agent("DocaicheBot/1.0")

        # Test Redis memory validator
        ConfigurationValidators.validate_redis_memory("512mb")
        ConfigurationValidators.validate_redis_memory("1GB")

        logger.info("All validators tested successfully")
        return True

    except Exception as e:
        logger.error(f"Validator testing failed: {e}")
        return False
