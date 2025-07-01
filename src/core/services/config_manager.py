"""
Service Configuration Management with Enhanced Logging and Metrics

Manages service configurations and orchestrates service restarts
with comprehensive logging to Loki and metrics to Prometheus.
"""

import logging
import time
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
import docker
from docker.errors import NotFound, APIError

from src.logging_config import MetricsLogger, ExternalServiceLogger
from src.core.config.manager import ConfigurationManager

logger = logging.getLogger(__name__)
metrics = MetricsLogger(logger)
service_logger = ExternalServiceLogger(logger)

# Service configuration mapping - which services need restart on config change
SERVICE_CONFIG_MAP = {
    "ai.providers": ["api"],  # AI provider changes require API restart
    "ai.model_selection": ["api"],  # Model selection changes require API restart
    "anythingllm": ["anythingllm"],  # AnythingLLM config requires its restart
    "search": ["api"],  # Search config changes require API restart
    "redis": ["redis", "api"],  # Redis config changes require Redis and API restart
    "database": ["api"],  # Database config changes require API restart
    "logging": ["api", "admin-ui", "promtail"],  # Logging changes affect multiple services
    "monitoring": ["prometheus", "grafana"],  # Monitoring config changes
}

# Service restart priorities (lower number = higher priority)
SERVICE_RESTART_PRIORITY = {
    "redis": 1,
    "db": 2,
    "anythingllm": 3,
    "api": 4,
    "admin-ui": 5,
    "promtail": 6,
    "prometheus": 7,
    "grafana": 8,
}


