"""
Health service implementation.

Aggregates health status from all critical internal and external dependencies
to provide a comprehensive system health check.
"""

import asyncio
import datetime
from typing import List, Dict, Any, Optional
from src.database.manager import DatabaseManager
from src.cache.manager import CacheManager
from src.api.schemas import HealthResponse, HealthStatus


class HealthService:
    """Service for aggregating and reporting system health status."""
    
    def __init__(
        self,
        db_manager: Optional[DatabaseManager] = None,
        cache_manager: Optional[CacheManager] = None,
        anythingllm_client: Optional[Any] = None
    ):
        """
        Initialize the health service with system dependencies.
        
        Args:
            db_manager: DatabaseManager instance for database health checks
            cache_manager: CacheManager instance for cache health checks
            anythingllm_client: AnythingLLMClient instance for external service checks
        """
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self.anythingllm_client = anythingllm_client
    
    async def check_system_health(self) -> HealthResponse:
        """
        Checks all dependencies in parallel and aggregates their status.
        
        Returns:
            HealthResponse with overall system health and individual service statuses
        """
        health_checks = []
        
        # Add database health check
        if self.db_manager:
            health_checks.append(self._check_database())
        
        # Add cache health check
        if self.cache_manager:
            health_checks.append(self._check_cache())
        
        # Add AnythingLLM health check
        if self.anythingllm_client:
            health_checks.append(self._check_anythingllm())
        
        # If no dependencies are configured, add a basic API health check
        if not health_checks:
            health_checks.append(self._check_api())
        
        # Execute all health checks in parallel
        results = await asyncio.gather(*health_checks, return_exceptions=True)
        
        # Process results
        service_statuses = []
        for result in results:
            if isinstance(result, Exception):
                # If the health check threw an exception, mark as unhealthy
                service_statuses.append(HealthStatus(
                    service="unknown",
                    status="unhealthy",
                    detail=f"Health check failed: {str(result)}",
                    last_check=datetime.datetime.utcnow()
                ))
            elif isinstance(result, dict):
                # Convert dict result to HealthStatus
                service_statuses.append(HealthStatus(**result))
            elif isinstance(result, HealthStatus):
                # Already a HealthStatus object
                service_statuses.append(result)
        
        # Determine overall health status
        overall_status = self._calculate_overall_status(service_statuses)
        
        return HealthResponse(
            overall_status=overall_status,
            services=service_statuses,
            timestamp=datetime.datetime.utcnow()
        )
    
    async def _check_database(self) -> Dict[str, Any]:
        """Check database health status."""
        try:
            if hasattr(self.db_manager, 'health_check'):
                return await self.db_manager.health_check()
            
            # If no health_check method, try a simple query
            await self.db_manager.execute("SELECT 1", {})
            return {
                "service": "database",
                "status": "healthy",
                "detail": "Database connection is active",
                "last_check": datetime.datetime.utcnow()
            }
        except Exception as e:
            return {
                "service": "database",
                "status": "unhealthy",
                "detail": f"Database check failed: {str(e)}",
                "last_check": datetime.datetime.utcnow()
            }
    
    async def _check_cache(self) -> Dict[str, Any]:
        """Check cache health status."""
        try:
            if hasattr(self.cache_manager, 'health_check'):
                return await self.cache_manager.health_check()
            
            # If no health_check method, try a simple operation
            test_key = "__health_check__"
            test_value = "ok"
            await self.cache_manager.set(test_key, test_value, ttl=10)
            result = await self.cache_manager.get(test_key)
            
            if result == test_value:
                return {
                    "service": "cache",
                    "status": "healthy",
                    "detail": "Cache is operational",
                    "last_check": datetime.datetime.utcnow()
                }
            else:
                return {
                    "service": "cache",
                    "status": "degraded",
                    "detail": "Cache responded but with unexpected value",
                    "last_check": datetime.datetime.utcnow()
                }
        except Exception as e:
            return {
                "service": "cache",
                "status": "unhealthy",
                "detail": f"Cache check failed: {str(e)}",
                "last_check": datetime.datetime.utcnow()
            }
    
    async def _check_anythingllm(self) -> Dict[str, Any]:
        """Check AnythingLLM service health status."""
        try:
            if hasattr(self.anythingllm_client, 'health_check'):
                return await self.anythingllm_client.health_check()
            
            # If no health_check method, check if client is initialized
            if self.anythingllm_client:
                return {
                    "service": "anythingllm",
                    "status": "healthy",
                    "detail": "AnythingLLM client is initialized",
                    "last_check": datetime.datetime.utcnow()
                }
            else:
                return {
                    "service": "anythingllm",
                    "status": "degraded",
                    "detail": "AnythingLLM client not fully configured",
                    "last_check": datetime.datetime.utcnow()
                }
        except Exception as e:
            return {
                "service": "anythingllm",
                "status": "unhealthy",
                "detail": f"AnythingLLM check failed: {str(e)}",
                "last_check": datetime.datetime.utcnow()
            }
    
    async def _check_api(self) -> Dict[str, Any]:
        """Basic API health check when no dependencies are configured."""
        return {
            "service": "api",
            "status": "healthy",
            "detail": "API is responding",
            "last_check": datetime.datetime.utcnow()
        }
    
    def _calculate_overall_status(self, service_statuses: List[HealthStatus]) -> str:
        """
        Calculate overall system health based on individual service statuses.
        
        Args:
            service_statuses: List of individual service health statuses
            
        Returns:
            Overall health status: "healthy", "degraded", or "unhealthy"
        """
        if not service_statuses:
            return "healthy"
        
        # If any service is unhealthy, overall status is unhealthy
        if any(s.status == "unhealthy" for s in service_statuses):
            return "unhealthy"
        
        # If any service is degraded, overall status is degraded
        if any(s.status == "degraded" for s in service_statuses):
            return "degraded"
        
        # All services are healthy
        return "healthy"