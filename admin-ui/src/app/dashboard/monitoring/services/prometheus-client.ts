import { cache } from 'react';

export interface PrometheusQuery {
  metric: string;
  step?: string;
  start?: number;
  end?: number;
}

export interface PrometheusMetric {
  __name__: string;
  [key: string]: string;
}

export interface PrometheusResult {
  metric: PrometheusMetric;
  values?: [number, string][];
  value?: [number, string];
}

export interface PrometheusResponse {
  status: string;
  data: {
    resultType: string;
    result: PrometheusResult[];
  };
}

export interface MetricDataPoint {
  timestamp: number;
  value: number;
  metadata?: Record<string, string>;
}

export interface MetricSeries {
  name: string;
  data: MetricDataPoint[];
  labels: Record<string, string>;
}

class PrometheusClient {
  private baseUrl: string;

  constructor() {
    // Access Prometheus through the proxy
    this.baseUrl = '/prometheus';
  }

  /**
   * Query instant values from Prometheus
   */
  async queryInstant(query: string, time?: number): Promise<PrometheusResult[]> {
    const params = new URLSearchParams({
      query,
      ...(time && { time: time.toString() })
    });

    const response = await fetch(`${this.baseUrl}/api/v1/query?${params}`);
    
    if (!response.ok) {
      throw new Error(`Prometheus query failed: ${response.statusText}`);
    }

    const data: PrometheusResponse = await response.json();
    return data.data.result;
  }

  /**
   * Query time series data from Prometheus
   */
  async queryRange(
    query: string,
    start: number,
    end: number,
    step: string = '15s'
  ): Promise<MetricSeries[]> {
    const params = new URLSearchParams({
      query,
      start: start.toString(),
      end: end.toString(),
      step
    });

    const response = await fetch(`${this.baseUrl}/api/v1/query_range?${params}`);
    
    if (!response.ok) {
      throw new Error(`Prometheus query failed: ${response.statusText}`);
    }

    const data: PrometheusResponse = await response.json();
    
    // Transform Prometheus data to our format
    return data.data.result.map(result => ({
      name: result.metric.__name__ || query,
      labels: result.metric,
      data: (result.values || []).map(([timestamp, value]) => ({
        timestamp: timestamp * 1000, // Convert to milliseconds
        value: parseFloat(value),
        metadata: result.metric
      }))
    }));
  }

  /**
   * Get available metrics from Prometheus
   */
  async getMetrics(): Promise<string[]> {
    const response = await fetch(`${this.baseUrl}/api/v1/label/__name__/values`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch metrics: ${response.statusText}`);
    }

    const data = await response.json();
    return data.data;
  }

  /**
   * Get label values for a specific label
   */
  async getLabelValues(label: string): Promise<string[]> {
    const response = await fetch(`${this.baseUrl}/api/v1/label/${label}/values`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch label values: ${response.statusText}`);
    }

    const data = await response.json();
    return data.data;
  }

  /**
   * Common metric queries
   */
  async getContainerMetrics(timeRange: { start: number; end: number; step?: string }) {
    const queries = {
      grafana_requests: 'rate(grafana_http_request_duration_seconds_count[5m])',
      weaviate_requests: 'rate(weaviate_http_request_duration_seconds_count[5m])',
      prometheus_requests: 'rate(prometheus_http_requests_total[5m])',
      go_memory: 'go_memstats_alloc_bytes'
    };

    const results = [];
    // Process queries sequentially to avoid overwhelming the server
    for (const [metric, query] of Object.entries(queries)) {
      try {
        const data = await this.queryRange(
          query,
          timeRange.start,
          timeRange.end,
          timeRange.step || '30s'
        );
        results.push({ metric, data });
        // Small delay between requests
        await new Promise(resolve => setTimeout(resolve, 100));
      } catch (error) {
        console.error(`Failed to fetch container metric ${metric}:`, error);
        results.push({ metric, data: [] });
      }
    }

    return results.reduce((acc, { metric, data }) => {
      acc[metric] = data;
      return acc;
    }, {} as Record<string, MetricSeries[]>);
  }

  /**
   * Get Redis metrics
   */
  async getRedisMetrics(timeRange: { start: number; end: number; step?: string }) {
    const queries = {
      uptime: 'redis_uptime_in_seconds',
      connected_clients: 'redis_connected_clients',
      memory_used: 'redis_memory_used_bytes',
      commands_processed: 'rate(redis_commands_processed_total[5m])',
      keyspace_hits: 'rate(redis_keyspace_hits_total[5m])',
      keyspace_misses: 'rate(redis_keyspace_misses_total[5m])',
      hit_rate: 'redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total) * 100'
    };

    const results = [];
    // Process queries sequentially to avoid overwhelming the server
    for (const [metric, query] of Object.entries(queries)) {
      try {
        const data = await this.queryRange(
          query,
          timeRange.start,
          timeRange.end,
          timeRange.step || '30s'
        );
        results.push({ metric, data });
        // Small delay between requests
        await new Promise(resolve => setTimeout(resolve, 100));
      } catch (error) {
        console.error(`Failed to fetch Redis metric ${metric}:`, error);
        results.push({ metric, data: [] });
      }
    }

    return results.reduce((acc, { metric, data }) => {
      acc[metric] = data;
      return acc;
    }, {} as Record<string, MetricSeries[]>);
  }

  /**
   * Get API performance metrics
   */
  async getAPIMetrics(timeRange: { start: number; end: number; step?: string }) {
    const queries = {
      request_rate: 'sum(rate(grafana_http_request_duration_seconds_count[5m]) + rate(weaviate_http_request_duration_seconds_count[5m]))',
      latency_p50: 'histogram_quantile(0.5, rate(grafana_http_request_duration_seconds_bucket[5m]))',
      latency_p95: 'histogram_quantile(0.95, rate(grafana_http_request_duration_seconds_bucket[5m]))',
      latency_p99: 'histogram_quantile(0.99, rate(grafana_http_request_duration_seconds_bucket[5m]))',
      weaviate_latency_p95: 'histogram_quantile(0.95, rate(weaviate_http_request_duration_seconds_bucket[5m]))'
    };

    const results = [];
    // Process queries sequentially to avoid overwhelming the server
    for (const [metric, query] of Object.entries(queries)) {
      try {
        const data = await this.queryRange(
          query,
          timeRange.start,
          timeRange.end,
          timeRange.step || '30s'
        );
        results.push({ metric, data });
        // Small delay between requests
        await new Promise(resolve => setTimeout(resolve, 100));
      } catch (error) {
        console.error(`Failed to fetch API metric ${metric}:`, error);
        results.push({ metric, data: [] });
      }
    }

    return results.reduce((acc, { metric, data }) => {
      acc[metric] = data;
      return acc;
    }, {} as Record<string, MetricSeries[]>);
  }
}

// Export a cached instance to share across components
export const prometheusClient = new PrometheusClient();

// React cache wrapper for common queries
export const getContainerMetrics = cache(prometheusClient.getContainerMetrics.bind(prometheusClient));
export const getRedisMetrics = cache(prometheusClient.getRedisMetrics.bind(prometheusClient));
export const getAPIMetrics = cache(prometheusClient.getAPIMetrics.bind(prometheusClient));