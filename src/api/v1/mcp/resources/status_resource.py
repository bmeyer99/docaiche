"""
Status Resource
==============

Provides system status and health information.
"""

import logging
from typing import Dict, Any
from datetime import datetime

from .base_resource import BaseResource
from src.database.connection import DatabaseManager, CacheManager
from src.search.orchestrator import SearchOrchestrator

logger = logging.getLogger(__name__)


class StatusResource(BaseResource):
    """System status resource"""
    
    def __init__(
        self,
        db_manager: DatabaseManager = None,
        cache_manager: CacheManager = None,
        search_orchestrator: SearchOrchestrator = None
    ):
        super().__init__(
            uri_prefix="docaiche://status",
            description="Get system status and health information"
        )
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self.search_orchestrator = search_orchestrator
    
    async def read(self, uri: str) -> Dict[str, Any]:
        """
        Read system status.
        
        Args:
            uri: Resource URI (e.g., docaiche://status)
            
        Returns:
            Status data
        """
        try:
            status = {
                "timestamp": datetime.utcnow().isoformat(),
                "overall_status": "healthy",
                "services": {}
            }
            
            # Check database status
            if self.db_manager:
                try:
                    db_health = await self.db_manager.health_check()
                    status["services"]["database"] = {
                        "status": "healthy" if db_health.get("connected") else "unhealthy",
                        "details": db_health
                    }
                except Exception as e:
                    status["services"]["database"] = {
                        "status": "error",
                        "error": str(e)
                    }
                    status["overall_status"] = "degraded"
            
            # Check cache status
            if self.cache_manager:
                try:
                    cache_health = await self.cache_manager.health_check()
                    status["services"]["cache"] = {
                        "status": "healthy" if cache_health.get("connected") else "unhealthy",
                        "details": cache_health
                    }
                except Exception as e:
                    status["services"]["cache"] = {
                        "status": "error",
                        "error": str(e)
                    }
                    status["overall_status"] = "degraded"
            
            # Check search orchestrator status
            if self.search_orchestrator:
                try:
                    search_health = await self.search_orchestrator.health_check()
                    status["services"]["search"] = {
                        "status": search_health.get("overall_status", "unknown"),
                        "details": search_health
                    }
                    if search_health.get("overall_status") != "healthy":
                        status["overall_status"] = "degraded"
                except Exception as e:
                    status["services"]["search"] = {
                        "status": "error",
                        "error": str(e)
                    }
                    status["overall_status"] = "degraded"
            
            return {
                "uri": uri,
                "name": "System Status",
                "mimeType": "application/json",
                "text": status
            }
            
        except Exception as e:
            logger.error(f"Failed to read status: {e}", exc_info=True)
            raise ValueError(f"Failed to read status: {str(e)}")