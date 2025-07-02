'use client';

import { useEffect, useRef, useState, useCallback } from 'react';

interface WebSocketOptions {
  reconnect?: boolean;
  reconnectInterval?: number;
  reconnectAttempts?: number;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  onMessage?: (data: any) => void;
}

interface WebSocketState {
  isConnected: boolean;
  lastMessage: any;
  error: Error | null;
}

export function useWebSocket(
  url: string | null,
  options: WebSocketOptions = {}
) {
  const {
    reconnect = true,
    reconnectInterval = 3000,
    reconnectAttempts = 5,
    onOpen,
    onClose,
    onError,
    onMessage,
  } = options;

  const [state, setState] = useState<WebSocketState>({
    isConnected: false,
    lastMessage: null,
    error: null,
  });

  const ws = useRef<WebSocket | null>(null);
  const reconnectCount = useRef(0);
  const reconnectTimeoutId = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnect = useRef(reconnect);

  const connect = useCallback(() => {
    // Prevent multiple connections
    if (!url || ws.current) return;

    try {
      console.log('Creating new WebSocket connection to:', url);
      ws.current = new WebSocket(url);

      ws.current.onopen = (event) => {
        console.log('WebSocket connected:', url);
        setState(prev => ({ ...prev, isConnected: true, error: null }));
        reconnectCount.current = 0;
        onOpen?.(event);
      };

      ws.current.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        setState(prev => ({ ...prev, isConnected: false }));
        onClose?.(event);

        // Clear any existing reconnect timeout
        if (reconnectTimeoutId.current) {
          clearTimeout(reconnectTimeoutId.current);
          reconnectTimeoutId.current = null;
        }

        // Attempt to reconnect if enabled
        if (
          shouldReconnect.current &&
          reconnect &&
          reconnectCount.current < reconnectAttempts &&
          !event.wasClean &&
          event.code !== 1000 // Normal closure
        ) {
          const backoffDelay = Math.min(reconnectInterval * Math.pow(2, reconnectCount.current), 30000); // Exponential backoff, max 30s
          reconnectTimeoutId.current = setTimeout(() => {
            console.log(`Attempting to reconnect... (${reconnectCount.current + 1}/${reconnectAttempts}) after ${backoffDelay}ms`);
            reconnectCount.current++;
            connect();
          }, backoffDelay);
        } else if (reconnectCount.current >= reconnectAttempts) {
          console.log('Max reconnection attempts reached, giving up');
          setState(prev => ({ 
            ...prev, 
            error: new Error(`Failed to connect after ${reconnectAttempts} attempts`) 
          }));
        }
      };

      ws.current.onerror = (event) => {
        console.error('WebSocket error:', event);
        const error = new Error('WebSocket connection error');
        setState(prev => ({ ...prev, error }));
        onError?.(event);
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setState(prev => ({ ...prev, lastMessage: data }));
          onMessage?.(data);
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setState(prev => ({ 
        ...prev, 
        error: error instanceof Error ? error : new Error('Failed to connect') 
      }));
    }
  }, [url, reconnect, reconnectInterval, reconnectAttempts, onOpen, onClose, onError, onMessage]);

  const disconnect = useCallback(() => {
    console.log('Disconnecting WebSocket');
    shouldReconnect.current = false;
    reconnectCount.current = 0; // Reset reconnect count on manual disconnect
    
    if (reconnectTimeoutId.current) {
      clearTimeout(reconnectTimeoutId.current);
      reconnectTimeoutId.current = null;
    }

    if (ws.current && ws.current.readyState !== WebSocket.CLOSED) {
      ws.current.close(1000, 'Component unmounting');
    }
    ws.current = null;
  }, []);

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(typeof message === 'string' ? message : JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected');
    }
  }, []);

  // Auto-connect on mount if URL is provided
  useEffect(() => {
    if (url && !ws.current) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [url, connect, disconnect]); // Added connect and disconnect dependencies

  return {
    ...state,
    connect,
    disconnect,
    sendMessage,
  };
}

