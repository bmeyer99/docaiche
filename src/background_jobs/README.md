# Context7 Background Job Framework

A comprehensive background job framework specifically designed for managing Context7 document TTL and refresh operations. This framework provides intelligent scheduling, monitoring, error recovery, and configuration-driven job management.

## Features

### Core Capabilities
- **Daily TTL Cleanup**: Automatically removes expired Context7 documents
- **Weekly Document Refresh**: Updates near-expired documents with fresh content
- **Intelligent Scheduling**: Supports cron expressions and interval-based scheduling
- **Health Monitoring**: Real-time monitoring with alerting and metrics
- **Error Recovery**: Comprehensive retry logic with exponential backoff
- **Persistent Storage**: Job configurations and execution history storage
- **Configuration-Driven**: Flexible configuration for job timing and behavior

### Job Types
1. **TTL Cleanup Job**: Removes expired documents from Weaviate and database
2. **Document Refresh Job**: Re-fetches and processes near-expired documents
3. **Health Check Job**: Monitors service health and connectivity
4. **Maintenance Job**: General maintenance operations

## Architecture

```
Context7BackgroundJobManager
├── JobScheduler          # Handles job scheduling (cron, intervals)
├── JobStorage           # Persistent job and execution storage
├── JobMonitor          # Real-time monitoring and alerting
└── Job Implementations  # Specific job logic (TTL, refresh, health)
```

## Quick Start

### Basic Usage

```python
from src.background_jobs import (
    Context7BackgroundJobManager, 
    BackgroundJobManagerConfig,
    create_default_config
)

# Create configuration
config = create_default_config()

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

# Monitor health
health = await manager.get_health_status()
print(f"Health: {health['status']}")

# Stop gracefully
await manager.stop()
```

### Service Integration

```python
from src.background_jobs.service import BackgroundJobService

# Create service
service = BackgroundJobService(
    context7_service=context7_service,
    weaviate_client=weaviate_client,
    db_manager=db_manager,
    llm_client=llm_client
)

# Use context manager for lifecycle
async with service.lifecycle():
    # Service is running
    info = await service.get_service_info()
    print(f"Service: {info['service_name']}")
```

## Configuration

### Manager Configuration

```python
from src.background_jobs.models import BackgroundJobManagerConfig, Context7JobConfig

config = BackgroundJobManagerConfig(
    enabled=True,
    max_concurrent_jobs=5,
    job_queue_size=100,
    scheduler_interval_seconds=60,
    job_history_retention_days=30,
    health_check_interval_seconds=300,
    context7_config=Context7JobConfig(
        ttl_cleanup_batch_size=50,
        refresh_batch_size=20,
        refresh_threshold_days=7,
        max_concurrent_workspace_jobs=3
    )
)
```

### Job Configuration

```python
from src.background_jobs.models import JobConfig, JobSchedule, JobType, JobPriority

# Daily TTL cleanup at 2 AM
ttl_job = JobConfig(
    job_id="daily-ttl-cleanup",
    job_type=JobType.TTL_CLEANUP,
    job_name="Daily TTL Cleanup",
    schedule=JobSchedule(
        schedule_type="cron",
        cron_expression="0 2 * * *"  # Daily at 2 AM
    ),
    enabled=True,
    priority=JobPriority.HIGH,
    parameters={
        "batch_size": 50,
        "max_age_days": 90
    }
)

# Weekly document refresh on Sunday at 3 AM
refresh_job = JobConfig(
    job_id="weekly-document-refresh",
    job_type=JobType.DOCUMENT_REFRESH,
    job_name="Weekly Document Refresh",
    schedule=JobSchedule(
        schedule_type="cron",
        cron_expression="0 3 * * 0"  # Sunday at 3 AM
    ),
    enabled=True,
    priority=JobPriority.MEDIUM,
    parameters={
        "batch_size": 20,
        "threshold_days": 7,
        "minimum_quality_score": 0.3
    }
)
```

## Scheduling

### Cron Expressions
Standard 5-field cron expressions are supported:
- `0 2 * * *` - Daily at 2 AM
- `0 3 * * 0` - Weekly on Sunday at 3 AM
- `*/15 * * * *` - Every 15 minutes
- `0 */6 * * *` - Every 6 hours

### Interval Scheduling
Time-based intervals:
```python
JobSchedule(
    schedule_type="interval",
    interval_seconds=300,     # Every 5 minutes
    interval_minutes=30,      # Every 30 minutes
    interval_hours=6,         # Every 6 hours
    interval_days=1           # Daily
)
```

### One-time Execution
```python
JobSchedule(
    schedule_type="once",
    execute_at=datetime(2024, 1, 1, 12, 0, 0)
)
```

## Monitoring and Metrics

### Health Monitoring
```python
# Get overall health
health = await manager.get_health_status()

# Get job-specific metrics
metrics = await manager.get_job_metrics("ttl-cleanup-job")

# Get running jobs
running = await manager.get_running_jobs()
```

### PIPELINE_METRICS Logging
The framework provides comprehensive logging with PIPELINE_METRICS format:

```
PIPELINE_METRICS: step=ttl_cleanup_job_start correlation_id=ttl_cleanup_abc123 job_id=daily-ttl-cleanup
PIPELINE_METRICS: step=ttl_cleanup_workspace_complete correlation_id=ttl_cleanup_abc123 workspace=test-workspace duration_ms=1500 deleted_documents=10
PIPELINE_METRICS: step=ttl_cleanup_job_complete correlation_id=ttl_cleanup_abc123 duration_ms=5000 success_rate=100.0%
```

