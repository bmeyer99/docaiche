# Service Metrics and Monitoring

This document describes the comprehensive metrics and monitoring capabilities for service configuration management, provider operations, and service restart orchestration in DocAIche.

## Overview

The service metrics system provides complete observability for:
- Provider configuration operations (initialization, updates, testing)
- Service configuration changes and propagation
- Automated and manual service restarts
- Health monitoring and performance tracking
- Correlation tracking across distributed operations

All metrics are exposed in Prometheus format and all logs are structured for Loki ingestion.

## Provider Configuration Metrics

### Provider Initialization Metrics

#### `provider_initialization_duration`
- **Type**: Histogram/Gauge
- **Description**: Duration of provider initialization at startup
- **Labels**:
  - `status`: `success` | `failed`
  - `providers_total`: Total number of providers being initialized
  - `error_type`: Error type if failed (e.g., `TypeError`, `DatabaseError`)
- **Unit**: Seconds
- **Example**: `provider_initialization_duration{status="success",providers_total="8"} 5.722`

#### `provider_initialization_count`
- **Type**: Counter
- **Description**: Count of provider initialization attempts
- **Labels**:
  - `status`: `success` | `failed`
  - `operation`: `startup`
- **Example**: `provider_initialization_count{status="success",operation="startup"} 1`

#### `provider_config_operation_duration`
- **Type**: Histogram/Gauge
- **Description**: Duration of individual provider configuration operations
- **Labels**:
  - `provider_id`: Provider identifier (e.g., `ollama`, `openai`, `anthropic`)
  - `operation`: `initialize` | `update`
  - `status`: `success` | `failed`
  - `error_type`: Error type if failed
- **Unit**: Seconds
- **Example**: `provider_config_operation_duration{provider_id="ollama",operation="initialize",status="success"} 0.125`

### Provider Test Metrics

#### `provider_test_duration`
- **Type**: Histogram/Gauge
- **Description**: Duration of provider connection tests
- **Labels**:
  - `provider_id`: Provider identifier
  - `status`: `success` | `failed` | `timeout` | `exception`
  - `error_type`: Specific error type (e.g., `ConnectError`, `timeout`, `http_401`)
  - `queryable`: `true` | `false` (whether provider supports model discovery)
- **Unit**: Seconds
- **Example**: `provider_test_duration{provider_id="ollama",status="success",queryable="true"} 0.234`

#### `provider_test_models_discovered`
- **Type**: Gauge
- **Description**: Number of models discovered during provider test (for queryable providers)
- **Labels**:
  - `provider_id`: Provider identifier
- **Example**: `provider_test_models_discovered{provider_id="ollama"} 7`

### Provider Configuration Update Metrics

#### `provider_config_update_duration`
- **Type**: Histogram/Gauge
- **Description**: Duration of provider configuration updates
- **Labels**:
  - `provider_id`: Provider identifier
  - `status`: `success` | `failed`
  - `error_type`: Error type if failed
- **Unit**: Seconds
- **Example**: `provider_config_update_duration{provider_id="openai",status="success"} 0.045`

#### `provider_config_update_count`
- **Type**: Counter
- **Description**: Count of provider configuration update attempts
- **Labels**:
  - `provider_id`: Provider identifier
  - `status`: `success` | `failed`
- **Example**: `provider_config_update_count{provider_id="openai",status="success"} 3`

## Service Configuration Metrics

### Configuration Change Metrics

#### `service_config_change_count`
- **Type**: Counter
- **Description**: Count of configuration changes detected
- **Labels**:
  - `config_key`: Configuration key that changed (e.g., `ai.providers.ollama`, `redis.host`)
  - `operation`: `change_detected`
- **Example**: `service_config_change_count{config_key="ai.providers.ollama",operation="change_detected"} 2`

#### `service_config_change_duration`
- **Type**: Histogram/Gauge
- **Description**: Total duration of handling a configuration change (including service restarts)
- **Labels**:
  - `config_key`: Configuration key that changed
  - `status`: `success` | `failed`
- **Unit**: Seconds
- **Example**: `service_config_change_duration{config_key="ai.model_selection",status="success"} 12.345`

#### `service_config_persist_duration`
- **Type**: Histogram/Gauge
- **Description**: Duration of persisting configuration to service-specific files
- **Labels**:
  - `config_key`: Configuration key
  - `status`: `success` | `failed`
  - `error_type`: Error type if failed
- **Unit**: Seconds
- **Example**: `service_config_persist_duration{config_key="logging.level",status="success"} 0.023`

