import { prometheusClient, MetricDataPoint } from './prometheus-client';
import { lokiClient, LogEntry } from './loki-client';

export interface CorrelationContext {
  timestamp: number;
  service?: string;
  container?: string;
  labels?: Record<string, string>;
  windowMs?: number;
}

export interface CorrelatedData {
  metrics: {
    [metricName: string]: MetricDataPoint[];
  };
  logs: LogEntry[];
  anomalies: AnomalyEvent[];
  relatedServices: string[];
}

export interface AnomalyEvent {
  timestamp: number;
  type: 'spike' | 'drop' | 'missing_data' | 'threshold_breach';
  severity: 'low' | 'medium' | 'high' | 'critical';
  metric: string;
  value: number;
  threshold?: number;
  message: string;
}

class CorrelationEngine {
  /**
   * Get all correlated data for a specific point in time
   */
  async getCorrelatedData(context: CorrelationContext): Promise<CorrelatedData> {
    const { timestamp, service, container, labels, windowMs = 300000 } = context; // 5 min window default
    
    const startTime = timestamp - windowMs / 2;
    const endTime = timestamp + windowMs / 2;

    // Fetch metrics and logs in parallel
    const [containerMetrics, logs, serviceMetrics] = await Promise.all([
      // Get container metrics if container is specified
      container ? this.getContainerMetricsForTime(container, startTime, endTime) : Promise.resolve({}),
      
      // Get logs around the timestamp
      this.getCorrelatedLogs(timestamp, windowMs, { service, container }),
      
      // Get service-level metrics if service is specified
      service ? this.getServiceMetricsForTime(service, startTime, endTime) : Promise.resolve({})
    ]);

    // Merge metrics
    const metrics = { ...containerMetrics, ...serviceMetrics };

    // Detect anomalies in the metrics
    const anomalies = this.detectAnomalies(metrics, timestamp);

    // Find related services from logs and metrics
    const relatedServices = this.findRelatedServices(logs, metrics);

    return {
      metrics,
      logs,
      anomalies,
      relatedServices
    };
  }

  /**
   * Get container-specific metrics for a time window
   */
  private async getContainerMetricsForTime(
    container: string,
    start: number,
    end: number
  ): Promise<Record<string, MetricDataPoint[]>> {
    const queries = {
      cpu: `rate(container_cpu_usage_seconds_total{container="${container}"}[5m]) * 100`,
      memory: `container_memory_usage_bytes{container="${container}"}`,
      network_rx: `rate(container_network_receive_bytes_total{container="${container}"}[5m])`,
      network_tx: `rate(container_network_transmit_bytes_total{container="${container}"}[5m])`,
      restarts: `container_restart_count{container="${container}"}`
    };

    const results: Record<string, MetricDataPoint[]> = {};

    await Promise.all(
      Object.entries(queries).map(async ([metric, query]) => {
        try {
          const data = await prometheusClient.queryRange(query, start, end, '30s');
          if (data.length > 0) {
            results[`container_${metric}`] = data[0].data;
          }
        } catch (error) {
          console.error(`Failed to fetch container metric ${metric}:`, error);
        }
      })
    );

    return results;
  }

