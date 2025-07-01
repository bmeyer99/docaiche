/**
 * System State Slice
 * Manages system health, metrics, and logs
 */

import { StateCreator } from 'zustand';
import { SystemHealth, RealtimeMetrics, LogEntry } from '../types';

export interface SystemState {
  system: {
    health: SystemHealth;
    metrics: RealtimeMetrics;
    logs: LogEntry[];
    loading: boolean;
    error: string | null;
  };
}

export interface SystemActions {
  // Health actions
  updateSystemHealth: (health: Partial<SystemHealth>) => void;
  setServiceHealth: (service: keyof SystemHealth['services'], status: SystemHealth['services'][keyof SystemHealth['services']]) => void;
  
  // Metrics actions
  updateMetrics: (metrics: Partial<RealtimeMetrics>) => void;
  updateSystemLoad: (load: Partial<RealtimeMetrics['systemLoad']>) => void;
  updateApiMetrics: (metrics: Partial<RealtimeMetrics['apiMetrics']>) => void;
  setActiveConnections: (count: number) => void;
  
  // Logs actions
  addLogEntry: (entry: LogEntry) => void;
  addLogEntries: (entries: LogEntry[]) => void;
  clearLogs: () => void;
  setMaxLogEntries: (max: number) => void;
  
  // Loading and error states
  setSystemLoading: (loading: boolean) => void;
  setSystemError: (error: string | null) => void;
  
  // Computed selectors
  getHealthyServices: () => string[];
  getUnhealthyServices: () => string[];
  getOverallHealthStatus: () => 'healthy' | 'degraded' | 'unhealthy';
  getRecentLogs: (count?: number) => LogEntry[];
  getLogsByService: (service: string) => LogEntry[];
  getLogsByLevel: (level: LogEntry['level']) => LogEntry[];
}

export type SystemSlice = SystemState & SystemActions;

// Default state
const defaultSystemHealth: SystemHealth = {
  status: 'healthy',
  services: {
    api: { status: 'healthy' },
    database: { status: 'healthy' },
    redis: { status: 'healthy' },
    anythingllm: { status: 'healthy' },
    monitoring: { status: 'healthy' },
  },
  lastCheck: new Date(),
};

const defaultRealtimeMetrics: RealtimeMetrics = {
  systemLoad: {
    cpu: 0,
    memory: 0,
    disk: 0,
  },
  apiMetrics: {
    requestsPerSecond: 0,
    averageResponseTime: 0,
    errorRate: 0,
  },
  activeConnections: 0,
  lastUpdate: new Date(),
};

const defaultSystemState: SystemState['system'] = {
  health: defaultSystemHealth,
  metrics: defaultRealtimeMetrics,
  logs: [],
  loading: false,
  error: null,
};

// Configuration
const MAX_LOG_ENTRIES = 1000; // Keep last 1000 log entries

import type { ImmerStateCreator } from '../store-types';

export const createSystemSlice: ImmerStateCreator<SystemSlice> = (set, get) => ({
  system: defaultSystemState,

  // Health actions
  updateSystemHealth: (health) =>
    set((state) => {
      Object.assign(state.system.health, health);
      state.system.health.lastCheck = new Date();
    }),

  setServiceHealth: (service, status) =>
    set((state) => {
      state.system.health.services[service] = status;
      state.system.health.lastCheck = new Date();
      
      // Update overall health status based on service statuses
      const services = Object.values(state.system.health.services);
      const unhealthyCount = services.filter((s: any) => s.status === 'unhealthy').length;
      const degradedCount = services.filter((s: any) => s.status === 'degraded').length;
      
      if (unhealthyCount > 0) {
        state.system.health.status = 'unhealthy';
      } else if (degradedCount > 0) {
        state.system.health.status = 'degraded';
      } else {
        state.system.health.status = 'healthy';
      }
    }),

  // Metrics actions
  updateMetrics: (metrics) =>
    set((state) => {
      Object.assign(state.system.metrics, metrics);
      state.system.metrics.lastUpdate = new Date();
    }),

  updateSystemLoad: (load) =>
    set((state) => {
      Object.assign(state.system.metrics.systemLoad, load);
      state.system.metrics.lastUpdate = new Date();
    }),

  updateApiMetrics: (metrics) =>
    set((state) => {
      Object.assign(state.system.metrics.apiMetrics, metrics);
      state.system.metrics.lastUpdate = new Date();
    }),

  setActiveConnections: (count) =>
    set((state) => {
      state.system.metrics.activeConnections = count;
      state.system.metrics.lastUpdate = new Date();
    }),

  // Logs actions
  addLogEntry: (entry) =>
    set((state) => {
      state.system.logs.unshift(entry); // Add to beginning for reverse chronological order
      
      // Trim logs if exceeding max entries
      if (state.system.logs.length > MAX_LOG_ENTRIES) {
        state.system.logs = state.system.logs.slice(0, MAX_LOG_ENTRIES);
      }
    }),

  addLogEntries: (entries) =>
    set((state) => {
      // Add entries in reverse chronological order (newest first)
      const sortedEntries = [...entries].sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
      state.system.logs.unshift(...sortedEntries);
      
      // Trim logs if exceeding max entries
      if (state.system.logs.length > MAX_LOG_ENTRIES) {
        state.system.logs = state.system.logs.slice(0, MAX_LOG_ENTRIES);
      }
    }),

  clearLogs: () =>
    set((state) => {
      state.system.logs = [];
    }),

  setMaxLogEntries: (max) => {
    // This would be implemented if we wanted dynamic max log entries
    set((state) => {
      if (state.system.logs.length > max) {
        state.system.logs = state.system.logs.slice(0, max);
      }
    });
  },

  // Loading and error states
  setSystemLoading: (loading) =>
    set((state) => {
      state.system.loading = loading;
    }),

  setSystemError: (error) =>
    set((state) => {
      state.system.error = error;
    }),

  // Computed selectors
  getHealthyServices: () => {
    const state = get();
    return Object.entries(state.system.health.services)
      .filter(([, status]) => status.status === 'healthy')
      .map(([service]) => service);
  },

  getUnhealthyServices: () => {
    const state = get();
    return Object.entries(state.system.health.services)
      .filter(([, status]) => status.status === 'unhealthy')
      .map(([service]) => service);
  },

  getOverallHealthStatus: () => {
    const state = get();
    return state.system.health.status;
  },

  getRecentLogs: (count = 50) => {
    const state = get();
    return state.system.logs.slice(0, count);
  },

  getLogsByService: (service) => {
    const state = get();
    return state.system.logs.filter(log => log.service === service);
  },

  getLogsByLevel: (level) => {
    const state = get();
    return state.system.logs.filter(log => log.level === level);
  },
});