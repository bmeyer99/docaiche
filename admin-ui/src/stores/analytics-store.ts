'use client';

import { create } from 'zustand';
import { subscribeWithSelector } from 'zustand/middleware';

export interface AnalyticsData {
  systemHealth?: any;
  searchMetrics?: any;
  contentMetrics?: any;
}

export interface StatsData {
  search_stats?: any;
  content_stats?: any;
  service_metrics?: any;
  redis_metrics?: any;
  weaviate_metrics?: any;
}

export interface AnalyticsStore {
  // Data states
  analytics: AnalyticsData | null;
  stats: StatsData | null;
  lastUpdateTime: number;
  
  // Connection states
  wsConnection: WebSocket | null;
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  isPaused: boolean;
  
  // Configuration
  timeRange: string;
  
  // Actions
  setAnalytics: (data: AnalyticsData | null) => void;
  setStats: (data: StatsData | null) => void;
  updateSystemHealth: (systemHealth: any) => void;
  mergeStats: (newStats: Partial<StatsData>) => void;
  setWsConnection: (ws: WebSocket | null) => void;
  setConnectionStatus: (status: 'connected' | 'disconnected' | 'connecting') => void;
  setPaused: (paused: boolean) => void;
  setTimeRange: (timeRange: string) => void;
  clearData: () => void;
}

export const useAnalyticsStore = create<AnalyticsStore>()(
  subscribeWithSelector((set, get) => ({
    // Initial state
    analytics: null,
    stats: null,
    lastUpdateTime: 0,
    wsConnection: null,
    connectionStatus: 'disconnected',
    isPaused: false,
    timeRange: '24h',
    
    // Actions
    setAnalytics: (analytics) => 
      set({ analytics, lastUpdateTime: Date.now() }),
    
    setStats: (stats) => 
      set({ stats, lastUpdateTime: Date.now() }),
    
    updateSystemHealth: (systemHealth) => 
      set((state) => ({
        analytics: {
          ...state.analytics,
          systemHealth
        },
        lastUpdateTime: Date.now()
      })),
    
    mergeStats: (newStats) => 
      set((state) => ({
        stats: {
          ...state.stats,
          ...newStats
        },
        lastUpdateTime: Date.now()
      })),
    
    setWsConnection: (wsConnection) => 
      set({ wsConnection }),
    
    setConnectionStatus: (connectionStatus) => 
      set({ connectionStatus }),
    
    setPaused: (isPaused) => 
      set({ isPaused }),
    
    setTimeRange: (timeRange) => 
      set({ timeRange }),
    
    clearData: () => 
      set({ 
        analytics: null, 
        stats: null, 
        lastUpdateTime: 0 
      }),
  }))
);