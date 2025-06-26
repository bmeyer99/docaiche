"""Data Service for Web UI."""

from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

# In-memory store for legacy configuration
config_store = {"setting1": "value1", "setting2": True}

class DataService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def fetch_stats(self) -> dict:
        """Fetch system statistics."""
        logger.info("Fetching system stats")
        return {"uptime": 12345.6, "active_users": 10, "additional_stats": {}}

    async def fetch_config(self) -> dict:
        """Fetch current configuration from core config system."""
        logger.info("Fetching configuration from core system")
        try:
            from src.core.config.manager import get_configuration_manager
            manager = await get_configuration_manager()
            system_config = manager.get_configuration()
            
            # Convert SystemConfiguration to frontend format
            return self._convert_system_to_frontend_config(system_config)
        except Exception as e:
            logger.warning(f"Failed to fetch from core config system: {e}")
            return config_store

    async def update_config(self, config: dict) -> dict:
        """Update configuration in core config system."""
        logger.info(f"Updating configuration with: {config}")
        
        try:
            from src.core.config.manager import get_configuration_manager
            manager = await get_configuration_manager()
            
            # Map frontend config to core config structure and save
            await self._save_frontend_config_to_core(manager, config)
            
            # Return updated configuration
            system_config = manager.get_configuration()
            return self._convert_system_to_frontend_config(system_config)
            
        except Exception as e:
            logger.error(f"Failed to update core config system: {e}")
            # Fallback to in-memory store
            config_store.update(config)
            return config_store

    def _convert_system_to_frontend_config(self, system_config) -> dict:
        """Convert SystemConfiguration to frontend expected format."""
        return {
            # Application Settings
            "environment": system_config.app.environment,
            "debug_mode": system_config.app.debug,
            "log_level": system_config.app.log_level,
            "workers": system_config.app.workers,
            "api_host": system_config.app.api_host,
            
            # Service Configuration
            "api_timeout": 30,  # Default values for missing fields
            "websocket_url": f"ws://{system_config.app.api_host.replace('http://', '').replace('https://', '')}:4080/ws/updates",
            "max_retries": 3,
            
            # Cache Management
            "cache_ttl": system_config.ai.cache_ttl_seconds,
            "cache_max_size": 1000,
            "auto_refresh": True,
            "refresh_interval": 300,
            
            # AI/LLM Configuration - Map from extended dual provider structure
            "text_provider": getattr(system_config.ai, 'text_provider', system_config.ai.primary_provider),
            "text_base_url": getattr(system_config.ai, 'text_base_url', system_config.ai.ollama.endpoint),
            "text_api_key": getattr(system_config.ai, 'text_api_key', ''),
            
            "embedding_provider": getattr(system_config.ai, 'embedding_provider', system_config.ai.primary_provider),
            "embedding_base_url": getattr(system_config.ai, 'embedding_base_url', system_config.ai.ollama.endpoint),
            "embedding_api_key": getattr(system_config.ai, 'embedding_api_key', ''),
            "use_same_provider": getattr(system_config.ai, 'use_same_provider', True),
            
            # Model configuration
            "llm_model": getattr(system_config.ai, 'llm_model', system_config.ai.ollama.model),
            "llm_embedding_model": getattr(system_config.ai, 'llm_embedding_model', getattr(system_config.anythingllm, 'embedding_model', 'nomic-embed-text:latest')),
            
            # Text generation advanced parameters
            "text_max_tokens": getattr(system_config.ai, 'text_max_tokens', system_config.ai.ollama.max_tokens),
            "text_temperature": getattr(system_config.ai, 'text_temperature', system_config.ai.ollama.temperature),
            "text_top_p": getattr(system_config.ai, 'text_top_p', 1.0),
            "text_top_k": getattr(system_config.ai, 'text_top_k', 40),
            "text_timeout": getattr(system_config.ai, 'text_timeout', system_config.ai.ollama.timeout_seconds),
            "text_retries": getattr(system_config.ai, 'text_retries', 3),
            
            # Embedding advanced parameters
            "embedding_batch_size": getattr(system_config.ai, 'embedding_batch_size', 10),
            "embedding_timeout": getattr(system_config.ai, 'embedding_timeout', 30),
            "embedding_retries": getattr(system_config.ai, 'embedding_retries', 3),
            "embedding_chunk_size": getattr(system_config.ai, 'embedding_chunk_size', 512),
            "embedding_overlap": getattr(system_config.ai, 'embedding_overlap', 50),
            "embedding_normalize": getattr(system_config.ai, 'embedding_normalize', True),
        }

    async def _save_frontend_config_to_core(self, manager, frontend_config: dict):
        """
        Atomically map frontend configuration to core config structure and save.
        
        Uses single database transaction to ensure all configuration updates
        succeed or fail together (no partial updates).
        
        Args:
            manager: ConfigurationManager instance
            frontend_config: Dictionary containing frontend configuration values
            
        Raises:
            Exception: If atomic transaction fails (no changes committed)
        """
        # Build atomic configuration updates dictionary
        config_updates = {}
        
        # Map basic application settings
        if "environment" in frontend_config:
            config_updates["app.environment"] = frontend_config["environment"]
        if "debug_mode" in frontend_config:
            config_updates["app.debug"] = frontend_config["debug_mode"]
        if "log_level" in frontend_config:
            config_updates["app.log_level"] = frontend_config["log_level"]
        if "workers" in frontend_config:
            config_updates["app.workers"] = frontend_config["workers"]
        if "api_host" in frontend_config:
            config_updates["app.api_host"] = frontend_config["api_host"]
            
        # Map dual provider AI/LLM settings
        if "text_provider" in frontend_config:
            config_updates["ai.text_provider"] = frontend_config["text_provider"]
            config_updates["ai.primary_provider"] = frontend_config["text_provider"]
        if "text_base_url" in frontend_config:
            config_updates["ai.text_base_url"] = frontend_config["text_base_url"]
        if "text_api_key" in frontend_config:
            config_updates["ai.text_api_key"] = frontend_config["text_api_key"]
            
        if "embedding_provider" in frontend_config:
            config_updates["ai.embedding_provider"] = frontend_config["embedding_provider"]
        if "embedding_base_url" in frontend_config:
            config_updates["ai.embedding_base_url"] = frontend_config["embedding_base_url"]
        if "embedding_api_key" in frontend_config:
            config_updates["ai.embedding_api_key"] = frontend_config["embedding_api_key"]
        if "use_same_provider" in frontend_config:
            config_updates["ai.use_same_provider"] = frontend_config["use_same_provider"]
            
        # Map model configuration
        if "llm_model" in frontend_config:
            config_updates["ai.llm_model"] = frontend_config["llm_model"]
        if "llm_embedding_model" in frontend_config:
            config_updates["ai.llm_embedding_model"] = frontend_config["llm_embedding_model"]
            
        # Map text generation advanced parameters
        if "text_max_tokens" in frontend_config:
            config_updates["ai.text_max_tokens"] = frontend_config["text_max_tokens"]
        if "text_temperature" in frontend_config:
            config_updates["ai.text_temperature"] = frontend_config["text_temperature"]
        if "text_top_p" in frontend_config:
            config_updates["ai.text_top_p"] = frontend_config["text_top_p"]
        if "text_top_k" in frontend_config:
            config_updates["ai.text_top_k"] = frontend_config["text_top_k"]
        if "text_timeout" in frontend_config:
            config_updates["ai.text_timeout"] = frontend_config["text_timeout"]
        if "text_retries" in frontend_config:
            config_updates["ai.text_retries"] = frontend_config["text_retries"]
            
        # Map embedding advanced parameters
        if "embedding_batch_size" in frontend_config:
            config_updates["ai.embedding_batch_size"] = frontend_config["embedding_batch_size"]
        if "embedding_timeout" in frontend_config:
            config_updates["ai.embedding_timeout"] = frontend_config["embedding_timeout"]
        if "embedding_retries" in frontend_config:
            config_updates["ai.embedding_retries"] = frontend_config["embedding_retries"]
        if "embedding_chunk_size" in frontend_config:
            config_updates["ai.embedding_chunk_size"] = frontend_config["embedding_chunk_size"]
        if "embedding_overlap" in frontend_config:
            config_updates["ai.embedding_overlap"] = frontend_config["embedding_overlap"]
        if "embedding_normalize" in frontend_config:
            config_updates["ai.embedding_normalize"] = frontend_config["embedding_normalize"]
            
        # Map provider-specific settings for backward compatibility
        if frontend_config.get("text_provider") == "ollama":
            if "text_base_url" in frontend_config:
                config_updates["ai.ollama.endpoint"] = frontend_config["text_base_url"]
            if "llm_model" in frontend_config:
                config_updates["ai.ollama.model"] = frontend_config["llm_model"]
            if "text_max_tokens" in frontend_config:
                config_updates["ai.ollama.max_tokens"] = frontend_config["text_max_tokens"]
            if "text_temperature" in frontend_config:
                config_updates["ai.ollama.temperature"] = frontend_config["text_temperature"]
            if "text_timeout" in frontend_config:
                config_updates["ai.ollama.timeout_seconds"] = frontend_config["text_timeout"]
                
        elif frontend_config.get("text_provider") == "openai":
            if "text_api_key" in frontend_config:
                config_updates["ai.openai.api_key"] = frontend_config["text_api_key"]
            if "llm_model" in frontend_config:
                config_updates["ai.openai.model"] = frontend_config["llm_model"]
            if "text_max_tokens" in frontend_config:
                config_updates["ai.openai.max_tokens"] = frontend_config["text_max_tokens"]
            if "text_temperature" in frontend_config:
                config_updates["ai.openai.temperature"] = frontend_config["text_temperature"]
                
        # Map embedding settings to AnythingLLM config
        if "llm_embedding_model" in frontend_config:
            config_updates["anythingllm.embedding_model"] = frontend_config["llm_embedding_model"]
        if "embedding_provider" in frontend_config:
            config_updates["anythingllm.embedding_provider"] = frontend_config["embedding_provider"]
            
        # Map cache settings
        if "cache_ttl" in frontend_config:
            config_updates["ai.cache_ttl_seconds"] = frontend_config["cache_ttl"]
        
        # Perform atomic bulk update using single transaction and audit
        if config_updates:
            await manager.bulk_update_in_db(config_updates, user="WebUI")
            logger.info(f"Frontend configuration mapped and saved atomically: {len(config_updates)} items")
        else:
            logger.info("No configuration updates to apply from frontend")

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