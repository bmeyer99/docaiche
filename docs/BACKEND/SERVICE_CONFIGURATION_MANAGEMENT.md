# Service Configuration Management

## Overview

The DocAIche service configuration management system provides a sophisticated mechanism for handling configuration changes and triggering service process restarts. This system is designed to handle configuration updates dynamically without requiring container restarts.

## Key Concepts

### Service Process vs Container Restarts

**Important**: When we refer to "restarting a service", we mean restarting the **service process inside the container**, NOT the container itself. This approach provides:

- **Faster restart times** - Process restarts are much quicker than container restarts
- **No Docker daemon access required** - Containers don't need privileged access
- **Service-specific restart mechanisms** - Each service can implement its optimal reload strategy
- **Better scalability** - Pattern works for any configuration change across the system

### Configuration Change Flow

```
1. User updates configuration via API
   ↓
2. Configuration saved to database
   ↓
3. Configuration change detected by ConfigurationManager
   ↓
4. ServiceConfigManager determines affected services
   ↓
5. Service-specific configuration files/env vars updated
   ↓
6. Service process restart triggered (not container restart)
   ↓
7. Service reloads with new configuration
   ↓
8. Comprehensive logging and metrics recorded
```

## Architecture

### Service Configuration Mapping

The `SERVICE_CONFIG_MAP` in `/src/core/services/config_manager.py` defines which service processes need to be restarted when specific configurations change:

```python
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
```

### Service Restart Priority

Services are restarted in priority order to handle dependencies:

```python
SERVICE_RESTART_PRIORITY = {
    "redis": 1,
    "db": 2,
    "anythingllm": 3,
    "promtail": 4,
    "prometheus": 5,
    "grafana": 6,
}
```

## Service-Specific Restart Mechanisms

Each service can implement its own optimal restart mechanism:

### Text AI Service
- **Location**: Runs within the API container
- **Restart Methods**:
  - Send SIGHUP signal to the process
  - Call a reload endpoint (e.g., `/internal/reload`)
  - Write to a watched configuration file
  - Use a message queue for reload notifications

### Embedding Service
- **Location**: Often part of AnythingLLM or a separate service
- **Restart Methods**:
  - Similar to Text AI Service
  - May use AnythingLLM's API for configuration updates

### AnythingLLM Service
- **Location**: Separate container
- **Restart Methods**:
  - Use AnythingLLM API endpoints to reload configuration
  - Update environment variables and signal reload
  - Modify configuration files that AnythingLLM monitors

### Redis Service
- **Location**: Redis container
- **Restart Methods**:
  - Use `CONFIG SET` followed by `CONFIG REWRITE`
  - No actual restart needed - Redis can reload config dynamically

### Other Services
Each service should implement appropriate mechanisms based on its capabilities:
- **Prometheus/Grafana**: Signal-based config reload
- **Promtail**: File-based configuration with inotify
- **Custom services**: HTTP reload endpoints or file watchers

## Implementation Details

### ConfigurationManager Integration

The `ConfigurationManager` (`/src/core/config/manager.py`) includes the `_handle_config_change` method that:

1. Detects configuration changes
2. Generates correlation IDs for tracking
3. Calls the ServiceConfigManager
4. Logs all operations with structured logging

### ServiceConfigManager

The `ServiceConfigManager` (`/src/core/services/config_manager.py`) handles:

1. **Configuration Change Detection**: Determines which services are affected
2. **Configuration Persistence**: Updates service-specific config files/env vars
3. **Service Restart Orchestration**: Triggers service-specific restart mechanisms
4. **Logging and Metrics**: Records comprehensive metrics for monitoring

### Restart Trigger Implementation

The `_trigger_service_restart` method provides service-specific restart logic:

```python
async def _trigger_service_restart(self, service_name: str, correlation_id: str) -> bool:
    """
    Trigger a service process restart using service-specific mechanisms
    """
    if service_name == "text-ai-service":
        # Implement text AI service restart
        # Options: SIGHUP, reload endpoint, config file update
        return True
    elif service_name == "embedding-service":
        # Implement embedding service restart
        return True
    # ... other services
```

## Monitoring and Observability

### Structured Logging

All configuration changes and service restarts are logged with:
- Event types for Loki queries
- Correlation IDs for tracing workflows
- Service names and operation types
- Duration and status information

### Metrics

Prometheus metrics are recorded for:
- `service_config_change_count` - Configuration changes detected
- `service_config_change_duration` - Total duration of config change handling
- `service_restart_count` - Service restart attempts
- `service_restart_duration` - Duration of service restarts
- `service_config_persist_duration` - Time to persist configurations

## Best Practices

1. **Graceful Reloads**: Services should implement graceful reload mechanisms that don't drop active connections
2. **Health Checks**: Services should update their health status during reload
3. **Rollback Capability**: Services should validate new configurations before applying
4. **Minimal Downtime**: Use rolling updates or blue-green deployments where possible
5. **Correlation Tracking**: Always use correlation IDs to trace configuration changes through the system

## Adding New Services

To add configuration management for a new service:

1. **Update SERVICE_CONFIG_MAP**: Add the configuration key and affected service
2. **Add Restart Logic**: Implement the service-specific restart in `_trigger_service_restart`
3. **Implement Reload Mechanism**: Add reload capability to your service (signal handler, API endpoint, etc.)
4. **Add Health Checks**: Ensure the service reports health during reload
5. **Document**: Update this documentation with the new service's restart mechanism

## Example: Adding a New ML Model Service

```python
# In SERVICE_CONFIG_MAP
"ml.model_config": ["ml-model-service"],

# In _trigger_service_restart
elif service_name == "ml-model-service":
    # Call ML service reload endpoint
    async with httpx.AsyncClient() as client:
        response = await client.post("http://ml-service:8080/internal/reload")
    return response.status_code == 200
```

## Troubleshooting

### Service Not Restarting
1. Check SERVICE_CONFIG_MAP has correct mapping
2. Verify service name matches exactly
3. Check logs for correlation ID to trace the flow
4. Ensure service restart mechanism is implemented

### Configuration Not Persisting
1. Verify _persist_*_config methods are implemented
2. Check file permissions for config files
3. Ensure environment variables are properly set
4. Review logs for persistence errors

### Metrics Not Appearing
1. Verify MetricsLogger is properly initialized
2. Check Prometheus scrape configuration
3. Look for METRIC entries in logs
4. Ensure labels have reasonable cardinality