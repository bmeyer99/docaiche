"""
Secrets Management for AI Documentation Cache System - PRD-003
Secure handling of sensitive configuration values

Provides secure management of API keys, tokens, and other sensitive configuration
with production environment validation.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SecretsManager:
    """Manage sensitive configuration values"""
    
    @staticmethod
    def get_required_secret(env_var: str, description: str) -> str:
        """Get a required secret from environment"""
        value = os.getenv(env_var)
        if not value:
            raise ValueError(f"Required secret {env_var} not found in environment: {description}")
        return value
    
    @staticmethod
    def get_optional_secret(env_var: str, default: Optional[str] = None) -> Optional[str]:
        """Get an optional secret from environment"""
        return os.getenv(env_var, default)
    
    @staticmethod
    def validate_production_secrets(config) -> None:
        """Validate that production environment has required secrets"""
        from .models import SystemConfiguration
        
        if not isinstance(config, SystemConfiguration):
            logger.warning("Invalid config type passed to validate_production_secrets")
            return
            
        if config.app.environment == "production":
            required_secrets = []
            
            # Check AnythingLLM API key
            if not config.anythingllm.api_key:
                required_secrets.append("ANYTHINGLLM_API_KEY")
            
            # Check GitHub API token
            if not config.github.api_token:
                required_secrets.append("GITHUB_API_TOKEN")
            
            # Check OpenAI API key if OpenAI is configured
            if (config.ai.primary_provider == "openai" or 
                config.ai.fallback_provider == "openai"):
                if not config.ai.openai.api_key:
                    required_secrets.append("OPENAI_API_KEY")
            
            # Check Redis password in production
            if not config.redis.password:
                logger.warning("Redis password not set in production environment")
            
            if required_secrets:
                raise ValueError(f"Missing required secrets for production: {', '.join(required_secrets)}")
    
    @staticmethod
    def mask_secret_for_logging(secret: str, visible_chars: int = 4) -> str:
        """
        Mask a secret for safe logging
        
        Args:
            secret: The secret to mask
            visible_chars: Number of characters to show at the end
            
        Returns:
            Masked secret string
        """
        if not secret or len(secret) <= visible_chars:
            return "***"
        
        return "*" * (len(secret) - visible_chars) + secret[-visible_chars:]
    
    @staticmethod
    def validate_secret_format(secret: str, min_length: int = 8) -> bool:
        """
        Validate secret format meets basic security requirements
        
        Args:
            secret: Secret to validate
            min_length: Minimum required length
            
        Returns:
            True if secret meets requirements
        """
        if not secret:
            return False
        
        if len(secret.strip()) < min_length:
            return False
        
        # Additional validation could be added here
        # (e.g., character complexity requirements)
        
        return True
    
    @staticmethod
    def log_secret_status(secret_name: str, secret_value: Optional[str]) -> None:
        """
        Log the status of a secret (present/missing) without exposing the value
        
        Args:
            secret_name: Name of the secret
            secret_value: Value of the secret (None if missing)
        """
        if secret_value:
            masked = SecretsManager.mask_secret_for_logging(secret_value)
            logger.info(f"Secret {secret_name} configured: {masked}")
        else:
            logger.warning(f"Secret {secret_name} not configured")