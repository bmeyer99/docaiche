"""
Context7 Background Jobs Package
===============================

Comprehensive background job framework for managing Context7 document TTL
and refresh operations with scheduling, monitoring, and error recovery.

Main Components:
- Context7BackgroundJobManager: Main job management orchestrator
- JobScheduler: Handles job scheduling with cron and interval support
- JobStorage: Persistent storage for job configurations and execution history
- JobMonitor: Real-time monitoring, alerting, and health checking
- Job Implementations: TTL cleanup, document refresh, and health check jobs

Usage:
    from src.background_jobs import Context7BackgroundJobManager, BackgroundJobManagerConfig
    
    # Create configuration
    config = BackgroundJobManagerConfig(
        enabled=True,
        max_concurrent_jobs=5,
        job_queue_size=100
    )
    
    # Initialize manager
    manager = Context7BackgroundJobManager(
        config=config,
        context7_service=context7_service,
        weaviate_client=weaviate_client,
        db_manager=db_manager,
        llm_client=llm_client
    )
    
    # Start background jobs
    await manager.start()
    
    # Register custom jobs
    await manager.register_job(custom_job_config)
    
    # Monitor health
    health = await manager.get_health_status()
    
    # Stop gracefully
    await manager.stop()
"""

from .models import (
    # Configuration models
    BackgroundJobManagerConfig,
    Context7JobConfig,
    JobConfig,
    JobSchedule,
    RetryConfig,
    
    # Execution models
    JobExecution,
    JobMetrics,
    
    # Enums
    JobStatus,
    JobType,
    JobPriority
)

from .manager import Context7BackgroundJobManager
from .scheduler import JobScheduler, CronParser
from .storage import JobStorage
from .monitoring import JobMonitor
from .jobs import TTLCleanupJob, DocumentRefreshJob, HealthCheckJob

__version__ = "1.0.0"

__all__ = [
    # Main manager
    "Context7BackgroundJobManager",
    
    # Configuration
    "BackgroundJobManagerConfig",
    "Context7JobConfig", 
    "JobConfig",
    "JobSchedule",
    "RetryConfig",
    
    # Execution
    "JobExecution",
    "JobMetrics",
    
    # Enums
    "JobStatus",
    "JobType", 
    "JobPriority",
    
    # Components
    "JobScheduler",
    "CronParser",
    "JobStorage",
    "JobMonitor",
    
    # Job implementations
    "TTLCleanupJob",
    "DocumentRefreshJob", 
    "HealthCheckJob"
]


def create_default_config() -> BackgroundJobManagerConfig:
    """Create a default background job manager configuration"""
    from .models import JobSchedule
    
    # Default TTL cleanup job (daily at 2 AM)
    ttl_cleanup_job = JobConfig(
        job_id="context7-ttl-cleanup-daily",
        job_type=JobType.TTL_CLEANUP,
        job_name="Daily Context7 TTL Cleanup",
        description="Daily cleanup of expired Context7 documents",
        enabled=True,
        priority=JobPriority.HIGH,
        schedule=JobSchedule(
            schedule_type="cron",
            cron_expression="0 2 * * *"  # Daily at 2 AM
        ),
        parameters={
            "batch_size": 50,
            "max_age_days": 90
        }
    )
    
    # Default document refresh job (weekly on Sunday at 3 AM)
    refresh_job = JobConfig(
        job_id="context7-document-refresh-weekly",
        job_type=JobType.DOCUMENT_REFRESH,
        job_name="Weekly Context7 Document Refresh",
        description="Weekly refresh of near-expired Context7 documents",
        enabled=True,
        priority=JobPriority.MEDIUM,
        schedule=JobSchedule(
            schedule_type="cron",
            cron_expression="0 3 * * 0"  # Sunday at 3 AM
        ),
        parameters={
            "batch_size": 20,
            "threshold_days": 7,
            "max_age_days": 30,
            "minimum_quality_score": 0.3
        }
    )
    
    # Default health check job (every 5 minutes)
    health_check_job = JobConfig(
        job_id="context7-health-check-frequent",
        job_type=JobType.HEALTH_CHECK,
        job_name="Context7 Health Check",
        description="Regular health check for Context7 services",
        enabled=True,
        priority=JobPriority.LOW,
        schedule=JobSchedule(
            schedule_type="interval",
            interval_minutes=5
        ),
        parameters={}
    )
    
    return BackgroundJobManagerConfig(
        enabled=True,
        max_concurrent_jobs=5,
        job_queue_size=100,
        scheduler_interval_seconds=60,
        job_history_retention_days=30,
        health_check_interval_seconds=300,
        metrics_export_interval_seconds=60,
        dead_letter_queue_enabled=True,
        max_failed_jobs_retention=1000,
        context7_config=Context7JobConfig(),
        default_jobs=[ttl_cleanup_job, refresh_job, health_check_job]
    )


def create_minimal_config() -> BackgroundJobManagerConfig:
    """Create a minimal configuration for testing or limited deployments"""
    return BackgroundJobManagerConfig(
        enabled=True,
        max_concurrent_jobs=2,
        job_queue_size=50,
        scheduler_interval_seconds=120,
        job_history_retention_days=7,
        health_check_interval_seconds=600,
        metrics_export_interval_seconds=120,
        dead_letter_queue_enabled=False,
        max_failed_jobs_retention=100,
        context7_config=Context7JobConfig(
            ttl_cleanup_batch_size=25,
            refresh_batch_size=10,
            max_concurrent_workspace_jobs=2
        ),
        default_jobs=[]  # No default jobs
    )