"""
Background Jobs API Endpoints
=============================

FastAPI endpoints for managing and monitoring Context7 background jobs.
Provides REST API access to job scheduling, execution, and monitoring.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Path, Body
from pydantic import BaseModel, Field

from src.background_jobs.service import BackgroundJobService
from src.background_jobs.models import (
    JobConfig, JobSchedule, RetryConfig, JobStatus, JobType, JobPriority
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/background-jobs", tags=["background-jobs"])

# Global service instance (would be injected in real application)
_background_job_service: Optional[BackgroundJobService] = None


def get_background_job_service() -> BackgroundJobService:
    """Dependency to get background job service"""
    if _background_job_service is None:
        raise HTTPException(
            status_code=503,
            detail="Background job service is not available"
        )
    return _background_job_service


def set_background_job_service(service: BackgroundJobService) -> None:
    """Set the global background job service instance"""
    global _background_job_service
    _background_job_service = service


# Request/Response models
class JobConfigRequest(BaseModel):
    """Request model for creating/updating job configurations"""
    job_id: str = Field(..., description="Unique job identifier")
    job_name: str = Field(..., description="Human-readable job name")
    job_type: JobType = Field(..., description="Type of job")
    description: Optional[str] = Field(None, description="Job description")
    enabled: bool = Field(True, description="Whether job is enabled")
    priority: JobPriority = Field(JobPriority.MEDIUM, description="Job priority")
    schedule: JobSchedule = Field(..., description="Job schedule configuration")
    retry_config: Optional[RetryConfig] = Field(None, description="Retry configuration")
    timeout_seconds: int = Field(3600, description="Job timeout in seconds")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Job parameters")
    max_concurrent_executions: int = Field(1, description="Max concurrent executions")
    alert_on_failure: bool = Field(True, description="Alert on job failure")
    alert_on_success: bool = Field(False, description="Alert on job success")


class JobConfigResponse(BaseModel):
    """Response model for job configurations"""
    job_id: str
    job_name: str
    job_type: str
    description: Optional[str]
    enabled: bool
    priority: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class JobExecutionResponse(BaseModel):
    """Response model for job executions"""
    execution_id: str
    job_id: str
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    correlation_id: Optional[str]
    records_processed: int
    records_failed: int
    error_message: Optional[str]


class JobMetricsResponse(BaseModel):
    """Response model for job metrics"""
    total_executions: int
    successful_executions: int
    failed_executions: int
    error_rate: float
    average_duration_seconds: float
    health_status: str
    consecutive_failures: int
    last_execution_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]


class HealthStatusResponse(BaseModel):
    """Response model for health status"""
    status: str
    total_jobs: int
    running_jobs: int
    queue_size: int
    metrics: Dict[str, Any]


class ServiceInfoResponse(BaseModel):
    """Response model for service information"""
    service_name: str
    version: str
    running: bool
    enabled: bool
    configuration: Dict[str, Any]
    context7_config: Dict[str, Any]


# Endpoints
@router.get("/health", response_model=HealthStatusResponse)
async def get_health_status(
    service: BackgroundJobService = Depends(get_background_job_service)
):
    """Get overall health status of background job system"""
    try:
        health = await service.get_health_status()
        return HealthStatusResponse(**health)
    except Exception as e:
        logger.error(f"Failed to get health status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/service/info", response_model=ServiceInfoResponse)
async def get_service_info(
    service: BackgroundJobService = Depends(get_background_job_service)
):
    """Get background job service information"""
    try:
        info = await service.get_service_info()
        return ServiceInfoResponse(**info)
    except Exception as e:
        logger.error(f"Failed to get service info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=List[JobConfigResponse])
async def list_jobs(
    enabled_only: bool = Query(False, description="Only return enabled jobs"),
    job_type: Optional[JobType] = Query(None, description="Filter by job type"),
    service: BackgroundJobService = Depends(get_background_job_service)
):
    """List all registered background jobs"""
    try:
        jobs = await service.list_jobs()
        
        # Apply filters
        if enabled_only:
            jobs = [job for job in jobs if job.get("enabled", False)]
        
        if job_type:
            jobs = [job for job in jobs if job.get("job_type") == job_type.value]
        
        return [JobConfigResponse(**job) for job in jobs]
    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=JobConfigResponse)
async def get_job(
    job_id: str = Path(..., description="Job ID"),
    service: BackgroundJobService = Depends(get_background_job_service)
):
    """Get specific job configuration"""
    try:
        job = await service.get_job_status(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return JobConfigResponse(**job)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/metrics", response_model=JobMetricsResponse)
async def get_job_metrics(
    job_id: str = Path(..., description="Job ID"),
    service: BackgroundJobService = Depends(get_background_job_service)
):
    """Get job execution metrics"""
    try:
        metrics = await service.get_job_metrics(job_id)
        if not metrics:
            raise HTTPException(status_code=404, detail=f"Metrics for job {job_id} not found")
        
        return JobMetricsResponse(**metrics)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job metrics for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/execute")
async def execute_job(
    job_id: str = Path(..., description="Job ID"),
    correlation_id: Optional[str] = Body(None, description="Optional correlation ID"),
    service: BackgroundJobService = Depends(get_background_job_service)
):
    """Execute a job immediately"""
    try:
        execution = await service.execute_job(job_id, correlation_id)
        return {
            "message": f"Job {job_id} queued for execution",
            "execution": execution
        }
    except Exception as e:
        logger.error(f"Failed to execute job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/enable")
async def enable_job(
    job_id: str = Path(..., description="Job ID"),
    service: BackgroundJobService = Depends(get_background_job_service)
):
    """Enable a job"""
    try:
        success = await service.enable_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return {"message": f"Job {job_id} enabled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/disable")
async def disable_job(
    job_id: str = Path(..., description="Job ID"),
    service: BackgroundJobService = Depends(get_background_job_service)
):
    """Disable a job"""
    try:
        success = await service.disable_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return {"message": f"Job {job_id} disabled successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/running")
async def get_running_jobs(
    service: BackgroundJobService = Depends(get_background_job_service)
):
    """Get currently running job executions"""
    try:
        running_jobs = await service.get_running_jobs()
        return {
            "running_jobs": running_jobs,
            "count": len(running_jobs)
        }
    except Exception as e:
        logger.error(f"Failed to get running jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/executions/history/{job_id}")
async def get_job_execution_history(
    job_id: str = Path(..., description="Job ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of executions to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    status: Optional[JobStatus] = Query(None, description="Filter by execution status"),
    service: BackgroundJobService = Depends(get_background_job_service)
):
    """Get execution history for a specific job"""
    try:
        # This would require additional storage methods to implement fully
        # For now, return a placeholder response
        return {
            "job_id": job_id,
            "executions": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "message": "Execution history endpoint requires additional storage implementation"
        }
    except Exception as e:
        logger.error(f"Failed to get execution history for {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_job_statistics(
    service: BackgroundJobService = Depends(get_background_job_service)
):
    """Get overall job execution statistics"""
    try:
        jobs = await service.list_jobs()
        
        # Calculate summary statistics
        total_jobs = len(jobs)
        enabled_jobs = len([job for job in jobs if job.get("enabled", False)])
        disabled_jobs = total_jobs - enabled_jobs
        
        # Get health status
        health = await service.get_health_status()
        
        # Get running jobs
        running_jobs = await service.get_running_jobs()
        
        # Calculate job type distribution
        job_type_counts = {}
        for job in jobs:
            job_type = job.get("job_type", "unknown")
            job_type_counts[job_type] = job_type_counts.get(job_type, 0) + 1
        
        return {
            "summary": {
                "total_jobs": total_jobs,
                "enabled_jobs": enabled_jobs,
                "disabled_jobs": disabled_jobs,
                "running_jobs": len(running_jobs),
                "overall_health": health.get("status", "unknown")
            },
            "job_type_distribution": job_type_counts,
            "health_details": health,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get job statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/service/restart")
async def restart_service(
    service: BackgroundJobService = Depends(get_background_job_service)
):
    """Restart the background job service"""
    try:
        await service.restart()
        return {"message": "Background job service restarted successfully"}
    except Exception as e:
        logger.error(f"Failed to restart service: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check endpoint for monitoring
@router.get("/ping")
async def ping():
    """Simple ping endpoint for health monitoring"""
    return {
        "status": "ok",
        "service": "background-jobs",
        "timestamp": datetime.utcnow().isoformat()
    }


# Export router for inclusion in main app
__all__ = ["router", "set_background_job_service"]