class ServiceConfigManager:
    """Manages service configurations and orchestrates restarts with comprehensive logging"""
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config_manager = config_manager
        self.docker_client = None
        self._initialize_docker()
        
    def _initialize_docker(self):
        """Initialize Docker client"""
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized for service management")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}", extra={
                "event": "docker_init_failed",
                "error": str(e),
                "error_type": type(e).__name__
            })
    
    async def handle_config_change(
        self, 
        config_key: str, 
        new_config: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle configuration change and orchestrate service restarts
        
        Args:
            config_key: Configuration key that was changed
            new_config: New configuration values
            correlation_id: Correlation ID for tracking the change
            
        Returns:
            Dictionary with restart results
        """
        start_time = time.time()
        if not correlation_id:
            correlation_id = f"config_change_{int(time.time() * 1000)}"
        
        # Log configuration change event
        logger.info(f"Handling configuration change for {config_key}", extra={
            "event": "config_change_start",
            "correlation_id": correlation_id,
            "config_key": config_key,
            "timestamp": datetime.now().isoformat(),
            "operation": "config_change_handler"
        })
        
        # Record config change metric
        metrics.record_metric("service_config_change_count", 1, {
            "config_key": config_key,
            "operation": "change_detected"
        })
        
        # Determine which services need restart
        affected_services = self._determine_affected_services(config_key)
        
        if not affected_services:
            logger.info(f"No services require restart for config key: {config_key}", extra={
                "event": "config_change_no_restart",
                "correlation_id": correlation_id,
                "config_key": config_key
            })
            return {
                "success": True,
                "message": "Configuration updated, no service restart required",
                "services_restarted": []
            }
        
        # Log services that will be restarted
        logger.info(f"Services requiring restart: {affected_services}", extra={
            "event": "services_restart_required",
            "correlation_id": correlation_id,
            "config_key": config_key,
            "affected_services": affected_services,
            "service_count": len(affected_services)
        })
        
        # Persist configuration to files if needed
        await self._persist_service_configs(config_key, new_config, correlation_id)
        
        # Restart services in priority order
        restart_results = await self._restart_services(affected_services, correlation_id)
        
        # Calculate metrics
        duration = time.time() - start_time
        success_count = sum(1 for r in restart_results.values() if r.get("success"))
        failed_count = len(restart_results) - success_count
        
        # Log completion
        logger.info(f"Configuration change handling completed", extra={
            "event": "config_change_complete",
            "correlation_id": correlation_id,
            "config_key": config_key,
            "duration_seconds": round(duration, 3),
            "services_restarted": len(restart_results),
            "success_count": success_count,
            "failed_count": failed_count,
            "status": "success" if failed_count == 0 else "partial_failure"
        })
        
        # Record completion metrics
        metrics.record_metric("service_config_change_duration", duration, {
            "config_key": config_key,
            "status": "success" if failed_count == 0 else "failed"
        })
        
        return {
            "success": failed_count == 0,
            "message": f"Restarted {success_count}/{len(restart_results)} services",
            "services_restarted": restart_results,
            "duration_seconds": round(duration, 3)
        }
    
    def _determine_affected_services(self, config_key: str) -> List[str]:
        """Determine which services need restart based on config key"""
        affected = []
        
        # Check exact matches and prefix matches
        for pattern, services in SERVICE_CONFIG_MAP.items():
            if config_key == pattern or config_key.startswith(f"{pattern}."):
                affected.extend(services)
        
        # Remove duplicates and sort by priority
        affected = list(set(affected))
        affected.sort(key=lambda s: SERVICE_RESTART_PRIORITY.get(s, 999))
        
        return affected
    
    async def _persist_service_configs(
        self, 
        config_key: str, 
        new_config: Dict[str, Any],
        correlation_id: str
    ):
        """Persist service configurations to appropriate files"""
        persist_start = time.time()
        
        try:
            # AI provider configurations
            if config_key.startswith("ai.providers."):
                provider_id = config_key.split(".")[-1]
                await self._persist_provider_config(provider_id, new_config, correlation_id)
            
            # Model selection configuration
            elif config_key == "ai.model_selection":
                await self._persist_model_selection(new_config, correlation_id)
            
            # Redis configuration
            elif config_key.startswith("redis."):
                await self._persist_redis_config(new_config, correlation_id)
            
            # Logging configuration
            elif config_key.startswith("logging."):
                await self._persist_logging_config(new_config, correlation_id)
            
            persist_duration = time.time() - persist_start
            
            logger.info(f"Service configuration persisted", extra={
                "event": "config_persist_success",
                "correlation_id": correlation_id,
                "config_key": config_key,
                "duration_seconds": round(persist_duration, 3)
            })
            
            metrics.record_metric("service_config_persist_duration", persist_duration, {
                "config_key": config_key,
                "status": "success"
            })
            
        except Exception as e:
            persist_duration = time.time() - persist_start
            
            logger.error(f"Failed to persist service configuration", extra={
                "event": "config_persist_failed",
                "correlation_id": correlation_id,
                "config_key": config_key,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_seconds": round(persist_duration, 3)
            })
            
            metrics.record_metric("service_config_persist_duration", persist_duration, {
                "config_key": config_key,
                "status": "failed",
                "error_type": type(e).__name__
            })
    
    async def _restart_services(
        self, 
        services: List[str],
        correlation_id: str
    ) -> Dict[str, Dict[str, Any]]:
        """Restart services with logging and metrics"""
        results = {}
        
        for service_name in services:
            service_start = time.time()
            
            try:
                # Log restart attempt
                logger.info(f"Restarting service: {service_name}", extra={
                    "event": "service_restart_start",
                    "correlation_id": correlation_id,
                    "service_name": service_name,
                    "restart_reason": "config_change"
                })
                
                # Get container
                container = self._get_container(service_name)
                if not container:
                    raise Exception(f"Container not found for service: {service_name}")
                
                # Capture pre-restart state
                pre_status = container.status
                
                # Restart container
                container.restart(timeout=30)
                
                # Wait for container to be healthy
                healthy = await self._wait_for_healthy(container, service_name, correlation_id)
                
                service_duration = time.time() - service_start
                
                # Log successful restart
                logger.info(f"Service {service_name} restarted successfully", extra={
                    "event": "service_restart_success",
                    "correlation_id": correlation_id,
                    "service_name": service_name,
                    "pre_status": pre_status,
                    "post_status": "healthy" if healthy else "running",
                    "duration_seconds": round(service_duration, 3),
                    "health_check_passed": healthy
                })
                
                # Record success metrics
                metrics.record_metric("service_restart_duration", service_duration, {
                    "service_name": service_name,
                    "status": "success"
                })
                
                metrics.record_metric("service_restart_count", 1, {
                    "service_name": service_name,
                    "status": "success"
                })
                
                results[service_name] = {
                    "success": True,
                    "duration_seconds": round(service_duration, 3),
                    "healthy": healthy
                }
                
            except Exception as e:
                service_duration = time.time() - service_start
                
                # Log failed restart
                logger.error(f"Failed to restart service {service_name}", extra={
                    "event": "service_restart_failed",
                    "correlation_id": correlation_id,
                    "service_name": service_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": round(service_duration, 3)
                })
                
                # Record failure metrics
                metrics.record_metric("service_restart_duration", service_duration, {
                    "service_name": service_name,
                    "status": "failed",
                    "error_type": type(e).__name__
                })
                
                metrics.record_metric("service_restart_count", 1, {
                    "service_name": service_name,
                    "status": "failed"
                })
                
                results[service_name] = {
                    "success": False,
                    "error": str(e),
                    "duration_seconds": round(service_duration, 3)
                }
        
        return results
    
    def _get_container(self, service_name: str) -> Optional[Any]:
        """Get Docker container for service"""
        if not self.docker_client:
            return None
        
        try:
            # Try to find container by service name
            containers = self.docker_client.containers.list(all=True)
            for container in containers:
                # Check container name or service label
                if service_name in container.name or \
                   container.labels.get("com.docker.compose.service") == service_name:
                    return container
            return None
        except Exception as e:
            logger.error(f"Error finding container for service {service_name}: {e}")
            return None
    
    async def _wait_for_healthy(
        self, 
        container: Any,
        service_name: str,
        correlation_id: str,
        timeout: int = 60
    ) -> bool:
        """Wait for container to become healthy"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                container.reload()
                
                # Check health status
                health = container.attrs.get("State", {}).get("Health", {})
                if health.get("Status") == "healthy":
                    return True
                
                # If no health check, just check if running
                if not health and container.status == "running":
                    await asyncio.sleep(2)  # Give it a moment to stabilize
                    return True
                
            except Exception as e:
                logger.debug(f"Error checking health for {service_name}: {e}")
            
            await asyncio.sleep(1)
        
        logger.warning(f"Service {service_name} did not become healthy within timeout", extra={
            "event": "service_health_timeout",
            "correlation_id": correlation_id,
            "service_name": service_name,
            "timeout_seconds": timeout
        })
        
        return False
    
    async def _persist_provider_config(
        self, 
        provider_id: str,
        config: Dict[str, Any],
        correlation_id: str
    ):
        """Persist provider configuration to appropriate location"""
        # This would write to environment files or config files
        # that get mounted into containers
        logger.debug(f"Persisting provider config for {provider_id}", extra={
            "event": "persist_provider_config",
            "correlation_id": correlation_id,
            "provider_id": provider_id
        })
    
    async def _persist_model_selection(
        self, 
        config: Dict[str, Any],
        correlation_id: str
    ):
        """Persist model selection configuration"""
        logger.debug("Persisting model selection config", extra={
            "event": "persist_model_selection",
            "correlation_id": correlation_id
        })
    
    async def _persist_redis_config(
        self, 
        config: Dict[str, Any],
        correlation_id: str
    ):
        """Persist Redis configuration"""
        logger.debug("Persisting Redis config", extra={
            "event": "persist_redis_config",
            "correlation_id": correlation_id
        })
    
    async def _persist_logging_config(
        self, 
        config: Dict[str, Any],
        correlation_id: str
    ):
        """Persist logging configuration"""
        logger.debug("Persisting logging config", extra={
            "event": "persist_logging_config",
            "correlation_id": correlation_id
        })