"""
Background Job Models for Context7 Document TTL Management
==========================================================

Configuration models and data structures for managing Context7 document
TTL cleanup and refresh operations through scheduled background jobs.
"""

import json
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"


class JobType(str, Enum):
    """Type of background job"""
    TTL_CLEANUP = "ttl_cleanup"
    DOCUMENT_REFRESH = "document_refresh"
    HEALTH_CHECK = "health_check"
    MAINTENANCE = "maintenance"


class JobPriority(str, Enum):
    """Job priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class JobSchedule(BaseModel):
    """Job scheduling configuration"""
    
    # Schedule type
    schedule_type: str = Field(
        "interval", 
        description="Schedule type: interval, cron, or once"
    )
    
    # Interval settings
    interval_seconds: Optional[int] = Field(
        None, 
        description="Interval in seconds for periodic jobs"
    )
    interval_minutes: Optional[int] = Field(
        None,
        description="Interval in minutes for periodic jobs"
    )
    interval_hours: Optional[int] = Field(
        None,
        description="Interval in hours for periodic jobs"
    )
    interval_days: Optional[int] = Field(
        None,
        description="Interval in days for periodic jobs"
    )
    
    # Cron expression (alternative to interval)
    cron_expression: Optional[str] = Field(
        None,
        description="Cron expression for complex scheduling"
    )
    
    # One-time execution
    execute_at: Optional[datetime] = Field(
        None,
        description="Specific datetime for one-time execution"
    )
    
    # Schedule bounds
    start_time: Optional[datetime] = Field(
        None,
        description="When to start the schedule"
    )
    end_time: Optional[datetime] = Field(
        None,
        description="When to end the schedule"
    )
    
    # Execution limits
    max_executions: Optional[int] = Field(
        None,
        description="Maximum number of executions"
    )
    
    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        """Validate cron expression format"""
        if v is None:
            return v
        
        # Basic cron validation (5 or 6 fields)
        parts = v.split()
        if len(parts) not in [5, 6]:
            raise ValueError("Cron expression must have 5 or 6 fields")
        
        return v


class RetryConfig(BaseModel):
    """Configuration for job retry behavior"""
    
    max_retries: int = Field(
        3,
        ge=0,
        le=10,
        description="Maximum number of retry attempts"
    )
    
    retry_delay_seconds: int = Field(
        60,
        ge=1,
        description="Initial delay between retries in seconds"
    )
    
    retry_backoff_multiplier: float = Field(
        2.0,
        ge=1.0,
        le=10.0,
        description="Multiplier for exponential backoff"
    )
    
    retry_max_delay_seconds: int = Field(
        3600,
        ge=1,
        description="Maximum delay between retries in seconds"
    )
    
    retry_on_errors: List[str] = Field(
        default_factory=lambda: [
            "ConnectionError",
            "TimeoutError",
            "WeaviateError",
            "DatabaseError"
        ],
        description="Error types that should trigger retries"
    )


class JobConfig(BaseModel):
    """Configuration for a specific job"""
    
    job_id: str = Field(
        description="Unique identifier for the job"
    )
    
    job_type: JobType = Field(
        description="Type of job to execute"
    )
    
    job_name: str = Field(
        description="Human-readable name for the job"
    )
    
    description: Optional[str] = Field(
        None,
        description="Description of what the job does"
    )
    
    enabled: bool = Field(
        True,
        description="Whether the job is enabled"
    )
    
    priority: JobPriority = Field(
        JobPriority.MEDIUM,
        description="Job priority level"
    )
    
    schedule: JobSchedule = Field(
        description="Scheduling configuration"
    )
    
    retry_config: RetryConfig = Field(
        default_factory=RetryConfig,
        description="Retry configuration"
    )
    
    timeout_seconds: int = Field(
        3600,
        ge=1,
        description="Job execution timeout in seconds"
    )
    
    # Job-specific parameters
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Job-specific parameters"
    )
    
    # Resource constraints
    max_concurrent_executions: int = Field(
        1,
        ge=1,
        description="Maximum concurrent executions of this job"
    )
    
    # Monitoring
    alert_on_failure: bool = Field(
        True,
        description="Whether to alert on job failure"
    )
    
    alert_on_success: bool = Field(
        False,
        description="Whether to alert on job success"
    )


class JobExecution(BaseModel):
    """Record of a job execution"""
    
    execution_id: str = Field(
        description="Unique identifier for this execution"
    )
    
    job_id: str = Field(
        description="ID of the job that was executed"
    )
    
    status: JobStatus = Field(
        JobStatus.PENDING,
        description="Current status of the execution"
    )
    
    started_at: Optional[datetime] = Field(
        None,
        description="When the execution started"
    )
    
    completed_at: Optional[datetime] = Field(
        None,
        description="When the execution completed"
    )
    
    duration_seconds: Optional[float] = Field(
        None,
        description="Execution duration in seconds"
    )
    
    retry_count: int = Field(
        0,
        ge=0,
        description="Number of retry attempts"
    )
    
    error_message: Optional[str] = Field(
        None,
        description="Error message if execution failed"
    )
    
    error_details: Optional[Dict[str, Any]] = Field(
        None,
        description="Detailed error information"
    )
    
    result: Optional[Dict[str, Any]] = Field(
        None,
        description="Job execution result"
    )
    
    correlation_id: Optional[str] = Field(
        None,
        description="Correlation ID for tracking"
    )
    
    # Metrics
    records_processed: int = Field(
        0,
        ge=0,
        description="Number of records processed"
    )
    
    records_failed: int = Field(
        0,
        ge=0,
        description="Number of records that failed"
    )
    
    memory_usage_mb: Optional[float] = Field(
        None,
        description="Peak memory usage in MB"
    )
    
    cpu_usage_percent: Optional[float] = Field(
        None,
        description="Average CPU usage percentage"
    )


class Context7JobConfig(BaseModel):
    """Context7-specific job configuration"""
    
    # TTL cleanup job settings
    ttl_cleanup_batch_size: int = Field(
        50,
        ge=1,
        le=500,
        description="Number of documents to process in each cleanup batch"
    )
    
    ttl_cleanup_max_age_days: int = Field(
        90,
        ge=1,
        description="Maximum age in days before forced cleanup"
    )
    
    # Document refresh job settings
    refresh_batch_size: int = Field(
        20,
        ge=1,
        le=100,
        description="Number of documents to refresh in each batch"
    )
    
    refresh_threshold_days: int = Field(
        7,
        ge=1,
        description="Days before expiration to trigger refresh"
    )
    
    refresh_max_age_days: int = Field(
        30,
        ge=1,
        description="Maximum age in days before refresh is required"
    )
    
    # Workspace settings
    target_workspaces: List[str] = Field(
        default_factory=list,
        description="Specific workspaces to process (empty = all)"
    )
    
    excluded_workspaces: List[str] = Field(
        default_factory=list,
        description="Workspaces to exclude from processing"
    )
    
    # Performance settings
    max_concurrent_workspace_jobs: int = Field(
        3,
        ge=1,
        le=10,
        description="Maximum concurrent workspace processing jobs"
    )
    
    rate_limit_delay_seconds: float = Field(
        1.0,
        ge=0.1,
        description="Delay between operations to avoid overwhelming services"
    )
    
    # Quality settings
    minimum_quality_score: float = Field(
        0.3,
        ge=0.0,
        le=1.0,
        description="Minimum quality score for document refresh"
    )
    
    skip_recent_updates: bool = Field(
        True,
        description="Skip documents updated within the last hour"
    )


class BackgroundJobManagerConfig(BaseModel):
    """Configuration for the background job manager"""
    
    # Manager settings
    enabled: bool = Field(
        True,
        description="Whether the background job manager is enabled"
    )
    
    max_concurrent_jobs: int = Field(
        5,
        ge=1,
        le=20,
        description="Maximum concurrent job executions"
    )
    
    job_queue_size: int = Field(
        100,
        ge=10,
        description="Maximum number of jobs in the queue"
    )
    
    # Scheduling settings
    scheduler_interval_seconds: int = Field(
        60,
        ge=1,
        description="How often to check for scheduled jobs"
    )
    
    # Persistence settings
    job_history_retention_days: int = Field(
        30,
        ge=1,
        description="How long to keep job execution history"
    )
    
    # Monitoring settings
    health_check_interval_seconds: int = Field(
        300,
        ge=60,
        description="Health check interval in seconds"
    )
    
    metrics_export_interval_seconds: int = Field(
        60,
        ge=10,
        description="Metrics export interval in seconds"
    )
    
    # Error handling
    dead_letter_queue_enabled: bool = Field(
        True,
        description="Whether to use dead letter queue for failed jobs"
    )
    
    max_failed_jobs_retention: int = Field(
        1000,
        ge=100,
        description="Maximum number of failed jobs to retain"
    )
    
    # Context7-specific settings
    context7_config: Context7JobConfig = Field(
        default_factory=Context7JobConfig,
        description="Context7-specific job configuration"
    )
    
    # Default job configurations
    default_jobs: List[JobConfig] = Field(
        default_factory=list,
        description="Default jobs to create on startup"
    )
    
    @field_validator("default_jobs", mode="before")
    @classmethod
    def validate_default_jobs(cls, v: Union[List[Dict[str, Any]], List[JobConfig]]) -> List[JobConfig]:
        """Validate and convert default jobs configuration"""
        if not v:
            return []
        
        jobs = []
        for job_data in v:
            if isinstance(job_data, dict):
                try:
                    job_config = JobConfig(**job_data)
                    jobs.append(job_config)
                except Exception as e:
                    logger.error(f"Failed to parse job configuration: {e}")
                    continue
            elif isinstance(job_data, JobConfig):
                jobs.append(job_data)
            else:
                logger.warning(f"Ignoring invalid job configuration: {job_data}")
        
        return jobs


class JobMetrics(BaseModel):
    """Metrics for job execution monitoring"""
    
    # Execution metrics
    total_executions: int = Field(0, description="Total number of executions")
    successful_executions: int = Field(0, description="Number of successful executions")
    failed_executions: int = Field(0, description="Number of failed executions")
    
    # Timing metrics
    average_duration_seconds: float = Field(0.0, description="Average execution duration")
    min_duration_seconds: float = Field(0.0, description="Minimum execution duration")
    max_duration_seconds: float = Field(0.0, description="Maximum execution duration")
    
    # Processing metrics
    total_records_processed: int = Field(0, description="Total records processed")
    total_records_failed: int = Field(0, description="Total records failed")
    
    # Resource metrics
    average_memory_usage_mb: float = Field(0.0, description="Average memory usage")
    peak_memory_usage_mb: float = Field(0.0, description="Peak memory usage")
    average_cpu_usage_percent: float = Field(0.0, description="Average CPU usage")
    
    # Error metrics
    error_rate: float = Field(0.0, description="Error rate as percentage")
    retry_rate: float = Field(0.0, description="Retry rate as percentage")
    
    # Last execution
    last_execution_at: Optional[datetime] = Field(None, description="Last execution time")
    last_success_at: Optional[datetime] = Field(None, description="Last successful execution")
    last_failure_at: Optional[datetime] = Field(None, description="Last failed execution")
    
    # Health status
    health_status: str = Field("unknown", description="Overall health status")
    consecutive_failures: int = Field(0, description="Number of consecutive failures")