## Service Restart Metrics

### Automated Restart Metrics

#### `service_restart_duration`
- **Type**: Histogram/Gauge
- **Description**: Duration of individual service restart operations
- **Labels**:
  - `service_name`: Service name (e.g., `api`, `redis`, `admin-ui`)
  - `status`: `success` | `failed`
  - `error_type`: Error type if failed
- **Unit**: Seconds
- **Example**: `service_restart_duration{service_name="api",status="success"} 8.234`

#### `service_restart_count`
- **Type**: Counter
- **Description**: Count of service restart attempts
- **Labels**:
  - `service_name`: Service name
  - `status`: `success` | `failed`
- **Example**: `service_restart_count{service_name="api",status="success"} 5`

### Manual Restart Metrics

#### `manual_service_restart_duration`
- **Type**: Histogram/Gauge
- **Description**: Duration of manual service restart operations initiated via API
- **Labels**:
  - `service_name`: Service name
  - `status`: `success` | `failed`
  - `error_type`: Error type if failed
- **Unit**: Seconds
- **Example**: `manual_service_restart_duration{service_name="redis",status="success"} 3.456`

## Health Check Metrics

#### `service_health_check_duration`
- **Type**: Histogram/Gauge
- **Description**: Duration of service health check operations
- **Labels**:
  - `service_count`: Number of services checked
  - `status`: `success` | `failed`
  - `error_type`: Error type if failed
- **Unit**: Seconds
- **Example**: `service_health_check_duration{service_count="8",status="success"} 0.567`

## Structured Log Events

All operations emit structured logs with the following event types:

### Provider Events
- `provider_init_start` - Provider initialization begins
- `provider_init_complete` - Provider initialization successful
- `provider_init_error` - Provider initialization failed
- `provider_test_start` - Provider connection test begins
- `provider_test_success` - Provider test successful
- `provider_test_failed` - Provider test failed (HTTP error)
- `provider_test_timeout` - Provider test timed out
- `provider_test_exception` - Provider test encountered exception
- `provider_config_update_start` - Provider configuration update begins
- `provider_config_update_success` - Provider configuration updated
- `provider_config_update_failed` - Provider configuration update failed

### Service Configuration Events
- `config_change_detected` - Configuration change detected
- `config_change_start` - Configuration change handling begins
- `config_change_complete` - Configuration change handling complete
- `config_change_no_restart` - Configuration changed but no restart needed
- `services_restart_required` - Services identified for restart
- `config_persist_success` - Configuration persisted to files
- `config_persist_failed` - Configuration persistence failed

### Service Restart Events
- `service_restart_start` - Service restart initiated
- `service_restart_success` - Service restarted successfully
- `service_restart_failed` - Service restart failed
- `service_health_timeout` - Service did not become healthy within timeout
- `manual_restart_request` - Manual restart requested via API
- `manual_restart_complete` - Manual restart completed
- `manual_restart_failed` - Manual restart failed

### Health Check Events
- `health_check_request` - Health check requested
- `health_check_complete` - Health check completed

## Correlation Tracking

Every configuration change and service operation is tracked with correlation IDs:

### Correlation ID Format
- Provider operations: `init_providers_{timestamp}`
- Configuration changes: `config_{config_key}_{timestamp}`
- Provider tests: `test_provider_{provider_id}_{timestamp}`
- Provider config updates: `config_provider_{provider_id}_{timestamp}`
- Manual restarts: `manual_restart_{service_name}_{timestamp}`
- Health checks: `health_check_{timestamp}`

### Example Correlation Flow
```
1. User updates provider configuration via API
   correlation_id: "config_provider_ollama_1704123456789"
   
2. Configuration saved to database
   correlation_id: "config_provider_ollama_1704123456789"
   
3. Configuration change detected
   correlation_id: "config_ai.providers.ollama_1704123456789"
   
4. Service restart triggered
   correlation_id: "config_ai.providers.ollama_1704123456789"
   
5. API service restarted
   correlation_id: "config_ai.providers.ollama_1704123456789"
```

## Service Configuration Mapping

The following configuration keys trigger service restarts:

| Configuration Key Pattern | Affected Services | Priority Order |
|--------------------------|-------------------|----------------|
| `ai.providers.*` | api | 4 |
| `ai.model_selection` | api | 4 |
| `anythingllm.*` | anythingllm | 3 |
| `search.*` | api | 4 |
| `redis.*` | redis, api | 1, 4 |
| `database.*` | api | 4 |
| `logging.*` | api, admin-ui, promtail | 4, 5, 6 |
| `monitoring.*` | prometheus, grafana | 7, 8 |

