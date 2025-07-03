'use client';

/**
 * WebSocket hooks for Search Configuration real-time updates
 */

import { useEffect, useCallback, useRef, useState, useMemo } from 'react';
import { useWebSocket } from '@/lib/hooks/use-websocket';
import { 
  WebSocketMessage, 
  HealthUpdate, 
  MetricsUpdate,
  SearchConfiguration 
} from '../types';

interface UseSearchConfigWebSocketOptions {
  onConfigUpdate?: (config: Partial<SearchConfiguration>) => void;
  onHealthUpdate?: (update: HealthUpdate) => void;
  onMetricsUpdate?: (update: MetricsUpdate) => void;
  onAlert?: (alert: any) => void;
  autoConnect?: boolean;
}

export function useSearchConfigWebSocket(options: UseSearchConfigWebSocketOptions = {}) {
  const {
    onConfigUpdate,
    onHealthUpdate,
    onMetricsUpdate,
    onAlert,
    autoConnect = true
  } = options;

  const handleMessage = useCallback((data: any) => {
    try {
      const message: WebSocketMessage = data;
      
      switch (message.type) {
        case 'config_update':
          onConfigUpdate?.(message.payload);
          break;
          
        case 'health_update':
          onHealthUpdate?.(message.payload);
          break;
          
        case 'metrics_update':
          onMetricsUpdate?.(message.payload);
          break;
          
        case 'alert':
          onAlert?.(message.payload);
          break;
          
        default:
          console.warn('Unknown WebSocket message type:', message.type);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }, [onConfigUpdate, onHealthUpdate, onMetricsUpdate, onAlert]);
  
  const wsState = useWebSocket(
    '/ws/admin/search',
    {
      reconnect: autoConnect,
      reconnectAttempts: 5,
      reconnectInterval: 3000,
      onMessage: handleMessage
    }
  );
  
  const { isConnected, connect, disconnect, sendMessage } = wsState;

  // Subscribe to specific updates
  const subscribe = useCallback((topics: string[]) => {
    sendMessage({
      type: 'subscribe',
      topics
    });
  }, [sendMessage]);

  // Unsubscribe from updates
  const unsubscribe = useCallback((topics: string[]) => {
    sendMessage({
      type: 'unsubscribe',
      topics
    });
  }, [sendMessage]);

  return {
    isConnected,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    handleMessage
  };
}

/**
 * Hook for real-time queue metrics
 */
export function useQueueMetrics() {
  const metricsRef = useRef<MetricsUpdate[]>([]);
  const [currentDepth, setCurrentDepth] = useState<number>(0);
  const [processingRate, setProcessingRate] = useState<number>(0);

  const { subscribe, unsubscribe } = useSearchConfigWebSocket({
    onMetricsUpdate: (update) => {
      if (update.metric === 'queue_depth') {
        setCurrentDepth(update.value);
        metricsRef.current.push(update);
        
        // Keep only last 100 metrics
        if (metricsRef.current.length > 100) {
          metricsRef.current = metricsRef.current.slice(-100);
        }
      } else if (update.metric === 'processing_rate') {
        setProcessingRate(update.value);
      }
    }
  });

  useEffect(() => {
    subscribe(['queue_metrics']);
    return () => unsubscribe(['queue_metrics']);
  }, [subscribe, unsubscribe]);

  return {
    currentDepth,
    processingRate,
    history: metricsRef.current
  };
}

/**
 * Hook for system health monitoring
 */
export function useSystemHealth() {
  const [healthStatus, setHealthStatus] = useState<Record<string, HealthUpdate>>({});

  const { subscribe, unsubscribe, isConnected } = useSearchConfigWebSocket({
    onHealthUpdate: (update) => {
      setHealthStatus(prev => ({
        ...prev,
        [update.component]: update
      }));
    }
  });

  useEffect(() => {
    if (isConnected) {
      subscribe(['health_updates']);
    }
    return () => {
      if (isConnected) {
        unsubscribe(['health_updates']);
      }
    };
  }, [subscribe, unsubscribe, isConnected]);

  const overallHealth = useMemo(() => {
    const statuses = Object.values(healthStatus);
    if (statuses.length === 0) return 'unknown';
    
    if (statuses.some(s => s.status === 'unhealthy')) return 'unhealthy';
    if (statuses.some(s => s.status === 'degraded')) return 'degraded';
    return 'healthy';
  }, [healthStatus]);

  return {
    healthStatus,
    overallHealth,
    isConnected
  };
}

/**
 * Hook for configuration change notifications
 */
export function useConfigChangeNotifications() {
  const [pendingChanges, setPendingChanges] = useState<Partial<SearchConfiguration> | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);

  const { subscribe, unsubscribe } = useSearchConfigWebSocket({
    onConfigUpdate: (config) => {
      setPendingChanges(config);
      setLastUpdate(new Date().toISOString());
    }
  });

  useEffect(() => {
    subscribe(['config_changes']);
    return () => unsubscribe(['config_changes']);
  }, [subscribe, unsubscribe]);

  const acknowledgeChanges = useCallback(() => {
    setPendingChanges(null);
  }, []);

  return {
    pendingChanges,
    lastUpdate,
    acknowledgeChanges
  };
}