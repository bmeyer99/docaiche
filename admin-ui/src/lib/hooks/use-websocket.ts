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
    if (!url || ws.current?.readyState === WebSocket.OPEN) return;

    try {
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

        // Attempt to reconnect if enabled
        if (
          shouldReconnect.current &&
          reconnect &&
          reconnectCount.current < reconnectAttempts &&
          !event.wasClean
        ) {
          reconnectTimeoutId.current = setTimeout(() => {
            console.log(`Attempting to reconnect... (${reconnectCount.current + 1}/${reconnectAttempts})`);
            reconnectCount.current++;
            connect();
          }, reconnectInterval);
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
    shouldReconnect.current = false;
    reconnectCount.current = 0; // Reset reconnect count on manual disconnect
    
    if (reconnectTimeoutId.current) {
      clearTimeout(reconnectTimeoutId.current);
      reconnectTimeoutId.current = null;
    }

    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
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
    if (url) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [url, connect, disconnect]);

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
  
  // Use relative path that will be proxied by Next.js
  const [url, setUrl] = useState<string | null>(null);
  
  useEffect(() => {
    if (typeof window !== 'undefined' && enabled) {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      setUrl(`${wsProtocol}//${window.location.host}/ws/analytics`);
    } else if (!enabled) {
      setUrl(null); // Don't connect if not enabled
    }
  }, [enabled]);

  const { isConnected, error, sendMessage } = useWebSocket(url, {
    onMessage: (data) => {
      if (data.type === 'analytics_update') {
        setAnalytics(data.data.analytics);
        setStats(data.data.stats);
      }
    },
    onOpen: () => {
      console.log('Analytics WebSocket connected');
    },
    onError: (error) => {
      console.error('Analytics WebSocket error:', error);
    },
  });

  // Send time range change when it updates
  useEffect(() => {
    if (isConnected) {
      sendMessage({
        type: 'change_timerange',
        timeRange,
      });
    }
  }, [timeRange, isConnected, sendMessage]);

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