# Provider & Service Configuration Monitoring Dashboard

## Overview

A comprehensive Grafana dashboard has been created to monitor provider initialization and service configuration operations. This dashboard provides real-time visibility into:

- Provider initialization success/failure rates
- Configuration operation durations
- Service restart metrics
- System configuration persistence

## Dashboard Location

**File**: `/grafana/dashboards/provider-config-monitoring.json`
**Dashboard ID**: `provider-config-monitoring`
**Folder**: DocAIche

## Accessing the Dashboard

1. **Open Grafana**:
   ```
   http://localhost:3000
   ```

2. **Login Credentials**:
   - Username: `admin`
   - Password: `admin` (or as configured in your deployment)

3. **Navigate to Dashboard**:
   - Click "Dashboards" in the left menu
   - Look for "DocAIche" folder
   - Select "Provider & Service Configuration Monitoring"

## Dashboard Panels

### Summary Statistics (Top Row)
1. **Total Provider Initializations** - Count of successful provider setups
2. **Failed Provider Initializations** - Count of failed provider setups
3. **Avg Provider Init Duration** - Average time to initialize providers
4. **Successful Service Restarts** - Count of successful service restarts

### Time Series Visualizations
1. **Provider Initialization Duration by Provider** - Shows initialization time for each provider
2. **Service Restart Duration** - Tracks service restart times over time

### Detailed Tables
1. **Provider Configuration Operations** - Lists all provider operations with status and duration
2. **Service Restart History** - Shows service restart events with duration

### Distribution Charts
1. **Provider Initialization Distribution** - Pie chart showing relative init times
2. **Service Restart Rate by Status** - Bar chart of restart success/failure rates

## Metrics Being Tracked

The dashboard monitors these key metrics:

### Provider Metrics
- `provider_initialization_count` - Counter for initialization attempts
- `provider_initialization_duration` - Gauge for init duration in seconds
- `provider_config_operation_duration` - Gauge for config operations

### Service Metrics
- `service_restart_count` - Counter for service restart attempts
- `service_restart_duration` - Gauge for restart duration
- `model_selection_operation_duration` - Gauge for model selection ops

## Current Status

✅ **Dashboard Created**: The dashboard JSON is properly configured
✅ **Grafana Provisioning**: Dashboard is auto-loaded via provisioning
⚠️ **Metrics Collection**: Metrics are being logged but not yet exposed to Prometheus

## Next Steps for Full Functionality

To enable full metrics collection, these metrics need to be:

1. **Option A: Expose via /metrics endpoint**
   - Implement a proper Prometheus metrics endpoint in the API
   - Use `prometheus_client` library for proper metric exposition

2. **Option B: Use Loki Recording Rules**
   - Configure Loki to extract metrics from logs
   - Create recording rules to expose metrics to Prometheus

3. **Option C: Use Promtail metric extraction**
   - Configure Promtail to extract metrics from logs
   - Push to Prometheus Pushgateway

## Example Metric Log Format

The application logs metrics in this format:
```
METRIC provider_initialization_duration=0.009804725646972656 status="success" providers_total="8"
METRIC provider_initialization_count=1 status="success" operation="startup"
```

These are being captured by Promtail and sent to Loki, but need to be exposed to Prometheus for the dashboard to function.

## Verification

Once metrics are properly exposed, you can verify by:

1. Checking Prometheus targets:
   ```
   http://localhost:9090/targets
   ```

2. Querying metrics directly:
   ```
   curl http://localhost:4080/metrics | grep provider_
   ```

3. Using the test script:
   ```bash
   ./scripts/test-config-metrics.sh
   ```

## Benefits

This dashboard provides:
- Real-time visibility into configuration operations
- Early warning of configuration failures
- Performance tracking for optimization
- Historical data for troubleshooting
- Compliance with monitoring best practices