# Backend API Requirements for Monitoring Dashboard

## 🎯 Overview
This document outlines the backend API requirements needed to support the comprehensive monitoring dashboard for DocAIche.

## 📡 API Endpoints

### 1. Logs Management API

#### GET /api/v1/logs/services
**Purpose**: List all available services for log viewing
```json
Response:
{
  "services": [
    {
      "id": "api",
      "name": "DocAIche API",
      "status": "running",
      "log_level": "INFO"
    },
    {
      "id": "admin-ui",
      "name": "Admin UI",
      "status": "running",
      "log_level": "INFO"
    },
    {
      "id": "redis",
      "name": "Redis Cache",
      "status": "running",
      "log_level": "WARN"
    }
  ]
}
```

#### GET /api/v1/logs/{service_id}
**Purpose**: Retrieve logs for a specific service
```
Query Parameters:
- level: string (DEBUG|INFO|WARN|ERROR)
- start_time: ISO timestamp
- end_time: ISO timestamp
- search: string (search term)
- limit: int (default: 1000)
- offset: int (pagination)

Response:
{
  "logs": [
    {
      "timestamp": "2025-01-29T10:30:45.123Z",
      "level": "INFO",
      "service": "api",
      "message": "Request processed successfully",
      "metadata": {
        "request_id": "123e4567-e89b-12d3-a456-426614174000",
        "duration_ms": 145
      }
    }
  ],
  "total": 15234,
  "has_more": true
}
```

#### WebSocket /ws/logs/{service_id}
**Purpose**: Real-time log streaming
```json
Message Format:
{
  "type": "log",
  "data": {
    "timestamp": "2025-01-29T10:30:45.123Z",
    "level": "INFO",
    "service": "api",
    "message": "New connection established",
    "metadata": {}
  }
}
```

### 2. Container Management API

#### GET /api/v1/containers
**Purpose**: List all containers with their status
```json
Response:
{
  "containers": [
    {
      "id": "docaiche-api-1",
      "name": "DocAIche API",
      "image": "docaiche:api-latest",
      "status": "running",
      "created": "2025-01-29T08:00:00Z",
      "ports": ["4080:4080"],
      "resources": {
        "cpu_percent": 15.5,
        "memory_mb": 256,
        "memory_percent": 12.5,
        "network_rx_mb": 1024,
        "network_tx_mb": 512
      }
    }
  ]
}
```

#### POST /api/v1/containers/{container_id}/action
**Purpose**: Execute container actions
```json
Request:
{
  "action": "restart" // start|stop|restart
}

Response:
{
  "success": true,
  "message": "Container restarted successfully"
}
```

#### GET /api/v1/containers/{container_id}/logs
**Purpose**: Get container logs (last N lines)
```
Query Parameters:
- lines: int (default: 100)
- follow: bool (stream logs)

Response:
{
  "logs": "2025-01-29 10:30:45 INFO Starting application...\n..."
}
```

#### WebSocket /ws/terminal/{container_id}
**Purpose**: SSH terminal access to container
```
Protocol: Binary WebSocket
- Send: Terminal input (stdin)
- Receive: Terminal output (stdout/stderr)
- Special messages for resize events
```

### 3. Metrics & Monitoring API

#### GET /api/v1/metrics/dashboards
**Purpose**: List available Grafana dashboards
```json
Response:
{
  "dashboards": [
    {
      "id": "system-overview",
      "title": "System Overview",
      "description": "Overall system health and performance",
      "url": "/grafana/d/system-overview",
      "tags": ["system", "overview"]
    },
    {
      "id": "api-metrics",
      "title": "API Performance",
      "description": "API request metrics and latencies",
      "url": "/grafana/d/api-metrics",
      "tags": ["api", "performance"]
    }
  ]
}
```

#### GET /api/v1/metrics/query
**Purpose**: Execute Prometheus/Grafana queries
```
Query Parameters:
- query: string (PromQL query)
- start: timestamp
- end: timestamp
- step: duration

Response:
{
  "resultType": "matrix",
  "result": [
    {
      "metric": {
        "__name__": "http_requests_total",
        "method": "GET",
        "status": "200"
      },
      "values": [
        [1643723400, "1234"],
        [1643723460, "1245"]
      ]
    }
  ]
}
```

#### GET /api/v1/metrics/alerts
**Purpose**: Get active alerts
```json
Response:
{
  "alerts": [
    {
      "id": "high-cpu-usage",
      "name": "High CPU Usage",
      "severity": "warning",
      "service": "api",
      "description": "CPU usage above 80% for 5 minutes",
      "started_at": "2025-01-29T10:00:00Z",
      "value": 85.5,
      "threshold": 80
    }
  ]
}
```

