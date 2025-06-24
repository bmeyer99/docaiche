"""Data Service for Web UI."""

from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

# In-memory store for configuration
config_store = {"setting1": "value1", "setting2": True}

class DataService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def fetch_stats(self) -> dict:
        """Fetch system statistics."""
        logger.info("Fetching system stats")
        return {"uptime": 12345.6, "active_users": 10, "additional_stats": {}}

    async def fetch_config(self) -> dict:
        """Fetch current configuration."""
        logger.info("Fetching configuration")
        return config_store

    async def update_config(self, config: dict) -> dict:
        """Update configuration."""
        logger.info(f"Updating configuration with: {config}")
        config_store.update(config)
        return config_store

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