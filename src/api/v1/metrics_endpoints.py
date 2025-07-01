"""
Metrics and Monitoring API Endpoints
Provides access to Prometheus metrics and Grafana dashboards
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx
import json
from fastapi import APIRouter, HTTPException, Query, Depends, Request
from fastapi.responses import StreamingResponse

from .dependencies import get_current_user_optional, require_role, get_search_orchestrator, get_cache_manager
from .middleware import limiter
from src.search.orchestrator import SearchOrchestrator
from src.database.connection import CacheManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Grafana dashboard definitions
DASHBOARDS = {
    "system-overview": {
        "id": "docaiche-overview",
        "title": "DocAIche System Overview",
        "description": "Overall system health and performance metrics",
        "tags": ["system", "overview"],
        "panels": ["cpu", "memory", "network", "logs"]
    },
    "api-performance": {
        "id": "api-metrics",
        "title": "API Performance",
        "description": "API request metrics, latencies, and error rates",
        "tags": ["api", "performance"],
        "panels": ["request_rate", "latency", "error_rate", "top_endpoints"]
    },
    "database-performance": {
        "id": "db-metrics",
        "title": "Database Performance",
        "description": "Database query performance and connection pool metrics",
        "tags": ["database", "performance"],
        "panels": ["query_duration", "connections", "slow_queries", "cache_hit_rate"]
    },
    "cache-performance": {
        "id": "cache-metrics",
        "title": "Cache Performance",
        "description": "Redis cache hit rates and memory usage",
        "tags": ["cache", "redis"],
        "panels": ["hit_rate", "memory_usage", "evictions", "operations"]
    },
    "container-resources": {
        "id": "container-metrics",
        "title": "Container Resources",
        "description": "Container CPU, memory, and network usage",
        "tags": ["containers", "resources"],
        "panels": ["cpu_by_container", "memory_by_container", "network_io", "disk_io"]
    }
}


@router.get("/dashboards")
async def list_dashboards(
    request: Request,
    tags: Optional[List[str]] = Query(None),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    List available Grafana dashboards
    
    Args:
        tags: Filter dashboards by tags
        
    Returns:
        List of available dashboards with metadata
    """
    if current_user:
        require_role(current_user, ["admin", "developer", "viewer"])
    
    dashboards = []
    
    for dashboard_id, dashboard_info in DASHBOARDS.items():
        # Filter by tags if specified
        if tags:
            if not any(tag in dashboard_info["tags"] for tag in tags):
                continue
        
        dashboards.append({
            "id": dashboard_info["id"],
            "title": dashboard_info["title"],
            "description": dashboard_info["description"],
            "url": f"/grafana/d/{dashboard_info['id']}/{dashboard_info['title'].lower().replace(' ', '-')}",
            "tags": dashboard_info["tags"]
        })
    
    return {"dashboards": dashboards}


