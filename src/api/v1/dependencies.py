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
from src.clients.weaviate_client import WeaviateVectorClient
from src.search.orchestrator import SearchOrchestrator
from src.core.config.manager import ConfigurationManager

logger = logging.getLogger(__name__)

# Global instances (will be initialized on first use)
_db_manager: Optional[DatabaseManager] = None
_cache_manager: Optional[CacheManager] = None
_weaviate_client: Optional[WeaviateVectorClient] = None
_search_orchestrator: Optional[SearchOrchestrator] = None
_configuration_manager: Optional[ConfigurationManager] = None
_knowledge_enricher = None  # Type: Optional[KnowledgeEnricher]


def _reset_dependent_instances():
    """Reset all dependent instances when database is reinitialized"""
    global _search_orchestrator, _knowledge_enricher
    _search_orchestrator = None
    _knowledge_enricher = None
    logger.info("Reset dependent instances due to database reinitialization")


async def reset_service_instances():
    """Reset all service instances when configuration changes"""
    global _weaviate_client, _search_orchestrator, _knowledge_enricher, _configuration_manager
    
    # Disconnect existing clients gracefully
    if _weaviate_client is not None:
        try:
            await _weaviate_client.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting Weaviate client: {e}")
    
    # Reset all service instances
    _weaviate_client = None
    _search_orchestrator = None
    _knowledge_enricher = None
    _configuration_manager = None
    
    # Reset AI provider instances to pick up new models/configs
    try:
        from src.llm.provider_registry import get_provider_registry
        provider_registry = get_provider_registry()
        provider_registry.clear_instances()
        logger.info("Cleared AI provider instances")
    except ImportError:
        logger.warning("Could not reset AI provider instances - provider registry not available")
    
    logger.info("Reset all service instances due to configuration change")


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


