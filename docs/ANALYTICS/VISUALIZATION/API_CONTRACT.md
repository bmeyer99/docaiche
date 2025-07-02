# Pipeline Visualization API Contract

## Overview
This document serves as the single source of truth for the Pipeline Visualization System API contract between frontend, API server, and microservices.

## WebSocket Endpoint

### Connection
- **URL**: `ws://admin-ui:4080/api/v1/ws/pipeline`
- **Protocol**: WebSocket
- **Authentication**: Bearer token in initial connection header
- **Reconnection**: Automatic with exponential backoff (1s, 2s, 4s, 8s, max 30s)

### Connection Handshake
```typescript
// Client -> Server (on connection)
{
  "type": "connection_init",
  "payload": {
    "token": "bearer_token_here",
    "client_id": "unique_client_id",
    "subscriptions": ["metrics", "traces", "system_health"]
  }
}

// Server -> Client (acknowledgment)
{
  "type": "connection_ack",
  "payload": {
    "client_id": "unique_client_id",
    "server_time": "2025-01-01T00:00:00Z",
    "available_services": ["web_scraper", "content_processor", "search_engine", "weaviate", "llm_orchestrator"]
  }
}
```

## Message Types

### 1. Metrics Update
Real-time metrics for each service.

```typescript
// Server -> Client
{
  "type": "metrics_update",
  "timestamp": "2025-01-01T00:00:00Z",
  "payload": {
    "service_name": "web_scraper",
    "metrics": {
      "queue_length": 42,
      "avg_latency": 234.5, // milliseconds
      "throughput": 15.3, // requests per second
      "error_rate": 0.02, // percentage
      "memory_usage": 256.7, // MB
      "cpu_usage": 45.2, // percentage
      "active_connections": 12,
      "last_updated": "2025-01-01T00:00:00Z"
    }
  }
}
```

### 2. Trace Update
Individual request trace through the pipeline.

```typescript
// Server -> Client
{
  "type": "trace_update",
  "timestamp": "2025-01-01T00:00:00Z",
  "payload": {
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "in_progress", // "started" | "in_progress" | "completed" | "failed"
    "start_time": "2025-01-01T00:00:00.000Z",
    "current_span": {
      "service_name": "content_processor",
      "span_id": "7435a9fe-9a44-4c9f-8e5c-2c83a24d5ee2",
      "operation": "extract_content",
      "start_time": "2025-01-01T00:00:00.123Z",
      "duration": 45, // milliseconds (null if still running)
      "attributes": {
        "content_type": "html",
        "content_size": 125000,
        "extraction_method": "beautifulsoup"
      }
    },
    "spans": [
      {
        "service_name": "web_scraper",
        "span_id": "123e4567-e89b-12d3-a456-426614174000",
        "parent_span_id": null,
        "operation": "fetch_url",
        "start_time": "2025-01-01T00:00:00.000Z",
        "end_time": "2025-01-01T00:00:00.100Z",
        "duration": 100,
        "status": "completed",
        "attributes": {
          "url": "https://example.com",
          "status_code": 200,
          "content_length": 125000
        }
      }
      // Additional spans...
    ]
  }
}
```

### 3. Service Status Update
Service health and availability status.

```typescript
// Server -> Client
{
  "type": "service_status",
  "timestamp": "2025-01-01T00:00:00Z",
  "payload": {
    "service_name": "llm_orchestrator",
    "status": "healthy", // "healthy" | "degraded" | "unhealthy" | "offline"
    "health_score": 95, // 0-100
    "last_heartbeat": "2025-01-01T00:00:00Z",
    "circuit_breaker": {
      "state": "closed", // "closed" | "open" | "half_open"
      "failure_count": 0,
      "last_failure": null
    },
    "dependencies": {
      "openai": "healthy",
      "anthropic": "degraded",
      "database": "healthy"
    }
  }
}
```

### 4. System Alert
Critical system-wide alerts.

```typescript
// Server -> Client
{
  "type": "system_alert",
  "timestamp": "2025-01-01T00:00:00Z",
  "payload": {
    "alert_id": "alert_123",
    "severity": "warning", // "info" | "warning" | "error" | "critical"
    "service_name": "content_processor",
    "message": "High memory usage detected (>90%)",
    "details": {
      "current_usage": "920MB",
      "threshold": "900MB",
      "trend": "increasing"
    },
    "suggested_action": "Consider scaling the service or optimizing memory usage"
  }
}
```

### 5. Batch Metrics
Aggregated metrics for dashboard view.

```typescript
// Server -> Client
{
  "type": "batch_metrics",
  "timestamp": "2025-01-01T00:00:00Z",
  "payload": {
    "time_range": {
      "start": "2025-01-01T00:00:00Z",
      "end": "2025-01-01T00:05:00Z"
    },
    "services": {
      "web_scraper": {
        "throughput_history": [
          { "timestamp": "2025-01-01T00:00:00Z", "value": 15.2 },
          { "timestamp": "2025-01-01T00:00:30Z", "value": 16.8 }
          // ... more data points
        ],
        "latency_percentiles": {
          "p50": 45,
          "p90": 120,
          "p95": 200,
          "p99": 450
        },
        "error_distribution": {
          "4xx": 12,
          "5xx": 3,
          "timeout": 1,
          "network": 0
        }
      }
      // ... other services
    },
    "system_totals": {
      "total_requests": 1523,
      "successful_requests": 1498,
      "failed_requests": 25,
      "avg_pipeline_latency": 850.3
    }
  }
}
```

