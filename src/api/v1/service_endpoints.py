"""
Service Management API Endpoints
Provides service restart and configuration management capabilities
with comprehensive logging and metrics
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from .middleware import limiter, get_trace_id
from .dependencies import get_configuration_manager
from src.core.config.manager import ConfigurationManager
from src.core.services.config_manager import ServiceConfigManager
from src.logging_config import MetricsLogger, SecurityLogger

logger = logging.getLogger(__name__)
metrics = MetricsLogger(logger)

# Import enhanced logging for security monitoring
try:
    _security_logger = SecurityLogger(logger)
except ImportError:
    _security_logger = None
    logger.warning("Enhanced security logging not available")

router = APIRouter()


@router.post("/services/{service_name}/restart", tags=["services"])
# @limiter.limit("5/minute")  # Limit service restarts
async def restart_service(
    request: Request,
    service_name: str,
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> Dict[str, Any]:
    """
    POST /api/v1/services/{service_name}/restart - Manually restart a specific service
    
    This endpoint allows manual service restart with comprehensive logging
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    trace_id = get_trace_id(request)
    correlation_id = f"manual_restart_{service_name}_{int(time.time() * 1000)}"
    
    # Log security-sensitive operation
    if _security_logger:
        _security_logger.log_admin_action(
            action="manual_service_restart",
            target=f"service_{service_name}",
            impact_level="high",
            client_ip=client_ip,
            trace_id=trace_id,
            additional_data={
                "service_name": service_name,
                "correlation_id": correlation_id
            }
        )
    
    logger.info(f"Manual service restart requested for {service_name}", extra={
        "event": "manual_restart_request",
        "correlation_id": correlation_id,
        "trace_id": trace_id,
        "service_name": service_name,
        "client_ip": client_ip,
        "operation": "manual_service_restart"
    })
    
    try:
        # Initialize service config manager
        service_manager = ServiceConfigManager(config_manager)
        
        # Restart the specific service
        results = await service_manager._restart_services([service_name], correlation_id)
        
        if service_name not in results:
            raise HTTPException(
                status_code=404,
                detail=f"Service '{service_name}' not found"
            )
        
        service_result = results[service_name]
        duration = time.time() - start_time
        
        # Log completion
        logger.info(f"Manual service restart completed for {service_name}", extra={
            "event": "manual_restart_complete",
            "correlation_id": correlation_id,
            "trace_id": trace_id,
            "service_name": service_name,
            "success": service_result.get("success", False),
            "duration_seconds": round(duration, 3),
            "healthy": service_result.get("healthy", False)
        })
        
        # Record metrics
        metrics.record_metric("manual_service_restart_duration", duration, {
            "service_name": service_name,
            "status": "success" if service_result.get("success") else "failed"
        })
        
        return {
            "service": service_name,
            "restart_status": service_result,
            "correlation_id": correlation_id,
            "duration_seconds": round(duration, 3)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        duration = time.time() - start_time
        
        logger.error(f"Failed to restart service {service_name}", extra={
            "event": "manual_restart_failed",
            "correlation_id": correlation_id,
            "trace_id": trace_id,
            "service_name": service_name,
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_seconds": round(duration, 3)
        })
        
        # Record failure metrics
        metrics.record_metric("manual_service_restart_duration", duration, {
            "service_name": service_name,
            "status": "failed",
            "error_type": type(e).__name__
        })
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart service: {str(e)}"
        )


@router.get("/services/restart-history", tags=["services"])
# @limiter.limit("30/minute")
async def get_restart_history(
    request: Request,
    limit: int = 100,
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> Dict[str, Any]:
    """
    GET /api/v1/services/restart-history - Get service restart history
    
    Returns recent service restart events with details
    """
    client_ip = request.client.host if request.client else "unknown"
    trace_id = get_trace_id(request)
    
    logger.info("Service restart history requested", extra={
        "event": "restart_history_request",
        "trace_id": trace_id,
        "client_ip": client_ip,
        "limit": limit
    })
    
    # This would typically query a database or log storage
    # For now, return a placeholder response
    return {
        "history": [],
        "message": "Service restart history would be retrieved from logs/database",
        "limit": limit
    }


@router.post("/services/health-check", tags=["services"])
# @limiter.limit("10/minute")
async def trigger_health_check(
    request: Request,
    service_names: Optional[list[str]] = None,
    config_manager: ConfigurationManager = Depends(get_configuration_manager),
) -> Dict[str, Any]:
    """
    POST /api/v1/services/health-check - Trigger health checks for services
    
    Performs health checks on specified services or all services
    """
    start_time = time.time()
    client_ip = request.client.host if request.client else "unknown"
    trace_id = get_trace_id(request)
    correlation_id = f"health_check_{int(time.time() * 1000)}"
    
    logger.info("Service health check requested", extra={
        "event": "health_check_request",
        "correlation_id": correlation_id,
        "trace_id": trace_id,
        "client_ip": client_ip,
        "service_count": len(service_names) if service_names else "all"
    })
    
    try:
        # Initialize service config manager
        service_manager = ServiceConfigManager(config_manager)
        
        # Get Docker client
        if not service_manager.docker_client:
            raise HTTPException(
                status_code=503,
                detail="Docker service unavailable"
            )
        
        # Get all or specified containers
        containers = service_manager.docker_client.containers.list()
        health_results = {}
        
        for container in containers:
            service_name = container.labels.get("com.docker.compose.service", container.name)
            
            # Skip if specific services requested and this isn't one
            if service_names and service_name not in service_names:
                continue
            
            # Check container health
            health = container.attrs.get("State", {}).get("Health", {})
            
            health_results[service_name] = {
                "status": container.status,
                "health_status": health.get("Status", "no_healthcheck"),
                "last_check": health.get("Log", [{}])[-1].get("End") if health.get("Log") else None,
                "running_for": container.attrs.get("State", {}).get("StartedAt")
            }
        
        duration = time.time() - start_time
        
        logger.info("Service health check completed", extra={
            "event": "health_check_complete",
            "correlation_id": correlation_id,
            "trace_id": trace_id,
            "services_checked": len(health_results),
            "duration_seconds": round(duration, 3)
        })
        
        # Record metrics
        metrics.record_metric("service_health_check_duration", duration, {
            "service_count": len(health_results),
            "status": "success"
        })
        
        return {
            "health_status": health_results,
            "services_checked": len(health_results),
            "correlation_id": correlation_id,
            "duration_seconds": round(duration, 3)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        duration = time.time() - start_time
        
        logger.error(f"Failed to perform health check: {e}", extra={
            "event": "health_check_failed",
            "correlation_id": correlation_id,
            "trace_id": trace_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "duration_seconds": round(duration, 3)
        })
        
        # Record failure metrics
        metrics.record_metric("service_health_check_duration", duration, {
            "status": "failed",
            "error_type": type(e).__name__
        })
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform health check: {str(e)}"
        )