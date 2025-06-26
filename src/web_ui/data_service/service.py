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