'use client';

import { useAnalyticsStore } from '@/stores/analytics-store';
import { browserLogger } from '@/lib/utils/browser-logger';

class CleanAnalyticsManager {
  private static instance: CleanAnalyticsManager;
  private ws: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000;
  private url: string | null = null;
  
  private constructor() {
    this.setupVisibilityListener();
  }
  
  static getInstance(): CleanAnalyticsManager {
    if (!CleanAnalyticsManager.instance) {
      CleanAnalyticsManager.instance = new CleanAnalyticsManager();
    }
    return CleanAnalyticsManager.instance;
  }
  
  connect(url: string) {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    
    this.url = url;
    const store = useAnalyticsStore.getState();
    store.setConnectionStatus('connecting');
    
    browserLogger.info('CleanAnalyticsManager: Connecting to WebSocket', { url });
    
    this.ws = new WebSocket(url);
    
    this.ws.onopen = () => {
      browserLogger.info('CleanAnalyticsManager: WebSocket connected');
      store.setConnectionStatus('connected');
      store.setWsConnection(this.ws);
      this.reconnectAttempts = 0;
    };
    
    this.ws.onmessage = (event) => {
      const store = useAnalyticsStore.getState();
      
      // Drop messages if tab is not visible (paused)
      if (store.isPaused) {
        browserLogger.debug('CleanAnalyticsManager: Dropping message - tab not visible');
        return;
      }
      
      this.handleMessage(event.data);
    };
    
    this.ws.onclose = (event) => {
      browserLogger.warn('CleanAnalyticsManager: WebSocket disconnected', { 
        code: event.code, 
        reason: event.reason 
      });
      store.setConnectionStatus('disconnected');
      store.setWsConnection(null);
      this.scheduleReconnect();
    };
    
    this.ws.onerror = (error) => {
      browserLogger.error('CleanAnalyticsManager: WebSocket error', error);
      store.setConnectionStatus('disconnected');
    };
  }
  
  private handleMessage(data: string) {
    try {
      const parsed = JSON.parse(data);
      const store = useAnalyticsStore.getState();
      
      if (parsed.type === 'analytics_update') {
        browserLogger.debug('CleanAnalyticsManager: Received analytics phase', { 
          phase: parsed.phase 
        });
        
        switch (parsed.phase) {
          case 'essential':
            // Phase 1: Essential data - merge with existing
            if (parsed.data.systemHealth) {
              const currentAnalytics = store.analytics;
              store.setAnalytics({
                ...currentAnalytics,
                systemHealth: {
                  ...currentAnalytics?.systemHealth,
                  ...parsed.data.systemHealth
                }
              });
            }
            if (parsed.data.stats) {
              store.setStats(parsed.data.stats);
            }
            break;
            
          case 'extended':
            // Phase 2: Extended system health - merge with existing
            if (parsed.data.systemHealth) {
              const currentAnalytics = store.analytics;
              const newSystemHealth = {
                ...currentAnalytics?.systemHealth,
                ...parsed.data.systemHealth
              };
              
              
              store.setAnalytics({
                ...currentAnalytics,
                systemHealth: newSystemHealth
              });
            }
            break;
            
          case 'detailed':
            // Phase 3: Detailed analytics and metrics
            if (parsed.data.analytics) {
              const currentAnalytics = store.analytics;
              store.setAnalytics({
                ...currentAnalytics,
                ...parsed.data.analytics
              });
            }
            if (parsed.data.service_metrics || parsed.data.redis_metrics || parsed.data.weaviate_metrics) {
              const newStats = {};
              if (parsed.data.service_metrics) {
                Object.assign(newStats, { service_metrics: parsed.data.service_metrics });
              }
              if (parsed.data.redis_metrics) {
                Object.assign(newStats, { redis_metrics: parsed.data.redis_metrics });
              }
              if (parsed.data.weaviate_metrics) {
                Object.assign(newStats, { weaviate_metrics: parsed.data.weaviate_metrics });
              }
              store.mergeStats(newStats);
            }
            break;
            
          case 'complete':
            browserLogger.info('CleanAnalyticsManager: Analytics load complete');
            break;
            
          default:
            browserLogger.warn('CleanAnalyticsManager: Unknown analytics phase', { 
              phase: parsed.phase 
            });
            break;
        }
      }
    } catch (error) {
      browserLogger.error('CleanAnalyticsManager: Failed to parse WebSocket message', error as Error);
    }
  }
  
  private setupVisibilityListener() {
    if (typeof document === 'undefined') return;
    
    document.addEventListener('visibilitychange', () => {
      const store = useAnalyticsStore.getState();
      
      if (document.hidden) {
        browserLogger.info('CleanAnalyticsManager: Tab hidden - pausing updates');
        store.setPaused(true);
      } else {
        browserLogger.info('CleanAnalyticsManager: Tab visible - resuming updates');
        store.setPaused(false);
        
        // Request fresh data when tab becomes visible again
        if (this.ws?.readyState === WebSocket.OPEN) {
          this.requestFreshData();
        }
      }
    });
  }
  
  private requestFreshData() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      browserLogger.debug('CleanAnalyticsManager: Requesting fresh data');
      this.ws.send(JSON.stringify({ 
        type: 'refresh_data',
        timestamp: Date.now()
      }));
    }
  }
  
  sendTimeRange(timeRange: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      browserLogger.debug('CleanAnalyticsManager: Sending time range update', { timeRange });
      this.ws.send(JSON.stringify({
        type: 'change_timerange',
        timeRange
      }));
    }
  }
  
  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      browserLogger.error('CleanAnalyticsManager: Max reconnection attempts reached');
      return;
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    
    const delay = Math.min(
      this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts),
      30000
    );
    
    browserLogger.info('CleanAnalyticsManager: Scheduling reconnection', { 
      delayMs: delay, 
      attempt: this.reconnectAttempts + 1 
    });
    
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      if (this.url) {
        this.connect(this.url);
      }
    }, delay);
  }
  
  disconnect() {
    browserLogger.info('CleanAnalyticsManager: Disconnecting WebSocket');
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    
    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
    
    const store = useAnalyticsStore.getState();
    store.setConnectionStatus('disconnected');
    store.setWsConnection(null);
  }
}

export default CleanAnalyticsManager;