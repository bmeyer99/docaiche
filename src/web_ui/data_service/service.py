"""Data Service for Web UI with SystemConfiguration support."""

from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config.models import (
    SystemConfiguration, AppConfig, ContentConfig, AnythingLLMConfig,
    GitHubConfig, ScrapingConfig, RedisConfig, AIConfig, EnrichmentConfig
)
import logging
import json

logger = logging.getLogger(__name__)

# Create default SystemConfiguration instance
_default_system_config = SystemConfiguration(
    app=AppConfig(),
    content=ContentConfig(),
    anythingllm=AnythingLLMConfig(),
    github=GitHubConfig(),
    scraping=ScrapingConfig(),
    redis=RedisConfig(),
    ai=AIConfig(),
    enrichment=EnrichmentConfig()
)

# In-memory store for system configuration (simulates persistent storage)
_system_config_store = _default_system_config.model_copy()

class DataService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def fetch_stats(self) -> dict:
        """Fetch system statistics."""
        logger.info("Fetching system stats")
        return {"uptime": 12345.6, "active_users": 10, "additional_stats": {}}

    async def fetch_config(self) -> dict:
        """Legacy method - returns simplified config for backward compatibility."""
        logger.info("Fetching legacy configuration")
        system_config = await self.fetch_system_config()
        # Return simplified version for legacy support
        return {
            "environment": system_config.app.environment,
            "debug_mode": system_config.app.debug,
            "log_level": system_config.app.log_level,
            "workers": system_config.app.workers,
            "llm_provider": system_config.ai.primary_provider,
            "llm_model": system_config.ai.ollama.model,
            "temperature": system_config.ai.ollama.temperature,
            "max_tokens": system_config.ai.ollama.max_tokens
        }

    async def fetch_system_config(self) -> SystemConfiguration:
        """Fetch full system configuration."""
        logger.info("Fetching system configuration")
        # In real implementation, this would load from database
        # For now, return the in-memory store
        return _system_config_store

    async def update_config(self, config: dict) -> dict:
        """Legacy method - updates simplified config."""
        logger.info(f"Updating legacy configuration with: {config}")
        # Convert legacy config to SystemConfiguration format and update
        current_config = await self.fetch_system_config()
        
        # Map legacy fields to SystemConfiguration structure
        if "environment" in config:
            current_config.app.environment = config["environment"]
        if "debug_mode" in config:
            current_config.app.debug = config["debug_mode"]
        if "log_level" in config:
            current_config.app.log_level = config["log_level"]
        if "workers" in config:
            current_config.app.workers = config["workers"]
        if "llm_provider" in config:
            current_config.ai.primary_provider = config["llm_provider"]
        if "llm_model" in config:
            current_config.ai.ollama.model = config["llm_model"]
        if "temperature" in config:
            current_config.ai.ollama.temperature = config["temperature"]
        if "max_tokens" in config:
            current_config.ai.ollama.max_tokens = config["max_tokens"]
        
        # Update the store
        global _system_config_store
        _system_config_store = current_config
        
        # Return legacy format
        return await self.fetch_config()

    async def update_system_config(self, config: SystemConfiguration) -> SystemConfiguration:
        """Update full system configuration."""
        logger.info("Updating system configuration")
        # In real implementation, this would persist to database
        # For now, update the in-memory store
        global _system_config_store
        _system_config_store = config.model_copy()
        logger.info("System configuration updated successfully")
        return _system_config_store

    async def fetch_collections(self) -> list:
        """Fetch content collections."""
        logger.info("Fetching collections")
        return [{"id": "collection1", "name": "Sample Collection", "content_id": "doc1"}]

    async def delete_content(self, content_id: str) -> dict:
        """Delete or flag content for removal."""
        logger.info(f"Deleting content with id: {content_id}")
        return {"status": "deleted", "content_id": content_id}

    async def admin_search_content(self) -> list:
        """Admin search for content."""
        logger.info("Performing admin content search")
        return [{"id": "doc1", "title": "Admin Search Result"}]