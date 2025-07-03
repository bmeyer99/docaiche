# DocAIche Performance Monitoring Guide

## Overview
The performance monitoring dashboard provides comprehensive visibility into your DocAIche system's health, resource usage, and potential issues before they become critical.

## Accessing the Dashboard
1. Open Grafana at `http://localhost:4080/grafana`
2. Login with credentials: `admin` / `admin`
3. Navigate to Dashboards → DocAIche Performance Monitoring

## Dashboard Sections

### 🔴 Critical Health Indicators
- **Service Health Status**: Real-time UP/DOWN status for all critical services
- **Container CPU Usage**: Live CPU usage with warning thresholds at 50% and 80%
- **Memory Usage vs Limit**: Shows how close containers are to their memory limits

### 📊 Resource Usage Trends
- **Container Resource Summary**: Table view of CPU, Memory, and restart counts
- **Network I/O**: Monitor data transfer rates to identify network bottlenecks

### 🎯 Application Performance
- **API Request Rate**: Track request volume trends
- **API Response Time**: 95th and 99th percentile latencies
- **Error Rate**: 4xx and 5xx error counts

### 🔍 Logs & Errors Analysis
- **Log Volume by Service**: Identify services generating excessive logs
- **Recent Errors**: Real-time error log analysis

### 🎨 Predictive Analytics
- **Memory Usage Prediction**: 1-hour forecast based on current growth
- **System Resource Saturation**: Overall system health gauge

### ⚡ Performance Bottleneck Detection
- **CPU Usage Heatmap**: Visual representation of CPU hotspots
- **Potential Bottlenecks**: Scoring system to identify problematic containers

## Proactive Alerts

The system includes the following alerts:

### Critical Alerts
- **ServiceDown**: Service unavailable for >2 minutes
- **CriticalCPUUsage**: CPU usage >95% for 2 minutes
- **HighErrorRate**: 5xx errors >0.1 req/sec for 5 minutes

### Warning Alerts
- **HighCPUUsage**: CPU >80% for 5 minutes
- **HighMemoryUsage**: Memory >85% of limit
- **MemoryLimitApproaching**: Predicted to hit limit within 1 hour
- **ContainerRestarting**: >2 restarts in last hour
- **SlowAPIResponse**: 95th percentile >2 seconds
- **ExcessiveLogging**: >100 log lines/sec
- **SystemResourceSaturation**: Both CPU and Memory >70%

## Best Practices

1. **Daily Review**: Check the dashboard at least once daily
2. **Alert Response**: Investigate warnings before they become critical
3. **Trend Analysis**: Use the predictive panels to plan capacity
4. **Resource Limits**: Adjust container limits based on actual usage patterns
5. **Log Volume**: High log volume often indicates issues - investigate root cause

## Key Metrics to Watch

1. **CPU Usage**: Keep below 70% for healthy operation
2. **Memory Usage**: Should stay below 80% of limits
3. **Container Restarts**: Any restarts indicate instability
4. **API Response Time**: p95 should be <1 second
5. **Error Rate**: Should be near zero
6. **Log Volume**: Sudden spikes indicate problems

## Troubleshooting

### High CPU Usage
1. Check recent deployments
2. Look for infinite loops in logs
3. Review health check frequencies
4. Check for resource-intensive queries

### High Memory Usage
1. Check for memory leaks
2. Review cache configurations
3. Look for large data processing
4. Check database query efficiency

### Frequent Restarts
1. Check container logs for errors
2. Review resource limits
3. Check for OOM kills
4. Verify health check configurations

## Performance Optimization Tips

1. **Increase scrape intervals** if metrics collection impacts performance
2. **Adjust health check intervals** to reduce unnecessary load
3. **Set appropriate resource limits** to prevent container sprawl
4. **Use the bottleneck scoring** to prioritize optimization efforts
5. **Monitor trends** not just current values for better insights