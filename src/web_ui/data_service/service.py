"""Data Service for Web UI Service."""

import logging
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from src.web_ui.database.models import ConfigEntry

logger = logging.getLogger(__name__)

class IDataService(ABC):
    """Abstract interface for the Data Service."""

    @abstractmethod
    async def fetch_stats(self) -> Dict[str, Any]:
        """Fetch system statistics from data sources.
        Returns:
            Dictionary of statistics.
        """
        pass

    @abstractmethod
    async def fetch_config(self) -> Dict[str, Any]:
        """Fetch configuration data from data sources.
        Returns:
            Dictionary of configuration.
        """
        pass

class DataService(IDataService):
    """Concrete Data Service implementation."""

    def __init__(self, db_session: Optional[AsyncSession] = None):
        # TODO: IMPLEMENTATION ENGINEER - Inject dependencies (db, cache, etc.)
        self.db_session = db_session

    async def fetch_stats(self) -> Dict[str, Any]:
        """Fetch system statistics from data sources."""
        # TODO: IMPLEMENTATION ENGINEER - Implement data aggregation logic
        try:
            # Example: count config entries as a simple stat
            result = await self.db_session.execute(select(ConfigEntry))
            count = len(result.scalars().all())
            stats = {
                "config_entry_count": count,
                "status": "ok"
            }
            logger.info("Fetched stats: %s", stats)
            return stats
        except SQLAlchemyError as e:
            logger.error(f"Database error in fetch_stats: {e}")
            raise Exception("Failed to fetch stats from database")

    async def fetch_config(self) -> Dict[str, Any]:
        """Fetch configuration data from data sources."""
        # TODO: IMPLEMENTATION ENGINEER - Implement config retrieval logic
        try:
            result = await self.db_session.execute(select(ConfigEntry))
            entries = result.scalars().all()
            config = {entry.key: entry.value for entry in entries}
            logger.info("Fetched config: %s", config)
            return config
        except SQLAlchemyError as e:
            logger.error(f"Database error in fetch_config: {e}")
            raise Exception("Failed to fetch config from database")