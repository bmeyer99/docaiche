/**
 * Realtime State Slice
 * Manages WebSocket connections and real-time state updates
 */

import { StateCreator } from 'zustand';
import { RealtimeMetrics } from '../types';

export interface RealtimeState {
  realtime: {
    connected: boolean;
    reconnecting: boolean;
    lastHeartbeat: Date | null;
    connectionAttempts: number;
    maxReconnectAttempts: number;
    reconnectDelay: number;
    wsInstance: WebSocket | null;
  };
}

export interface RealtimeActions {
  // Connection actions
  setRealtimeConnected: (connected: boolean) => void;
  setReconnecting: (reconnecting: boolean) => void;
  updateLastHeartbeat: () => void;
  incrementConnectionAttempts: () => void;
  resetConnectionAttempts: () => void;
  setWebSocketInstance: (ws: WebSocket | null) => void;
  
  // Metrics actions (real-time updates)
  updateRealtimeMetrics: (metrics: Partial<RealtimeMetrics>) => void;
  
  // Connection management
  initializeConnection: () => Promise<void>;
  disconnectWebSocket: () => void;
  reconnectWebSocket: () => Promise<void>;
  
  // Computed selectors
  getConnectionStatus: () => 'connected' | 'disconnected' | 'reconnecting' | 'failed';
  isConnected: () => boolean;
  getTimeSinceLastHeartbeat: () => number | null;
  shouldReconnect: () => boolean;
}

export type RealtimeSlice = RealtimeState & RealtimeActions;

// Default state
const defaultRealtimeState: RealtimeState['realtime'] = {
  connected: false,
  reconnecting: false,
  lastHeartbeat: null,
  connectionAttempts: 0,
  maxReconnectAttempts: 5,
  reconnectDelay: 5000, // 5 seconds
  wsInstance: null,
};

import type { ImmerStateCreator } from '../store-types';

export const createRealtimeSlice: ImmerStateCreator<RealtimeSlice> = (set, get) => ({
  realtime: defaultRealtimeState,

  // Connection actions
  setRealtimeConnected: (connected) =>
    set((state) => {
      state.realtime.connected = connected;
      if (connected) {
        state.realtime.reconnecting = false;
        state.realtime.connectionAttempts = 0;
        state.realtime.lastHeartbeat = new Date();
      }
    }),

  setReconnecting: (reconnecting) =>
    set((state) => {
      state.realtime.reconnecting = reconnecting;
    }),

  updateLastHeartbeat: () =>
    set((state) => {
      state.realtime.lastHeartbeat = new Date();
    }),

  incrementConnectionAttempts: () =>
    set((state) => {
      state.realtime.connectionAttempts += 1;
    }),

  resetConnectionAttempts: () =>
    set((state) => {
      state.realtime.connectionAttempts = 0;
    }),

  setWebSocketInstance: (ws) =>
    set((state) => {
      state.realtime.wsInstance = ws;
    }),

  // Metrics actions (real-time updates)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  updateRealtimeMetrics: (_metrics) =>
    set((state) => {
      // This would update the system metrics in real-time
      // For now, we'll store this in the realtime slice, but in practice
      // it might update the system slice directly
      Object.assign(state.realtime, { lastMetricsUpdate: new Date() });
    }),

  // Connection management
  initializeConnection: async () => {
    const state = get();
    
    if (state.realtime.connected || state.realtime.reconnecting) {
      return; // Already connected or trying to connect
    }

    set((state) => {
      state.realtime.reconnecting = true;
    });

    try {
      // Get WebSocket URL from environment or construct it
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsHost = window.location.host;
      const wsUrl = `${wsProtocol}//${wsHost}/api/ws`;

      const ws = new WebSocket(wsUrl);

      // Set up event handlers
      ws.onopen = () => {
        console.log('WebSocket connected');
        get().setRealtimeConnected(true);
        get().setWebSocketInstance(ws);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // Handle different message types
          switch (data.type) {
            case 'heartbeat':
              get().updateLastHeartbeat();
              break;
            case 'metrics':
              get().updateRealtimeMetrics(data.payload);
              break;
            case 'system_health':
              // Would update system health in system slice
              break;
            case 'logs':
              // Would update logs in system slice
              break;
            default:
              console.log('Unknown WebSocket message type:', data.type);
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason);
        get().setRealtimeConnected(false);
        get().setWebSocketInstance(null);
        
        // Attempt to reconnect if it wasn't a manual disconnect
        if (event.code !== 1000 && get().shouldReconnect()) {
          setTimeout(() => {
            get().reconnectWebSocket();
          }, state.realtime.reconnectDelay);
        }
      };

    } catch (error) {
      console.error('Failed to initialize WebSocket connection:', error);
      set((state) => {
        state.realtime.reconnecting = false;
      });
    }
  },

  disconnectWebSocket: () => {
    const state = get();
    
    if (state.realtime.wsInstance) {
      state.realtime.wsInstance.close(1000, 'Manual disconnect');
    }
    
    set((state) => {
      state.realtime.connected = false;
      state.realtime.reconnecting = false;
      state.realtime.wsInstance = null;
    });
  },

  reconnectWebSocket: async () => {
    const state = get();
    
    if (state.realtime.connectionAttempts >= state.realtime.maxReconnectAttempts) {
      console.log('Max reconnection attempts reached');
      set((state) => {
        state.realtime.reconnecting = false;
      });
      return;
    }

    get().incrementConnectionAttempts();
    await get().initializeConnection();
  },

  // Computed selectors
  getConnectionStatus: () => {
    const state = get();
    
    if (state.realtime.connected) {
      return 'connected';
    } else if (state.realtime.reconnecting) {
      return 'reconnecting';
    } else if (state.realtime.connectionAttempts >= state.realtime.maxReconnectAttempts) {
      return 'failed';
    } else {
      return 'disconnected';
    }
  },

  isConnected: () => {
    const state = get();
    return state.realtime.connected;
  },

  getTimeSinceLastHeartbeat: () => {
    const state = get();
    
    if (!state.realtime.lastHeartbeat) {
      return null;
    }
    
    return Date.now() - state.realtime.lastHeartbeat.getTime();
  },

  shouldReconnect: () => {
    const state = get();
    return state.realtime.connectionAttempts < state.realtime.maxReconnectAttempts;
  },
});