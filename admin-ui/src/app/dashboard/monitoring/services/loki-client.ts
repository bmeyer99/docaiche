import { cache } from 'react';

export interface LokiQuery {
  query: string;
  start?: number;
  end?: number;
  limit?: number;
  direction?: 'forward' | 'backward';
}

export interface LokiStream {
  stream: Record<string, string>;
  values: [string, string][];
}

export interface LokiResponse {
  status: string;
  data: {
    resultType: string;
    result: LokiStream[];
    stats?: Record<string, any>;
  };
}

export interface LogEntry {
  timestamp: number;
  message: string;
  labels: Record<string, string>;
  level?: string;
  service?: string;
  container?: string;
}

export interface LogQueryOptions {
  start: number;
  end: number;
  query: string;
  limit?: number;
  filters?: {
    level?: string[];
    service?: string[];
    container?: string[];
  };
}

class LokiClient {
  private baseUrl: string;

  constructor() {
    // Access Loki through the proxy
    this.baseUrl = '/loki';
  }

  /**
   * Query logs from Loki
   */
  async queryLogs(options: LogQueryOptions): Promise<LogEntry[]> {
    const { start, end, query, limit = 1000, filters } = options;

    // Build the LogQL query with filters
    let logQL = query || '{job=~".+"}';
    
    if (filters) {
      const filterClauses: string[] = [];
      
      if (filters.level?.length) {
        filterClauses.push(`level=~"${filters.level.join('|')}"`);
      }
      
      if (filters.service?.length) {
        filterClauses.push(`service=~"${filters.service.join('|')}"`);
      }
      
      if (filters.container?.length) {
        filterClauses.push(`container=~"${filters.container.join('|')}"`);
      }
      
      if (filterClauses.length > 0) {
        logQL = `{${filterClauses.join(', ')}}`;
      }
    }

    const params = new URLSearchParams({
      query: logQL,
      start: (start * 1000000).toString(), // Convert to nanoseconds
      end: (end * 1000000).toString(),
      limit: limit.toString(),
      direction: 'backward'
    });

    const response = await fetch(`${this.baseUrl}/loki/api/v1/query_range?${params}`);
    
    if (!response.ok) {
      throw new Error(`Loki query failed: ${response.statusText}`);
    }

    const data: LokiResponse = await response.json();
    
    // Transform Loki data to our format
    const logs: LogEntry[] = [];
    
    data.data.result.forEach(stream => {
      stream.values.forEach(([timestamp, message]) => {
        logs.push({
          timestamp: parseInt(timestamp) / 1000000, // Convert from nanoseconds to milliseconds
          message,
          labels: stream.stream,
          level: stream.stream.level || this.extractLogLevel(message),
          service: stream.stream.service || stream.stream.job,
          container: stream.stream.container_name || stream.stream.container
        });
      });
    });

    // Sort by timestamp descending
    return logs.sort((a, b) => b.timestamp - a.timestamp);
  }

  /**
   * Get logs for a specific time window around an event
   */
  async getLogsAroundTime(
    timestamp: number,
    windowMs: number = 60000,
    filters?: LogQueryOptions['filters']
  ): Promise<LogEntry[]> {
    const start = timestamp - windowMs / 2;
    const end = timestamp + windowMs / 2;

    return this.queryLogs({
      start,
      end,
      query: '{job=~".+"}',
      filters,
      limit: 500
    });
  }

  /**
   * Get available log labels
   */
  async getLabels(): Promise<string[]> {
    const response = await fetch(`${this.baseUrl}/loki/api/v1/labels`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch labels: ${response.statusText}`);
    }

    const data = await response.json();
    return data.data;
  }

  /**
   * Get values for a specific label
   */
  async getLabelValues(label: string): Promise<string[]> {
    const response = await fetch(`${this.baseUrl}/loki/api/v1/label/${label}/values`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch label values: ${response.statusText}`);
    }

    const data = await response.json();
    return data.data;
  }

  /**
   * Search logs by pattern
   */
  async searchLogs(
    pattern: string,
    timeRange: { start: number; end: number },
    options?: {
      caseSensitive?: boolean;
      regex?: boolean;
      limit?: number;
    }
  ): Promise<LogEntry[]> {
    const { caseSensitive = false, regex = false, limit = 1000 } = options || {};
    
    // Build the search query
    let query = '{job=~".+"}';
    
    if (regex) {
      query += ` |~ "${pattern}"`;
    } else {
      // Escape special regex characters for literal search
      const escaped = pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      query += caseSensitive ? ` |~ "${escaped}"` : ` |~ "(?i)${escaped}"`;
    }

    return this.queryLogs({
      start: timeRange.start,
      end: timeRange.end,
      query,
      limit
    });
  }

  /**
   * Get log statistics for a time range
   */
  async getLogStats(timeRange: { start: number; end: number }) {
    // Query to count logs by level
    const levelQuery = 'sum by (level) (count_over_time({job=~".+"}[1m]))';
    
    // Query to count logs by service
    const serviceQuery = 'sum by (service) (count_over_time({job=~".+"}[1m]))';

    const params = new URLSearchParams({
      start: timeRange.start.toString(),
      end: timeRange.end.toString(),
      step: '60'
    });

    const [levelStats, serviceStats] = await Promise.all([
      fetch(`${this.baseUrl}/loki/api/v1/query_range?query=${encodeURIComponent(levelQuery)}&${params}`),
      fetch(`${this.baseUrl}/loki/api/v1/query_range?query=${encodeURIComponent(serviceQuery)}&${params}`)
    ]);

    if (!levelStats.ok || !serviceStats.ok) {
      throw new Error('Failed to fetch log statistics');
    }

    const levelData = await levelStats.json();
    const serviceData = await serviceStats.json();

    return {
      byLevel: levelData.data.result,
      byService: serviceData.data.result
    };
  }

  /**
   * Extract log level from message
   */
  private extractLogLevel(message: string): string {
    const patterns = [
      /\b(ERROR|ERR)\b/i,
      /\b(WARN|WARNING)\b/i,
      /\b(INFO)\b/i,
      /\b(DEBUG)\b/i,
      /\b(TRACE)\b/i,
      /\b(FATAL|CRITICAL)\b/i
    ];

    const levels = ['error', 'warn', 'info', 'debug', 'trace', 'fatal'];

    for (let i = 0; i < patterns.length; i++) {
      if (patterns[i].test(message)) {
        return levels[i];
      }
    }

    return 'info'; // Default level
  }

  /**
   * Get error logs for troubleshooting
   */
  async getErrorLogs(timeRange: { start: number; end: number }, service?: string) {
    const filters: LogQueryOptions['filters'] = {
      level: ['error', 'fatal', 'critical']
    };

    if (service) {
      filters.service = [service];
    }

    return this.queryLogs({
      ...timeRange,
      query: '{job=~".+"}',
      filters,
      limit: 500
    });
  }
}

// Export a cached instance to share across components
export const lokiClient = new LokiClient();

// React cache wrapper for common queries
export const getLogsAroundTime = cache(lokiClient.getLogsAroundTime.bind(lokiClient));
export const getErrorLogs = cache(lokiClient.getErrorLogs.bind(lokiClient));
export const getLogStats = cache(lokiClient.getLogStats.bind(lokiClient));