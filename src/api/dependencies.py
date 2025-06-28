"""
Service dependencies for the Docaiche API.

Provides dependency injection for all services with proper initialization
of backend managers and clients.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status

# Import backend managers
from src.core.config.manager import ConfigurationManager, get_configuration_manager
from src.database.manager import DatabaseManager, create_database_manager
from src.cache.manager import CacheManager
from src.search.factory import create_search_orchestrator
from src.search.orchestrator import SearchOrchestrator

# Import services
from src.services.search import SearchService
from src.services.config import ConfigService
from src.services.health import HealthService
from src.services.content import ContentService
from src.services.feedback import FeedbackService

# Global instances for singleton pattern
_config_manager: Optional[ConfigurationManager] = None
_db_manager: Optional[DatabaseManager] = None
_cache_manager: Optional[CacheManager] = None
_search_orchestrator: Optional[SearchOrchestrator] = None

# Async locks for thread-safe initialization
import asyncio
_config_lock = asyncio.Lock()
_db_lock = asyncio.Lock()
_cache_lock = asyncio.Lock()
_search_lock = asyncio.Lock()


class ServiceError(Exception):
    """Base exception for service-related errors."""
    pass


class ServiceUnavailableError(ServiceError):
    """Service is unavailable."""
    pass


async def get_database_manager() -> DatabaseManager:
    """Get or create the database manager instance."""
    global _db_manager
    
    if _db_manager is None:
        async with _db_lock:
            # Double-check pattern for thread safety
            if _db_manager is None:
                try:
                    _db_manager = await create_database_manager()
                    await _db_manager.connect()
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=f"Failed to initialize database: {str(e)}"
                    )
    
    return _db_manager


async def get_cache_manager() -> Optional[CacheManager]:
    """Get or create the cache manager instance."""
    global _cache_manager
    
    if _cache_manager is None:
        async with _cache_lock:
            # Double-check pattern for thread safety
            if _cache_manager is None:
                try:
                    # Try to create cache manager, but don't fail if unavailable
                    config_manager = await get_configuration_manager()
                    config = config_manager.get_configuration()
                    
                    if config.cache and config.cache.enabled:
                        _cache_manager = CacheManager()
                        await _cache_manager.initialize(config.cache)
                except Exception:
                    # Cache is optional, so we don't raise an error
                    pass
    
    return _cache_manager


async def get_search_orchestrator(
    db_manager: DatabaseManager = Depends(get_database_manager),
    cache_manager: Optional[CacheManager] = Depends(get_cache_manager)
) -> Optional[SearchOrchestrator]:
    """Get or create the search orchestrator instance."""
    global _search_orchestrator
    
    if _search_orchestrator is None:
        try:
            _search_orchestrator = await create_search_orchestrator(
                db_manager=db_manager,
                cache_manager=cache_manager
            )
        except Exception:
            # Search orchestrator might not be fully configured
            pass
    
    return _search_orchestrator


async def get_config_service() -> ConfigService:
    """Get the configuration service instance."""
    try:
        config_manager = await get_configuration_manager()
        return ConfigService(config_manager=config_manager)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to initialize configuration service: {str(e)}"
        )


async def get_health_service(
    db_manager: DatabaseManager = Depends(get_database_manager),
    cache_manager: Optional[CacheManager] = Depends(get_cache_manager)
) -> HealthService:
    """Get the health service instance."""
    try:
        return HealthService(
            db_manager=db_manager,
            cache_manager=cache_manager
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to initialize health service: {str(e)}"
        )


async def get_search_service(
    orchestrator: Optional[SearchOrchestrator] = Depends(get_search_orchestrator)
) -> SearchService:
    """Get the search service instance."""
    try:
        return SearchService(orchestrator=orchestrator)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to initialize search service: {str(e)}"
        )


async def get_content_service(
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> ContentService:
    """Get the content service instance."""
    try:
        return ContentService(db_manager=db_manager)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to initialize content service: {str(e)}"
        )


async def get_feedback_service(
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> FeedbackService:
    """Get the feedback service instance."""
    try:
        return FeedbackService(db_manager=db_manager)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to initialize feedback service: {str(e)}"
        )