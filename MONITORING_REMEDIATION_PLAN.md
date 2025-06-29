# Monitoring Infrastructure Remediation Plan

## Executive Summary
The code review revealed that only ~25% of the planned monitoring infrastructure was implemented. This document outlines the critical gaps and provides a prioritized remediation plan.

## Critical Gaps Identified

### 1. Missing API Endpoints (CRITICAL)
**Current State**: Zero monitoring-specific API endpoints implemented
**Required State**: Full API implementation as specified in BACKEND_API_REQUIREMENTS.md

#### Immediate Actions Required:
1. Create `src/api/v1/logs_endpoints.py` with:
   - GET /api/v1/logs/services
   - GET /api/v1/logs/{service_id}
   - WebSocket /ws/logs/{service_id}

2. Create `src/api/v1/containers_endpoints.py` with:
   - GET /api/v1/containers
   - POST /api/v1/containers/{container_id}/action
   - GET /api/v1/containers/{container_id}/logs
   - WebSocket /ws/terminal/{container_id}

3. Create `src/api/v1/metrics_endpoints.py` with:
   - GET /api/v1/metrics/dashboards
   - GET /api/v1/metrics/query
   - GET /api/v1/metrics/alerts

### 2. Security Vulnerabilities (CRITICAL)
**Current State**: No authentication, default passwords, no authorization
**Required State**: Full security implementation

#### Immediate Actions Required:
1. Add JWT authentication middleware to all monitoring endpoints
2. Implement role-based access control:
   ```python
   roles = {
       "admin": ["*"],
       "developer": ["logs:read", "metrics:read"],
       "viewer": ["dashboards:read"]
   }
   ```
3. Change Grafana default credentials via environment variables
4. Add audit logging for all monitoring access

### 3. Application Logging Integration (HIGH)
**Current State**: Applications not configured to send logs to Loki
**Required State**: Structured logging to /var/log/docaiche/

#### Immediate Actions Required:
1. Update `src/main.py` to configure file logging:
   ```python
   from src.logging_config import setup_structured_logging
   setup_structured_logging(
       level="INFO",
       enable_file_logging=True,
       log_path="/var/log/docaiche/api.log"
   )
   ```

2. Mount log directory in docker-compose:
   ```yaml
   api:
     volumes:
       - ./logs:/var/log/docaiche
   ```

### 4. Proxy Configuration (HIGH)
**Current State**: No proxy configuration for monitoring services
**Required State**: All monitoring services accessible through admin-ui proxy

#### Update admin-ui proxy configuration:
The admin-ui needs to proxy requests to monitoring services:
- `/grafana/*` → `http://grafana:3000/*`
- `/prometheus/*` → `http://prometheus:9090/*`
- `/loki/*` → `http://loki:3100/*`

This maintains the security model where only port 4080 is exposed externally.

### 5. WebSocket Implementation (HIGH)
**Current State**: No WebSocket support
**Required State**: Real-time log streaming and terminal access

#### Implementation Requirements:
1. Add FastAPI WebSocket support:
   ```python
   from fastapi import WebSocket
   from src.core.websocket import ConnectionManager
   
   manager = ConnectionManager()
   
   @router.websocket("/ws/logs/{service_id}")
   async def websocket_logs(websocket: WebSocket, service_id: str):
       await manager.connect(websocket)
       # Stream logs from Loki
   ```

2. Implement terminal WebSocket for SSH access

### 6. Comprehensive Dashboards (MEDIUM)
**Current State**: One basic dashboard
**Required State**: Multiple role-specific dashboards

#### Required Dashboards:
1. API Performance Dashboard
2. Database Performance Dashboard  
3. Cache Performance Dashboard
4. User Activity Dashboard
5. System Resources Dashboard

## Implementation Priority

### Phase 1: Critical Security & API (Week 1)
1. Implement authentication middleware
2. Create log management API endpoints
3. Add port exposures to docker-compose
4. Configure application logging

### Phase 2: Core Functionality (Week 2)
1. Implement container management API
2. Add WebSocket support for logs
3. Create metrics proxy endpoints
4. Implement basic RBAC