### Metrics Available
- Total executions
- Success/failure rates
- Average execution duration
- Error rates and consecutive failures
- Resource usage (memory, CPU)
- Health status per job

## Error Handling

### Retry Configuration
```python
from src.background_jobs.models import RetryConfig

retry_config = RetryConfig(
    max_retries=3,
    retry_delay_seconds=60,
    retry_backoff_multiplier=2.0,
    retry_max_delay_seconds=3600,
    retry_on_errors=[
        "ConnectionError",
        "TimeoutError", 
        "WeaviateError",
        "DatabaseError"
    ]
)
```

### Error Recovery
- Exponential backoff for retries
- Dead letter queue for failed jobs
- Automatic service recovery
- Comprehensive error logging

## API Endpoints

REST API endpoints for job management (when integrated with FastAPI):

- `GET /api/v1/background-jobs/health` - Overall health status
- `GET /api/v1/background-jobs/jobs` - List all jobs
- `GET /api/v1/background-jobs/jobs/{job_id}` - Get specific job
- `POST /api/v1/background-jobs/jobs/{job_id}/execute` - Execute job immediately
- `POST /api/v1/background-jobs/jobs/{job_id}/enable` - Enable job
- `POST /api/v1/background-jobs/jobs/{job_id}/disable` - Disable job
- `GET /api/v1/background-jobs/executions/running` - Get running jobs
- `GET /api/v1/background-jobs/stats/summary` - Job statistics

## Database Schema

The framework creates the following tables:

### background_job_configs
Stores job configurations:
```sql
CREATE TABLE background_job_configs (
    job_id VARCHAR(255) PRIMARY KEY,
    job_name VARCHAR(255) NOT NULL,
    job_type VARCHAR(50) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    schedule_config JSONB NOT NULL,
    retry_config JSONB NOT NULL,
    -- ... additional fields
);
```

### background_job_executions
Stores execution history:
```sql
CREATE TABLE background_job_executions (
    execution_id VARCHAR(255) PRIMARY KEY,
    job_id VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds FLOAT,
    -- ... additional fields
);
```

### background_job_metrics
Stores aggregated metrics:
```sql
CREATE TABLE background_job_metrics (
    job_id VARCHAR(255) PRIMARY KEY,
    total_executions INTEGER NOT NULL DEFAULT 0,
    successful_executions INTEGER NOT NULL DEFAULT 0,
    failed_executions INTEGER NOT NULL DEFAULT 0,
    -- ... additional metrics
);
```

## Testing

### Running Tests
```bash
# Run comprehensive tests
python test_background_jobs.py

# Expected output:
# ✅ All tests passed successfully
# 🎉 Background job framework is ready for deployment!
```

### Test Coverage
- Configuration model validation
- Job scheduling (cron and interval)
- Job storage and execution history
- Job monitoring and health checks
- TTL cleanup job implementation
- Document refresh job implementation
- Background job manager integration
- Service lifecycle management

## Environment Variables

Configure via environment variables:

```bash
# Service configuration
BG_JOBS_ENABLED=true
BG_JOBS_MAX_CONCURRENT=5
BG_JOBS_QUEUE_SIZE=100
BG_JOBS_SCHEDULER_INTERVAL=60
BG_JOBS_HISTORY_RETENTION=30

# Context7 specific
CTX7_TTL_CLEANUP_BATCH_SIZE=50
CTX7_REFRESH_BATCH_SIZE=20
CTX7_REFRESH_THRESHOLD_DAYS=7
CTX7_MAX_CONCURRENT_WORKSPACE_JOBS=3
```

## Production Deployment

### Docker Configuration
```yaml
# docker-compose.yml
services:
  docaiche:
    environment:
      - BG_JOBS_ENABLED=true
      - BG_JOBS_MAX_CONCURRENT=5
      - CTX7_TTL_CLEANUP_BATCH_SIZE=50
```

### Monitoring Setup
1. **Metrics Collection**: Use PIPELINE_METRICS logs for monitoring
2. **Health Checks**: Monitor `/api/v1/background-jobs/health` endpoint
3. **Alerting**: Configure alerts for job failures and health degradation
4. **Resource Monitoring**: Monitor CPU, memory, and database connections

### Performance Tuning
- Adjust `max_concurrent_jobs` based on system resources
- Tune batch sizes for TTL cleanup and refresh operations
- Configure appropriate rate limiting delays
- Set reasonable job timeouts

## Troubleshooting

### Common Issues

#### Jobs Not Starting
- Check if `enabled=True` in configuration
- Verify database connectivity
- Check logs for initialization errors

#### High Memory Usage
- Reduce batch sizes in job parameters
- Decrease `max_concurrent_jobs`
- Check for memory leaks in custom job implementations

#### Database Connection Issues
- Verify database configuration
- Check connection pool settings
- Monitor database resource usage

#### Job Execution Failures
- Check job-specific logs
- Verify external service connectivity (Weaviate, LLM providers)
- Review retry configuration

### Debug Logging
Enable debug logging for detailed troubleshooting:
```python
import logging
logging.getLogger('src.background_jobs').setLevel(logging.DEBUG)
```

## Contributing

### Adding New Job Types
1. Create job implementation in `jobs.py`
2. Add job type to `JobType` enum
3. Register handler in `Context7BackgroundJobManager`
4. Add tests for new job type

### Extending Configuration
1. Add new fields to relevant models in `models.py`
2. Update configuration validation
3. Add environment variable support in `service.py`
4. Update documentation

## License

This background job framework is part of the DocAIche project and follows the same licensing terms.