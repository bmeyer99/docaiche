"""
API v1 Dependencies - PRD-001: HTTP API Foundation
FastAPI dependency injection for database, cache, and service integrations

This module provides dependency injection functions for FastAPI endpoints
to access database managers, cache managers, and integrated services.
"""

import logging
from typing import Optional, AsyncGenerator

from fastapi import Depends, HTTPException
from src.core.config import get_settings
from src.database.connection import DatabaseManager, CacheManager, create_database_manager, create_cache_manager
from src.clients.anythingllm import AnythingLLMClient
from src.search.orchestrator import SearchOrchestrator

logger = logging.getLogger(__name__)

# Global instances (will be initialized on first use)
_db_manager: Optional[DatabaseManager] = None
_cache_manager: Optional[CacheManager] = None
_anythingllm_client: Optional[AnythingLLMClient] = None
_search_orchestrator: Optional[SearchOrchestrator] = None


async def get_database_manager() -> DatabaseManager:
    """
    Dependency to get DatabaseManager instance.
    
    Returns:
        DatabaseManager: Shared database manager instance
        
    Raises:
        HTTPException: If database connection fails
    """
    global _db_manager
    
    if _db_manager is None:
        try:
            _db_manager = await create_database_manager()
            await _db_manager.connect()
            logger.info("Database manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise HTTPException(
                status_code=503,
                detail="Database service unavailable"
            )
    
    return _db_manager


async def get_cache_manager() -> CacheManager:
    """
    Dependency to get CacheManager instance.
    
    Returns:
        CacheManager: Shared cache manager instance
        
    Raises:
        HTTPException: If cache connection fails (degraded mode allowed)
    """
    global _cache_manager
    
    if _cache_manager is None:
        try:
            _cache_manager = await create_cache_manager()
            await _cache_manager.connect()
            logger.info("Cache manager initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize cache manager: {e}")
            # For cache, we allow degraded operation without cache
            # Create a mock cache manager that does nothing
            _cache_manager = MockCacheManager()
    
    return _cache_manager


async def get_anythingllm_client() -> AnythingLLMClient:
    """
    Dependency to get AnythingLLM client instance.
    
    Returns:
        AnythingLLMClient: Shared AnythingLLM client instance
        
    Raises:
        HTTPException: If AnythingLLM client initialization fails
    """
    global _anythingllm_client
    
    if _anythingllm_client is None:
        try:
            config = get_settings()
            _anythingllm_client = AnythingLLMClient(
                endpoint=config.anythingllm.endpoint,
                api_key=config.anythingllm.api_key
            )
            # Test connection
            await _anythingllm_client.health_check()
            logger.info("AnythingLLM client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize AnythingLLM client: {e}")
            raise HTTPException(
                status_code=503,
                detail="Vector database service unavailable"
            )
    
    return _anythingllm_client


async def get_search_orchestrator(
    db_manager: DatabaseManager = Depends(get_database_manager),
    cache_manager: CacheManager = Depends(get_cache_manager),
    anythingllm_client: AnythingLLMClient = Depends(get_anythingllm_client)
) -> SearchOrchestrator:
    """
    Dependency to get SearchOrchestrator instance.
    
    Args:
        db_manager: Database manager dependency
        cache_manager: Cache manager dependency
        anythingllm_client: AnythingLLM client dependency
        
    Returns:
        SearchOrchestrator: Configured search orchestrator instance
        
    Raises:
        HTTPException: If search orchestrator initialization fails
    """
    global _search_orchestrator
    
    if _search_orchestrator is None:
        try:
            _search_orchestrator = SearchOrchestrator(
                db_manager=db_manager,
                cache_manager=cache_manager,
                anythingllm_client=anythingllm_client,
                llm_client=None,  # Will be integrated when PRD-005 is implemented
                knowledge_enricher=None  # Will be integrated when PRD-010 is implemented
            )
            logger.info("Search orchestrator initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize search orchestrator: {e}")
            raise HTTPException(
                status_code=503,
                detail="Search service unavailable"
            )
    
    return _search_orchestrator


class MockCacheManager:
    """
    Mock cache manager for degraded operation when Redis is unavailable.
    All operations are no-ops to allow the application to continue functioning.
    """
    
    def __init__(self):
        self._connected = False
    
    async def connect(self) -> None:
        """Mock connect - does nothing"""
        pass
    
    async def disconnect(self) -> None:
        """Mock disconnect - does nothing"""
        pass
    
    async def get(self, key: str) -> None:
        """Mock get - always returns None (cache miss)"""
        return None
    
    async def set(self, key: str, value: any, ttl: int) -> None:
        """Mock set - does nothing"""
        pass
    
    async def delete(self, key: str) -> None:
        """Mock delete - does nothing"""
        pass
    
    async def increment(self, key: str) -> int:
        """Mock increment - always returns 1"""
        return 1
    
    async def expire(self, key: str, seconds: int) -> None:
        """Mock expire - does nothing"""
        pass
    
    async def health_check(self) -> dict:
        """Mock health check - returns degraded status"""
        return {
            "status": "degraded",
            "connected": False,
            "error": "Cache service unavailable - operating in degraded mode"
        }


# Cleanup function for application shutdown
async def cleanup_dependencies():
    """
    Cleanup all dependency instances on application shutdown.
    """
    global _db_manager, _cache_manager, _anythingllm_client, _search_orchestrator
    
    try:
        if _db_manager:
            await _db_manager.disconnect()
            logger.info("Database manager disconnected")
        
        if _cache_manager and hasattr(_cache_manager, 'disconnect'):
            await _cache_manager.disconnect()
            logger.info("Cache manager disconnected")
        
        if _anythingllm_client and hasattr(_anythingllm_client, 'close'):
            await _anythingllm_client.close()
            logger.info("AnythingLLM client closed")
        
        # Reset global instances
        _db_manager = None
        _cache_manager = None
        _anythingllm_client = None
        _search_orchestrator = None
        
        logger.info("All dependencies cleaned up successfully")
        
    except Exception as e:
        logger.error(f"Error during dependency cleanup: {e}")