**Priority**: Lower number = higher priority (restarted first)

## API Endpoints

### Service Management Endpoints

#### `POST /api/v1/services/{service_name}/restart`
Manually restart a specific service with comprehensive logging.

**Response**:
```json
{
  "service": "api",
  "restart_status": {
    "success": true,
    "duration_seconds": 8.234,
    "healthy": true
  },
  "correlation_id": "manual_restart_api_1704123456789",
  "duration_seconds": 8.567
}
```

#### `GET /api/v1/services/restart-history`
Get service restart history (queries logs/database).

**Query Parameters**:
- `limit`: Maximum number of events to return (default: 100)

#### `POST /api/v1/services/health-check`
Trigger health checks for specified services or all services.

**Request Body**:
```json
{
  "service_names": ["api", "redis", "admin-ui"]  // Optional, checks all if not provided
}
```

**Response**:
```json
{
  "health_status": {
    "api": {
      "status": "running",
      "health_status": "healthy",
      "last_check": "2024-01-01T12:00:00Z",
      "running_for": "2024-01-01T10:00:00Z"
    },
    "redis": {
      "status": "running",
      "health_status": "no_healthcheck",
      "last_check": null,
      "running_for": "2024-01-01T10:00:00Z"
    }
  },
  "services_checked": 2,
  "correlation_id": "health_check_1704123456789",
  "duration_seconds": 0.567
}
```

## Grafana Dashboard Queries

Example Prometheus queries for monitoring:

### Provider Success Rate
```promql
sum(rate(provider_test_duration{status="success"}[5m])) by (provider_id) /
sum(rate(provider_test_duration[5m])) by (provider_id)
```

### Service Restart Success Rate
```promql
sum(rate(service_restart_count{status="success"}[1h])) by (service_name) /
sum(rate(service_restart_count[1h])) by (service_name)
```

### Average Service Restart Duration
```promql
avg(service_restart_duration) by (service_name, status)
```

### Configuration Change Frequency
```promql
sum(rate(service_config_change_count[1h])) by (config_key)
```

### Provider Test Response Times (95th percentile)
```promql
histogram_quantile(0.95, 
  sum(rate(provider_test_duration_bucket[5m])) by (provider_id, le)
)
```

## Alerting Rules

Example Prometheus alerting rules:

```yaml
groups:
  - name: service_health
    rules:
      - alert: ServiceRestartFailureRate
        expr: |
          sum(rate(service_restart_count{status="failed"}[5m])) by (service_name) /
          sum(rate(service_restart_count[5m])) by (service_name) > 0.5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High service restart failure rate for {{ $labels.service_name }}"
          description: "{{ $labels.service_name }} has failed to restart >50% of attempts in the last 5 minutes"
      
      - alert: ProviderTestTimeout
        expr: |
          sum(rate(provider_test_duration{status="timeout"}[5m])) by (provider_id) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Provider {{ $labels.provider_id }} experiencing timeouts"
          description: "Provider {{ $labels.provider_id }} has timeout rate >0.1/sec"
      
      - alert: ConfigurationPersistenceFailure
        expr: |
          sum(rate(service_config_persist_duration{status="failed"}[5m])) > 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Configuration persistence failures detected"
          description: "Failed to persist configuration changes to service files"
```

## Best Practices

1. **Correlation ID Usage**: Always include correlation IDs in logs when tracking related operations
2. **Metric Labels**: Keep label cardinality reasonable - avoid high-cardinality labels like full error messages
3. **Log Levels**: Use appropriate log levels (INFO for normal operations, ERROR for failures)
4. **Health Checks**: Implement proper health checks for all services to enable accurate monitoring
5. **Retention**: Configure appropriate retention policies for metrics and logs based on operational needs

## Troubleshooting

### Missing Metrics
If metrics are not appearing in Prometheus:
1. Check that the API service is running: `docker logs docaiche-api-1`
2. Verify Prometheus scrape configuration includes the API service
3. Check for errors in metric recording: look for `METRIC` entries in logs

### Correlation Tracking
To trace a complete operation:
1. Find the initial correlation ID in logs
2. Search Loki for all logs with that correlation_id: `{app="docaiche"} |= "correlation_id=\"your_id_here\""`
3. Sort by timestamp to see the complete flow

### Service Restart Issues
If services are not restarting properly:
1. Check Docker daemon connectivity
2. Verify service names match Docker Compose service definitions
3. Check for health check timeouts in logs
4. Review service dependencies and restart priorities