// Specialized hook for analytics WebSocket
export function useAnalyticsWebSocket(timeRange: string = '24h', enabled: boolean = true) {
  const [analytics, setAnalytics] = useState<any>(null);
  const [stats, setStats] = useState<any>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!enabled || typeof window === 'undefined') {
      return;
    }

    // Import dynamically to avoid SSR issues
    import('../websocket-manager').then(({ default: WebSocketManager }) => {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // Use the new progressive endpoint
      const url = `${wsProtocol}//${window.location.host}/ws/analytics/progressive`;
      
      const manager = WebSocketManager.getInstance(url);

      // Set up event handlers
      const unsubscribeMessage = manager.onMessage((data) => {
        if (data.type === 'analytics_update') {
          // Handle progressive data based on section
          if (data.section === 'health' && data.data.systemHealth) {
            setAnalytics((prev: any) => ({ ...prev, systemHealth: data.data.systemHealth }));
          } else if (data.section === 'basic_stats' && data.data.stats) {
            setStats(data.data.stats);
          } else if (data.section === 'detailed_analytics' && data.data.analytics) {
            setAnalytics((prev: any) => ({ ...prev, ...data.data.analytics }));
          } else if (data.section === 'service_metrics' && data.data.service_metrics) {
            setStats((prev: any) => ({ ...prev, service_metrics: data.data.service_metrics }));
          } else if (data.section === 'stats_update' && data.data.stats) {
            setStats((prev: any) => ({ ...prev, ...data.data.stats }));
          } else if (data.section === 'health_update' && data.data.systemHealth) {
            setAnalytics((prev: any) => ({ ...prev, systemHealth: data.data.systemHealth }));
          }
          // Legacy support for non-progressive endpoints
          else if (!data.section) {
            setAnalytics(data.data.analytics);
            setStats(data.data.stats);
          }
        }
      });

      const unsubscribeConnect = manager.onConnect(() => {
        console.log('Analytics WebSocket connected');
        setIsConnected(true);
        setError(null);
        
        // Send initial time range with a small delay to ensure connection is ready
        setTimeout(() => {
          manager.send({
            type: 'change_timerange',
            timeRange,
          });
        }, 100);
      });

      const unsubscribeError = manager.onError((event) => {
        console.error('Analytics WebSocket error:', event);
        setError(new Error('WebSocket connection error'));
        setIsConnected(false);
      });

      // Connect
      manager.connect();

      // Cleanup function
      return () => {
        unsubscribeMessage();
        unsubscribeConnect();
        unsubscribeError();
        // Note: We don't disconnect here because other components might be using it
      };
    });
  }, [enabled, timeRange]); // Added timeRange dependency

  // Handle time range changes
  useEffect(() => {
    if (isConnected && typeof window !== 'undefined') {
      import('../websocket-manager').then(({ default: WebSocketManager }) => {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${wsProtocol}//${window.location.host}/ws/analytics/progressive`;
        const manager = WebSocketManager.getInstance(url);
        
        manager.send({
          type: 'change_timerange',
          timeRange,
        });
      });
    }
  }, [timeRange, isConnected]);

  return {
    analytics,
    stats,
    isConnected,
    error,
  };
}

// Specialized hook for health monitoring WebSocket
export function useHealthWebSocket() {
  const [health, setHealth] = useState<any>(null);
  
  // Use relative path that will be proxied by Next.js
  const [url, setUrl] = useState<string | null>(null);
  
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      setUrl(`${wsProtocol}//${window.location.host}/ws/health`);
    }
  }, []);

  const { isConnected, error } = useWebSocket(url, {
    onMessage: (data) => {
      if (data.type === 'health_update') {
        setHealth(data.data);
      }
    },
    onOpen: () => {
      console.log('Health WebSocket connected');
    },
    onError: (error) => {
      console.error('Health WebSocket error:', error);
    },
  });

  return {
    health,
    isConnected,
    error,
  };
}