## Client Commands

### 1. Subscribe to Specific Traces
```typescript
// Client -> Server
{
  "type": "subscribe_trace",
  "payload": {
    "query_id": "query_123",
    "workspace": "research_workspace"
  }
}
```

### 2. Request Historical Data
```typescript
// Client -> Server
{
  "type": "request_history",
  "payload": {
    "service_name": "web_scraper",
    "metric_type": "throughput",
    "time_range": {
      "start": "2025-01-01T00:00:00Z",
      "end": "2025-01-01T01:00:00Z"
    },
    "resolution": "1m" // 1m, 5m, 15m, 1h
  }
}
```

### 3. Pause/Resume Updates
```typescript
// Client -> Server
{
  "type": "pause_updates",
  "payload": {
    "subscription_types": ["metrics"] // Pause only metrics, keep traces
  }
}
```

## OpenTelemetry Integration

### Service Instrumentation Requirements
Each service MUST export the following metrics to the OpenTelemetry Collector:

```yaml
# Required Metrics
metrics:
  - name: service.request.count
    type: counter
    unit: "1"
    description: Total number of requests processed
    
  - name: service.request.duration
    type: histogram
    unit: "ms"
    description: Request processing duration
    
  - name: service.queue.length
    type: gauge
    unit: "1"
    description: Current queue length
    
  - name: service.error.count
    type: counter
    unit: "1"
    description: Total number of errors
    attributes:
      - error.type: [timeout, validation, server_error, client_error]
      
  - name: service.memory.usage
    type: gauge
    unit: "By"
    description: Current memory usage in bytes
    
  - name: service.cpu.usage
    type: gauge
    unit: "1"
    description: CPU usage percentage (0-100)
```

### Trace Context Propagation
All services MUST propagate trace context using W3C Trace Context standard:

```python
# Example trace context headers
{
  "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
  "tracestate": "congo=t61rcWkgMzE"
}
```

## Error Handling

### WebSocket Errors
```typescript
// Server -> Client
{
  "type": "error",
  "timestamp": "2025-01-01T00:00:00Z",
  "payload": {
    "error_code": "SUBSCRIPTION_FAILED",
    "message": "Failed to subscribe to metrics updates",
    "details": {
      "service": "web_scraper",
      "reason": "Service temporarily unavailable"
    },
    "retry_after": 5000 // milliseconds
  }
}
```

### Error Codes
- `CONNECTION_FAILED`: WebSocket connection failure
- `AUTH_FAILED`: Authentication failure
- `SUBSCRIPTION_FAILED`: Failed to subscribe to updates
- `INVALID_MESSAGE`: Invalid message format
- `RATE_LIMITED`: Too many requests
- `SERVICE_UNAVAILABLE`: Backend service unavailable

## Rate Limiting
- Max connections per client: 5
- Max messages per second: 100
- Metrics update frequency: 1 update per second per service
- Trace updates: Real-time (no throttling)
- Batch requests: Max 1 per 10 seconds

## Data Retention
- Real-time metrics: Last 1 hour
- Historical metrics: Last 24 hours (1-minute resolution)
- Traces: Last 1000 traces or 1 hour (whichever is less)
- Alerts: Last 100 alerts or 24 hours

## Frontend Expected Behaviors

### Connection Management
1. Establish WebSocket connection on component mount
2. Implement automatic reconnection with exponential backoff
3. Show connection status indicator
4. Queue messages during disconnection
5. Resync state after reconnection

### Data Handling
1. Maintain local state for last known metrics
2. Implement data smoothing for visualization
3. Cache trace data for replay functionality
4. Aggregate metrics for dashboard views
5. Handle out-of-order messages gracefully

### Performance Requirements
- Initial connection: < 1 second
- Message processing: < 50ms
- UI update latency: < 100ms
- Memory usage: < 100MB for 1 hour of data
- Frame rate: Maintain 60 FPS during animations

## API Server Expected Behaviors

### Connection Handling
1. Accept WebSocket connections with authentication
2. Maintain client registry with subscriptions
3. Implement connection pooling for services
4. Handle graceful shutdown with client notification
5. Implement circuit breakers for service calls

### Data Processing
1. Aggregate metrics from OpenTelemetry Collector
2. Buffer and batch updates for efficiency
3. Implement message deduplication
4. Maintain sliding window for calculations
5. Filter data based on client subscriptions

### Scalability
- Support 1000+ concurrent WebSocket connections
- Process 10,000+ metrics per second
- Handle 1000+ active traces
- Horizontal scaling via connection routing
- Implement connection affinity for traces

## Service Integration Requirements

### OpenTelemetry SDK
1. Initialize tracer and meter providers
2. Configure OTLP exporter to collector
3. Implement automatic instrumentation
4. Add custom metrics and spans
5. Handle context propagation

### Performance Impact
- Max overhead: < 2% CPU
- Max memory: < 50MB per service
- Sampling rate: 100% for traces (configurable)
- Metric export interval: 10 seconds
- Batch size: 1000 data points

This contract ensures all teams can work independently while maintaining compatibility.