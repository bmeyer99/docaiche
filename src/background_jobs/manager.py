"""
Context7 Background Job Manager
===============================

Comprehensive background job framework for managing Context7 document TTL
and refresh operations with scheduling, monitoring, and error recovery.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

from .models import (
    JobConfig, JobExecution, JobStatus, JobType, JobPriority,
    BackgroundJobManagerConfig, Context7JobConfig, JobMetrics, JobSchedule
)

from src.ingestion.context7_ingestion_service import Context7IngestionService
from src.clients.weaviate_client import WeaviateVectorClient
from src.database.manager import DatabaseManager
from src.llm.client import LLMProviderClient

logger = logging.getLogger(__name__)


@dataclass
class RunningJob:
    """Information about a currently running job"""
    execution_id: str
    job_id: str
    job_config: JobConfig
    task: asyncio.Task
    started_at: datetime
    correlation_id: str
    
    def __post_init__(self):
        self.status = JobStatus.RUNNING


class Context7BackgroundJobManager:
    """
    Context7 Background Job Manager
    
    Manages the complete lifecycle of Context7 document TTL and refresh operations
    through a comprehensive background job framework with scheduling, monitoring,
    error recovery, and health management.
    
    Features:
    - Daily TTL cleanup jobs
    - Weekly document refresh jobs
    - Job scheduling and monitoring
    - Error handling and retry logic
    - Health checks and metrics
    - Configuration-driven behavior
    """
    
    def __init__(
        self,
        config: BackgroundJobManagerConfig,
        context7_service: Context7IngestionService,
        weaviate_client: WeaviateVectorClient,
        db_manager: DatabaseManager,
        llm_client: LLMProviderClient
    ):
        self.config = config
        self.context7_service = context7_service
        self.weaviate_client = weaviate_client
        self.db_manager = db_manager
        self.llm_client = llm_client
        
        # Core components will be initialized later to avoid circular imports
        self.scheduler = None
        self.storage = None
        self.monitor = None
        
        # Job registry
        self.job_registry: Dict[str, JobConfig] = {}
        self.job_handlers: Dict[JobType, Callable] = {}
        
        # Runtime state
        self.running_jobs: Dict[str, RunningJob] = {}
        self.job_queue: asyncio.Queue = asyncio.Queue(maxsize=config.job_queue_size)
        self.shutdown_event = asyncio.Event()
        self.health_status = "unknown"
        
        # Background tasks
        self.scheduler_task: Optional[asyncio.Task] = None
        self.worker_tasks: List[asyncio.Task] = []
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Metrics
        self.metrics: Dict[str, JobMetrics] = {}
        
        # Initialize job handlers
        self._initialize_job_handlers()
        
        logger.info("Context7 Background Job Manager initialized")
    
    def _initialize_job_handlers(self) -> None:
        """Initialize job type handlers"""
        self.job_handlers = {
            JobType.TTL_CLEANUP: self._handle_ttl_cleanup,
            JobType.DOCUMENT_REFRESH: self._handle_document_refresh,
            JobType.HEALTH_CHECK: self._handle_health_check,
            JobType.MAINTENANCE: self._handle_maintenance
        }
    
    async def start(self) -> None:
        """Start the background job manager"""
        try:
            logger.info("Starting Context7 Background Job Manager")
            
            # Initialize core components
            from .scheduler import JobScheduler
            from .storage import JobStorage
            from .monitoring import JobMonitor
            
            self.scheduler = JobScheduler(self.config)
            self.storage = JobStorage(self.db_manager)
            self.monitor = JobMonitor(self.config)
            
            # Initialize storage
            await self.storage.initialize()
            
            # Load job configurations
            await self._load_job_configurations()
            
            # Start scheduler
            self.scheduler_task = asyncio.create_task(self._scheduler_loop())
            
            # Start worker tasks
            for i in range(self.config.max_concurrent_jobs):
                worker_task = asyncio.create_task(self._worker_loop(f"worker-{i}"))
                self.worker_tasks.append(worker_task)
            
            # Start monitor
            self.monitor_task = asyncio.create_task(self._monitor_loop())
            
            self.health_status = "healthy"
            logger.info("Context7 Background Job Manager started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Context7 Background Job Manager: {e}")
            self.health_status = "unhealthy"
            raise
    
    async def stop(self) -> None:
        """Stop the background job manager"""
        try:
            logger.info("Stopping Context7 Background Job Manager")
            
            # Signal shutdown
            self.shutdown_event.set()
            
            # Cancel running jobs
            for job_id, running_job in self.running_jobs.items():
                if not running_job.task.done():
                    running_job.task.cancel()
                    logger.info(f"Cancelled running job: {job_id}")
            
            # Wait for jobs to complete or cancel
            if self.running_jobs:
                await asyncio.gather(
                    *[job.task for job in self.running_jobs.values()],
                    return_exceptions=True
                )
            
            # Stop background tasks
            tasks_to_cancel = []
            if self.scheduler_task:
                tasks_to_cancel.append(self.scheduler_task)
            if self.monitor_task:
                tasks_to_cancel.append(self.monitor_task)
            tasks_to_cancel.extend(self.worker_tasks)
            
            for task in tasks_to_cancel:
                if not task.done():
                    task.cancel()
            
            if tasks_to_cancel:
                await asyncio.gather(*tasks_to_cancel, return_exceptions=True)
            
            # Cleanup
            await self.storage.cleanup()
            
            self.health_status = "stopped"
            logger.info("Context7 Background Job Manager stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Context7 Background Job Manager: {e}")
            self.health_status = "error"
    
    async def _load_job_configurations(self) -> None:
        """Load job configurations from storage and defaults"""
        try:
            # Load from storage
            stored_jobs = await self.storage.get_all_jobs()
            for job_config in stored_jobs:
                self.job_registry[job_config.job_id] = job_config
            
            # Load default jobs if none exist
            if not self.job_registry and self.config.default_jobs:
                for job_config in self.config.default_jobs:
                    await self.register_job(job_config)
            
            # Create standard Context7 jobs if none exist
            if not self.job_registry:
                await self._create_default_context7_jobs()
            
            logger.info(f"Loaded {len(self.job_registry)} job configurations")
            
        except Exception as e:
            logger.error(f"Failed to load job configurations: {e}")
            raise
    
    async def _create_default_context7_jobs(self) -> None:
        """Create default Context7 jobs"""
        try:
            # Daily TTL cleanup job
            ttl_cleanup_job = JobConfig(
                job_id="context7-ttl-cleanup",
                job_type=JobType.TTL_CLEANUP,
                job_name="Context7 TTL Cleanup",
                description="Daily cleanup of expired Context7 documents",
                enabled=True,
                priority=JobPriority.HIGH,
                schedule=JobSchedule(
                    schedule_type="interval",
                    interval_days=1
                ),
                parameters={
                    "batch_size": self.config.context7_config.ttl_cleanup_batch_size,
                    "max_age_days": self.config.context7_config.ttl_cleanup_max_age_days,
                    "target_workspaces": self.config.context7_config.target_workspaces,
                    "excluded_workspaces": self.config.context7_config.excluded_workspaces
                }
            )
            
            # Weekly document refresh job
            refresh_job = JobConfig(
                job_id="context7-document-refresh",
                job_type=JobType.DOCUMENT_REFRESH,
                job_name="Context7 Document Refresh",
                description="Weekly refresh of near-expired Context7 documents",
                enabled=True,
                priority=JobPriority.MEDIUM,
                schedule=JobSchedule(
                    schedule_type="interval",
                    interval_days=7
                ),
                parameters={
                    "batch_size": self.config.context7_config.refresh_batch_size,
                    "threshold_days": self.config.context7_config.refresh_threshold_days,
                    "max_age_days": self.config.context7_config.refresh_max_age_days,
                    "minimum_quality_score": self.config.context7_config.minimum_quality_score,
                    "target_workspaces": self.config.context7_config.target_workspaces,
                    "excluded_workspaces": self.config.context7_config.excluded_workspaces
                }
            )
            
            # Health check job
            health_check_job = JobConfig(
                job_id="context7-health-check",
                job_type=JobType.HEALTH_CHECK,
                job_name="Context7 Health Check",
                description="Regular health check for Context7 services",
                enabled=True,
                priority=JobPriority.LOW,
                schedule=JobSchedule(
                    schedule_type="interval",
                    interval_seconds=self.config.health_check_interval_seconds
                ),
                parameters={}
            )
            
            # Register jobs
            await self.register_job(ttl_cleanup_job)
            await self.register_job(refresh_job)
            await self.register_job(health_check_job)
            
            logger.info("Created default Context7 jobs")
            
        except Exception as e:
            logger.error(f"Failed to create default Context7 jobs: {e}")
            raise
    
    async def register_job(self, job_config: JobConfig) -> None:
        """Register a new job configuration"""
        try:
            # Validate job configuration
            if job_config.job_id in self.job_registry:
                logger.warning(f"Job {job_config.job_id} already exists, updating")
            
            # Store in registry
            self.job_registry[job_config.job_id] = job_config
            
            # Persist to storage
            await self.storage.save_job(job_config)
            
            # Initialize metrics
            if job_config.job_id not in self.metrics:
                self.metrics[job_config.job_id] = JobMetrics()
            
            # Schedule job
            await self.scheduler.schedule_job(job_config)
            
            logger.info(f"Registered job: {job_config.job_id}")
            
        except Exception as e:
            logger.error(f"Failed to register job {job_config.job_id}: {e}")
            raise
    
    async def unregister_job(self, job_id: str) -> None:
        """Unregister a job"""
        try:
            if job_id not in self.job_registry:
                logger.warning(f"Job {job_id} not found in registry")
                return
            
            # Cancel if running
            if job_id in self.running_jobs:
                running_job = self.running_jobs[job_id]
                if not running_job.task.done():
                    running_job.task.cancel()
                    logger.info(f"Cancelled running job: {job_id}")
            
            # Remove from scheduler
            await self.scheduler.unschedule_job(job_id)
            
            # Remove from registry
            del self.job_registry[job_id]
            
            # Remove from storage
            await self.storage.delete_job(job_id)
            
            logger.info(f"Unregistered job: {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to unregister job {job_id}: {e}")
            raise
    
    async def execute_job(self, job_id: str, correlation_id: str = None) -> JobExecution:
        """Execute a job immediately"""
        try:
            if job_id not in self.job_registry:
                raise ValueError(f"Job {job_id} not found in registry")
            
            job_config = self.job_registry[job_id]
            
            if correlation_id is None:
                correlation_id = f"manual_{uuid.uuid4().hex[:8]}"
            
            # Create execution record
            execution = JobExecution(
                execution_id=f"{job_id}_{uuid.uuid4().hex[:8]}",
                job_id=job_id,
                status=JobStatus.PENDING,
                correlation_id=correlation_id
            )
            
            # Queue the job
            await self.job_queue.put((job_config, execution))
            
            logger.info(f"Queued job for execution: {job_id}")
            return execution
            
        except Exception as e:
            logger.error(f"Failed to execute job {job_id}: {e}")
            raise
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop"""
        logger.info("Starting scheduler loop")
        
        while not self.shutdown_event.is_set():
            try:
                # Check for scheduled jobs
                due_jobs = await self.scheduler.get_due_jobs()
                
                for job_config in due_jobs:
                    if job_config.enabled:
                        correlation_id = f"scheduled_{uuid.uuid4().hex[:8]}"
                        
                        # Create execution record
                        execution = JobExecution(
                            execution_id=f"{job_config.job_id}_{uuid.uuid4().hex[:8]}",
                            job_id=job_config.job_id,
                            status=JobStatus.PENDING,
                            correlation_id=correlation_id
                        )
                        
                        # Queue the job
                        try:
                            await self.job_queue.put((job_config, execution))
                            logger.info(f"Scheduled job queued: {job_config.job_id}")
                        except asyncio.QueueFull:
                            logger.warning(f"Job queue full, skipping job: {job_config.job_id}")
                
                # Wait for next check
                await asyncio.sleep(self.config.scheduler_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self.config.scheduler_interval_seconds)
        
        logger.info("Scheduler loop stopped")
    
    async def _worker_loop(self, worker_id: str) -> None:
        """Worker loop for processing jobs"""
        logger.info(f"Starting worker loop: {worker_id}")
        
        while not self.shutdown_event.is_set():
            try:
                # Get job from queue
                try:
                    job_config, execution = await asyncio.wait_for(
                        self.job_queue.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # Check if job is still enabled
                if not job_config.enabled:
                    logger.info(f"Skipping disabled job: {job_config.job_id}")
                    continue
                
                # Check concurrent execution limits
                running_count = sum(
                    1 for job in self.running_jobs.values()
                    if job.job_id == job_config.job_id
                )
                
                if running_count >= job_config.max_concurrent_executions:
                    logger.warning(f"Job {job_config.job_id} at max concurrent executions")
                    # Re-queue for later
                    await self.job_queue.put((job_config, execution))
                    continue
                
                # Execute job
                await self._execute_job_internal(job_config, execution, worker_id)
                
            except Exception as e:
                logger.error(f"Error in worker loop {worker_id}: {e}")
                await asyncio.sleep(1)
        
        logger.info(f"Worker loop stopped: {worker_id}")
    
    async def _execute_job_internal(
        self, 
        job_config: JobConfig, 
        execution: JobExecution,
        worker_id: str
    ) -> None:
        """Execute a job internally"""
        start_time = time.time()
        
        try:
            logger.info(f"Starting job execution: {job_config.job_id} "
                       f"(execution_id: {execution.execution_id}, worker: {worker_id})")
            
            # Update execution status
            execution.status = JobStatus.RUNNING
            execution.started_at = datetime.utcnow()
            
            # Store execution
            await self.storage.save_execution(execution)
            
            # Create running job record
            job_task = asyncio.create_task(
                self._run_job_with_timeout(job_config, execution)
            )
            
            running_job = RunningJob(
                execution_id=execution.execution_id,
                job_id=job_config.job_id,
                job_config=job_config,
                task=job_task,
                started_at=execution.started_at,
                correlation_id=execution.correlation_id
            )
            
            self.running_jobs[execution.execution_id] = running_job
            
            # Wait for job completion
            try:
                result = await job_task
                
                # Update execution with result
                execution.status = JobStatus.COMPLETED
                execution.result = result
                execution.completed_at = datetime.utcnow()
                execution.duration_seconds = time.time() - start_time
                
                # Update metrics
                await self._update_job_metrics(job_config.job_id, execution, True)
                
                logger.info(f"Job completed successfully: {job_config.job_id} "
                           f"(duration: {execution.duration_seconds:.2f}s)")
                
            except asyncio.CancelledError:
                execution.status = JobStatus.CANCELLED
                execution.error_message = "Job was cancelled"
                execution.completed_at = datetime.utcnow()
                execution.duration_seconds = time.time() - start_time
                
                logger.warning(f"Job cancelled: {job_config.job_id}")
                
            except Exception as e:
                execution.status = JobStatus.FAILED
                execution.error_message = str(e)
                execution.error_details = {
                    "error_type": type(e).__name__,
                    "worker_id": worker_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
                execution.completed_at = datetime.utcnow()
                execution.duration_seconds = time.time() - start_time
                
                # Update metrics
                await self._update_job_metrics(job_config.job_id, execution, False)
                
                logger.error(f"Job failed: {job_config.job_id} - {e}")
                
                # Check if job should be retried
                if execution.retry_count < job_config.retry_config.max_retries:
                    await self._schedule_retry(job_config, execution)
            
            # Store final execution state
            await self.storage.save_execution(execution)
            
        except Exception as e:
            logger.error(f"Critical error in job execution: {e}")
            execution.status = JobStatus.FAILED
            execution.error_message = f"Critical execution error: {e}"
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = time.time() - start_time
            
            try:
                await self.storage.save_execution(execution)
            except Exception as storage_error:
                logger.error(f"Failed to save execution state: {storage_error}")
        
        finally:
            # Remove from running jobs
            if execution.execution_id in self.running_jobs:
                del self.running_jobs[execution.execution_id]
    
    async def _run_job_with_timeout(
        self, 
        job_config: JobConfig, 
        execution: JobExecution
    ) -> Dict[str, Any]:
        """Run job with timeout protection"""
        try:
            # Get job handler
            handler = self.job_handlers.get(job_config.job_type)
            if not handler:
                raise ValueError(f"No handler for job type: {job_config.job_type}")
            
            # Execute with timeout
            result = await asyncio.wait_for(
                handler(job_config, execution),
                timeout=job_config.timeout_seconds
            )
            
            return result
            
        except asyncio.TimeoutError:
            raise Exception(f"Job timed out after {job_config.timeout_seconds} seconds")
    
    async def _schedule_retry(self, job_config: JobConfig, execution: JobExecution) -> None:
        """Schedule a job retry"""
        try:
            retry_config = job_config.retry_config
            
            # Calculate retry delay with exponential backoff
            delay = retry_config.retry_delay_seconds * (
                retry_config.retry_backoff_multiplier ** execution.retry_count
            )
            delay = min(delay, retry_config.retry_max_delay_seconds)
            
            # Create retry execution
            retry_execution = JobExecution(
                execution_id=f"{job_config.job_id}_retry_{execution.retry_count + 1}_{uuid.uuid4().hex[:8]}",
                job_id=job_config.job_id,
                status=JobStatus.RETRY,
                retry_count=execution.retry_count + 1,
                correlation_id=execution.correlation_id
            )
            
            # Schedule retry
            await asyncio.sleep(delay)
            await self.job_queue.put((job_config, retry_execution))
            
            logger.info(f"Scheduled retry for job {job_config.job_id} "
                       f"(attempt {retry_execution.retry_count} after {delay}s)")
            
        except Exception as e:
            logger.error(f"Failed to schedule retry for job {job_config.job_id}: {e}")
    
    async def _update_job_metrics(
        self, 
        job_id: str, 
        execution: JobExecution, 
        success: bool
    ) -> None:
        """Update job metrics"""
        try:
            if job_id not in self.metrics:
                self.metrics[job_id] = JobMetrics()
            
            metrics = self.metrics[job_id]
            
            # Update execution counts
            metrics.total_executions += 1
            if success:
                metrics.successful_executions += 1
                metrics.consecutive_failures = 0
                metrics.last_success_at = execution.completed_at
            else:
                metrics.failed_executions += 1
                metrics.consecutive_failures += 1
                metrics.last_failure_at = execution.completed_at
            
            # Update timing metrics
            if execution.duration_seconds:
                duration = execution.duration_seconds
                if metrics.total_executions == 1:
                    metrics.average_duration_seconds = duration
                    metrics.min_duration_seconds = duration
                    metrics.max_duration_seconds = duration
                else:
                    metrics.average_duration_seconds = (
                        (metrics.average_duration_seconds * (metrics.total_executions - 1) + duration) /
                        metrics.total_executions
                    )
                    metrics.min_duration_seconds = min(metrics.min_duration_seconds, duration)
                    metrics.max_duration_seconds = max(metrics.max_duration_seconds, duration)
            
            # Update processing metrics
            if execution.records_processed:
                metrics.total_records_processed += execution.records_processed
            if execution.records_failed:
                metrics.total_records_failed += execution.records_failed
            
            # Update error rate
            if metrics.total_executions > 0:
                metrics.error_rate = (metrics.failed_executions / metrics.total_executions) * 100
            
            # Update health status
            if metrics.consecutive_failures >= 3:
                metrics.health_status = "unhealthy"
            elif metrics.consecutive_failures >= 1:
                metrics.health_status = "degraded"
            else:
                metrics.health_status = "healthy"
            
            metrics.last_execution_at = execution.completed_at
            
        except Exception as e:
            logger.error(f"Failed to update metrics for job {job_id}: {e}")
    
    async def _monitor_loop(self) -> None:
        """Monitor loop for health checks and metrics"""
        logger.info("Starting monitor loop")
        
        while not self.shutdown_event.is_set():
            try:
                # Export metrics
                await self._export_metrics()
                
                # Check job health
                await self._check_job_health()
                
                # Cleanup old executions
                await self._cleanup_old_executions()
                
                # Wait for next check
                await asyncio.sleep(self.config.metrics_export_interval_seconds)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(self.config.metrics_export_interval_seconds)
        
        logger.info("Monitor loop stopped")
    
    async def _export_metrics(self) -> None:
        """Export job metrics"""
        try:
            for job_id, metrics in self.metrics.items():
                logger.info(f"PIPELINE_METRICS: job_id={job_id} "
                           f"total_executions={metrics.total_executions} "
                           f"successful_executions={metrics.successful_executions} "
                           f"failed_executions={metrics.failed_executions} "
                           f"error_rate={metrics.error_rate:.2f}% "
                           f"average_duration={metrics.average_duration_seconds:.2f}s "
                           f"health_status={metrics.health_status} "
                           f"consecutive_failures={metrics.consecutive_failures}")
        
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
    
    async def _check_job_health(self) -> None:
        """Check overall job health"""
        try:
            healthy_jobs = 0
            total_jobs = len(self.metrics)
            
            for job_id, metrics in self.metrics.items():
                if metrics.health_status == "healthy":
                    healthy_jobs += 1
            
            if total_jobs == 0:
                self.health_status = "unknown"
            elif healthy_jobs == total_jobs:
                self.health_status = "healthy"
            elif healthy_jobs > total_jobs * 0.5:
                self.health_status = "degraded"
            else:
                self.health_status = "unhealthy"
            
            logger.info(f"Overall job health: {self.health_status} "
                       f"({healthy_jobs}/{total_jobs} healthy)")
        
        except Exception as e:
            logger.error(f"Failed to check job health: {e}")
            self.health_status = "error"
    
    async def _cleanup_old_executions(self) -> None:
        """Clean up old job executions"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.config.job_history_retention_days)
            cleaned_count = await self.storage.cleanup_old_executions(cutoff_date)
            
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} old job executions")
        
        except Exception as e:
            logger.error(f"Failed to cleanup old executions: {e}")
    
    # Job handlers
    async def _handle_ttl_cleanup(self, job_config: JobConfig, execution: JobExecution) -> Dict[str, Any]:
        """Handle TTL cleanup job"""
        from .jobs import TTLCleanupJob
        
        ttl_job = TTLCleanupJob(
            context7_service=self.context7_service,
            weaviate_client=self.weaviate_client,
            db_manager=self.db_manager,
            config=self.config.context7_config
        )
        
        return await ttl_job.execute(job_config, execution)
    
    async def _handle_document_refresh(self, job_config: JobConfig, execution: JobExecution) -> Dict[str, Any]:
        """Handle document refresh job"""
        from .jobs import DocumentRefreshJob
        
        refresh_job = DocumentRefreshJob(
            context7_service=self.context7_service,
            weaviate_client=self.weaviate_client,
            db_manager=self.db_manager,
            llm_client=self.llm_client,
            config=self.config.context7_config
        )
        
        return await refresh_job.execute(job_config, execution)
    
    async def _handle_health_check(self, job_config: JobConfig, execution: JobExecution) -> Dict[str, Any]:
        """Handle health check job"""
        from .jobs import HealthCheckJob
        
        health_job = HealthCheckJob(
            context7_service=self.context7_service,
            weaviate_client=self.weaviate_client,
            db_manager=self.db_manager,
            config=self.config.context7_config
        )
        
        return await health_job.execute(job_config, execution)
    
    async def _handle_maintenance(self, job_config: JobConfig, execution: JobExecution) -> Dict[str, Any]:
        """Handle maintenance job"""
        # Basic maintenance operations
        result = {
            "status": "completed",
            "operations": [],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Add maintenance operations as needed
        return result
    
    # Public API methods
    async def get_job_status(self, job_id: str) -> Optional[JobConfig]:
        """Get job status"""
        return self.job_registry.get(job_id)
    
    async def get_job_metrics(self, job_id: str) -> Optional[JobMetrics]:
        """Get job metrics"""
        return self.metrics.get(job_id)
    
    async def get_running_jobs(self) -> List[Dict[str, Any]]:
        """Get currently running jobs"""
        return [
            {
                "execution_id": job.execution_id,
                "job_id": job.job_id,
                "job_name": job.job_config.job_name,
                "started_at": job.started_at.isoformat(),
                "correlation_id": job.correlation_id,
                "status": job.status.value
            }
            for job in self.running_jobs.values()
        ]
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        return {
            "status": self.health_status,
            "total_jobs": len(self.job_registry),
            "running_jobs": len(self.running_jobs),
            "queue_size": self.job_queue.qsize(),
            "metrics": {
                job_id: {
                    "health_status": metrics.health_status,
                    "consecutive_failures": metrics.consecutive_failures,
                    "last_execution": metrics.last_execution_at.isoformat() if metrics.last_execution_at else None
                }
                for job_id, metrics in self.metrics.items()
            }
        }