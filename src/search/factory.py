"""
Search Orchestrator Factory - PRD-009
Factory functions for creating search orchestration components.

Provides dependency injection and configuration integration for search
orchestrator initialization as specified in PRD-009.
"""

import logging
from typing import Optional, Any

from .orchestrator import SearchOrchestrator
from .strategies import WorkspaceSearchStrategy
from .ranking import ResultRanker
from .cache import SearchCacheManager
from src.database.connection import (
    DatabaseManager,
    CacheManager,
    create_database_manager,
    create_cache_manager,
)
from src.clients.weaviate_client import WeaviateVectorClient

logger = logging.getLogger(__name__)


async def create_search_orchestrator(
    db_manager: Optional[DatabaseManager] = None,
    cache_manager: Optional[CacheManager] = None,
    weaviate_client: Optional[WeaviateVectorClient] = None,
    llm_client: Optional[Any] = None,
    knowledge_enricher: Optional[Any] = None,
) -> SearchOrchestrator:
    """
    Factory function to create SearchOrchestrator with dependency injection.

    Provides configuration integration and automatic dependency creation
    for search orchestrator components as specified in PRD-009.

    Args:
        db_manager: Database manager (created if None)
        cache_manager: Cache manager (created if None)
        weaviate_client: Weaviate client (optional)
        llm_client: LLM provider client (optional, for evaluation)
        knowledge_enricher: Knowledge enricher (optional, for background tasks)

    Returns:
        Configured SearchOrchestrator instance

    Raises:
        Exception: If required dependencies cannot be created
    """
    try:
        logger.info("Creating SearchOrchestrator with factory")

        # Create database manager if not provided
        if db_manager is None:
            logger.debug("Creating DatabaseManager from factory")
            db_manager = await create_database_manager()
            await db_manager.connect()

        # Create cache manager if not provided
        if cache_manager is None:
            logger.debug("Creating CacheManager from factory")
            cache_manager = await create_cache_manager()
            await cache_manager.connect()

        # Log available dependencies
        logger.debug(
            f"Dependencies: db={db_manager is not None}, cache={cache_manager is not None}, "
            f"weaviate={weaviate_client is not None}, llm={llm_client is not None}, "
            f"enricher={knowledge_enricher is not None}"
        )

        # Create search orchestrator
        orchestrator = SearchOrchestrator(
            db_manager=db_manager,
            cache_manager=cache_manager,
            weaviate_client=weaviate_client,
            llm_client=llm_client,
            knowledge_enricher=knowledge_enricher,
        )

        logger.info("SearchOrchestrator created successfully")
        return orchestrator

    except Exception as e:
        logger.error(f"Failed to create SearchOrchestrator: {e}")
        raise


def create_workspace_search_strategy(
    db_manager: DatabaseManager, weaviate_client: WeaviateVectorClient
) -> WorkspaceSearchStrategy:
    """
    Factory function to create WorkspaceSearchStrategy.

    Args:
        db_manager: Database manager for workspace metadata
        weaviate_client: Weaviate client for vector search

    Returns:
        Configured WorkspaceSearchStrategy instance
    """
    try:
        logger.debug("Creating WorkspaceSearchStrategy")

        strategy = WorkspaceSearchStrategy(db_manager, weaviate_client)

        logger.debug("WorkspaceSearchStrategy created successfully")
        return strategy

    except Exception as e:
        logger.error(f"Failed to create WorkspaceSearchStrategy: {e}")
        raise


def create_result_ranker() -> ResultRanker:
    """
    Factory function to create ResultRanker.

    Returns:
        Configured ResultRanker instance
    """
    try:
        logger.debug("Creating ResultRanker")

        ranker = ResultRanker()

        logger.debug("ResultRanker created successfully")
        return ranker

    except Exception as e:
        logger.error(f"Failed to create ResultRanker: {e}")
        raise


def create_search_cache_manager(cache_manager: CacheManager) -> SearchCacheManager:
    """
    Factory function to create SearchCacheManager.

    Args:
        cache_manager: Redis cache manager

    Returns:
        Configured SearchCacheManager instance
    """
    try:
        logger.debug("Creating SearchCacheManager")

        search_cache = SearchCacheManager(cache_manager)

        logger.debug("SearchCacheManager created successfully")
        return search_cache

    except Exception as e:
        logger.error(f"Failed to create SearchCacheManager: {e}")
        raise