  /**
   * Get service-specific metrics for a time window
   */
  private async getServiceMetricsForTime(
    service: string,
    start: number,
    end: number
  ): Promise<Record<string, MetricDataPoint[]>> {
    const queries = {
      request_rate: `sum(rate(http_requests_total{service="${service}"}[5m]))`,
      error_rate: `sum(rate(http_requests_total{service="${service}",status=~"5.."}[5m]))`,
      latency_p95: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{service="${service}"}[5m]))`,
      active_connections: `http_connections_active{service="${service}"}`
    };

    const results: Record<string, MetricDataPoint[]> = {};

    await Promise.all(
      Object.entries(queries).map(async ([metric, query]) => {
        try {
          const data = await prometheusClient.queryRange(query, start, end, '30s');
          if (data.length > 0) {
            results[`service_${metric}`] = data[0].data;
          }
        } catch (error) {
          console.error(`Failed to fetch service metric ${metric}:`, error);
        }
      })
    );

    return results;
  }

  /**
   * Get correlated logs for a specific time
   */
  private async getCorrelatedLogs(
    timestamp: number,
    windowMs: number,
    filters?: { service?: string; container?: string }
  ): Promise<LogEntry[]> {
    const lokiFilters = filters ? {
      service: filters.service ? [filters.service] : undefined,
      container: filters.container ? [filters.container] : undefined
    } : undefined;
    
    const logs = await lokiClient.getLogsAroundTime(timestamp, windowMs, lokiFilters);
    
    // Sort logs by relevance (closest to the timestamp first)
    return logs.sort((a, b) => {
      const aDiff = Math.abs(a.timestamp - timestamp);
      const bDiff = Math.abs(b.timestamp - timestamp);
      return aDiff - bDiff;
    });
  }

  /**
   * Detect anomalies in metrics
   */
  private detectAnomalies(
    metrics: Record<string, MetricDataPoint[]>,
    targetTimestamp: number
  ): AnomalyEvent[] {
    const anomalies: AnomalyEvent[] = [];

    Object.entries(metrics).forEach(([metricName, dataPoints]) => {
      if (dataPoints.length < 3) return;

      // Find the data point closest to our target timestamp
      const targetPoint = dataPoints.reduce((closest, point) => {
        const closestDiff = Math.abs(closest.timestamp - targetTimestamp);
        const pointDiff = Math.abs(point.timestamp - targetTimestamp);
        return pointDiff < closestDiff ? point : closest;
      });

      const targetIndex = dataPoints.indexOf(targetPoint);
      
      // Calculate statistics for anomaly detection
      const values = dataPoints.map(d => d.value);
      const mean = values.reduce((a, b) => a + b, 0) / values.length;
      const stdDev = Math.sqrt(
        values.reduce((sq, n) => sq + Math.pow(n - mean, 2), 0) / values.length
      );

      // Check for spikes (3 standard deviations)
      if (targetPoint.value > mean + 3 * stdDev) {
        anomalies.push({
          timestamp: targetPoint.timestamp,
          type: 'spike',
          severity: targetPoint.value > mean + 4 * stdDev ? 'critical' : 'high',
          metric: metricName,
          value: targetPoint.value,
          threshold: mean + 3 * stdDev,
          message: `${metricName} spiked to ${targetPoint.value.toFixed(2)} (${((targetPoint.value / mean - 1) * 100).toFixed(1)}% above average)`
        });
      }

      // Check for drops
      if (targetPoint.value < mean - 3 * stdDev && mean > 0) {
        anomalies.push({
          timestamp: targetPoint.timestamp,
          type: 'drop',
          severity: targetPoint.value < mean - 4 * stdDev ? 'critical' : 'high',
          metric: metricName,
          value: targetPoint.value,
          threshold: mean - 3 * stdDev,
          message: `${metricName} dropped to ${targetPoint.value.toFixed(2)} (${((1 - targetPoint.value / mean) * 100).toFixed(1)}% below average)`
        });
      }

      // Check for missing data
      if (targetIndex > 0) {
        const prevPoint = dataPoints[targetIndex - 1];
        const timeDiff = targetPoint.timestamp - prevPoint.timestamp;
        const expectedInterval = 30000; // 30 seconds
        
        if (timeDiff > expectedInterval * 3) {
          anomalies.push({
            timestamp: targetPoint.timestamp,
            type: 'missing_data',
            severity: 'medium',
            metric: metricName,
            value: timeDiff / 1000,
            message: `Data gap of ${(timeDiff / 1000).toFixed(0)} seconds detected in ${metricName}`
          });
        }
      }
    });

    return anomalies;
  }

  /**
   * Find related services from logs and metrics
   */
  private findRelatedServices(
    logs: LogEntry[],
    metrics: Record<string, MetricDataPoint[]>
  ): string[] {
    const services = new Set<string>();

    // Extract services from logs
    logs.forEach(log => {
      if (log.service) {
        services.add(log.service);
      }
      
      // Look for service names in log messages
      const servicePattern = /service[:\s]+(\w+)/gi;
      let match;
      while ((match = servicePattern.exec(log.message)) !== null) {
        services.add(match[1]);
      }
    });

    // Extract services from metric labels
    Object.entries(metrics).forEach(([metricName, dataPoints]) => {
      dataPoints.forEach(point => {
        if (point.metadata?.service) {
          services.add(point.metadata.service);
        }
      });
    });

    return Array.from(services);
  }

  /**
   * Analyze error propagation across services
   */
  async analyzeErrorPropagation(
    errorTimestamp: number,
    sourceService: string,
    windowMs: number = 300000
  ): Promise<{
    propagationPath: string[];
    affectedServices: Array<{
      service: string;
      firstErrorTime: number;
      errorCount: number;
    }>;
    rootCause?: string;
  }> {
    const startTime = errorTimestamp - windowMs / 2;
    const endTime = errorTimestamp + windowMs / 2;

    // Get error logs from all services
    const errorLogs = await lokiClient.getErrorLogs({ start: startTime, end: endTime });
    
    // Group errors by service and time
    const serviceErrors = new Map<string, LogEntry[]>();
    errorLogs.forEach(log => {
      if (log.service) {
        if (!serviceErrors.has(log.service)) {
          serviceErrors.set(log.service, []);
        }
        serviceErrors.get(log.service)!.push(log);
      }
    });

    // Sort services by first error occurrence
    const affectedServices = Array.from(serviceErrors.entries())
      .map(([service, logs]) => ({
        service,
        firstErrorTime: Math.min(...logs.map(l => l.timestamp)),
        errorCount: logs.length
      }))
      .sort((a, b) => a.firstErrorTime - b.firstErrorTime);

    // Determine propagation path
    const propagationPath = affectedServices.map(s => s.service);

    // Try to identify root cause
    let rootCause: string | undefined;
    if (affectedServices.length > 0) {
      const firstService = affectedServices[0];
      const firstErrors = serviceErrors.get(firstService.service) || [];
      
      // Look for common patterns in early errors
      const errorPatterns = [
        { pattern: /connection refused/i, cause: 'Service unavailable' },
        { pattern: /timeout/i, cause: 'Service timeout' },
        { pattern: /out of memory/i, cause: 'Memory exhaustion' },
        { pattern: /disk full/i, cause: 'Disk space exhausted' },
        { pattern: /rate limit/i, cause: 'Rate limiting triggered' }
      ];

      for (const error of firstErrors) {
        for (const { pattern, cause } of errorPatterns) {
          if (pattern.test(error.message)) {
            rootCause = `${cause} in ${firstService.service}`;
            break;
          }
        }
        if (rootCause) break;
      }
    }

    return {
      propagationPath,
      affectedServices,
      rootCause
    };
  }
}

// Export singleton instance
export const correlationEngine = new CorrelationEngine();