@router.get("/query")
async def query_metrics(
    request: Request,
    query: str = Query(..., description="PromQL query"),
    start: Optional[datetime] = Query(default_factory=lambda: datetime.utcnow() - timedelta(hours=1)),
    end: Optional[datetime] = Query(default_factory=datetime.utcnow),
    step: Optional[str] = Query("15s", pattern="^[0-9]+[smhd]$"),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Execute Prometheus query
    
    Args:
        query: PromQL query string
        start: Start time for range query
        end: End time for range query
        step: Query resolution step
        
    Returns:
        Prometheus query results
    """
    if current_user:
        require_role(current_user, ["admin", "developer"])
    
    try:
        # Query Prometheus
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "http://prometheus:9090/api/v1/query_range",
                params={
                    "query": query,
                    "start": int(start.timestamp()),
                    "end": int(end.timestamp()),
                    "step": step
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Prometheus query failed: {response.status_code} - {response.text}")
                raise HTTPException(status_code=502, detail="Failed to query metrics")
            
            data = response.json()
            
            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                raise HTTPException(status_code=400, detail=f"Query error: {error_msg}")
            
            return data["data"]
    
    except httpx.TimeoutException:
        logger.error("Prometheus query timeout")
        raise HTTPException(status_code=504, detail="Metrics query timeout")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query Prometheus: {e}")
        raise HTTPException(status_code=502, detail="Failed to query metrics")


@router.get("/instant")
async def instant_query(
    request: Request,
    query: str = Query(..., description="PromQL query"),
    time: Optional[datetime] = Query(default_factory=datetime.utcnow),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Execute instant Prometheus query
    
    Args:
        query: PromQL query string
        time: Evaluation timestamp
        
    Returns:
        Instant query results
    """
    if current_user:
        require_role(current_user, ["admin", "developer", "viewer"])
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "http://prometheus:9090/api/v1/query",
                params={
                    "query": query,
                    "time": int(time.timestamp())
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Prometheus query failed: {response.status_code} - {response.text}")
                raise HTTPException(status_code=502, detail="Failed to query metrics")
            
            data = response.json()
            
            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                raise HTTPException(status_code=400, detail=f"Query error: {error_msg}")
            
            return data["data"]
    
    except httpx.TimeoutException:
        logger.error("Prometheus query timeout")
        raise HTTPException(status_code=504, detail="Metrics query timeout")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to query Prometheus: {e}")
        raise HTTPException(status_code=502, detail="Failed to query metrics")


@router.get("/alerts")
async def get_alerts(
    request: Request,
    active_only: bool = True,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Get active alerts from monitoring system
    
    Args:
        active_only: Only return active alerts
        
    Returns:
        List of alerts with details
    """
    if current_user:
        require_role(current_user, ["admin", "developer", "viewer"])
    
    # For now, return mock alerts
    # In production, this would query Prometheus Alertmanager
    alerts = []
    
    # Check some basic metrics for alerts
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check CPU usage
            cpu_response = await client.get(
                "http://prometheus:9090/api/v1/query",
                params={
                    "query": 'avg(rate(container_cpu_usage_seconds_total[5m])) by (container_label_com_docker_compose_service) * 100'
                }
            )
            
            if cpu_response.status_code == 200:
                cpu_data = cpu_response.json()
                if cpu_data.get("status") == "success":
                    for result in cpu_data["data"]["result"]:
                        service = result["metric"].get("container_label_com_docker_compose_service", "unknown")
                        cpu_percent = float(result["value"][1])
                        
                        if cpu_percent > 80:
                            alerts.append({
                                "id": f"high-cpu-{service}",
                                "name": "High CPU Usage",
                                "severity": "warning" if cpu_percent < 90 else "critical",
                                "service": service,
                                "description": f"CPU usage is {cpu_percent:.1f}% for service {service}",
                                "started_at": datetime.utcnow().isoformat() + "Z",
                                "value": cpu_percent,
                                "threshold": 80,
                                "status": "active"
                            })
            
            # Check memory usage
            memory_response = await client.get(
                "http://prometheus:9090/api/v1/query",
                params={
                    "query": 'avg(container_memory_usage_bytes / container_spec_memory_limit_bytes) by (container_label_com_docker_compose_service) * 100'
                }
            )
            
            if memory_response.status_code == 200:
                memory_data = memory_response.json()
                if memory_data.get("status") == "success":
                    for result in memory_data["data"]["result"]:
                        service = result["metric"].get("container_label_com_docker_compose_service", "unknown")
                        memory_percent = float(result["value"][1])
                        
                        if memory_percent > 80:
                            alerts.append({
                                "id": f"high-memory-{service}",
                                "name": "High Memory Usage",
                                "severity": "warning" if memory_percent < 90 else "critical",
                                "service": service,
                                "description": f"Memory usage is {memory_percent:.1f}% for service {service}",
                                "started_at": datetime.utcnow().isoformat() + "Z",
                                "value": memory_percent,
                                "threshold": 80,
                                "status": "active"
                            })
    
    except Exception as e:
        logger.warning(f"Failed to check alerts: {e}")
    
    # Add some static alerts for demo
    if not alerts:
        alerts = [
            {
                "id": "demo-alert-1",
                "name": "Demo Alert",
                "severity": "info",
                "service": "monitoring",
                "description": "This is a demo alert. Real alerts will appear when thresholds are exceeded.",
                "started_at": datetime.utcnow().isoformat() + "Z",
                "value": 0,
                "threshold": 0,
                "status": "active"
            }
        ]
    
    if not active_only:
        # Add resolved alerts (mock data)
        alerts.extend([
            {
                "id": "resolved-cpu-spike",
                "name": "CPU Spike Resolved",
                "severity": "info",
                "service": "api",
                "description": "CPU usage spike has been resolved",
                "started_at": (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z",
                "resolved_at": (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z",
                "value": 45,
                "threshold": 80,
                "status": "resolved"
            }
        ])
    
    return {"alerts": alerts}


@router.get("/targets")
async def get_targets(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Get Prometheus scrape targets and their status
    
    Returns:
        List of configured targets with health status
    """
    if current_user:
        require_role(current_user, ["admin", "developer"])
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://prometheus:9090/api/v1/targets")
            
            if response.status_code != 200:
                logger.error(f"Failed to get targets: {response.status_code}")
                raise HTTPException(status_code=502, detail="Failed to get targets")
            
            data = response.json()
            
            if data.get("status") != "success":
                raise HTTPException(status_code=502, detail="Failed to get targets")
            
            # Format targets for easier consumption
            targets = []
            for target in data["data"]["activeTargets"]:
                targets.append({
                    "job": target["labels"].get("job"),
                    "instance": target["labels"].get("instance"),
                    "health": target["health"],
                    "last_scrape": target.get("lastScrape"),
                    "last_error": target.get("lastError", ""),
                    "labels": target["labels"]
                })
            
            return {"targets": targets}
    
    except httpx.TimeoutException:
        logger.error("Prometheus targets query timeout")
        raise HTTPException(status_code=504, detail="Targets query timeout")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get targets: {e}")
        raise HTTPException(status_code=502, detail="Failed to get targets")


@router.get("/series")
async def get_series(
    request: Request,
    match: List[str] = Query(..., description="Series selector (can be specified multiple times)"),
    start: Optional[datetime] = Query(default_factory=lambda: datetime.utcnow() - timedelta(hours=1)),
    end: Optional[datetime] = Query(default_factory=datetime.utcnow),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Get time series that match label selectors
    
    Args:
        match: Series selectors
        start: Start time
        end: End time
        
    Returns:
        List of matching time series
    """
    if current_user:
        require_role(current_user, ["admin", "developer"])
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            params = {
                "start": int(start.timestamp()),
                "end": int(end.timestamp())
            }
            
            # Add all match parameters
            for matcher in match:
                params[f"match[]"] = matcher
            
            response = await client.get(
                "http://prometheus:9090/api/v1/series",
                params=params
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to get series: {response.status_code}")
                raise HTTPException(status_code=502, detail="Failed to get series")
            
            data = response.json()
            
            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                raise HTTPException(status_code=400, detail=f"Query error: {error_msg}")
            
            return {"series": data["data"]}
    
    except httpx.TimeoutException:
        logger.error("Prometheus series query timeout")
        raise HTTPException(status_code=504, detail="Series query timeout")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get series: {e}")
        raise HTTPException(status_code=502, detail="Failed to get series")


@router.get("/labels")
async def get_labels(
    request: Request,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Get all label names
    
    Returns:
        List of label names
    """
    if current_user:
        require_role(current_user, ["admin", "developer", "viewer"])
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://prometheus:9090/api/v1/labels")
            
            if response.status_code != 200:
                logger.error(f"Failed to get labels: {response.status_code}")
                raise HTTPException(status_code=502, detail="Failed to get labels")
            
            data = response.json()
            
            if data.get("status") != "success":
                raise HTTPException(status_code=502, detail="Failed to get labels")
            
            return {"labels": data["data"]}
    
    except httpx.TimeoutException:
        logger.error("Prometheus labels query timeout")
        raise HTTPException(status_code=504, detail="Labels query timeout")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get labels: {e}")
        raise HTTPException(status_code=502, detail="Failed to get labels")


@router.get("/label/{label}/values")
async def get_label_values(
    request: Request,
    label: str,
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Get all values for a specific label
    
    Args:
        label: Label name
        
    Returns:
        List of label values
    """
    if current_user:
        require_role(current_user, ["admin", "developer", "viewer"])
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"http://prometheus:9090/api/v1/label/{label}/values")
            
            if response.status_code != 200:
                logger.error(f"Failed to get label values: {response.status_code}")
                raise HTTPException(status_code=502, detail="Failed to get label values")
            
            data = response.json()
            
            if data.get("status") != "success":
                raise HTTPException(status_code=502, detail="Failed to get label values")
            
            return {"values": data["data"]}
    
    except httpx.TimeoutException:
        logger.error("Prometheus label values query timeout")
        raise HTTPException(status_code=504, detail="Label values query timeout")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get label values: {e}")
        raise HTTPException(status_code=502, detail="Failed to get label values")


@router.get("/dashboard")
async def get_dashboard_metrics(
    request: Request,
    current_user = Depends(get_current_user_optional),
    search_orchestrator: SearchOrchestrator = Depends(get_search_orchestrator),
    cache_manager: CacheManager = Depends(get_cache_manager)
):
    """
    GET /api/v1/metrics/dashboard - Get dashboard metrics
    
    Returns comprehensive metrics for the search configuration dashboard
    including search statistics, cache performance, and provider status.
    """
    if current_user:
        require_role(current_user, ["admin", "developer", "viewer"])
    
    try:
        logger.info("Fetching dashboard metrics")
        
        # Get cache statistics
        cache_stats = {}
        try:
            cache_health = await cache_manager.health_check()
            cache_stats = {
                "hit_rate": 0.75,  # Would come from cache metrics
                "total_requests": 1000,  # Would come from cache metrics
                "cache_size_mb": 45.2    # Would come from cache metrics
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            cache_stats = {"hit_rate": 0, "total_requests": 0, "cache_size_mb": 0}
        
        # Get MCP provider status
        active_providers = 0
        mcp_stats = {}
        if hasattr(search_orchestrator, 'mcp_enhancer') and search_orchestrator.mcp_enhancer:
            try:
                # Get provider count from MCP enhancer
                active_providers = 2  # Would come from actual provider registry
                mcp_stats = {
                    "external_searches_24h": 150,
                    "avg_external_latency_ms": 280,
                    "provider_success_rate": 0.95
                }
            except Exception as e:
                logger.warning(f"Failed to get MCP stats: {e}")
        
        # Get workspace count (simplified)
        vector_workspaces = 0
        try:
            if hasattr(search_orchestrator, 'workspace_strategy'):
                # Would get actual workspace count
                vector_workspaces = 3  # Placeholder
        except Exception as e:
            logger.warning(f"Failed to get workspace count: {e}")
        
        # Generate hourly search volume data (last 24 hours)
        search_volume_hourly = []
        base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        for i in range(24):
            hour_time = base_time - timedelta(hours=23-i)
            search_volume_hourly.append({
                "hour": hour_time.strftime("%H:00"),
                "searches": max(0, 50 + (i % 4) * 25),  # Simulated pattern
                "avgLatency": 200 + (i % 3) * 50
            })
        
        # Generate recent searches (mock data for now)
        recent_searches = []
        for i in range(5):
            recent_searches.append({
                "timestamp": (datetime.now() - timedelta(minutes=i*2)).isoformat(),
                "query": f"example search query {i+1}",
                "type": "Vector" if i % 2 == 0 else "External",
                "latency_ms": 200 + (i * 50),
                "results_count": 5 + (i * 2),
                "status": "healthy"
            })
        
        # Compile dashboard response
        dashboard_metrics = {
            "total_searches_24h": 1250,
            "avg_latency_ms": cache_stats.get("avg_latency", 0) or 185,
            "cache_hit_rate": cache_stats.get("hit_rate", 0),
            "error_rate": 0.02,
            "active_providers": active_providers,
            "vector_workspaces": vector_workspaces,
            "search_volume_hourly": search_volume_hourly,
            "recent_searches": recent_searches,
            "cache_stats": cache_stats,
            "mcp_stats": mcp_stats,
            "timestamp": datetime.now().isoformat()
        }
        
        return dashboard_metrics
        
    except Exception as e:
        logger.error(f"Failed to get dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve dashboard metrics: {str(e)}")