"""
API v1 Dependencies - PRD-001: HTTP API Foundation
FastAPI dependency injection with graceful degradation for zero-config startup
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException
from src.core.config import get_system_configuration
from src.database.connection import (
    DatabaseManager,
    CacheManager,
    create_database_manager,
    create_cache_manager,
)
from src.clients.anythingllm import AnythingLLMClient
from src.search.orchestrator import SearchOrchestrator
from src.core.config.manager import ConfigurationManager

logger = logging.getLogger(__name__)

# Global instances (will be initialized on first use)
_db_manager: Optional[DatabaseManager] = None
_cache_manager: Optional[CacheManager] = None
_anythingllm_client: Optional[AnythingLLMClient] = None
_search_orchestrator: Optional[SearchOrchestrator] = None
_configuration_manager: Optional[ConfigurationManager] = None
_knowledge_enricher = None  # Type: Optional[KnowledgeEnricher]


class StubDatabaseManager:
    """Stub database manager for degraded operation"""

    def __init__(self):
        self._connected = False

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {
            "status": "degraded",
            "connected": False,
            "message": "Database unavailable - operating in stub mode",
        }

    async def execute(self, query: str, params=()) -> None:
        logger.warning("Database execute called in stub mode - operation ignored")

    async def fetch_one(self, query: str, params=()):
        logger.warning("Database fetch_one called in stub mode - returning None")
        return None

    async def fetch_all(self, query: str, params=()):
        logger.warning("Database fetch_all called in stub mode - returning empty list")
        return []


class StubAnythingLLMClient:
    """Stub AnythingLLM client for degraded operation"""

    def __init__(self, config=None):
        self.config = config

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {
            "status": "unavailable",
            "message": "AnythingLLM service not configured or unavailable",
        }

    async def list_workspaces(self):
        return []

    async def search_workspace(self, workspace_slug: str, query: str, limit: int = 20):
        return []


class StubCacheManager:
    """Stub cache manager for degraded operation when Redis is unavailable"""

    def __init__(self):
        self._connected = False

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def get(self, key: str):
        return None

    async def set(self, key: str, value, ttl: int) -> None:
        pass

    async def delete(self, key: str) -> None:
        pass

    async def increment(self, key: str) -> int:
        return 1

    async def expire(self, key: str, seconds: int) -> None:
        pass

    async def health_check(self) -> dict:
        return {
            "status": "unavailable",
            "connected": False,
            "message": "Cache service unavailable - operating without cache",
        }


class StubSearchOrchestrator:
    """Stub search orchestrator for degraded operation"""

    def __init__(self, **kwargs):
        pass

    async def health_check(self) -> dict:
        return {
            "status": "degraded",
            "message": "Search orchestrator operating in degraded mode",
        }


async def get_database_manager() -> DatabaseManager:
    """
    Dependency to get DatabaseManager instance with graceful degradation
    """
    global _db_manager

    if _db_manager is None:
        try:
            _db_manager = await create_database_manager()
            await _db_manager.connect()
            logger.info("Database manager initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize database manager: {e}")
            logger.info("Using stub database manager for degraded operation")
            _db_manager = StubDatabaseManager()

    return _db_manager


async def get_cache_manager() -> CacheManager:
    """
    Dependency to get CacheManager instance with graceful degradation
    """
    global _cache_manager

    if _cache_manager is None:
        try:
            _cache_manager = await create_cache_manager()
            await _cache_manager.connect()
            logger.info("Cache manager initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize cache manager: {e}")
            logger.info("Using stub cache manager for degraded operation")
            _cache_manager = StubCacheManager()

    return _cache_manager


async def get_anythingllm_client() -> AnythingLLMClient:
    """
    Dependency to get AnythingLLM client instance with graceful degradation
    """
    global _anythingllm_client

    if _anythingllm_client is None:
        try:
            config = get_system_configuration()
            _anythingllm_client = AnythingLLMClient(config.anythingllm)
            await _anythingllm_client.connect()
            # Test connection but don't fail hard
            await _anythingllm_client.health_check()
            logger.info("AnythingLLM client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize AnythingLLM client: {e}")
            logger.info("Using stub AnythingLLM client for degraded operation")
            try:
                config = get_system_configuration()
                _anythingllm_client = StubAnythingLLMClient(config.anythingllm)
            except Exception:
                _anythingllm_client = StubAnythingLLMClient()

    return _anythingllm_client


async def get_search_orchestrator(
    db_manager: DatabaseManager = Depends(get_database_manager),
    cache_manager: CacheManager = Depends(get_cache_manager),
    anythingllm_client: AnythingLLMClient = Depends(get_anythingllm_client),
) -> SearchOrchestrator:
    """
    Dependency to get SearchOrchestrator instance with graceful degradation
    """
    global _search_orchestrator

    if _search_orchestrator is None:
        try:
            _search_orchestrator = SearchOrchestrator(
                db_manager=db_manager,
                cache_manager=cache_manager,
                anythingllm_client=anythingllm_client,
                llm_client=None,  # Will be integrated when PRD-005 is implemented
                knowledge_enricher=None,  # Will be integrated when PRD-010 is implemented
            )
            logger.info("Search orchestrator initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize search orchestrator: {e}")
            logger.info("Using stub search orchestrator for degraded operation")
            _search_orchestrator = StubSearchOrchestrator(
                db_manager=db_manager,
                cache_manager=cache_manager,
                anythingllm_client=anythingllm_client,
            )

    return _search_orchestrator


async def get_configuration_manager() -> ConfigurationManager:
    """
    Dependency to get ConfigurationManager instance
    """
    global _configuration_manager

    if _configuration_manager is None:
        try:
            _configuration_manager = ConfigurationManager()
            logger.info("Configuration manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize configuration manager: {e}")
            raise HTTPException(
                status_code=500, detail="Configuration manager unavailable"
            )

    return _configuration_manager


async def get_knowledge_enricher():
    """
    Dependency to get KnowledgeEnricher instance
    """
    global _knowledge_enricher
    
    if _knowledge_enricher is None:
        try:
            # Import here to avoid circular imports
            from src.enrichment.factory import create_knowledge_enricher_with_integrated_config
            from src.llm.client import LLMClient
            
            # Get required dependencies
            db_manager = await get_database_manager()
            cache_manager = await get_cache_manager()
            anythingllm_client = await get_anythingllm_client()
            config_manager = await get_configuration_manager()
            
            # Create LLM client
            config = config_manager.get_configuration()
            llm_client = LLMClient(config.ai)
            
            # Create enricher with all dependencies
            _knowledge_enricher = await create_knowledge_enricher_with_integrated_config(
                db_manager=db_manager,
                cache_manager=cache_manager,
                anythingllm_client=anythingllm_client,
                llm_client=llm_client,
                shutdown_timeout=30.0
            )
            
            logger.info("Knowledge enricher initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize knowledge enricher: {e}")
            raise HTTPException(
                status_code=503, detail="Knowledge enricher not available"
            )
    
    return _knowledge_enricher


# Cleanup function for application shutdown
async def cleanup_dependencies():
    """
    Cleanup all dependency instances on application shutdown
    """
    global _db_manager, _cache_manager, _anythingllm_client, _search_orchestrator, _configuration_manager, _knowledge_enricher

    try:
        if _db_manager and hasattr(_db_manager, "disconnect"):
            await _db_manager.disconnect()
            logger.info("Database manager disconnected")

        if _cache_manager and hasattr(_cache_manager, "disconnect"):
            await _cache_manager.disconnect()
            logger.info("Cache manager disconnected")

        if _anythingllm_client and hasattr(_anythingllm_client, "disconnect"):
            await _anythingllm_client.disconnect()
            logger.info("AnythingLLM client disconnected")

        # Cleanup knowledge enricher
        if _knowledge_enricher and hasattr(_knowledge_enricher, "shutdown"):
            await _knowledge_enricher.shutdown()
            logger.info("Knowledge enricher shut down")

        # Reset global instances
        _db_manager = None
        _cache_manager = None
        _anythingllm_client = None
        _search_orchestrator = None
        _configuration_manager = None
        _knowledge_enricher = None

        logger.info("All dependencies cleaned up successfully")

    except Exception as e:
        logger.error(f"Error during dependency cleanup: {e}")
