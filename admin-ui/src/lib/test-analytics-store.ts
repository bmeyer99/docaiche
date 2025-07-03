/**
 * Test utility to verify analytics store functionality
 * This file can be removed after testing
 */

import { useAnalyticsStore } from '@/stores/analytics-store';

export function testAnalyticsStore() {
  console.log('=== Analytics Store Test ===');
  
  const store = useAnalyticsStore.getState();
  
  console.log('Initial state:', {
    analytics: store.analytics,
    stats: store.stats,
    connectionStatus: store.connectionStatus,
    isPaused: store.isPaused,
    timeRange: store.timeRange,
    lastUpdateTime: store.lastUpdateTime
  });
  
  // Test setting analytics data
  store.setAnalytics({
    systemHealth: {
      api_core: { status: 'healthy', message: 'All systems operational' },
      search_engine: { status: 'healthy', message: 'Search running normally' }
    },
    searchMetrics: {
      queriesByHour: [
        { count: 10, responseTime: 150 },
        { count: 15, responseTime: 120 }
      ],
      topQueries: [
        { query: 'react hooks', count: 25 },
        { query: 'typescript', count: 18 }
      ]
    }
  });
  
  // Test setting stats
  store.setStats({
    search_stats: {
      total_searches: 1547,
      avg_response_time_ms: 145,
      cache_hit_rate: 0.82
    },
    content_stats: {
      total_documents: 12450,
      workspaces: 8
    }
  });
  
  // Test connection status
  store.setConnectionStatus('connected');
  
  console.log('After setting test data:', {
    analytics: store.analytics,
    stats: store.stats,
    connectionStatus: store.connectionStatus,
    lastUpdateTime: store.lastUpdateTime
  });
  
  // Test pause functionality
  store.setPaused(true);
  console.log('Paused state:', store.isPaused);
  
  store.setPaused(false);
  console.log('Resumed state:', store.isPaused);
  
  // Test time range change
  store.setTimeRange('7d');
  console.log('Time range changed to:', store.timeRange);
  
  console.log('=== Analytics Store Test Complete ===');
}

// Export for manual testing in browser console
if (typeof window !== 'undefined') {
  (window as any).testAnalyticsStore = testAnalyticsStore;
}