"""
Job Monitoring for Context7 Background Jobs
============================================

Provides comprehensive monitoring, alerting, and health checking
for background job execution and system health.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable

from .models import (
    JobConfig, JobExecution, JobStatus, JobMetrics, 
    BackgroundJobManagerConfig
)

logger = logging.getLogger(__name__)


class JobMonitor:
    """
    Background job monitoring and alerting system
    
    Features:
    - Real-time job health monitoring
    - Performance metrics collection
    - Alert generation for failures
    - Resource usage tracking
    - System health dashboards
    """
    
    def __init__(self, config: BackgroundJobManagerConfig):
        self.config = config
        self.health_checks: Dict[str, Callable] = {}
        self.alert_handlers: List[Callable] = []
        self.metrics_handlers: List[Callable] = []
        
        # Monitoring state
        self.system_health = "unknown"
        self.last_health_check = datetime.utcnow()
        self.health_check_results: Dict[str, Any] = {}
        
        # Performance tracking
        self.performance_metrics: Dict[str, Any] = {
            "total_jobs_executed": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "average_execution_time": 0.0,
            "system_load": 0.0,
            "memory_usage": 0.0,
            "cpu_usage": 0.0
        }
        
        # Alert thresholds
        self.alert_thresholds = {
            "consecutive_failures": 3,
            "error_rate_percent": 25.0,
            "execution_time_multiplier": 3.0,
            "memory_usage_percent": 80.0,
            "cpu_usage_percent": 80.0
        }
        
        logger.info("Job monitor initialized")
    
    def register_health_check(self, name: str, check_func: Callable) -> None:
        """Register a health check function"""
        self.health_checks[name] = check_func
        logger.debug(f"Registered health check: {name}")
    
    def register_alert_handler(self, handler: Callable) -> None:
        """Register an alert handler"""
        self.alert_handlers.append(handler)
        logger.debug("Registered alert handler")
    
    def register_metrics_handler(self, handler: Callable) -> None:
        """Register a metrics handler"""
        self.metrics_handlers.append(handler)
        logger.debug("Registered metrics handler")
    
    async def monitor_job_execution(
        self, 
        job_config: JobConfig, 
        execution: JobExecution
    ) -> None:
        """Monitor job execution progress"""
        try:
            # Track execution start
            logger.info(f"PIPELINE_METRICS: step=job_execution_start "
                       f"job_id={job_config.job_id} execution_id={execution.execution_id} "
                       f"job_type={job_config.job_type.value} priority={job_config.priority.value}")
            
            # Update performance metrics
            self.performance_metrics["total_jobs_executed"] += 1
            
            # Check for alerts during execution
            await self._check_execution_alerts(job_config, execution)
            
        except Exception as e:
            logger.error(f"Error monitoring job execution: {e}")
    
    async def monitor_job_completion(
        self, 
        job_config: JobConfig, 
        execution: JobExecution,
        success: bool
    ) -> None:
        """Monitor job completion and generate alerts"""
        try:
            # Update completion metrics
            if success:
                self.performance_metrics["successful_jobs"] += 1
            else:
                self.performance_metrics["failed_jobs"] += 1
            
            # Update average execution time
            if execution.duration_seconds:
                current_avg = self.performance_metrics["average_execution_time"]
                total_jobs = self.performance_metrics["total_jobs_executed"]
                
                if total_jobs > 1:
                    new_avg = ((current_avg * (total_jobs - 1)) + execution.duration_seconds) / total_jobs
                else:
                    new_avg = execution.duration_seconds
                
                self.performance_metrics["average_execution_time"] = new_avg
            
            # Log completion metrics
            logger.info(f"PIPELINE_METRICS: step=job_execution_complete "
                       f"job_id={job_config.job_id} execution_id={execution.execution_id} "
                       f"success={success} duration_seconds={execution.duration_seconds or 0} "
                       f"records_processed={execution.records_processed} "
                       f"records_failed={execution.records_failed}")
            
            # Check for post-completion alerts
            await self._check_completion_alerts(job_config, execution, success)
            
        except Exception as e:
            logger.error(f"Error monitoring job completion: {e}")
    
    async def perform_health_checks(self) -> Dict[str, Any]:
        """Perform all registered health checks"""
        results = {}
        overall_health = "healthy"
        
        try:
            # Run all health checks
            for name, check_func in self.health_checks.items():
                try:
                    result = await check_func()
                    results[name] = result
                    
                    # Update overall health
                    if result.get("status") == "unhealthy":
                        overall_health = "unhealthy"
                    elif result.get("status") == "degraded" and overall_health == "healthy":
                        overall_health = "degraded"
                        
                except Exception as e:
                    logger.error(f"Health check '{name}' failed: {e}")
                    results[name] = {
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    overall_health = "unhealthy"
            
            # Update system health
            self.system_health = overall_health
            self.last_health_check = datetime.utcnow()
            self.health_check_results = results
            
            # Log health status
            logger.info(f"PIPELINE_METRICS: step=health_check_complete "
                       f"overall_health={overall_health} checks_run={len(self.health_checks)} "
                       f"timestamp={self.last_health_check.isoformat()}")
            
            return {
                "overall_health": overall_health,
                "timestamp": self.last_health_check.isoformat(),
                "checks": results
            }
            
        except Exception as e:
            logger.error(f"Error performing health checks: {e}")
            self.system_health = "error"
            return {
                "overall_health": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect system and job metrics"""
        try:
            # System metrics
            system_metrics = await self._collect_system_metrics()
            
            # Job metrics
            job_metrics = self.performance_metrics.copy()
            
            # Calculate derived metrics
            total_jobs = job_metrics["total_jobs_executed"]
            if total_jobs > 0:
                job_metrics["success_rate"] = (job_metrics["successful_jobs"] / total_jobs) * 100
                job_metrics["failure_rate"] = (job_metrics["failed_jobs"] / total_jobs) * 100
            else:
                job_metrics["success_rate"] = 0.0
                job_metrics["failure_rate"] = 0.0
            
            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "system": system_metrics,
                "jobs": job_metrics,
                "health_status": self.system_health
            }
            
            # Send to metrics handlers
            for handler in self.metrics_handlers:
                try:
                    await handler(metrics)
                except Exception as e:
                    logger.error(f"Error in metrics handler: {e}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level metrics"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            # Update internal metrics
            self.performance_metrics["cpu_usage"] = cpu_percent
            self.performance_metrics["memory_usage"] = memory_percent
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_used_mb": memory.used / (1024 * 1024),
                "memory_total_mb": memory.total / (1024 * 1024),
                "disk_percent": disk_percent,
                "disk_used_gb": disk.used / (1024 * 1024 * 1024),
                "disk_total_gb": disk.total / (1024 * 1024 * 1024),
                "load_average": psutil.getloadavg()[0] if hasattr(psutil, 'getloadavg') else 0.0
            }
            
        except ImportError:
            logger.warning("psutil not available, using placeholder metrics")
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "memory_used_mb": 0.0,
                "memory_total_mb": 0.0,
                "disk_percent": 0.0,
                "disk_used_gb": 0.0,
                "disk_total_gb": 0.0,
                "load_average": 0.0
            }
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return {
                "error": str(e)
            }
    
    async def _check_execution_alerts(
        self, 
        job_config: JobConfig, 
        execution: JobExecution
    ) -> None:
        """Check for alerts during job execution"""
        try:
            alerts = []
            
            # Check execution timeout
            if execution.started_at:
                elapsed = (datetime.utcnow() - execution.started_at).total_seconds()
                if elapsed > job_config.timeout_seconds * 0.9:  # 90% of timeout
                    alerts.append({
                        "type": "execution_timeout_warning",
                        "job_id": job_config.job_id,
                        "execution_id": execution.execution_id,
                        "message": f"Job execution approaching timeout ({elapsed:.1f}s / {job_config.timeout_seconds}s)",
                        "severity": "warning"
                    })
            
            # Send alerts
            for alert in alerts:
                await self._send_alert(alert)
                
        except Exception as e:
            logger.error(f"Error checking execution alerts: {e}")
    
    async def _check_completion_alerts(
        self, 
        job_config: JobConfig, 
        execution: JobExecution,
        success: bool
    ) -> None:
        """Check for alerts after job completion"""
        try:
            alerts = []
            
            # Check for failure alerts
            if not success and job_config.alert_on_failure:
                alerts.append({
                    "type": "job_failure",
                    "job_id": job_config.job_id,
                    "execution_id": execution.execution_id,
                    "message": f"Job failed: {execution.error_message or 'Unknown error'}",
                    "severity": "error",
                    "details": {
                        "retry_count": execution.retry_count,
                        "duration_seconds": execution.duration_seconds,
                        "error_details": execution.error_details
                    }
                })
            
            # Check for success alerts
            if success and job_config.alert_on_success:
                alerts.append({
                    "type": "job_success",
                    "job_id": job_config.job_id,
                    "execution_id": execution.execution_id,
                    "message": f"Job completed successfully",
                    "severity": "info",
                    "details": {
                        "duration_seconds": execution.duration_seconds,
                        "records_processed": execution.records_processed
                    }
                })
            
            # Check for performance alerts
            if execution.duration_seconds:
                avg_duration = self.performance_metrics["average_execution_time"]
                if avg_duration > 0 and execution.duration_seconds > avg_duration * self.alert_thresholds["execution_time_multiplier"]:
                    alerts.append({
                        "type": "performance_degradation",
                        "job_id": job_config.job_id,
                        "execution_id": execution.execution_id,
                        "message": f"Job execution time significantly above average ({execution.duration_seconds:.1f}s vs {avg_duration:.1f}s avg)",
                        "severity": "warning"
                    })
            
            # Send alerts
            for alert in alerts:
                await self._send_alert(alert)
                
        except Exception as e:
            logger.error(f"Error checking completion alerts: {e}")
    
    async def check_job_health(self, job_metrics: JobMetrics) -> Dict[str, Any]:
        """Check health of a specific job"""
        try:
            health_status = "healthy"
            issues = []
            
            # Check consecutive failures
            if job_metrics.consecutive_failures >= self.alert_thresholds["consecutive_failures"]:
                health_status = "unhealthy"
                issues.append(f"Consecutive failures: {job_metrics.consecutive_failures}")
            
            # Check error rate
            if job_metrics.error_rate >= self.alert_thresholds["error_rate_percent"]:
                if health_status == "healthy":
                    health_status = "degraded"
                issues.append(f"High error rate: {job_metrics.error_rate:.1f}%")
            
            # Check execution time trends
            if job_metrics.max_duration_seconds > 0 and job_metrics.average_duration_seconds > 0:
                if job_metrics.max_duration_seconds > job_metrics.average_duration_seconds * self.alert_thresholds["execution_time_multiplier"]:
                    if health_status == "healthy":
                        health_status = "degraded"
                    issues.append(f"Execution time variance: max {job_metrics.max_duration_seconds:.1f}s vs avg {job_metrics.average_duration_seconds:.1f}s")
            
            # Check staleness
            if job_metrics.last_execution_at:
                time_since_last = datetime.utcnow() - job_metrics.last_execution_at
                if time_since_last > timedelta(days=2):  # No execution in 2 days
                    if health_status == "healthy":
                        health_status = "degraded"
                    issues.append(f"No recent executions: {time_since_last.days} days ago")
            
            return {
                "health_status": health_status,
                "issues": issues,
                "metrics": {
                    "total_executions": job_metrics.total_executions,
                    "success_rate": ((job_metrics.successful_executions / job_metrics.total_executions) * 100) if job_metrics.total_executions > 0 else 0,
                    "error_rate": job_metrics.error_rate,
                    "consecutive_failures": job_metrics.consecutive_failures,
                    "average_duration": job_metrics.average_duration_seconds,
                    "last_execution": job_metrics.last_execution_at.isoformat() if job_metrics.last_execution_at else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error checking job health: {e}")
            return {
                "health_status": "error",
                "error": str(e)
            }
    
    async def _send_alert(self, alert: Dict[str, Any]) -> None:
        """Send alert to all registered handlers"""
        try:
            # Add timestamp
            alert["timestamp"] = datetime.utcnow().isoformat()
            
            # Log alert
            logger.warning(f"ALERT: {alert['type']} - {alert['message']}")
            
            # Send to alert handlers
            for handler in self.alert_handlers:
                try:
                    await handler(alert)
                except Exception as e:
                    logger.error(f"Error in alert handler: {e}")
                    
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status"""
        return {
            "status": self.system_health,
            "last_check": self.last_health_check.isoformat(),
            "check_results": self.health_check_results,
            "performance_metrics": self.performance_metrics
        }
    
    def get_alert_thresholds(self) -> Dict[str, Any]:
        """Get current alert thresholds"""
        return self.alert_thresholds.copy()
    
    def update_alert_thresholds(self, thresholds: Dict[str, Any]) -> None:
        """Update alert thresholds"""
        self.alert_thresholds.update(thresholds)
        logger.info(f"Updated alert thresholds: {thresholds}")
    
    def reset_metrics(self) -> None:
        """Reset performance metrics"""
        self.performance_metrics = {
            "total_jobs_executed": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "average_execution_time": 0.0,
            "system_load": 0.0,
            "memory_usage": 0.0,
            "cpu_usage": 0.0
        }
        logger.info("Performance metrics reset")


# Default health check functions
async def default_database_health_check() -> Dict[str, Any]:
    """Default database health check"""
    try:
        # This would typically check database connectivity
        return {
            "status": "healthy",
            "component": "database",
            "response_time_ms": 10,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "component": "database",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def default_weaviate_health_check() -> Dict[str, Any]:
    """Default Weaviate health check"""
    try:
        # This would typically check Weaviate connectivity
        return {
            "status": "healthy",
            "component": "weaviate",
            "response_time_ms": 15,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "component": "weaviate",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


async def default_llm_health_check() -> Dict[str, Any]:
    """Default LLM health check"""
    try:
        # This would typically check LLM provider connectivity
        return {
            "status": "healthy",
            "component": "llm",
            "response_time_ms": 200,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "component": "llm",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }