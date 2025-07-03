'use client';

import { useAnalyticsStore } from '@/stores/analytics-store';

class AnalyticsWebSocketManager {
  private static instance: AnalyticsWebSocketManager;
  private ws: WebSocket | null = null;
  private reconnectTimeout: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000;
  private url: string | null = null;
  
  private constructor() {
    this.setupVisibilityListener();
  }
  
  static getInstance(): AnalyticsWebSocketManager {
    if (!AnalyticsWebSocketManager.instance) {
      AnalyticsWebSocketManager.instance = new AnalyticsWebSocketManager();
    }
    return AnalyticsWebSocketManager.instance;
  }
  
  connect(url: string) {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    
    this.url = url;
    const store = useAnalyticsStore.getState();
    store.setConnectionStatus('connecting');
    
    console.log('[AnalyticsWebSocketManager] Connecting to:', url);
    
    this.ws = new WebSocket(url);
    
    this.ws.onopen = () => {
      console.log('[AnalyticsWebSocketManager] Connected');
      store.setConnectionStatus('connected');
      store.setWsConnection(this.ws);
      this.reconnectAttempts = 0;
      
      // Request fresh data immediately on connection
      this.requestFreshData();
      
      // Send current time range
      this.sendTimeRange(store.timeRange);
    };
    
    this.ws.onmessage = (event) => {
      const store = useAnalyticsStore.getState();
      
      // Drop messages if tab is not visible (paused)
      if (store.isPaused) {
        console.log('[AnalyticsWebSocketManager] Dropping message - tab not visible');
        return;
      }
      
      this.handleMessage(event.data);
    };
    
    this.ws.onclose = (event) => {
      console.log('[AnalyticsWebSocketManager] Disconnected:', event.code, event.reason);
      store.setConnectionStatus('disconnected');
      store.setWsConnection(null);
      this.scheduleReconnect();
    };
    
    this.ws.onerror = (error) => {
      console.error('[AnalyticsWebSocketManager] Error:', error);
      store.setConnectionStatus('disconnected');
    };
  }
  
  private handleMessage(data: string) {
    try {
      const parsed = JSON.parse(data);
      const store = useAnalyticsStore.getState();
      
      if (parsed.type === 'analytics_update') {
        // Handle progressive data based on section
        switch (parsed.section) {
          case 'health':
          case 'detailed_health':
          case 'search_ai_health':
          case 'monitoring_health':
            if (parsed.data.systemHealth) {
              store.updateSystemHealth(parsed.data.systemHealth);
            }
            break;
            
          case 'api_endpoint':
            if (parsed.data.systemHealth) {
              // Merge individual API endpoint results into existing system health
              const currentAnalytics = store.analytics;
              store.setAnalytics({
                ...currentAnalytics,
                systemHealth: {
                  ...currentAnalytics?.systemHealth,
                  ...parsed.data.systemHealth
                }
              });
            }
            break;
            
          case 'basic_stats':
            if (parsed.data.stats) {
              store.setStats(parsed.data.stats);
            }
            break;
            
          case 'detailed_analytics':
            if (parsed.data.analytics) {
              const currentAnalytics = store.analytics;
              store.setAnalytics({
                ...currentAnalytics,
                ...parsed.data.analytics
              });
            }
            break;
            
          case 'service_metrics':
            if (parsed.data.service_metrics) {
              store.mergeStats({ service_metrics: parsed.data.service_metrics });
            }
            break;
            
          case 'stats_update':
            if (parsed.data.stats) {
              store.mergeStats(parsed.data.stats);
            }
            break;
            
          case 'health_update':
            if (parsed.data.systemHealth) {
              store.updateSystemHealth(parsed.data.systemHealth);
            }
            break;
            
          // Legacy support for non-progressive endpoints
          default:
            if (!parsed.section) {
              if (parsed.data.analytics) {
                store.setAnalytics(parsed.data.analytics);
              }
              if (parsed.data.stats) {
                store.setStats(parsed.data.stats);
              }
            }
            break;
        }
      }
    } catch (error) {
      console.error('[AnalyticsWebSocketManager] Failed to parse message:', error);
    }
  }
  
  private setupVisibilityListener() {
    if (typeof document === 'undefined') return;
    
    document.addEventListener('visibilitychange', () => {
      const store = useAnalyticsStore.getState();
      
      if (document.hidden) {
        // Pause updates - messages will be dropped
        console.log('[AnalyticsWebSocketManager] Tab hidden - pausing updates');
        store.setPaused(true);
      } else {
        // Resume updates and request fresh data
        console.log('[AnalyticsWebSocketManager] Tab visible - resuming updates');
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
      console.log('[AnalyticsWebSocketManager] Requesting fresh data');
      this.ws.send(JSON.stringify({ 
        type: 'refresh_data',
        timestamp: Date.now()
      }));
    }
  }
  
  sendTimeRange(timeRange: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[AnalyticsWebSocketManager] Sending time range:', timeRange);
      this.ws.send(JSON.stringify({
        type: 'change_timerange',
        timeRange
      }));
    }
  }
  
  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.log('[AnalyticsWebSocketManager] Max reconnection attempts reached');
      return;
    }
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
    }
    
    const delay = Math.min(
      this.reconnectInterval * Math.pow(1.5, this.reconnectAttempts),
      30000
    );
    
    console.log(`[AnalyticsWebSocketManager] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.reconnectAttempts++;
      if (this.url) {
        this.connect(this.url);
      }
    }, delay);
  }
  
  disconnect() {
    console.log('[AnalyticsWebSocketManager] Disconnecting');
    
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

export default AnalyticsWebSocketManager;