### 4. System Information API

#### GET /api/v1/system/info
**Purpose**: Get system information
```json
Response:
{
  "version": "1.0.0",
  "environment": "production",
  "uptime_seconds": 86400,
  "services": {
    "api": "healthy",
    "database": "healthy",
    "cache": "healthy",
    "search": "degraded"
  },
  "resources": {
    "total_cpu_cores": 8,
    "total_memory_gb": 16,
    "total_disk_gb": 100,
    "used_cpu_percent": 45,
    "used_memory_gb": 8.5,
    "used_disk_gb": 35
  }
}
```

## 🔧 Implementation Details

### Authentication & Authorization
- All endpoints require authentication via JWT token
- Role-based access control:
  - `admin`: Full access to all features
  - `developer`: Read logs, view metrics, no container actions
  - `viewer`: Read-only access to dashboards

### Rate Limiting
- General API: 100 requests/minute
- Log queries: 20 requests/minute
- Metrics queries: 30 requests/minute
- WebSocket connections: 10 concurrent per user

### Caching Strategy
- Service list: Cache for 5 minutes
- Dashboard list: Cache for 1 hour
- Metrics data: Cache based on query time range
- Container list: Real-time (no caching)

### Error Handling
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Container not found",
    "details": {
      "container_id": "invalid-id"
    }
  }
}
```

## 🏗️ Infrastructure Requirements

### Loki Configuration
```yaml
# loki-config.yaml
auth_enabled: false

server:
  http_listen_port: 3100

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1

schema_config:
  configs:
    - from: 2024-01-01
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  retention_period: 168h
```

### Promtail Configuration
```yaml
# promtail-config.yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: containers
    static_configs:
      - targets:
          - localhost
        labels:
          job: dockerlogs
          __path__: /var/lib/docker/containers/*/*log
    pipeline_stages:
      - json:
          expressions:
            output: log
            stream: stream
            attrs:
      - json:
          expressions:
            tag:
          source: attrs
      - regex:
          expression: (?P<service>(?:[^|]*))\|(?P<image_tag>(?:[^|]*))\|(?P<instance_name>(?:[^|]*))
          source: tag
      - timestamp:
          format: RFC3339Nano
          source: time
      - labels:
          stream:
          service:
          image_tag:
          instance_name:
      - output:
          source: output
```

### Docker Compose Updates
```yaml
# Additional services for monitoring
services:
  loki:
    image: grafana/loki:2.9.0
    ports:
      - "3100:3100"
    volumes:
      - ./loki-config.yaml:/etc/loki/local-config.yaml
      - loki_data:/loki
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - docaiche_network

  promtail:
    image: grafana/promtail:2.9.0
    volumes:
      - ./promtail-config.yaml:/etc/promtail/config.yml
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock
    command: -config.file=/etc/promtail/config.yml
    networks:
      - docaiche_network

  grafana:
    image: grafana/grafana:10.0.0
    ports:
      - "3000:3000"
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
      - GF_AUTH_ANONYMOUS_ORG_ROLE=Admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    networks:
      - docaiche_network

volumes:
  loki_data:
  grafana_data:
```

## 📊 Metrics to Collect

### Application Metrics
- HTTP request rate, error rate, duration (RED)
- Database query performance
- Cache hit/miss rates
- Search query performance
- WebSocket connection counts

### System Metrics
- CPU utilization (USE)
- Memory usage
- Disk I/O
- Network traffic
- Container resource usage

### Business Metrics
- Active users
- Documents processed
- Search queries per minute
- AI provider usage
- Error rates by service

## 🔐 Security Considerations

### API Security
- JWT tokens with short expiration (15 minutes)
- Refresh token rotation
- API key authentication for service-to-service
- Rate limiting per user/IP
- Request signing for sensitive operations

### Log Security
- PII redaction in logs
- Log retention policies
- Audit logging for all access
- Encryption at rest and in transit

### Container Security
- SSH access requires admin role
- Session timeout after 30 minutes of inactivity
- Command logging for audit trail
- Resource limits on terminal sessions
- Network isolation for containers

## 🚀 Next Steps

1. Set up Loki and Promtail for log aggregation
2. Configure Grafana with initial dashboards
3. Implement authentication middleware
4. Create log streaming endpoints
5. Implement container management API
6. Set up WebSocket handlers for real-time features
7. Create metrics proxy endpoints
8. Implement caching layer
9. Add comprehensive error handling
10. Write API documentation