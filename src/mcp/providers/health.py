"""
Provider Health Monitoring System
=================================

Monitors health of search providers with periodic checks,
failure pattern detection, and recovery monitoring.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
import statistics

from .base import SearchProvider
from .models import HealthCheck, HealthStatus
from .registry import ProviderRegistry

logger = logging.getLogger(__name__)


class HealthTrend(str, Enum):
    """Health trend directions."""
    IMPROVING = "improving"
    STABLE = "stable"
    DEGRADING = "degrading"
    VOLATILE = "volatile"


class HealthMetrics:
    """
    Aggregated health metrics for a provider.
    
    Tracks health history and calculates trends.
    """
    
    def __init__(self, window_size: int = 10):
        """
        Initialize health metrics.
        
        Args:
            window_size: Number of checks to keep in history
        """
        self.window_size = window_size
        self.history: List[HealthCheck] = []
        self.failure_patterns: List[Dict[str, Any]] = []
        self.last_notification: Optional[datetime] = None
    
    def add_check(self, check: HealthCheck) -> None:
        """Add a health check to history."""
        self.history.append(check)
        if len(self.history) > self.window_size:
            self.history.pop(0)
    
    def get_trend(self) -> HealthTrend:
        """
        Calculate health trend from recent history.
        
        Returns:
            Current health trend
        """
        if len(self.history) < 3:
            return HealthTrend.STABLE
        
        # Get recent statuses
        recent_statuses = [h.status for h in self.history[-5:]]
        
        # Count status changes
        status_values = {
            HealthStatus.HEALTHY: 3,
            HealthStatus.DEGRADED: 2,
            HealthStatus.UNHEALTHY: 1,
            HealthStatus.UNKNOWN: 0
        }
        
        values = [status_values.get(s, 0) for s in recent_statuses]
        
        # Calculate trend
        if len(set(values)) == 1:
            return HealthTrend.STABLE
        
        # Check for improvement or degradation
        first_half = statistics.mean(values[:len(values)//2])
        second_half = statistics.mean(values[len(values)//2:])
        
        if second_half > first_half + 0.5:
            return HealthTrend.IMPROVING
        elif second_half < first_half - 0.5:
            return HealthTrend.DEGRADING
        elif len(set(values)) > 2:
            return HealthTrend.VOLATILE
        else:
            return HealthTrend.STABLE
    
    def get_availability(self) -> float:
        """
        Calculate availability percentage from history.
        
        Returns:
            Availability percentage (0-100)
        """
        if not self.history:
            return 100.0
        
        healthy_checks = sum(
            1 for h in self.history
            if h.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        )
        
        return (healthy_checks / len(self.history)) * 100
    
    def get_average_latency(self) -> Optional[float]:
        """
        Calculate average response time from history.
        
        Returns:
            Average latency in ms or None
        """
        latencies = [
            h.response_time_ms for h in self.history
            if h.response_time_ms is not None
        ]
        
        if not latencies:
            return None
        
        return statistics.mean(latencies)
    
    def detect_failure_pattern(self) -> Optional[str]:
        """
        Detect common failure patterns.
        
        Returns:
            Description of detected pattern or None
        """
        if len(self.history) < 5:
            return None
        
        # Check for consistent failures
        recent_failures = sum(
            1 for h in self.history[-5:]
            if h.status == HealthStatus.UNHEALTHY
        )
        
        if recent_failures >= 4:
            return "Consistent failures - provider may be down"
        
        # Check for intermittent issues
        statuses = [h.status for h in self.history[-10:]]
        unhealthy_count = statuses.count(HealthStatus.UNHEALTHY)
        
        if unhealthy_count >= 3 and unhealthy_count <= 6:
            return "Intermittent failures - possible network or load issues"
        
        # Check for degradation pattern
        if self.get_trend() == HealthTrend.DEGRADING:
            return "Progressive degradation - provider health declining"
        
        return None


class ProviderHealthMonitor:
    """
    Monitors health of multiple search providers.
    
    Performs periodic health checks, tracks metrics,
    detects failure patterns, and triggers alerts.
    """
    
    def __init__(
        self,
        registry: ProviderRegistry,
        check_interval_seconds: int = 60,
        alert_callback: Optional[Callable] = None
    ):
        """
        Initialize health monitor.
        
        Args:
            registry: Provider registry to monitor
            check_interval_seconds: Interval between health checks
            alert_callback: Optional callback for health alerts
        """
        self.registry = registry
        self.check_interval = check_interval_seconds
        self.alert_callback = alert_callback
        
        self._metrics: Dict[str, HealthMetrics] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info(f"ProviderHealthMonitor initialized with {check_interval_seconds}s interval")
    
    async def start_monitoring(self) -> None:
        """Start health monitoring loop."""
        if self._running:
            logger.warning("Health monitoring already running")
            return
        
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started health monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring loop."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped health monitoring")
    
    async def check_all_providers(self) -> Dict[str, HealthCheck]:
        """
        Perform health check on all providers.
        
        Returns:
            Map of provider_id to health check result
        """
        providers = self.registry.list_providers(active_only=True, healthy_only=False)
        
        # Run checks concurrently
        tasks = {}
        for provider_id in providers:
            provider = self.registry.get_provider(provider_id)
            if provider:
                tasks[provider_id] = self._check_provider_health(provider)
        
        if not tasks:
            return {}
        
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        health_checks = {}
        for provider_id, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Health check failed for {provider_id}: {result}")
                health_checks[provider_id] = HealthCheck(
                    status=HealthStatus.UNKNOWN,
                    error_rate_percent=100.0,
                    details={"error": str(result)}
                )
            else:
                health_checks[provider_id] = result
                
                # Update metrics
                if provider_id not in self._metrics:
                    self._metrics[provider_id] = HealthMetrics()
                self._metrics[provider_id].add_check(result)
                
                # Check for alerts
                await self._check_alerts(provider_id, result)
        
        return health_checks
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive health summary.
        
        Returns:
            Summary of all provider health states
        """
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "providers": {},
            "overall_status": HealthStatus.HEALTHY.value,
            "alerts": []
        }
        
        unhealthy_count = 0
        
        for provider_id, metrics in self._metrics.items():
            if not metrics.history:
                continue
            
            latest = metrics.history[-1]
            trend = metrics.get_trend()
            availability = metrics.get_availability()
            avg_latency = metrics.get_average_latency()
            pattern = metrics.detect_failure_pattern()
            
            provider_summary = {
                "status": latest.status.value,
                "trend": trend.value,
                "availability_percent": availability,
                "average_latency_ms": avg_latency,
                "last_check": latest.checked_at.isoformat(),
                "circuit_breaker": latest.circuit_breaker_state,
                "error_rate": latest.error_rate_percent
            }
            
            if pattern:
                provider_summary["failure_pattern"] = pattern
                summary["alerts"].append({
                    "provider": provider_id,
                    "type": "failure_pattern",
                    "message": pattern
                })
            
            summary["providers"][provider_id] = provider_summary
            
            if latest.status == HealthStatus.UNHEALTHY:
                unhealthy_count += 1
        
        # Set overall status
        total_providers = len(summary["providers"])
        if unhealthy_count == 0:
            summary["overall_status"] = HealthStatus.HEALTHY.value
        elif unhealthy_count < total_providers / 2:
            summary["overall_status"] = HealthStatus.DEGRADED.value
        else:
            summary["overall_status"] = HealthStatus.UNHEALTHY.value
        
        return summary
    
    def get_provider_metrics(self, provider_id: str) -> Optional[HealthMetrics]:
        """
        Get health metrics for specific provider.
        
        Args:
            provider_id: Provider to get metrics for
            
        Returns:
            Health metrics or None
        """
        return self._metrics.get(provider_id)
    
    async def trigger_recovery_check(self, provider_id: str) -> HealthCheck:
        """
        Trigger immediate health check for provider.
        
        Args:
            provider_id: Provider to check
            
        Returns:
            Health check result
        """
        provider = self.registry.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider {provider_id} not found")
        
        check = await self._check_provider_health(provider)
        
        # Update metrics
        if provider_id not in self._metrics:
            self._metrics[provider_id] = HealthMetrics()
        self._metrics[provider_id].add_check(check)
        
        return check
    
    # Private methods
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self.check_all_providers()
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}", exc_info=True)
            
            # Wait for next check
            await asyncio.sleep(self.check_interval)
    
    async def _check_provider_health(self, provider: SearchProvider) -> HealthCheck:
        """
        Perform health check on single provider.
        
        Args:
            provider: Provider to check
            
        Returns:
            Health check result
        """
        try:
            # First try the provider's health check method
            check = await provider.check_health()
            
            # Merge with runtime metrics
            runtime_health = provider.get_health_status()
            check.error_rate_percent = runtime_health.error_rate_percent
            check.consecutive_failures = runtime_health.consecutive_failures
            check.circuit_breaker_state = runtime_health.circuit_breaker_state
            
            return check
            
        except Exception as e:
            logger.error(f"Health check failed for {provider.__class__.__name__}: {e}")
            return HealthCheck(
                status=HealthStatus.UNHEALTHY,
                error_rate_percent=100.0,
                details={"error": str(e)}
            )
    
    async def _check_alerts(self, provider_id: str, check: HealthCheck) -> None:
        """
        Check if alerts should be triggered.
        
        Args:
            provider_id: Provider identifier
            check: Health check result
        """
        metrics = self._metrics.get(provider_id)
        if not metrics:
            return
        
        # Don't alert too frequently
        if metrics.last_notification:
            elapsed = (datetime.utcnow() - metrics.last_notification).seconds
            if elapsed < 300:  # 5 minutes
                return
        
        alert_triggered = False
        alert_data = {
            "provider_id": provider_id,
            "timestamp": datetime.utcnow().isoformat(),
            "health_check": check.dict()
        }
        
        # Check for critical issues
        if check.status == HealthStatus.UNHEALTHY:
            if check.consecutive_failures >= 3:
                alert_data["type"] = "provider_down"
                alert_data["message"] = f"Provider {provider_id} is down"
                alert_triggered = True
        
        # Check for degradation
        elif metrics.get_trend() == HealthTrend.DEGRADING:
            alert_data["type"] = "health_degrading"
            alert_data["message"] = f"Provider {provider_id} health is degrading"
            alert_triggered = True
        
        # Check for recovery
        elif (len(metrics.history) >= 2 and 
              metrics.history[-2].status == HealthStatus.UNHEALTHY and
              check.status == HealthStatus.HEALTHY):
            alert_data["type"] = "provider_recovered"
            alert_data["message"] = f"Provider {provider_id} has recovered"
            alert_triggered = True
        
        # Trigger alert
        if alert_triggered and self.alert_callback:
            metrics.last_notification = datetime.utcnow()
            try:
                await self.alert_callback(alert_data)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")