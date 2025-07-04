"""
Job Storage for Context7 Background Jobs
=========================================

Provides persistent storage for job configurations and execution history
using the existing database infrastructure.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .models import JobConfig, JobExecution, JobStatus, JobType
from src.database.manager import DatabaseManager

logger = logging.getLogger(__name__)


class JobStorage:
    """
    Persistent storage for background jobs
    
    Handles:
    - Job configuration storage
    - Job execution history
    - Job metrics persistence
    - Cleanup of old records
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._initialized = False
        
        logger.info("Job storage initialized")
    
    async def initialize(self) -> None:
        """Initialize storage tables"""
        if self._initialized:
            return
        
        try:
            # Create job configurations table
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS background_job_configs (
                    job_id VARCHAR(255) PRIMARY KEY,
                    job_name VARCHAR(255) NOT NULL,
                    job_type VARCHAR(50) NOT NULL,
                    description TEXT,
                    enabled BOOLEAN NOT NULL DEFAULT TRUE,
                    priority VARCHAR(20) NOT NULL DEFAULT 'medium',
                    schedule_config JSONB NOT NULL,
                    retry_config JSONB NOT NULL,
                    timeout_seconds INTEGER NOT NULL DEFAULT 3600,
                    parameters JSONB NOT NULL DEFAULT '{}',
                    max_concurrent_executions INTEGER NOT NULL DEFAULT 1,
                    alert_on_failure BOOLEAN NOT NULL DEFAULT TRUE,
                    alert_on_success BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create job executions table
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS background_job_executions (
                    execution_id VARCHAR(255) PRIMARY KEY,
                    job_id VARCHAR(255) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    duration_seconds FLOAT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    error_details JSONB,
                    result JSONB,
                    correlation_id VARCHAR(255),
                    records_processed INTEGER NOT NULL DEFAULT 0,
                    records_failed INTEGER NOT NULL DEFAULT 0,
                    memory_usage_mb FLOAT,
                    cpu_usage_percent FLOAT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES background_job_configs(job_id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            await self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_executions_job_id 
                ON background_job_executions(job_id)
            """)
            
            await self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_executions_status 
                ON background_job_executions(status)
            """)
            
            await self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_executions_created_at 
                ON background_job_executions(created_at)
            """)
            
            await self.db.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_executions_correlation_id 
                ON background_job_executions(correlation_id)
            """)
            
            # Create job metrics table
            await self.db.execute("""
                CREATE TABLE IF NOT EXISTS background_job_metrics (
                    job_id VARCHAR(255) PRIMARY KEY,
                    total_executions INTEGER NOT NULL DEFAULT 0,
                    successful_executions INTEGER NOT NULL DEFAULT 0,
                    failed_executions INTEGER NOT NULL DEFAULT 0,
                    average_duration_seconds FLOAT NOT NULL DEFAULT 0,
                    min_duration_seconds FLOAT NOT NULL DEFAULT 0,
                    max_duration_seconds FLOAT NOT NULL DEFAULT 0,
                    total_records_processed INTEGER NOT NULL DEFAULT 0,
                    total_records_failed INTEGER NOT NULL DEFAULT 0,
                    average_memory_usage_mb FLOAT NOT NULL DEFAULT 0,
                    peak_memory_usage_mb FLOAT NOT NULL DEFAULT 0,
                    average_cpu_usage_percent FLOAT NOT NULL DEFAULT 0,
                    error_rate FLOAT NOT NULL DEFAULT 0,
                    retry_rate FLOAT NOT NULL DEFAULT 0,
                    last_execution_at TIMESTAMP,
                    last_success_at TIMESTAMP,
                    last_failure_at TIMESTAMP,
                    health_status VARCHAR(20) NOT NULL DEFAULT 'unknown',
                    consecutive_failures INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (job_id) REFERENCES background_job_configs(job_id) ON DELETE CASCADE
                )
            """)
            
            logger.info("Job storage tables initialized")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Failed to initialize job storage: {e}")
            raise
    
    async def save_job(self, job_config: JobConfig) -> None:
        """Save job configuration"""
        try:
            await self.db.execute("""
                INSERT INTO background_job_configs (
                    job_id, job_name, job_type, description, enabled, priority,
                    schedule_config, retry_config, timeout_seconds, parameters,
                    max_concurrent_executions, alert_on_failure, alert_on_success
                ) VALUES (
                    :job_id, :job_name, :job_type, :description, :enabled, :priority,
                    :schedule_config, :retry_config, :timeout_seconds, :parameters,
                    :max_concurrent_executions, :alert_on_failure, :alert_on_success
                ) ON CONFLICT (job_id) DO UPDATE SET
                    job_name = EXCLUDED.job_name,
                    job_type = EXCLUDED.job_type,
                    description = EXCLUDED.description,
                    enabled = EXCLUDED.enabled,
                    priority = EXCLUDED.priority,
                    schedule_config = EXCLUDED.schedule_config,
                    retry_config = EXCLUDED.retry_config,
                    timeout_seconds = EXCLUDED.timeout_seconds,
                    parameters = EXCLUDED.parameters,
                    max_concurrent_executions = EXCLUDED.max_concurrent_executions,
                    alert_on_failure = EXCLUDED.alert_on_failure,
                    alert_on_success = EXCLUDED.alert_on_success,
                    updated_at = CURRENT_TIMESTAMP
            """, {
                "job_id": job_config.job_id,
                "job_name": job_config.job_name,
                "job_type": job_config.job_type.value,
                "description": job_config.description,
                "enabled": job_config.enabled,
                "priority": job_config.priority.value,
                "schedule_config": json.dumps(job_config.schedule.dict()),
                "retry_config": json.dumps(job_config.retry_config.dict()),
                "timeout_seconds": job_config.timeout_seconds,
                "parameters": json.dumps(job_config.parameters),
                "max_concurrent_executions": job_config.max_concurrent_executions,
                "alert_on_failure": job_config.alert_on_failure,
                "alert_on_success": job_config.alert_on_success
            })
            
            logger.debug(f"Saved job configuration: {job_config.job_id}")
            
        except Exception as e:
            logger.error(f"Failed to save job configuration {job_config.job_id}: {e}")
            raise
    
    async def get_job(self, job_id: str) -> Optional[JobConfig]:
        """Get job configuration by ID"""
        try:
            result = await self.db.fetch_one("""
                SELECT * FROM background_job_configs WHERE job_id = :job_id
            """, {"job_id": job_id})
            
            if not result:
                return None
            
            return self._row_to_job_config(result)
            
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {e}")
            return None
    
    async def get_all_jobs(self) -> List[JobConfig]:
        """Get all job configurations"""
        try:
            results = await self.db.fetch_all("""
                SELECT * FROM background_job_configs ORDER BY created_at
            """)
            
            return [self._row_to_job_config(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get all jobs: {e}")
            return []
    
    async def delete_job(self, job_id: str) -> None:
        """Delete job configuration"""
        try:
            await self.db.execute("""
                DELETE FROM background_job_configs WHERE job_id = :job_id
            """, {"job_id": job_id})
            
            logger.debug(f"Deleted job configuration: {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {e}")
            raise
    
    async def save_execution(self, execution: JobExecution) -> None:
        """Save job execution record"""
        try:
            await self.db.execute("""
                INSERT INTO background_job_executions (
                    execution_id, job_id, status, started_at, completed_at,
                    duration_seconds, retry_count, error_message, error_details,
                    result, correlation_id, records_processed, records_failed,
                    memory_usage_mb, cpu_usage_percent
                ) VALUES (
                    :execution_id, :job_id, :status, :started_at, :completed_at,
                    :duration_seconds, :retry_count, :error_message, :error_details,
                    :result, :correlation_id, :records_processed, :records_failed,
                    :memory_usage_mb, :cpu_usage_percent
                ) ON CONFLICT (execution_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    started_at = EXCLUDED.started_at,
                    completed_at = EXCLUDED.completed_at,
                    duration_seconds = EXCLUDED.duration_seconds,
                    retry_count = EXCLUDED.retry_count,
                    error_message = EXCLUDED.error_message,
                    error_details = EXCLUDED.error_details,
                    result = EXCLUDED.result,
                    records_processed = EXCLUDED.records_processed,
                    records_failed = EXCLUDED.records_failed,
                    memory_usage_mb = EXCLUDED.memory_usage_mb,
                    cpu_usage_percent = EXCLUDED.cpu_usage_percent,
                    updated_at = CURRENT_TIMESTAMP
            """, {
                "execution_id": execution.execution_id,
                "job_id": execution.job_id,
                "status": execution.status.value,
                "started_at": execution.started_at,
                "completed_at": execution.completed_at,
                "duration_seconds": execution.duration_seconds,
                "retry_count": execution.retry_count,
                "error_message": execution.error_message,
                "error_details": json.dumps(execution.error_details) if execution.error_details else None,
                "result": json.dumps(execution.result) if execution.result else None,
                "correlation_id": execution.correlation_id,
                "records_processed": execution.records_processed,
                "records_failed": execution.records_failed,
                "memory_usage_mb": execution.memory_usage_mb,
                "cpu_usage_percent": execution.cpu_usage_percent
            })
            
            logger.debug(f"Saved job execution: {execution.execution_id}")
            
        except Exception as e:
            logger.error(f"Failed to save job execution {execution.execution_id}: {e}")
            raise
    
    async def get_execution(self, execution_id: str) -> Optional[JobExecution]:
        """Get job execution by ID"""
        try:
            result = await self.db.fetch_one("""
                SELECT * FROM background_job_executions WHERE execution_id = :execution_id
            """, {"execution_id": execution_id})
            
            if not result:
                return None
            
            return self._row_to_job_execution(result)
            
        except Exception as e:
            logger.error(f"Failed to get job execution {execution_id}: {e}")
            return None
    
    async def get_job_executions(
        self, 
        job_id: str, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[JobExecution]:
        """Get executions for a job"""
        try:
            results = await self.db.fetch_all("""
                SELECT * FROM background_job_executions 
                WHERE job_id = :job_id 
                ORDER BY created_at DESC 
                LIMIT :limit OFFSET :offset
            """, {"job_id": job_id, "limit": limit, "offset": offset})
            
            return [self._row_to_job_execution(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get executions for job {job_id}: {e}")
            return []
    
    async def get_executions_by_status(
        self, 
        status: JobStatus, 
        limit: int = 100
    ) -> List[JobExecution]:
        """Get executions by status"""
        try:
            results = await self.db.fetch_all("""
                SELECT * FROM background_job_executions 
                WHERE status = :status 
                ORDER BY created_at DESC 
                LIMIT :limit
            """, {"status": status.value, "limit": limit})
            
            return [self._row_to_job_execution(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get executions by status {status}: {e}")
            return []
    
    async def get_executions_by_correlation_id(
        self, 
        correlation_id: str
    ) -> List[JobExecution]:
        """Get executions by correlation ID"""
        try:
            results = await self.db.fetch_all("""
                SELECT * FROM background_job_executions 
                WHERE correlation_id = :correlation_id 
                ORDER BY created_at DESC
            """, {"correlation_id": correlation_id})
            
            return [self._row_to_job_execution(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get executions by correlation ID {correlation_id}: {e}")
            return []
    
    async def cleanup_old_executions(self, cutoff_date: datetime) -> int:
        """Clean up old job executions"""
        try:
            result = await self.db.execute("""
                DELETE FROM background_job_executions 
                WHERE created_at < :cutoff_date
            """, {"cutoff_date": cutoff_date})
            
            # Extract rowcount from result
            rowcount = 0
            if hasattr(result, 'rowcount'):
                rowcount = result.rowcount
            
            logger.info(f"Cleaned up {rowcount} old job executions")
            return rowcount
            
        except Exception as e:
            logger.error(f"Failed to cleanup old executions: {e}")
            return 0
    
    async def save_job_metrics(self, job_id: str, metrics: Dict[str, Any]) -> None:
        """Save job metrics"""
        try:
            await self.db.execute("""
                INSERT INTO background_job_metrics (
                    job_id, total_executions, successful_executions, failed_executions,
                    average_duration_seconds, min_duration_seconds, max_duration_seconds,
                    total_records_processed, total_records_failed, average_memory_usage_mb,
                    peak_memory_usage_mb, average_cpu_usage_percent, error_rate,
                    retry_rate, last_execution_at, last_success_at, last_failure_at,
                    health_status, consecutive_failures
                ) VALUES (
                    :job_id, :total_executions, :successful_executions, :failed_executions,
                    :average_duration_seconds, :min_duration_seconds, :max_duration_seconds,
                    :total_records_processed, :total_records_failed, :average_memory_usage_mb,
                    :peak_memory_usage_mb, :average_cpu_usage_percent, :error_rate,
                    :retry_rate, :last_execution_at, :last_success_at, :last_failure_at,
                    :health_status, :consecutive_failures
                ) ON CONFLICT (job_id) DO UPDATE SET
                    total_executions = EXCLUDED.total_executions,
                    successful_executions = EXCLUDED.successful_executions,
                    failed_executions = EXCLUDED.failed_executions,
                    average_duration_seconds = EXCLUDED.average_duration_seconds,
                    min_duration_seconds = EXCLUDED.min_duration_seconds,
                    max_duration_seconds = EXCLUDED.max_duration_seconds,
                    total_records_processed = EXCLUDED.total_records_processed,
                    total_records_failed = EXCLUDED.total_records_failed,
                    average_memory_usage_mb = EXCLUDED.average_memory_usage_mb,
                    peak_memory_usage_mb = EXCLUDED.peak_memory_usage_mb,
                    average_cpu_usage_percent = EXCLUDED.average_cpu_usage_percent,
                    error_rate = EXCLUDED.error_rate,
                    retry_rate = EXCLUDED.retry_rate,
                    last_execution_at = EXCLUDED.last_execution_at,
                    last_success_at = EXCLUDED.last_success_at,
                    last_failure_at = EXCLUDED.last_failure_at,
                    health_status = EXCLUDED.health_status,
                    consecutive_failures = EXCLUDED.consecutive_failures,
                    updated_at = CURRENT_TIMESTAMP
            """, {
                "job_id": job_id,
                **metrics
            })
            
            logger.debug(f"Saved job metrics: {job_id}")
            
        except Exception as e:
            logger.error(f"Failed to save job metrics for {job_id}: {e}")
            raise
    
    async def get_job_metrics(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job metrics"""
        try:
            result = await self.db.fetch_one("""
                SELECT * FROM background_job_metrics WHERE job_id = :job_id
            """, {"job_id": job_id})
            
            if not result:
                return None
            
            return dict(result)
            
        except Exception as e:
            logger.error(f"Failed to get job metrics for {job_id}: {e}")
            return None
    
    async def cleanup(self) -> None:
        """Cleanup storage resources"""
        try:
            # No specific cleanup needed for database storage
            logger.info("Job storage cleanup completed")
            
        except Exception as e:
            logger.error(f"Failed to cleanup job storage: {e}")
    
    def _row_to_job_config(self, row: Any) -> JobConfig:
        """Convert database row to JobConfig"""
        from .models import JobSchedule, RetryConfig, JobType, JobPriority
        
        schedule_data = json.loads(row["schedule_config"])
        retry_data = json.loads(row["retry_config"])
        parameters = json.loads(row["parameters"])
        
        return JobConfig(
            job_id=row["job_id"],
            job_type=JobType(row["job_type"]),
            job_name=row["job_name"],
            description=row["description"],
            enabled=row["enabled"],
            priority=JobPriority(row["priority"]),
            schedule=JobSchedule(**schedule_data),
            retry_config=RetryConfig(**retry_data),
            timeout_seconds=row["timeout_seconds"],
            parameters=parameters,
            max_concurrent_executions=row["max_concurrent_executions"],
            alert_on_failure=row["alert_on_failure"],
            alert_on_success=row["alert_on_success"]
        )
    
    def _row_to_job_execution(self, row: Any) -> JobExecution:
        """Convert database row to JobExecution"""
        error_details = None
        if row["error_details"]:
            error_details = json.loads(row["error_details"])
        
        result = None
        if row["result"]:
            result = json.loads(row["result"])
        
        return JobExecution(
            execution_id=row["execution_id"],
            job_id=row["job_id"],
            status=JobStatus(row["status"]),
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            duration_seconds=row["duration_seconds"],
            retry_count=row["retry_count"],
            error_message=row["error_message"],
            error_details=error_details,
            result=result,
            correlation_id=row["correlation_id"],
            records_processed=row["records_processed"],
            records_failed=row["records_failed"],
            memory_usage_mb=row["memory_usage_mb"],
            cpu_usage_percent=row["cpu_usage_percent"]
        )