### Phase 3: Advanced Features (Week 3)
1. SSH terminal WebSocket
2. Comprehensive Grafana dashboards
3. Alert management
4. Audit logging

### Phase 4: Production Hardening (Week 4)
1. Resource limits on containers
2. HA configuration
3. Backup strategies
4. Documentation

## Code Templates

### Log Streaming Endpoint Template
```python
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any
import httpx
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/api/v1/logs/{service_id}")
async def get_service_logs(
    service_id: str,
    level: str = Query(None, regex="^(DEBUG|INFO|WARN|ERROR)$"),
    start_time: datetime = Query(default_factory=lambda: datetime.utcnow() - timedelta(hours=1)),
    end_time: datetime = Query(default_factory=datetime.utcnow),
    search: str = Query(None),
    limit: int = Query(1000, le=10000),
    user: dict = Depends(get_current_user)
):
    """Retrieve logs for a specific service"""
    
    # Build Loki query
    query = f'{{service_name="{service_id}"}}'
    if level:
        query += f' |= "{level}"'
    if search:
        query += f' |~ "{search}"'
    
    # Query Loki
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://loki:3100/loki/api/v1/query_range",
            params={
                "query": query,
                "start": int(start_time.timestamp()),
                "end": int(end_time.timestamp()),
                "limit": limit
            }
        )
    
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to query logs")
    
    # Parse and return logs
    data = response.json()
    logs = []
    for stream in data.get("data", {}).get("result", []):
        for value in stream.get("values", []):
            timestamp, log_line = value
            logs.append({
                "timestamp": datetime.fromtimestamp(int(timestamp) / 1e9).isoformat(),
                "message": log_line,
                "service": service_id,
                "metadata": stream.get("stream", {})
            })
    
    return {
        "logs": logs,
        "total": len(logs),
        "has_more": len(logs) >= limit
    }
```

### Container Management Template
```python
import docker
from docker.errors import NotFound, APIError

@router.get("/api/v1/containers")
async def list_containers(
    user: dict = Depends(get_current_user)
):
    """List all containers with their status"""
    require_role(user, ["admin", "developer"])
    
    client = docker.from_env()
    containers = []
    
    for container in client.containers.list(all=True):
        stats = container.stats(stream=False)
        
        # Calculate resource usage
        cpu_percent = calculate_cpu_percent(stats)
        memory_mb = stats["memory_stats"]["usage"] / 1024 / 1024
        
        containers.append({
            "id": container.short_id,
            "name": container.name,
            "image": container.image.tags[0] if container.image.tags else container.image.id,
            "status": container.status,
            "created": container.attrs["Created"],
            "ports": container.attrs["NetworkSettings"]["Ports"],
            "resources": {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_mb,
                "memory_percent": (memory_mb / stats["memory_stats"]["limit"]) * 100
            }
        })
    
    return {"containers": containers}
```

## Testing Strategy

1. **Unit Tests**: Test each API endpoint with mocked dependencies
2. **Integration Tests**: Test full flow from API to monitoring services
3. **Security Tests**: Verify authentication and authorization
4. **Load Tests**: Ensure WebSocket connections scale appropriately

## Success Criteria

1. All planned API endpoints operational
2. Authentication required on all endpoints
3. Real-time log streaming functional
4. SSH terminal access working
5. Comprehensive dashboards available
6. Production-ready security measures in place

## Risk Mitigation

1. **Security Risk**: Implement defense-in-depth with multiple auth layers
2. **Performance Risk**: Add caching layer for frequently accessed metrics
3. **Availability Risk**: Implement circuit breakers for external service calls
4. **Data Loss Risk**: Configure persistent volumes with backup strategy

## Estimated Timeline

- **Total Duration**: 4 weeks
- **Developer Resources**: 2 full-time developers
- **Testing**: 1 week integrated throughout
- **Documentation**: Ongoing

This remediation plan addresses all critical gaps identified in the code review and provides a clear path to achieving the originally planned monitoring infrastructure.