class StubWeaviateClient:
    """Stub Weaviate client for degraded operation"""

    def __init__(self, config=None):
        self.config = config

    async def connect(self) -> None:
        pass

    async def disconnect(self) -> None:
        pass

    async def health_check(self) -> dict:
        return {
            "status": "unavailable",
            "message": "Weaviate service not configured or unavailable",
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
    else:
        # Database should already be initialized at startup
        # Just log a warning if we detect issues but don't auto-reinitialize
        try:
            # Simple connection verification
            result = await _db_manager.fetch_one("SELECT COUNT(*) as count FROM sqlite_master WHERE type='table'")
            table_count = result.get("count", 0) if result else 0
            if table_count < 8:
                logger.warning(f"Database appears incomplete (found {table_count} tables). Database should be initialized at startup.")
        except Exception as e:
            logger.warning(f"Database connection verification failed: {e}")

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


async def get_weaviate_client() -> WeaviateVectorClient:
    """
    Dependency to get Weaviate client instance with graceful degradation
    """
    global _weaviate_client

    if _weaviate_client is None:
        try:
            config = get_system_configuration()
            _weaviate_client = WeaviateVectorClient(config.weaviate)
            await _weaviate_client.connect()
            # Test connection but don't fail hard
            await _weaviate_client.health_check()
            logger.info("Weaviate client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Weaviate client: {e}")
            logger.info("Using stub Weaviate client for degraded operation")
            try:
                config = get_system_configuration()
                _weaviate_client = StubWeaviateClient(config.weaviate)
            except Exception:
                _weaviate_client = StubWeaviateClient()

    return _weaviate_client


async def get_search_orchestrator() -> SearchOrchestrator:
    """
    Dependency to get Enhanced SearchOrchestrator instance with LLM intelligence
    """
    global _search_orchestrator
    
    # Get the actual service instances
    db_manager = await get_database_manager()
    cache_manager = await get_cache_manager()
    weaviate_client = await get_weaviate_client()

    # Always recreate if db_manager was reinitialized or is different
    if _search_orchestrator is None or (hasattr(_search_orchestrator, 'db_manager') and _search_orchestrator.db_manager != db_manager):
        try:
            # Import LLM client for MCP integration
            from src.llm.client import LLMProviderClient
            
            # Get configuration and create LLM client
            config = get_system_configuration()
            llm_client = None
            
            if config and hasattr(config, 'ai'):
                try:
                    llm_client = LLMProviderClient(
                        config.ai.model_dump() if hasattr(config.ai, 'model_dump') else config.ai.dict()
                    )
                    logger.info("LLM client initialized for MCP search orchestrator")
                except Exception as e:
                    logger.warning(f"Failed to initialize LLM client: {e}")
            
            # Create search orchestrator with LLM client for MCP integration
            _search_orchestrator = SearchOrchestrator(
                db_manager=db_manager,
                cache_manager=cache_manager,
                weaviate_client=weaviate_client,
                llm_client=llm_client,
                knowledge_enricher=None,
            )
            logger.info("Search orchestrator with MCP integration initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize search orchestrator with LLM client: {e}")
            logger.info("Falling back to basic search orchestrator without MCP")
            # Fall back to basic orchestrator without MCP
            _search_orchestrator = SearchOrchestrator(
                db_manager=db_manager,
                cache_manager=cache_manager,
                weaviate_client=weaviate_client,
                llm_client=None,
                knowledge_enricher=None,
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
            # Initialize with database manager for configuration updates
            await _configuration_manager.initialize()
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
            from src.clients.github import GitHubClient
            from src.clients.webscraper import WebScrapingClient
            from src.processors.content_processor import ContentProcessingPipeline
            
            # Get required dependencies
            db_manager = await get_database_manager()
            search_orchestrator = await get_search_orchestrator()
            config_manager = await get_configuration_manager()
            config = config_manager.get_configuration()
            
            # Create required clients
            # GitHub client needs GitHubConfig specifically
            github_config = getattr(config, 'github', None)
            if not github_config:
                # Create default GitHub config
                from src.core.config.models import GitHubConfig
                github_config = GitHubConfig()
            
            github_client = GitHubClient(config=github_config, db_manager=db_manager)
            
            # WebScraper client needs ScrapingConfig
            scraping_config = getattr(config, 'scraping', None)
            if not scraping_config:
                # Create default scraping config
                from src.core.config.models import ScrapingConfig
                scraping_config = ScrapingConfig()
            
            webscraper_client = WebScrapingClient(config=scraping_config)
            content_processor = ContentProcessingPipeline(
                db_manager=db_manager,
                cache_manager=await get_cache_manager(),
                weaviate_client=await get_weaviate_client()
            )
            
            # Create enricher with all dependencies (not async)
            _knowledge_enricher = create_knowledge_enricher_with_integrated_config(
                db_manager=db_manager,
                github_client=github_client,
                webscraper_client=webscraper_client,
                content_processor=content_processor,
                search_orchestrator=search_orchestrator,
                config=config.enrichment.model_dump() if hasattr(config.enrichment, 'model_dump') else {}
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

        if _weaviate_client and hasattr(_weaviate_client, "disconnect"):
            await _weaviate_client.disconnect()
            logger.info("Weaviate client disconnected")

        # Cleanup knowledge enricher
        if _knowledge_enricher and hasattr(_knowledge_enricher, "shutdown"):
            await _knowledge_enricher.shutdown()
            logger.info("Knowledge enricher shut down")

        # Reset global instances
        _db_manager = None
        _cache_manager = None
        _weaviate_client = None
        _search_orchestrator = None
        _configuration_manager = None
        _knowledge_enricher = None

        logger.info("All dependencies cleaned up successfully")

    except Exception as e:
        logger.error(f"Error during dependency cleanup: {e}")


# Authentication dependencies for monitoring endpoints
async def get_current_user_optional():
    """
    Optional authentication dependency - returns None if no auth configured
    For now, returns None to allow unauthenticated access during development
    """
    # TODO: Implement proper JWT authentication
    return None


def require_role(user: Optional[dict], allowed_roles: list):
    """
    Check if user has required role
    
    Args:
        user: User dict from authentication
        allowed_roles: List of allowed roles
        
    Raises:
        HTTPException: If user doesn't have required role
    """
    if not user:
        # For now, allow access without authentication in development
        # TODO: Remove this in production
        return
    
    user_role = user.get("role", "viewer")
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Insufficient permissions. Required role: {allowed_roles}"
        )
