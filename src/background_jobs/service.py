"""
Background Job Service Integration
==================================

Service integration layer for the Context7 Background Job Manager.
Provides startup, shutdown, and lifecycle management for integration
with the main application.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

from .manager import Context7BackgroundJobManager
from .models import BackgroundJobManagerConfig
from . import create_default_config

from src.ingestion.context7_ingestion_service import Context7IngestionService
from src.clients.weaviate_client import WeaviateVectorClient
from src.database.manager import DatabaseManager
from src.llm.client import LLMProviderClient

logger = logging.getLogger(__name__)


class BackgroundJobService:
    """
    Background Job Service
    
    Provides lifecycle management and integration for the Context7 Background
    Job Manager within the main application architecture.
    
    Features:
    - Automatic startup and shutdown management
    - Configuration loading and validation
    - Health monitoring integration
    - Graceful error handling and recovery
    """
    
    def __init__(
        self,
        context7_service: Context7IngestionService,
        weaviate_client: WeaviateVectorClient,
        db_manager: DatabaseManager,
        llm_client: LLMProviderClient,
        config: Optional[BackgroundJobManagerConfig] = None
    ):
        self.context7_service = context7_service
        self.weaviate_client = weaviate_client
        self.db_manager = db_manager
        self.llm_client = llm_client
        
        # Use provided config or create default
        self.config = config or create_default_config()
        
        # Job manager instance
        self.job_manager: Optional[Context7BackgroundJobManager] = None
        
        # Service state
        self._running = False
        self._shutdown_event = asyncio.Event()
        
        logger.info("Background job service initialized")
    
    async def start(self) -> None:
        """Start the background job service"""
        if self._running:
            logger.warning("Background job service is already running")
            return
        
        try:
            logger.info("Starting background job service")
            
            # Check if background jobs are enabled
            if not self.config.enabled:
                logger.info("Background jobs are disabled in configuration")
                return
            
            # Initialize job manager
            self.job_manager = Context7BackgroundJobManager(
                config=self.config,
                context7_service=self.context7_service,
                weaviate_client=self.weaviate_client,
                db_manager=self.db_manager,
                llm_client=self.llm_client
            )
            
            # Start job manager
            await self.job_manager.start()
            
            self._running = True
            logger.info("Background job service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start background job service: {e}")
            # Cleanup on failure
            if self.job_manager:
                try:
                    await self.job_manager.stop()
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup: {cleanup_error}")
                self.job_manager = None
            raise
    
    async def stop(self) -> None:
        """Stop the background job service"""
        if not self._running:
            logger.warning("Background job service is not running")
            return
        
        try:
            logger.info("Stopping background job service")
            
            # Signal shutdown
            self._shutdown_event.set()
            
            # Stop job manager
            if self.job_manager:
                await self.job_manager.stop()
                self.job_manager = None
            
            self._running = False
            logger.info("Background job service stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping background job service: {e}")
            raise
    
    async def restart(self) -> None:
        """Restart the background job service"""
        logger.info("Restarting background job service")
        await self.stop()
        await self.start()
    
    @asynccontextmanager
    async def lifecycle(self):
        """Context manager for service lifecycle"""
        await self.start()
        try:
            yield self
        finally:
            await self.stop()
    
    # Delegation methods for common operations
    async def execute_job(self, job_id: str, correlation_id: str = None) -> Optional[Dict[str, Any]]:
        """Execute a job immediately"""
        if not self.job_manager:
            raise RuntimeError("Background job service is not running")
        
        execution = await self.job_manager.execute_job(job_id, correlation_id)
        return {
            "execution_id": execution.execution_id,
            "job_id": execution.job_id,
            "status": execution.status.value,
            "correlation_id": execution.correlation_id
        }
    
    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job status and configuration"""
        if not self.job_manager:
            return None
        
        job_config = await self.job_manager.get_job_status(job_id)
        if not job_config:
            return None
        
        return {
            "job_id": job_config.job_id,
            "job_name": job_config.job_name,
            "job_type": job_config.job_type.value,
            "enabled": job_config.enabled,
            "priority": job_config.priority.value,
            "description": job_config.description
        }
    
    async def get_job_metrics(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job execution metrics"""
        if not self.job_manager:
            return None
        
        metrics = await self.job_manager.get_job_metrics(job_id)
        if not metrics:
            return None
        
        return {
            "total_executions": metrics.total_executions,
            "successful_executions": metrics.successful_executions,
            "failed_executions": metrics.failed_executions,
            "error_rate": metrics.error_rate,
            "average_duration_seconds": metrics.average_duration_seconds,
            "health_status": metrics.health_status,
            "consecutive_failures": metrics.consecutive_failures,
            "last_execution_at": metrics.last_execution_at.isoformat() if metrics.last_execution_at else None,
            "last_success_at": metrics.last_success_at.isoformat() if metrics.last_success_at else None,
            "last_failure_at": metrics.last_failure_at.isoformat() if metrics.last_failure_at else None
        }
    
    async def get_running_jobs(self) -> List[Dict[str, Any]]:
        """Get currently running jobs"""
        if not self.job_manager:
            return []
        
        return await self.job_manager.get_running_jobs()
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        if not self.job_manager:
            return {
                "status": "not_running",
                "message": "Background job service is not running"
            }
        
        return await self.job_manager.get_health_status()
    
    async def get_service_info(self) -> Dict[str, Any]:
        """Get comprehensive service information"""
        return {
            "service_name": "Context7 Background Job Service",
            "version": "1.0.0",
            "running": self._running,
            "enabled": self.config.enabled,
            "configuration": {
                "max_concurrent_jobs": self.config.max_concurrent_jobs,
                "job_queue_size": self.config.job_queue_size,
                "scheduler_interval_seconds": self.config.scheduler_interval_seconds,
                "job_history_retention_days": self.config.job_history_retention_days,
                "health_check_interval_seconds": self.config.health_check_interval_seconds
            },
            "context7_config": {
                "ttl_cleanup_batch_size": self.config.context7_config.ttl_cleanup_batch_size,
                "refresh_batch_size": self.config.context7_config.refresh_batch_size,
                "refresh_threshold_days": self.config.context7_config.refresh_threshold_days,
                "max_concurrent_workspace_jobs": self.config.context7_config.max_concurrent_workspace_jobs
            }
        }
    
    # Administrative methods
    async def enable_job(self, job_id: str) -> bool:
        """Enable a specific job"""
        if not self.job_manager:
            return False
        
        job_config = await self.job_manager.get_job_status(job_id)
        if not job_config:
            return False
        
        job_config.enabled = True
        await self.job_manager.register_job(job_config)
        
        logger.info(f"Enabled job: {job_id}")
        return True
    
    async def disable_job(self, job_id: str) -> bool:
        """Disable a specific job"""
        if not self.job_manager:
            return False
        
        job_config = await self.job_manager.get_job_status(job_id)
        if not job_config:
            return False
        
        job_config.enabled = False
        await self.job_manager.register_job(job_config)
        
        logger.info(f"Disabled job: {job_id}")
        return True
    
    async def list_jobs(self) -> List[Dict[str, Any]]:
        """List all registered jobs"""
        if not self.job_manager:
            return []
        
        jobs = []
        for job_id in self.job_manager.job_registry.keys():
            job_info = await self.get_job_status(job_id)
            if job_info:
                # Add metrics
                metrics = await self.get_job_metrics(job_id)
                if metrics:
                    job_info["metrics"] = metrics
                jobs.append(job_info)
        
        return jobs
    
    # Properties
    @property
    def is_running(self) -> bool:
        """Check if the service is running"""
        return self._running
    
    @property
    def is_enabled(self) -> bool:
        """Check if background jobs are enabled"""
        return self.config.enabled


# Factory function for easy service creation
def create_background_job_service(
    context7_service: Context7IngestionService,
    weaviate_client: WeaviateVectorClient,
    db_manager: DatabaseManager,
    llm_client: LLMProviderClient,
    config: Optional[BackgroundJobManagerConfig] = None
) -> BackgroundJobService:
    """
    Factory function to create a BackgroundJobService instance
    
    Args:
        context7_service: Context7 ingestion service
        weaviate_client: Weaviate vector client
        db_manager: Database manager
        llm_client: LLM client
        config: Optional configuration (uses default if not provided)
    
    Returns:
        Configured BackgroundJobService instance
    """
    return BackgroundJobService(
        context7_service=context7_service,
        weaviate_client=weaviate_client,
        db_manager=db_manager,
        llm_client=llm_client,
        config=config
    )


# Utility functions for configuration management
def load_config_from_dict(config_dict: Dict[str, Any]) -> BackgroundJobManagerConfig:
    """Load configuration from dictionary"""
    return BackgroundJobManagerConfig(**config_dict)


def load_config_from_env() -> BackgroundJobManagerConfig:
    """Load configuration from environment variables"""
    import os
    
    config_data = {
        "enabled": os.getenv("BG_JOBS_ENABLED", "true").lower() == "true",
        "max_concurrent_jobs": int(os.getenv("BG_JOBS_MAX_CONCURRENT", "5")),
        "job_queue_size": int(os.getenv("BG_JOBS_QUEUE_SIZE", "100")),
        "scheduler_interval_seconds": int(os.getenv("BG_JOBS_SCHEDULER_INTERVAL", "60")),
        "job_history_retention_days": int(os.getenv("BG_JOBS_HISTORY_RETENTION", "30")),
        "health_check_interval_seconds": int(os.getenv("BG_JOBS_HEALTH_CHECK_INTERVAL", "300")),
        "metrics_export_interval_seconds": int(os.getenv("BG_JOBS_METRICS_INTERVAL", "60"))
    }
    
    # Context7 specific config
    context7_config_data = {
        "ttl_cleanup_batch_size": int(os.getenv("CTX7_TTL_CLEANUP_BATCH_SIZE", "50")),
        "refresh_batch_size": int(os.getenv("CTX7_REFRESH_BATCH_SIZE", "20")),
        "refresh_threshold_days": int(os.getenv("CTX7_REFRESH_THRESHOLD_DAYS", "7")),
        "max_concurrent_workspace_jobs": int(os.getenv("CTX7_MAX_CONCURRENT_WORKSPACE_JOBS", "3"))
    }
    
    config_data["context7_config"] = Context7JobConfig(**context7_config_data)
    
    return BackgroundJobManagerConfig(**config_data)