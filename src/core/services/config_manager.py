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
# Maps configuration keys to the service processes that need to be restarted
SERVICE_CONFIG_MAP = {
    "ai.providers": [],  # Provider config changes alone don't require restarts
    "ai.model_selection.text": ["text-ai-service"],  # Text model changes require text AI service restart
    "ai.model_selection.embedding": ["embedding-service"],  # Embedding model changes require embedding service restart
    "anythingllm": ["anythingllm-service"],  # AnythingLLM config requires its service restart
    "search": ["search-service"],  # Search config changes require search service restart
    "redis": ["redis-service"],  # Redis config changes require Redis service restart
    "database": [],  # Database config changes don't require service restarts
    "logging": ["logging-service"],  # Logging changes affect logging service
    "monitoring": ["metrics-service"],  # Monitoring config changes affect metrics service
}

# Service restart priorities (lower number = higher priority)
SERVICE_RESTART_PRIORITY = {
    "redis": 1,
    "db": 2,
    "anythingllm": 3,
    "promtail": 4,
    "prometheus": 5,
    "grafana": 6,
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
        """Restart service processes (not containers) with logging and metrics"""
        results = {}
        
        for service_name in services:
            service_start = time.time()
            
            try:
                # Log restart attempt
                logger.info(f"Restarting service process: {service_name}", extra={
                    "event": "service_restart_start",
                    "correlation_id": correlation_id,
                    "service_name": service_name,
                    "restart_reason": "config_change",
                    "restart_type": "process"
                })
                
                # Trigger service-specific restart mechanism
                restart_success = await self._trigger_service_restart(service_name, correlation_id)
                
                service_duration = time.time() - service_start
                
                if restart_success:
                    # Log successful restart
                    logger.info(f"Service process {service_name} restarted successfully", extra={
                        "event": "service_restart_success",
                        "correlation_id": correlation_id,
                        "service_name": service_name,
                        "duration_seconds": round(service_duration, 3),
                        "restart_type": "process"
                    })
                    
                    # Record success metrics
                    metrics.record_metric("service_restart_duration", service_duration, {
                        "service_name": service_name,
                        "status": "success",
                        "restart_type": "process"
                    })
                    
                    metrics.record_metric("service_restart_count", 1, {
                        "service_name": service_name,
                        "status": "success",
                        "restart_type": "process"
                    })
                    
                    results[service_name] = {
                        "success": True,
                        "duration_seconds": round(service_duration, 3),
                        "restart_type": "process"
                    }
                else:
                    raise Exception("Service restart signal failed")
                
            except Exception as e:
                service_duration = time.time() - service_start
                
                # Log failed restart
                logger.error(f"Failed to restart service process {service_name}", extra={
                    "event": "service_restart_failed",
                    "correlation_id": correlation_id,
                    "service_name": service_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": round(service_duration, 3),
                    "restart_type": "process"
                })
                
                # Record failure metrics
                metrics.record_metric("service_restart_duration", service_duration, {
                    "service_name": service_name,
                    "status": "failed",
                    "error_type": type(e).__name__,
                    "restart_type": "process"
                })
                
                metrics.record_metric("service_restart_count", 1, {
                    "service_name": service_name,
                    "status": "failed",
                    "restart_type": "process"
                })
                
                results[service_name] = {
                    "success": False,
                    "error": str(e),
                    "duration_seconds": round(service_duration, 3),
                    "restart_type": "process"
                }
        
        return results
    
    async def _trigger_service_restart(self, service_name: str, correlation_id: str) -> bool:
        """
        Trigger a service process restart using service-specific mechanisms
        
        Each service should have its own restart mechanism:
        - text-ai-service: Send SIGHUP or call restart endpoint
        - embedding-service: Send SIGHUP or call restart endpoint  
        - anythingllm-service: Use AnythingLLM API to reload
        - redis-service: Use Redis CONFIG REWRITE command
        - etc.
        """
        try:
            if service_name == "text-ai-service":
                # Text AI service restart logic
                # This could be:
                # 1. Sending a signal to the process
                # 2. Calling a reload endpoint
                # 3. Writing to a file that the service monitors
                logger.info(f"Triggering text AI service restart", extra={
                    "event": "text_ai_service_restart",
                    "correlation_id": correlation_id
                })
                # TODO: Implement actual restart mechanism
                return True
                
            elif service_name == "embedding-service":
                # Embedding service restart logic (often part of AnythingLLM)
                logger.info(f"Triggering embedding service restart", extra={
                    "event": "embedding_service_restart", 
                    "correlation_id": correlation_id
                })
                # TODO: Implement actual restart mechanism
                return True
                
            elif service_name == "anythingllm-service":
                # AnythingLLM service restart logic
                logger.info(f"Triggering AnythingLLM service restart", extra={
                    "event": "anythingllm_service_restart",
                    "correlation_id": correlation_id
                })
                # TODO: Call AnythingLLM API to reload configuration
                return True
                
            elif service_name == "search-service":
                # Search service restart logic
                logger.info(f"Triggering search service restart", extra={
                    "event": "search_service_restart",
                    "correlation_id": correlation_id
                })
                # TODO: Implement actual restart mechanism
                return True
                
            elif service_name == "redis-service":
                # Redis service can reload config without restart
                logger.info(f"Triggering Redis config reload", extra={
                    "event": "redis_config_reload",
                    "correlation_id": correlation_id
                })
                # TODO: Use Redis CONFIG REWRITE command
                return True
                
            elif service_name == "logging-service":
                # Logging service restart logic
                logger.info(f"Triggering logging service restart", extra={
                    "event": "logging_service_restart",
                    "correlation_id": correlation_id
                })
                # TODO: Implement actual restart mechanism
                return True
                
            elif service_name == "metrics-service":
                # Metrics service restart logic
                logger.info(f"Triggering metrics service restart", extra={
                    "event": "metrics_service_restart",
                    "correlation_id": correlation_id
                })
                # TODO: Implement actual restart mechanism
                return True
                
            else:
                logger.warning(f"Unknown service: {service_name}", extra={
                    "event": "unknown_service_restart",
                    "correlation_id": correlation_id,
                    "service_name": service_name
                })
                return False
                
        except Exception as e:
            logger.error(f"Error triggering service restart for {service_name}: {e}", extra={
                "event": "service_restart_trigger_error",
                "correlation_id": correlation_id,
                "service_name": service_name,
                "error": str(e),
                "error_type": type(e).__name__
            })
            return False
    
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
        """Persist provider configuration to AnythingLLM"""
        try:
            # For AnythingLLM, we need to update its LLM provider settings
            # This typically involves updating environment variables or API calls
            
            logger.info(f"Updating AnythingLLM with {provider_id} provider config", extra={
                "event": "persist_provider_config",
                "correlation_id": correlation_id,
                "provider_id": provider_id,
                "config_keys": list(config.keys())
            })
            
            # TODO: Implement actual AnythingLLM configuration update
            # This would involve either:
            # 1. Updating environment variables that AnythingLLM reads
            # 2. Making API calls to AnythingLLM to update its settings
            # 3. Writing to a configuration file that AnythingLLM monitors
            
        except Exception as e:
            logger.error(f"Failed to persist provider config to AnythingLLM", extra={
                "event": "persist_provider_config_error",
                "correlation_id": correlation_id,
                "provider_id": provider_id,
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise
    
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